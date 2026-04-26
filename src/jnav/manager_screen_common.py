from typing import override

from textual.app import ComposeResult
from textual.widgets import Footer


class WrappingFooter(Footer):
    def __init__(self, *, columns: int = 4) -> None:
        super().__init__()
        self._columns = columns

    @override
    def compose(self) -> ComposeResult:
        yield from super().compose()
        self.styles.grid_size_columns = self._columns
