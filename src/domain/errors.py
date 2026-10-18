class DomainError(Exception):
    """Base type for all domain-layer violations."""


class EmptyComment(DomainError):
    pass


class CommentTooLong(DomainError):
    def __init__(self, length: int, max_length: int):
        super().__init__(f"comment of {length} chars exceeds max of {max_length}")
        self.length = length
        self.max_length = max_length


class ShowNotFound(DomainError):
    def __init__(self, show_id: int):
        super().__init__(f"show {show_id} not found")
        self.show_id = show_id


class EpisodeNotFound(DomainError):
    def __init__(self, episode_id: int):
        super().__init__(f"episode {episode_id} not found")
        self.episode_id = episode_id
