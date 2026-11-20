from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, conversations, documents, document_analysis, legal
from app.config.settings import settings

app = FastAPI(
    title="MyLegal AI API",
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
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Workspace-ID"],
)
app.include_router(conversations.router)
app.include_router(documents.router)
app.include_router(document_analysis.router)
app.include_router(chat.router)
app.include_router(legal.router)


@app.get("/")
def root():
    return {"service": "mylegal-ai", "status": "ok", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "mylegal-ai", "jurisdiction": "BD", "workspace_persistence": bool(settings.supabase_url and settings.supabase_service_role_key)}
