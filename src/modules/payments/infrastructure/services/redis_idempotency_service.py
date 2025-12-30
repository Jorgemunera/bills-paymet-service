"""Redis-based idempotency service implementation."""

from typing import Any

from src.modules.payments.application.ports.idempotency_service import IdempotencyService
from src.shared.infrastructure.cache.redis_client import RedisClient
from src.shared.utils.logger import Logger


class RedisIdempotencyService(IdempotencyService):
    """
    Redis-based idempotency service.

    This is an ADAPTER in hexagonal architecture terms.
    It implements the IdempotencyService PORT.

    Provides:
    - Idempotency key storage with TTL
    - Distributed locks to prevent race conditions
    """

    def __init__(self, redis_client: RedisClient) -> None:
        """
        Initialize the idempotency service.

        Args:
            redis_client: Redis client for storage
        """
        self._redis = redis_client
        self._logger = Logger("SERVICE:IDEMPOTENCY")

    async def get_existing_result(self, idempotency_key: str) -> dict[str, Any] | None:
        """
        Get existing result for an idempotency key.

        Args:
            idempotency_key: The idempotency key to check

        Returns:
            The stored result if key exists, None otherwise
        """
        self._logger.debug(
            "Checking idempotency key",
            extra={"idempotency_key": idempotency_key},
        )

        result = await self._redis.get_idempotency_key(idempotency_key)

        if result:
            self._logger.info(
                "Idempotency key found",
                extra={
                    "idempotency_key": idempotency_key,
                    "payment_id": result.get("payment_id"),
                },
            )
        else:
            self._logger.debug(
                "Idempotency key not found",
                extra={"idempotency_key": idempotency_key},
            )

        return result

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
        self._logger.debug(
            "Saving idempotency result",
            extra={
                "idempotency_key": idempotency_key,
                "payment_id": result.get("payment_id"),
            },
        )

        await self._redis.set_idempotency_key(idempotency_key, result)

        self._logger.info(
            "Idempotency result saved",
            extra={"idempotency_key": idempotency_key},
        )

    async def acquire_lock(self, idempotency_key: str, ttl_ms: int = 10000) -> bool:
        """
        Acquire a distributed lock for an idempotency key.

        This prevents race conditions when multiple requests
        arrive with the same idempotency key simultaneously.

        Args:
            idempotency_key: The idempotency key to lock
            ttl_ms: Lock time-to-live in milliseconds

        Returns:
            True if lock was acquired, False otherwise
        """
        lock_name = f"idempotency:{idempotency_key}"

        self._logger.debug(
            "Acquiring lock",
            extra={
                "idempotency_key": idempotency_key,
                "ttl_ms": ttl_ms,
            },
        )

        acquired = await self._redis.acquire_lock(lock_name, ttl_ms)

        if acquired:
            self._logger.debug(
                "Lock acquired",
                extra={"idempotency_key": idempotency_key},
            )
        else:
            self._logger.warning(
                "Failed to acquire lock",
                extra={"idempotency_key": idempotency_key},
            )

        return acquired

    async def release_lock(self, idempotency_key: str) -> None:
        """
        Release a distributed lock.

        Args:
            idempotency_key: The idempotency key to unlock
        """
        lock_name = f"idempotency:{idempotency_key}"

        self._logger.debug(
            "Releasing lock",
            extra={"idempotency_key": idempotency_key},
        )

        await self._redis.release_lock(lock_name)

        self._logger.debug(
            "Lock released",
            extra={"idempotency_key": idempotency_key},
        )