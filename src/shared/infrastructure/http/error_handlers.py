"""Global error handlers for FastAPI application."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.modules.payments.domain.errors import PaymentError
from src.shared.utils.logger import Logger

logger = Logger("ERROR_HANDLER")


def _make_serializable(obj):
    """Convert objects to JSON-serializable types."""
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(_make_serializable(item) for item in obj)
    elif hasattr(obj, '__str__') and not isinstance(obj, (str, int, float, bool, type(None))):
        return str(obj)
    return obj


def setup_error_handlers(app: FastAPI) -> None:
    """
    Setup global error handlers for the FastAPI application.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(PaymentError)
    async def payment_error_handler(
        request: Request,
        exc: PaymentError,
    ) -> JSONResponse:
        """Handle domain payment errors."""
        logger.warning(
            "Payment error",
            extra={
                "code": exc.code,
                "message": exc.message,
                "path": request.url.path,
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Handle Pydantic validation errors."""
        errors = exc.errors()

        # Extract first error for simplified message
        first_error = errors[0] if errors else {}
        field = ".".join(str(loc) for loc in first_error.get("loc", ["unknown"]))
        message = first_error.get("msg", "Validation error")

        logger.warning(
            "Validation error",
            extra={
                "field": field,
                "message": message,
                "path": request.url.path,
            },
        )

        # Convert errors to serializable format
        serializable_errors = _make_serializable(errors)

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": f"{field}: {message}",
                    "details": {"errors": serializable_errors},
                },
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unexpected errors."""
        logger.error(
            "Unexpected error",
            extra={
                "error": str(exc),
                "path": request.url.path,
            },
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                },
            },
        )