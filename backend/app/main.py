from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import chat, conversations, documents, document_analysis, legal, auth_admin
from app.services.auth_security import authenticate_access_token, bind_workspace_to_user
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

app.include_router(conversations.router)
app.include_router(documents.router)
app.include_router(document_analysis.router)
app.include_router(chat.router)
app.include_router(legal.router)
app.include_router(auth_admin.router)


@app.middleware("http")
async def authenticate_api_requests(request: Request, call_next):
    """Protect all API routes with a verified Supabase access token.

    Workspace routes are also bound to the authenticated user on first access.
    This prevents a signed-in user from reading another account's workspace by
    supplying a different X-Workspace-ID header.
    """
    path = request.url.path
    # Browser CORS preflight requests contain no bearer token.
    if request.method == "OPTIONS":
        return await call_next(request)
    if path.startswith("/api/v1/") and path != "/api/v1/auth/bootstrap-super-admin":
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            return JSONResponse({"detail": "লগইন প্রয়োজন।"}, status_code=401)
        try:
            user = authenticate_access_token(token.strip())
            request.state.user = user
            workspace_route = path.startswith("/api/v1/conversations") or (
                path.startswith("/api/v1/documents/") and path != "/api/v1/documents/analyze"
            )
            if workspace_route:
                workspace_id = request.headers.get("X-Workspace-ID")
                if not workspace_id:
                    return JSONResponse({"detail": "X-Workspace-ID header is required."}, status_code=400)
                bind_workspace_to_user(workspace_id, user["id"])
        except HTTPException as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        except Exception:
            return JSONResponse({"detail": "Authentication service unavailable."}, status_code=503)
    return await call_next(request)


@app.get("/")
def root():
    return {"service": "mylegal-ai", "status": "ok", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "mylegal-ai", "jurisdiction": "BD", "workspace_persistence": bool(settings.supabase_url and settings.supabase_service_role_key)}


# Wrap the complete application so CORS headers are added to error responses too.
app = CORSMiddleware(
    app,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Workspace-ID"],
)
