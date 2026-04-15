from dataclasses import dataclass, field

from rich.style import Style
from rich.text import Text

from jnav.tree_rendering import (
    DEFAULT_JSON_STRING_STYLE,
    DEFAULT_SEARCH_HIGHLIGHT_STYLE,
    DEFAULT_VALUE_NULL_STYLE,
    DEFAULT_VALUE_STYLE,
    TreeBuildVisitor,
    highlight_text,
    oneline,
    sorted_keys,
    walk_tree,
)


class TestSortedKeys:
    def test_priority_keys_come_first_in_canonical_order(self) -> None:
        keys = sorted_keys({"extra": 1, "level": "INFO", "zz": 0, "ts": 0})
        assert keys == ["ts", "level", "extra", "zz"]

    def test_non_priority_keys_keep_insertion_order(self) -> None:
        assert sorted_keys({"c": 1, "a": 2, "b": 3}) == ["c", "a", "b"]

    def test_all_priority_keys_present(self) -> None:
        d = {
            "msg": "",
            "message": "",
            "severity": "",
            "level": "",
            "time": 0,
            "ts": 0,
            "timestamp": 0,
        }
        assert sorted_keys(d) == [
            "timestamp",
            "ts",
            "time",
            "level",
            "severity",
            "message",
            "msg",
        ]

    def test_both_timestamp_and_ts_keep_canonical_order(self) -> None:
        assert sorted_keys({"ts": 1, "timestamp": 2}) == ["timestamp", "ts"]

    def test_empty_string_key_sorts_after_priority_keys(self) -> None:
        assert sorted_keys({"": 1, "ts": 0}) == ["ts", ""]

    def test_empty_dict(self) -> None:
        assert sorted_keys({}) == []


class TestOneline:
    def test_plain_string_unchanged(self) -> None:
        assert oneline("hello") == "hello"

    def test_newline_replaced_by_ellipsis(self) -> None:
        assert oneline("first\nsecond") == "first\u2026"

    def test_only_first_line_kept(self) -> None:
        assert oneline("a\nb\nc") == "a\u2026"

    def test_leading_newline(self) -> None:
        assert oneline("\nrest") == "\u2026"

    def test_non_string_stringified(self) -> None:
        assert oneline(42) == "42"
        assert oneline(None) == "None"
        assert oneline(True) == "True"

    def test_tuple_stringified(self) -> None:
        assert oneline((1, 2)) == "(1, 2)"


class TestHighlightText:
    def test_no_term_returns_same_object(self) -> None:
        text = Text("hello")
        assert highlight_text(text, None) is text

    def test_empty_term_returns_same_object(self) -> None:
        text = Text("hello")
        assert highlight_text(text, "") is text

    def test_single_match_is_styled(self) -> None:
        text = Text("hello world")
        highlight_text(text, "world", style="red")
        spans = [(s.start, s.end, str(s.style)) for s in text.spans]
        assert spans == [(6, 11, "red")]

    def test_match_is_case_insensitive(self) -> None:
        text = Text("Hello WORLD")
        highlight_text(text, "world", style="red")
        spans = [(s.start, s.end) for s in text.spans]
        assert spans == [(6, 11)]

    def test_multiple_non_overlapping_matches(self) -> None:
        text = Text("ab_ab_ab")
        highlight_text(text, "ab", style="red")
        spans = sorted((s.start, s.end) for s in text.spans)
        assert spans == [(0, 2), (3, 5), (6, 8)]

    def test_overlapping_matches_are_all_highlighted(self) -> None:
        text = Text("aaaa")
        highlight_text(text, "aa", style="red")
        spans = {(s.start, s.end) for s in text.spans}
        assert {(0, 2), (1, 3), (2, 4)} <= spans

    def test_no_match_leaves_spans_empty(self) -> None:
        text = Text("hello")
        highlight_text(text, "xyz", style="red")
        assert text.spans == []

    def test_term_longer_than_text_does_not_match(self) -> None:
        text = Text("hi")
        highlight_text(text, "hello world", style="red")
        assert text.spans == []

    def test_regex_metachars_matched_literally(self) -> None:
        text = Text("a.b.c")
        highlight_text(text, ".", style="red")
        spans = sorted((s.start, s.end) for s in text.spans)
        assert spans == [(1, 2), (3, 4)]

    def test_regex_wildcard_not_interpreted(self) -> None:
        text = Text("abc")
        highlight_text(text, ".", style="red")
        assert text.spans == []

    def test_ascii_case_folding_matches_unicode_counterparts(self) -> None:
        text = Text("Straße")
        highlight_text(text, "STRASSE", style="red")
        assert text.spans == []

    def test_uses_default_style_when_not_provided(self) -> None:
        text = Text("hello")
        highlight_text(text, "ell")
        assert [str(s.style) for s in text.spans] == [DEFAULT_SEARCH_HIGHLIGHT_STYLE]


