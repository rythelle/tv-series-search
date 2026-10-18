-- Genre filters compare case-insensitively, and lower(genre) at query time
-- could not use an index. So the comparable form is stored beside the display
-- spelling (which stays exactly as the catalog sent it: "Science-Fiction",
-- "DIY") and the GIN index covers that column.
CREATE FUNCTION lower_genres(genres TEXT[]) RETURNS TEXT[] AS $$
    SELECT coalesce(array_agg(lower(genre)), '{}')
    FROM unnest(genres) AS genre
$$ LANGUAGE sql IMMUTABLE;

ALTER TABLE shows
    ADD COLUMN genres_normalized TEXT[] GENERATED ALWAYS AS (lower_genres(genres)) STORED;

CREATE INDEX IF NOT EXISTS shows_genres_normalized_idx ON shows USING GIN (genres_normalized);
