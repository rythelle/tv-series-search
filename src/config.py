from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_PORT: int = 7777
    DATABASE_URL: str = "postgresql://app:app@db:5432/tvseries"

    SEARCH_CACHE_TTL_SECONDS: int = 60
    POPULAR_CACHE_TTL_SECONDS: int = 300
    SHOW_STALE_AFTER_SECONDS: int = 86400
    TRIGRAM_WORD_SIMILARITY_THRESHOLD: float = 0.5
    SEARCH_RESULT_LIMIT: int = 20

    TVMAZE_TIMEOUT_SECONDS: float = 1.5
    TVMAZE_BREAKER_FAILURES: int = 5
    TVMAZE_BREAKER_COOLDOWN_SECONDS: float = 30

    COMMENT_MAX_LENGTH: int = 1000
    COMMENTS_PAGE_SIZE: int = 50

    AI_PROVIDER: str = "gemini"
    AI_API_KEY: str = ""
    AI_MODEL: str = "gemini-3.1-flash-lite"
    AI_TIMEOUT_SECONDS: float = 8
    AI_MAX_RETRIES: int = 2
    AI_BREAKER_FAILURES: int = 3
    AI_BREAKER_COOLDOWN_SECONDS: float = 60
    AI_MAX_CONCURRENCY: int = 4
    AI_PROMPT_COMMENT_COUNT: int = 10
    AI_PROMPT_MAX_CHARS: int = 4000

    INSIGHT_CACHE_TTL_SECONDS: int = 86400
    INSIGHT_FALLBACK_TTL_SECONDS: int = 300

    RATE_LIMIT_PER_MINUTE: int = 120
    INSIGHT_RATE_LIMIT_PER_MINUTE: int = 10

    SEED_ON_START: bool = True
    # The TVMaze index serves 250 shows per page. This is the browsable shelf --
    # a slice of the catalog, not a mirror of it; search is what reaches the rest.
    SEED_PAGES: int = 3
    OUTBOX_POLL_INTERVAL_SECONDS: float = 2
    OUTBOX_MAX_ATTEMPTS: int = 5
