"""Logging configuration helper."""
from __future__ import annotations

import logging
import sys

from loguru import logger

_LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"


def configure_logging(debug: bool = False) -> None:
    """Configure global logging format and bridge stdlib logging to loguru."""
    logger.remove()
    logger.add(sys.stdout, level="DEBUG" if debug else "INFO", format=_LOG_FORMAT)

    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - bridge
            logger_opt = logger.opt(depth=6, exception=record.exc_info)
            logger_opt.log(record.levelname, record.getMessage())

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
