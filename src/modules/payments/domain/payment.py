"""Payment entity - the core domain object."""

from datetime import datetime
from decimal import Decimal
from typing import Self
from uuid import uuid4

from src.modules.payments.domain.payment_status import PaymentStatus
from src.modules.payments.domain.errors import (
    PaymentValidationError,
    CannotRetryPaymentError,
    MaxRetriesExceededError,
)


class Payment:
    """
    Payment entity representing a payment transaction.

    This is a rich domain entity with behavior, not just a data container.
    All business rules related to payments are encapsulated here.
    """

    MAX_RETRIES = 3

    def __init__(
        self,
        payment_id: str,
        reference: str,
        amount: Decimal,
        currency: str,
        status: PaymentStatus,
        retries: int,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        """
        Initialize a Payment instance.

        Use the create() factory method for new payments.
        This constructor is for reconstituting from persistence.
        """
        self._payment_id = payment_id
        self._reference = reference
        self._amount = amount
        self._currency = currency
        self._status = status
        self._retries = retries
        self._created_at = created_at
        self._updated_at = updated_at

    @classmethod
    def create(
        cls,
        reference: str,
        amount: Decimal,
        currency: str,
    ) -> Self:
        """
        Factory method to create a new Payment.

        Args:
            reference: External reference for the bill/contract
            amount: Payment amount (must be > 0)
            currency: Currency code (must be exactly 3 characters)

        Returns:
            A new Payment instance in PENDING status

        Raises:
            PaymentValidationError: If validation fails
        """
        # Validate reference
        if not reference or not reference.strip():
            raise PaymentValidationError(
                message="Reference cannot be empty",
                field="reference",
            )

        # Validate amount
        if amount <= Decimal("0"):
            raise PaymentValidationError(
                message="Amount must be greater than zero",
                field="amount",
            )

        # Validate currency
        if len(currency) != 3:
            raise PaymentValidationError(
                message="Currency must be exactly 3 characters",
                field="currency",
            )

        now = datetime.utcnow()

        return cls(
            payment_id=str(uuid4()),
            reference=reference.strip(),
            amount=amount,
            currency=currency.upper(),
            status=PaymentStatus.PENDING,
            retries=0,
            created_at=now,
            updated_at=now,
        )

    # ==================== Properties ====================

    @property
    def payment_id(self) -> str:
        """Get payment ID."""
        return self._payment_id

    @property
    def reference(self) -> str:
        """Get payment reference."""
        return self._reference

    @property
    def amount(self) -> Decimal:
        """Get payment amount."""
        return self._amount

    @property
    def currency(self) -> str:
        """Get payment currency."""
        return self._currency

    @property
    def status(self) -> PaymentStatus:
        """Get payment status."""
        return self._status

    @property
    def retries(self) -> int:
        """Get number of retry attempts."""
        return self._retries

    @property
    def created_at(self) -> datetime:
        """Get creation timestamp."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """Get last update timestamp."""
        return self._updated_at

    # ==================== Behavior ====================

    def can_retry(self) -> bool:
        """
        Check if this payment can be retried.

        Returns:
            True if payment is FAILED and has retries remaining
        """
        return (
            self._status.can_retry() and
            self._retries < self.MAX_RETRIES
        )

    def mark_as_success(self) -> None:
        """Mark payment as successfully processed."""
        self._status = PaymentStatus.SUCCESS
        self._updated_at = datetime.utcnow()

    def mark_as_failed(self) -> None:
        """Mark payment as failed."""
        self._status = PaymentStatus.FAILED
        self._updated_at = datetime.utcnow()

    def mark_as_exhausted(self) -> None:
        """Mark payment as exhausted (no more retries allowed)."""
        self._status = PaymentStatus.EXHAUSTED
        self._updated_at = datetime.utcnow()

    def increment_retries(self) -> None:
        """
        Increment the retry counter.

        Raises:
            CannotRetryPaymentError: If payment is not in FAILED status
            MaxRetriesExceededError: If max retries already reached
        """
        if not self._status.can_retry():
            raise CannotRetryPaymentError(
                payment_id=self._payment_id,
                current_status=self._status.value,
            )

        if self._retries >= self.MAX_RETRIES:
            raise MaxRetriesExceededError(
                payment_id=self._payment_id,
                max_retries=self.MAX_RETRIES,
            )

        self._retries += 1
        self._updated_at = datetime.utcnow()

    def process_retry_result(self, success: bool) -> None:
        """
        Process the result of a retry attempt.

        Args:
            success: Whether the retry was successful

        This method handles the state transition after a retry:
        - If success: transition to SUCCESS
        - If failed and retries < max: stay in FAILED
        - If failed and retries = max: transition to EXHAUSTED
        """
        if success:
            self.mark_as_success()
        elif self._retries >= self.MAX_RETRIES:
            self.mark_as_exhausted()
        else:
            self.mark_as_failed()

    # ==================== Serialization ====================

    def to_dict(self) -> dict:
        """Convert payment to dictionary representation."""
        return {
            "payment_id": self._payment_id,
            "reference": self._reference,
            "amount": float(self._amount),
            "currency": self._currency,
            "status": self._status.value,
            "retries": self._retries,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Payment(id={self._payment_id}, "
            f"amount={self._amount} {self._currency}, "
            f"status={self._status.value}, "
            f"retries={self._retries})"
        )

    def __eq__(self, other: object) -> bool:
        """Check equality based on payment ID."""
        if not isinstance(other, Payment):
            return False
        return self._payment_id == other._payment_id