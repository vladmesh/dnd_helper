import json
import logging
import os
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        service = getattr(record, "service", None)
        if service:
            base["service"] = service
        corr = getattr(record, "correlation_id", None)
        if corr:
            base["correlation_id"] = corr
        # Include exception details if present
        if record.exc_info:
            try:
                base["exception_type"] = record.exc_info[0].__name__ if record.exc_info and record.exc_info[0] else None
                base["exception_message"] = str(record.exc_info[1]) if record.exc_info and record.exc_info[1] else None
                base["traceback"] = self.formatException(record.exc_info)
            except Exception:
                pass
        return json.dumps(base, ensure_ascii=False)


class HumanFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        service = getattr(record, "service", "-")
        corr = getattr(record, "correlation_id", "-")
        base = (
            f"{ts} | {record.levelname:<8} | {service} | {record.name} | "
            f"{record.getMessage()} | corr={corr}"
        )
        if record.exc_info:
            try:
                base += "\n" + self.formatException(record.exc_info)
            except Exception:
                pass
        return base


class ServiceFilter(logging.Filter):
    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "service"):
            record.service = self.service_name
        return True


def _safe_level(level_value: str) -> int:
    try:
        return getattr(logging, (level_value or "INFO").upper(), logging.INFO)
    except Exception:
        return logging.INFO


def configure_logging(
    service_name: str,
    json_enabled: bool | None = None,
    level_value: str | None = None,
) -> None:
    if json_enabled is None:
        json_enabled = os.getenv("LOG_JSON", "true").lower() in {"1", "true", "yes", "on"}
    if level_value is None:
        level_value = os.getenv("LOG_LEVEL", "INFO")
    level = _safe_level(level_value)

    root = logging.getLogger()
    # Clear existing handlers
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.addFilter(ServiceFilter(os.getenv("LOG_SERVICE_NAME", service_name)))
    handler.setFormatter(JsonFormatter() if json_enabled else HumanFormatter())

    root.addHandler(handler)
    root.setLevel(level)

    # Reduce verbosity of third-party noisy loggers
    for noisy in ("httpx",):
        logging.getLogger(noisy).setLevel(logging.WARNING)


