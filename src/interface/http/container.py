import asyncpg
import httpx
from fastapi import APIRouter

from application.errors import CatalogUnavailable
from application.use_cases.generate_insight import GenerateInsight
from application.use_cases.get_cached_insight import GetCachedInsight
from application.use_cases.get_show_details import GetShowDetails
from application.use_cases.list_comments import ListComments
from application.use_cases.list_genres import ListGenres
from application.use_cases.list_popular_shows import ListPopularShows
from application.use_cases.list_watched_episodes import ListWatchedEpisodes
from application.use_cases.post_comment import PostComment
from application.use_cases.search_shows import SearchShows
from application.use_cases.toggle_episode_watched import ToggleEpisodeWatched
from config import Settings
from infrastructure.ai.insight_generator_factory import build_insight_generator
from infrastructure.messaging.outbox_worker import OutboxWorker
from infrastructure.persistence.postgres_comment_repository import PostgresCommentRepository
from infrastructure.persistence.postgres_insight_cache import PostgresInsightCache
from infrastructure.persistence.postgres_outbox_store import PostgresOutboxStore
from infrastructure.persistence.postgres_show_read_model_repository import PostgresShowReadModelRepository
from infrastructure.persistence.postgres_unit_of_work import PostgresUnitOfWork
from infrastructure.persistence.postgres_watch_repository import PostgresWatchRepository
from infrastructure.resilience.circuit_breaker import CircuitBreaker
from infrastructure.resilience.token_bucket_rate_limiter import TokenBucketRateLimiter
from infrastructure.system_clock import SystemClock
from infrastructure.tvmaze.show_catalog import TVMazeShowCatalog
from interface.http.routers.catalog import build_catalog_router
from interface.http.routers.comments import build_comments_router
from interface.http.routers.health import build_health_router, build_ready_router
from interface.http.routers.insights import build_insights_router
from interface.http.routers.watched import build_watched_router


class Container:
    def __init__(self, settings: Settings, pool: asyncpg.Pool):
        self.settings = settings
        self.pool = pool
        self.clock = SystemClock()

        self.show_repository = PostgresShowReadModelRepository(pool, settings.TRIGRAM_WORD_SIMILARITY_THRESHOLD)
        self.watch_repository = PostgresWatchRepository(pool)
        self.comment_repository = PostgresCommentRepository(pool)
        self.insight_cache = PostgresInsightCache(pool)

        tvmaze_client = httpx.AsyncClient(base_url="https://api.tvmaze.com")
        tvmaze_breaker = CircuitBreaker(
            settings.TVMAZE_BREAKER_FAILURES, settings.TVMAZE_BREAKER_COOLDOWN_SECONDS, self.clock,
        )
        self.show_catalog = TVMazeShowCatalog(tvmaze_client, settings.TVMAZE_TIMEOUT_SECONDS, tvmaze_breaker)

        ai_http_client = httpx.AsyncClient()
        self.insight_generator = build_insight_generator(
            provider=settings.AI_PROVIDER, api_key=settings.AI_API_KEY, model=settings.AI_MODEL,
            timeout_seconds=settings.AI_TIMEOUT_SECONDS, max_retries=settings.AI_MAX_RETRIES,
            breaker_failures=settings.AI_BREAKER_FAILURES,
            breaker_cooldown_seconds=settings.AI_BREAKER_COOLDOWN_SECONDS,
            max_concurrency=settings.AI_MAX_CONCURRENCY, cache=self.insight_cache,
            cache_ttl_seconds=settings.INSIGHT_CACHE_TTL_SECONDS,
            fallback_ttl_seconds=settings.INSIGHT_FALLBACK_TTL_SECONDS,
            clock=self.clock, http_client=ai_http_client,
        )

        self.search_shows = SearchShows(
            repository=self.show_repository, catalog=self.show_catalog, clock=self.clock,
        )
        self.list_popular_shows = ListPopularShows(repository=self.show_repository)
        self.list_genres = ListGenres(repository=self.show_repository)
        self.get_show_details = GetShowDetails(
            repository=self.show_repository, catalog=self.show_catalog, clock=self.clock,
            stale_after_seconds=settings.SHOW_STALE_AFTER_SECONDS,
        )
        self.list_watched_episodes = ListWatchedEpisodes(repository=self.watch_repository)
        self.toggle_episode_watched = ToggleEpisodeWatched(
            watch_repository=self.watch_repository, show_repository=self.show_repository, clock=self.clock,
        )
        self.post_comment = PostComment(
            unit_of_work_factory=lambda: PostgresUnitOfWork(pool, self.clock), clock=self.clock,
        )
        self.list_comments = ListComments(repository=self.comment_repository)
        self.generate_insight = GenerateInsight(
            show_repository=self.show_repository, comment_repository=self.comment_repository,
            insight_generator=self.insight_generator, prompt_comment_count=settings.AI_PROMPT_COMMENT_COUNT,
        )
        self.get_cached_insight = GetCachedInsight(
            show_repository=self.show_repository, comment_repository=self.comment_repository,
            cache=self.insight_cache,
        )

        self.rate_limiter = TokenBucketRateLimiter(self.clock)

        self.outbox_store = PostgresOutboxStore(pool)
        self.outbox_worker = OutboxWorker(
            store=self.outbox_store, insight_cache=self.insight_cache,
            poll_interval_seconds=settings.OUTBOX_POLL_INTERVAL_SECONDS,
            max_attempts=settings.OUTBOX_MAX_ATTEMPTS,
        )

    def build_routers(self) -> list[APIRouter]:
        return [
            build_health_router(),
            build_ready_router(self.pool),
            build_catalog_router(
                self.search_shows, self.list_popular_shows, self.list_genres,
                self.get_show_details, self.settings.SEARCH_RESULT_LIMIT,
            ),
            build_watched_router(self.list_watched_episodes, self.toggle_episode_watched),
            build_comments_router(self.post_comment, self.list_comments, self.settings.COMMENTS_PAGE_SIZE),
            build_insights_router(self.generate_insight, self.get_cached_insight),
        ]

    async def seed_popular_shows(self) -> None:
        # Fills the browsable listing, and defines it: SEED_PAGES of the TVMaze
        # index is the shelf, deliberately a slice rather than a mirror of the
        # whole catalog. Anything outside it is reached through search, which
        # queries TVMaze directly and stores what it finds.
        #
        # The index is numbered from 0: page 0 holds the first 250 shows. Running
        # past the last page answers 404, which the catalog reports as
        # CatalogUnavailable -- the same signal as a real outage, and either way
        # the right move is to keep whatever was already stored and stop.
        for page in range(self.settings.SEED_PAGES):
            try:
                shows = await self.show_catalog.list_page(page)
            except CatalogUnavailable:
                return
            now = self.clock.now()
            for show in shows:
                show.details_fetched_at = now
            await self.show_repository.upsert_shows(shows)