@dataclass
class _Call:
    op: str
    args: tuple[object, ...]


class _RecordingVisitor:
    def __init__(self) -> None:
        self.calls: list[_Call] = []

    def enter_property(
        self, key: str, value: object, path: str, from_json: bool
    ) -> None:
        self.calls.append(_Call("enter_property", (key, value, path, from_json)))

    def exit_property(self) -> None:
        self.calls.append(_Call("exit_property", ()))

    def on_property(self, key: str, value: object, path: str) -> None:
        self.calls.append(_Call("on_property", (key, value, path)))

    def enter_item(self, index: int, value: object, path: str) -> None:
        self.calls.append(_Call("enter_item", (index, value, path)))

    def exit_item(self) -> None:
        self.calls.append(_Call("exit_item", ()))

    def on_item(self, index: int, value: object, path: str) -> None:
        self.calls.append(_Call("on_item", (index, value, path)))


def _find_call(calls: list[_Call], op: str, key: str) -> _Call:
    return next(c for c in calls if c.op == op and c.args and c.args[0] == key)


class TestWalkTree:
    def test_flat_dict_emits_leaves_sorted_by_priority(self) -> None:
        visitor = _RecordingVisitor()
        walk_tree(
            value={"extra": 1, "level": "INFO"},
            path="",
            visitor=visitor,
        )
        assert visitor.calls == [
            _Call("on_property", ("level", "INFO", "level")),
            _Call("on_property", ("extra", 1, "extra")),
        ]

    def test_nested_dict_enters_and_exits(self) -> None:
        visitor = _RecordingVisitor()
        walk_tree(
            value={"outer": {"inner": 1}},
            path="",
            visitor=visitor,
        )
        assert visitor.calls == [
            _Call("enter_property", ("outer", {"inner": 1}, "outer", False)),
            _Call("on_property", ("inner", 1, "outer.inner")),
            _Call("exit_property", ()),
        ]

    def test_list_root_emits_items(self) -> None:
        visitor = _RecordingVisitor()
        walk_tree(value=["a", "b"], path="", visitor=visitor)
        assert visitor.calls == [
            _Call("on_item", (0, "a", "[0]")),
            _Call("on_item", (1, "b", "[1]")),
        ]

    def test_nested_list_enters_and_exits(self) -> None:
        visitor = _RecordingVisitor()
        walk_tree(value={"xs": [1, {"k": 2}]}, path="", visitor=visitor)
        assert visitor.calls == [
            _Call("enter_property", ("xs", [1, {"k": 2}], "xs", False)),
            _Call("on_item", (0, 1, "xs[0]")),
            _Call("enter_item", (1, {"k": 2}, "xs[1]")),
            _Call("on_property", ("k", 2, "xs[1].k")),
            _Call("exit_item", ()),
            _Call("exit_property", ()),
        ]

    def test_from_json_flag_set_for_matching_path(self) -> None:
        visitor = _RecordingVisitor()
        walk_tree(
            value={"a": {"b": 1}, "c": {"d": 2}},
            path="",
            visitor=visitor,
            json_paths={"a"},
        )
        enter_a = _find_call(visitor.calls, "enter_property", "a")
        enter_c = _find_call(visitor.calls, "enter_property", "c")
        assert enter_a.args[3] is True
        assert enter_c.args[3] is False

    def test_from_json_flag_not_propagated_to_descendants(self) -> None:
        visitor = _RecordingVisitor()
        walk_tree(
            value={"a": {"b": {"c": 1}}},
            path="",
            visitor=visitor,
            json_paths={"a"},
        )
        enter_a = _find_call(visitor.calls, "enter_property", "a")
        enter_b = _find_call(visitor.calls, "enter_property", "b")
        assert enter_a.args[3] is True
        assert enter_b.args[3] is False

    def test_path_prefix_respected(self) -> None:
        visitor = _RecordingVisitor()
        walk_tree(value={"k": 1}, path="root", visitor=visitor)
        assert visitor.calls == [_Call("on_property", ("k", 1, "root.k"))]

    def test_scalar_root_yields_no_calls(self) -> None:
        visitor = _RecordingVisitor()
        walk_tree(value=42, path="", visitor=visitor)
        assert visitor.calls == []

    def test_empty_dict_yields_no_calls(self) -> None:
        visitor = _RecordingVisitor()
        walk_tree(value={}, path="", visitor=visitor)
        assert visitor.calls == []

    def test_empty_list_yields_no_calls(self) -> None:
        visitor = _RecordingVisitor()
        walk_tree(value=[], path="", visitor=visitor)
        assert visitor.calls == []

    def test_deep_nesting_builds_dotted_path(self) -> None:
        visitor = _RecordingVisitor()
        walk_tree(
            value={"a": {"b": {"c": {"d": {"e": 1}}}}},
            path="",
            visitor=visitor,
        )
        leaf = next(c for c in visitor.calls if c.op == "on_property")
        assert leaf.args == ("e", 1, "a.b.c.d.e")


