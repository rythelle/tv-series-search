-- The popular listing pages by keyset, not OFFSET. Rows arrive in the middle of
-- the ranking while a reader is browsing -- a search upserts every hit it gets
-- from the catalog, and those shows sort by their own popularity -- and under
-- OFFSET a row landing above the reader shifts every later offset by one, so
-- the next page repeats a show. The next page is instead "the rows sorting
-- after the last one handed out", which needs the ranking itself indexed. `id`
-- is part of it because popularity is the TVMaze weight, a small integer whose
-- ties are what the tiebreaker resolves.
CREATE INDEX IF NOT EXISTS shows_popularity_id_idx ON shows (popularity DESC, id);
