"""Data Transfer Objects for the payments application layer."""

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

from src.modules.payments.domain.payment import Payment


@dataclass(frozen=True)
class CreatePaymentRequest:
    """Request DTO for creating a payment."""

    reference: str
    amount: Decimal
    currency: str
    idempotency_key: str


@dataclass(frozen=True)
class GetPaymentRequest:
    """Request DTO for getting a payment."""

    payment_id: str


@dataclass(frozen=True)
class RetryPaymentRequest:
    """Request DTO for retrying a payment."""

    payment_id: str


@dataclass(frozen=True)
class ListPaymentsRequest:
    """Request DTO for listing payments."""

    status: str | None = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class PaymentResponse:
    """Response DTO for payment operations."""

    payment_id: str
    reference: str
    amount: float
    currency: str
    status: str
    retries: int
    created_at: str
    updated_at: str

    @classmethod
    def from_entity(cls, payment: Payment) -> "PaymentResponse":
        """
        Create response DTO from Payment entity.

        Args:
            payment: The payment entity

        Returns:
            PaymentResponse DTO
        """
        return cls(
            payment_id=payment.payment_id,
            reference=payment.reference,
            amount=float(payment.amount),
            currency=payment.currency,
            status=payment.status.value,
            retries=payment.retries,
            created_at=payment.created_at.isoformat(),
            updated_at=payment.updated_at.isoformat(),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "payment_id": self.payment_id,
            "reference": self.reference,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "retries": self.retries,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class ListPaymentsResponse:
    """Response DTO for listing payments."""

    payments: list[PaymentResponse]
    total: int
    limit: int
    offset: int

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "payments": [p.to_dict() for p in self.payments],
            "total": self.total,
            "limit": self.limit,
            "offset": self.offset,
        }