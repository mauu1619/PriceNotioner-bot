import sys

from loguru import logger

from src.core.config import settings


def setup_logging():
    logger.remove()
    if settings.LOG_FORMAT.lower() == "json":
        # Structured JSON logging
        logger.add(sys.stdout, serialize=True)
    else:
        # Beautiful text logging for development with forced colorize
        logger.add(
            sys.stdout,
            colorize=True,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>",
        )
