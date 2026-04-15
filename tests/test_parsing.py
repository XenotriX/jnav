import json

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

    def test_basic_entry_has_no_expanded_paths(self) -> None:
        result = parse_entry('{"level": "INFO", "message": "hello"}')
        assert result is not None
        assert result.expanded == {"level": "INFO", "message": "hello"}
        assert result.expanded_paths == set()

    def test_nested_json_string_expanded(self) -> None:
        inner = json.dumps({"a": 1, "b": 2})
        result = parse_entry(json.dumps({"data": inner}))
        assert result is not None
        assert result.expanded["data"] == {"a": 1, "b": 2}
        assert "data" in result.expanded_paths

    def test_non_json_string_left_alone(self) -> None:
        result = parse_entry('{"msg": "plain text"}')
        assert result is not None
        assert result.expanded["msg"] == "plain text"
        assert result.expanded_paths == set()

    def test_empty_json_string_not_expanded(self) -> None:
        result = parse_entry('{"a": "{}", "b": "[]"}')
        assert result is not None
        assert result.expanded == {"a": "{}", "b": "[]"}
        assert result.expanded_paths == set()
