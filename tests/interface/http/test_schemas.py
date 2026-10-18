from datetime import datetime, timezone

from domain.entities.comment import Comment
from domain.entities.episode import Episode
from domain.entities.season import Season
from domain.entities.show import Show
from domain.value_objects.comment_body import CommentBody
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.genre import Genre
from domain.value_objects.show_id import ShowId
from domain.value_objects.viewer_id import ViewerId
from interface.http.schemas.comment_schemas import CommentSchema
from interface.http.schemas.show_schemas import EpisodeSchema, SeasonSchema, ShowSummarySchema

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
VIEWER = ViewerId("3fae9e20-7a1a-4b7a-9f0e-6a6a7b6b5a10")


def test_show_summary_schema_maps_value_objects_to_plain_types():
    show = Show(
        id=ShowId(1), name="Breaking Bad", premiered_year=2008, poster_url=None,
        summary="A show.", genres=[Genre("Drama")], rating=9.4, popularity=98.0,
        details_fetched_at=NOW, episodes_fetched_at=NOW,
    )

    schema = ShowSummarySchema.from_domain(show)

    assert schema.id == 1
    assert schema.genres == ["Drama"]


def test_episode_schema_maps_an_episode():
    episode = Episode(
        id=EpisodeId(10), show_id=ShowId(1), season=1, number=1, name="Pilot",
        airdate="2008-01-20", runtime=58, summary="",
    )

    schema = EpisodeSchema.from_domain(episode)

    assert schema.id == 10
    assert schema.name == "Pilot"


def test_season_schema_maps_its_episodes():
    episode = Episode(
        id=EpisodeId(10), show_id=ShowId(1), season=1, number=1, name="Pilot",
        airdate=None, runtime=None, summary="",
    )
    season = Season(number=1, episodes=[episode])

    schema = SeasonSchema.from_domain(season)

    assert schema.number == 1
    assert schema.episodes[0].id == 10


def test_comment_schema_maps_a_comment():
    comment = Comment(
        id=5, target_type="show", target_id=1, viewer_id=VIEWER,
        body=CommentBody("Great show!"), created_at=NOW,
    )

    schema = CommentSchema.from_domain(comment)

    assert schema.id == 5
    assert schema.viewer_id == VIEWER.value
    assert schema.body == "Great show!"
