from fastapi import APIRouter

from core.response import err, ok

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/gmail")
async def gmail_auth_url():
    return ok({"auth_url": "<placeholder>"})


@router.get("/gmail/callback")
async def gmail_callback():
    err("NOT_IMPLEMENTED", "Gmail OAuth callback not yet implemented", 501)
