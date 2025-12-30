"""Payment repository interface (port)."""

from abc import ABC, abstractmethod

from src.modules.payments.domain.payment import Payment


class PaymentRepository(ABC):
    """
    Abstract repository for Payment persistence.

    This is a PORT in hexagonal architecture terms.
    Concrete implementations (adapters) will be in the infrastructure layer.
    """

    @abstractmethod
    async def save(self, payment: Payment) -> None:
        """
        Persist a new payment.

        Args:
            payment: The payment entity to save

        Raises:
            RepositoryError: If persistence fails
        """
        pass

    @abstractmethod
    async def find_by_id(self, payment_id: str) -> Payment | None:
        """
        Find a payment by its ID.

        Args:
            payment_id: The unique payment identifier

        Returns:
            The payment if found, None otherwise
        """
        pass

    @abstractmethod
    async def update(self, payment: Payment) -> None:
        """
        Update an existing payment.

        Args:
            payment: The payment entity with updated values

        Raises:
            RepositoryError: If update fails
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def count(self, status: str | None = None) -> int:
        """
        Count payments with optional filtering.

        Args:
            status: Filter by payment status (optional)

        Returns:
            Number of payments matching the criteria
        """
        pass