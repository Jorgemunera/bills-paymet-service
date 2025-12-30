"""Application entry point."""

import uvicorn

from src.config.settings import get_settings
from src.shared.infrastructure.http.server import create_app
from src.shared.utils.logger import Logger

logger = Logger("MAIN")

# Create application instance
app = create_app()


if __name__ == "__main__":
    settings = get_settings()

    logger.info("=" * 60)
    logger.info("🚀 PAYMENT SERVICE")
    logger.info("=" * 60)
    logger.info(f"   Environment: {settings.environment}")
    logger.info(f"   Host:        {settings.host}")
    logger.info(f"   Port:        {settings.port}")
    logger.info(f"   Debug:       {settings.debug}")
    logger.info("=" * 60)

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_level="info" if settings.debug else "warning",
    )