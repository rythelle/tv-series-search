from application.dto.insight_dto import InsightContext
from infrastructure.ai.prompt_builder import PromptBuilder


def _context(**overrides):
    defaults = dict(
        target_type="show", target_id=1, cache_key="k", genres=["Drama"],
        summary="A show.", recent_comments=[],
    )
    defaults.update(overrides)
    return InsightContext(**defaults)


def test_includes_genres_and_summary():
    prompt = PromptBuilder().build(_context())
    assert "Drama" in prompt
    assert "A show." in prompt


def test_strips_html_tags_from_the_summary():
    prompt = PromptBuilder().build(_context(summary="<p>A <b>great</b> show.</p>"))
    assert "<p>" not in prompt and "<b>" not in prompt
    assert "great" in prompt


def test_includes_recent_comments_when_present():
    prompt = PromptBuilder().build(_context(recent_comments=["Loved it!"]))
    assert "Loved it!" in prompt


def test_omits_the_comments_block_when_there_are_none():
    prompt = PromptBuilder().build(_context(recent_comments=[]))
    assert "Recent viewer comments" not in prompt


def test_truncates_to_max_chars():
    prompt = PromptBuilder(max_chars=50).build(_context(summary="x" * 500))
    assert len(prompt) == 50


def test_includes_series_context_for_an_episode_when_present():
    prompt = PromptBuilder().build(
        _context(target_type="episode", summary="An episode.", series_summary="The whole series.")
    )
    assert "An episode." in prompt
    assert "The whole series." in prompt


def test_strips_html_tags_from_the_series_summary():
    prompt = PromptBuilder().build(_context(series_summary="<p>A <b>series</b>.</p>"))
    assert "<p>" not in prompt and "<b>" not in prompt
    assert "series" in prompt


def test_omits_the_series_context_when_absent():
    prompt = PromptBuilder().build(_context(series_summary=None))
    assert "Series summary" not in prompt


def test_instructs_the_model_to_focus_on_the_specific_episode():
    prompt = PromptBuilder().build(
        _context(target_type="episode", summary="An episode.", series_summary="The series.")
    )
    assert "this specific episode" in prompt.lower()


def test_does_not_add_the_episode_focus_instruction_for_a_show():
    prompt = PromptBuilder().build(_context(target_type="show"))
    assert "this specific episode" not in prompt.lower()
