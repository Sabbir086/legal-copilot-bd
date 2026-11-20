-- M2: evidence-preserving document intelligence layered onto the M0/M1 schema.
-- Apply ONLY after 001_initial_schema.sql and 002_conversational_workspace.sql.
-- The existing public.documents table from migration 001 is extended, not replaced.

alter table public.documents
  add column if not exists workspace_id uuid,
  add column if not exists conversation_id uuid references public.conversations(id) on delete cascade,
  add column if not exists attachment_id uuid unique references public.conversation_attachments(id) on delete cascade,
  add column if not exists processing_status text not null default 'queued',
  add column if not exists document_type text,
  add column if not exists classification_confidence numeric(4,3),
  add column if not exists classification_provenance jsonb not null default '{}'::jsonb,
  add column if not exists summary text,
  add column if not exists summary_provenance jsonb not null default '{}'::jsonb,
  add column if not exists extracted_characters bigint not null default 0,
  add column if not exists page_count integer not null default 0,
  add column if not exists block_count integer not null default 0,
  add column if not exists prompt_injection_detected boolean not null default false,
  add column if not exists processing_metadata jsonb not null default '{}'::jsonb,
  add column if not exists last_error_code text,
  add column if not exists last_error_message text,
  add column if not exists updated_at timestamptz not null default now();

alter table public.documents drop constraint if exists documents_processing_status_check;
alter table public.documents add constraint documents_processing_status_check
  check (processing_status in ('queued','processing','partial','completed','failed','needs_ocr','ocr_unavailable'));

create index if not exists documents_workspace_status_idx
  on public.documents(workspace_id, processing_status, updated_at desc);
create index if not exists documents_conversation_idx
  on public.documents(conversation_id, created_at desc);

create table if not exists public.document_pages (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  workspace_id uuid not null,
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  page_number integer,
  block_index integer not null default 0,
  source_text text not null default '',
  ocr_text text not null default '',
  combined_text text not null default '',
  source_type text not null default 'source_text'
    check (source_type in ('source_text','ocr_text','mixed','model_description')),
  ocr_status text not null default 'not_needed'
    check (ocr_status in ('not_needed','queued','completed','failed','needs_ocr','ocr_unavailable')),
  ocr_engine text,
  ocr_languages text[] not null default '{}',
  ocr_confidence numeric(5,4),
  image_width integer,
  image_height integer,
  artifact_storage_path text,
  source_locator jsonb not null default '{}'::jsonb,
  provenance jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(document_id, page_number, block_index)
);
create index if not exists document_pages_document_order_idx
  on public.document_pages(document_id, page_number nulls last, block_index);
create index if not exists document_pages_workspace_idx
  on public.document_pages(workspace_id, conversation_id, document_id);

create table if not exists public.document_segments (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  workspace_id uuid not null,
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  segment_index integer not null,
  parent_segment_id uuid references public.document_segments(id) on delete cascade,
  heading text,
  clause_number text,
  content text not null,
  start_locator jsonb not null default '{}'::jsonb,
  end_locator jsonb not null default '{}'::jsonb,
  has_overlap boolean not null default false,
  overlap_from_segment_index integer,
  overlap_prefix text,
  character_count integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(document_id, segment_index)
);
create index if not exists document_segments_document_order_idx
  on public.document_segments(document_id, segment_index);
create index if not exists document_segments_workspace_idx
  on public.document_segments(workspace_id, conversation_id, document_id);

create table if not exists public.document_facts (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  workspace_id uuid not null,
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  fact_key text not null,
  field text not null,
  value text,
  evidence_locator jsonb not null default '{}'::jsonb,
  supporting_quote text,
  confidence numeric(5,4) not null check (confidence >= 0 and confidence <= 1),
  extraction_method text not null check (extraction_method in ('rule_based','ocr_rule_based','llm','manual')),
  needs_review boolean not null default true,
  uncertainty_reason text,
  provenance jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(document_id, fact_key)
);
create index if not exists document_facts_document_field_idx
  on public.document_facts(document_id, field);
create index if not exists document_facts_review_idx
  on public.document_facts(workspace_id, needs_review, document_id);

create table if not exists public.document_processing_jobs (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  attachment_id uuid not null references public.conversation_attachments(id) on delete cascade,
  workspace_id uuid not null,
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  job_type text not null default 'extract',
  status text not null default 'queued'
    check (status in ('queued','processing','partial','completed','failed','needs_ocr','ocr_unavailable')),
  attempts integer not null default 0 check (attempts >= 0),
  max_attempts integer not null default 3 check (max_attempts > 0),
  error_code text,
  error_message text,
  result_metadata jsonb not null default '{}'::jsonb,
  queued_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  locked_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(document_id, job_type)
);
create index if not exists document_jobs_queue_idx
  on public.document_processing_jobs(status, queued_at)
  where status = 'queued';
