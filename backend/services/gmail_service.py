import asyncio
import base64
import json
import logging
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from typing import Optional

import httpx
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.crypto import decrypt_bytes, encrypt_bytes
from core.exceptions import GmailNotConnectedError, GmailQuotaExceededError
from models.oauth_token import OauthToken

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GmailService:
    def __init__(self, redis_client=None) -> None:
        self._redis = redis_client
        # Per-instance lock prevents concurrent token refreshes within one process.
        # Sufficient for single-worker MVP; replace with Redis lock for multi-worker.
        self._refresh_lock: asyncio.Lock = asyncio.Lock()

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as aioredis

            self._redis = await aioredis.from_url(settings.redis_url)
        return self._redis

    # ── Auth URL ─────────────────────────────────────────────────────────────

    async def get_auth_url(self) -> str:
        from urllib.parse import urlencode

        params = {
            "client_id": settings.gmail_client_id,
            "redirect_uri": f"{settings.backend_url}/api/auth/gmail/callback",
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{_GOOGLE_AUTH_URL}?{urlencode(params)}"

    # ── Token exchange ────────────────────────────────────────────────────────

    async def exchange_code(self, code: str, db: AsyncSession) -> None:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.gmail_client_id,
                    "client_secret": settings.gmail_client_secret,
                    "redirect_uri": f"{settings.backend_url}/api/auth/gmail/callback",
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            token_data = resp.json()

        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=token_data.get("expires_in", 3600)
        )

        cred_blob = json.dumps(
            {
                "token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token", ""),
                "token_uri": _GOOGLE_TOKEN_URL,
                "client_id": settings.gmail_client_id,
                "client_secret": settings.gmail_client_secret,
                "scopes": SCOPES,
            }
        ).encode()

        result = await db.execute(
            select(OauthToken).where(OauthToken.provider == "gmail")
        )
        row = result.scalars().first()

        if row is None:
            row = OauthToken(provider="gmail")
            db.add(row)

        row.access_token_enc = encrypt_bytes(cred_blob)
        row.refresh_token_enc = encrypt_bytes(
            token_data.get("refresh_token", "").encode()
        )
        row.expires_at = expires_at
        await db.commit()

    # ── Credentials (with transparent refresh) ────────────────────────────────

    async def _get_credentials(self, db: AsyncSession) -> Credentials:
        result = await db.execute(
            select(OauthToken).where(OauthToken.provider == "gmail")
        )
        row = result.scalars().first()
        if row is None:
            raise GmailNotConnectedError

        async with self._refresh_lock:
            # Re-read after acquiring lock — another coroutine may have refreshed already.
            await db.refresh(row)

            cred_data = json.loads(decrypt_bytes(row.access_token_enc))
            is_expired = row.expires_at is None or row.expires_at <= datetime.now(
                timezone.utc
            )

            if is_expired:
                refresh_token = cred_data.get("refresh_token") or decrypt_bytes(
                    row.refresh_token_enc
                ).decode()

                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        _GOOGLE_TOKEN_URL,
                        data={
                            "client_id": settings.gmail_client_id,
                            "client_secret": settings.gmail_client_secret,
                            "refresh_token": refresh_token,
                            "grant_type": "refresh_token",
                        },
                    )
                    resp.raise_for_status()
                    refreshed = resp.json()

                cred_data["token"] = refreshed["access_token"]
                row.access_token_enc = encrypt_bytes(json.dumps(cred_data).encode())
                row.expires_at = datetime.now(timezone.utc) + timedelta(
                    seconds=refreshed.get("expires_in", 3600)
                )
                await db.commit()

        return Credentials(
            token=cred_data["token"],
            refresh_token=cred_data.get("refresh_token"),
            token_uri=cred_data.get("token_uri", _GOOGLE_TOKEN_URL),
            client_id=cred_data.get("client_id", settings.gmail_client_id),
            client_secret=cred_data.get("client_secret", settings.gmail_client_secret),
            scopes=cred_data.get("scopes", SCOPES),
        )

    # ── Send email ────────────────────────────────────────────────────────────

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        reply_to: Optional[str],
        db: AsyncSession,
    ) -> str:
        redis = await self._get_redis()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rate_key = f"gmail:sent:{today}"

        count_bytes = await redis.get(rate_key)
        if count_bytes is not None and int(count_bytes) >= 100:
            raise GmailQuotaExceededError("Daily Gmail send limit reached")

        creds = await self._get_credentials(db)

        mime = MIMEText(body, "plain")
        mime["to"] = to
        mime["subject"] = subject
        if reply_to:
            mime["Reply-To"] = reply_to

        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()

        loop = asyncio.get_event_loop()
        service = await loop.run_in_executor(
            None, lambda: build("gmail", "v1", credentials=creds)
        )
        result = await loop.run_in_executor(
            None,
            lambda: service.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute(),
        )

        # Increment only after confirmed success
        await redis.incr(rate_key)
        midnight = (
            datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            + timedelta(days=1)
        )
        await redis.expireat(rate_key, int(midnight.timestamp()))

        return result["id"]

    # ── Create draft ──────────────────────────────────────────────────────────

    async def create_draft(
        self, to: str, subject: str, body: str, db: AsyncSession
    ) -> str:
        creds = await self._get_credentials(db)
        mime = MIMEText(body, "plain")
        mime["to"] = to
        mime["subject"] = subject
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()

        loop = asyncio.get_event_loop()
        service = await loop.run_in_executor(
            None, lambda: build("gmail", "v1", credentials=creds)
        )
        result = await loop.run_in_executor(
            None,
            lambda: service.users()
            .drafts()
            .create(userId="me", body={"message": {"raw": raw}})
            .execute(),
        )
        return result["id"]

    # ── List recent replies ───────────────────────────────────────────────────

    async def list_recent_replies(
        self, since_timestamp: datetime, db: AsyncSession
    ) -> list[dict]:
        creds = await self._get_credentials(db)
        after_epoch = int(since_timestamp.timestamp())
        query = f"is:inbox after:{after_epoch}"

        loop = asyncio.get_event_loop()
        service = await loop.run_in_executor(
            None, lambda: build("gmail", "v1", credentials=creds)
        )
        results = await loop.run_in_executor(
            None,
            lambda: service.users()
            .messages()
            .list(userId="me", q=query)
            .execute(),
        )

        messages = results.get("messages", [])
        output = []
        for msg in messages:
            detail = await loop.run_in_executor(
                None,
                lambda m=msg: service.users()
                .messages()
                .get(userId="me", id=m["id"], format="metadata")
                .execute(),
            )
            headers = {h["name"].lower(): h["value"] for h in detail.get("payload", {}).get("headers", [])}
            output.append(
                {
                    "gmail_message_id": detail["id"],
                    "from": headers.get("from", ""),
                    "subject": headers.get("subject", ""),
                    "snippet": detail.get("snippet", ""),
                    "received_at": datetime.fromtimestamp(
                        int(detail["internalDate"]) / 1000, tz=timezone.utc
                    ),
                }
            )
        return output
