CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE TABLE IF NOT EXISTS shows (
    id BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    premiered_year INTEGER,
    poster_url TEXT,
    summary TEXT NOT NULL DEFAULT '',
    genres TEXT[] NOT NULL DEFAULT '{}',
    rating DOUBLE PRECISION,
    popularity DOUBLE PRECISION NOT NULL DEFAULT 0,
    details_fetched_at TIMESTAMPTZ,
    episodes_fetched_at TIMESTAMPTZ,
    search_vector tsvector NOT NULL
);
CREATE FUNCTION shows_update_search_vector() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := to_tsvector(
        'simple', unaccent(NEW.name || ' ' || array_to_string(NEW.genres, ' '))
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER shows_search_vector_trigger
BEFORE INSERT OR UPDATE OF name, genres ON shows
FOR EACH ROW EXECUTE FUNCTION shows_update_search_vector();
CREATE INDEX IF NOT EXISTS shows_search_vector_idx ON shows USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS shows_name_trgm_idx ON shows USING GIN (name gin_trgm_ops);

CREATE TABLE IF NOT EXISTS episodes (
    id BIGINT PRIMARY KEY,
    show_id BIGINT NOT NULL REFERENCES shows(id) ON DELETE CASCADE,
    season INTEGER NOT NULL,
    number INTEGER,
    name TEXT NOT NULL DEFAULT '',
    airdate TEXT,
    runtime INTEGER,
    summary TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS episodes_show_season_number_idx ON episodes (show_id, season, number);

CREATE TABLE IF NOT EXISTS watch_marks (
    viewer_id UUID NOT NULL,
    episode_id BIGINT NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    watched_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (viewer_id, episode_id)
);

CREATE TABLE IF NOT EXISTS comments (
    id BIGSERIAL PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_id BIGINT NOT NULL,
    viewer_id UUID NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS comments_target_created_idx ON comments (target_type, target_id, created_at DESC);

CREATE TABLE IF NOT EXISTS insight_cache (
    cache_key TEXT PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_id BIGINT NOT NULL,
    text TEXT NOT NULL,
    source TEXT NOT NULL,
    model TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS insight_cache_target_idx ON insight_cache (target_type, target_id);

CREATE TABLE IF NOT EXISTS outbox (
    id BIGSERIAL PRIMARY KEY,
    type TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    processed_at TIMESTAMPTZ,
    attempts INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS outbox_unprocessed_idx ON outbox (processed_at) WHERE processed_at IS NULL;
