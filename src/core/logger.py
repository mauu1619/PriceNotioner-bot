import sys
from pathlib import Path

from loguru import logger

from src.core.config import settings


def setup_logging():
    logger.remove()

    log_format = settings.LOG_FORMAT.lower()

    if log_format == "json":
        # 1. Stdout JSON logging (good for Docker/Kubernetes)
        logger.add(sys.stdout, serialize=True)

        # 2. File JSON logging
        log_dir = Path(settings.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_dir / "app.json.log",
            serialize=True,
            rotation="500 MB",
            retention="10 days",
            compression="zip",
            level="INFO",
        )
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
