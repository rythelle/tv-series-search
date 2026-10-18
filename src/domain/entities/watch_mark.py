from dataclasses import dataclass
from datetime import datetime

from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.viewer_id import ViewerId


@dataclass
class WatchMark:
    viewer_id: ViewerId
    episode_id: EpisodeId
    watched_at: datetime
