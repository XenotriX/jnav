import logging
from datetime import UTC, datetime
from logging import FileHandler
from typing import override

from pythonjsonlogger.core import LogData
from pythonjsonlogger.json import JsonFormatter


class HLJsonFormatter(JsonFormatter):
    @override
    def process_log_record(self, log_data: LogData) -> LogData:
        log_data = super().process_log_record(log_data)
        log_data["caller"] = f"{log_data['filename']}:{log_data['lineno']}"
        log_data.pop("filename", None)
        log_data.pop("lineno", None)
        log_data.pop("funcName", None)
        if log_data.get("exc_info") is None:
            log_data.pop("exc_info", None)
        log_data["ts"] = datetime.fromtimestamp(log_data["created"], tz=UTC).isoformat()
        log_data.pop("created", None)
        return log_data


def init_logging() -> None:
    file_handler = FileHandler("jnav.log", mode="a", encoding="utf-8")
    file_handler.setFormatter(
        HLJsonFormatter(
            [
                "message",
                "levelname",
                "filename",
                "lineno",
                "funcName",
                "name",
                "exc_info",
                "caller",
                "created",
            ],
            rename_fields={
                "levelname": "level",
                "name": "logger",
            },
        )
    )
    file_handler.setLevel(logging.DEBUG)

    logging.basicConfig(
        level=logging.NOTSET,
        format="%(message)s",
        handlers=[file_handler],
    )
