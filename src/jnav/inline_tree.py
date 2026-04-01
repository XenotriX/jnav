from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from rich.tree import Tree as RichTree
from textual.widgets import Static

if TYPE_CHECKING:
    from textual import getters
    from textual.app import App

from .field_manager import FieldManager
from .filtering import get_nested
from .parsing import ParsedEntry
from .search_engine import SearchEngine
from .tree_rendering import TreeBuildVisitor, walk_tree


def _add_branch(
    parent: RichTree,
    label: Text,
    path: str,
    value: object,
) -> RichTree:
    del path, value  # unused
    return parent.add(label)


def _add_leaf(
    parent: RichTree,
    label: Text,
    path: str,
    value: object,
) -> None:
    del path, value  # unused
    parent.add(label)


class InlineTree(Static):
    if TYPE_CHECKING:
        app = getters.app(App[None])

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

    def __init__(
        self,
        *,
        parsed: ParsedEntry,
        fields: FieldManager,
        search: SearchEngine,
    ) -> None:
        super().__init__()
        self._parsed = parsed
        self._fields = fields
        self._search = search

    async def on_mount(self) -> None:
        await self._fields.on_change.subscribe_async(self._on_change)
        await self._search.on_change.subscribe_async(self._on_change)
        self.app.theme_changed_signal.subscribe(self, lambda _: self._render_tree())
        self._render_tree()

    async def _on_change(self, _: None) -> None:
        self._render_tree()

    def _render_tree(self) -> None:
        custom = self._fields.custom_fields_set
        if not custom:
            self.remove_class("has-content")
            return
        self.add_class("has-content")

        key_style = self.get_component_rich_style("tree--key", partial=True)
        selected_style = self.get_component_rich_style(
            "tree--key-selected", partial=True
        )

        filtered = {f: get_nested(self._parsed.expanded, f) for f in custom}
        tree = RichTree("", guide_style="dim", hide_root=True)
        visitor = TreeBuildVisitor(
            root=tree,
            add_branch=_add_branch,
            add_leaf=_add_leaf,
            selected=custom,
            key_style=key_style,
            selected_style=selected_style,
            search_term=self._search.term,
        )
        walk_tree(
            value=filtered,
            path="",
            visitor=visitor,
            json_paths=self._parsed.expanded_paths,
        )
        self.update(tree)
