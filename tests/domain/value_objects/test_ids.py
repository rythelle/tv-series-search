import pytest

from domain.value_objects.episode_id import EpisodeId
from domain.value_objects.show_id import ShowId


@pytest.mark.parametrize("cls", [ShowId, EpisodeId])
def test_rejects_non_positive_ids(cls):
    with pytest.raises(ValueError):
        cls(0)


@pytest.mark.parametrize("cls", [ShowId, EpisodeId])
def test_accepts_positive_ids(cls):
    assert cls(42).value == 42
