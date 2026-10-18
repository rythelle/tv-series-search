from fastapi import APIRouter

from application.dto.show_dto import (
    GetShowDetailsInput,
    ListPopularShowsInput,
    PopularCursor,
    SearchShowsInput,
)
from application.use_cases.get_show_details import GetShowDetails
from application.use_cases.list_genres import ListGenres
from application.use_cases.list_popular_shows import ListPopularShows
from application.use_cases.search_shows import SearchShows
from interface.http.schemas.show_schemas import (
    GenresResponseSchema,
    PopularResponseSchema,
    SearchResponseSchema,
    SeasonSchema,
    ShowDetailsResponseSchema,
    ShowSummarySchema,
)


def build_catalog_router(
    search_shows: SearchShows,
    list_popular_shows: ListPopularShows,
    list_genres: ListGenres,
    get_show_details: GetShowDetails,
    search_result_limit: int,
) -> APIRouter:
    router = APIRouter()

    @router.get("/shows/search", response_model=SearchResponseSchema)
    async def search(q: str, limit: int = search_result_limit, genre: str | None = None):
        result = await search_shows.execute(
            SearchShowsInput(query=q, limit=limit, genre=genre or None)
        )
        return SearchResponseSchema(
            items=[ShowSummarySchema.from_domain(show) for show in result.items],
            degraded=result.degraded,
        )

    @router.get("/shows/popular", response_model=PopularResponseSchema)
    async def popular(
        limit: int = search_result_limit,
        cursor: str | None = None,
        genre: str | None = None,
    ):
        # A cursor that does not parse raises ValueError, which the error handler
        # reports as a 400 -- the client only ever echoes back what it was given.
        result = await list_popular_shows.execute(
            ListPopularShowsInput(
                limit=limit,
                cursor=PopularCursor.parse(cursor) if cursor else None,
                genre=genre or None,
            )
        )
        return PopularResponseSchema(
            items=[ShowSummarySchema.from_domain(show) for show in result.items],
            degraded=False,
            total=result.total,
            next_cursor=result.next_cursor.encode() if result.next_cursor else None,
        )

    @router.get("/shows/genres", response_model=GenresResponseSchema)
    async def genres():
        return GenresResponseSchema(items=[genre.value for genre in await list_genres.execute()])

    @router.get("/shows/{show_id}", response_model=ShowDetailsResponseSchema)
    async def details(show_id: int):
        result = await get_show_details.execute(GetShowDetailsInput(show_id=show_id))
        return ShowDetailsResponseSchema(
            show=ShowSummarySchema.from_domain(result.show),
            seasons=[SeasonSchema.from_domain(season) for season in result.seasons],
            degraded=result.degraded,
        )

    return router
