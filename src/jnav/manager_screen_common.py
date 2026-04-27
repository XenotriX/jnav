from typing import override

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Footer


class WrappingFooter(Footer):
    _bindings_ready: reactive[bool] | bool = True

    def __init__(self, *, columns: int = 4) -> None:
        super().__init__()
        self._columns = columns

    @override
    def compose(self) -> ComposeResult:
        self._bindings_ready = True
        yield from super().compose()
        self.styles.grid_size_columns = self._columns
