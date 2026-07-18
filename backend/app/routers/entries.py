"""Debt entry endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..deps import require_device_uuid

router = APIRouter(prefix="/entries", tags=["entries"])


@router.post("", response_model=schemas.EntryOut, status_code=201)
def create_entry(
    payload: schemas.EntryCreate,
    owner: str = Depends(require_device_uuid),
    db: Session = Depends(get_db),
) -> schemas.EntryOut:
    # Ensure the friend exists and belongs to this device before creating.
    friend = crud.get_friend(db, owner, payload.friend_id)
    if friend is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend not found for this device.",
        )
    entry = crud.create_entry(db, owner, payload)
    return schemas.EntryOut.model_validate(entry)


@router.get("", response_model=list[schemas.EntryOut])
def list_entries(
    friend_id: str | None = None,
    owner: str = Depends(require_device_uuid),
    db: Session = Depends(get_db),
) -> list[schemas.EntryOut]:
    entries = crud.list_entries(db, owner, friend_id)
    return [schemas.EntryOut.model_validate(e) for e in entries]


def _get_or_404(db: Session, owner: str, entry_id: str):
    entry = crud.get_entry(db, owner, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found."
        )
    return entry


@router.get("/{entry_id}", response_model=schemas.EntryOut)
def get_entry(
    entry_id: str,
    owner: str = Depends(require_device_uuid),
    db: Session = Depends(get_db),
) -> schemas.EntryOut:
    entry = _get_or_404(db, owner, entry_id)
    return schemas.EntryOut.model_validate(entry)


@router.patch("/{entry_id}", response_model=schemas.EntryOut)
def update_entry(
    entry_id: str,
    payload: schemas.EntryUpdate,
    owner: str = Depends(require_device_uuid),
    db: Session = Depends(get_db),
) -> schemas.EntryOut:
    entry = _get_or_404(db, owner, entry_id)
    entry = crud.update_entry(db, entry, payload)
    return schemas.EntryOut.model_validate(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: str,
    owner: str = Depends(require_device_uuid),
    db: Session = Depends(get_db),
) -> None:
    entry = _get_or_404(db, owner, entry_id)
    crud.delete_entry(db, entry)
