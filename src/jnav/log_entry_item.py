from __future__ import annotations

from typing import override

from textual.app import ComposeResult
from textual.widgets import ListItem

from .entry_summary import EntrySummary
from .inline_tree import InlineTree
from .store import IndexedEntry


class LogEntryItem(ListItem):
    def __init__(self, entry: IndexedEntry) -> None:
        super().__init__()
        self.entry_index = entry.index
        self._summary = EntrySummary()
        self._summary.set_entry(entry.entry)
        self._inline_tree = InlineTree()
        self._inline_tree.set_entry(entry.entry)

    @override
    def compose(self) -> ComposeResult:
        yield self._summary
        yield self._inline_tree

    def refresh_content(
        self,
        custom: set[str],
        search: str,
        expanded: bool,
    ) -> None:
        self._summary.refresh_content(search)
        if custom and expanded:
            self._inline_tree.refresh_content(custom, search)
            self._inline_tree.display = True
        else:
            self._inline_tree.display = False
