"""Pydantic request/response schemas.

Monetary values cross the API as JSON numbers with 2 decimals. Internally
they are `Decimal` to stay exact; Pydantic serializes them to floats in JSON
which is fine for display (values are bounded and 2dp).
"""
from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import Direction

# --------------------------------------------------------------------------- #
# Device
# --------------------------------------------------------------------------- #


class DeviceRegisterIn(BaseModel):
    device_uuid: str = Field(..., min_length=8, max_length=64)


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    created_at: datetime


# --------------------------------------------------------------------------- #
# Friend
# --------------------------------------------------------------------------- #


class FriendCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    avatar_emoji: str | None = Field(default=None, max_length=16)
    avatar_color: str | None = Field(default=None, max_length=16)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank")
        return v


class FriendUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    avatar_emoji: str | None = Field(default=None, max_length=16)
    avatar_color: str | None = Field(default=None, max_length=16)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank")
        return v


class FriendOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    avatar_emoji: str | None
    avatar_color: str | None
    created_at: datetime


class FriendWithBalance(FriendOut):
    # Signed net balance of UNSETTLED entries:
    #   positive => they owe you; negative => you owe them; 0 => settled up.
    balance: Decimal
    last_activity: date_type | None
    open_entry_count: int


# --------------------------------------------------------------------------- #
# Debt entries
# --------------------------------------------------------------------------- #


class EntryCreate(BaseModel):
    friend_id: str
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    direction: Direction
    description: str | None = Field(default=None, max_length=280)
    date: date_type | None = None

    @field_validator("description")
    @classmethod
    def _strip_desc(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None


class EntryUpdate(BaseModel):
    amount: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )
    direction: Direction | None = None
    description: str | None = Field(default=None, max_length=280)
    date: date_type | None = None
    is_settled: bool | None = None

    @field_validator("description")
    @classmethod
    def _strip_desc(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None


class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    friend_id: str
    amount: Decimal
    direction: Direction
    description: str | None
    date: date_type
    is_settled: bool
    settled_at: datetime | None
    created_at: datetime
    updated_at: datetime


class FriendDetailOut(FriendWithBalance):
    entries: list[EntryOut]


# --------------------------------------------------------------------------- #
# Stats
# --------------------------------------------------------------------------- #


class SummaryOut(BaseModel):
    total_owed_to_me: Decimal
    total_i_owe: Decimal
    net_balance: Decimal
    friend_count: int
    open_entry_count: int


class FriendBalancePoint(BaseModel):
    friend_id: str
    name: str
    avatar_emoji: str | None
    avatar_color: str | None
    balance: Decimal


class TimelinePoint(BaseModel):
    date: date_type
    net_balance: Decimal


class TimelineOut(BaseModel):
    points: list[TimelinePoint]
    per_friend: list[FriendBalancePoint]
