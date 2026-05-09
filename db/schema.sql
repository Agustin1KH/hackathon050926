-- Supabase schema — single source of truth for all four people.
-- Run this in the Supabase SQL editor on a fresh project.
--
-- Status state machines:
--   scheduled.status: pending → approved → sent (or → failed)
--   mentions.status:  new → drafted → approved → replied (or → skipped/spam)
--   replies.status:   pending → approved → sent

create extension if not exists "pgcrypto";

create table if not exists drafts (
  id            uuid primary key default gen_random_uuid(),
  topic         text,
  content       text not null,
  variant_index int,
  created_at    timestamptz default now()
);

create table if not exists scheduled (
  id            uuid primary key default gen_random_uuid(),
  content       text not null,
  scheduled_for timestamptz not null,
  status        text not null default 'pending',
  draft_id      uuid references drafts(id) on delete set null,
  created_at    timestamptz default now()
);

create index if not exists scheduled_status_idx on scheduled(status, scheduled_for);

create table if not exists sent_log (
  id          uuid primary key default gen_random_uuid(),
  x_tweet_id  text,
  content     text not null,
  sent_at     timestamptz default now()
);

create table if not exists mentions (
  id          uuid primary key default gen_random_uuid(),
  x_id        text unique not null,
  author      text,
  text        text,
  fetched_at  timestamptz default now(),
  status      text not null default 'new'
);

create index if not exists mentions_status_idx on mentions(status, fetched_at desc);

create table if not exists replies (
  id            uuid primary key default gen_random_uuid(),
  mention_id    uuid references mentions(id) on delete cascade,
  draft_content text not null,
  status        text not null default 'pending',
  created_at    timestamptz default now()
);

create index if not exists replies_status_idx on replies(status, created_at desc);

create table if not exists config (
  key   text primary key,
  value text
);

-- Seed default config values. Edit these via the Settings page or directly.
insert into config (key, value) values
  ('style_profile', 'casual, technical, no hashtags, concise'),
  ('post_schedule', '09:00,13:00,18:00'),
  ('phone_number',  '')
on conflict (key) do nothing;
