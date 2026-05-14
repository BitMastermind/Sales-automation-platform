from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LeadCreate(BaseModel):
    campaign_id: UUID
    company_name: str
    email: str
    website: Optional[str] = None
    contact_name: Optional[str] = None
    status: Literal[
        "new", "researched", "email_sent", "replied", "meeting_booked", "unsubscribed"
    ] = "new"
    research_data: Optional[dict[str, Any]] = None


class LeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    company_name: str
    email: str
    website: Optional[str] = None
    contact_name: Optional[str] = None
    status: str
    research_data: Optional[dict[str, Any]] = None
    created_at: datetime
