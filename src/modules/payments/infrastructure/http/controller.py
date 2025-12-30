"""HTTP controller for payments endpoints."""

from decimal import Decimal

from src.modules.payments.application.use_cases import (
    CreatePaymentUseCase,
    GetPaymentUseCase,
    RetryPaymentUseCase,
    ListPaymentsUseCase,
)
from src.modules.payments.application.dtos import (
    CreatePaymentRequest,
    GetPaymentRequest,
    RetryPaymentRequest,
    ListPaymentsRequest,
    PaymentResponse,
    ListPaymentsResponse,
)
from src.modules.payments.infrastructure.http.schemas import CreatePaymentRequestSchema
from src.shared.utils.logger import Logger


class PaymentController:
    """
    HTTP controller for payment operations.

    Handles HTTP-specific concerns:
    - Request validation
    - Header extraction
    - Response formatting

    Delegates business logic to use cases.
    """

    def __init__(
        self,
        create_payment_use_case: CreatePaymentUseCase,
        get_payment_use_case: GetPaymentUseCase,
        retry_payment_use_case: RetryPaymentUseCase,
        list_payments_use_case: ListPaymentsUseCase,
    ) -> None:
        """
        Initialize controller with use cases.

        Args:
            create_payment_use_case: Use case for creating payments
            get_payment_use_case: Use case for retrieving payments
            retry_payment_use_case: Use case for retrying payments
            list_payments_use_case: Use case for listing payments
        """
        self._create_payment = create_payment_use_case
        self._get_payment = get_payment_use_case
        self._retry_payment = retry_payment_use_case
        self._list_payments = list_payments_use_case
        self._logger = Logger("CONTROLLER:PAYMENT")

    async def create_payment(
        self,
        body: CreatePaymentRequestSchema,
        idempotency_key: str,
    ) -> tuple[PaymentResponse, bool]:
        """
        Handle payment creation request.

        Args:
            body: Validated request body
            idempotency_key: Idempotency key from header

        Returns:
            Tuple of (PaymentResponse, is_new)
        """
        self._logger.info(
            "Received create payment request",
            extra={
                "reference": body.reference,
                "amount": float(body.amount),
                "currency": body.currency,
            },
        )

        request = CreatePaymentRequest(
            reference=body.reference,
            amount=body.amount,
            currency=body.currency,
            idempotency_key=idempotency_key,
        )

        response, is_new = await self._create_payment.execute(request)

        self._logger.info(
            "Payment creation completed",
            extra={
                "payment_id": response.payment_id,
                "status": response.status,
                "is_new": is_new,
            },
        )

        return response, is_new

    async def get_payment(self, payment_id: str) -> PaymentResponse:
        """
        Handle get payment request.

        Args:
            payment_id: Payment ID from path

        Returns:
            PaymentResponse with payment data
        """
        self._logger.info(
            "Received get payment request",
            extra={"payment_id": payment_id},
        )

        request = GetPaymentRequest(payment_id=payment_id)
        response = await self._get_payment.execute(request)

        self._logger.info(
            "Get payment completed",
            extra={
                "payment_id": response.payment_id,
                "status": response.status,
            },
        )

        return response

    async def retry_payment(self, payment_id: str) -> PaymentResponse:
        """
        Handle retry payment request.

        Args:
            payment_id: Payment ID from path

        Returns:
            PaymentResponse with updated payment data
        """
        self._logger.info(
            "Received retry payment request",
            extra={"payment_id": payment_id},
        )

        request = RetryPaymentRequest(payment_id=payment_id)
        response = await self._retry_payment.execute(request)

        self._logger.info(
            "Retry payment completed",
            extra={
                "payment_id": response.payment_id,
                "status": response.status,
                "retries": response.retries,
            },
        )

        return response

    async def list_payments(
        self,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ListPaymentsResponse:
        """
        Handle list payments request.

        Args:
            status: Optional status filter
            limit: Maximum results
            offset: Results to skip

        Returns:
            ListPaymentsResponse with paginated results
        """
        self._logger.info(
            "Received list payments request",
            extra={
                "status": status,
                "limit": limit,
                "offset": offset,
            },
        )

        request = ListPaymentsRequest(
            status=status,
            limit=limit,
            offset=offset,
        )

        response = await self._list_payments.execute(request)

        self._logger.info(
            "List payments completed",
            extra={
                "count": len(response.payments),
                "total": response.total,
            },
        )

        return response