import logging
from datetime import datetime, timezone

import httpx
import pytest

from application.errors import CatalogUnavailable
from domain.value_objects.show_id import ShowId
from infrastructure.resilience.circuit_breaker import CircuitBreaker
from infrastructure.tvmaze.show_catalog import TVMazeShowCatalog
from tests.fakes.clock import FakeClock

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)

SHOW_PAYLOAD = {
    "id": 169, "name": "Breaking Bad", "premiered": "2008-01-20",
    "image": {"original": "https://example.com/o.jpg"}, "summary": "A show.",
    "genres": ["Drama"], "rating": {"average": 9.4}, "weight": 98,
}
EPISODE_PAYLOAD = {
    "id": 1, "name": "Pilot", "season": 1, "number": 1,
    "airdate": "2008-01-20", "runtime": 58, "summary": "",
}


def _catalog(handler, breaker=None):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.tvmaze.com")
    breaker = breaker or CircuitBreaker(failure_threshold=5, cooldown_seconds=30, clock=FakeClock(NOW))
    return TVMazeShowCatalog(client=client, timeout_seconds=1.5, breaker=breaker)


async def test_search_maps_the_results():
    def handler(request):
        assert request.url.path == "/search/shows"
        return httpx.Response(200, json=[{"score": 1.0, "show": SHOW_PAYLOAD}])

    results = await _catalog(handler).search("breaking")

    assert results[0].id == ShowId(169)


async def test_get_show_maps_the_result():
    def handler(request):
        return httpx.Response(200, json=SHOW_PAYLOAD)

    show = await _catalog(handler).get_show(ShowId(169))

    assert show.name == "Breaking Bad"


async def test_get_episodes_maps_the_results():
    def handler(request):
        return httpx.Response(200, json=[EPISODE_PAYLOAD])

    episodes = await _catalog(handler).get_episodes(ShowId(169))

    assert episodes[0].name == "Pilot"


async def test_a_non_200_response_raises_catalog_unavailable():
    def handler(request):
        return httpx.Response(503)

    with pytest.raises(CatalogUnavailable):
        await _catalog(handler).get_show(ShowId(169))


async def test_a_transport_failure_raises_catalog_unavailable():
    def handler(request):
        raise httpx.ConnectTimeout("timed out")

    with pytest.raises(CatalogUnavailable):
        await _catalog(handler).get_show(ShowId(169))


async def test_an_open_breaker_raises_catalog_unavailable_without_a_request():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503)

    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=30, clock=FakeClock(NOW))
    catalog = _catalog(handler, breaker=breaker)

    with pytest.raises(CatalogUnavailable):
        await catalog.get_show(ShowId(169))
    calls_before = len(calls)

    with pytest.raises(CatalogUnavailable):
        await catalog.get_show(ShowId(169))

    assert len(calls) == calls_before


async def test_list_page_maps_the_index_results():
    def handler(request):
        assert request.url.path == "/shows"
        assert request.url.params["page"] == "3"
        return httpx.Response(200, json=[SHOW_PAYLOAD])

    results = await _catalog(handler).list_page(3)

    assert [show.id for show in results] == [ShowId(169)]


async def test_list_page_past_the_end_raises_catalog_unavailable():
    def handler(request):
        return httpx.Response(404)

    with pytest.raises(CatalogUnavailable):
        await _catalog(handler).list_page(9999)


async def test_a_failure_is_logged_as_a_warning(caplog):
    # The callers turn CatalogUnavailable into a degraded answer, which is
    # invisible from the server side: the request still answers 200, and httpx
    # logs nothing when the response never arrives.
    def handler(request):
        raise httpx.ConnectTimeout("timed out")

    with caplog.at_level(logging.WARNING), pytest.raises(CatalogUnavailable):
        await _catalog(handler).search("breaking")

    assert [record.levelname for record in caplog.records] == ["WARNING"]
    assert "/search/shows" in caplog.text


async def test_an_open_breaker_is_logged_as_a_warning(caplog):
    def handler(request):
        return httpx.Response(503)

    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=30, clock=FakeClock(NOW))
    catalog = _catalog(handler, breaker=breaker)

    with caplog.at_level(logging.WARNING), pytest.raises(CatalogUnavailable):
        await catalog.get_show(ShowId(169))
    caplog.clear()
    with caplog.at_level(logging.WARNING), pytest.raises(CatalogUnavailable):
        await catalog.get_show(ShowId(169))

    assert "circuit breaker is open" in caplog.text
