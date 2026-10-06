from datetime import datetime
from typing import Literal

from pydantic import BaseModel

TimestampFormat = Literal["iso8601", "epoch_s", "epoch_ms", "epoch_us", "epoch_ns"]


BindingSource = Literal["fallback", "format", "user"]


class RoleBinding(BaseModel):
    expression: str


class TimeRoleBinding(RoleBinding):
    format: TimestampFormat


class RoleMapping(BaseModel):
    timestamp: TimeRoleBinding | None = None
    level: RoleBinding | None = None
    message: RoleBinding | None = None

    def get(self, name: str) -> RoleBinding | None:
        return dict(self).get(name)


def detect_timestamp_format(value: object) -> TimestampFormat | None:
    if isinstance(value, str) and value:
        try:
            _ = datetime.fromisoformat(value)
            return "iso8601"
        except ValueError:
            return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _epoch_format_from_magnitude(float(value))
    return None


def _epoch_format_from_magnitude(value: float) -> TimestampFormat:
    magnitude = abs(value)
    if magnitude < 1e11:
        return "epoch_s"
    if magnitude < 1e14:
        return "epoch_ms"
    if magnitude < 1e17:
        return "epoch_us"
    return "epoch_ns"
