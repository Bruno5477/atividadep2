from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorPayload(BaseModel):
    error: str
    message: str
    details: dict[str, Any] | None = None


class DomainError(Exception):
    def __init__(
        self,
        error: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.error = error
        self.message = message
        self.status_code = status_code
        self.details = details


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        payload = ErrorPayload(error=exc.error, message=exc.message, details=exc.details)
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())
