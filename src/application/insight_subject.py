from application.dto.insight_dto import GenerateInsightInput
from application.interfaces.show_read_model_repository import ShowReadModelRepository
from domain.errors import EpisodeNotFound, ShowNotFound
from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.show_id import ShowId


async def resolve_insight_subject(
    show_repository: ShowReadModelRepository, input: GenerateInsightInput
) -> tuple[list[str], str, str | None]:
    """Resolve the (genres, summary, series_summary) an insight is based on.

    For an episode, genres and the series summary come from its parent show;
    they fall back to empty/None when the parent show is not in the read model.
    """
    if input.target_type == "show":
        show = await show_repository.get_show(ShowId(input.target_id))
        if show is None:
            raise ShowNotFound(input.target_id)
        return [genre.value for genre in show.genres], show.summary, None

    episode = await show_repository.get_episode(EpisodeId(input.target_id))
    if episode is None:
        raise EpisodeNotFound(input.target_id)
    show = await show_repository.get_show(episode.show_id)
    if show is None:
        return [], episode.summary, None
    return [genre.value for genre in show.genres], episode.summary, show.summary
