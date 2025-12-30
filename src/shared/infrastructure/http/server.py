"""FastAPI application factory."""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import get_settings
from src.shared.infrastructure.http.error_handlers import setup_error_handlers
from src.shared.infrastructure.http.middlewares import LoggingMiddleware
from src.shared.infrastructure.database.sqlite import SQLiteConnection
from src.shared.infrastructure.cache.redis_client import RedisClient
from src.shared.utils.logger import Logger

logger = Logger("HTTP:SERVER")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("=" * 60)
    logger.info("🚀 STARTING PAYMENT SERVICE")
    logger.info("=" * 60)

    # Get infrastructure instances
    sqlite_connection = SQLiteConnection.get_instance()
    redis_client = RedisClient.get_instance()

    # Connect to databases
    await sqlite_connection.connect()
    await redis_client.connect()

    settings = get_settings()
    logger.info("Service started successfully", extra={
        "host": settings.host,
        "port": settings.port,
        "environment": settings.environment,
    })

    yield

    # Shutdown
    logger.info("Shutting down...")
    await sqlite_connection.disconnect()
    await redis_client.disconnect()
    logger.info("Service stopped")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application
    """
    settings = get_settings()

    app = FastAPI(
        title="Payment Service",
        description="""
        Payment processing service with idempotency support.

        ## Features

        - **Payment Creation**: Create new payments with idempotency guarantees
        - **Payment Retrieval**: Get payment details by ID
        - **Payment Retry**: Retry failed payments (max 3 attempts)
        - **Payment Listing**: List payments with filtering and pagination

        ## Business Rules

        - Payments with amount ≤ 1000 succeed immediately
        - Payments with amount > 1000 fail and can be retried
        - Each retry has a 50% chance of success
        - After 3 failed retries, payment status becomes EXHAUSTED
        """,
        version=settings.app_version,
        lifespan=lifespan,
    )

    # Add middlewares
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup error handlers
    setup_error_handlers(app)

    # Register routes
    from src.modules.payments.infrastructure.http.routes import router as payment_router
    app.include_router(payment_router)

    # Health check endpoint
    @app.get(
        "/health",
        tags=["Health"],
        summary="Health check",
        description="Check the health status of the service and its dependencies.",
    )
    async def health_check():
        """Check service health."""
        sqlite_connection = SQLiteConnection.get_instance()
        redis_client = RedisClient.get_instance()

        db_health = await sqlite_connection.health_check()
        redis_health = await redis_client.health_check()

        is_healthy = (
            db_health["status"] == "healthy" and
            redis_health["status"] == "healthy"
        )

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": db_health,
                "redis": redis_health,
            },
        }

    return app