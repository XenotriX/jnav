import pytest

from jnav.field_mapping import RoleBinding, RoleMapping
from jnav.log_entry_item import render_summary
from jnav.parsing import parse_entry


def _message(line: str, expression: str) -> str:
    parsed = parse_entry(line)
    assert parsed is not None
    mapping = RoleMapping(message=RoleBinding(expression=expression))
    return render_summary(parsed, mapping).plain.removeprefix(" ")


class TestRenderSummaryMessage:
    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ('"plain text"', "plain text"),
            ("42", "42"),
            ("1.5", "1.5"),
            ("true", "true"),
            ("false", "false"),
            ("null", "null"),
            ('[1, "x", null]', '[1,"x",null]'),
            ("[]", "[]"),
        ],
    )
    def test_whole_non_object_entry_renders_as_json(
        self, line: str, expected: str
    ) -> None:
        assert _message(line, ".") == expected

    def test_whole_object_entry_renders_as_compact_json(self) -> None:
        assert _message('{"a": true, "b": null}', ".") == '{"a":true,"b":null}'

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ('{"a": 1}', '{"a":1}'),
            ("[1, true, null]", "[1,true,null]"),
            ("{}", "{}"),
            ("false", "false"),
            ("0", "0"),
            ("null", "null"),
        ],
    )
    def test_message_field_renders_as_json(self, value: str, expected: str) -> None:
        assert _message(f'{{"message": {value}}}', ".message") == expected

    def test_message_string_renders_verbatim(self) -> None:
        assert _message('{"message": "hi"}', ".message") == "hi"

    def test_empty_message_string_renders_blank(self) -> None:
        assert _message('{"message": ""}', ".message") == ""

    def test_missing_message_field_renders_null(self) -> None:
        assert _message('{"other": 1}', ".message") == "null"

    @pytest.mark.parametrize("line", ["42", '"s"', "[1, 2]", "null"])
    def test_message_field_of_non_object_entry_renders_null(self, line: str) -> None:
        assert _message(line, ".message") == "null"

    def test_multiline_message_joins_lines_with_marker(self) -> None:
        assert _message('{"message": "a\\nb"}', ".message") == "a↵ b"

    def test_multiple_results_render_as_json_array(self) -> None:
        line = '{"items": [{"m": "x"}, {"m": 2}]}'
        assert _message(line, ".items[].m") == '["x",2]'
