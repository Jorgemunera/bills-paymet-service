"""SQLite implementation of PaymentRepository."""

from datetime import datetime
from decimal import Decimal

from src.modules.payments.domain.payment import Payment
from src.modules.payments.domain.payment_status import PaymentStatus
from src.modules.payments.domain.repository import PaymentRepository
from src.shared.infrastructure.database.sqlite import SQLiteConnection
from src.shared.utils.logger import Logger


class SQLitePaymentRepository(PaymentRepository):
    """
    SQLite implementation of the PaymentRepository interface.

    This is an ADAPTER in hexagonal architecture terms.
    It implements the PORT defined in the domain layer.
    """

    def __init__(self, connection: SQLiteConnection) -> None:
        """
        Initialize repository with database connection.

        Args:
            connection: SQLite connection manager
        """
        self._connection = connection
        self._logger = Logger("REPOSITORY:PAYMENT")

    async def save(self, payment: Payment) -> None:
        """
        Persist a new payment.

        Args:
            payment: The payment entity to save
        """
        self._logger.debug(
            "Saving payment",
            extra={"payment_id": payment.payment_id},
        )

        await self._connection.execute(
            """
            INSERT INTO payments (
                payment_id, reference, amount, currency,
                status, retries, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payment.payment_id,
                payment.reference,
                str(payment.amount),
                payment.currency,
                payment.status.value,
                payment.retries,
                payment.created_at.isoformat(),
                payment.updated_at.isoformat(),
            ),
        )

        await self._connection.commit()

        self._logger.debug(
            "Payment saved",
            extra={"payment_id": payment.payment_id},
        )

    async def find_by_id(self, payment_id: str) -> Payment | None:
        """
        Find a payment by its ID.

        Args:
            payment_id: The unique payment identifier

        Returns:
            The payment if found, None otherwise
        """
        self._logger.debug(
            "Finding payment by ID",
            extra={"payment_id": payment_id},
        )

        row = await self._connection.fetch_one(
            "SELECT * FROM payments WHERE payment_id = ?",
            (payment_id,),
        )

        if row is None:
            self._logger.debug(
                "Payment not found",
                extra={"payment_id": payment_id},
            )
            return None

        payment = self._row_to_entity(row)

        self._logger.debug(
            "Payment found",
            extra={
                "payment_id": payment.payment_id,
                "status": payment.status.value,
            },
        )

        return payment

    async def update(self, payment: Payment) -> None:
        """
        Update an existing payment.

        Args:
            payment: The payment entity with updated values
        """
        self._logger.debug(
            "Updating payment",
            extra={
                "payment_id": payment.payment_id,
                "status": payment.status.value,
            },
        )

        await self._connection.execute(
            """
            UPDATE payments
            SET reference = ?,
                amount = ?,
                currency = ?,
                status = ?,
                retries = ?,
                updated_at = ?
            WHERE payment_id = ?
            """,
            (
                payment.reference,
                str(payment.amount),
                payment.currency,
                payment.status.value,
                payment.retries,
                payment.updated_at.isoformat(),
                payment.payment_id,
            ),
        )

        await self._connection.commit()

        self._logger.debug(
            "Payment updated",
            extra={"payment_id": payment.payment_id},
        )

    async def find_all(
        self,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Payment]:
        """
        Find all payments with optional filtering.

        Args:
            status: Filter by payment status (optional)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of payments matching the criteria
        """
        self._logger.debug(
            "Finding all payments",
            extra={"status": status, "limit": limit, "offset": offset},
        )

        if status:
            query = """
                SELECT * FROM payments
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            params = (status, limit, offset)
        else:
            query = """
                SELECT * FROM payments
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            params = (limit, offset)

        rows = await self._connection.fetch_all(query, params)

        payments = [self._row_to_entity(row) for row in rows]

        self._logger.debug(
            "Payments found",
            extra={"count": len(payments)},
        )

        return payments

    async def count(self, status: str | None = None) -> int:
        """
        Count payments with optional filtering.

        Args:
            status: Filter by payment status (optional)

        Returns:
            Number of payments matching the criteria
        """
        self._logger.debug(
            "Counting payments",
            extra={"status": status},
        )

        if status:
            query = "SELECT COUNT(*) as count FROM payments WHERE status = ?"
            params = (status,)
        else:
            query = "SELECT COUNT(*) as count FROM payments"
            params = ()

        row = await self._connection.fetch_one(query, params)

        count = row["count"] if row else 0

        self._logger.debug(
            "Payments counted",
            extra={"count": count},
        )

        return count

    def _row_to_entity(self, row) -> Payment:
        """
        Convert database row to Payment entity.

        Args:
            row: Database row (dict-like)

        Returns:
            Payment entity
        """
        return Payment(
            payment_id=row["payment_id"],
            reference=row["reference"],
            amount=Decimal(row["amount"]),
            currency=row["currency"],
            status=PaymentStatus(row["status"]),
            retries=row["retries"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )