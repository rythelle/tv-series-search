from domain.entities.episode import Episode
from domain.entities.season import Season

SPECIALS_SEASON_NUMBER = 0


def group_episodes_by_season(episodes: list[Episode]) -> list[Season]:
    by_season: dict[int, list[Episode]] = {}
    for episode in episodes:
        by_season.setdefault(episode.season, []).append(episode)

    def sort_key(episode: Episode) -> tuple[int, int]:
        return (0, episode.number) if episode.number is not None else (1, 0)

    ordered_numbers = sorted(
        by_season.keys(),
        key=lambda n: (n == SPECIALS_SEASON_NUMBER, n),
    )
    return [
        Season(number=number, episodes=sorted(by_season[number], key=sort_key))
        for number in ordered_numbers
    ]
