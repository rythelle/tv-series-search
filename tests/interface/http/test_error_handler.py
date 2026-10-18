import httpx
from fastapi import FastAPI, Query

from domain.errors import CommentTooLong, EmptyComment, EpisodeNotFound, ShowNotFound
from interface.http.middleware.error_handler import register_error_handlers
from interface.http.middleware.request_id import RequestIdMiddleware


def _app():
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app)

    @app.get("/show-not-found")
    async def show_not_found():
        raise ShowNotFound(1)

    @app.get("/episode-not-found")
    async def episode_not_found():
        raise EpisodeNotFound(1)

    @app.get("/empty-comment")
    async def empty_comment():
        raise EmptyComment("blank")

    @app.get("/comment-too-long")
    async def comment_too_long():
        raise CommentTooLong(1001, 1000)

    @app.get("/boom")
    async def boom():
        raise RuntimeError("unexpected")

    @app.get("/validated")
    async def validated(offset: int = Query(default=0, ge=0)):
        return {"offset": offset}

    @app.get("/bad-value")
    async def bad_value():
        from domain.value_objects.viewer_id import ViewerId

        ViewerId("not-a-uuid")

    return app


async def _get(path: str) -> httpx.Response:
    # raise_app_exceptions=False: Starlette's ServerErrorMiddleware sends the 500
    # envelope and then re-raises so the ASGI server can log it. A real network
    # client only sees the response; this flag makes the in-process transport
    # behave the same instead of propagating the re-raised exception.
    transport = httpx.ASGITransport(app=_app(), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


async def test_show_not_found_maps_to_404():
    response = await _get("/show-not-found")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_episode_not_found_maps_to_404():
    assert (await _get("/episode-not-found")).status_code == 404


async def test_empty_comment_maps_to_400():
    response = await _get("/empty-comment")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


async def test_comment_too_long_maps_to_400():
    assert (await _get("/comment-too-long")).status_code == 400


async def test_unexpected_error_maps_to_500_with_a_request_id():
    response = await _get("/boom")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["request_id"]


async def test_a_malformed_value_object_input_maps_to_400():
    response = await _get("/bad-value")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


async def test_a_rejected_query_parameter_uses_the_same_error_envelope():
    # Every other error answers {"error": {code, message, request_id}}; FastAPI's
    # own validation response is {"detail": [...]}, so a client would need a
    # second shape just for these.
    response = await _get("/validated?offset=-1")

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_request"
    assert "offset" in body["error"]["message"]
    assert body["error"]["request_id"]


async def test_a_valid_query_parameter_still_passes_through():
    response = await _get("/validated?offset=3")

    assert response.status_code == 200
    assert response.json() == {"offset": 3}
