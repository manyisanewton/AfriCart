from __future__ import annotations

import json
import logging
import logging.handlers
from pathlib import Path

from flask import current_app


LOGGER_NAME = "app.mpesa"


def get_mpesa_logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if getattr(logger, "_techhive_configured", False):
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    log_dir = Path(current_app.config["MPESA_LOG_DIR"])
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / current_app.config["MPESA_LOG_FILE"]

    handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=current_app.config["MPESA_LOG_MAX_BYTES"],
        backupCount=current_app.config["MPESA_LOG_BACKUP_COUNT"],
        encoding="utf-8",
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger._techhive_configured = True  # type: ignore[attr-defined]
    logger._techhive_log_path = str(log_path)  # type: ignore[attr-defined]
    return logger


def log_mpesa_debug(message: str, payload: dict | None = None) -> None:
    logger = get_mpesa_logger()
    if payload is None:
        logger.debug(message)
        return
    logger.debug("%s: %s", message, payload)


def log_mpesa_error(message: str, error: Exception | str, payload: dict | None = None) -> None:
    logger = get_mpesa_logger()
    if payload is None:
        logger.error("%s: %s", message, error)
        return
    logger.error("%s: %s | context=%s", message, error, payload)


def tail_mpesa_logs(limit: int = 100) -> dict:
    logger = get_mpesa_logger()
    log_path = Path(getattr(logger, "_techhive_log_path", Path(current_app.config["MPESA_LOG_DIR"]) / current_app.config["MPESA_LOG_FILE"]))
    if not log_path.exists():
        return {
            "path": str(log_path),
            "exists": False,
            "lines": [],
            "line_count": 0,
        }

    lines = log_path.read_text(encoding="utf-8").splitlines()
    if limit > 0:
        lines = lines[-limit:]
    return {
        "path": str(log_path),
        "exists": True,
        "lines": lines,
        "line_count": len(lines),
    }


def compact_payload(payload: dict | None) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload, sort_keys=True)
