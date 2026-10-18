from fastapi import APIRouter, Header, Response

from application.dto.watch_dto import ListWatchedEpisodesInput, ToggleEpisodeWatchedInput
from application.use_cases.list_watched_episodes import ListWatchedEpisodes
from application.use_cases.toggle_episode_watched import ToggleEpisodeWatched
from interface.http.schemas.watch_schemas import WatchedResponseSchema


def build_watched_router(
    list_watched_episodes: ListWatchedEpisodes, toggle_episode_watched: ToggleEpisodeWatched,
) -> APIRouter:
    router = APIRouter()

    @router.get("/viewers/me/watched", response_model=WatchedResponseSchema)
    async def get_watched(show_id: int, x_viewer_id: str = Header(...)):
        episode_ids = await list_watched_episodes.execute(
            ListWatchedEpisodesInput(viewer_id=x_viewer_id, show_id=show_id)
        )
        return WatchedResponseSchema(episode_ids=sorted(episode_ids))

    @router.put("/viewers/me/watched/{episode_id}", status_code=204)
    async def mark_watched(episode_id: int, x_viewer_id: str = Header(...)):
        await toggle_episode_watched.execute(
            ToggleEpisodeWatchedInput(viewer_id=x_viewer_id, episode_id=episode_id, watched=True)
        )
        return Response(status_code=204)

    @router.delete("/viewers/me/watched/{episode_id}", status_code=204)
    async def unmark_watched(episode_id: int, x_viewer_id: str = Header(...)):
        await toggle_episode_watched.execute(
            ToggleEpisodeWatchedInput(viewer_id=x_viewer_id, episode_id=episode_id, watched=False)
        )
        return Response(status_code=204)

    return router
