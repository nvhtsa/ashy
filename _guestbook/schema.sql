-- ashy.lol final guestbook — paste this into the Supabase SQL editor once.
--
-- The insert policy is the real deadline: once the date passes, the database
-- refuses signatures even if somebody edits the page or calls the API by hand.
-- Keep the date in step with expiresAt in config.js.

create table if not exists public.guestbook (
  id uuid primary key default gen_random_uuid(),
  name text not null default 'anonymous',
  message text not null,
  created_at timestamptz not null default now(),
  constraint guestbook_name_length check (char_length(name) between 1 and 40),
  constraint guestbook_message_length check (char_length(message) between 2 and 280)
);

alter table public.guestbook enable row level security;

-- Read and append only. No update or delete grant, so signatures are permanent.
grant usage on schema public to anon;
grant select, insert on public.guestbook to anon;
revoke update, delete on public.guestbook from anon;

drop policy if exists "guestbook is public to read" on public.guestbook;
create policy "guestbook is public to read"
  on public.guestbook for select
  to anon
  using (true);

drop policy if exists "sign before shutdown" on public.guestbook;
create policy "sign before shutdown"
  on public.guestbook for insert
  to anon
  with check (now() < timestamptz '2027-01-16 23:59:59+00');

create index if not exists guestbook_created_at_idx
  on public.guestbook (created_at desc);

-- Without a server there is no per-IP limit, so cap the whole table instead.
create or replace function public.guestbook_throttle()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare recent integer;
begin
  select count(*) into recent
  from public.guestbook
  where created_at > now() - interval '10 seconds';

  if recent >= 5 then
    raise exception 'Too many signatures at once — try again in a few seconds.';
  end if;

  return new;
end;
$$;

drop trigger if exists guestbook_throttle on public.guestbook;
create trigger guestbook_throttle
  before insert on public.guestbook
  for each row execute function public.guestbook_throttle();
