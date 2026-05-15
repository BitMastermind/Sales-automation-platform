import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, unquote, urlparse

import pytest
import respx
from httpx import Response
from sqlalchemy import select

from core.exceptions import GmailNotConnectedError, GmailQuotaExceededError
from models.oauth_token import OauthToken
from services.gmail_service import GmailService


_TEST_DB_URL = "postgresql+asyncpg://sales:sales@localhost:5432/sales_test"


@pytest.fixture(autouse=True)
async def clear_oauth_tokens():
    """Truncate oauth_tokens before each test using a dedicated connection."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(_TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM oauth_tokens"))
    await engine.dispose()
    yield


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    from cryptography.fernet import Fernet

    from core.config import settings

    monkeypatch.setattr(settings, "fernet_key", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "gmail_client_id", "test-client-id")
    monkeypatch.setattr(settings, "gmail_client_secret", "test-client-secret")
    monkeypatch.setattr(settings, "backend_url", "http://localhost:8000")
    monkeypatch.setattr(settings, "frontend_url", "http://localhost:3000")


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.incr = AsyncMock(return_value=1)
    redis.expireat = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def gmail_service(mock_redis):
    return GmailService(redis_client=mock_redis)


@pytest.fixture
async def connected_token(db_session, patch_settings):
    """Insert a valid (non-expired) encrypted credential blob into oauth_tokens."""
    from core.crypto import encrypt_bytes

    cred_data = json.dumps(
        {
            "token": "valid-access-token",
            "refresh_token": "valid-refresh-token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "scopes": [
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/gmail.readonly",
            ],
        }
    ).encode()

    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    token = OauthToken(
        provider="gmail",
        access_token_enc=encrypt_bytes(cred_data),
        refresh_token_enc=encrypt_bytes(b"valid-refresh-token"),
        expires_at=expires_at,
    )
    db_session.add(token)
    await db_session.commit()
    return token


# ── TEST 1 ──────────────────────────────────────────────────────────────────


async def test_get_auth_url_contains_required_params(gmail_service):
    """Auth URL must contain client_id from settings, required scopes, and redirect_uri."""
    url = await gmail_service.get_auth_url()

    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    assert "accounts.google.com" in parsed.netloc
    assert params["client_id"] == ["test-client-id"]
    assert params["response_type"] == ["code"]

    scopes = unquote(params["scope"][0])
    assert "gmail.send" in scopes
    assert "gmail.readonly" in scopes

    redirect_uri = unquote(params["redirect_uri"][0])
    assert redirect_uri.endswith("/api/auth/gmail/callback")


# ── TEST 2 ──────────────────────────────────────────────────────────────────


async def test_exchange_code_saves_encrypted_token(db_session, gmail_service):
    """exchange_code POSTs to Google token endpoint and stores Fernet-encrypted tokens."""
    from core.crypto import decrypt_bytes

    with respx.mock(assert_all_called=True) as mock:
        mock.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(
                200,
                json={
                    "access_token": "brand-new-access-token",
                    "refresh_token": "brand-new-refresh-token",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )
        )

        await gmail_service.exchange_code("auth-code-123", db_session)

    result = await db_session.execute(
        select(OauthToken).where(OauthToken.provider == "gmail")
    )
    row = result.scalar_one()

    # Ciphertext must not contain the plaintext token
    assert b"brand-new-access-token" not in row.access_token_enc

    # Decryption must recover the access token
    decrypted = decrypt_bytes(row.access_token_enc)
    assert b"brand-new-access-token" in decrypted


# ── TEST 3 ──────────────────────────────────────────────────────────────────


@patch("services.gmail_service.build")
async def test_send_email_success_returns_message_id_and_increments_counter(
    mock_build, db_session, gmail_service, connected_token
):
    """send_email returns message_id from Gmail API and increments the Redis daily counter."""
    mock_svc = MagicMock()
    mock_build.return_value = mock_svc
    mock_svc.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "msg-abc123"
    }
    gmail_service._redis.get = AsyncMock(return_value=b"5")  # 5 sent today

    msg_id = await gmail_service.send_email(
        to="lead@example.com",
        subject="Personalized outreach",
        body="Hello from the platform",
        reply_to=None,
        db=db_session,
    )

    assert msg_id == "msg-abc123"
    gmail_service._redis.incr.assert_called_once()


# ── TEST 4 ──────────────────────────────────────────────────────────────────


async def test_send_email_raises_quota_exceeded_and_does_not_increment(
    db_session, gmail_service, connected_token
):
    """send_email raises GmailQuotaExceededError at 100 and must NOT increment the counter."""
    gmail_service._redis.get = AsyncMock(return_value=b"100")

    with pytest.raises(GmailQuotaExceededError):
        await gmail_service.send_email(
            to="lead@example.com",
            subject="Test",
            body="Body",
            reply_to=None,
            db=db_session,
        )

    gmail_service._redis.incr.assert_not_called()


# ── TEST 5 ──────────────────────────────────────────────────────────────────


async def test_token_refresh_saves_new_encrypted_token(db_session, gmail_service):
    """_get_credentials refreshes an expired token via httpx and re-encrypts it in DB."""
    from core.crypto import decrypt_bytes, encrypt_bytes

    cred_data = json.dumps(
        {
            "token": "expired-access-token",
            "refresh_token": "valid-refresh-token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "scopes": ["https://www.googleapis.com/auth/gmail.send"],
        }
    ).encode()

    token_row = OauthToken(
        provider="gmail",
        access_token_enc=encrypt_bytes(cred_data),
        refresh_token_enc=encrypt_bytes(b"valid-refresh-token"),
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # expired
    )
    db_session.add(token_row)
    await db_session.commit()

    with respx.mock(assert_all_called=True) as mock:
        mock.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(
                200,
                json={
                    "access_token": "refreshed-access-token",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )
        )

        await gmail_service._get_credentials(db_session)

    await db_session.refresh(token_row)
    decrypted = decrypt_bytes(token_row.access_token_enc)
    decoded = json.loads(decrypted)

    assert decoded["token"] == "refreshed-access-token"
    assert decoded["token"] != "expired-access-token"
