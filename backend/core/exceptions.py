from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class GmailQuotaExceededError(Exception):
    pass


class GmailNotConnectedError(Exception):
    pass


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(GmailQuotaExceededError)
    async def gmail_quota_handler(request: Request, exc: GmailQuotaExceededError):
        return JSONResponse(
            status_code=429,
            content={
                "data": None,
                "error": {"code": "GMAIL_QUOTA_EXCEEDED", "message": "Daily Gmail send limit (100) reached."},
                "meta": {},
            },
        )

    @app.exception_handler(GmailNotConnectedError)
    async def gmail_not_connected_handler(request: Request, exc: GmailNotConnectedError):
        return JSONResponse(
            status_code=400,
            content={
                "data": None,
                "error": {"code": "GMAIL_NOT_CONNECTED", "message": "Gmail account not connected. Complete OAuth first."},
                "meta": {},
            },
        )
