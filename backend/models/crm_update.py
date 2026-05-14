from sqlalchemy import Column, DateTime, Enum, ForeignKey, JSON, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.database import Base


class CrmUpdate(Base):
    __tablename__ = "crm_updates"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    lead_id = Column(
        UUID(as_uuid=True),
        ForeignKey("leads.id"),
        nullable=False,
    )
    platform = Column(
        Enum("hubspot", "airtable", "notion", name="crm_platform"),
        nullable=False,
    )
    payload = Column(JSON, nullable=False)
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
