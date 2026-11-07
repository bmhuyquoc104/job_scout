import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from job_scout.core.errors import ERROR_CATALOG, AppError, ErrorCode

logger = logging.getLogger(__name__)


def error_response(code: ErrorCode, status_code: int | None = None) -> JSONResponse:
    definition = ERROR_CATALOG[code]
    return JSONResponse(
        status_code=status_code or definition.status_code,
        content={"error": {"code": code.value, "message": definition.message}},
    )


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.code)


async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code == 404:
        return error_response(ErrorCode.NOT_FOUND)
    return error_response(ErrorCode.HTTP_ERROR, status_code=exc.status_code)


async def validation_error_handler(_: Request, __: RequestValidationError) -> JSONResponse:
    return error_response(ErrorCode.VALIDATION_ERROR)


async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled request exception",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return error_response(ErrorCode.INTERNAL_ERROR)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
