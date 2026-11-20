create extension if not exists vector;
create extension if not exists pgcrypto;

create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  file_name text not null,
  file_path text not null,
  file_type text not null,
  jurisdiction text not null default 'BD',
  status text not null default 'uploaded',
  created_at timestamptz not null default now()
);

create table if not exists public.document_clauses (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  clause_number text,
  title text,
  page_number integer,
  content text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.analysis_runs (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  status text not null default 'pending',
  started_at timestamptz default now(),
  completed_at timestamptz
);

create table if not exists public.legal_sources (
  id uuid primary key default gen_random_uuid(),
  act_name text not null,
  act_year integer,
  section_number text,
  jurisdiction text not null default 'BD',
  content text not null,
  source_url text not null,
  source_type text not null default 'statute',
  legal_status text not null default 'needs_review',
  effective_date date,
  last_verified_at timestamptz,
  embedding vector(768),
  created_at timestamptz default now()
);

create table if not exists public.legal_risks (
  id uuid primary key default gen_random_uuid(),
  analysis_id uuid not null references public.analysis_runs(id) on delete cascade,
  clause_id uuid references public.document_clauses(id) on delete set null,
  risk_title text not null,
  category text,
  severity text check (severity in ('critical','high','medium','low')),
  description text,
  recommendation text,
  created_at timestamptz default now()
);

create table if not exists public.legal_citations (
  id uuid primary key default gen_random_uuid(),
  risk_id uuid not null references public.legal_risks(id) on delete cascade,
  source_id uuid references public.legal_sources(id) on delete set null,
  verification_status text not null default 'UNVERIFIED',
  quoted_text text,
  evidence text,
  checked_at timestamptz
);

create table if not exists public.memoranda (
  id uuid primary key default gen_random_uuid(),
  analysis_id uuid not null references public.analysis_runs(id) on delete cascade,
  report_content jsonb not null default '{}'::jsonb,
  pdf_path text,
  created_at timestamptz default now()
);

-- RLS is enabled now; user-scoped policies are added when authenticated
-- document persistence is wired in the next milestone.
alter table public.documents enable row level security;
alter table public.document_clauses enable row level security;
alter table public.analysis_runs enable row level security;
alter table public.legal_sources enable row level security;
alter table public.legal_risks enable row level security;
alter table public.legal_citations enable row level security;
alter table public.memoranda enable row level security;

create policy "Public can read reviewed legal sources" on public.legal_sources
for select to anon, authenticated using (legal_status = 'verified');
