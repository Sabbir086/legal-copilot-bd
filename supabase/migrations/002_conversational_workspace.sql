-- M1: conversational workspace, persistent chat history and private attachments.
-- The browser never talks directly to these tables or the Storage bucket.
-- FastAPI uses the server-only Supabase service-role key.

create extension if not exists pgcrypto;

create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null,
  title text not null default 'নতুন আইনি আলোচনা',
  jurisdiction text not null default 'BD',
  language text not null default 'auto' check (language in ('auto', 'bn', 'en')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz
);

create index if not exists conversations_workspace_updated_idx
  on public.conversations(workspace_id, updated_at desc)
  where deleted_at is null;

create table if not exists public.conversation_messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists conversation_messages_conversation_created_idx
  on public.conversation_messages(conversation_id, created_at asc);

create table if not exists public.conversation_attachments (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  workspace_id uuid not null,
  filename text not null,
  mime_type text not null check (mime_type in ('application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'image/png', 'image/jpeg', 'image/webp')),
  size_bytes bigint not null check (size_bytes > 0),
  storage_path text not null unique,
  document_type text not null default 'other',
  document_type_bn text not null default 'অন্যান্য নথি',
  page_count integer not null default 0,
  extracted_characters integer not null default 0,
  extracted_pages jsonb not null default '[]'::jsonb,
  parse_status text not null default 'ready' check (parse_status in ('uploaded', 'ready', 'failed')),
  created_at timestamptz not null default now()
);

create index if not exists conversation_attachments_conversation_created_idx
  on public.conversation_attachments(conversation_id, created_at asc);

create or replace function public.set_conversation_updated_at()
returns trigger
language plpgsql
as $$
begin
  update public.conversations set updated_at = now() where id = new.conversation_id;
  return new;
end;
$$;

drop trigger if exists conversation_messages_touch_parent on public.conversation_messages;
create trigger conversation_messages_touch_parent
after insert on public.conversation_messages
for each row execute function public.set_conversation_updated_at();

drop trigger if exists conversation_attachments_touch_parent on public.conversation_attachments;
create trigger conversation_attachments_touch_parent
after insert on public.conversation_attachments
for each row execute function public.set_conversation_updated_at();

-- Private bucket. No public read policy is created.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'conversation-attachments',
  'conversation-attachments',
  false,
  20971520,
  array[
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/png',
    'image/jpeg',
    'image/webp'
  ]
)
on conflict (id) do update set
  public = false,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- Deny direct browser access. Backend service-role requests bypass RLS.
alter table public.conversations enable row level security;
alter table public.conversation_messages enable row level security;
alter table public.conversation_attachments enable row level security;

revoke all on public.conversations from anon, authenticated;
revoke all on public.conversation_messages from anon, authenticated;
revoke all on public.conversation_attachments from anon, authenticated;
grant all on public.conversations to service_role;
grant all on public.conversation_messages to service_role;
grant all on public.conversation_attachments to service_role;

-- IMPORTANT SECURITY LIMITATION:
-- M1 uses a random browser workspace UUID (X-Workspace-ID), not Supabase Auth.
-- This provides device-scoped history for the prototype but is NOT user identity.
-- M8 must add Supabase Auth, bind rows to auth.uid(), create per-user RLS policies,
-- and stop relying on a browser-supplied workspace UUID before production use.
