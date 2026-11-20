-- Repair the M1 conversational workspace schema and service-role access.
-- Safe to re-run. Does not delete conversations, messages, attachments, or users.
-- Run after 005_auth_profile_repair.sql (it creates public.profiles).
-- It also repairs the conversation objects normally created by migration 002.

begin;

create extension if not exists pgcrypto;

-- Ensure the core conversation table exists with the exact columns used by the API.
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

alter table public.conversations add column if not exists id uuid default gen_random_uuid();
alter table public.conversations add column if not exists workspace_id uuid;
alter table public.conversations add column if not exists title text not null default 'নতুন আইনি আলোচনা';
alter table public.conversations add column if not exists jurisdiction text not null default 'BD';
alter table public.conversations add column if not exists language text not null default 'auto';
alter table public.conversations add column if not exists created_at timestamptz not null default now();
alter table public.conversations add column if not exists updated_at timestamptz not null default now();
alter table public.conversations add column if not exists deleted_at timestamptz;

update public.conversations set id = gen_random_uuid() where id is null;
update public.conversations set workspace_id = gen_random_uuid() where workspace_id is null;
update public.conversations set title = 'নতুন আইনি আলোচনা' where title is null or btrim(title) = '';
update public.conversations set jurisdiction = 'BD' where jurisdiction is null;
update public.conversations set language = 'auto' where language is null or language not in ('auto', 'bn', 'en');
update public.conversations set created_at = now() where created_at is null;
update public.conversations set updated_at = coalesce(created_at, now()) where updated_at is null;

alter table public.conversations alter column id set default gen_random_uuid();
alter table public.conversations alter column id set not null;
alter table public.conversations alter column workspace_id set not null;
alter table public.conversations alter column title set default 'নতুন আইনি আলোচনা';
alter table public.conversations alter column title set not null;
alter table public.conversations alter column jurisdiction set default 'BD';
alter table public.conversations alter column jurisdiction set not null;
alter table public.conversations alter column language set default 'auto';
alter table public.conversations alter column language set not null;
alter table public.conversations alter column created_at set default now();
alter table public.conversations alter column created_at set not null;
alter table public.conversations alter column updated_at set default now();
alter table public.conversations alter column updated_at set not null;

create index if not exists conversations_workspace_updated_idx
  on public.conversations(workspace_id, updated_at desc)
  where deleted_at is null;

-- Workspace binding is checked by the authentication middleware before every chat request.
-- Migration 005 must be applied first because this table references public.profiles.
create table if not exists public.workspace_owners (
  workspace_id uuid primary key,
  user_id uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now()
);
create index if not exists workspace_owners_user_idx on public.workspace_owners(user_id);
alter table public.workspace_owners enable row level security;
revoke all on public.workspace_owners from anon, authenticated;
grant all privileges on public.workspace_owners to service_role;

-- Persistent messages used by the chat API.
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

-- Attachment metadata used by M1/M2. Files remain in the private Storage bucket.
create table if not exists public.conversation_attachments (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  workspace_id uuid not null,
  filename text not null,
  mime_type text not null check (mime_type in (
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/png', 'image/jpeg', 'image/webp'
  )),
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

-- Preserve the private bucket configuration required by attachment uploads.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'conversation-attachments',
  'conversation-attachments',
  false,
  20971520,
  array[
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/png', 'image/jpeg', 'image/webp'
  ]
)
on conflict (id) do update set
  public = false,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- The browser must not access these tables directly. Render uses the server-only key.
alter table public.conversations enable row level security;
alter table public.conversation_messages enable row level security;
alter table public.conversation_attachments enable row level security;

revoke all on public.conversations from anon, authenticated;
revoke all on public.conversation_messages from anon, authenticated;
revoke all on public.conversation_attachments from anon, authenticated;
grant usage on schema public to service_role;
grant all privileges on public.conversations to service_role;
grant all privileges on public.conversation_messages to service_role;
grant all privileges on public.conversation_attachments to service_role;

commit;

-- Refresh the PostgREST schema cache after migration completion.
notify pgrst, 'reload schema';
