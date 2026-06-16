import logging
import re
import sys


class RedactingFilter(logging.Filter):
    _sensitive_key_pattern = re.compile(
        r"(?i)\b(api[_-]?key|authorization|token|secret|password|webhook_secret)\b"
        r"\s*[:=]\s*['\"]?[^'\"\s,}]+"
    )
    _bearer_pattern = re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+")
    _phone_pattern = re.compile(r"\b\d{8,15}\b")

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._redact(str(record.msg))
        if record.args:
            record.args = tuple(self._redact(str(arg)) for arg in record.args)
        return True

    def _redact(self, value: str) -> str:
        value = self._sensitive_key_pattern.sub(lambda m: f"{m.group(1)}=<redacted>", value)
        value = self._bearer_pattern.sub("Bearer <redacted>", value)
        return self._phone_pattern.sub("<phone>", value)


def setup_logging(level: str = "INFO") -> None:
    redacting_filter = RedactingFilter()
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(redacting_filter)

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[handler],
    )
    logging.getLogger().addFilter(redacting_filter)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
