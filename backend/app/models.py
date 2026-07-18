"""SQLAlchemy ORM models.

Notes on portability:
- UUIDs are stored as CHAR(36) strings rather than a native UUID type so the
  same schema works on SQLite and Postgres.
- Money is stored as Numeric(12, 2) (decimal), never float, to avoid rounding
  errors. Amounts are always positive; sign is derived from `direction`.
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    CHAR,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Direction(str, enum.Enum):
    """Which way a debt points."""

    THEY_OWE_ME = "THEY_OWE_ME"
    I_OWE_THEM = "I_OWE_THEM"


class Device(Base):
    """An anonymous device identity. The only 'account' the app has."""

    __tablename__ = "devices"

    uuid: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now()
    )


class Friend(Base):
    __tablename__ = "friends"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=_uuid)
    owner_uuid: Mapped[str] = mapped_column(CHAR(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # A short emoji or a color token for visual identity. Optional.
    avatar_emoji: Mapped[str | None] = mapped_column(String(16), nullable=True)
    avatar_color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now()
    )

    entries: Mapped[list["DebtEntry"]] = relationship(
        back_populates="friend",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (Index("ix_friends_owner_name", "owner_uuid", "name"),)


class DebtEntry(Base):
    __tablename__ = "debt_entries"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=_uuid)
    owner_uuid: Mapped[str] = mapped_column(CHAR(36), nullable=False, index=True)
    friend_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("friends.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    direction: Mapped[Direction] = mapped_column(
        Enum(Direction, native_enum=False, length=16), nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(280), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    is_settled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    settled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        server_default=func.now(),
    )

    friend: Mapped["Friend"] = relationship(back_populates="entries")

    __table_args__ = (
        Index("ix_entries_owner_friend", "owner_uuid", "friend_id"),
        Index("ix_entries_owner_date", "owner_uuid", "date"),
    )
