import pytest

from domain.value_objects.insight_text import InsightText


def test_accepts_non_blank_text():
    assert InsightText("A tense drama.").value == "A tense drama."


def test_rejects_blank_after_strip():
    with pytest.raises(ValueError):
        InsightText("   ")
