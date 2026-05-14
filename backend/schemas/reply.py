from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReplyCreate(BaseModel):
    email_id: UUID
    content: str
    classified_as: Literal[
        "interested", "not_interested", "meeting_request",
        "unsubscribe", "needs_more_info", "unknown"
    ] = "unknown"


class ReplyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email_id: UUID
    content: str
    classified_as: str
    received_at: datetime
