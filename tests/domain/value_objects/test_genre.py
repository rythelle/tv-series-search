import pytest

from domain.value_objects.genre import Genre


def test_trims_surrounding_whitespace():
    assert Genre("  Drama  ").value == "Drama"


def test_rejects_blank_after_trim():
    with pytest.raises(ValueError):
        Genre("   ")


def test_keeps_the_spelling_the_catalog_sent():
    assert Genre("Science-Fiction").value == "Science-Fiction"
    assert Genre("DIY").value == "DIY"


def test_two_spellings_of_the_same_genre_are_equal():
    assert Genre("comedy") == Genre("Comedy")
    assert Genre("COMEDY") == Genre("Comedy")


def test_equal_genres_share_a_hash_so_they_collapse_in_a_set():
    assert len({Genre("Comedy"), Genre("comedy")}) == 1


def test_different_genres_are_not_equal():
    assert Genre("Comedy") != Genre("Drama")
    assert Genre("Comedy") != "Comedy"


def test_exposes_the_form_comparisons_and_sql_filters_use():
    assert Genre("Science-Fiction").normalized == "science-fiction"
