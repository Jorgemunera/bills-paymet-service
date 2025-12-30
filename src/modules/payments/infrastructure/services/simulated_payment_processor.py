"""Simulated payment processor implementation."""

import random
from decimal import Decimal

from src.modules.payments.application.ports.payment_processor import (
    PaymentProcessor,
    ProcessingResult,
)
from src.config.settings import get_settings
from src.shared.utils.logger import Logger


class SimulatedPaymentProcessor(PaymentProcessor):
    """
    Simulated payment processor for testing and demonstration.

    This is an ADAPTER in hexagonal architecture terms.
    It implements the PaymentProcessor PORT.

    Processing rules:
    - Initial processing: amount <= 1000 -> SUCCESS, amount > 1000 -> FAILED
    - Retry processing: 50% probability of SUCCESS (configurable)
    """

    # Threshold for initial processing success
    AMOUNT_THRESHOLD = Decimal("1000")

    def __init__(self) -> None:
        """Initialize the simulated processor."""
        self._settings = get_settings()
        self._logger = Logger("SERVICE:PAYMENT_PROCESSOR")
        self._retry_success_probability = self._settings.retry_success_probability

    async def process(self, payment_id: str, amount: Decimal) -> ProcessingResult:
        """
        Process a payment (initial attempt).

        Business rule:
        - amount <= 1000: SUCCESS
        - amount > 1000: FAILED

        Args:
            payment_id: The payment identifier
            amount: The payment amount

        Returns:
            ProcessingResult indicating success or failure
        """
        self._logger.info(
            "Processing payment",
            extra={
                "payment_id": payment_id,
                "amount": float(amount),
                "threshold": float(self.AMOUNT_THRESHOLD),
            },
        )

        # Simulate processing delay (in real system, this would call external API)
        # await asyncio.sleep(0.1)

        if amount <= self.AMOUNT_THRESHOLD:
            self._logger.info(
                "Payment processed successfully",
                extra={
                    "payment_id": payment_id,
                    "reason": "Amount within threshold",
                },
            )
            return ProcessingResult(
                success=True,
                message="Payment processed successfully",
            )
        else:
            self._logger.info(
                "Payment processing failed",
                extra={
                    "payment_id": payment_id,
                    "reason": "Amount exceeds threshold",
                },
            )
            return ProcessingResult(
                success=False,
                message=f"Payment failed: amount {amount} exceeds threshold {self.AMOUNT_THRESHOLD}",
            )

    async def process_retry(self, payment_id: str, amount: Decimal) -> ProcessingResult:
        """
        Process a payment retry.

        Retry has a configurable probability of success (default 50%).
        This simulates real-world scenarios where temporary failures
        may resolve on retry.

        Args:
            payment_id: The payment identifier
            amount: The payment amount

        Returns:
            ProcessingResult indicating success or failure
        """
        self._logger.info(
            "Processing payment retry",
            extra={
                "payment_id": payment_id,
                "amount": float(amount),
                "success_probability": self._retry_success_probability,
            },
        )

        # Simulate processing delay
        # await asyncio.sleep(0.1)

        # Random success based on configured probability
        success = random.random() < self._retry_success_probability

        if success:
            self._logger.info(
                "Payment retry succeeded",
                extra={"payment_id": payment_id},
            )
            return ProcessingResult(
                success=True,
                message="Payment retry processed successfully",
            )
        else:
            self._logger.info(
                "Payment retry failed",
                extra={"payment_id": payment_id},
            )
            return ProcessingResult(
                success=False,
                message="Payment retry failed: simulated temporary failure",
            )