"""Stats / chart-data endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..deps import require_device_uuid

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary", response_model=schemas.SummaryOut)
def get_summary(
    owner: str = Depends(require_device_uuid),
    db: Session = Depends(get_db),
) -> schemas.SummaryOut:
    return crud.summary(db, owner)


@router.get("/timeline", response_model=schemas.TimelineOut)
def get_timeline(
    days: int = Query(default=30, ge=1, le=365),
    owner: str = Depends(require_device_uuid),
    db: Session = Depends(get_db),
) -> schemas.TimelineOut:
    return crud.timeline(db, owner, days)
