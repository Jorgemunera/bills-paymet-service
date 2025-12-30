"""Domain errors for the payments module."""

from typing import Any


class PaymentError(Exception):
    """Base class for payment domain errors."""

    def __init__(
        self,
        message: str,
        code: str = "PAYMENT_ERROR",
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize payment error.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            status_code: HTTP status code for API responses
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for API responses."""
        result = {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
            },
        }

        if self.details:
            result["error"]["details"] = self.details

        return result


class PaymentNotFoundError(PaymentError):
    """Raised when a payment is not found."""

    def __init__(self, payment_id: str) -> None:
        """
        Initialize payment not found error.

        Args:
            payment_id: The ID of the payment that was not found
        """
        super().__init__(
            message=f"Payment with id '{payment_id}' not found",
            code="PAYMENT_NOT_FOUND",
            status_code=404,
            details={"payment_id": payment_id},
        )


class PaymentValidationError(PaymentError):
    """Raised when payment data validation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        """
        Initialize validation error.

        Args:
            message: Description of the validation failure
            field: The field that failed validation (optional)
        """
        details = {"field": field} if field else {}
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details,
        )


class CannotRetryPaymentError(PaymentError):
    """Raised when a payment cannot be retried due to its current status."""

    def __init__(self, payment_id: str, current_status: str) -> None:
        """
        Initialize cannot retry error.

        Args:
            payment_id: The ID of the payment
            current_status: The current status that prevents retry
        """
        super().__init__(
            message=f"Payment '{payment_id}' cannot be retried. Current status: {current_status}. Only FAILED payments can be retried.",
            code="CANNOT_RETRY_PAYMENT",
            status_code=409,
            details={
                "payment_id": payment_id,
                "current_status": current_status,
                "allowed_status": "FAILED",
            },
        )


class MaxRetriesExceededError(PaymentError):
    """Raised when maximum retry attempts have been reached."""

    def __init__(self, payment_id: str, max_retries: int) -> None:
        """
        Initialize max retries exceeded error.

        Args:
            payment_id: The ID of the payment
            max_retries: The maximum number of retries allowed
        """
        super().__init__(
            message=f"Payment '{payment_id}' has reached the maximum number of retries ({max_retries})",
            code="MAX_RETRIES_EXCEEDED",
            status_code=409,
            details={
                "payment_id": payment_id,
                "max_retries": max_retries,
            },
        )