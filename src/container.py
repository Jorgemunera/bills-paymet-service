"""Dependency injection container."""

from src.config.settings import get_settings
from src.shared.utils.logger import Logger
from src.shared.infrastructure.database.sqlite import SQLiteConnection
from src.shared.infrastructure.cache.redis_client import RedisClient

from src.modules.payments.domain.repository import PaymentRepository
from src.modules.payments.application.ports.payment_processor import PaymentProcessor
from src.modules.payments.application.ports.idempotency_service import IdempotencyService

from src.modules.payments.application.use_cases import (
    CreatePaymentUseCase,
    GetPaymentUseCase,
    RetryPaymentUseCase,
    ListPaymentsUseCase,
)

from src.modules.payments.infrastructure.persistence import SQLitePaymentRepository
from src.modules.payments.infrastructure.services import (
    SimulatedPaymentProcessor,
    RedisIdempotencyService,
)
from src.modules.payments.infrastructure.http import (
    PaymentController,
    create_payment_routes,
)

logger = Logger("CONTAINER")


class Container:
    """
    Dependency injection container.

    Manages the creation and wiring of all application dependencies.
    Implements a simple form of dependency injection without external libraries.
    """

    def __init__(self) -> None:
        """Initialize container."""
        self._instances: dict = {}
        self._initialized = False
        self._settings = get_settings()

    def initialize(self) -> None:
        """
        Initialize all dependencies.

        Creates instances in the correct order based on dependencies.
        """
        if self._initialized:
            logger.warning("Container already initialized")
            return

        logger.info("Initializing dependency container...")

        # ============================================
        # INFRASTRUCTURE - Shared
        # ============================================
        logger.info("Creating shared infrastructure...")

        self._instances["sqlite_connection"] = SQLiteConnection.get_instance()
        self._instances["redis_client"] = RedisClient.get_instance()

        # ============================================
        # INFRASTRUCTURE - Repositories
        # ============================================
        logger.info("Creating repositories...")

        self._instances["payment_repository"] = SQLitePaymentRepository(
            connection=self._instances["sqlite_connection"],
        )

        # ============================================
        # INFRASTRUCTURE - Services
        # ============================================
        logger.info("Creating services...")

        self._instances["payment_processor"] = SimulatedPaymentProcessor()

        self._instances["idempotency_service"] = RedisIdempotencyService(
            redis_client=self._instances["redis_client"],
        )

        # ============================================
        # APPLICATION - Use Cases
        # ============================================
        logger.info("Creating use cases...")

        self._instances["create_payment_use_case"] = CreatePaymentUseCase(
            payment_repository=self._instances["payment_repository"],
            payment_processor=self._instances["payment_processor"],
            idempotency_service=self._instances["idempotency_service"],
        )

        self._instances["get_payment_use_case"] = GetPaymentUseCase(
            payment_repository=self._instances["payment_repository"],
        )

        self._instances["retry_payment_use_case"] = RetryPaymentUseCase(
            payment_repository=self._instances["payment_repository"],
            payment_processor=self._instances["payment_processor"],
        )

        self._instances["list_payments_use_case"] = ListPaymentsUseCase(
            payment_repository=self._instances["payment_repository"],
        )

        # ============================================
        # HTTP - Controllers
        # ============================================
        logger.info("Creating controllers...")

        self._instances["payment_controller"] = PaymentController(
            create_payment_use_case=self._instances["create_payment_use_case"],
            get_payment_use_case=self._instances["get_payment_use_case"],
            retry_payment_use_case=self._instances["retry_payment_use_case"],
            list_payments_use_case=self._instances["list_payments_use_case"],
        )

        # ============================================
        # HTTP - Routes
        # ============================================
        logger.info("Creating routes...")

        self._instances["payment_routes"] = create_payment_routes(
            controller=self._instances["payment_controller"],
        )

        self._initialized = True
        logger.info("Container initialized successfully")

    def get(self, name: str):
        """
        Get a dependency by name.

        Args:
            name: Dependency name

        Returns:
            The dependency instance

        Raises:
            RuntimeError: If container not initialized
            KeyError: If dependency not found
        """
        if not self._initialized:
            raise RuntimeError("Container not initialized. Call initialize() first.")

        if name not in self._instances:
            raise KeyError(f"Dependency not found: {name}")

        return self._instances[name]

    # ==================== Property Accessors ====================

    @property
    def sqlite_connection(self) -> SQLiteConnection:
        """Get SQLite connection."""
        return self.get("sqlite_connection")

    @property
    def redis_client(self) -> RedisClient:
        """Get Redis client."""
        return self.get("redis_client")

    @property
    def payment_repository(self) -> PaymentRepository:
        """Get payment repository."""
        return self.get("payment_repository")

    @property
    def payment_processor(self) -> PaymentProcessor:
        """Get payment processor."""
        return self.get("payment_processor")

    @property
    def idempotency_service(self) -> IdempotencyService:
        """Get idempotency service."""
        return self.get("idempotency_service")

    @property
    def create_payment_use_case(self) -> CreatePaymentUseCase:
        """Get create payment use case."""
        return self.get("create_payment_use_case")

    @property
    def get_payment_use_case(self) -> GetPaymentUseCase:
        """Get get payment use case."""
        return self.get("get_payment_use_case")

    @property
    def retry_payment_use_case(self) -> RetryPaymentUseCase:
        """Get retry payment use case."""
        return self.get("retry_payment_use_case")

    @property
    def list_payments_use_case(self) -> ListPaymentsUseCase:
        """Get list payments use case."""
        return self.get("list_payments_use_case")

    @property
    def payment_controller(self) -> PaymentController:
        """Get payment controller."""
        return self.get("payment_controller")

    @property
    def payment_routes(self):
        """Get payment routes."""
        return self.get("payment_routes")


# Global container instance (singleton)
container = Container()


def get_container() -> Container:
    """Get the global container instance."""
    return container