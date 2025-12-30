"""Unit tests for RetryPaymentUseCase."""

import pytest
from decimal import Decimal
from datetime import datetime

from src.modules.payments.application.use_cases.retry_payment import RetryPaymentUseCase
from src.modules.payments.application.dtos import RetryPaymentRequest
from src.modules.payments.application.ports.payment_processor import ProcessingResult
from src.modules.payments.domain.payment import Payment
from src.modules.payments.domain.payment_status import PaymentStatus
from src.modules.payments.domain.errors import (
    PaymentNotFoundError,
    CannotRetryPaymentError,
    MaxRetriesExceededError,
)


class TestRetryPaymentUseCase:
    """Tests for RetryPaymentUseCase."""

    @pytest.fixture
    def use_case(
        self,
        mock_payment_repository,
        mock_payment_processor,
    ) -> RetryPaymentUseCase:
        """Create use case with mocked dependencies."""
        return RetryPaymentUseCase(
            payment_repository=mock_payment_repository,
            payment_processor=mock_payment_processor,
        )

    @pytest.mark.asyncio
    async def test_retry_payment_success(
        self,
        use_case,
        mock_payment_repository,
        mock_payment_processor,
        failed_payment,
    ):
        """Should retry and succeed."""
        mock_payment_repository.find_by_id.return_value = failed_payment
        mock_payment_processor.process_retry.return_value = ProcessingResult(
            success=True,
            message="Retry successful",
        )

        request = RetryPaymentRequest(payment_id=failed_payment.payment_id)
        response = await use_case.execute(request)

        assert response.status == PaymentStatus.SUCCESS.value
        assert response.retries == 1

        mock_payment_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_payment_failed_with_retries_remaining(
        self,
        use_case,
        mock_payment_repository,
        mock_payment_processor,
        failed_payment,
    ):
        """Should stay FAILED when retry fails but retries remain."""
        mock_payment_repository.find_by_id.return_value = failed_payment
        mock_payment_processor.process_retry.return_value = ProcessingResult(
            success=False,
            message="Retry failed",
        )

        request = RetryPaymentRequest(payment_id=failed_payment.payment_id)
        response = await use_case.execute(request)

        assert response.status == PaymentStatus.FAILED.value
        assert response.retries == 1

    @pytest.mark.asyncio
    async def test_retry_payment_exhausted_after_max_retries(
        self,
        use_case,
        mock_payment_repository,
        mock_payment_processor,
    ):
        """Should become EXHAUSTED after 3rd failed retry."""
        # Payment with 2 retries already
        payment = Payment(
            payment_id="pay-almost-exhausted",
            reference="FAC-123",
            amount=Decimal("1500.00"),
            currency="MXN",
            status=PaymentStatus.FAILED,
            retries=2,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        mock_payment_repository.find_by_id.return_value = payment
        mock_payment_processor.process_retry.return_value = ProcessingResult(
            success=False,
            message="Retry failed",
        )

        request = RetryPaymentRequest(payment_id=payment.payment_id)
        response = await use_case.execute(request)

        assert response.status == PaymentStatus.EXHAUSTED.value
        assert response.retries == 3

    @pytest.mark.asyncio
    async def test_retry_payment_not_found_raises_error(
        self,
        use_case,
        mock_payment_repository,
    ):
        """Should raise PaymentNotFoundError when payment doesn't exist."""
        mock_payment_repository.find_by_id.return_value = None

        request = RetryPaymentRequest(payment_id="non-existent-id")

        with pytest.raises(PaymentNotFoundError) as exc_info:
            await use_case.execute(request)

        assert exc_info.value.code == "PAYMENT_NOT_FOUND"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_retry_success_payment_raises_error(
        self,
        use_case,
        mock_payment_repository,
        success_payment,
    ):
        """Should raise CannotRetryPaymentError for SUCCESS payment."""
        mock_payment_repository.find_by_id.return_value = success_payment

        request = RetryPaymentRequest(payment_id=success_payment.payment_id)

        with pytest.raises(CannotRetryPaymentError) as exc_info:
            await use_case.execute(request)

        assert exc_info.value.code == "CANNOT_RETRY_PAYMENT"
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_retry_pending_payment_raises_error(
        self,
        use_case,
        mock_payment_repository,
        sample_payment,
    ):
        """Should raise CannotRetryPaymentError for PENDING payment."""
        mock_payment_repository.find_by_id.return_value = sample_payment

        request = RetryPaymentRequest(payment_id=sample_payment.payment_id)

        with pytest.raises(CannotRetryPaymentError) as exc_info:
            await use_case.execute(request)

        assert exc_info.value.code == "CANNOT_RETRY_PAYMENT"

    @pytest.mark.asyncio
    async def test_retry_exhausted_payment_raises_error(
        self,
        use_case,
        mock_payment_repository,
        exhausted_payment,
    ):
        """Should raise CannotRetryPaymentError for EXHAUSTED payment."""
        mock_payment_repository.find_by_id.return_value = exhausted_payment

        request = RetryPaymentRequest(payment_id=exhausted_payment.payment_id)

        with pytest.raises(CannotRetryPaymentError) as exc_info:
            await use_case.execute(request)

        assert exc_info.value.code == "CANNOT_RETRY_PAYMENT"

    @pytest.mark.asyncio
    async def test_retry_max_retries_exceeded_raises_error(
        self,
        use_case,
        mock_payment_repository,
        failed_payment_max_retries,
    ):
        """Should raise MaxRetriesExceededError when max retries reached."""
        mock_payment_repository.find_by_id.return_value = failed_payment_max_retries

        request = RetryPaymentRequest(payment_id=failed_payment_max_retries.payment_id)

        with pytest.raises(MaxRetriesExceededError) as exc_info:
            await use_case.execute(request)

        assert exc_info.value.code == "MAX_RETRIES_EXCEEDED"
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_retry_calls_process_retry_not_process(
        self,
        use_case,
        mock_payment_repository,
        mock_payment_processor,
        failed_payment,
    ):
        """Should call process_retry, not process."""
        mock_payment_repository.find_by_id.return_value = failed_payment
        mock_payment_processor.process_retry.return_value = ProcessingResult(
            success=True,
            message="Success",
        )

        request = RetryPaymentRequest(payment_id=failed_payment.payment_id)
        await use_case.execute(request)

        mock_payment_processor.process_retry.assert_called_once()
        mock_payment_processor.process.assert_not_called()