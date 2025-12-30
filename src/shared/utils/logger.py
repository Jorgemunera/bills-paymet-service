"""Structured logger for the application."""

import logging
import sys
from datetime import datetime
from typing import Any

from src.config.settings import get_settings


class Logger:
    """Structured logger with context prefixes."""

    _configured: bool = False

    def __init__(self, context: str) -> None:
        """
        Initialize logger with a context prefix.

        Args:
            context: Prefix for all log messages (e.g., 'USE_CASE:CREATE_PAYMENT')
        """
        self.context = context
        self._logger = logging.getLogger(context)
        self._configure_logging()

    @classmethod
    def _configure_logging(cls) -> None:
        """Configure logging once for the entire application."""
        if cls._configured:
            return

        settings = get_settings()
        level = logging.DEBUG if settings.debug else logging.INFO

        # Create formatter
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        # Remove existing handlers
        root_logger.handlers.clear()

        # Add stdout handler
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(level)
        stdout_handler.setFormatter(formatter)
        root_logger.addHandler(stdout_handler)

        cls._configured = True

    def _format_message(self, message: str, extra: dict[str, Any] | None = None) -> str:
        """Format message with context and extra data."""
        formatted = f"[{self.context}] {message}"

        if extra:
            extra_str = " | ".join(f"{k}={v}" for k, v in extra.items())
            formatted = f"{formatted} | {extra_str}"

        return formatted

    def debug(self, message: str, extra: dict[str, Any] | None = None) -> None:
        """Log debug message."""
        self._logger.debug(self._format_message(message, extra))

    def info(self, message: str, extra: dict[str, Any] | None = None) -> None:
        """Log info message."""
        self._logger.info(self._format_message(message, extra))

    def warning(self, message: str, extra: dict[str, Any] | None = None) -> None:
        """Log warning message."""
        self._logger.warning(self._format_message(message, extra))

    def error(self, message: str, extra: dict[str, Any] | None = None) -> None:
        """Log error message."""
        self._logger.error(self._format_message(message, extra))

    def critical(self, message: str, extra: dict[str, Any] | None = None) -> None:
        """Log critical message."""
        self._logger.critical(self._format_message(message, extra))