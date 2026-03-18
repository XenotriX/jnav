from __future__ import annotations

import json
import re
import sys
from collections import OrderedDict
from datetime import datetime

import click
import jq
from rich.text import Text
from rich.tree import Tree as RichTree
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    DataTable, Footer, Header, Input, ListItem, ListView, Static, Tree,
)
from textual.widgets.tree import TreeNode


PRIORITY_KEYS = ("timestamp", "ts", "time", "level", "severity", "message", "msg")
MAX_CELL_WIDTH = 50

LEVEL_COLORS = {
    "error": "red",
    "fatal": "red bold",
    "critical": "red bold",
    "warn": "yellow",
    "warning": "yellow",
    "info": "green",
    "debug": "dim",
    "trace": "dim",
}

TS_KEYS = {"timestamp", "ts", "time"}


def apply_jq_filter(
    expression: str, entries: list[dict],
) -> tuple[list[int], str | None]:
    try:
        prog = jq.compile(expression)
    except ValueError as e:
        return [], str(e)

    matched = []
    for i, entry in enumerate(entries):
        try:
            results = prog.input_value(entry).all()
            if any(_is_truthy(r) for r in results):
                matched.append(i)
        except Exception:
            continue
    return matched, None


_ASSIGNMENT_RE = re.compile(r'(?<![=!<>])=(?!=)')


def _check_filter_warning(expression: str) -> str | None:
    if _ASSIGNMENT_RE.search(expression):
        return "Did you mean '==' instead of '='? ('=' is jq's update operator)"
    return None


def _is_truthy(value: object) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, (list, dict, str)) and len(value) == 0:
        return False
    return True


def _get_nested(entry: dict, dotted_key: str) -> object:
    obj = entry
    for part in dotted_key.split("."):
        if isinstance(obj, dict):
            obj = obj.get(part, "")
        else:
            return ""
    return obj


def _flatten_keys(obj: dict, prefix: str = "") -> list[str]:
    keys = []
    for k, v in obj.items():
        full = f"{prefix}{k}"
        if isinstance(v, dict):
            for sub_k in v:
                keys.append(f"{full}.{sub_k}")
        else:
            keys.append(full)
    return keys


def _detect_all_columns(entries: list[dict]) -> list[str]:
    seen: OrderedDict[str, None] = OrderedDict()
    for entry in entries:
        for key in _flatten_keys(entry):
            if key not in seen:
                seen[key] = None
    return list(seen)


def _default_columns(all_columns: list[str]) -> list[str]:
    return [k for k in PRIORITY_KEYS if k in all_columns]


