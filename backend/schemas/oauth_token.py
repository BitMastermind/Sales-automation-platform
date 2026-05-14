from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OauthTokenCreate(BaseModel):
    user_id: Optional[UUID] = None
    provider: Literal["gmail", "hubspot", "slack"]
    access_token_enc: bytes
    refresh_token_enc: Optional[bytes] = None
    expires_at: Optional[datetime] = None


class OauthTokenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: Optional[UUID] = None
    provider: str
    access_token_enc: bytes
    refresh_token_enc: Optional[bytes] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
