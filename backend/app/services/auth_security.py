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
            try:
                client.table("profiles").insert({
                    "id": user_id,
                    "email": email,
                    "role": "user",
                }).execute()
            except Exception:
                # Another signup process may have created the profile.
                logger.info("Profile insert skipped; checking for existing row.")

            result = (
                client.table("profiles")
                .select("id,email,role,is_active,created_at,last_sign_in_at")
                .eq("id", user_id)
                .limit(1)
                .execute()
            )
            rows = result.data or []

        if not rows:
            raise HTTPException(
                status_code=503,
                detail="User profile missing. Check Supabase profiles table."
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
            detail="User profile database service is unavailable."
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
