from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CampaignCreate(BaseModel):
    name: str
    status: Literal["draft", "active", "paused", "completed"] = "draft"
    settings: Optional[dict[str, Any]] = None


class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    status: str
    settings: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
