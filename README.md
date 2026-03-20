# jnav

> **Proof of concept** — this project was developed as an experiment with heavy use of a coding agent. It is functional but not production-hardened.

Interactive JSON log viewer with jq filtering. Navigate, search, filter, and inspect structured logs in the terminal.

Inspired by [lnav](https://github.com/tstack/lnav), but focused on JSON/JSONL logs with jq as the filter language.

<video src="https://github.com/user-attachments/assets/4632f8f5-1982-41c5-878f-9c01fe75bb68" autoplay loop muted playsinline></video>

## Install

```
uv tool install .
```

## Usage

```bash
# Open a log file (with live tailing)
jnav app.log

# Pipe from stdin
cat logs.jsonl | jnav

# Start with a filter
jnav -f '.level == "error"' app.log
```

## Keybindings

### Navigation

| Key | Action |
|-----|--------|
| `j` / `k` | Move up/down (or arrow keys) |
| `g` / `G` | Jump to first/last entry |
| `Ctrl+D` / `Ctrl+U` | Half-page scroll |
| `h` / `l` | Switch focus between list and detail panel |
| `Enter` | Open detail panel and inspect entry |
| `Escape` | Return to list / clear search |

### Search and Filter

| Key | Action |
|-----|--------|
| `/` | Search (highlights matches, does not hide entries) |
| `n` / `N` | Next/previous search match |
| `f` | Manage filters (hides non-matching entries) |
| `Ctrl+F` | Quick add text filter (AND) |
| `Ctrl+S` | Quick add text filter (OR) |
| `Space` | Pause/unpause all filters |
| `r` | Reset filters, fields, and search |

### Display

| Key | Action |
|-----|--------|
| `e` | Toggle expanded view (inline field trees) |
| `d` | Toggle detail panel |
| `c` | Manage selected fields |
| `y` | Copy current entry as JSON |
| `?` | Help |
| `q` | Quit |

### Detail Panel

| Key | Action |
|-----|--------|
| `f` then `f` | Filter by value (AND) |
| `f` then `o` | Filter by value (OR) |
| `f` then `n` | Has field filter (AND) |
| `f` then `N` | Has field filter (OR) |
| `s` | Select field for display |
| `v` | View value in `$EDITOR` |
| `t` | Toggle: show only selected fields |

### Filter/Field Manager

| Key | Action |
|-----|--------|
| `a` | Add new entry |
| `e` | Edit highlighted entry |
| `Space` | Toggle enabled/disabled |
| `o` | Toggle AND/OR (filters only) |
| `d` | Delete |
| `Escape` | Close |

## Features

### Filtering

Filters use [jq](https://jqlang.github.io/jq/) expressions. They hide entries that don't match. Multiple AND filters are combined, OR filters are unioned with the AND group. Examples:

```
.level == "error"
.message | test("timeout")
.status >= 500
.data.user_id == "abc123"
```

### Search

`/` opens a non-destructive search. Matching entries are highlighted in the list and detail tree. Use `n`/`N` to jump between matches. `Escape` clears the search.

### Field Selection

Select fields with `s` in the detail panel or `c` to open the field manager. Selected fields appear as columns in the table view and as inline trees in expanded mode.

Field paths support jq syntax for array iteration:

```
data.role                              # simple path
state.messages[0].content              # array index
state.messages[].content               # all array elements
state.messages[] | {role, content}     # multiple fields per element
```

### JSON String Expansion

Values that are JSON-encoded strings (e.g. `"data": "{\"key\": \"value\"}"`) are automatically parsed and displayed as nested objects. The tree view shows `"{}"` in orange italic to distinguish them from real objects. Filters and field selection work through expanded JSON strings transparently.

### Live Tailing

When opening a file, jnav watches it for new lines (like `tail -f`). New entries are parsed, filtered, and appended to the view. If you're at the bottom of the list, it auto-scrolls to show new entries.

### Session Persistence

Filters, selected fields, scroll position, panel state, and search terms are saved when you quit and restored when reopening the same file. State is stored in `~/.local/share/jnav/`.
