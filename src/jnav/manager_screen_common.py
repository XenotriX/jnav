from typing import override

from rich.text import Text
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


def list_option_prompt(label: str, enabled: bool, combine: str = "and") -> Text:
    marker = "\u2713" if enabled else " "
    style = "" if enabled else "dim"
    prefix = "OR " if combine == "or" else "   "
    return Text.assemble(
        (prefix, "italic" if combine == "or" else "dim"),
        (f"{marker} ", style),
        (label, style),
    )
