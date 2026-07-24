"""Structured JSON logging for external monitoring systems (Grafana, Loki, ELK).

Usage:
    from handlers.json_logger import json_logger
    json_logger.info("provider_status", provider="gemini", status="429", latency=913)

Logs are written to bot_data/logs/ directory as JSONL files.
Also supports console output in JSON format when JSON_LOGS=true env var is set.
"""
import json
import logging
import os
from datetime import datetime, timezone

_JSON_DIR = None


def _ensure_dir() -> str:
    global _JSON_DIR
    if _JSON_DIR:
        return _JSON_DIR
    candidates = ["/data/logs", "/app/logs", "logs"]
    for d in candidates:
        try:
            os.makedirs(d, exist_ok=True)
            testf = os.path.join(d, ".write_test")
            with open(testf, "w") as f:
                f.write("ok")
            os.remove(testf)
            _JSON_DIR = d
            return d
        except:
            continue
    _JSON_DIR = "logs"
    os.makedirs(_JSON_DIR, exist_ok=True)
    return _JSON_DIR


class JsonLogger:
    def __init__(self):
        self._console = os.environ.get("JSON_LOGS", "").lower() in ("1", "true", "yes")
        self._log_dir = _ensure_dir()

    def _log(self, level: str, event: str, **kwargs):
        record = {
            "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": level,
            "event": event,
            **kwargs,
        }
        line = json.dumps(record, ensure_ascii=False, default=str)

        if self._console:
            print(line, flush=True)

        try:
            date = datetime.now().strftime("%Y-%m-%d")
            path = os.path.join(self._log_dir, f"{date}.jsonl")
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except:
            pass

    def info(self, event: str, **kwargs):
        self._log("INFO", event, **kwargs)

    def warn(self, event: str, **kwargs):
        self._log("WARN", event, **kwargs)

    def error(self, event: str, **kwargs):
        self._log("ERROR", event, **kwargs)

    def debug(self, event: str, **kwargs):
        self._log("DEBUG", event, **kwargs)


json_logger = JsonLogger()