@dataclass
class _FakeNode:
    label: Text | None = None
    path: str = ""
    value: object = None
    is_leaf: bool = False
    children: list[_FakeNode] = field(default_factory=list)


def _add_branch(parent: _FakeNode, label: Text, path: str, value: object) -> _FakeNode:
    node = _FakeNode(label=label, path=path, value=value)
    parent.children.append(node)
    return node


def _add_leaf(parent: _FakeNode, label: Text, path: str, value: object) -> None:
    parent.children.append(_FakeNode(label=label, path=path, value=value, is_leaf=True))


def _build(
    data: object,
    *,
    selected: set[str] | None = None,
    search_term: str | None = None,
    json_paths: set[str] | None = None,
    value_style: str | Style = DEFAULT_VALUE_STYLE,
    value_null_style: str | Style = DEFAULT_VALUE_NULL_STYLE,
    json_string_style: str | Style = DEFAULT_JSON_STRING_STYLE,
    search_highlight_style: str | Style = DEFAULT_SEARCH_HIGHLIGHT_STYLE,
) -> _FakeNode:
    root = _FakeNode()
    visitor = TreeBuildVisitor(
        root=root,
        add_branch=_add_branch,
        add_leaf=_add_leaf,
        selected=selected or set(),
        key_style="cyan",
        selected_style="bold green",
        value_style=value_style,
        value_null_style=value_null_style,
        json_string_style=json_string_style,
        search_highlight_style=search_highlight_style,
        search_term=search_term,
    )
    walk_tree(value=data, path="", visitor=visitor, json_paths=json_paths)
    return root


