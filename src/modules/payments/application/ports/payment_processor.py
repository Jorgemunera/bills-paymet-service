"""Payment processor interface (port)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProcessingResult:
    """Result of payment processing."""

    success: bool
    message: str


class PaymentProcessor(ABC):
    """
    Abstract payment processor.

    This is a PORT in hexagonal architecture terms.
    The concrete implementation will simulate payment processing
    based on business rules (amount threshold, retry probability).
    """

    @abstractmethod
    async def process(self, payment_id: str, amount: Decimal) -> ProcessingResult:
        """
        Process a payment.

        Args:
            payment_id: The payment identifier
            amount: The payment amount

        Returns:
            ProcessingResult indicating success or failure
        """
        pass

    @abstractmethod
    async def process_retry(self, payment_id: str, amount: Decimal) -> ProcessingResult:
        """
        Process a payment retry.

        Retry processing may have different success probability
        than initial processing.

        Args:
            payment_id: The payment identifier
            amount: The payment amount

        Returns:
            ProcessingResult indicating success or failure
        """
        pass