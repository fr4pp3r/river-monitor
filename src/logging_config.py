from pathlib import Path
import sys

from loguru import logger

from src.settings import settings


def setup_logging() -> None:
    logger.remove()

    logger.add(
        sys.stdout,
        level="INFO" if not settings.app_debug else "DEBUG",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    logger.add(
        log_dir / "river-monitor-{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        compression="gz",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    logger.info(f"Logging initialized | env={settings.app_env}")
