import pytest

from domain.errors import CommentTooLong, EmptyComment
from domain.value_objects.comment_body import CommentBody


def test_trims_surrounding_whitespace():
    assert CommentBody("  hello  ").value == "hello"


def test_rejects_empty_after_trim():
    with pytest.raises(EmptyComment):
        CommentBody("   ")


def test_rejects_body_over_max_length():
    with pytest.raises(CommentTooLong):
        CommentBody("x" * 1001, max_length=1000)


def test_accepts_body_at_max_length():
    assert CommentBody("x" * 1000, max_length=1000).value == "x" * 1000
