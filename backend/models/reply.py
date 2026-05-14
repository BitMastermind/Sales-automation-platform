from sqlalchemy import Column, DateTime, Enum, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.database import Base


class Reply(Base):
    __tablename__ = "replies"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    email_id = Column(
        UUID(as_uuid=True),
        ForeignKey("emails.id"),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    classified_as = Column(
        Enum(
            "interested",
            "not_interested",
            "meeting_request",
            "unsubscribe",
            "needs_more_info",
            "unknown",
            name="reply_classification",
        ),
        nullable=False,
        server_default="unknown",
    )
    received_at = Column(DateTime(timezone=True), server_default=func.now())
