"""SQLite async connection manager."""

import aiosqlite
from pathlib import Path

from src.config.settings import get_settings
from src.shared.utils.logger import Logger


class SQLiteConnection:
    """
    SQLite async connection manager.

    Manages database connections and provides methods for
    executing queries and managing transactions.
    """

    _instance: "SQLiteConnection | None" = None
    _connection: aiosqlite.Connection | None = None

    def __init__(self) -> None:
        """Initialize SQLite connection manager."""
        self._settings = get_settings()
        self._logger = Logger("SQLITE")
        self._db_path = self._settings.database_path

    @classmethod
    def get_instance(cls) -> "SQLiteConnection":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def connect(self) -> None:
        """
        Establish database connection and initialize schema.

        Creates the database file and tables if they don't exist.
        """
        if self._connection is not None:
            return

        self._logger.info("Connecting to SQLite", extra={"path": self._db_path})

        # Ensure directory exists
        db_dir = Path(self._db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        # Connect to database
        self._connection = await aiosqlite.connect(self._db_path)
        self._connection.row_factory = aiosqlite.Row

        # Enable foreign keys
        await self._connection.execute("PRAGMA foreign_keys = ON")

        # Initialize schema
        await self._initialize_schema()

        self._logger.info("SQLite connected and schema initialized")

    async def _initialize_schema(self) -> None:
        """Create database tables if they don't exist."""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                payment_id TEXT PRIMARY KEY,
                reference TEXT NOT NULL,
                amount TEXT NOT NULL,
                currency TEXT NOT NULL CHECK(length(currency) = 3),
                status TEXT NOT NULL DEFAULT 'PENDING'
                    CHECK(status IN ('PENDING', 'SUCCESS', 'FAILED', 'EXHAUSTED')),
                retries INTEGER NOT NULL DEFAULT 0 
                    CHECK(retries >= 0 AND retries <= 3),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_payments_status 
            ON payments(status)
        """)

        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_payments_reference 
            ON payments(reference)
        """)

        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_payments_created_at 
            ON payments(created_at)
        """)

        await self._connection.commit()

    async def disconnect(self) -> None:
        """Close database connection."""
        if self._connection is not None:
            self._logger.info("Disconnecting from SQLite")
            await self._connection.close()
            self._connection = None
            self._logger.info("SQLite disconnected")

    async def execute(
        self,
        query: str,
        parameters: tuple = (),
    ) -> aiosqlite.Cursor:
        """
        Execute a query.

        Args:
            query: SQL query string
            parameters: Query parameters

        Returns:
            Cursor with results
        """
        if self._connection is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        return await self._connection.execute(query, parameters)

    async def execute_many(
        self,
        query: str,
        parameters_list: list[tuple],
    ) -> None:
        """
        Execute a query multiple times with different parameters.

        Args:
            query: SQL query string
            parameters_list: List of parameter tuples
        """
        if self._connection is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        await self._connection.executemany(query, parameters_list)

    async def fetch_one(
        self,
        query: str,
        parameters: tuple = (),
    ) -> aiosqlite.Row | None:
        """
        Execute query and fetch one row.

        Args:
            query: SQL query string
            parameters: Query parameters

        Returns:
            Single row or None
        """
        cursor = await self.execute(query, parameters)
        return await cursor.fetchone()

    async def fetch_all(
        self,
        query: str,
        parameters: tuple = (),
    ) -> list[aiosqlite.Row]:
        """
        Execute query and fetch all rows.

        Args:
            query: SQL query string
            parameters: Query parameters

        Returns:
            List of rows
        """
        cursor = await self.execute(query, parameters)
        return await cursor.fetchall()

    async def commit(self) -> None:
        """Commit current transaction."""
        if self._connection is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        await self._connection.commit()

    async def rollback(self) -> None:
        """Rollback current transaction."""
        if self._connection is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        await self._connection.rollback()

    async def health_check(self) -> dict:
        """
        Check database health.

        Returns:
            Health status dictionary
        """
        try:
            if self._connection is None:
                return {"status": "unhealthy", "error": "Not connected"}

            await self._connection.execute("SELECT 1")
            return {"status": "healthy"}

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}