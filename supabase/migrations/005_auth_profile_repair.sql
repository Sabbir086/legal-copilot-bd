-- Repair/ensure the profile table used by the backend auth middleware.
-- Safe to run on projects where migration 004 was already applied.

begin;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null unique,
  role text not null default 'user'
    check (role in ('user', 'admin', 'super_admin')),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_sign_in_at timestamptz
);

-- Fill in any columns missing from an older/incomplete profiles table.
alter table public.profiles add column if not exists email text;
alter table public.profiles add column if not exists role text not null default 'user';
alter table public.profiles add column if not exists is_active boolean not null default true;
alter table public.profiles add column if not exists created_at timestamptz not null default now();
alter table public.profiles add column if not exists updated_at timestamptz not null default now();
alter table public.profiles add column if not exists last_sign_in_at timestamptz;

create index if not exists profiles_role_created_idx
  on public.profiles(role, created_at desc);

create or replace function public.set_profile_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
before update on public.profiles
for each row execute function public.set_profile_updated_at();

create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles(id, email, role)
  values (new.id, lower(new.email), 'user')
  on conflict (id) do update set email = excluded.email;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created_profile on auth.users;
create trigger on_auth_user_created_profile
after insert on auth.users
for each row execute function public.handle_new_auth_user();

-- Backfill accounts already present in Supabase Auth without changing their roles.
insert into public.profiles(id, email, role)
select u.id, lower(u.email), 'user'
from auth.users u
where u.email is not null
on conflict (id) do update set email = excluded.email
where profiles.role <> 'super_admin';

create or replace function public.protect_super_admin_identity()
returns trigger
language plpgsql
as $$
begin
  if old.role = 'super_admin'
     and (new.role <> old.role or lower(new.email) <> lower(old.email)) then
    raise exception 'Super Admin identity and role are immutable';
  end if;
  return new;
end;
$$;

drop trigger if exists profiles_protect_super_admin on public.profiles;
create trigger profiles_protect_super_admin
before update on public.profiles
for each row execute function public.protect_super_admin_identity();

alter table public.profiles enable row level security;
drop policy if exists profiles_read_self on public.profiles;
create policy profiles_read_self on public.profiles
for select to authenticated using (id = auth.uid());

revoke all on table public.profiles from anon;
grant select on table public.profiles to authenticated;
grant all privileges on table public.profiles to service_role;

commit;
