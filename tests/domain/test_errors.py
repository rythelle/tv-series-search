from domain.errors import (
    CommentTooLong,
    DomainError,
    EpisodeNotFound,
    ShowNotFound,
)


def test_show_not_found_stores_show_id():
    error = ShowNotFound(42)
    assert isinstance(error, DomainError)
    assert error.show_id == 42


def test_episode_not_found_stores_episode_id():
    error = EpisodeNotFound(7)
    assert isinstance(error, DomainError)
    assert error.episode_id == 7


def test_comment_too_long_stores_lengths():
    error = CommentTooLong(1500, 1000)
    assert isinstance(error, DomainError)
    assert error.length == 1500
    assert error.max_length == 1000
