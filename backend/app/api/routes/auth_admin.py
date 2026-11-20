from __future__ import annotations
from collections import Counter
from datetime import datetime, timedelta, timezone
from uuid import UUID
import hmac

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.services.auth_security import get_request_user, require_admin, require_super_admin
from app.services.supabase_client import get_supabase_client

router = APIRouter(prefix="/api/v1", tags=["authentication and administration"])


class RoleUpdate(BaseModel):
    role: str = Field(pattern="^(user|admin)$")


class SuperAdminBootstrapRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=256)


def _client():
    return get_supabase_client()


@router.get("/auth/me")
def auth_me(request: Request):
    user = get_request_user(request)
    now = datetime.now(timezone.utc).isoformat()
    _client().table("profiles").update({"last_sign_in_at": now}).eq("id", user["id"]).execute()
    return {"user": {**user, "last_sign_in_at": now}}


@router.post("/auth/bootstrap-super-admin")
def bootstrap_super_admin(payload: SuperAdminBootstrapRequest):
    """Provision the fixed Super Admin only when the configured credentials are presented."""
    email = (settings.super_admin_email or "").strip().lower()
    password = settings.super_admin_password or ""
    if not email or not password:
        raise HTTPException(status_code=503, detail="Backend-এ SUPER_ADMIN_EMAIL ও SUPER_ADMIN_PASSWORD secret সেট করুন।")
    if not hmac.compare_digest(payload.email.strip().lower(), email) or not hmac.compare_digest(payload.password, password):
        raise HTTPException(status_code=403, detail="এই credentials-এর জন্য Super Admin provisioning অনুমোদিত নয়।")
    client = _client()
    existing = client.table("profiles").select("id,email,role").eq("email", email).limit(1).execute().data or []
    if existing:
        profile = existing[0]
        if profile.get("role") == "super_admin":
            return {"created": False, "ready": True}
        try:
            # The configured email is reserved for Super Admin. If it was
            # registered before the first bootstrap, recover it only after the
            # submitted password has matched the backend-only secret above.
            client.auth.admin.update_user_by_id(
                str(profile["id"]),
                {"password": password, "email_confirm": True},
            )
            client.table("profiles").update({"role": "super_admin", "email": email}).eq("id", str(profile["id"])).execute()
            return {"created": False, "ready": True, "recovered": True}
        except Exception as exc:
            raise HTTPException(status_code=409, detail="Reserved Super Admin account recover করা যায়নি। Supabase Auth permissions পরীক্ষা করুন।") from exc
    try:
        auth_response = client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"display_name": "Super Admin"},
        })
        created_user = getattr(auth_response, "user", None) or (auth_response.get("user") if isinstance(auth_response, dict) else None)
        if hasattr(created_user, "model_dump"):
            created_user = created_user.model_dump()
        user_id = (created_user or {}).get("id") if isinstance(created_user, dict) else getattr(created_user, "id", None)
        if not user_id:
            raise RuntimeError("Supabase Auth did not return the created user ID")
        # Explicit server-side grant: public self-signup can never grant this role.
        existing_profile = client.table("profiles").select("id").eq("id", str(user_id)).limit(1).execute().data or []
        if existing_profile:
            client.table("profiles").update({"role": "super_admin", "email": email}).eq("id", str(user_id)).execute()
        else:
            client.table("profiles").insert({"id": str(user_id), "email": email, "role": "super_admin"}).execute()
    except Exception as exc:
        raise HTTPException(status_code=409, detail="Super Admin Auth account তৈরি করা যায়নি। Supabase Auth users ও migration পরীক্ষা করুন।") from exc
    return {"created": True, "ready": True, "message": "Super Admin account তৈরি হয়েছে। এখন নির্ধারিত email/password দিয়ে sign in করুন।"}


@router.get("/admin/overview")
def admin_overview(request: Request):
    require_admin(request)
    client = _client()
    users = client.table("profiles").select("id", count="exact").execute()
    events = client.table("chatbot_search_events").select("id", count="exact").execute()
    recent = client.table("chatbot_search_events").select("id,user_id,query_text,query_category,retrieved_sections,created_at").order("created_at", desc=True).limit(10).execute().data or []
    return {
        "total_users": users.count or 0,
        "total_searches": events.count or 0,
        "recent_searches": recent,
    }


@router.get("/admin/users")
def admin_users(request: Request):
    require_admin(request)
    rows = _client().table("profiles").select("id,email,role,is_active,created_at,last_sign_in_at").order("created_at", desc=True).limit(500).execute().data or []
    return {"users": rows}


@router.patch("/admin/users/{user_id}/role")
def update_user_role(user_id: str, payload: RoleUpdate, request: Request):
    actor = require_super_admin(request)
    try:
        target_id = str(UUID(user_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user id.") from exc
    if target_id == str(actor["id"]):
        raise HTTPException(status_code=400, detail="নিজের Super Admin role পরিবর্তন করা যাবে না।")
    client = _client()
    target_rows = client.table("profiles").select("id,email,role").eq("id", target_id).limit(1).execute().data or []
    if not target_rows:
        raise HTTPException(status_code=404, detail="User পাওয়া যায়নি।")
    target = target_rows[0]
    if target.get("role") == "super_admin" or target.get("email", "").lower() == (settings.super_admin_email or "").lower():
        raise HTTPException(status_code=403, detail="Super Admin account অপরিবর্তনীয়।")
    client.table("profiles").update({"role": payload.role}).eq("id", target_id).execute()
    updated = client.table("profiles").select("id,email,role,is_active,created_at,last_sign_in_at").eq("id", target_id).single().execute().data
    return {"user": updated, "updated": True}


@router.get("/admin/analytics")
def admin_analytics(request: Request, days: int = 30):
    require_admin(request)
    days = max(1, min(days, 180))
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = _client().table("chatbot_search_events").select("user_id,query_text,query_category,retrieved_sections,created_at").gte("created_at", since).order("created_at", desc=True).limit(5000).execute().data or []
    categories = Counter(row.get("query_category", "general_legal_information") for row in rows)
    frequent = Counter(row.get("query_text", "")[:180] for row in rows if row.get("query_text"))
    daily = Counter(str(row.get("created_at", ""))[:10] for row in rows)
    user_counts = Counter(row.get("user_id", "") for row in rows if row.get("user_id"))
    return {
        "days": days,
        "total_searches": len(rows),
        "active_users": len({row.get("user_id") for row in rows}),
        "categories": [{"category": key, "count": count} for key, count in categories.most_common()],
        "frequent_queries": [{"query": key, "count": count} for key, count in frequent.most_common(10)],
        "user_activity": [{"user_id": key, "count": count} for key, count in user_counts.most_common(10)],
        "daily_searches": [{"date": key, "count": count} for key, count in sorted(daily.items())],
    }
