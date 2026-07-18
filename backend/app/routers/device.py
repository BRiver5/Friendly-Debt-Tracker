"""Device registration endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/device", tags=["device"])


@router.post("/register", response_model=schemas.DeviceOut)
def register_device(
    payload: schemas.DeviceRegisterIn,
    db: Session = Depends(get_db),
) -> schemas.DeviceOut:
    """Register (or re-affirm) a device UUID generated on the client.

    Idempotent: calling it again for an existing UUID just returns the record,
    so the app can safely call it on every cold start without side effects.
    """
    device = crud.get_or_create_device(db, payload.device_uuid.strip())
    return device
