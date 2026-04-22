from dataclasses import dataclass
from typing import Any, cast

import orjson

from jnav.json_model import ExpandedString, JsonValue


@dataclass
class ParsedEntry:
    raw: str
    expanded: JsonValue


def parse_entry(line: str) -> ParsedEntry | None:
    """Parse a JSON line into a ``ParsedEntry`` with nested JSON-encoded
    strings expanded in place. Returns ``None`` for blank lines, invalid
    JSON, and JSON that isn't an object."""
    stripped = line.strip()
    if not stripped:
        return None
    parsed = _try_parse_json(stripped)
    if not isinstance(parsed, dict):
        return None
    expanded = expand(parsed)
    return ParsedEntry(
        raw=stripped,
        expanded=expanded,
    )


def expand(value: JsonValue) -> JsonValue:
    """Recursively expand JSON-encoded strings in a JSON value."""
    if isinstance(value, dict):
        return {k: expand(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [expand(v) for v in value]
    elif isinstance(value, str):
        parsed = _try_parse_json(value)
        if parsed is not None:
            return ExpandedString(original=value, parsed=expand(parsed))
        return value
    else:
        return value


def _try_parse_json(value: str) -> dict[str, Any] | list[Any] | None:
    if not value or value[0] not in ("{", "["):
        return None
    try:
        parsed = orjson.loads(value)
    except orjson.JSONDecodeError, ValueError:
        return None
    if isinstance(parsed, (dict, list)) and parsed:
        return cast(dict[str, Any] | list[Any], parsed)
    return None
