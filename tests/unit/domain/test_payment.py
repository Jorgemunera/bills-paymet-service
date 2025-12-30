"""Unit tests for Payment entity."""

import pytest
from decimal import Decimal
from datetime import datetime

from src.modules.payments.domain.payment import Payment
from src.modules.payments.domain.payment_status import PaymentStatus
from src.modules.payments.domain.errors import (
    PaymentValidationError,
    CannotRetryPaymentError,
    MaxRetriesExceededError,
)


class TestPaymentCreate:
    """Tests for Payment.create() factory method."""

    def test_create_payment_success(self):
        """Should create a payment with valid data."""
        payment = Payment.create(
            reference="FAC-12345",
            amount=Decimal("1500.00"),
            currency="MXN",
        )

        assert payment.payment_id is not None
        assert len(payment.payment_id) == 36  # UUID format
        assert payment.reference == "FAC-12345"
        assert payment.amount == Decimal("1500.00")
        assert payment.currency == "MXN"
        assert payment.status == PaymentStatus.PENDING
        assert payment.retries == 0
        assert payment.created_at is not None
        assert payment.updated_at is not None

    def test_create_payment_trims_reference(self):
        """Should trim whitespace from reference."""
        payment = Payment.create(
            reference="  FAC-12345  ",
            amount=Decimal("100.00"),
            currency="MXN",
        )

        assert payment.reference == "FAC-12345"

    def test_create_payment_uppercase_currency(self):
        """Should convert currency to uppercase."""
        payment = Payment.create(
            reference="FAC-12345",
            amount=Decimal("100.00"),
            currency="mxn",
        )

        assert payment.currency == "MXN"

    def test_create_payment_empty_reference_raises_error(self):
        """Should raise error when reference is empty."""
        with pytest.raises(PaymentValidationError) as exc_info:
            Payment.create(
                reference="",
                amount=Decimal("100.00"),
                currency="MXN",
            )

        assert exc_info.value.code == "VALIDATION_ERROR"
        assert "reference" in exc_info.value.message.lower()

    def test_create_payment_whitespace_reference_raises_error(self):
        """Should raise error when reference is only whitespace."""
        with pytest.raises(PaymentValidationError) as exc_info:
            Payment.create(
                reference="   ",
                amount=Decimal("100.00"),
                currency="MXN",
            )

        assert exc_info.value.code == "VALIDATION_ERROR"

    def test_create_payment_zero_amount_raises_error(self):
        """Should raise error when amount is zero."""
        with pytest.raises(PaymentValidationError) as exc_info:
            Payment.create(
                reference="FAC-12345",
                amount=Decimal("0"),
                currency="MXN",
            )

        assert exc_info.value.code == "VALIDATION_ERROR"
        assert "amount" in exc_info.value.message.lower()

    def test_create_payment_negative_amount_raises_error(self):
        """Should raise error when amount is negative."""
        with pytest.raises(PaymentValidationError) as exc_info:
            Payment.create(
                reference="FAC-12345",
                amount=Decimal("-100.00"),
                currency="MXN",
            )

        assert exc_info.value.code == "VALIDATION_ERROR"
        assert "amount" in exc_info.value.message.lower()

    def test_create_payment_invalid_currency_length_raises_error(self):
        """Should raise error when currency is not 3 characters."""
        with pytest.raises(PaymentValidationError) as exc_info:
            Payment.create(
                reference="FAC-12345",
                amount=Decimal("100.00"),
                currency="MXNN",
            )

        assert exc_info.value.code == "VALIDATION_ERROR"
        assert "currency" in exc_info.value.message.lower()

    def test_create_payment_short_currency_raises_error(self):
        """Should raise error when currency is too short."""
        with pytest.raises(PaymentValidationError) as exc_info:
            Payment.create(
                reference="FAC-12345",
                amount=Decimal("100.00"),
                currency="MX",
            )

        assert exc_info.value.code == "VALIDATION_ERROR"
        assert "currency" in exc_info.value.message.lower()


class TestPaymentStatus:
    """Tests for PaymentStatus enum."""

    def test_pending_is_not_final(self):
        """PENDING should not be a final status."""
        assert not PaymentStatus.PENDING.is_final()

    def test_success_is_final(self):
        """SUCCESS should be a final status."""
        assert PaymentStatus.SUCCESS.is_final()

    def test_failed_is_not_final(self):
        """FAILED should not be a final status."""
        assert not PaymentStatus.FAILED.is_final()

    def test_exhausted_is_final(self):
        """EXHAUSTED should be a final status."""
        assert PaymentStatus.EXHAUSTED.is_final()

    def test_only_failed_can_retry(self):
        """Only FAILED status should allow retry."""
        assert PaymentStatus.FAILED.can_retry()
        assert not PaymentStatus.PENDING.can_retry()
        assert not PaymentStatus.SUCCESS.can_retry()
        assert not PaymentStatus.EXHAUSTED.can_retry()


class TestPaymentCanRetry:
    """Tests for Payment.can_retry() method."""

    def test_failed_payment_can_retry(self, failed_payment):
        """FAILED payment with retries < 3 can retry."""
        assert failed_payment.can_retry()

    def test_failed_payment_max_retries_cannot_retry(self, failed_payment_max_retries):
        """FAILED payment with retries = 3 cannot retry."""
        assert not failed_payment_max_retries.can_retry()

    def test_success_payment_cannot_retry(self, success_payment):
        """SUCCESS payment cannot retry."""
        assert not success_payment.can_retry()

    def test_pending_payment_cannot_retry(self, sample_payment):
        """PENDING payment cannot retry."""
        assert not sample_payment.can_retry()

    def test_exhausted_payment_cannot_retry(self, exhausted_payment):
        """EXHAUSTED payment cannot retry."""
        assert not exhausted_payment.can_retry()


