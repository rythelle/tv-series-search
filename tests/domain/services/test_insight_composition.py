from domain.services.insight_composition import compose_heuristic_insight


def test_mentions_the_genres():
    text = compose_heuristic_insight(genres=["Drama", "Crime"], summary="", comments=[])
    assert "Drama" in text and "Crime" in text


def test_strips_html_from_the_summary_before_extracting_keywords():
    text = compose_heuristic_insight(
        genres=["Drama"],
        summary="<p>A <b>chemistry</b> teacher turns to <i>crime</i>.</p>",
        comments=[],
    )
    assert "<p>" not in text and "<b>" not in text


def test_reflects_a_positive_comment_tone():
    text = compose_heuristic_insight(
        genres=["Drama"], summary="A show.",
        comments=["I love this show, it's amazing and great"],
    )
    assert "positive" in text.lower() or "loved" in text.lower() or "praised" in text.lower()


def test_reflects_a_negative_comment_tone():
    text = compose_heuristic_insight(
        genres=["Drama"], summary="A show.",
        comments=["This is terrible, I hate the boring awful plot"],
    )
    assert "negative" in text.lower() or "mixed" in text.lower() or "critical" in text.lower()


def test_handles_no_comments_without_error():
    text = compose_heuristic_insight(genres=["Drama"], summary="A show.", comments=[])
    assert isinstance(text, str) and len(text) > 0


def test_handles_no_genres_without_error():
    text = compose_heuristic_insight(genres=[], summary="A show about nothing.", comments=[])
    assert isinstance(text, str) and len(text) > 0


def test_neutral_comments_add_no_tone_clause():
    text = compose_heuristic_insight(
        genres=["Drama"], summary="A show.",
        comments=["just some words about plot and characters"],
    )
    assert "positive" not in text.lower() and "negative" not in text.lower()


def test_a_tie_between_positive_and_negative_resolves_to_positive():
    text = compose_heuristic_insight(
        genres=["Drama"], summary="A show.",
        comments=["I love it", "I hate it"],
    )
    assert "positive" in text.lower()


def test_uses_the_given_subject_noun():
    text = compose_heuristic_insight(
        genres=["Drama"], summary="A teacher cooks.", comments=[], subject_noun="episode",
    )
    assert "episode" in text.lower()
    assert "title" not in text.lower()


def test_uses_the_subject_noun_when_there_are_no_genres():
    text = compose_heuristic_insight(
        genres=[], summary="A teacher cooks.", comments=[], subject_noun="episode",
    )
    assert "episode" in text.lower()


def test_reflects_a_positive_tone_written_in_portuguese():
    text = compose_heuristic_insight(
        genres=["Drama"], summary="A show.",
        comments=["Amei esse episódio, incrível e emocionante"],
    )
    assert "positive" in text.lower()


def test_reflects_a_negative_tone_written_in_portuguese():
    text = compose_heuristic_insight(
        genres=["Drama"], summary="A show.",
        comments=["Que episódio terrível e chato, odiei"],
    )
    assert "negative" in text.lower()


def test_cites_recurring_themes_from_the_comments():
    text = compose_heuristic_insight(
        genres=["Drama"], summary="A show.",
        comments=["A reviravolta foi chocante", "Que reviravolta inesperada", "amei"],
    )
    assert "reviravolta" in text.lower()


def test_does_not_cite_sentiment_words_as_themes():
    text = compose_heuristic_insight(
        genres=["Drama"], summary="A show.",
        comments=["incrível", "incrível", "incrível"],
    )
    assert "incrível" not in text.lower()


def test_does_not_repeat_a_summary_keyword_as_a_comment_theme():
    text = compose_heuristic_insight(
        genres=["Drama"], summary="A story about chemistry and crime.",
        comments=["the chemistry was great", "loved the chemistry"],
    )
    assert text.lower().count("chemistry") == 1
