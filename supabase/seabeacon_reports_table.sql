create table public.seabeacon_reports (
    id text primary key,
    ai_type text not null,
    country text not null,
    province text not null,
    score numeric not null check (score >= 0 and score <= 1),
    submitted_at timestamp with time zone not null,
    display_time text not null,
    high_lang boolean not null,
    ctx jsonb not null default '{}'::jsonb,
    simulated boolean not null default false,
    debug boolean not null default false
);

alter table public.seabeacon_reports enable row level security;

create policy "Allow all operations for anon role" on public.seabeacon_reports
    to anon
    using (true)
    with check (true);

create index idx_seabeacon_reports_submitted_at on public.seabeacon_reports(submitted_at);