from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from domain.errors import CommentTooLong, DomainError, EmptyComment, EpisodeNotFound, ShowNotFound
from infrastructure.observability.request_context import get_request_id

_NOT_FOUND = (ShowNotFound, EpisodeNotFound)
_INVALID_REQUEST = (EmptyComment, CommentTooLong)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        if isinstance(exc, _NOT_FOUND):
            return _envelope(404, "not_found", str(exc))
        if isinstance(exc, _INVALID_REQUEST):
            return _envelope(400, "invalid_request", str(exc))
        return _envelope(400, "domain_error", str(exc))

    @app.exception_handler(ValueError)
    async def handle_value_error(request: Request, exc: ValueError) -> JSONResponse:
        # Value objects (ViewerId, CommentBody, ...) raise plain ValueError for malformed
        # input, e.g. a non-UUID X-Viewer-Id header — that is a 400, not a server fault.
        return _envelope(400, "invalid_request", str(exc))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # FastAPI answers its own validation failures with {"detail": [...]}.
        # Keep the status it chose, but report it in the one envelope the rest of
        # the API uses so a client needs a single error shape.
        return _envelope(422, "invalid_request", _describe(exc))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        return _envelope(500, "internal_error", "an unexpected error occurred")


def _describe(exc: RequestValidationError) -> str:
    parts = []
    for error in exc.errors():
        # loc is ("query", "offset") / ("body", "target_id") — the first entry is
        # where it came from, the rest names the field.
        field = ".".join(str(piece) for piece in error.get("loc", ())[1:]) or "request"
        parts.append(f"{field}: {error.get('msg', 'is invalid')}")
    return "; ".join(parts) or "the request is invalid"


def _envelope(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "request_id": get_request_id() or ""}},
    )
