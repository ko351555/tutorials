"""Structured JSON logging: stdout + logs/<project_id>.log."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import structlog

from ystick.config import PROJECT_ROOT


def configure_logging(project_id: str | None = None) -> structlog.stdlib.BoundLogger:
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if project_id:
        file_handler = logging.FileHandler(log_dir / f"{project_id}.log")
        handlers.append(file_handler)

    logging.basicConfig(format="%(message)s", level=logging.INFO, handlers=handlers, force=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    log = structlog.get_logger()
    if project_id:
        structlog.contextvars.bind_contextvars(project_id=project_id)
    return log