class TestTreeBuildVisitor:
    def test_scalar_properties_become_leaves(self) -> None:
        root = _build({"a": 1, "b": "x"})
        assert len(root.children) == 2
        assert all(c.is_leaf for c in root.children)
        assert [c.path for c in root.children] == ["a", "b"]
        assert [c.value for c in root.children] == [1, "x"]

    def test_leaf_label_contains_key_and_value(self) -> None:
        root = _build({"level": "INFO"})
        assert root.children[0].label is not None
        assert root.children[0].label.plain == "level: INFO"

    def test_null_value_uses_null_style(self) -> None:
        root = _build({"x": None}, value_null_style="dim italic")
        label = root.children[0].label
        assert label is not None
        value_start = label.plain.index("None")
        value_end = value_start + len("None")
        null_spans = [
            (s.start, s.end) for s in label.spans if str(s.style) == "dim italic"
        ]
        assert (value_start, value_end) in null_spans

    def test_selected_path_uses_selected_style(self) -> None:
        root = _build({"alpha": 1, "beta": 2}, selected={"alpha"})
        label_a = root.children[0].label
        label_b = root.children[1].label
        assert label_a is not None
        assert label_b is not None
        key_span_a = next(
            s for s in label_a.spans if s.start == 0 and s.end == len("alpha")
        )
        key_span_b = next(
            s for s in label_b.spans if s.start == 0 and s.end == len("beta")
        )
        assert str(key_span_a.style) == "bold green"
        assert str(key_span_b.style) == "cyan"

    def test_dict_branch_label_uses_brace_indicator(self) -> None:
        root = _build({"outer": {"inner": 1}})
        branch = root.children[0]
        assert not branch.is_leaf
        assert branch.label is not None
        assert branch.label.plain == "outer: {}"

    def test_list_branch_label_shows_item_count(self) -> None:
        root = _build({"xs": [1, 2, 3]})
        branch = root.children[0]
        assert branch.label is not None
        assert branch.label.plain == "xs: [3 items]"

    def test_empty_list_branch_shows_zero_items(self) -> None:
        root = _build({"xs": []})
        branch = root.children[0]
        assert branch.label is not None
        assert branch.label.plain == "xs: [0 items]"
        assert branch.children == []

    def test_json_branch_indicator_is_quoted(self) -> None:
        root = _build(
            {"payload": {"inner": 1}},
            json_paths={"payload"},
        )
        branch = root.children[0]
        assert branch.label is not None
        assert branch.label.plain == 'payload: "{}"'

    def test_json_list_branch_indicator_is_quoted(self) -> None:
        root = _build(
            {"payload": [1, 2]},
            json_paths={"payload"},
        )
        branch = root.children[0]
        assert branch.label is not None
        assert branch.label.plain == 'payload: "[2 items]"'

    def test_branch_stores_path_and_value(self) -> None:
        data = {"outer": {"inner": 1}}
        root = _build(data)
        branch = root.children[0]
        assert branch.path == "outer"
        assert branch.value == {"inner": 1}

    def test_list_items_become_indexed_children(self) -> None:
        root = _build({"xs": [10, 20]})
        branch = root.children[0]
        assert [c.path for c in branch.children] == ["xs[0]", "xs[1]"]
        assert [c.value for c in branch.children] == [10, 20]
        assert [c.label.plain for c in branch.children if c.label is not None] == [
            "[0]: 10",
            "[1]: 20",
        ]

    def test_nested_list_items_produce_index_branches(self) -> None:
        root = _build({"xs": [{"k": 1}, {"k": 2}]})
        xs = root.children[0]
        assert len(xs.children) == 2
        for idx, item in enumerate(xs.children):
            assert not item.is_leaf
            assert item.label is not None
            assert item.label.plain == f"[{idx}]"
            assert item.path == f"xs[{idx}]"

    def test_search_highlight_styles_matches_in_leaves(self) -> None:
        root = _build(
            {"level": "INFO"},
            search_term="inf",
            search_highlight_style="on yellow",
        )
        label = root.children[0].label
        assert label is not None
        match_start = label.plain.lower().index("inf")
        hl = [(s.start, s.end) for s in label.spans if str(s.style) == "on yellow"]
        assert hl == [(match_start, match_start + len("inf"))]

    def test_search_highlight_applies_to_branch_labels(self) -> None:
        root = _build(
            {"outer": {"inner": 1}},
            search_term="out",
            search_highlight_style="on yellow",
        )
        label = root.children[0].label
        assert label is not None
        hl = [(s.start, s.end) for s in label.spans if str(s.style) == "on yellow"]
        assert hl == [(0, len("out"))]

    def test_no_search_term_adds_no_highlight_spans(self) -> None:
        root = _build(
            {"level": "INFO"},
            search_term=None,
            search_highlight_style="on yellow",
        )
        label = root.children[0].label
        assert label is not None
        assert not any(str(s.style) == "on yellow" for s in label.spans)

    def test_multiline_value_gets_ellipsis(self) -> None:
        root = _build({"msg": "first\nsecond"})
        label = root.children[0].label
        assert label is not None
        assert label.plain == "msg: first\u2026"

    def test_second_walk_starts_at_root(self) -> None:
        root = _FakeNode()
        visitor = TreeBuildVisitor(
            root=root,
            add_branch=_add_branch,
            add_leaf=_add_leaf,
            selected=set(),
            key_style="cyan",
            selected_style="bold green",
        )
        walk_tree(value={"a": {"b": [{"c": 1}]}}, path="", visitor=visitor)
        walk_tree(value={"top": 1}, path="", visitor=visitor)
        top_leaf = root.children[-1]
        assert top_leaf.is_leaf
        assert top_leaf.path == "top"

    def test_null_list_item_uses_null_style(self) -> None:
        root = _build({"xs": [None]}, value_null_style="dim italic")
        branch = root.children[0]
        leaf = branch.children[0]
        assert leaf.is_leaf
        assert leaf.label is not None
        value_start = leaf.label.plain.index("None")
        value_end = value_start + len("None")
        null_spans = [
            (s.start, s.end) for s in leaf.label.spans if str(s.style) == "dim italic"
        ]
        assert (value_start, value_end) in null_spans

    def test_json_paths_does_not_affect_list_items(self) -> None:
        root = _build(
            {"xs": [{"k": 1}]},
            json_paths={"xs[0]"},
        )
        branch = root.children[0]
        item = branch.children[0]
        assert item.label is not None
        assert item.label.plain == "[0]"
        nested = item.children[0]
        assert nested.label is not None
        assert nested.label.plain == "k: 1"
