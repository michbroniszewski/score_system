from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from score_system.api.routes import router
from score_system.application.services import ConflictError, NotFoundError
from score_system.domain.errors import DomainError
from score_system.domain.matches import InvalidTransitionError

app = FastAPI(title="Score System API", version="0.1.0")
app.include_router(router)


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
