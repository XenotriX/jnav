import json

from jnav.parsing import ParsedEntry, parse_line, preprocess_entry


class TestParseLine:
    def test_valid_json_object(self) -> None:
        result = parse_line('{"key": "value"}')
        assert result.is_ok()
        assert result.ok == {"key": "value"}

    def test_invalid_json(self) -> None:
        result = parse_line("not json")
        assert result.is_error()

    def test_empty_line(self) -> None:
        result = parse_line("")
        assert result.is_error()

    def test_json_array_rejected(self) -> None:
        result = parse_line("[1, 2, 3]")
        assert result.is_error()

    def test_whitespace_stripped(self) -> None:
        result = parse_line('  {"a": 1}  \n')
        assert result.is_ok()
        assert result.ok == {"a": 1}


class TestPreprocessEntry:
    def test_basic_entry(self) -> None:
        entry = {"level": "INFO", "message": "hello"}
        parsed = preprocess_entry(entry)
        assert isinstance(parsed, ParsedEntry)
        assert parsed.raw is entry
        assert parsed.expanded == entry
        assert parsed.expanded_paths == set()

    def test_nested_json_string_expanded(self) -> None:
        inner = json.dumps({"a": 1, "b": 2})
        entry = {"data": inner}
        parsed = preprocess_entry(entry)
        assert parsed.expanded["data"] == {"a": 1, "b": 2}
        assert "data" in parsed.expanded_paths

    def test_non_json_string_left_alone(self) -> None:
        entry = {"msg": "plain text"}
        parsed = preprocess_entry(entry)
        assert parsed.expanded["msg"] == "plain text"
