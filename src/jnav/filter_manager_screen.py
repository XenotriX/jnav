from typing import ClassVar, override

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from jnav.filter_provider import FilterProvider
from jnav.filter_tree import FilterTree
from jnav.filtering import build_expression
from jnav.manager_screen_common import WrappingFooter


class FilterManagerScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
    FilterManagerScreen {
        align: center middle;
    }
    #filter-modal {
        width: 70;
        max-width: 90%;
        height: auto;
        max-height: 70%;
        border: round $primary;
        background: $background;
    }
    #filter-wrapper {
        padding: 1 2;
        height: auto;
    }
    #filter-expression {
        color: $accent;
        background: transparent;
        border: round $background-lighten-2;
        margin: 1 0 0 0;
        padding: 0 1;
        height: auto;
        max-height: 5;
    }
    #filter-expression.empty {
        color: $text-muted;
    }
    #filter-hints {
        color: $text-muted;
        margin: 1 0 0 0;
    }
    #filter-modal Footer {
        background: transparent;
        layout: grid;
        grid-size: 4;
        height: auto;
    }
    #filter-modal FooterKey .footer-key--key {
        color: $primary;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "maybe_close", "Close", priority=True),
        Binding("q", "maybe_close", show=False),
        Binding("ctrl+c", "maybe_close", show=False),
    ]

    def __init__(self, filter_provider: FilterProvider) -> None:
        super().__init__()
        self._fp = filter_provider

    @override
    def compose(self) -> ComposeResult:
        yield Vertical(
            Vertical(
                FilterTree(self._fp, id="filter-tree"),
                Static(id="filter-expression"),
                id="filter-wrapper",
            ),
            WrappingFooter(columns=4),
            id="filter-modal",
        )

    def on_mount(self) -> None:
        self.query_one("#filter-modal").border_title = "Filters"
        self.query_one("#filter-tree", FilterTree).focus()
        self._update_preview()

    def on_filter_tree_changed(self) -> None:
        self._update_preview()

    def _update_preview(self) -> None:
        expr_widget = self.query_one("#filter-expression", Static)
        expr = build_expression(self._fp.root)
        if expr:
            expr_widget.update(f"{expr}")
            expr_widget.remove_class("empty")
        else:
            expr_widget.update("(no active filters)")
            expr_widget.add_class("empty")

    def action_maybe_close(self) -> None:
        self.dismiss(True)
