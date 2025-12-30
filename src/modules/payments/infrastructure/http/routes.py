"""FastAPI routes for payments module."""

from fastapi import APIRouter, Header, Query, status
from fastapi.responses import JSONResponse

from src.modules.payments.infrastructure.http.schemas import (
    CreatePaymentRequestSchema,
    PaymentResponseSchema,
    ListPaymentsResponseSchema,
    ErrorResponseSchema,
)
from src.modules.payments.application.dtos import (
    CreatePaymentRequest,
    GetPaymentRequest,
    RetryPaymentRequest,
    ListPaymentsRequest,
)
from src.dependencies import (
    CreatePaymentUseCaseDep,
    GetPaymentUseCaseDep,
    RetryPaymentUseCaseDep,
    ListPaymentsUseCaseDep,
)
from src.shared.utils.logger import Logger

router = APIRouter(prefix="/payments", tags=["Payments"])
logger = Logger("HTTP:PAYMENTS")


@router.post(
    "",
    response_model=PaymentResponseSchema,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {
            "model": PaymentResponseSchema,
            "description": "Payment previously created (idempotency)",
        },
        201: {
            "model": PaymentResponseSchema,
            "description": "Payment created successfully",
        },
        400: {
            "model": ErrorResponseSchema,
            "description": "Validation error",
        },
    },
    summary="Create a new payment",
    description="""
    Create a new payment with the provided details.

    **Idempotency:** The `Idempotency-Key` header is required. If a payment
    was previously created with the same key, the original payment will be
    returned with status 200 instead of creating a duplicate.

    **Processing Rules:**
    - Payments with amount ≤ 1000 will be processed successfully (SUCCESS)
    - Payments with amount > 1000 will fail (FAILED) and can be retried
    """,
)
async def create_payment(
    body: CreatePaymentRequestSchema,
    use_case: CreatePaymentUseCaseDep,
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        description="Unique key to ensure idempotent requests",
        examples=["unique-key-123"],
    ),
):
    """Create a new payment."""
    logger.info(
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

    response, is_new = await use_case.execute(request)

    logger.info(
        "Payment creation completed",
        extra={
            "payment_id": response.payment_id,
            "status": response.status,
            "is_new": is_new,
        },
    )

    if is_new:
        return response.to_dict()
    else:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response.to_dict(),
        )


@router.get(
    "",
    response_model=ListPaymentsResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "model": ErrorResponseSchema,
            "description": "Invalid status filter",
        },
    },
    summary="List all payments",
    description="""
    Retrieve a paginated list of payments with optional filtering.

    **Filters:**
    - `status`: Filter by payment status (PENDING, SUCCESS, FAILED, EXHAUSTED)

    **Pagination:**
    - `limit`: Maximum number of results (default: 100)
    - `offset`: Number of results to skip (default: 0)
    """,
)
async def list_payments(
    use_case: ListPaymentsUseCaseDep,
    status: str | None = Query(
        default=None,
        description="Filter by payment status",
        examples=["FAILED"],
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum results per page",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of results to skip",
    ),
):
    """List all payments with optional filtering."""
    logger.info(
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

    response = await use_case.execute(request)

    logger.info(
        "List payments completed",
        extra={
            "count": len(response.payments),
            "total": response.total,
        },
    )

    return response.to_dict()


@router.get(
    "/{payment_id}",
    response_model=PaymentResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "model": ErrorResponseSchema,
            "description": "Payment not found",
        },
    },
    summary="Get payment by ID",
    description="Retrieve a specific payment by its unique identifier.",
)
async def get_payment(
    payment_id: str,
    use_case: GetPaymentUseCaseDep,
):
    """Get a payment by ID."""
    logger.info(
        "Received get payment request",
        extra={"payment_id": payment_id},
    )

    request = GetPaymentRequest(payment_id=payment_id)
    response = await use_case.execute(request)

    logger.info(
        "Get payment completed",
        extra={
            "payment_id": response.payment_id,
            "status": response.status,
        },
    )

    return response.to_dict()


@router.post(
    "/{payment_id}/retry",
    response_model=PaymentResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "model": ErrorResponseSchema,
            "description": "Payment not found",
        },
        409: {
            "model": ErrorResponseSchema,
            "description": "Payment cannot be retried",
        },
    },
    summary="Retry a failed payment",
    description="""
    Retry a payment that previously failed.

    **Rules:**
    - Only payments with status FAILED can be retried
    - Maximum 3 retry attempts allowed
    - Each retry has a 50% chance of success
    - After 3 failed retries, status changes to EXHAUSTED
    """,
)
async def retry_payment(
    payment_id: str,
    use_case: RetryPaymentUseCaseDep,
):
    """Retry a failed payment."""
    logger.info(
        "Received retry payment request",
        extra={"payment_id": payment_id},
    )

    request = RetryPaymentRequest(payment_id=payment_id)
    response = await use_case.execute(request)

    logger.info(
        "Retry payment completed",
        extra={
            "payment_id": response.payment_id,
            "status": response.status,
            "retries": response.retries,
        },
    )

    return response.to_dict()