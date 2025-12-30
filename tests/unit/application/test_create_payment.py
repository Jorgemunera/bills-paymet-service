"""Unit tests for CreatePaymentUseCase."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock

from src.modules.payments.application.use_cases.create_payment import CreatePaymentUseCase
from src.modules.payments.application.dtos import CreatePaymentRequest
from src.modules.payments.application.ports.payment_processor import ProcessingResult
from src.modules.payments.domain.payment_status import PaymentStatus
from src.modules.payments.domain.errors import PaymentValidationError


class TestCreatePaymentUseCase:
    """Tests for CreatePaymentUseCase."""

    @pytest.fixture
    def use_case(
        self,
        mock_payment_repository,
        mock_payment_processor,
        mock_idempotency_service,
    ) -> CreatePaymentUseCase:
        """Create use case with mocked dependencies."""
        return CreatePaymentUseCase(
            payment_repository=mock_payment_repository,
            payment_processor=mock_payment_processor,
            idempotency_service=mock_idempotency_service,
        )

    @pytest.fixture
    def valid_request(self) -> CreatePaymentRequest:
        """Create a valid payment request."""
        return CreatePaymentRequest(
            reference="FAC-12345",
            amount=Decimal("500.00"),
            currency="MXN",
            idempotency_key="test-key-123",
        )

    @pytest.mark.asyncio
    async def test_create_payment_success_amount_under_threshold(
        self,
        use_case,
        valid_request,
        mock_payment_repository,
        mock_payment_processor,
        mock_idempotency_service,
    ):
        """Should create payment with SUCCESS status when amount <= 1000."""
        mock_payment_processor.process.return_value = ProcessingResult(
            success=True,
            message="Payment processed successfully",
        )

        response, is_new = await use_case.execute(valid_request)

        assert is_new is True
        assert response.reference == "FAC-12345"
        assert response.amount == 500.00
        assert response.currency == "MXN"
        assert response.status == PaymentStatus.SUCCESS.value

        mock_payment_repository.save.assert_called_once()
        mock_payment_repository.update.assert_called_once()
        mock_idempotency_service.save_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_payment_failed_amount_over_threshold(
        self,
        use_case,
        mock_payment_repository,
        mock_payment_processor,
        mock_idempotency_service,
    ):
        """Should create payment with FAILED status when amount > 1000."""
        request = CreatePaymentRequest(
            reference="FAC-12345",
            amount=Decimal("1500.00"),
            currency="MXN",
            idempotency_key="test-key-456",
        )

        mock_payment_processor.process.return_value = ProcessingResult(
            success=False,
            message="Payment failed",
        )

        response, is_new = await use_case.execute(request)

        assert is_new is True
        assert response.amount == 1500.00
        assert response.status == PaymentStatus.FAILED.value

    @pytest.mark.asyncio
    async def test_create_payment_idempotency_returns_existing(
        self,
        use_case,
        valid_request,
        mock_payment_repository,
        mock_idempotency_service,
        sample_payment,
    ):
        """Should return existing payment when idempotency key exists."""
        mock_idempotency_service.get_existing_result.return_value = {
            "payment_id": sample_payment.payment_id,
        }
        mock_payment_repository.find_by_id.return_value = sample_payment

        response, is_new = await use_case.execute(valid_request)

        assert is_new is False
        assert response.payment_id == sample_payment.payment_id

        mock_payment_repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_payment_acquires_and_releases_lock(
        self,
        use_case,
        valid_request,
        mock_payment_processor,
        mock_idempotency_service,
    ):
        """Should acquire and release lock during creation."""
        mock_payment_processor.process.return_value = ProcessingResult(
            success=True,
            message="Success",
        )

        await use_case.execute(valid_request)

        mock_idempotency_service.acquire_lock.assert_called_once_with(
            valid_request.idempotency_key
        )
        mock_idempotency_service.release_lock.assert_called_once_with(
            valid_request.idempotency_key
        )

    @pytest.mark.asyncio
    async def test_create_payment_releases_lock_on_error(
        self,
        use_case,
        mock_payment_repository,
        mock_payment_processor,
        mock_idempotency_service,
    ):
        """Should release lock even when error occurs."""
        request = CreatePaymentRequest(
            reference="",  # Invalid - will raise error
            amount=Decimal("500.00"),
            currency="MXN",
            idempotency_key="test-key-error",
        )

        with pytest.raises(PaymentValidationError):
            await use_case.execute(request)

        mock_idempotency_service.release_lock.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_payment_invalid_reference_raises_error(
        self,
        use_case,
        mock_idempotency_service,
    ):
        """Should raise validation error for empty reference."""
        request = CreatePaymentRequest(
            reference="",
            amount=Decimal("500.00"),
            currency="MXN",
            idempotency_key="test-key",
        )

        with pytest.raises(PaymentValidationError) as exc_info:
            await use_case.execute(request)

        assert exc_info.value.code == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_create_payment_invalid_amount_raises_error(
        self,
        use_case,
        mock_idempotency_service,
    ):
        """Should raise validation error for zero amount."""
        request = CreatePaymentRequest(
            reference="FAC-12345",
            amount=Decimal("0"),
            currency="MXN",
            idempotency_key="test-key",
        )

        with pytest.raises(PaymentValidationError) as exc_info:
            await use_case.execute(request)

        assert exc_info.value.code == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_create_payment_invalid_currency_raises_error(
        self,
        use_case,
        mock_idempotency_service,
    ):
        """Should raise validation error for invalid currency."""
        request = CreatePaymentRequest(
            reference="FAC-12345",
            amount=Decimal("500.00"),
            currency="INVALID",
            idempotency_key="test-key",
        )

        with pytest.raises(PaymentValidationError) as exc_info:
            await use_case.execute(request)

        assert exc_info.value.code == "VALIDATION_ERROR"