"""Create payment use case."""

from src.modules.payments.domain.payment import Payment
from src.modules.payments.domain.repository import PaymentRepository
from src.modules.payments.application.ports.payment_processor import PaymentProcessor
from src.modules.payments.application.ports.idempotency_service import IdempotencyService
from src.modules.payments.application.dtos import CreatePaymentRequest, PaymentResponse
from src.shared.utils.logger import Logger


class CreatePaymentUseCase:
    """
    Use case for creating a new payment.

    This use case orchestrates:
    1. Idempotency check (return existing if duplicate)
    2. Payment entity creation with validation
    3. Initial persistence in PENDING status
    4. Payment processing (simulated)
    5. Status update based on processing result
    6. Idempotency key storage
    """

    def __init__(
        self,
        payment_repository: PaymentRepository,
        payment_processor: PaymentProcessor,
        idempotency_service: IdempotencyService,
    ) -> None:
        """
        Initialize use case with dependencies.

        Args:
            payment_repository: Repository for payment persistence
            payment_processor: Service for processing payments
            idempotency_service: Service for idempotency management
        """
        self._payment_repository = payment_repository
        self._payment_processor = payment_processor
        self._idempotency_service = idempotency_service
        self._logger = Logger("USE_CASE:CREATE_PAYMENT")

    async def execute(self, request: CreatePaymentRequest) -> tuple[PaymentResponse, bool]:
        """
        Execute the create payment use case.

        Args:
            request: The create payment request DTO

        Returns:
            Tuple of (PaymentResponse, is_new) where is_new indicates
            if a new payment was created (True) or existing returned (False)

        Raises:
            PaymentValidationError: If payment data is invalid
        """
        self._logger.info(
            "Creating payment",
            extra={
                "reference": request.reference,
                "amount": float(request.amount),
                "currency": request.currency,
                "idempotency_key": request.idempotency_key,
            },
        )

        # Step 1: Check idempotency - return existing if duplicate
        existing_result = await self._idempotency_service.get_existing_result(
            request.idempotency_key
        )

        if existing_result:
            self._logger.info(
                "Idempotency key found, returning existing payment",
                extra={"payment_id": existing_result.get("payment_id")},
            )
            existing_payment = await self._payment_repository.find_by_id(
                existing_result["payment_id"]
            )
            if existing_payment:
                return PaymentResponse.from_entity(existing_payment), False

        # Step 2: Acquire lock to prevent race conditions
        lock_acquired = await self._idempotency_service.acquire_lock(
            request.idempotency_key
        )

        if not lock_acquired:
            # Another request is processing, wait and check again
            self._logger.warning(
                "Could not acquire lock, checking for existing result",
                extra={"idempotency_key": request.idempotency_key},
            )
            # Re-check after failed lock (another request might have completed)
            existing_result = await self._idempotency_service.get_existing_result(
                request.idempotency_key
            )
            if existing_result:
                existing_payment = await self._payment_repository.find_by_id(
                    existing_result["payment_id"]
                )
                if existing_payment:
                    return PaymentResponse.from_entity(existing_payment), False

        try:
            # Step 3: Create payment entity (validates business rules)
            payment = Payment.create(
                reference=request.reference,
                amount=request.amount,
                currency=request.currency,
            )

            self._logger.info(
                "Payment entity created",
                extra={
                    "payment_id": payment.payment_id,
                    "status": payment.status.value,
                },
            )

            # Step 4: Persist in PENDING status
            await self._payment_repository.save(payment)

            self._logger.info(
                "Payment persisted in PENDING status",
                extra={"payment_id": payment.payment_id},
            )

            # Step 5: Process payment (simulated)
            processing_result = await self._payment_processor.process(
                payment_id=payment.payment_id,
                amount=payment.amount,
            )

            self._logger.info(
                "Payment processing completed",
                extra={
                    "payment_id": payment.payment_id,
                    "success": processing_result.success,
                    "message": processing_result.message,
                },
            )

            # Step 6: Update status based on processing result
            if processing_result.success:
                payment.mark_as_success()
            else:
                payment.mark_as_failed()

            await self._payment_repository.update(payment)

            self._logger.info(
                "Payment status updated",
                extra={
                    "payment_id": payment.payment_id,
                    "status": payment.status.value,
                },
            )

            # Step 7: Save idempotency key
            await self._idempotency_service.save_result(
                idempotency_key=request.idempotency_key,
                result={"payment_id": payment.payment_id},
            )

            return PaymentResponse.from_entity(payment), True

        finally:
            # Always release lock
            if lock_acquired:
                await self._idempotency_service.release_lock(request.idempotency_key)