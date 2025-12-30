"""Idempotency service interface (port)."""

from abc import ABC, abstractmethod
from typing import Any


class IdempotencyService(ABC):
    """
    Abstract idempotency service.

    This is a PORT in hexagonal architecture terms.
    Handles idempotency key management to prevent duplicate operations.
    """

    @abstractmethod
    async def get_existing_result(self, idempotency_key: str) -> dict[str, Any] | None:
        """
        Get existing result for an idempotency key.

        Args:
            idempotency_key: The idempotency key to check

        Returns:
            The stored result if key exists, None otherwise
        """
        pass

    @abstractmethod
    async def save_result(
        self,
        idempotency_key: str,
        result: dict[str, Any],
    ) -> None:
        """
        Save result for an idempotency key.

        Args:
            idempotency_key: The idempotency key
            result: The result to store
        """
        pass

    @abstractmethod
    async def acquire_lock(self, idempotency_key: str, ttl_ms: int = 10000) -> bool:
        """
        Acquire a distributed lock for an idempotency key.

        This prevents race conditions when multiple requests
        arrive with the same idempotency key.

        Args:
            idempotency_key: The idempotency key to lock
            ttl_ms: Lock time-to-live in milliseconds

        Returns:
            True if lock was acquired, False otherwise
        """
        pass

    @abstractmethod
    async def release_lock(self, idempotency_key: str) -> None:
        """
        Release a distributed lock.

        Args:
            idempotency_key: The idempotency key to unlock
        """
        pass