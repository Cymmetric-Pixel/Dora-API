-- Canonical schema for the Dora content database (CloudSQL / Postgres).
-- Idempotent: safe to run against an empty database or an existing one.

create table if not exists public.contents (
  content_id text not null,
  type text,
  category text,
  title text,
  body text,
  url text,
  constraint contents_pkey primary key (content_id)
);

-- No FK on content_id by design: keyword rows reference a global content
-- catalog that is loaded book-by-book, so a keyword can point at a content row
-- from a book not yet inserted. Referential integrity is verified post-load by
-- query (0 orphans on a complete load) rather than enforced per-insert.
create table if not exists public.keywords (
  keyword text not null,
  content_id text not null,
  constraint keywords_pkey primary key (keyword, content_id)
);

-- keyword lookups are served by keywords_pkey's leading column; only the
-- reverse (content_id -> keywords) and category filters need their own index.
create index if not exists keywords_content_id_idx on public.keywords (content_id);
create index if not exists contents_category_idx on public.contents (category);
