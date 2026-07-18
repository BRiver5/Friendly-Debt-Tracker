"""Data-access and computation layer.

All functions are scoped by `owner_uuid`; a caller can never read or mutate
another device's data. Balances are computed here, never stored, so they can
never drift out of sync with the underlying entries.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas

TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def _q(value: Decimal) -> Decimal:
    """Quantize to 2 decimal places."""
    return (value or ZERO).quantize(TWO_PLACES)


def _signed(entry: models.DebtEntry) -> Decimal:
    """Signed contribution of an entry to a balance (they owe me = positive)."""
    amount = Decimal(entry.amount)
    if entry.direction == models.Direction.THEY_OWE_ME:
        return amount
    return -amount


# --------------------------------------------------------------------------- #
# Device
# --------------------------------------------------------------------------- #


def get_or_create_device(db: Session, device_uuid: str) -> models.Device:
    device = db.get(models.Device, device_uuid)
    if device is None:
        device = models.Device(uuid=device_uuid)
        db.add(device)
        db.commit()
        db.refresh(device)
    return device


# --------------------------------------------------------------------------- #
# Friends
# --------------------------------------------------------------------------- #


def create_friend(
    db: Session, owner_uuid: str, data: schemas.FriendCreate
) -> models.Friend:
    friend = models.Friend(
        owner_uuid=owner_uuid,
        name=data.name,
        avatar_emoji=data.avatar_emoji,
        avatar_color=data.avatar_color,
    )
    db.add(friend)
    db.commit()
    db.refresh(friend)
    return friend


def get_friend(
    db: Session, owner_uuid: str, friend_id: str
) -> models.Friend | None:
    stmt = select(models.Friend).where(
        models.Friend.id == friend_id,
        models.Friend.owner_uuid == owner_uuid,
    )
    return db.scalars(stmt).first()


def list_friends(db: Session, owner_uuid: str) -> list[models.Friend]:
    stmt = (
        select(models.Friend)
        .where(models.Friend.owner_uuid == owner_uuid)
        .order_by(models.Friend.name.asc())
    )
    return list(db.scalars(stmt).all())


def update_friend(
    db: Session, friend: models.Friend, data: schemas.FriendUpdate
) -> models.Friend:
    payload = data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(friend, field, value)
    db.commit()
    db.refresh(friend)
    return friend


def delete_friend(db: Session, friend: models.Friend) -> None:
    db.delete(friend)  # entries cascade-delete
    db.commit()


# --------------------------------------------------------------------------- #
# Balance helpers
# --------------------------------------------------------------------------- #


def friend_balance(friend: models.Friend) -> Decimal:
    """Signed net of this friend's UNSETTLED entries."""
    total = ZERO
    for entry in friend.entries:
        if not entry.is_settled:
            total += _signed(entry)
    return _q(total)


def friend_last_activity(friend: models.Friend) -> date | None:
    if not friend.entries:
        return None
    return max(entry.date for entry in friend.entries)


def friend_open_count(friend: models.Friend) -> int:
    return sum(1 for entry in friend.entries if not entry.is_settled)


def friend_with_balance(friend: models.Friend) -> schemas.FriendWithBalance:
    return schemas.FriendWithBalance(
        id=friend.id,
        name=friend.name,
        avatar_emoji=friend.avatar_emoji,
        avatar_color=friend.avatar_color,
        created_at=friend.created_at,
        balance=friend_balance(friend),
        last_activity=friend_last_activity(friend),
        open_entry_count=friend_open_count(friend),
    )


# --------------------------------------------------------------------------- #
# Entries
# --------------------------------------------------------------------------- #


