from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.config.settings import settings


class SupabaseNotConfigured(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Return the server-only Supabase client.

    The service-role key must never be exposed to the browser. This client is
    used only by the FastAPI backend; workspace ownership is enforced in the
    query layer until authentication/RLS policies are introduced in M8.
    """
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise SupabaseNotConfigured(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY on the backend."
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def reset_supabase_client_for_tests() -> None:
    get_supabase_client.cache_clear()
