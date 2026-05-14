import csv
import io
import logging
import re
from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.response import err, ok, paginated
from models.email import Email
from models.lead import Lead
from models.reply import Reply
from schemas.email import EmailRead
from schemas.lead import LeadRead
from schemas.reply import ReplyRead

router = APIRouter(prefix="/leads", tags=["leads"])
logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


@router.post("/upload")
async def upload_leads(
    file: UploadFile = File(...),
    campaign_id: UUID = Form(...),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    fieldnames = set(reader.fieldnames or [])
    if not {"company_name", "email"}.issubset(fieldnames):
        err("MISSING_REQUIRED_COLUMNS", "CSV must contain columns: company_name, email")

    to_insert: list[dict] = []
    skipped = 0
    errors: list[dict] = []

    for row_num, row in enumerate(reader, start=2):
        email = (row.get("email") or "").strip()
        if not _EMAIL_RE.match(email):
            skipped += 1
            errors.append({"row": row_num, "reason": "invalid email"})
            continue
        to_insert.append(
            {
                "campaign_id": campaign_id,
                "company_name": (row.get("company_name") or "").strip(),
                "email": email,
                "website": (row.get("website") or "").strip() or None,
                "contact_name": (row.get("contact_name") or "").strip() or None,
            }
        )

    if to_insert:
        await db.execute(insert(Lead), to_insert)
        await db.commit()

    return ok({"inserted": len(to_insert), "skipped": skipped, "errors": errors})


@router.get("")
async def list_leads(
    campaign_id: UUID | None = None,
    status: str | None = None,
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func

    base = select(Lead)
    count_base = select(func.count()).select_from(Lead)
    if campaign_id is not None:
        base = base.where(Lead.campaign_id == campaign_id)
        count_base = count_base.where(Lead.campaign_id == campaign_id)
    if status is not None:
        base = base.where(Lead.status == status)
        count_base = count_base.where(Lead.status == status)

    total = (await db.scalar(count_base)) or 0
    stmt = base.order_by(Lead.created_at.desc()).offset((page - 1) * size).limit(size)
    leads = (await db.execute(stmt)).scalars().all()
    return paginated([LeadRead.model_validate(l).model_dump() for l in leads], page, size, total)


@router.get("/{lead_id}")
async def get_lead(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, lead_id)
    if lead is None:
        err("LEAD_NOT_FOUND", "Lead not found", 404)

    emails_result = await db.execute(
        select(Email).where(Email.lead_id == lead_id).order_by(Email.sent_at.desc())
    )
    emails = emails_result.scalars().all()

    email_ids = [e.id for e in emails]
    replies_by_email: dict = defaultdict(list)
    if email_ids:
        replies_result = await db.execute(
            select(Reply).where(Reply.email_id.in_(email_ids))
        )
        for reply in replies_result.scalars().all():
            replies_by_email[reply.email_id].append(ReplyRead.model_validate(reply).model_dump())

    emails_data = []
    for email in emails:
        email_dict = EmailRead.model_validate(email).model_dump()
        email_dict["replies"] = replies_by_email[email.id]
        emails_data.append(email_dict)

    lead_data = LeadRead.model_validate(lead).model_dump()
    lead_data["emails"] = emails_data
    return ok(lead_data)
