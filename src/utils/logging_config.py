"""
FIN SIGHT AI - Logging Configuration
Provides a consistent logging setup across all modules.
"""
import logging
import sys
from pathlib import Path
from src.utils.config import LOG_LEVEL, BASE_DIR

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_datefmt = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """
    Return a configured logger for the given module name.
    Logs go to both the console and a rotating log file.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # already configured

    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Console handler
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    ch.setFormatter(logging.Formatter(_fmt, datefmt=_datefmt))
    logger.addHandler(ch)

    # File handler
    fh = logging.FileHandler(LOG_DIR / "fin_sight_ai.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(_fmt, datefmt=_datefmt))
    logger.addHandler(fh)

    logger.propagate = False
    return logger
