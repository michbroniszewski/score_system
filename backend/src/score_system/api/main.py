from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from score_system.api.routes import router
from score_system.application.services import ConflictError, NotFoundError
from score_system.domain.errors import DomainError
from score_system.domain.matches import InvalidTransitionError

app = FastAPI(title="Score System API", version="0.1.0")
app.include_router(router)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@app.middleware("http")
async def same_origin_writes(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Refuse changes sent by a page from another site (CSRF).

    The API has no login yet, so any web page open in the browser could otherwise post a
    form to http://localhost:8000 and, e.g., cancel a match. Browsers send `Origin` with
    such requests; it must name the host the request was sent to: the API itself (`Host`),
    or the Vite dev server that proxies /api (`X-Forwarded-Host`). Another site cannot set
    that header itself without a CORS preflight, which the API does not allow. Requests
    without `Origin` (curl, tests) pass.
    """
    origin = request.headers.get("origin")
    hosts = {request.headers.get("host"), request.headers.get("x-forwarded-host")}
    foreign = origin is not None and urlsplit(origin).netloc not in hosts
    if request.method not in SAFE_METHODS and foreign:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "cross-origin changes are not allowed"},
        )
    return await call_next(request)


def _error(
    code: int, detail: str | None = None
) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    """Handler answering `code` with `detail`, or with the exception message if None."""

    async def handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=code, content={"detail": detail or str(exc)})

    return handler


# Domain and use-case errors as HTTP errors. Handlers are matched along the exception's
# class hierarchy, so InvalidTransitionError (a DomainError) gets 409, not 422. Any other
# exception, a plain ValueError included, is a bug and gives 500.
app.add_exception_handler(NotFoundError, _error(status.HTTP_404_NOT_FOUND))
app.add_exception_handler(ConflictError, _error(status.HTTP_409_CONFLICT))
app.add_exception_handler(InvalidTransitionError, _error(status.HTTP_409_CONFLICT))
app.add_exception_handler(DomainError, _error(status.HTTP_422_UNPROCESSABLE_CONTENT))
# Unique constraints are checked before writing; this covers concurrent requests.
app.add_exception_handler(
    IntegrityError, _error(status.HTTP_409_CONFLICT, "conflicts with existing data")
)
