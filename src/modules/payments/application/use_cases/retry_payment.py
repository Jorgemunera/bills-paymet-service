"""Retry payment use case."""

from src.modules.payments.domain.repository import PaymentRepository
from src.modules.payments.domain.errors import (
    PaymentNotFoundError,
    CannotRetryPaymentError,
    MaxRetriesExceededError,
)
from src.modules.payments.application.ports.payment_processor import PaymentProcessor
from src.modules.payments.application.dtos import RetryPaymentRequest, PaymentResponse
from src.shared.utils.logger import Logger


class RetryPaymentUseCase:
    """
    Use case for retrying a failed payment.

    This use case orchestrates:
    1. Payment retrieval and validation
    2. Retry eligibility check (status and retry count)
    3. Retry counter increment
    4. Payment re-processing (with retry probability)
    5. Status update based on result
    """

    def __init__(
        self,
        payment_repository: PaymentRepository,
        payment_processor: PaymentProcessor,
    ) -> None:
        """
        Initialize use case with dependencies.

        Args:
            payment_repository: Repository for payment persistence
            payment_processor: Service for processing payments
        """
        self._payment_repository = payment_repository
        self._payment_processor = payment_processor
        self._logger = Logger("USE_CASE:RETRY_PAYMENT")

    async def execute(self, request: RetryPaymentRequest) -> PaymentResponse:
        """
        Execute the retry payment use case.

        Args:
            request: The retry payment request DTO

        Returns:
            PaymentResponse with updated payment data

        Raises:
            PaymentNotFoundError: If payment does not exist
            CannotRetryPaymentError: If payment is not in FAILED status
            MaxRetriesExceededError: If max retries already reached
        """
        self._logger.info(
            "Retrying payment",
            extra={"payment_id": request.payment_id},
        )

        # Step 1: Retrieve payment
        payment = await self._payment_repository.find_by_id(request.payment_id)

        if not payment:
            self._logger.warning(
                "Payment not found",
                extra={"payment_id": request.payment_id},
            )
            raise PaymentNotFoundError(request.payment_id)

        self._logger.info(
            "Payment found",
            extra={
                "payment_id": payment.payment_id,
                "status": payment.status.value,
                "retries": payment.retries,
            },
        )

        # Step 2: Check if can retry (this raises appropriate errors)
        if not payment.can_retry():
            if not payment.status.can_retry():
                self._logger.warning(
                    "Cannot retry - invalid status",
                    extra={
                        "payment_id": payment.payment_id,
                        "status": payment.status.value,
                    },
                )
                raise CannotRetryPaymentError(
                    payment_id=payment.payment_id,
                    current_status=payment.status.value,
                )
            else:
                self._logger.warning(
                    "Cannot retry - max retries exceeded",
                    extra={
                        "payment_id": payment.payment_id,
                        "retries": payment.retries,
                    },
                )
                raise MaxRetriesExceededError(
                    payment_id=payment.payment_id,
                    max_retries=payment.MAX_RETRIES,
                )

        # Step 3: Increment retry counter
        payment.increment_retries()

        self._logger.info(
            "Retry counter incremented",
            extra={
                "payment_id": payment.payment_id,
                "retries": payment.retries,
            },
        )

        # Step 4: Process retry (with different probability than initial)
        processing_result = await self._payment_processor.process_retry(
            payment_id=payment.payment_id,
            amount=payment.amount,
        )

        self._logger.info(
            "Retry processing completed",
            extra={
                "payment_id": payment.payment_id,
                "success": processing_result.success,
                "message": processing_result.message,
            },
        )

        # Step 5: Update status based on result
        payment.process_retry_result(success=processing_result.success)

        await self._payment_repository.update(payment)

        self._logger.info(
            "Payment status updated after retry",
            extra={
                "payment_id": payment.payment_id,
                "status": payment.status.value,
                "retries": payment.retries,
            },
        )

        return PaymentResponse.from_entity(payment)