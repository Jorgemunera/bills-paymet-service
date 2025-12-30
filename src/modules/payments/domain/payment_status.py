"""Payment status enumeration."""

from enum import Enum


class PaymentStatus(str, Enum):
    """
    Possible states for a payment.

    State transitions:
        PENDING -> SUCCESS (payment processed successfully)
        PENDING -> FAILED (payment processing failed)
        FAILED -> SUCCESS (retry succeeded)
        FAILED -> FAILED (retry failed, retries < max)
        FAILED -> EXHAUSTED (retry failed, retries = max)

    Final states: SUCCESS, EXHAUSTED
    Non-final states: PENDING, FAILED
    """

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    EXHAUSTED = "EXHAUSTED"

    def is_final(self) -> bool:
        """Check if this is a final state (no more transitions allowed)."""
        return self in (PaymentStatus.SUCCESS, PaymentStatus.EXHAUSTED)

    def can_retry(self) -> bool:
        """Check if payment in this status can be retried."""
        return self == PaymentStatus.FAILED