def _format_timestamp(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%H:%M:%S") + f".{dt.microsecond // 1000:03d}"
    except (ValueError, TypeError):
        return str(value)


def _truncate(value: object, width: int = MAX_CELL_WIDTH) -> str:
    s = str(value) if not isinstance(value, str) else value
    if len(s) > width:
        return s[: width - 1] + "\u2026"
    return s


def _style_level(value: str) -> Text:
    color = LEVEL_COLORS.get(value.lower(), "")
    return Text(value, style=color) if color else Text(value)


def _jq_value_literal(value: object) -> str:
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value)


# --- Textual Tree builder (interactive, for detail panel) ---

def _node_label(
    key: str, value: object, path: str, custom_selected: set[str],
) -> Text:
    is_custom = path in custom_selected
    key_style = "bold green" if is_custom else "bold"

    if isinstance(value, dict):
        return Text.assemble((key, key_style), ": ", ("{}", "dim"))
    elif isinstance(value, list):
        return Text.assemble(
            (key, key_style), ": ", (f"[{len(value)} items]", "dim"),
        )
    else:
        display = _truncate(str(value), 60)
        return Text.assemble((key, key_style), ": ", (display, ""))


def _sorted_keys(d: dict) -> list[str]:
    """Sort dict keys: priority keys first (in order), then the rest."""
    priority = [k for k in PRIORITY_KEYS if k in d]
    rest = [k for k in d if k not in priority]
    return priority + rest


def _build_tree(
    node: TreeNode, value: object, path: str = "",
    selected: set[str] | None = None,
) -> None:
    sel = selected or set()
    if isinstance(value, dict):
        for k in _sorted_keys(value):
            v = value[k]
            child_path = f"{path}.{k}" if path else k
            if isinstance(v, (dict, list)):
                branch = node.add(
                    _node_label(k, v, child_path, sel),
                    data={"path": child_path, "value": v},
                )
                _build_tree(branch, v, child_path, sel)
            else:
                node.add_leaf(
                    _node_label(k, v, child_path, sel),
                    data={"path": child_path, "value": v},
                )
    elif isinstance(value, list):
        for i, item in enumerate(value):
            child_path = f"{path}[{i}]"
            if isinstance(item, (dict, list)):
                branch = node.add(
                    Text.assemble((f"[{i}]", "dim")),
                    data={"path": child_path, "value": item},
                )
                _build_tree(branch, item, child_path, sel)
            else:
                display = _truncate(str(item), 60)
                node.add_leaf(
                    Text.assemble((f"[{i}]", "dim"), ": ", (display, "")),
                    data={"path": child_path, "value": item},
                )


# --- Rich Tree builder (static, for inline expanded view) ---

def _build_rich_tree(entry: dict, custom_selected: set[str]) -> RichTree:
    tree = RichTree("", guide_style="dim", hide_root=True)
    _populate_rich_tree(tree, entry, "", custom_selected)
    return tree


def _populate_rich_tree(
    node: RichTree, value: object, path: str, custom_selected: set[str],
) -> None:
    if isinstance(value, dict):
        for k in _sorted_keys(value):
            v = value[k]
            child_path = f"{path}.{k}" if path else k
            is_custom = child_path in custom_selected
            key_style = "bold green" if is_custom else "bold"
            if isinstance(v, dict):
                label = Text.assemble((k, key_style))
                branch = node.add(label)
                _populate_rich_tree(branch, v, child_path, custom_selected)
            elif isinstance(v, list):
                label = Text.assemble(
                    (k, key_style), (f" [{len(v)}]", "dim"),
                )
                branch = node.add(label)
                _populate_rich_tree(branch, v, child_path, custom_selected)
            else:
                display = _truncate(str(v), 60)
                label = Text.assemble(
                    (k, key_style), (": ", "dim"), (display, ""),
                )
                node.add(label)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            child_path = f"{path}[{i}]"
            if isinstance(item, (dict, list)):
                branch = node.add(Text(f"[{i}]", style="dim"))
                _populate_rich_tree(branch, item, child_path, custom_selected)
            else:
                display = _truncate(str(item), 60)
                node.add(
                    Text.assemble((f"[{i}]", "dim"), (": ", ""), (display, "")),
                )


def _entry_summary(entry: dict, columns: list[str], col_widths: list[int]) -> Text:
    """Format an entry as a fixed-width row matching table column layout."""
    parts: list[str | tuple[str, str]] = []
    for col, width in zip(columns, col_widths):
        val = _get_nested(entry, col)
        s = str(val) if val or val == 0 else ""
        if col in TS_KEYS:
            s = _format_timestamp(s)
        s = _truncate(s, width)
        cell = s.ljust(width)
        if col in ("level", "severity"):
            color = LEVEL_COLORS.get(s.strip().lower(), "")
            parts.append((cell, color))
        else:
            parts.append(cell)
        parts.append(" ")
    return Text.assemble(*parts) if parts else Text("(empty)")


def _compute_col_widths(
    entries: list[dict], indices: list[int], columns: list[str],
) -> list[int]:
    """Compute column widths based on header and data."""
    widths = [len(col) for col in columns]
    for i in indices:
        entry = entries[i]
        for j, col in enumerate(columns):
            val = _get_nested(entry, col)
            s = str(val) if val or val == 0 else ""
            if col in TS_KEYS:
                s = _format_timestamp(s)
            s = _truncate(s, MAX_CELL_WIDTH)
            widths[j] = max(widths[j], len(s))
    return [min(w, MAX_CELL_WIDTH) for w in widths]


# --- Widgets ---

class FilterBar(Static):
    pass


class LogEntryItem(ListItem):
    def __init__(self, entry_index: int, *children: Static) -> None:
        super().__init__(*children)
        self.entry_index = entry_index


class DetailTree(Tree):
    BINDINGS = [
        Binding("f", "add_filter", "Filter by"),
        Binding("s", "add_select", "Add column"),
        Binding("t", "toggle_filter_tree", "Selected only"),
    ]

    show_selected_only: bool = False

    def action_toggle_filter_tree(self) -> None:
        self.show_selected_only = not self.show_selected_only
        app: JnavApp = self.app
        if app._current_detail_entry is not None:
            app._update_detail(app._current_detail_entry)

    def action_add_filter(self) -> None:
        node = self.cursor_node
        if node is None or node.data is None:
            return
        path = node.data["path"]
        value = node.data["value"]
        if isinstance(value, (dict, list)):
            return
        app: JnavApp = self.app
        expr = f'.{path} == {_jq_value_literal(value)}'
        filter_input = app.query_one("#filter-input", Input)
        filter_input.value = expr
        app._apply_filter(expr)
        app._focus_main()

    def action_add_select(self) -> None:
        node = self.cursor_node
        if node is None or node.data is None:
            return
        app: JnavApp = self.app
        app.add_select(node.data["path"])


class JnavApp(App):
    CSS = """
    .input-row {
        height: 1;
        padding: 0 1;
        background: $surface;
    }
    .input-row.hidden {
        display: none;
    }
    .input-label {
        width: 5;
    }
    .input-row Input {
        width: 1fr;
        border: none;
        height: 1;
        padding: 0;
    }
    #filter-bar {
        height: 1;
        padding: 0 1;
        background: $panel;
        color: $text-muted;
    }
    #content-area {
        height: 1fr;
    }
    #log-table {
        width: 1fr;
    }
    #log-table.hidden {
        display: none;
    }
    #expanded-container {
        display: none;
        width: 1fr;
    }
    #expanded-container.visible {
        display: block;
    }
    #expanded-header {
        height: 1;
        padding: 0 1;
        background: $panel;
        text-style: bold;
    }
    #expanded-view {
        height: 1fr;
    }
    #expanded-view LogEntryItem {
        padding: 0 1;
    }
    .inline-tree {
        background: $surface-darken-1;
        padding: 0 0 0 4;
    }
    #detail-tree {
        width: 50;
        padding: 0 0 0 2;
        background: $surface-darken-1;
        border-left: tall $accent;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("slash", "focus_filter", "Filter", key_display="/"),
        Binding("c", "focus_columns", "Columns"),
        Binding("e", "toggle_expanded", "Expand"),
        Binding("escape", "escape", "Back"),
    ]

    def __init__(
        self,
        entries: list[dict],
        initial_filter: str = "",
    ) -> None:
        super().__init__()
        self.entries = entries
        self.initial_filter = initial_filter
        self.all_columns: list[str] = _detect_all_columns(entries)
        self.base_columns: list[str] = _default_columns(self.all_columns)
        self.columns: list[str] = self.base_columns
        self.visible_indices: list[int] = list(range(len(entries)))
        self._current_detail_entry: dict | None = None
        self._current_entry_index: int = 0
        self._expanded_mode: bool = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Static("jq> ", classes="input-label"),
            Input(
                placeholder="enter jq expression...",
                id="filter-input",
                value=self.initial_filter,
            ),
            classes="input-row hidden",
            id="filter-row",
        )
        yield Horizontal(
            Static("cols>", classes="input-label"),
            Input(
                placeholder="comma-separated fields, e.g. ts, data.role, message",
                id="columns-input",
            ),
            classes="input-row hidden",
            id="columns-row",
        )
        yield FilterBar(
            f"Showing {len(self.entries)}/{len(self.entries)} entries",
            id="filter-bar",
        )
        yield Horizontal(
            DataTable(id="log-table"),
            Vertical(
                Static("", id="expanded-header"),
                ListView(id="expanded-view"),
                id="expanded-container",
            ),
            DetailTree("entry", id="detail-tree"),
            id="content-area",
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#log-table", DataTable)
        table.cursor_type = "row"
        table.focus()
        self._rebuild_table()
        if self.initial_filter:
            self._apply_filter(self.initial_filter)
        if self.entries:
            self._update_detail(self.entries[0])

    def _custom_columns_set(self) -> set[str]:
        """Return only user-added columns (not base columns)."""
        return set(self.columns) - set(self.base_columns)

    def add_select(self, path: str) -> None:
        """Add a field as a column and filter to entries that have it."""
        columns_input = self.query_one("#columns-input", Input)
        current = columns_input.value.strip()
        existing = {
            c.strip().lstrip(".") for c in current.split(",") if c.strip()
        } if current else set()
        if path not in existing and path not in self.base_columns:
            if current:
                columns_input.value = f"{current}, {path}"
            else:
                columns_input.value = path
            extra = [
                c.strip().lstrip(".")
                for c in columns_input.value.split(",") if c.strip()
            ]
            self.columns = self.base_columns + [
                c for c in extra if c not in self.base_columns
            ]
            self._rebuild_table()
            if self._expanded_mode:
                self._rebuild_expanded()

        # Build a filter requiring all custom columns to be present
        custom = self._custom_columns_set()
        if custom:
            clauses = [f".{c} != null" for c in sorted(custom)]
            expr = " and ".join(clauses)
            filter_input = self.query_one("#filter-input", Input)
            filter_input.value = expr
            self._apply_filter(expr)

        if self._current_detail_entry:
            self._update_detail(self._current_detail_entry)
        self._focus_main()

    def _update_detail(self, entry: dict) -> None:
        self._current_detail_entry = entry
        tree = self.query_one("#detail-tree", DetailTree)
        tree.clear()
        sel = self._custom_columns_set()
        if tree.show_selected_only:
            tree.root.set_label("entry (selected)")
            filtered = {col: _get_nested(entry, col) for col in self.columns}
            _build_tree(tree.root, filtered, selected=sel)
        else:
            tree.root.set_label("entry")
            _build_tree(tree.root, entry, selected=sel)
        tree.root.expand_all()

    def _rebuild_table(self) -> None:
        table = self.query_one("#log-table", DataTable)
        table.clear(columns=True)
        for col in self.columns:
            table.add_column(col, key=col)
        self._populate_rows()

    def _populate_rows(self) -> None:
        table = self.query_one("#log-table", DataTable)
        table.clear()
        for i in self.visible_indices:
            entry = self.entries[i]
            row: list[str | Text] = []
            for col in self.columns:
                value = _get_nested(entry, col)
                if col in ("level", "severity"):
                    row.append(_style_level(_truncate(value)))
                elif col in TS_KEYS:
                    row.append(_format_timestamp(value))
                else:
                    row.append(_truncate(value))
            table.add_row(*row, key=str(i))

    def _rebuild_expanded(self) -> None:
        display_cols = self.base_columns
        col_widths = _compute_col_widths(
            self.entries, self.visible_indices, display_cols,
        )
        header_parts: list[str | tuple[str, str]] = []
        for col, width in zip(display_cols, col_widths):
            header_parts.append((col.ljust(width), "bold"))
            header_parts.append(" ")
        header = self.query_one("#expanded-header", Static)
        header.update(Text.assemble(*header_parts))

        lv = self.query_one("#expanded-view", ListView)
        lv.clear()
        custom = self._custom_columns_set()
        target_list_index = 0
        for list_idx, i in enumerate(self.visible_indices):
            entry = self.entries[i]
            summary = _entry_summary(entry, display_cols, col_widths)
            if custom:
                filtered = {col: _get_nested(entry, col) for col in custom}
                rich_tree = _build_rich_tree(filtered, custom)
            else:
                rich_tree = _build_rich_tree(entry, custom)
            item = LogEntryItem(
                i,
                Static(summary),
                Static(rich_tree, classes="inline-tree"),
            )
            lv.append(item)
            if i == self._current_entry_index:
                target_list_index = list_idx
        self._set_expanded_index(target_list_index)

    def _set_expanded_index(self, index: int) -> None:
        """Set the expanded view index after items are mounted."""
        def _do_set() -> None:
            lv = self.query_one("#expanded-view", ListView)
            lv.index = index
        self.call_after_refresh(_do_set)

    @on(Input.Submitted, "#filter-input")
    def on_filter_submitted(self, event: Input.Submitted) -> None:
        expression = event.value.strip()
        self._apply_filter(expression)
        self.query_one("#filter-row").add_class("hidden")
        self._focus_main()

    @on(Input.Submitted, "#columns-input")
    def on_columns_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        if raw:
            extra = [c.strip().lstrip(".") for c in raw.split(",") if c.strip()]
            self.columns = self.base_columns + [
                c for c in extra if c not in self.base_columns
            ]
        else:
            self.columns = self.base_columns
        self._rebuild_table()
        if self._expanded_mode:
            self._rebuild_expanded()
        if self._current_detail_entry:
            self._update_detail(self._current_detail_entry)
        self.query_one("#columns-row").add_class("hidden")
        self._focus_main()

    def _apply_filter(self, expression: str) -> None:
        bar = self.query_one("#filter-bar", FilterBar)

        if not expression:
            self.visible_indices = list(range(len(self.entries)))
            self._populate_rows()
            if self._expanded_mode:
                self._rebuild_expanded()
            bar.update(
                f"Showing {len(self.entries)}/{len(self.entries)} entries"
            )
            return

        warning = _check_filter_warning(expression)
        matched, error = apply_jq_filter(expression, self.entries)
        if error:
            bar.update(Text(f"Error: {error}", style="red"))
            return

        self.visible_indices = matched
        self._populate_rows()
        if self._expanded_mode:
            self._rebuild_expanded()
        status = f"Showing {len(matched)}/{len(self.entries)} entries"
        if warning:
            bar.update(Text(f"{status}  \u26a0 {warning}", style="yellow"))
        else:
            bar.update(status)

    def _focus_main(self) -> None:
        if self._expanded_mode:
            self.query_one("#expanded-view", ListView).focus()
        else:
            self.query_one("#log-table", DataTable).focus()

    def action_focus_filter(self) -> None:
        self.query_one("#filter-row").remove_class("hidden")
        self.query_one("#filter-input", Input).focus()

    def action_focus_columns(self) -> None:
        self.query_one("#columns-row").remove_class("hidden")
        self.query_one("#columns-input", Input).focus()

    def action_toggle_expanded(self) -> None:
        self._expanded_mode = not self._expanded_mode
        table = self.query_one("#log-table", DataTable)
        container = self.query_one("#expanded-container")
        ev = self.query_one("#expanded-view", ListView)
        if self._expanded_mode:
            table.add_class("hidden")
            container.add_class("visible")
            self._rebuild_expanded()
            ev.focus()
        else:
            container.remove_class("visible")
            table.remove_class("hidden")
            try:
                table.move_cursor(row=self.visible_indices.index(self._current_entry_index))
            except ValueError:
                pass
            table.focus()

    def action_escape(self) -> None:
        filter_input = self.query_one("#filter-input", Input)
        columns_input = self.query_one("#columns-input", Input)
        filter_row = self.query_one("#filter-row")
        columns_row = self.query_one("#columns-row")
        tree = self.query_one("#detail-tree", DetailTree)

        if self.screen.focused == filter_input:
            filter_row.add_class("hidden")
            self._focus_main()
            return

        if self.screen.focused == columns_input:
            columns_row.add_class("hidden")
            self._focus_main()
            return

        if self.screen.focused == tree:
            self._focus_main()
            return

        filter_input.value = ""
        columns_input.value = ""
        filter_row.add_class("hidden")
        columns_row.add_class("hidden")
        self.columns = self.base_columns
        self._rebuild_table()
        if self._expanded_mode:
            self._rebuild_expanded()
        self._apply_filter("")

    @on(DataTable.RowHighlighted, "#log-table")
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key and event.row_key.value is not None:
            self._current_entry_index = int(event.row_key.value)
            self._update_detail(self.entries[self._current_entry_index])

    @on(DataTable.RowSelected, "#log-table")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        self.query_one("#detail-tree", DetailTree).focus()

    @on(ListView.Highlighted, "#expanded-view")
    def on_expanded_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item and isinstance(event.item, LogEntryItem):
            self._current_entry_index = event.item.entry_index
            self._update_detail(self.entries[self._current_entry_index])

    @on(ListView.Selected, "#expanded-view")
    def on_expanded_selected(self, event: ListView.Selected) -> None:
        self.query_one("#detail-tree", DetailTree).focus()


def _parse_entries(lines: list[str]) -> list[dict]:
    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                entries.append(obj)
        except json.JSONDecodeError:
            continue
    return entries


@click.command()
@click.argument("file", required=False, type=click.Path(exists=True))
@click.option("-f", "--filter", "initial_filter", default="", help="Initial jq filter expression")
def main(file: str | None, initial_filter: str) -> None:
    """Interactive JSON log viewer with jq filtering."""
    if file:
        with open(file) as f:
            lines = f.readlines()
    elif not sys.stdin.isatty():
        lines = sys.stdin.readlines()
        sys.stdin.close()
        sys.stdin = open("/dev/tty")
    else:
        click.echo("Usage: jnav [FILE] or pipe JSONL via stdin", err=True)
        raise SystemExit(1)

    entries = _parse_entries(lines)
    if not entries:
        click.echo("No valid JSON entries found.", err=True)
        raise SystemExit(1)

    app = JnavApp(entries=entries, initial_filter=initial_filter)
    app.title = "jnav"
    app.run()


if __name__ == "__main__":
    main()
