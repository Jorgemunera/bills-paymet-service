"""Pytest fixtures and configuration."""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.modules.payments.domain.payment import Payment
from src.modules.payments.domain.payment_status import PaymentStatus
from src.modules.payments.domain.repository import PaymentRepository
from src.modules.payments.application.ports.payment_processor import (
    PaymentProcessor,
    ProcessingResult,
)
from src.modules.payments.application.ports.idempotency_service import IdempotencyService


# ============================================
# PAYMENT FIXTURES
# ============================================

@pytest.fixture
def sample_payment() -> Payment:
    """Create a sample payment in PENDING status."""
    return Payment(
        payment_id="pay-123-456",
        reference="FAC-12345",
        amount=Decimal("500.00"),
        currency="MXN",
        status=PaymentStatus.PENDING,
        retries=0,
        created_at=datetime(2024, 1, 15, 10, 30, 0),
        updated_at=datetime(2024, 1, 15, 10, 30, 0),
    )


@pytest.fixture
def failed_payment() -> Payment:
    """Create a sample payment in FAILED status."""
    return Payment(
        payment_id="pay-789-012",
        reference="FAC-67890",
        amount=Decimal("1500.00"),
        currency="MXN",
        status=PaymentStatus.FAILED,
        retries=0,
        created_at=datetime(2024, 1, 15, 10, 30, 0),
        updated_at=datetime(2024, 1, 15, 10, 30, 0),
    )


@pytest.fixture
def success_payment() -> Payment:
    """Create a sample payment in SUCCESS status."""
    return Payment(
        payment_id="pay-success-123",
        reference="FAC-SUCCESS",
        amount=Decimal("500.00"),
        currency="MXN",
        status=PaymentStatus.SUCCESS,
        retries=0,
        created_at=datetime(2024, 1, 15, 10, 30, 0),
        updated_at=datetime(2024, 1, 15, 10, 30, 0),
    )


@pytest.fixture
def exhausted_payment() -> Payment:
    """Create a sample payment in EXHAUSTED status."""
    return Payment(
        payment_id="pay-exhausted-123",
        reference="FAC-EXHAUSTED",
        amount=Decimal("1500.00"),
        currency="MXN",
        status=PaymentStatus.EXHAUSTED,
        retries=3,
        created_at=datetime(2024, 1, 15, 10, 30, 0),
        updated_at=datetime(2024, 1, 15, 10, 30, 0),
    )


@pytest.fixture
def failed_payment_max_retries() -> Payment:
    """Create a FAILED payment with max retries reached."""
    return Payment(
        payment_id="pay-max-retries",
        reference="FAC-MAX",
        amount=Decimal("1500.00"),
        currency="MXN",
        status=PaymentStatus.FAILED,
        retries=3,
        created_at=datetime(2024, 1, 15, 10, 30, 0),
        updated_at=datetime(2024, 1, 15, 10, 30, 0),
    )


# ============================================
# MOCK FIXTURES
# ============================================

@pytest.fixture
def mock_payment_repository() -> AsyncMock:
    """Create a mock payment repository."""
    mock = AsyncMock(spec=PaymentRepository)
    mock.save = AsyncMock()
    mock.find_by_id = AsyncMock(return_value=None)
    mock.update = AsyncMock()
    mock.find_all = AsyncMock(return_value=[])
    mock.count = AsyncMock(return_value=0)
    return mock


@pytest.fixture
def mock_payment_processor() -> AsyncMock:
    """Create a mock payment processor."""
    mock = AsyncMock(spec=PaymentProcessor)
    mock.process = AsyncMock(
        return_value=ProcessingResult(success=True, message="Success")
    )
    mock.process_retry = AsyncMock(
        return_value=ProcessingResult(success=True, message="Retry success")
    )
    return mock


@pytest.fixture
def mock_idempotency_service() -> AsyncMock:
    """Create a mock idempotency service."""
    mock = AsyncMock(spec=IdempotencyService)
    mock.get_existing_result = AsyncMock(return_value=None)
    mock.save_result = AsyncMock()
    mock.acquire_lock = AsyncMock(return_value=True)
    mock.release_lock = AsyncMock()
    return mock