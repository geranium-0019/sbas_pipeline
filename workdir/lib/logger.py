"""Logger configuration for the pipeline."""

import logging
import sys
from pathlib import Path

from lib.utils import ensure_dir


def setup_logger(logs_dir: Path) -> logging.Logger:
    """Set up and return a configured logger."""
    ensure_dir(logs_dir)
    log_file = logs_dir / "pipeline.log"

    logger = logging.getLogger("pipeline")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger
