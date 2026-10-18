import pytest

from domain.value_objects.viewer_id import ViewerId


def test_accepts_a_valid_uuid():
    viewer_id = ViewerId("3fae9e20-7a1a-4b7a-9f0e-6a6a7b6b5a10")
    assert viewer_id.value == "3fae9e20-7a1a-4b7a-9f0e-6a6a7b6b5a10"


def test_rejects_a_non_uuid_string():
    with pytest.raises(ValueError):
        ViewerId("not-a-uuid")


def test_canonicalizes_uppercase_to_a_stable_value():
    upper = ViewerId("3FAE9E20-7A1A-4B7A-9F0E-6A6A7B6B5A10")
    canonical = ViewerId("3fae9e20-7a1a-4b7a-9f0e-6a6a7b6b5a10")
    assert upper.value == "3fae9e20-7a1a-4b7a-9f0e-6a6a7b6b5a10"
    assert upper == canonical
