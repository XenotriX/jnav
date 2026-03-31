from __future__ import annotations

from typing import Any

from rich.text import Text
from rich.tree import Tree as RichTree
from textual.widgets import Static

from .filtering import get_nested
from .parsing import ParsedEntry
from .tree_rendering import walk_tree


class InlineTree(Static):
    DEFAULT_CSS = """
    InlineTree {
        display: none;
        padding: 0 1 0 5;
        color: $foreground;
        background: $surface;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._parsed: ParsedEntry | None = None

    def set_entry(self, parsed: ParsedEntry) -> None:
        self._parsed = parsed

    def refresh_content(self, selected_fields: set[str], search: str) -> None:
        if self._parsed is None:
            return
        filtered = {f: get_nested(self._parsed.expanded, f) for f in selected_fields}
        self.update(
            _build_rich_tree(
                entry=filtered,
                selected_fields=selected_fields,
                search_term=search,
                json_paths=self._parsed.expanded_paths,
            )
        )


def _build_rich_tree(
    *,
    entry: dict[str, Any],
    selected_fields: set[str],
    search_term: str = "",
    json_paths: set[str] | None = None,
) -> RichTree:
    tree = RichTree("", guide_style="dim", hide_root=True)
    _populate_rich_tree(
        node=tree,
        value=entry,
        path="",
        selected_fields=selected_fields,
        search_term=search_term,
        json_paths=json_paths,
    )
    return tree


def _populate_rich_tree(
    *,
    node: RichTree,
    value: object,
    path: str,
    selected_fields: set[str],
    search_term: str = "",
    json_paths: set[str] | None = None,
) -> None:
    def add_branch(
        label: Text,
        children_value: object,
        child_path: str,
        orig_value: object,
    ) -> None:
        del orig_value  # unused
        branch = node.add(label)
        _populate_rich_tree(
            node=branch,
            value=children_value,
            path=child_path,
            selected_fields=selected_fields,
            search_term=search_term,
            json_paths=json_paths,
        )

    def add_leaf(
        label: Text,
        child_path: str,
        orig_value: object,
    ) -> None:
        del child_path, orig_value  # unused
        node.add(label)

    walk_tree(
        value=value,
        path=path,
        selected=selected_fields,
        add_branch=add_branch,
        add_leaf=add_leaf,
        search_term=search_term,
        json_paths=json_paths,
    )
