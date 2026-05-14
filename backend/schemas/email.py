from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EmailCreate(BaseModel):
    lead_id: UUID
    subject: str
    body: str
    type: Literal["outreach", "followup"]
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    gmail_message_id: Optional[str] = None


class EmailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    subject: Optional[str] = None
    body: Optional[str] = None
    type: str
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    gmail_message_id: Optional[str] = None
