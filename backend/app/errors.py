"""Structured error responses and FastAPI exception handlers.

Every error leaves the API in the shape ``{"detail": "<message>", "code": "<MACHINE_CODE>"}``.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_STATUS_CODES = {
    400: "VALIDATION_ERROR",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "DUPLICATE",
    413: "FILE_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA",
    422: "VALIDATION_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


class AppError(Exception):
    """Application-level error with an HTTP status and machine-readable code."""

    def __init__(self, status_code: int, detail: str, code: str) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code
        super().__init__(detail)


def register_error_handlers(app: FastAPI) -> None:
    """Attach exception handlers to the FastAPI application."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": str(exc.detail),
                "code": _STATUS_CODES.get(exc.status_code, "INTERNAL_ERROR"),
            },
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        parts = []
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", []) if x not in ("body", "query", "form"))
            msg = str(err.get("msg", "invalid value")).removeprefix("Value error, ")
            parts.append(f"{loc}: {msg}" if loc else msg)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "; ".join(parts) or "Invalid request.", "code": "VALIDATION_ERROR"},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # Log the traceback server-side only (never request bodies / biometric data).
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred.", "code": "INTERNAL_ERROR"},
        )


# ─── Convenience constructors ─────────────────────────────────────────────────

def not_found(resource: str = "Resource") -> AppError:
    return AppError(404, f"{resource} not found.", "NOT_FOUND")


def duplicate(msg: str = "Already exists.") -> AppError:
    return AppError(409, msg, "DUPLICATE")


def validation_error(msg: str) -> AppError:
    return AppError(422, msg, "VALIDATION_ERROR")


def unauthorized(msg: str = "Not authenticated.") -> AppError:
    return AppError(401, msg, "UNAUTHORIZED")


def forbidden(msg: str = "Forbidden.") -> AppError:
    return AppError(403, msg, "FORBIDDEN")
