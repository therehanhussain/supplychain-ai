"""Structured JSON Logging Configuration.

Provides lightweight structured logging with secret masking, request ID correlation,
and standard level formatting.
"""

import json
import logging
import re
import sys
from datetime import datetime
from typing import Any, Dict

# Patterns for masking sensitive fields in logs
SENSITIVE_KEYS = re.compile(
    r"(password|secret|token|api_key|authorization|bearer|cookie|access_token)",
    re.IGNORECASE,
)


class JsonFormatter(logging.Formatter):
    """Custom formatter outputting single-line JSON log entries."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include request_id if available on record
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        # Include latency if available
        if hasattr(record, "latency_ms"):
            log_entry["latency_ms"] = record.latency_ms

        # Include exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Sanitize any sensitive tokens in the JSON
        serialized = json.dumps(log_entry, ensure_ascii=False)
        return self._mask_sensitive(serialized)

    def _mask_sensitive(self, text: str) -> str:
        """Mask common sensitive patterns in log messages."""
        # Mask Bearer tokens
        text = re.sub(r"(Bearer\s+)[A-Za-z0-9\-_\.]+", r"\1[MASKED]", text, flags=re.IGNORECASE)
        # Mask key-value patterns
        text = re.sub(
            r'("(?:api_key|password|secret|token)"\s*:\s*")[^"]+(")',
            r'\1[MASKED]\2',
            text,
            flags=re.IGNORECASE,
        )
        return text


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Configure and return the root application logger."""
    root_logger = logging.getLogger("supplychain")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        root_logger.addHandler(handler)

    # Avoid duplicate logs propagating to root
    root_logger.propagate = False
    return root_logger


logger = configure_logging()
