from __future__ import annotations

import logging
import sys
from pathlib import Path

from app.config import LOG_DIR


def setup_logging() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "app_error.log"

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "") == str(log_path) for h in root.handlers):
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        root.addHandler(fh)

    def _excepthook(exc_type, exc_value, exc_traceback):
        logging.getLogger("app.unhandled").exception("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = _excepthook
    return log_path
