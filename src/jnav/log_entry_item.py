from __future__ import annotations

from typing import override

from textual.app import ComposeResult
from textual.widgets import ListItem

from .entry_summary import EntrySummary
from .field_manager import FieldManager
from .inline_tree import InlineTree
from .search_engine import SearchEngine
from .store import IndexedEntry


class LogEntryItem(ListItem):
    def __init__(
        self,
        *,
        entry: IndexedEntry,
        fields: FieldManager,
        search: SearchEngine,
    ) -> None:
        super().__init__()
        self.entry_index = entry.index
        self._summary = EntrySummary(entry.entry, search)
        self._inline_tree = InlineTree(
            parsed=entry.entry,
            fields=fields,
            search=search,
        )

    @override
    def compose(self) -> ComposeResult:
        yield self._summary
        yield self._inline_tree
