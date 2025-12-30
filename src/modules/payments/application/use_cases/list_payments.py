"""List payments use case."""

from src.modules.payments.domain.repository import PaymentRepository
from src.modules.payments.domain.payment_status import PaymentStatus
from src.modules.payments.domain.errors import PaymentValidationError
from src.modules.payments.application.dtos import (
    ListPaymentsRequest,
    ListPaymentsResponse,
    PaymentResponse,
)
from src.shared.utils.logger import Logger


class ListPaymentsUseCase:
    """
    Use case for listing payments with optional filtering.

    Supports pagination and filtering by status.
    """

    def __init__(self, payment_repository: PaymentRepository) -> None:
        """
        Initialize use case with dependencies.

        Args:
            payment_repository: Repository for payment persistence
        """
        self._payment_repository = payment_repository
        self._logger = Logger("USE_CASE:LIST_PAYMENTS")

    async def execute(self, request: ListPaymentsRequest) -> ListPaymentsResponse:
        """
        Execute the list payments use case.

        Args:
            request: The list payments request DTO

        Returns:
            ListPaymentsResponse with paginated results

        Raises:
            PaymentValidationError: If status filter is invalid
        """
        self._logger.info(
            "Listing payments",
            extra={
                "status": request.status,
                "limit": request.limit,
                "offset": request.offset,
            },
        )

        # Validate status filter if provided
        if request.status:
            valid_statuses = [s.value for s in PaymentStatus]
            if request.status not in valid_statuses:
                self._logger.warning(
                    "Invalid status filter",
                    extra={
                        "status": request.status,
                        "valid_statuses": valid_statuses,
                    },
                )
                raise PaymentValidationError(
                    message=f"Invalid status '{request.status}'. Valid values: {', '.join(valid_statuses)}",
                    field="status",
                )

        # Get payments and total count
        payments = await self._payment_repository.find_all(
            status=request.status,
            limit=request.limit,
            offset=request.offset,
        )

        total = await self._payment_repository.count(status=request.status)

        self._logger.info(
            "Payments retrieved",
            extra={
                "count": len(payments),
                "total": total,
            },
        )

        return ListPaymentsResponse(
            payments=[PaymentResponse.from_entity(p) for p in payments],
            total=total,
            limit=request.limit,
            offset=request.offset,
        )