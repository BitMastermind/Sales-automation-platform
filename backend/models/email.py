from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.database import Base


class Email(Base):
    __tablename__ = "emails"
    __table_args__ = (Index("idx_emails_lead", "lead_id"),)

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    lead_id = Column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject = Column(Text)
    body = Column(Text)
    type = Column(
        Enum("outreach", "followup", name="email_type"),
        nullable=False,
    )
    sent_at = Column(DateTime(timezone=True))
    opened_at = Column(DateTime(timezone=True))
    replied_at = Column(DateTime(timezone=True))
    gmail_message_id = Column(String(255))
