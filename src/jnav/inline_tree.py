from __future__ import annotations

from rich.text import Text
from rich.tree import Tree as RichTree
from textual.widgets import Static

from .filtering import get_nested
from .parsing import ParsedEntry
from .tree_rendering import TreeBuildVisitor, walk_tree


def _add_branch(
    parent: RichTree, label: Text, path: str, value: object
) -> RichTree:
    del path, value  # unused
    return parent.add(label)


def _add_leaf(
    parent: RichTree, label: Text, path: str, value: object
) -> None:
    del path, value  # unused
    parent.add(label)


class InlineTree(Static):
    COMPONENT_CLASSES = {
        "tree--key",
        "tree--key-selected",
    }

    DEFAULT_CSS = """
    InlineTree {
        display: none;
        padding: 0 1 0 5;
        color: $foreground;
        background: $surface;
        & > .tree--key { color: $primary; text-style: italic; }
        & > .tree--key-selected { color: $primary; text-style: bold underline; }
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

        key_style = self.get_component_rich_style("tree--key", partial=True)
        selected_style = self.get_component_rich_style("tree--key-selected", partial=True)

        filtered = {f: get_nested(self._parsed.expanded, f) for f in selected_fields}
        tree = RichTree("", guide_style="dim", hide_root=True)
        visitor = TreeBuildVisitor(
            root=tree,
            add_branch=_add_branch,
            add_leaf=_add_leaf,
            selected=selected_fields,
            key_style=key_style,
            selected_style=selected_style,
            search_term=search,
        )
        walk_tree(
            value=filtered,
            path="",
            visitor=visitor,
            json_paths=self._parsed.expanded_paths,
        )
        self.update(tree)
