import json
from pathlib import Path

from domain.value_objects.show_id import ShowId
from infrastructure.tvmaze.mappers import map_episode, map_show

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "tvmaze"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text())


def test_maps_a_normal_show_payload():
    show = map_show(_load("show.json"))
    assert show.id == ShowId(169)
    assert show.name == "Breaking Bad"
    assert show.premiered_year == 2008
    assert show.poster_url == "https://example.com/original.jpg"
    assert [g.value for g in show.genres] == ["Drama", "Crime", "Thriller"]
    assert show.rating == 9.4
    assert show.popularity == 98.0


def test_maps_a_show_with_a_null_poster():
    show = map_show(_load("show_null_poster.json"))
    assert show.poster_url is None
    assert show.rating is None


def test_maps_a_show_with_a_null_premiered_date():
    show = map_show(_load("show_null_premiered.json"))
    assert show.premiered_year is None


def test_keeps_html_in_the_summary_for_the_domain_layer_to_strip_later():
    show = map_show(_load("show_html_summary.json"))
    assert "<b>bold</b>" in show.summary


def test_ignores_fields_it_does_not_recognize():
    show = map_show(_load("show_unknown_field.json"))
    assert show.id == ShowId(173)
    assert show.name == "Future Field Show"


def test_maps_episodes_including_specials_and_a_missing_number():
    episodes = [map_episode(item, ShowId(169)) for item in _load("episodes.json")]
    assert [e.number for e in episodes] == [1, 2, None]
    assert episodes[2].season == 0
