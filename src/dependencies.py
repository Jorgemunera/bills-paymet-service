"""FastAPI dependency injection functions."""

from functools import lru_cache
from typing import Annotated, AsyncGenerator

from fastapi import Depends

from src.config.settings import Settings, get_settings
from src.shared.infrastructure.database.sqlite import SQLiteConnection
from src.shared.infrastructure.cache.redis_client import RedisClient

from src.modules.payments.domain.repository import PaymentRepository
from src.modules.payments.application.ports.payment_processor import PaymentProcessor
from src.modules.payments.application.ports.idempotency_service import IdempotencyService

from src.modules.payments.infrastructure.persistence.sqlite_payment_repository import (
    SQLitePaymentRepository,
)
from src.modules.payments.infrastructure.services.simulated_payment_processor import (
    SimulatedPaymentProcessor,
)
from src.modules.payments.infrastructure.services.redis_idempotency_service import (
    RedisIdempotencyService,
)

from src.modules.payments.application.use_cases.create_payment import CreatePaymentUseCase
from src.modules.payments.application.use_cases.get_payment import GetPaymentUseCase
from src.modules.payments.application.use_cases.retry_payment import RetryPaymentUseCase
from src.modules.payments.application.use_cases.list_payments import ListPaymentsUseCase


# ============================================
# SETTINGS
# ============================================

def get_settings_dependency() -> Settings:
    """Get application settings."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_settings_dependency)]


# ============================================
# INFRASTRUCTURE - Database
# ============================================

@lru_cache
def get_sqlite_connection() -> SQLiteConnection:
    """Get SQLite connection singleton."""
    return SQLiteConnection.get_instance()


SQLiteConnectionDep = Annotated[SQLiteConnection, Depends(get_sqlite_connection)]


# ============================================
# INFRASTRUCTURE - Cache
# ============================================

@lru_cache
def get_redis_client() -> RedisClient:
    """Get Redis client singleton."""
    return RedisClient.get_instance()


RedisClientDep = Annotated[RedisClient, Depends(get_redis_client)]


# ============================================
# REPOSITORIES
# ============================================

def get_payment_repository(
    connection: SQLiteConnectionDep,
) -> PaymentRepository:
    """Get payment repository."""
    return SQLitePaymentRepository(connection=connection)


PaymentRepositoryDep = Annotated[PaymentRepository, Depends(get_payment_repository)]


# ============================================
# SERVICES
# ============================================

def get_payment_processor() -> PaymentProcessor:
    """Get payment processor."""
    return SimulatedPaymentProcessor()


PaymentProcessorDep = Annotated[PaymentProcessor, Depends(get_payment_processor)]


def get_idempotency_service(
    redis_client: RedisClientDep,
) -> IdempotencyService:
    """Get idempotency service."""
    return RedisIdempotencyService(redis_client=redis_client)


IdempotencyServiceDep = Annotated[IdempotencyService, Depends(get_idempotency_service)]


# ============================================
# USE CASES
# ============================================

def get_create_payment_use_case(
    payment_repository: PaymentRepositoryDep,
    payment_processor: PaymentProcessorDep,
    idempotency_service: IdempotencyServiceDep,
) -> CreatePaymentUseCase:
    """Get create payment use case."""
    return CreatePaymentUseCase(
        payment_repository=payment_repository,
        payment_processor=payment_processor,
        idempotency_service=idempotency_service,
    )


CreatePaymentUseCaseDep = Annotated[CreatePaymentUseCase, Depends(get_create_payment_use_case)]


def get_get_payment_use_case(
    payment_repository: PaymentRepositoryDep,
) -> GetPaymentUseCase:
    """Get get payment use case."""
    return GetPaymentUseCase(payment_repository=payment_repository)


GetPaymentUseCaseDep = Annotated[GetPaymentUseCase, Depends(get_get_payment_use_case)]


def get_retry_payment_use_case(
    payment_repository: PaymentRepositoryDep,
    payment_processor: PaymentProcessorDep,
) -> RetryPaymentUseCase:
    """Get retry payment use case."""
    return RetryPaymentUseCase(
        payment_repository=payment_repository,
        payment_processor=payment_processor,
    )


RetryPaymentUseCaseDep = Annotated[RetryPaymentUseCase, Depends(get_retry_payment_use_case)]


def get_list_payments_use_case(
    payment_repository: PaymentRepositoryDep,
) -> ListPaymentsUseCase:
    """Get list payments use case."""
    return ListPaymentsUseCase(payment_repository=payment_repository)


ListPaymentsUseCaseDep = Annotated[ListPaymentsUseCase, Depends(get_list_payments_use_case)]