from __future__ import annotations

import json
import logging
from urllib.request import Request as URLRequest, urlopen
from urllib.error import HTTPError, URLError
from uuid import UUID

from fastapi import HTTPException, Request

from app.config.settings import settings
from app.services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def _profile_database_error_detail(exc: Exception) -> str:
    """Return a safe, actionable hint without exposing database internals."""
    code = str(getattr(exc, "code", "") or "")
    message = str(getattr(exc, "message", "") or exc).lower()

    if code in {"42P01", "PGRST205"} or ("profiles" in message and "does not exist" in message):
        return (
            "Supabase public.profiles table পাওয়া যায়নি। সঠিক Supabase project-এর SQL Editor-এ "
            "supabase/migrations/005_auth_profile_repair.sql চালান।"
        )

    if code == "42501" or "permission denied" in message or "row-level security" in message:
        return (
            "Supabase Database permission denied। Render-এর SUPABASE_SERVICE_ROLE_KEY-এ "
            "server-side sb_secret_ key অথবা legacy service_role key দিন; anon/publishable key নয়।"
        )

    if code in {"42703", "PGRST204"} or ("column" in message and "does not exist" in message):
        return (
            "Supabase public.profiles table-এর প্রয়োজনীয় column অনুপস্থিত। "
            "সঠিক project-এর SQL Editor-এ supabase/migrations/005_auth_profile_repair.sql চালান।"
        )

    return (
        "Supabase profile database access ব্যর্থ হয়েছে। Render-এর SUPABASE_URL এবং "
        "SUPABASE_SERVICE_ROLE_KEY একই Supabase project-এর কি না এবং key-টি server-side "
        "service-role/secret key কি না যাচাই করুন। বিস্তারিত Render backend logs-এ আছে।"
    )


def _get_supabase_identity(token: str) -> dict:
    """Ask Supabase Auth to validate the actual access token."""
    api_key = (
        settings.supabase_publishable_key
        or settings.supabase_service_role_key
    ).strip()

    if not settings.supabase_url or not api_key:
        raise HTTPException(
            status_code=503,
            detail="Supabase Auth configuration is incomplete."
        )

    endpoint = settings.supabase_url.rstrip("/") + "/auth/v1/user"

    request = URLRequest(
        endpoint,
        headers={
            "apikey": api_key,
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=15) as response:
            identity = json.loads(response.read().decode("utf-8"))

    except HTTPError as exc:
        if exc.code in (401, 403):
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired Supabase session. Please sign in again."
            ) from exc

        logger.error("Supabase Auth returned HTTP %s", exc.code)
        raise HTTPException(
            status_code=503,
            detail="Supabase Auth service returned an error."
        ) from exc

    except (URLError, TimeoutError, OSError) as exc:
        logger.error("Supabase Auth connection failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="Could not connect to Supabase Auth."
        ) from exc

    except (ValueError, UnicodeDecodeError) as exc:
        logger.error("Invalid Supabase Auth response.")
        raise HTTPException(
            status_code=503,
            detail="Supabase Auth returned an invalid response."
        ) from exc

    user_id = str(identity.get("id") or "")
    email = str(identity.get("email") or "").strip().lower()

    if not user_id or not email:
        raise HTTPException(
            status_code=401,
            detail="Supabase session has no valid user identity."
        )

    try:
        UUID(user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid Supabase user ID."
        ) from exc

    return {"id": user_id, "email": email}


def authenticate_access_token(token: str) -> dict:
    if not token:
        raise HTTPException(status_code=401, detail="লগইন প্রয়োজন।")

    identity = _get_supabase_identity(token)
    user_id = identity["id"]
    email = identity["email"]

    try:
        client = get_supabase_client()

        result = (
            client.table("profiles")
            .select("id,email,role,is_active,created_at,last_sign_in_at")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []

        if not rows:
            profile_insert_error = None
            try:
                client.table("profiles").insert({
                    "id": user_id,
                    "email": email,
                    "role": "user",
                }).execute()
            except Exception as exc:
                # A concurrent signup may have inserted the same profile.
                # Keep the exception so a real permission/schema failure is not hidden.
                profile_insert_error = exc
                logger.warning(
                    "Profile auto-provisioning failed; checking whether another request created it.",
                    exc_info=True,
                )

            result = (
                client.table("profiles")
                .select("id,email,role,is_active,created_at,last_sign_in_at")
                .eq("id", user_id)
                .limit(1)
                .execute()
            )
            rows = result.data or []

            if not rows and profile_insert_error:
                raise HTTPException(
                    status_code=503,
                    detail=_profile_database_error_detail(profile_insert_error),
                ) from profile_insert_error

        if not rows:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Supabase Auth account আছে, কিন্তু public.profiles-এ profile পাওয়া যায়নি। "
                    "সঠিক project-এ migration 005 প্রয়োগ করুন এবং Auth user backfill হয়েছে কি না যাচাই করুন।"
                ),
            )

        profile = rows[0]

        if not profile.get("is_active", True):
            raise HTTPException(
                status_code=403,
                detail="এই অ্যাকাউন্টটি নিষ্ক্রিয় করা হয়েছে।"
            )

        old_email = str(profile.get("email") or "").strip().lower()

        if old_email != email:
            if profile.get("role") == "super_admin":
                raise HTTPException(
                    status_code=403,
                    detail="Super Admin email পরিবর্তন করা যাবে না।"
                )

            client.table("profiles").update(
                {"email": email}
            ).eq("id", user_id).execute()

            profile["email"] = email

        return profile

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Supabase profile database lookup failed")
        raise HTTPException(
            status_code=503,
            detail=_profile_database_error_detail(exc),
        ) from exc


def get_request_user(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="লগইন প্রয়োজন।")
    return user


def require_admin(request: Request) -> dict:
    user = get_request_user(request)
    if user.get("role") not in {"admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="Admin permission প্রয়োজন।")
    return user


def require_super_admin(request: Request) -> dict:
    user = get_request_user(request)
    if user.get("role") != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="শুধু Super Admin এই কাজটি করতে পারবেন।"
        )
    return user


def bind_workspace_to_user(workspace_id: str, user_id: str) -> None:
    try:
        valid_workspace = str(UUID(workspace_id))
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid X-Workspace-ID header."
        ) from exc

    client = get_supabase_client()

    result = (
        client.table("workspace_owners")
        .select("user_id")
        .eq("workspace_id", valid_workspace)
        .limit(1)
        .execute()
    )

    rows = result.data or []

    if rows:
        if str(rows[0].get("user_id")) != str(user_id):
            raise HTTPException(
                status_code=403,
                detail="এই workspace অন্য account-এর সঙ্গে যুক্ত।"
            )
        return

    try:
        client.table("workspace_owners").insert({
            "workspace_id": valid_workspace,
            "user_id": user_id,
        }).execute()

    except Exception:
        check = (
            client.table("workspace_owners")
            .select("user_id")
            .eq("workspace_id", valid_workspace)
            .limit(1)
            .execute()
        )

        found = check.data or []

        if not found or str(found[0].get("user_id")) != str(user_id):
            raise HTTPException(
                status_code=403,
                detail="এই workspace অন্য account-এর সঙ্গে যুক্ত।"
            )
