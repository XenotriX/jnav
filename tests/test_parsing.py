import json

from jnav.json_model import ExpandedString
from jnav.parsing import ParsedEntry, parse_entry


class TestParseEntry:
    def test_valid_json_object(self) -> None:
        result = parse_entry('{"key": "value"}')
        assert isinstance(result, ParsedEntry)
        assert result.expanded == {"key": "value"}
        assert result.raw == '{"key": "value"}'

    def test_invalid_json(self) -> None:
        assert parse_entry("not json") is None

    def test_empty_line(self) -> None:
        assert parse_entry("") is None

    def test_json_array_rejected(self) -> None:
        assert parse_entry("[1, 2, 3]") is None

    def test_whitespace_stripped(self) -> None:
        result = parse_entry('  {"a": 1}  \n')
        assert result is not None
        assert result.expanded == {"a": 1}
        assert result.raw == '{"a": 1}'

    def test_basic_entry_has_no_expanded_strings(self) -> None:
        result = parse_entry('{"level": "INFO", "message": "hello"}')
        assert result is not None
        assert result.expanded == {"level": "INFO", "message": "hello"}

    def test_nested_json_string_is_wrapped(self) -> None:
        inner = json.dumps({"a": 1, "b": 2})
        result = parse_entry(json.dumps({"data": inner}))
        assert result is not None
        assert isinstance(result.expanded, dict)
        data = result.expanded["data"]
        assert isinstance(data, ExpandedString)
        assert data.original == inner
        assert data.parsed == {"a": 1, "b": 2}

    def test_non_json_string_left_alone(self) -> None:
        result = parse_entry('{"msg": "plain text"}')
        assert result is not None
        assert isinstance(result.expanded, dict)
        assert result.expanded["msg"] == "plain text"

    def test_empty_json_string_not_expanded(self) -> None:
        result = parse_entry('{"a": "{}", "b": "[]"}')
        assert result is not None
        assert result.expanded == {"a": "{}", "b": "[]"}
