"""Shared FastAPI dependencies."""
from __future__ import annotations

from fastapi import Header, HTTPException, status


async def require_device_uuid(
    x_device_uuid: str | None = Header(default=None, alias="X-Device-UUID"),
) -> str:
    """Extract and validate the calling device's UUID from the header.

    Every data endpoint depends on this; without a valid header the request is
    rejected. This is the entire authorization model — data is scoped to the
    device UUID, so a caller can only ever see its own records.
    """
    if not x_device_uuid or len(x_device_uuid.strip()) < 8:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-Device-UUID header.",
        )
    return x_device_uuid.strip()
