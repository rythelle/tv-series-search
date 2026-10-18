from datetime import datetime, timezone

from application.use_cases.list_genres import ListGenres
from domain.entities.show import Show
from domain.value_objects.genre import Genre
from domain.value_objects.show_id import ShowId
from tests.fakes.show_fakes import FakeShowReadModelRepository

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _show(show_id, genres):
    return Show(
        id=ShowId(show_id), name=f"Show {show_id}", premiered_year=2020, poster_url=None,
        summary="", genres=[Genre(g) for g in genres], rating=None, popularity=1.0,
        details_fetched_at=NOW, episodes_fetched_at=NOW,
    )


async def test_returns_the_genres_available_in_the_read_model():
    repo = FakeShowReadModelRepository(shows=[_show(1, ["Drama"]), _show(2, ["Comedy", "Drama"])])
    use_case = ListGenres(repository=repo)

    result = await use_case.execute()

    assert [genre.value for genre in result] == ["Drama", "Comedy"]


async def test_returns_an_empty_list_when_no_show_has_genres():
    use_case = ListGenres(repository=FakeShowReadModelRepository(shows=[_show(1, [])]))

    assert await use_case.execute() == []
