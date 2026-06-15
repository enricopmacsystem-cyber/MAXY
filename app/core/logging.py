import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO") -> None:
    """Configura il logging globale dell'applicazione."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.setLevel(numeric_level)
        return

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger.setLevel(numeric_level)
    root_logger.addHandler(handler)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or "tech-assistant")
