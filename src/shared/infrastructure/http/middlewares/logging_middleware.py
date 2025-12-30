"""Request/Response logging middleware."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.shared.utils.logger import Logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.

    Logs:
    - HTTP method
    - Request path
    - Response status code
    - Request duration
    """

    def __init__(self, app) -> None:
        """Initialize middleware."""
        super().__init__(app)
        self._logger = Logger("HTTP:REQUEST")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Determine log level based on status code
        status_code = response.status_code
        log_method = self._logger.warning if status_code >= 400 else self._logger.info

        # Log request details
        log_method(
            f"{request.method} {request.url.path}",
            extra={
                "status": status_code,
                "duration": f"{duration_ms:.2f}ms",
                "method": request.method,
                "path": request.url.path,
            },
        )

        return response