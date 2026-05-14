from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CrmUpdateCreate(BaseModel):
    lead_id: UUID
    platform: Literal["hubspot", "airtable", "notion"]
    payload: dict[str, Any]


class CrmUpdateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    platform: str
    payload: dict[str, Any]
    synced_at: datetime
