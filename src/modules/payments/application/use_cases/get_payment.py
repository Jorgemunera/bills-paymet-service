"""Get payment use case."""

from src.modules.payments.domain.repository import PaymentRepository
from src.modules.payments.domain.errors import PaymentNotFoundError
from src.modules.payments.application.dtos import GetPaymentRequest, PaymentResponse
from src.shared.utils.logger import Logger


class GetPaymentUseCase:
    """
    Use case for retrieving a payment by ID.

    Simple query use case that retrieves a payment from the repository.
    """

    def __init__(self, payment_repository: PaymentRepository) -> None:
        """
        Initialize use case with dependencies.

        Args:
            payment_repository: Repository for payment persistence
        """
        self._payment_repository = payment_repository
        self._logger = Logger("USE_CASE:GET_PAYMENT")

    async def execute(self, request: GetPaymentRequest) -> PaymentResponse:
        """
        Execute the get payment use case.

        Args:
            request: The get payment request DTO

        Returns:
            PaymentResponse with payment data

        Raises:
            PaymentNotFoundError: If payment does not exist
        """
        self._logger.info(
            "Getting payment",
            extra={"payment_id": request.payment_id},
        )

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
            },
        )

        return PaymentResponse.from_entity(payment)