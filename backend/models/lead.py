from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, JSON, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.database import Base


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("idx_leads_email", "email"),
        Index("idx_leads_campaign", "campaign_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_name = Column(String(255), nullable=False)
    website = Column(String(500))
    contact_name = Column(String(255))
    email = Column(String(255), nullable=False)
    status = Column(
        Enum(
            "new",
            "researched",
            "email_sent",
            "replied",
            "meeting_booked",
            "unsubscribed",
            name="lead_status",
        ),
        nullable=False,
        server_default="new",
    )
    research_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
