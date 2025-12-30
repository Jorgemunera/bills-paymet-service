"""Unit tests for GetPaymentUseCase."""

import pytest

from src.modules.payments.application.use_cases.get_payment import GetPaymentUseCase
from src.modules.payments.application.dtos import GetPaymentRequest
from src.modules.payments.domain.errors import PaymentNotFoundError


class TestGetPaymentUseCase:
    """Tests for GetPaymentUseCase."""

    @pytest.fixture
    def use_case(self, mock_payment_repository) -> GetPaymentUseCase:
        """Create use case with mocked dependencies."""
        return GetPaymentUseCase(
            payment_repository=mock_payment_repository,
        )

    @pytest.mark.asyncio
    async def test_get_payment_success(
        self,
        use_case,
        mock_payment_repository,
        sample_payment,
    ):
        """Should return payment when found."""
        mock_payment_repository.find_by_id.return_value = sample_payment

        request = GetPaymentRequest(payment_id=sample_payment.payment_id)
        response = await use_case.execute(request)

        assert response.payment_id == sample_payment.payment_id
        assert response.reference == sample_payment.reference
        assert response.amount == float(sample_payment.amount)
        assert response.currency == sample_payment.currency
        assert response.status == sample_payment.status.value

        mock_payment_repository.find_by_id.assert_called_once_with(
            sample_payment.payment_id
        )

    @pytest.mark.asyncio
    async def test_get_payment_not_found_raises_error(
        self,
        use_case,
        mock_payment_repository,
    ):
        """Should raise PaymentNotFoundError when payment doesn't exist."""
        mock_payment_repository.find_by_id.return_value = None

        request = GetPaymentRequest(payment_id="non-existent-id")

        with pytest.raises(PaymentNotFoundError) as exc_info:
            await use_case.execute(request)

        assert exc_info.value.code == "PAYMENT_NOT_FOUND"
        assert "non-existent-id" in exc_info.value.message
        assert exc_info.value.status_code == 404