from domain.entities.episode import Episode
from domain.services.season_grouping import group_episodes_by_season
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.show_id import ShowId

SHOW = ShowId(1)


def _episode(episode_id, season, number, name="E"):
    return Episode(
        id=EpisodeId(episode_id), show_id=SHOW, season=season, number=number,
        name=name, airdate=None, runtime=None, summary="",
    )


def test_groups_episodes_by_season_number():
    episodes = [_episode(1, 1, 1), _episode(2, 1, 2), _episode(3, 2, 1)]
    seasons = group_episodes_by_season(episodes)
    assert [s.number for s in seasons] == [1, 2]
    assert [e.id for e in seasons[0].episodes] == [EpisodeId(1), EpisodeId(2)]


def test_sorts_episodes_within_a_season_by_number():
    episodes = [_episode(1, 1, 2), _episode(2, 1, 1)]
    seasons = group_episodes_by_season(episodes)
    assert [e.number for e in seasons[0].episodes] == [1, 2]


def test_specials_season_zero_sorts_after_numbered_seasons():
    episodes = [_episode(1, 0, 1, "Special"), _episode(2, 1, 1, "Pilot")]
    seasons = group_episodes_by_season(episodes)
    assert [s.number for s in seasons] == [1, 0]


def test_episodes_with_no_number_sort_after_numbered_ones():
    episodes = [_episode(1, 1, None, "Unnumbered"), _episode(2, 1, 1, "Pilot")]
    seasons = group_episodes_by_season(episodes)
    assert [e.name for e in seasons[0].episodes] == ["Pilot", "Unnumbered"]


def test_empty_input_yields_no_seasons():
    assert group_episodes_by_season([]) == []
