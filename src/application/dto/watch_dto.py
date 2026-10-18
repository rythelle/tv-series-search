from dataclasses import dataclass


@dataclass
class ToggleEpisodeWatchedInput:
    viewer_id: str
    episode_id: int
    watched: bool


@dataclass
class ListWatchedEpisodesInput:
    viewer_id: str
    show_id: int
