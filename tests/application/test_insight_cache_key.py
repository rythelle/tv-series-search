from application.insight_cache_key import build_insight_cache_key


def test_same_inputs_produce_the_same_key():
    key1 = build_insight_cache_key("show", 1, ["Drama"], "summary", 2, 5)
    key2 = build_insight_cache_key("show", 1, ["Drama"], "summary", 2, 5)
    assert key1 == key2


def test_a_new_comment_changes_the_key():
    key1 = build_insight_cache_key("show", 1, ["Drama"], "summary", 2, 5)
    key2 = build_insight_cache_key("show", 1, ["Drama"], "summary", 3, 6)
    assert key1 != key2


def test_genre_order_does_not_change_the_key():
    key1 = build_insight_cache_key("show", 1, ["Drama", "Crime"], "summary", 2, 5)
    key2 = build_insight_cache_key("show", 1, ["Crime", "Drama"], "summary", 2, 5)
    assert key1 == key2


def test_a_different_series_summary_changes_the_key():
    key1 = build_insight_cache_key("episode", 1, ["Drama"], "ep summary", 2, 5, series_summary="A")
    key2 = build_insight_cache_key("episode", 1, ["Drama"], "ep summary", 2, 5, series_summary="B")
    assert key1 != key2
