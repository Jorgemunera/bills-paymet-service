"""Shared HTTP schemas."""

from pydantic import BaseModel, Field


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