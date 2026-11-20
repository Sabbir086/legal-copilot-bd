from __future__ import annotations

from functools import lru_cache

from app.config.settings import settings


class SupabaseNotConfigured(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_supabase_client():
    """Create the server-only Supabase client lazily.

    Lazy import keeps offline/unit-test imports independent from the optional SDK;
    production still requires `supabase` from backend/requirements.txt.
    """
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise SupabaseNotConfigured(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY on the backend."
        )
    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError("Supabase SDK is missing. Install backend/requirements.txt.") from exc
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def reset_supabase_client_for_tests() -> None:
    get_supabase_client.cache_clear()
