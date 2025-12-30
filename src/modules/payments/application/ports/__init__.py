"""Application ports (interfaces) for external dependencies."""

from src.modules.payments.application.ports.payment_processor import PaymentProcessor
from src.modules.payments.application.ports.idempotency_service import IdempotencyService

__all__ = [
    "PaymentProcessor",
    "IdempotencyService",
]