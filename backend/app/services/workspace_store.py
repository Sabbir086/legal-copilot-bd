from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.config.settings import settings
from app.services.supabase_client import get_supabase_client


BUCKET = "conversation-attachments"


def _client():
    return get_supabase_client()


def _rows(response) -> list[dict[str, Any]]:
    return list(response.data or [])


def create_conversation(workspace_id: UUID, title: str, language: str = "auto", owner_id: str | None = None) -> dict:
    data = {
        "workspace_id": str(workspace_id),
        "title": title[:120] or "নতুন আইনি আলোচনা",
        "jurisdiction": "BD",
        "language": language if language in {"auto", "bn", "en"} else "auto",
    }
    result = _client().table("conversations").insert(data).execute()
    rows = _rows(result)
    if not rows:
        raise RuntimeError("Supabase did not return the created conversation.")
    return rows[0]


def list_conversations(workspace_id: UUID, limit: int = 50, owner_id: str | None = None) -> list[dict]:
    result = (
        _client().table("conversations")
        .select("id,title,jurisdiction,language,created_at,updated_at")
        .eq("workspace_id", str(workspace_id))
        .is_("deleted_at", "null")
        .order("updated_at", desc=True)
        .limit(max(1, min(limit, 100)))
        .execute()
    )
    return _rows(result)


def get_conversation(workspace_id: UUID, conversation_id: UUID, owner_id: str | None = None) -> dict | None:
    result = (
        _client().table("conversations")
        .select("*")
        .eq("id", str(conversation_id))
        .eq("workspace_id", str(workspace_id))
        .is_("deleted_at", "null")
        .limit(1)
        .execute()
    )
    rows = _rows(result)
    return rows[0] if rows else None


def list_messages(conversation_id: UUID, limit: int = 60) -> list[dict]:
    result = (
        _client().table("conversation_messages")
        .select("id,conversation_id,role,content,metadata,created_at")
        .eq("conversation_id", str(conversation_id))
        .order("created_at", desc=True)
        .limit(max(1, min(limit, 100)))
        .execute()
    )
    return list(reversed(_rows(result)))


def list_attachments(conversation_id: UUID) -> list[dict]:
    result = (
        _client().table("conversation_attachments")
        .select("id,conversation_id,filename,mime_type,size_bytes,document_type,document_type_bn,page_count,extracted_characters,parse_status,created_at")
        .eq("conversation_id", str(conversation_id))
        .order("created_at", desc=False)
        .execute()
    )
    return _rows(result)


def list_attachment_context(conversation_id: UUID) -> list[dict]:
    result = (
        _client().table("conversation_attachments")
        .select("id,filename,mime_type,storage_path,extracted_pages,document_type_bn,document_type")
        .eq("conversation_id", str(conversation_id))
        .eq("parse_status", "ready")
        .order("created_at", desc=False)
        .execute()
    )
    return _rows(result)


def insert_message(conversation_id: UUID, role: str, content: str, metadata: dict | None = None) -> dict:
    result = _client().table("conversation_messages").insert({
        "conversation_id": str(conversation_id),
        "role": role,
        "content": content,
        "metadata": metadata or {},
    }).execute()
    rows = _rows(result)
    if not rows:
        raise RuntimeError("Supabase did not return the saved message.")
    return rows[0]


def update_conversation_title(workspace_id: UUID, conversation_id: UUID, title: str) -> None:
    _client().table("conversations").update({
        "title": title[:120],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", str(conversation_id)).eq("workspace_id", str(workspace_id)).execute()


def touch_conversation(workspace_id: UUID, conversation_id: UUID) -> None:
    _client().table("conversations").update({
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", str(conversation_id)).eq("workspace_id", str(workspace_id)).execute()


def upload_attachment(storage_path: str, content: bytes, mime_type: str) -> None:
    _client().storage.from_(BUCKET).upload(
        path=storage_path,
        file=content,
        file_options={"content-type": mime_type, "upsert": "false"},
    )


def insert_attachment(data: dict) -> dict:
    result = _client().table("conversation_attachments").insert(data).execute()
    rows = _rows(result)
    if not rows:
        raise RuntimeError("Supabase did not return the saved attachment.")
    return rows[0]


def remove_storage_object(storage_path: str) -> None:
    _client().storage.from_(BUCKET).remove([storage_path])


def download_attachment(storage_path: str) -> bytes:
    return _client().storage.from_(BUCKET).download(storage_path)


def delete_conversation(workspace_id: UUID, conversation_id: UUID) -> None:
    """Remove private objects first, then hard-delete the conversation and its child rows."""
    client = _client()
    attachments = client.table("conversation_attachments").select("storage_path").eq(
        "conversation_id", str(conversation_id)
    ).eq("workspace_id", str(workspace_id)).execute()
    paths = [item["storage_path"] for item in _rows(attachments) if item.get("storage_path")]
    if paths:
        # Keep database metadata when Storage deletion fails so the operation can be retried.
        client.storage.from_(BUCKET).remove(paths)
    client.table("conversations").delete().eq("id", str(conversation_id)).eq(
        "workspace_id", str(workspace_id)
    ).execute()


def delete_attachment_rows(attachment_ids: list[str]) -> None:
    if attachment_ids:
        _client().table("conversation_attachments").delete().in_("id", attachment_ids).execute()
