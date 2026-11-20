-- Legal Copilot BD: authenticated accounts, role-based administration,
-- workspace ownership, query analytics, and searchable Penal Code corpus.
-- Run after migrations 001-003. Import penal_code_sections.csv after applying this file.

create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null unique,
  role text not null default 'user' check (role in ('user', 'admin', 'super_admin')),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_sign_in_at timestamptz
);

create index if not exists profiles_role_created_idx on public.profiles(role, created_at desc);

create or replace function public.set_profile_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end;
$$;

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at before update on public.profiles
for each row execute function public.set_profile_updated_at();

create or replace function public.handle_new_auth_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles(id, email, role)
  values (new.id, lower(new.email), 'user')
  on conflict (id) do update set email = excluded.email;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created_profile on auth.users;
create trigger on_auth_user_created_profile after insert on auth.users
for each row execute function public.handle_new_auth_user();

-- Backfill Auth accounts that existed before this profile trigger was installed.
insert into public.profiles(id, email, role)
select u.id, lower(u.email), 'user'
from auth.users u
where u.email is not null
on conflict (id) do update set email = excluded.email;

-- The super-admin identity is assigned by the backend bootstrap endpoint from
-- SUPER_ADMIN_EMAIL. Once assigned, neither its email nor role can be changed.
create or replace function public.protect_super_admin_identity()
returns trigger language plpgsql as $$
begin
  if old.role = 'super_admin' and (new.role <> old.role or lower(new.email) <> lower(old.email)) then
    raise exception 'Super Admin identity and role are immutable';
  end if;
  return new;
end;
$$;

drop trigger if exists profiles_protect_super_admin on public.profiles;
create trigger profiles_protect_super_admin before update on public.profiles
for each row execute function public.protect_super_admin_identity();

alter table public.profiles enable row level security;
drop policy if exists profiles_read_self on public.profiles;
create policy profiles_read_self on public.profiles
for select to authenticated using (id = auth.uid());
revoke all on public.profiles from anon;

-- Each browser workspace UUID is permanently bound to the account that first claims it.
create table if not exists public.workspace_owners (
  workspace_id uuid primary key,
  user_id uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now()
);
create index if not exists workspace_owners_user_idx on public.workspace_owners(user_id);
alter table public.workspace_owners enable row level security;
revoke all on public.workspace_owners from anon, authenticated;

-- Ownership for the legacy synchronous upload/chat compatibility endpoints.
create table if not exists public.legacy_document_owners (
  document_id uuid primary key,
  user_id uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now()
);
create index if not exists legacy_document_owners_user_idx on public.legacy_document_owners(user_id);
alter table public.legacy_document_owners enable row level security;
revoke all on public.legacy_document_owners from anon, authenticated;

create table if not exists public.penal_code_sections (
  id bigserial primary key,
  section_number text not null unique,
  title text not null default '',
  chapter text not null default '',
  section_text text not null,
  punishment_excerpt text not null default '',
  source_status text not null default 'text_present_in_source',
  source_page_start integer,
  source_page_end integer,
  act_name text not null default 'The Penal Code, 1860',
  act_number text not null default 'XLV of 1860',
  jurisdiction text not null default 'BD',
  source_pdf text not null,
  source_url text not null,
  source_snapshot_date date not null,
  verification_status text not null default 'needs_current_law_verification',
  search_vector tsvector generated always as (
    to_tsvector('simple', coalesce(section_number,'') || ' ' || coalesce(title,'') || ' ' || coalesce(section_text,'') || ' ' || coalesce(punishment_excerpt,''))
  ) stored,
  imported_at timestamptz not null default now()
);
create extension if not exists pg_trgm;
create index if not exists penal_code_sections_search_idx on public.penal_code_sections using gin(search_vector);
create index if not exists penal_code_sections_number_idx on public.penal_code_sections(section_number);
create index if not exists penal_code_sections_title_trgm_idx on public.penal_code_sections using gin(title gin_trgm_ops);

create or replace function public.search_penal_code_sections(search_query text, match_count integer default 10)
returns table (
  section_number text,
  title text,
  chapter text,
  section_text text,
  punishment_excerpt text,
  source_status text,
  source_page_start integer,
  source_page_end integer,
  source_pdf text,
  source_url text,
  source_snapshot_date date,
  verification_status text,
  rank real
)
language sql stable security invoker set search_path = public as $$
  with q as (
    select nullif(trim(coalesce(search_query, '')), '') as raw,
           websearch_to_tsquery('simple', coalesce(search_query, '')) as tsq
  )
  select s.section_number, s.title, s.chapter, s.section_text, s.punishment_excerpt,
         s.source_status, s.source_page_start, s.source_page_end,
         s.source_pdf, s.source_url, s.source_snapshot_date, s.verification_status,
         case when upper(s.section_number) = upper((select raw from q)) then 100.0::real
              else ts_rank_cd(s.search_vector, (select tsq from q)) end as rank
  from public.penal_code_sections s, q
  where q.raw is not null and (
    upper(s.section_number) = upper(q.raw)
    or s.search_vector @@ q.tsq
    or s.title ilike '%' || q.raw || '%'
  )
  order by (upper(s.section_number) = upper((select raw from q))) desc,
           ts_rank_cd(s.search_vector, (select tsq from q)) desc,
           s.section_number
  limit greatest(1, least(coalesce(match_count, 10), 25));
$$;

revoke all on public.penal_code_sections from anon, authenticated;
revoke all on function public.search_penal_code_sections(text, integer) from anon, authenticated;
grant execute on function public.search_penal_code_sections(text, integer) to service_role;

create table if not exists public.chatbot_search_events (
  id bigserial primary key,
  user_id uuid not null references public.profiles(id) on delete cascade,
  conversation_id uuid references public.conversations(id) on delete set null,
  query_text text not null,
  query_category text not null default 'general_legal_information',
  retrieved_sections text[] not null default '{}',
  created_at timestamptz not null default now()
);
create index if not exists chatbot_search_events_created_idx on public.chatbot_search_events(created_at desc);
create index if not exists chatbot_search_events_category_idx on public.chatbot_search_events(query_category, created_at desc);
create index if not exists chatbot_search_events_user_idx on public.chatbot_search_events(user_id, created_at desc);
alter table public.chatbot_search_events enable row level security;
revoke all on public.chatbot_search_events from anon, authenticated;

-- CSV import note: In Supabase Table Editor select penal_code_sections > Import data from CSV.
-- The CSV contains 555 section rows from the supplied 2013 PDF snapshot. It is not a current-law certification.
