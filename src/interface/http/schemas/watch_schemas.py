from pydantic import BaseModel


class WatchedResponseSchema(BaseModel):
    episode_ids: list[int]
