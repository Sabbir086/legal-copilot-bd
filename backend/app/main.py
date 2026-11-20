from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, documents, legal
from app.config.settings import settings

app = FastAPI(
    title="Legal Copilot BD API",
    version="0.3.0",
    description=(
        "Bangladesh-focused preliminary document screening API. "
        "AI risk findings are document-evidence signals, not verified legal advice."
    ),
)

origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(legal.router)


@app.get("/")
def root():
    return {"service": "legal-copilot-bd", "status": "ok", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "legal-copilot-bd", "jurisdiction": "BD"}
