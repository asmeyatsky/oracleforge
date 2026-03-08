"""OracleForge structured logging configuration.

Provides JSON-formatted log output with correlation IDs,
operation timing, and structured fields for observability.
"""

import logging
import json
import time
import uuid
import contextvars
from typing import Optional, Dict, Any
from functools import wraps

# Context variable for correlation ID (persists across async calls)
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set or generate a correlation ID for the current context."""
    cid = correlation_id or str(uuid.uuid4())[:8]
    correlation_id_var.set(cid)
    return cid


def get_correlation_id() -> str:
    """Get the current correlation ID."""
    return correlation_id_var.get()


class StructuredFormatter(logging.Formatter):
    """JSON log formatter with correlation ID and structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }

        # Add extra structured fields if present
        for key in ("module_name", "period", "org_id", "step", "duration_ms",
                     "table", "row_count", "dataset"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        if record.exc_info and record.exc_info[1]:
            log_entry["error"] = str(record.exc_info[1])
            log_entry["error_type"] = type(record.exc_info[1]).__name__

        return json.dumps(log_entry)


class TextFormatter(logging.Formatter):
    """Human-readable log formatter with correlation ID."""

    def format(self, record: logging.LogRecord) -> str:
        cid = get_correlation_id()
        prefix = f"[{cid}] " if cid else ""
        return f"{self.formatTime(record)} [{record.levelname}] {prefix}{record.name}: {record.getMessage()}"


def setup_logging(level: str = "INFO", format_type: str = "json",
                  log_file: Optional[str] = None) -> None:
    """Configure logging for the OracleForge application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        format_type: "json" for structured output, "text" for human-readable.
        log_file: Optional file path for log output.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    formatter = StructuredFormatter() if format_type == "json" else TextFormatter()

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def log_operation(operation: str, **fields):
    """Context manager / decorator for logging operation timing.

    Usage as decorator:
        @log_operation("extract_gl_journals", module="GL")
        async def extract(...): ...

    Usage as context manager:
        with log_operation("load_to_bq", table="gl_journals"):
            ...
    """
    class _OperationLogger:
        def __init__(self):
            self.logger = logging.getLogger("oracleforge.operations")
            self.start_time = None

        def __enter__(self):
            self.start_time = time.time()
            self.logger.info(
                f"Starting: {operation}",
                extra=fields,
            )
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            duration_ms = (time.time() - self.start_time) * 1000
            extra = {**fields, "duration_ms": round(duration_ms, 2)}
            if exc_type:
                self.logger.error(
                    f"Failed: {operation} ({duration_ms:.0f}ms)",
                    extra=extra,
                    exc_info=(exc_type, exc_val, exc_tb),
                )
            else:
                self.logger.info(
                    f"Completed: {operation} ({duration_ms:.0f}ms)",
                    extra=extra,
                )
            return False

        def __call__(self, func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self:
                    return await func(*args, **kwargs)

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self:
                    return func(*args, **kwargs)

            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

    return _OperationLogger()
