from collections.abc import Generator, Iterable
from dataclasses import dataclass
from typing import TypeIs

import orjson

from jnav.node_path import NodePath, Segment


@dataclass(frozen=True)
class ExpandedString:
    original: str
    parsed: JsonValue


type JsonArray = list[JsonValue]
type JsonObject = dict[str, JsonValue]
type JsonValue = (
    JsonObject | JsonArray | str | int | float | bool | None | ExpandedString
)


def is_container(
    value: JsonValue,
) -> TypeIs[JsonObject | JsonArray | ExpandedString]:
    return isinstance(value, (dict, list, ExpandedString))


def children(value: JsonValue) -> Iterable[tuple[Segment, JsonValue]]:
    if isinstance(value, ExpandedString):
        value = value.parsed
    if isinstance(value, dict):
        return value.items()
    if isinstance(value, list):
        return enumerate(value)
    return ()


def walk(
    node: JsonValue,
    path: NodePath | None = None,
) -> Generator[tuple[JsonValue, NodePath]]:
    if path is None:
        path = NodePath()
    yield node, path
    for seg, child in children(node):
        yield from walk(child, path / seg)


def to_json(entry: JsonValue) -> str:
    def _json_default(obj: object) -> object:
        if isinstance(obj, ExpandedString):
            return obj.parsed
        raise TypeError(
            f"Object of type {obj.__class__.__name__} is not JSON serializable"
        )

    return orjson.dumps(
        entry,
        default=_json_default,
        option=orjson.OPT_PASSTHROUGH_DATACLASS,
    ).decode()
