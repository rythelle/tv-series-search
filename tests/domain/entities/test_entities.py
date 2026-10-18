from datetime import datetime, timezone

from domain.entities.comment import Comment
from domain.entities.episode import Episode
from domain.entities.insight import Insight
from domain.entities.season import Season
from domain.entities.show import Show
from domain.entities.watch_mark import WatchMark
from domain.value_objects.comment_body import CommentBody
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.genre import Genre
from domain.value_objects.insight_text import InsightText
from domain.value_objects.show_id import ShowId
from domain.value_objects.viewer_id import ViewerId

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
VIEWER = ViewerId("3fae9e20-7a1a-4b7a-9f0e-6a6a7b6b5a10")


def test_show_holds_its_fields():
    show = Show(
        id=ShowId(1), name="Breaking Bad", premiered_year=2008, poster_url=None,
        summary="<p>A chemistry teacher...</p>", genres=[Genre("Drama")], rating=9.5,
        popularity=100.0, details_fetched_at=NOW, episodes_fetched_at=NOW,
    )
    assert show.name == "Breaking Bad"
    assert show.genres == [Genre("Drama")]


def test_episode_defaults_belong_to_a_show():
    episode = Episode(
        id=EpisodeId(10), show_id=ShowId(1), season=1, number=1, name="Pilot",
        airdate="2008-01-20", runtime=58, summary="",
    )
    assert episode.show_id == ShowId(1)


def test_season_groups_its_episodes():
    episode = Episode(
        id=EpisodeId(10), show_id=ShowId(1), season=1, number=1, name="Pilot",
        airdate=None, runtime=None, summary="",
    )
    season = Season(number=1, episodes=[episode])
    assert season.episodes == [episode]


def test_comment_carries_a_validated_body():
    comment = Comment(
        id=None, target_type="show", target_id=1, viewer_id=VIEWER,
        body=CommentBody("Great show!"), created_at=NOW,
    )
    assert comment.body.value == "Great show!"


def test_watch_mark_pairs_viewer_and_episode():
    mark = WatchMark(viewer_id=VIEWER, episode_id=EpisodeId(10), watched_at=NOW)
    assert mark.episode_id == EpisodeId(10)


def test_insight_declares_its_provenance():
    insight = Insight(text=InsightText("A tense drama."), source="fallback", model=None, generated_at=NOW)
    assert insight.source == "fallback"
