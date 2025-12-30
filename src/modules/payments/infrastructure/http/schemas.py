"""Pydantic schemas for HTTP request/response validation."""

from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class CreatePaymentRequestSchema(BaseModel):
    """Schema for payment creation request body."""

    reference: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="External reference for the bill/contract",
        examples=["FAC-12345"],
    )
    amount: Decimal = Field(
        ...,
        gt=0,
        description="Payment amount (must be greater than 0)",
        examples=[1500.00],
    )
    currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Currency code (exactly 3 characters)",
        examples=["MXN"],
    )

    @field_validator("currency")
    @classmethod
    def currency_to_upper(cls, v: str) -> str:
        """Convert currency to uppercase."""
        return v.upper()

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "reference": "FAC-12345",
                "amount": 1500.00,
                "currency": "MXN",
            }
        }


class PaymentResponseSchema(BaseModel):
    """Schema for payment response."""

    payment_id: str = Field(
        ...,
        description="Unique payment identifier",
    )
    reference: str = Field(
        ...,
        description="External reference for the bill/contract",
    )
    amount: float = Field(
        ...,
        description="Payment amount",
    )
    currency: str = Field(
        ...,
        description="Currency code",
    )
    status: str = Field(
        ...,
        description="Payment status (PENDING, SUCCESS, FAILED, EXHAUSTED)",
    )
    retries: int = Field(
        ...,
        description="Number of retry attempts",
    )
    created_at: str = Field(
        ...,
        description="Creation timestamp (ISO 8601)",
    )
    updated_at: str = Field(
        ...,
        description="Last update timestamp (ISO 8601)",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "payment_id": "550e8400-e29b-41d4-a716-446655440000",
                "reference": "FAC-12345",
                "amount": 1500.00,
                "currency": "MXN",
                "status": "FAILED",
                "retries": 1,
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-15T10:30:05",
            }
        }


class ListPaymentsResponseSchema(BaseModel):
    """Schema for list payments response."""

    payments: list[PaymentResponseSchema] = Field(
        ...,
        description="List of payments",
    )
    total: int = Field(
        ...,
        description="Total number of payments matching criteria",
    )
    limit: int = Field(
        ...,
        description="Maximum results per page",
    )
    offset: int = Field(
        ...,
        description="Number of results skipped",
    )


class ErrorDetailSchema(BaseModel):
    """Schema for error details."""

    code: str = Field(
        ...,
        description="Machine-readable error code",
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
    )
    details: dict | None = Field(
        default=None,
        description="Additional error details",
    )


class ErrorResponseSchema(BaseModel):
    """Schema for error response."""

    success: bool = Field(
        default=False,
        description="Always false for errors",
    )
    error: ErrorDetailSchema = Field(
        ...,
        description="Error information",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Amount must be greater than zero",
                    "details": {"field": "amount"},
                },
            }
        }


class HealthServiceSchema(BaseModel):
    """Schema for individual service health."""

    status: str = Field(
        ...,
        description="Service health status",
    )
    error: str | None = Field(
        default=None,
        description="Error message if unhealthy",
    )


class HealthResponseSchema(BaseModel):
    """Schema for health check response."""

    status: str = Field(
        ...,
        description="Overall health status",
    )
    timestamp: str = Field(
        ...,
        description="Health check timestamp",
    )
    services: dict[str, HealthServiceSchema] = Field(
        ...,
        description="Individual service health statuses",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00",
                "services": {
                    "database": {"status": "healthy"},
                    "redis": {"status": "healthy"},
                },
            }
        }