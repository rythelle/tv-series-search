from domain.entities.episode import Episode
from domain.entities.show import Show
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.genre import Genre
from domain.value_objects.show_id import ShowId


def map_show(payload: dict) -> Show:
    image = payload.get("image") or {}
    rating = payload.get("rating") or {}
    return Show(
        id=ShowId(payload["id"]),
        name=payload["name"],
        premiered_year=_extract_year(payload.get("premiered")),
        poster_url=image.get("original") or image.get("medium"),
        summary=payload.get("summary") or "",
        genres=[Genre(name) for name in payload.get("genres") or []],
        rating=rating.get("average"),
        popularity=float(payload.get("weight") or 0),
        details_fetched_at=None,
        episodes_fetched_at=None,
    )


def map_episode(payload: dict, show_id: ShowId) -> Episode:
    return Episode(
        id=EpisodeId(payload["id"]),
        show_id=show_id,
        season=payload.get("season", 0),
        number=payload.get("number"),
        name=payload.get("name") or "",
        airdate=payload.get("airdate"),
        runtime=payload.get("runtime"),
        summary=payload.get("summary") or "",
    )


def _extract_year(premiered: str | None) -> int | None:
    if not premiered:
        return None
    return int(premiered[:4])