class TestPaymentIncrementRetries:
    """Tests for Payment.increment_retries() method."""

    def test_increment_retries_success(self, failed_payment):
        """Should increment retries for FAILED payment."""
        initial_retries = failed_payment.retries

        failed_payment.increment_retries()

        assert failed_payment.retries == initial_retries + 1

    def test_increment_retries_updates_timestamp(self, failed_payment):
        """Should update updated_at timestamp."""
        old_updated_at = failed_payment.updated_at

        failed_payment.increment_retries()

        assert failed_payment.updated_at > old_updated_at

    def test_increment_retries_non_failed_raises_error(self, success_payment):
        """Should raise error for non-FAILED payment."""
        with pytest.raises(CannotRetryPaymentError) as exc_info:
            success_payment.increment_retries()

        assert exc_info.value.code == "CANNOT_RETRY_PAYMENT"
        assert success_payment.payment_id in exc_info.value.message

    def test_increment_retries_max_reached_raises_error(self, failed_payment_max_retries):
        """Should raise error when max retries reached."""
        with pytest.raises(MaxRetriesExceededError) as exc_info:
            failed_payment_max_retries.increment_retries()

        assert exc_info.value.code == "MAX_RETRIES_EXCEEDED"


class TestPaymentMarkAs:
    """Tests for Payment status transition methods."""

    def test_mark_as_success(self, sample_payment):
        """Should transition to SUCCESS status."""
        sample_payment.mark_as_success()

        assert sample_payment.status == PaymentStatus.SUCCESS

    def test_mark_as_failed(self, sample_payment):
        """Should transition to FAILED status."""
        sample_payment.mark_as_failed()

        assert sample_payment.status == PaymentStatus.FAILED

    def test_mark_as_exhausted(self, failed_payment):
        """Should transition to EXHAUSTED status."""
        failed_payment.mark_as_exhausted()

        assert failed_payment.status == PaymentStatus.EXHAUSTED

    def test_mark_as_updates_timestamp(self, sample_payment):
        """Should update updated_at timestamp."""
        old_updated_at = sample_payment.updated_at

        sample_payment.mark_as_success()

        assert sample_payment.updated_at > old_updated_at


class TestPaymentProcessRetryResult:
    """Tests for Payment.process_retry_result() method."""

    def test_process_retry_success(self, failed_payment):
        """Should mark as SUCCESS when retry succeeds."""
        failed_payment.increment_retries()

        failed_payment.process_retry_result(success=True)

        assert failed_payment.status == PaymentStatus.SUCCESS

    def test_process_retry_failed_with_retries_remaining(self, failed_payment):
        """Should stay FAILED when retry fails but retries remain."""
        failed_payment.increment_retries()  # retries = 1

        failed_payment.process_retry_result(success=False)

        assert failed_payment.status == PaymentStatus.FAILED

    def test_process_retry_failed_exhausted(self, failed_payment):
        """Should mark as EXHAUSTED when final retry fails."""
        # Increment to max retries
        failed_payment._retries = 3

        failed_payment.process_retry_result(success=False)

        assert failed_payment.status == PaymentStatus.EXHAUSTED


class TestPaymentToDict:
    """Tests for Payment.to_dict() method."""

    def test_to_dict_contains_all_fields(self, sample_payment):
        """Should include all payment fields."""
        result = sample_payment.to_dict()

        assert "payment_id" in result
        assert "reference" in result
        assert "amount" in result
        assert "currency" in result
        assert "status" in result
        assert "retries" in result
        assert "created_at" in result
        assert "updated_at" in result

    def test_to_dict_amount_is_float(self, sample_payment):
        """Should convert amount to float."""
        result = sample_payment.to_dict()

        assert isinstance(result["amount"], float)

    def test_to_dict_status_is_string(self, sample_payment):
        """Should convert status to string value."""
        result = sample_payment.to_dict()

        assert result["status"] == "PENDING"


class TestPaymentEquality:
    """Tests for Payment equality."""

    def test_payments_equal_by_id(self):
        """Payments with same ID should be equal."""
        payment1 = Payment(
            payment_id="same-id",
            reference="REF-1",
            amount=Decimal("100"),
            currency="MXN",
            status=PaymentStatus.PENDING,
            retries=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        payment2 = Payment(
            payment_id="same-id",
            reference="REF-2",
            amount=Decimal("200"),
            currency="USD",
            status=PaymentStatus.SUCCESS,
            retries=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert payment1 == payment2

    def test_payments_not_equal_different_id(self):
        """Payments with different IDs should not be equal."""
        payment1 = Payment(
            payment_id="id-1",
            reference="REF-1",
            amount=Decimal("100"),
            currency="MXN",
            status=PaymentStatus.PENDING,
            retries=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        payment2 = Payment(
            payment_id="id-2",
            reference="REF-1",
            amount=Decimal("100"),
            currency="MXN",
            status=PaymentStatus.PENDING,
            retries=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert payment1 != payment2