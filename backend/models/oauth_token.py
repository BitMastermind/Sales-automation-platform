from sqlalchemy import Column, DateTime, Enum, LargeBinary, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.database import Base


class OauthToken(Base):
    __tablename__ = "oauth_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True))
    provider = Column(
        Enum("gmail", "hubspot", "slack", name="oauth_provider"),
        nullable=False,
    )
    access_token_enc = Column(LargeBinary, nullable=False)
    refresh_token_enc = Column(LargeBinary)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
