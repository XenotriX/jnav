from typing import override

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from jnav.manager_screen_common import list_option_prompt
from jnav.selector_provider import SelectorProvider


class SelectorManagerScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
    SelectorManagerScreen {
        align: center middle;
    }
    #selector-modal {
        width: 60;
        max-width: 90%;
        height: auto;
        max-height: 70%;
        border: round $surface-lighten-2;
        background: $surface;
        padding: 1 2;
    }
    #selector-list {
        height: auto;
        max-height: 14;
        border: none;
    }
    #selector-add-input {
        margin: 1 0 0 0;
    }
    #selector-add-input.hidden {
        display: none;
    }
    #selector-hints {
        color: $text-muted;
        margin: 1 0 0 0;
    }
    """

    BINDINGS = [
        Binding("escape", "maybe_close", "Close", priority=True),
        Binding("q", "maybe_close", show=False),
        Binding("ctrl+c", "maybe_close", show=False),
        Binding("a", "add_mode", "Add", show=False),
        Binding("e", "edit_mode", "Edit", show=False),
        Binding("d", "delete", "Delete", show=False),
        Binding("t", "toggle_item", "Toggle", show=False),
    ]

    def __init__(self, selector_provider: SelectorProvider) -> None:
        super().__init__()
        self._sp = selector_provider
        self._editing_idx: int | None = None

    @override
    def compose(self) -> ComposeResult:
        yield Vertical(
            OptionList(id="selector-list"),
            Input(
                placeholder="jq selector (e.g. .data.role)...",
                id="selector-add-input",
                classes="hidden",
            ),
            Static(
                "[b]a[/b]:Add  [b]e[/b]:Edit  [b]space[/b]:Toggle  [b]d[/b]:Delete  [b]esc[/b]:Close",
                id="selector-hints",
            ),
            id="selector-modal",
        )

    def on_mount(self) -> None:
        self.query_one("#selector-modal").border_title = "Selectors"
        self._refresh_list()
        self.query_one("#selector-list", OptionList).focus()

    def _refresh_list(self, highlight: int | None = None) -> None:
        selectors = self._sp.selectors
        ol = self.query_one("#selector-list", OptionList)
        ol.clear_options()
        if not selectors:
            ol.add_option(Option(Text(" (no selectors)", style="dim"), disabled=True))
        else:
            for s in selectors:
                ol.add_option(list_option_prompt(s["path"], s["enabled"]))
        if highlight is not None and selectors:
            ol.highlighted = min(highlight, len(selectors) - 1)

    async def action_toggle_item(self) -> None:
        ol = self.query_one("#selector-list", OptionList)
        idx = ol.highlighted
        if idx is not None and idx < len(self._sp.selectors):
            await self._sp.toggle_selector(idx)
            self._refresh_list(idx)

    async def action_delete(self) -> None:
        ol = self.query_one("#selector-list", OptionList)
        idx = ol.highlighted
        if idx is not None and idx < len(self._sp.selectors):
            await self._sp.remove_selector(idx)
            self._refresh_list(idx)

    def action_add_mode(self) -> None:
        self._editing_idx = None
        inp = self.query_one("#selector-add-input", Input)
        inp.remove_class("hidden")
        inp.value = ""
        inp.focus()

    def action_edit_mode(self) -> None:
        ol = self.query_one("#selector-list", OptionList)
        idx = ol.highlighted
        selectors = self._sp.selectors
        if idx is None or idx >= len(selectors):
            return
        self._editing_idx = idx
        inp = self.query_one("#selector-add-input", Input)
        inp.remove_class("hidden")
        inp.value = selectors[idx]["path"]
        inp.focus()

    @on(Input.Submitted, "#selector-add-input")
    async def on_add_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip().lstrip(".")
        if raw:
            if self._editing_idx is not None:
                await self._sp.edit_selector(self._editing_idx, raw)
                highlight = self._editing_idx
            else:
                await self._sp.add_selector(raw)
                highlight = len(self._sp.selectors) - 1
        else:
            highlight = self._editing_idx
        self._editing_idx = None
        event.input.value = ""
        self.query_one("#selector-add-input").add_class("hidden")
        self._refresh_list(highlight)
        self.query_one("#selector-list", OptionList).focus()

    def action_maybe_close(self) -> None:
        inp = self.query_one("#selector-add-input", Input)
        if not inp.has_class("hidden"):
            self._editing_idx = None
            inp.add_class("hidden")
            inp.value = ""
            self.query_one("#selector-list", OptionList).focus()
        else:
            self.dismiss(True)
