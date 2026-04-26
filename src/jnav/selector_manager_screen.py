from typing import TYPE_CHECKING, ClassVar, Literal, override

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from jnav.modal import Modal
from jnav.selector_provider import Selector, SelectorProvider
from jnav.text_input_screen import TextInputScreen

if TYPE_CHECKING:
    from textual import getters
    from textual.app import App


class SelectorManagerScreen(Modal):
    if TYPE_CHECKING:
        app = getters.app(App[None])

    COMPONENT_CLASSES: ClassVar[set[str]] = {
        "selector-list--expression",
        "selector-list--expression-disabled",
        "selector-list--label",
        "selector-list--label-disabled",
    }

    DEFAULT_CSS = """
    #selector-list {
        height: auto;
        max-height: 14;
        border: none;
        background: transparent;

        & .option-list--option-highlighted {
            background: $background-darken-1;
        }
    }
    .selector-list--expression {
        color: $primary;
    }
    .selector-list--expression-disabled {
        color: $primary;
        text-style: dim;
    }
    .selector-list--label {
        color: $accent;
    }
    .selector-list--label-disabled {
        color: $accent;
        text-style: dim;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("a", "add", "Add"),
        Binding("e", "edit", "Edit"),
        Binding("r", "rename", "Rename"),
        Binding("d", "delete", "Cut"),
        Binding("y", "yank", "Yank"),
        Binding("p", "paste", "Paste"),
        Binding("P", "paste_above", "Paste above"),
        Binding("t", "toggle_item", "Toggle"),
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
    ]

    modal_title = "Selectors"
    modal_width = 70
    footer_columns = 4

    def __init__(self, selector_provider: SelectorProvider) -> None:
        super().__init__()
        self._sp = selector_provider
        self._clipboard: Selector | None = None

    @override
    def compose_body(self) -> ComposeResult:
        yield OptionList(id="selector-list")

    @override
    def on_mount(self) -> None:
        self._refresh_list(highlight=0)
        self.query_one("#selector-list", OptionList).focus()

    def _refresh_list(self, highlight: int | None = None) -> None:
        selectors = self._sp.selectors
        ol = self.query_one("#selector-list", OptionList)
        ol.clear_options()
        if not selectors:
            ol.add_option(Option(Text(" (no selectors)", style="dim"), disabled=True))
        else:
            for s in selectors:
                ol.add_option(self.list_option_prompt(s))
        if highlight is not None and selectors:
            ol.highlighted = min(highlight, len(selectors) - 1)

    def action_cursor_down(self) -> None:
        self.query_one("#selector-list", OptionList).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#selector-list", OptionList).action_cursor_up()

    async def action_toggle_item(self) -> None:
        ol = self.query_one("#selector-list", OptionList)
        idx = ol.highlighted
        if idx is not None and idx < len(self._sp.selectors):
            await self._sp.toggle_selector(idx)
            self._refresh_list(idx)

    async def action_delete(self) -> None:
        ol = self.query_one("#selector-list", OptionList)
        idx = ol.highlighted
        selectors = self._sp.selectors
        if idx is None or idx >= len(selectors):
            return
        self._clipboard = selectors[idx]
        await self._sp.remove_selector(idx)
        self._refresh_list(idx)

    def action_yank(self) -> None:
        ol = self.query_one("#selector-list", OptionList)
        idx = ol.highlighted
        selectors = self._sp.selectors
        if idx is None or idx >= len(selectors):
            return
        self._clipboard = selectors[idx].model_copy(deep=True)

    async def action_paste(self) -> None:
        await self._paste_at("after")

    async def action_paste_above(self) -> None:
        await self._paste_at("before")

    def action_add(self) -> None:
        ol = self.query_one("#selector-list", OptionList)
        idx = ol.highlighted
        target = (idx + 1) if idx is not None else len(self._sp.selectors)

        async def on_dismiss(value: str | None) -> None:
            if not value:
                return
            selector = Selector(expression=value, enabled=True)
            await self._sp.insert_selector(target, selector)
            self._refresh_list(target)

        self.app.push_screen(
            TextInputScreen("Add selector", placeholder="jq selector..."),
            on_dismiss,
        )

    def action_edit(self) -> None:
        ol = self.query_one("#selector-list", OptionList)
        idx = ol.highlighted
        selectors = self._sp.selectors
        if idx is None or idx >= len(selectors):
            return
        current = selectors[idx].expression

        async def on_dismiss(value: str | None) -> None:
            if not value:
                return
            await self._sp.edit_selector(idx, value)
            self._refresh_list(idx)

        self.app.push_screen(
            TextInputScreen(
                "Edit selector",
                placeholder="jq selector...",
                initial_value=current,
            ),
            on_dismiss,
        )

    def action_rename(self) -> None:
        ol = self.query_one("#selector-list", OptionList)
        idx = ol.highlighted
        selectors = self._sp.selectors
        if idx is None or idx >= len(selectors):
            return

        async def on_dismiss(label: str | None) -> None:
            if label is None:
                return
            self._sp.selectors[idx].label = label or None
            await self._sp.on_change.asend(None)
            self._refresh_list(idx)

        self.app.push_screen(
            TextInputScreen(
                "Rename",
                placeholder=selectors[idx].expression,
                initial_value=selectors[idx].label or "",
                allow_empty=True,
            ),
            on_dismiss,
        )

    def _highlighted_index(self) -> int | None:
        return self.query_one("#selector-list", OptionList).highlighted

    @staticmethod
    def _insert_position_for(idx: int, position: Literal["before", "after"]) -> int:
        return idx if position == "before" else idx + 1

    async def _paste_at(self, position: Literal["before", "after"]) -> None:
        # Ignore if clipboard is empty
        if self._clipboard is None:
            return

        # Determine target index for insertion
        idx = self._highlighted_index()
        if idx is None:
            target = 0 if position == "before" else len(self._sp.selectors)
        else:
            target = self._insert_position_for(idx, position)

        await self._sp.insert_selector(target, self._clipboard.model_copy(deep=True))
        self._refresh_list(target)

    def list_option_prompt(self, selector: Selector) -> Text:
        suffix = "" if selector.enabled else "-disabled"
        bullet = "●" if selector.enabled else "○"
        if selector.label:
            style = self.get_component_rich_style(
                f"selector-list--label{suffix}", partial=True
            )
            label = Text(selector.label, style=style)
        else:
            style = self.get_component_rich_style(
                f"selector-list--expression{suffix}", partial=True
            )
            label = Text(selector.expression, style=style)

        return Text.assemble(" ", bullet, " ", label)
