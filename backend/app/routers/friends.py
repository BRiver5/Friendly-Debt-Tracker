"""Friend endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..deps import require_device_uuid

router = APIRouter(prefix="/friends", tags=["friends"])


@router.post("", response_model=schemas.FriendWithBalance, status_code=201)
def create_friend(
    payload: schemas.FriendCreate,
    owner: str = Depends(require_device_uuid),
    db: Session = Depends(get_db),
) -> schemas.FriendWithBalance:
    friend = crud.create_friend(db, owner, payload)
    return crud.friend_with_balance(friend)


@router.get("", response_model=list[schemas.FriendWithBalance])
def list_friends(
    owner: str = Depends(require_device_uuid),
    db: Session = Depends(get_db),
) -> list[schemas.FriendWithBalance]:
    friends = crud.list_friends(db, owner)
    return [crud.friend_with_balance(f) for f in friends]


def _get_or_404(db: Session, owner: str, friend_id: str):
    friend = crud.get_friend(db, owner, friend_id)
    if friend is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Friend not found."
        )
    return friend


@router.get("/{friend_id}", response_model=schemas.FriendDetailOut)
def get_friend(
    friend_id: str,
    owner: str = Depends(require_device_uuid),
    db: Session = Depends(get_db),
) -> schemas.FriendDetailOut:
    friend = _get_or_404(db, owner, friend_id)
    base = crud.friend_with_balance(friend)
    entries = crud.list_entries(db, owner, friend_id)
    return schemas.FriendDetailOut(
        **base.model_dump(),
        entries=[schemas.EntryOut.model_validate(e) for e in entries],
    )


@router.patch("/{friend_id}", response_model=schemas.FriendWithBalance)
def update_friend(
    friend_id: str,
    payload: schemas.FriendUpdate,
    owner: str = Depends(require_device_uuid),
    db: Session = Depends(get_db),
) -> schemas.FriendWithBalance:
    friend = _get_or_404(db, owner, friend_id)
    friend = crud.update_friend(db, friend, payload)
    return crud.friend_with_balance(friend)


@router.delete("/{friend_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_friend(
    friend_id: str,
    owner: str = Depends(require_device_uuid),
    db: Session = Depends(get_db),
) -> None:
    friend = _get_or_404(db, owner, friend_id)
    crud.delete_friend(db, friend)


@router.post("/{friend_id}/settle", response_model=schemas.FriendDetailOut)
def settle_up(
    friend_id: str,
    owner: str = Depends(require_device_uuid),
    db: Session = Depends(get_db),
) -> schemas.FriendDetailOut:
    """Mark all outstanding entries with this friend as settled."""
    friend = _get_or_404(db, owner, friend_id)
    crud.settle_all_for_friend(db, owner, friend_id)
    db.refresh(friend)
    base = crud.friend_with_balance(friend)
    entries = crud.list_entries(db, owner, friend_id)
    return schemas.FriendDetailOut(
        **base.model_dump(),
        entries=[schemas.EntryOut.model_validate(e) for e in entries],
    )
