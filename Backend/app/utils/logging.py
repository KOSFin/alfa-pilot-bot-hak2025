"""Central logging configuration utilities."""
from __future__ import annotations

import logging
from logging.config import dictConfig


def setup_logging(level: int = logging.INFO) -> None:
    """Configure application-wide logging."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "rich": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "rich",
                    "level": level,
                }
            },
            "loggers": {
                "": {
                    "handlers": ["console"],
                    "level": level,
                }
            },
        }
    )
