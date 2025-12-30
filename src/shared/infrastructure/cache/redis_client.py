"""Redis async client for caching and distributed locks."""

import json
from typing import Any

import redis.asyncio as redis

from src.config.settings import get_settings
from src.shared.utils.logger import Logger


class RedisClient:
    """
    Redis async client.

    Provides methods for:
    - Key-value storage with TTL
    - Distributed locks
    - Health checks
    """

    _instance: "RedisClient | None" = None
    _client: redis.Redis | None = None

    def __init__(self) -> None:
        """Initialize Redis client."""
        self._settings = get_settings()
        self._logger = Logger("REDIS")

    @classmethod
    def get_instance(cls) -> "RedisClient":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def connect(self) -> None:
        """Establish Redis connection."""
        if self._client is not None:
            return

        self._logger.info(
            "Connecting to Redis",
            extra={
                "host": self._settings.redis_host,
                "port": self._settings.redis_port,
            },
        )

        self._client = redis.Redis(
            host=self._settings.redis_host,
            port=self._settings.redis_port,
            decode_responses=True,
        )

        # Test connection
        await self._client.ping()

        self._logger.info("Redis connected")

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            self._logger.info("Disconnecting from Redis")
            await self._client.close()
            self._client = None
            self._logger.info("Redis disconnected")

    def _ensure_connected(self) -> None:
        """Ensure client is connected."""
        if self._client is None:
            raise RuntimeError("Redis not connected. Call connect() first.")

    # ==================== Key-Value Operations ====================

    async def get(self, key: str) -> str | None:
        """
        Get value by key.

        Args:
            key: The key to retrieve

        Returns:
            Value if exists, None otherwise
        """
        self._ensure_connected()
        return await self._client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
    ) -> None:
        """
        Set key-value pair.

        Args:
            key: The key
            value: The value
            ttl_seconds: Time-to-live in seconds (optional)
        """
        self._ensure_connected()

        if ttl_seconds:
            await self._client.set(key, value, ex=ttl_seconds)
        else:
            await self._client.set(key, value)

    async def delete(self, key: str) -> None:
        """
        Delete a key.

        Args:
            key: The key to delete
        """
        self._ensure_connected()
        await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        """
        Check if key exists.

        Args:
            key: The key to check

        Returns:
            True if exists, False otherwise
        """
        self._ensure_connected()
        return await self._client.exists(key) > 0

    # ==================== JSON Operations ====================

    async def get_json(self, key: str) -> dict[str, Any] | None:
        """
        Get JSON value by key.

        Args:
            key: The key to retrieve

        Returns:
            Parsed JSON if exists, None otherwise
        """
        value = await self.get(key)
        if value:
            return json.loads(value)
        return None

    async def set_json(
        self,
        key: str,
        value: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> None:
        """
        Set JSON value.

        Args:
            key: The key
            value: The dictionary to store as JSON
            ttl_seconds: Time-to-live in seconds (optional)
        """
        await self.set(key, json.dumps(value), ttl_seconds)

    # ==================== Distributed Locks ====================

    async def acquire_lock(
        self,
        lock_name: str,
        ttl_ms: int = 10000,
    ) -> bool:
        """
        Acquire a distributed lock.

        Uses SET NX (set if not exists) for atomic lock acquisition.

        Args:
            lock_name: Name of the lock
            ttl_ms: Lock time-to-live in milliseconds

        Returns:
            True if lock acquired, False otherwise
        """
        self._ensure_connected()

        lock_key = f"lock:{lock_name}"
        result = await self._client.set(
            lock_key,
            "1",
            px=ttl_ms,
            nx=True,
        )

        acquired = result is not None

        self._logger.debug(
            f"Lock {'acquired' if acquired else 'not available'}",
            extra={"lock_name": lock_name},
        )

        return acquired

    async def release_lock(self, lock_name: str) -> None:
        """
        Release a distributed lock.

        Args:
            lock_name: Name of the lock to release
        """
        self._ensure_connected()

        lock_key = f"lock:{lock_name}"
        await self._client.delete(lock_key)

        self._logger.debug("Lock released", extra={"lock_name": lock_name})

    # ==================== Idempotency ====================

    async def get_idempotency_key(self, key: str) -> dict[str, Any] | None:
        """
        Get stored result for an idempotency key.

        Args:
            key: The idempotency key

        Returns:
            Stored result if exists, None otherwise
        """
        idempotency_key = f"idempotency:{key}"
        return await self.get_json(idempotency_key)

    async def set_idempotency_key(
        self,
        key: str,
        result: dict[str, Any],
    ) -> None:
        """
        Store result for an idempotency key.

        Args:
            key: The idempotency key
            result: The result to store
        """
        idempotency_key = f"idempotency:{key}"
        ttl = self._settings.idempotency_ttl_seconds
        await self.set_json(idempotency_key, result, ttl)

        self._logger.debug(
            "Idempotency key stored",
            extra={"key": key, "ttl_seconds": ttl},
        )

    # ==================== Health Check ====================

    async def health_check(self) -> dict:
        """
        Check Redis health.

        Returns:
            Health status dictionary
        """
        try:
            if self._client is None:
                return {"status": "unhealthy", "error": "Not connected"}

            await self._client.ping()
            return {"status": "healthy"}

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}