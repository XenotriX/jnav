from typing import TYPE_CHECKING, ClassVar, get_args, override

from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.content import Content
from textual.screen import ModalScreen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from jnav.confirm_modal import ConfirmModal
from jnav.field_mapping import (
    RoleBinding,
    RoleMapping,
    TimeRoleBinding,
    TimestampFormat,
)
from jnav.modal import Modal
from jnav.role_mapper import RoleMapper
from jnav.text_input_screen import TextInputScreen

if TYPE_CHECKING:
    from textual import getters
    from textual.app import App


_ROLE_NAMES: tuple[str, ...] = tuple(RoleMapping.model_fields.keys())

_ROLE_LABELS: dict[str, str] = {
    "timestamp": "Timestamp",
    "level": "Log level",
    "message": "Message",
}

_GUTTER_WIDTH = 3

_CALLOUT_TEXT = "These roles are detected automatically. Switch to Custom to edit them."

_MODE_HINT = "[bold $primary]m[/bold $primary]  Switch mode"

_TIMESTAMP_FORMATS: tuple[TimestampFormat, ...] = get_args(TimestampFormat)


class FormatPickerScreen(ModalScreen[TimestampFormat | None]):
    DEFAULT_CSS = """
    FormatPickerScreen {
        align: center middle;
    }
    FormatPickerScreen #format-list {
        width: 30;
        height: auto;
        max-height: 70%;
        border: round $primary;
        background: $background;
        padding: 0 1;

        & > .option-list--option-highlighted {
            background: $background-darken-1;
        }
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "close", show=False),
        Binding("q", "close", show=False),
        Binding("ctrl+c", "close", show=False),
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
    ]

    def __init__(self, current: TimestampFormat | None = None) -> None:
        super().__init__()
        self._current = current

    @override
    def compose(self) -> ComposeResult:
        yield OptionList(id="format-list")

    def on_mount(self) -> None:
        ol = self.query_one("#format-list", OptionList)
        ol.border_title = "Timestamp format"
        for fmt in _TIMESTAMP_FORMATS:
            ol.add_option(Option(fmt))
        if self._current is not None:
            ol.highlighted = _TIMESTAMP_FORMATS.index(self._current)
        ol.focus()

    @on(OptionList.OptionSelected, "#format-list")
    def on_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(_TIMESTAMP_FORMATS[event.option_index])

    def action_close(self) -> None:
        self.dismiss(None)

    def action_cursor_down(self) -> None:
        self.query_one("#format-list", OptionList).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#format-list", OptionList).action_cursor_up()


class RoleMappingScreen(Modal):
    if TYPE_CHECKING:
        app = getters.app(App[None])

    COMPONENT_CLASSES: ClassVar[set[str]] = {
        "role-list--name",
        "role-list--arrow",
        "role-list--expression-changed",
        "role-list--expression",
        "role-list--unset",
        "role-list--format",
        "role-list--auto",
        "role-list--marker",
    }

    DEFAULT_CSS = """
    RoleMappingScreen .modal-box {
        max-height: 90%;
    }
    #mode-indicator {
        width: 100%;
        content-align: center middle;
    }
    #mode-hint {
        width: 100%;
        content-align: center middle;
        margin-bottom: 1;
    }
    #callout {
        border: round $warning;
        border-title-color: $warning;
        padding: 0 1;
        margin-bottom: 1;
        height: auto;
    }
    #role-list {
        height: auto;
        max-height: 20;
        border: none;
        background: transparent;
        padding: 0;

        & > .option-list--option-highlighted {
            background: $background-darken-1;
        }
    }
    .role-list--name {
        color: $foreground;
        text-style: bold;
    }
    .role-list--arrow {
        color: $foreground 40%;
    }
    .role-list--expression {
        color: $primary;
    }
    .role-list--expression-changed {
        color: $primary;
        text-style: bold;
    }
    .role-list--unset {
        color: $foreground;
        text-style: dim italic;
    }
    .role-list--format {
        color: $foreground;
        text-style: dim;
    }
    .role-list--auto {
        color: $foreground;
        text-style: dim italic;
    }
    .role-list--marker {
        color: $warning;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("m", "toggle_mode", show=False),
        Binding("e", "edit", "Edit"),
        Binding("d", "clear", "Clear"),
        Binding("r", "reset_role", "Restore detected"),
        Binding("f", "edit_format", "Change format"),
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
    ]

    modal_title = "Field Roles"
    modal_width = 60
    footer_columns = 2

    def __init__(self, role_mapper: RoleMapper) -> None:
        super().__init__()
        self._rm = role_mapper
        self._cursor = 0

    @override
    def compose_body(self) -> ComposeResult:
        yield Static(id="mode-indicator")
        yield Static(_MODE_HINT, id="mode-hint")
        yield Static(id="callout")
        yield OptionList(id="role-list")

    @override
    def on_mount(self) -> None:
        self.call_after_refresh(self._refresh)

    @override
    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        del parameters
        editing = self._rm.overrides is not None
        match action:
            case "cursor_down" | "cursor_up":
                return editing
            case "lock":
                return editing
            case "edit" | "clear" | "reset_role" | "edit_format":
                if not editing:
                    return False
            case _:
                return True
        ol = self.query_one("#role-list", OptionList)
        if ol.highlighted is None:
            return True
        role, current = self._highlighted_role()
        match action:
            case "clear":
                return current is not None or None
            case "reset_role":
                return current != self._rm.fallback.get(role) or None
            case "edit_format":
                return isinstance(current, TimeRoleBinding) or None
            case _:
                return True

    @on(OptionList.OptionHighlighted, "#role-list")
    def on_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        self._cursor = event.option_index
        self.refresh_bindings()

    def action_cursor_down(self) -> None:
        self.query_one("#role-list", OptionList).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#role-list", OptionList).action_cursor_up()

    @work
    async def action_toggle_mode(self) -> None:
        overrides = self._rm.overrides
        if overrides is None:
            await self._apply(self._rm.fallback.model_copy(deep=True))
            return
        blocks = [
            diff
            for name, binding in overrides
            if (
                diff := self._format_role_diff(
                    name, binding, self._rm.fallback.get(name)
                )
            )
            is not None
        ]
        if blocks and not await self._confirm_diff(
            "Back to auto-detect?",
            "This will discard your custom mapping.",
            *blocks,
        ):
            return
        await self._apply(None)

    @work
    async def action_edit(self) -> None:
        role, current = self._highlighted_role()
        initial = current.expression if current is not None else ""

        async def on_dismiss(value: str | None) -> None:
            if not value or (current is not None and value == current.expression):
                return
            await self._commit_role(role, self._with_expression(role, value))

        self.app.push_screen(
            TextInputScreen(
                f"Edit {_ROLE_LABELS[role]}",
                placeholder="jq expression...",
                initial_value=initial,
            ),
            on_dismiss,
        )

    @work
    async def action_reset_role(self) -> None:
        role, _ = self._highlighted_role()
        await self._commit_role(role, self._rm.fallback.get(role))

    @work
    async def action_clear(self) -> None:
        role, _ = self._highlighted_role()
        await self._commit_role(role, None)

    @work
    async def action_edit_format(self) -> None:
        role, current = self._highlighted_role()
        if not isinstance(current, TimeRoleBinding):
            return

        async def on_dismiss(fmt: TimestampFormat | None) -> None:
            if fmt is None or fmt == current.format:
                return
            await self._commit_role(
                role, TimeRoleBinding(expression=current.expression, format=fmt)
            )

        self.app.push_screen(FormatPickerScreen(current.format), on_dismiss)

    def _highlighted_role(self) -> tuple[str, RoleBinding | None]:
        idx = self.query_one("#role-list", OptionList).highlighted
        assert idx is not None
        name = _ROLE_NAMES[idx]
        return name, (self._rm.overrides or self._rm.fallback).get(name)

    def _with_expression(self, role: str, value: str) -> RoleBinding:
        if role == "timestamp":
            overrides = self._rm.overrides
            current = overrides.timestamp if overrides is not None else None
            fmt = current.format if current is not None else "iso8601"
            return TimeRoleBinding(expression=value, format=fmt)
        return RoleBinding(expression=value)

    async def _commit_role(self, role: str, binding: RoleBinding | None) -> None:
        overrides = self._rm.overrides
        if overrides is None or overrides.get(role) == binding:
            return
        await self._apply(overrides.model_copy(update={role: binding}))

    async def _confirm_diff(self, title: str, *blocks: str | Content) -> bool:
        return bool(
            await self.app.push_screen_wait(
                ConfirmModal(title=title, prompt=Content("\n\n").join(blocks))
            )
        )

    async def _apply(self, mapping: RoleMapping | None) -> None:
        await self._rm.set_overrides(mapping)
        self._refresh()

    def _refresh(self) -> None:
        self._refresh_header()
        self._refresh_list()
        self.refresh_bindings()

    def _refresh_header(self) -> None:
        overrides = self._rm.overrides
        editing = overrides is not None
        active, dim = "bold $primary", "dim"
        auto_style, custom_style = (dim, active) if editing else (active, dim)
        auto_dot, custom_dot = ("\u25cb", "\u25cf") if editing else ("\u25cf", "\u25cb")
        self.query_one("#mode-indicator", Static).update(
            f"[{auto_style}]{auto_dot} Auto-detected[/]    [{custom_style}]{custom_dot} Custom[/]"
        )
        callout = self.query_one("#callout", Static)
        callout.border_title = "Read-only"
        callout.update(_CALLOUT_TEXT)
        callout.display = not editing

    def _refresh_list(self) -> None:
        ol = self.query_one("#role-list", OptionList)
        editing = self._rm.overrides is not None
        cursor = min(self._cursor, len(_ROLE_NAMES) - 1) if editing else None
        ol.clear_options()
        for name, binding in self._rm.overrides or self._rm.fallback:
            ol.add_option(Option(self._format_row(name, binding)))
        ol.can_focus = editing
        ol.highlighted = cursor
        if editing:
            ol.focus()

    def _format_row(self, name: str, binding: RoleBinding | None) -> RenderableType:
        style = self.get_component_rich_style
        auto = self._rm.fallback.get(name)
        editing = self._rm.overrides is not None
        changed = editing and binding != auto

        if changed:
            marker = Text("\u25cf", style=style("role-list--marker", partial=True))
        else:
            marker = Text("\u25cb" if editing else "")

        header = Table.grid(expand=True)
        header.add_column(width=_GUTTER_WIDTH)
        header.add_column(ratio=1)
        header.add_column(justify="right", no_wrap=True)
        header.add_row(
            Text(" ").append_text(marker),
            Text(_ROLE_LABELS[name], style=style("role-list--name", partial=True)),
            Text(binding.format, style=style("role-list--format", partial=True))
            if isinstance(binding, TimeRoleBinding)
            else "",
        )

        if binding is None:
            value = Text(
                "(unset)" if editing else "not detected",
                style=style("role-list--unset", partial=True),
            )
        else:
            value = Text(
                binding.expression,
                style=style(
                    "role-list--expression-changed"
                    if changed
                    else "role-list--expression",
                    partial=True,
                ),
            )

        body = Table.grid(expand=True)
        body.add_column(width=_GUTTER_WIDTH)
        body.add_column(width=2)
        body.add_column(ratio=1)
        body.add_row(
            "", Text("\u2192", style=style("role-list--arrow", partial=True)), value
        )
        if changed:
            detected = (
                f"detected: {auto.expression}"
                if auto is not None
                else "nothing detected"
            )
            detected_line = Table.grid(expand=True)
            detected_line.add_column(width=_GUTTER_WIDTH)
            detected_line.add_column(ratio=1)
            detected_line.add_row(
                "",
                Text(
                    detected,
                    style=style("role-list--auto", partial=True),
                ),
            )
            return Group(header, body, detected_line, "")
        return Group(header, body, "")

    def _format_role_diff(
        self,
        role: str,
        current: RoleBinding | None,
        new: RoleBinding | None,
    ) -> Content | None:
        if current == new:
            return None
        return Content("\n").join([
            Content.styled(_ROLE_LABELS[role], "bold"),
            Content.assemble(
                "  ", ("-", "$error"), " ", self._binding_content(current)
            ),
            Content.assemble("  ", ("+", "$success"), " ", self._binding_content(new)),
        ])

    def _binding_content(self, binding: RoleBinding | None) -> Content:
        if binding is None:
            return Content.styled("(unset)", "dim italic")
        expression = Content.styled(binding.expression, "$primary")
        if isinstance(binding, TimeRoleBinding):
            return Content.assemble(expression, "  ", (binding.format, "dim"))
        return expression
