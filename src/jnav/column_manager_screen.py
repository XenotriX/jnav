from typing import TypedDict, override

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from jnav.manager_screen_common import list_option_prompt


class FieldSelector(TypedDict):
    path: str
    enabled: bool


class ColumnManagerScreen(ModalScreen[bool]):
    custom_columns: list[FieldSelector]
    DEFAULT_CSS = """
    ColumnManagerScreen {
        align: center middle;
    }
    #column-modal {
        width: 60;
        max-width: 90%;
        height: auto;
        max-height: 70%;
        border: solid $surface-lighten-2;
        background: $surface;
        padding: 1 2;
    }
    #column-modal-title {
        text-style: bold;
        padding: 0 0 1 0;
    }
    #column-list {
        height: auto;
        max-height: 14;
        border: none;
    }
    #column-add-input {
        margin: 1 0 0 0;
    }
    #column-add-input.hidden {
        display: none;
    }
    #column-hints {
        color: $text-muted;
        margin: 1 0 0 0;
    }
    """

    BINDINGS = [
        Binding("escape", "maybe_close", "Close", priority=True),
        Binding("a", "add_mode", "Add", show=False),
        Binding("e", "edit_mode", "Edit", show=False),
        Binding("d", "delete", "Delete", show=False),
        Binding("space", "toggle_item", "Toggle", show=False),
    ]

    def __init__(
        self, custom_columns: list[FieldSelector], all_columns: list[str]
    ) -> None:
        super().__init__()
        self.custom_columns = custom_columns
        self.all_columns = all_columns
        self._editing_idx: int | None = None

    @override
    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("Fields", id="column-modal-title"),
            OptionList(id="column-list"),
            Input(
                placeholder="field path (e.g. data.role)...",
                id="column-add-input",
                classes="hidden",
            ),
            Static(
                "[b]a[/b]:Add  [b]e[/b]:Edit  [b]space[/b]:Toggle  [b]d[/b]:Delete  [b]esc[/b]:Close",
                id="column-hints",
            ),
            id="column-modal",
        )

    def on_mount(self) -> None:
        self._refresh_list()
        self.query_one("#column-list", OptionList).focus()

    def _refresh_list(self, highlight: int | None = None) -> None:
        ol = self.query_one("#column-list", OptionList)
        ol.clear_options()
        if not self.custom_columns:
            ol.add_option(
                Option(Text(" (no fields selected)", style="dim"), disabled=True)
            )
        else:
            for c in self.custom_columns:
                ol.add_option(list_option_prompt(c["path"], c["enabled"]))
        if highlight is not None and self.custom_columns:
            ol.highlighted = min(highlight, len(self.custom_columns) - 1)

    def action_toggle_item(self) -> None:
        ol = self.query_one("#column-list", OptionList)
        idx = ol.highlighted
        if idx is not None and idx < len(self.custom_columns):
            self.custom_columns[idx]["enabled"] = not self.custom_columns[idx][
                "enabled"
            ]
            self._refresh_list(idx)

    def action_delete(self) -> None:
        ol = self.query_one("#column-list", OptionList)
        idx = ol.highlighted
        if idx is not None and idx < len(self.custom_columns):
            self.custom_columns.pop(idx)
            self._refresh_list(idx)

    def action_add_mode(self) -> None:
        self._editing_idx = None
        inp = self.query_one("#column-add-input", Input)
        inp.remove_class("hidden")
        inp.value = ""
        inp.focus()

    def action_edit_mode(self) -> None:
        ol = self.query_one("#column-list", OptionList)
        idx = ol.highlighted
        if idx is None or idx >= len(self.custom_columns):
            return
        self._editing_idx = idx
        inp = self.query_one("#column-add-input", Input)
        inp.remove_class("hidden")
        inp.value = self.custom_columns[idx]["path"]
        inp.focus()

    @on(Input.Submitted, "#column-add-input")
    def on_add_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip().lstrip(".")
        if raw:
            if self._editing_idx is not None:
                self.custom_columns[self._editing_idx]["path"] = raw
                highlight = self._editing_idx
            else:
                existing = {c["path"] for c in self.custom_columns}
                if raw not in existing:
                    self.custom_columns.append({"path": raw, "enabled": True})
                highlight = len(self.custom_columns) - 1
        else:
            highlight = self._editing_idx
        self._editing_idx = None
        event.input.value = ""
        self.query_one("#column-add-input").add_class("hidden")
        self._refresh_list(highlight)
        self.query_one("#column-list", OptionList).focus()

    def action_maybe_close(self) -> None:
        inp = self.query_one("#column-add-input", Input)
        if not inp.has_class("hidden"):
            self._editing_idx = None
            inp.add_class("hidden")
            inp.value = ""
            self.query_one("#column-list", OptionList).focus()
        else:
            self.dismiss(True)
