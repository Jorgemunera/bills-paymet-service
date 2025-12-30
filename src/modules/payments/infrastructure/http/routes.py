"""FastAPI routes for payments module."""

from fastapi import APIRouter, Header, HTTPException, Query, status

from src.modules.payments.infrastructure.http.controller import PaymentController
from src.modules.payments.infrastructure.http.schemas import (
    CreatePaymentRequestSchema,
    PaymentResponseSchema,
    ListPaymentsResponseSchema,
    ErrorResponseSchema,
)


def create_payment_routes(controller: PaymentController) -> APIRouter:
    """
    Create FastAPI router for payment endpoints.

    Args:
        controller: Payment controller instance

    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/payments", tags=["Payments"])

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
        idempotency_key: str = Header(
            ...,
            alias="Idempotency-Key",
            description="Unique key to ensure idempotent requests",
            examples=["unique-key-123"],
        ),
    ):
        """Create a new payment."""
        response, is_new = await controller.create_payment(body, idempotency_key)

        if is_new:
            return response.to_dict()
        else:
            # Return 200 for idempotent request
            from fastapi.responses import JSONResponse
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
        response = await controller.list_payments(
            status=status,
            limit=limit,
            offset=offset,
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
    async def get_payment(payment_id: str):
        """Get a payment by ID."""
        response = await controller.get_payment(payment_id)
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
    async def retry_payment(payment_id: str):
        """Retry a failed payment."""
        response = await controller.retry_payment(payment_id)
        return response.to_dict()

    return router