create index if not exists document_jobs_workspace_idx
  on public.document_processing_jobs(workspace_id, conversation_id, document_id);

-- Backfill M1 attachment rows into the new document model without changing
-- conversation_attachments IDs, storage paths, original bytes, or legacy endpoints.
insert into public.documents (
  id, user_id, workspace_id, conversation_id, attachment_id,
  file_name, file_path, file_type, jurisdiction, status, processing_status,
  created_at, updated_at
)
select
  gen_random_uuid(), null, a.workspace_id, a.conversation_id, a.id,
  a.filename, a.storage_path, a.mime_type, 'BD', 'uploaded', 'queued',
  a.created_at, now()
from public.conversation_attachments a
on conflict (attachment_id) do nothing;

insert into public.document_processing_jobs (
  document_id, attachment_id, workspace_id, conversation_id, job_type, status
)
select d.id, d.attachment_id, d.workspace_id, d.conversation_id, 'extract', 'queued'
from public.documents d
where d.attachment_id is not null
on conflict (document_id, job_type) do nothing;

-- Atomic claim supports multiple Render workers without duplicate job execution.
create or replace function public.heartbeat_document_processing_job(p_job_id uuid, p_workspace_id uuid)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare touched integer;
begin
  update public.document_processing_jobs
  set locked_at = now(), updated_at = now()
  where id = p_job_id and workspace_id = p_workspace_id and status = 'processing';
  get diagnostics touched = row_count;
  return touched = 1;
end;
$$;

create or replace function public.claim_next_document_processing_job()
returns setof public.document_processing_jobs
language plpgsql
security definer
set search_path = public
as $$
declare claimed_id uuid;
begin
  -- Expire abandoned locks. Jobs that exhausted attempts become visibly failed.
  update public.document_processing_jobs
  set status = 'failed', error_code = 'worker_lock_expired',
      error_message = 'Worker lock expired after the maximum attempts.',
      finished_at = now(), updated_at = now()
  where status = 'processing'
    and locked_at < now() - interval '60 minutes'
    and attempts >= max_attempts;

  update public.documents d
  set processing_status = 'failed', last_error_code = 'worker_lock_expired',
      last_error_message = 'Worker lock expired after the maximum attempts.', updated_at = now()
  from public.document_processing_jobs j
  where j.document_id = d.id and j.status = 'failed'
    and j.error_code = 'worker_lock_expired';

  update public.conversation_attachments a
  set parse_status = 'failed'
  from public.document_processing_jobs j
  where j.attachment_id = a.id and j.status = 'failed'
    and j.error_code = 'worker_lock_expired';

  select id into claimed_id
  from public.document_processing_jobs
  where attempts < max_attempts
    and (
      status = 'queued'
      or (status = 'processing' and locked_at < now() - interval '60 minutes')
    )
  order by queued_at asc
  limit 1
  for update skip locked;

  if claimed_id is null then
    return;
  end if;

  update public.documents d
  set processing_status = 'processing', last_error_code = null,
      last_error_message = null, updated_at = now()
  from public.document_processing_jobs j
  where j.id = claimed_id and d.id = j.document_id;

  return query
  update public.document_processing_jobs
  set status = 'processing',
      attempts = attempts + 1,
      started_at = now(),
      locked_at = now(),
      updated_at = now(),
      error_code = null,
      error_message = null
  where id = claimed_id
  returning *;
end;
$$;

-- M1's original bucket remains private. Page images/normalized images use this
-- bucket and workspace/conversation/document-derived object keys.
update storage.buckets
set public = false,
    file_size_limit = greatest(file_size_limit, 20971520)
where id = 'conversation-attachments';

alter table public.document_pages enable row level security;
alter table public.document_segments enable row level security;
alter table public.document_facts enable row level security;
alter table public.document_processing_jobs enable row level security;

revoke all on public.documents from anon, authenticated;
grant all on public.documents to service_role;
revoke all on public.document_pages, public.document_segments,
  public.document_facts, public.document_processing_jobs from anon, authenticated;
grant all on public.document_pages, public.document_segments,
  public.document_facts, public.document_processing_jobs to service_role;
revoke all on function public.claim_next_document_processing_job() from public, anon, authenticated;
grant execute on function public.claim_next_document_processing_job() to service_role;
revoke all on function public.heartbeat_document_processing_job(uuid, uuid) from public, anon, authenticated;
grant execute on function public.heartbeat_document_processing_job(uuid, uuid) to service_role;

-- SECURITY NOTE: workspace_id is the M1 device-scope UUID, NOT auth.uid().
-- M8 must migrate ownership to verified Supabase Auth user_id and per-user RLS.
