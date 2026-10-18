from infrastructure.observability.request_context import get_request_id, set_request_id


def test_defaults_to_none_then_reflects_whatever_was_set():
    assert get_request_id() is None
    set_request_id("abc-123")
    assert get_request_id() == "abc-123"
