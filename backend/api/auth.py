from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.response import err, ok
from models.oauth_token import OauthToken
from services.gmail_service import GmailService

router = APIRouter(prefix="/auth", tags=["auth"])

_gmail_service = GmailService()


@router.get("/gmail")
async def gmail_auth_url():
    return ok({"auth_url": await _gmail_service.get_auth_url()})


@router.get("/gmail/callback")
async def gmail_callback(code: str = "", db: AsyncSession = Depends(get_db)):
    if not code:
        err("MISSING_CODE", "Authorization code missing from callback", 400)
    await _gmail_service.exchange_code(code, db)
    return RedirectResponse(url=f"{settings.frontend_url}/settings?gmail=connected")


@router.get("/gmail/status")
async def gmail_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OauthToken).where(OauthToken.provider == "gmail")
    )
    row = result.scalar_one_or_none()
    return ok({"connected": row is not None, "email": None})