def create_entry(
    db: Session, owner_uuid: str, data: schemas.EntryCreate
) -> models.DebtEntry:
    entry = models.DebtEntry(
        owner_uuid=owner_uuid,
        friend_id=data.friend_id,
        amount=data.amount,
        direction=data.direction,
        description=data.description,
        date=data.date or date.today(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_entry(
    db: Session, owner_uuid: str, entry_id: str
) -> models.DebtEntry | None:
    stmt = select(models.DebtEntry).where(
        models.DebtEntry.id == entry_id,
        models.DebtEntry.owner_uuid == owner_uuid,
    )
    return db.scalars(stmt).first()


def list_entries(
    db: Session, owner_uuid: str, friend_id: str | None = None
) -> list[models.DebtEntry]:
    stmt = select(models.DebtEntry).where(
        models.DebtEntry.owner_uuid == owner_uuid
    )
    if friend_id is not None:
        stmt = stmt.where(models.DebtEntry.friend_id == friend_id)
    stmt = stmt.order_by(
        models.DebtEntry.date.desc(), models.DebtEntry.created_at.desc()
    )
    return list(db.scalars(stmt).all())


def update_entry(
    db: Session, entry: models.DebtEntry, data: schemas.EntryUpdate
) -> models.DebtEntry:
    payload = data.model_dump(exclude_unset=True)

    # Keep settled_at consistent with the is_settled flag.
    if "is_settled" in payload:
        if payload["is_settled"] and not entry.is_settled:
            entry.settled_at = datetime.now(timezone.utc)
        elif not payload["is_settled"]:
            entry.settled_at = None

    for field, value in payload.items():
        setattr(entry, field, value)

    db.commit()
    db.refresh(entry)
    return entry


def delete_entry(db: Session, entry: models.DebtEntry) -> None:
    db.delete(entry)
    db.commit()


def settle_all_for_friend(
    db: Session, owner_uuid: str, friend_id: str
) -> int:
    """Mark every unsettled entry for a friend as settled. Returns the count."""
    entries = [
        e
        for e in list_entries(db, owner_uuid, friend_id)
        if not e.is_settled
    ]
    now = datetime.now(timezone.utc)
    for entry in entries:
        entry.is_settled = True
        entry.settled_at = now
    if entries:
        db.commit()
    return len(entries)


# --------------------------------------------------------------------------- #
# Stats
# --------------------------------------------------------------------------- #


def summary(db: Session, owner_uuid: str) -> schemas.SummaryOut:
    friends = list_friends(db, owner_uuid)
    total_owed_to_me = ZERO
    total_i_owe = ZERO
    open_entries = 0

    for friend in friends:
        for entry in friend.entries:
            if entry.is_settled:
                continue
            open_entries += 1
            signed = _signed(entry)
            if signed > 0:
                total_owed_to_me += signed
            else:
                total_i_owe += -signed

    net = total_owed_to_me - total_i_owe
    return schemas.SummaryOut(
        total_owed_to_me=_q(total_owed_to_me),
        total_i_owe=_q(total_i_owe),
        net_balance=_q(net),
        friend_count=len(friends),
        open_entry_count=open_entries,
    )


def timeline(
    db: Session, owner_uuid: str, days: int = 30
) -> schemas.TimelineOut:
    """Net-balance-over-time plus a per-friend balance breakdown.

    The timeline is the cumulative signed sum of ALL entries (settled or not)
    up to and including each day, so it reflects the real history of who owed
    whom over the window — not just the current open balance.
    """
    days = max(1, min(days, 365))
    today = date.today()
    start = today - timedelta(days=days - 1)

    entries = list_entries(db, owner_uuid)

    # Cumulative net at the day BEFORE the window start (baseline).
    baseline = ZERO
    daily_delta: dict[date, Decimal] = {}
    for entry in entries:
        signed = _signed(entry)
        if entry.date < start:
            baseline += signed
        else:
            daily_delta[entry.date] = daily_delta.get(entry.date, ZERO) + signed

    points: list[schemas.TimelinePoint] = []
    running = baseline
    for offset in range(days):
        day = start + timedelta(days=offset)
        running += daily_delta.get(day, ZERO)
        points.append(
            schemas.TimelinePoint(date=day, net_balance=_q(running))
        )

    friends = list_friends(db, owner_uuid)
    per_friend = [
        schemas.FriendBalancePoint(
            friend_id=f.id,
            name=f.name,
            avatar_emoji=f.avatar_emoji,
            avatar_color=f.avatar_color,
            balance=friend_balance(f),
        )
        for f in friends
    ]
    # Rank by absolute open balance so the chart highlights what matters.
    per_friend.sort(key=lambda p: abs(p.balance), reverse=True)

    return schemas.TimelineOut(points=points, per_friend=per_friend)
