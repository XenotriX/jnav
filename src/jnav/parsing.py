from dataclasses import dataclass, field
from typing import Any, cast

import orjson


@dataclass
class ParsedEntry:
    raw: str
    expanded: dict[str, Any]
    expanded_paths: set[str] = field(default_factory=set)


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
    expanded_paths: set[str] = set()
    _expand_in_place(
        parsed,
        path="",
        expanded_paths=expanded_paths,
    )
    return ParsedEntry(
        raw=stripped,
        expanded=parsed,
        expanded_paths=expanded_paths,
    )


def _expand_in_place(
    obj: dict[str, Any] | list[Any],
    *,
    path: str,
    expanded_paths: set[str],
) -> None:
    """Recursively replace JSON-encoded string values with their parsed
    objects, mutating dicts and lists in place."""
    match obj:
        case dict():
            for k, v in obj.items():
                _expand_slot(
                    obj,
                    key=k,
                    value=v,
                    child_path=f"{path}.{k}" if path else k,
                    expanded_paths=expanded_paths,
                )
        case list():
            for i, v in enumerate(obj):
                _expand_slot(
                    obj,
                    key=i,
                    value=v,
                    child_path=f"{path}[{i}]",
                    expanded_paths=expanded_paths,
                )


def _expand_slot(
    container: dict[str, Any] | list[Any],
    *,
    key: str | int,
    value: object,
    child_path: str,
    expanded_paths: set[str],
) -> None:
    # If the value is a string, try to parse it as JSON
    if isinstance(value, str):
        parsed = _try_parse_json(value)
        if parsed is not None:
            container[key] = parsed  # pyright: ignore[reportArgumentType, reportCallIssue]
            expanded_paths.add(child_path)
            value = parsed

    # If the value is now a dict or list, recursively expand it
    if isinstance(value, (dict, list)):
        value = cast(dict[str, Any] | list[Any], value)
        _expand_in_place(
            value,
            path=child_path,
            expanded_paths=expanded_paths,
        )


def _try_parse_json(value: str) -> dict[str, Any] | list[Any] | None:
    if not value or value[0] not in ("{", "["):
        return None
    try:
        parsed = orjson.loads(value)
    except orjson.JSONDecodeError, ValueError:
        return None
    if isinstance(parsed, (dict, list)) and len(parsed) > 0:
        return cast(dict[str, Any] | list[Any], parsed)
    return None
