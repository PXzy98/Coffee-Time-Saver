from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class NotFoundError(Exception):
    def __init__(self, detail: str = "Resource not found"):
        self.detail = detail


class ForbiddenError(Exception):
    def __init__(self, detail: str = "Access forbidden"):
        self.detail = detail


class ConflictError(Exception):
    def __init__(self, detail: str = "Resource already exists"):
        self.detail = detail


class UnprocessableError(Exception):
    def __init__(self, detail: str = "Unprocessable entity"):
        self.detail = detail


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": exc.detail})

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, exc: ForbiddenError):
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": exc.detail})

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError):
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": exc.detail})

    @app.exception_handler(UnprocessableError)
    async def unprocessable_handler(request: Request, exc: UnprocessableError):
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": exc.detail})
