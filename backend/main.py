from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import router as auth_router
from api.campaigns import router as campaigns_router
from api.emails import router as emails_router
from api.internal import router as internal_router
from api.leads import router as leads_router
from api.webhooks import router as webhooks_router
from core.exceptions import register_exception_handlers
from core.logging import setup_logging

setup_logging()

app = FastAPI(title="Sales Automation API", version="0.1.0")
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(campaigns_router, prefix="/api")
app.include_router(leads_router, prefix="/api")
app.include_router(emails_router, prefix="/api")
app.include_router(webhooks_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(internal_router, prefix="/api")


@app.get("/health")
async def health() -> dict:
    return {"data": {"status": "ok"}, "error": None, "meta": {}}
