# jnav

Textual TUI for navigating JSON logs. Python >= 3.14, managed with uv.

Released 1.0.0 on 2026-04-17 (GPL-3.0-only, on PyPI). Follow semver: breaking changes need a major bump.

Stack: Textual, jq for both filters and selectors, aioreactive pipeline, orjson parsing, pydantic models for the filter tree, platformdirs for session state. The theme uses the Open Color palette and only standard Unicode glyphs (no Nerd Font glyphs).

## Commands

- `just test [TEST]`, `just coverage`, `just format`
- `just check` runs every lefthook pre-commit hook on all files: em-dash check, `ruff format`, `ruff check --fix`, `basedpyright src/ tests/`, `pytest`
- The type-checker is basedpyright, not pyright

## Code style

- No em-dashes anywhere (lefthook rejects them). Use colons, commas or periods.
- No section-heading comments, dashed separators, or module docstrings.
- Unused arguments: keep the name and add `del arg  # unused` instead of renaming to `_arg`.
- Functions with more than 2-3 parameters: make them keyword-only (`*`), one per line.
- Don't silence the type-checker (`# pyright: ignore[...]`, `# type: ignore`) when a proper fix exists, e.g. `@override` or a missing annotation.
- Textual custom widget messages: use `@on(Widget.Message)` rather than `on_<widget>_<message>` methods, and convert existing ones in files you are already editing. Lifecycle and event hooks (`on_mount`, `on_key`, `on_focus`, ...) keep the implicit form.
- Test comments and docstrings describe the expected behavior, not the bug, the heuristic that misfires, or why a test currently fails.

## Terminology

Use these terms consistently in code, docs, and UI text.

- **Entry**: one JSON log line. Its `raw` form is the original line, its `expanded` form has JSON string expansion applied.
- **JSON string expansion**: string values that contain JSON are parsed and shown as nested values. The tree marks them with an italic `"{}"`. Filters and selectors see the expanded form.
- **Field**: a path to a value inside an entry (`NodePath`), written as a jq path like `.data.user_id`.
- **Summary**: the one-line rendering of an entry in the list, built from the timestamp, level, and message roles.
- **Field roles**: the timestamp, log level, and message roles, each bound to the field that fills that part of the summary. The timestamp role also has a format (`iso8601`, `epoch_s`, `epoch_ms`, `epoch_us`, `epoch_ns`). Roles are either auto-detected or custom (user overrides), edited in the Field Roles screen.
- **Selector**: a jq expression evaluated per entry. Its results are the **selected fields**, rendered inline next to the summary and managed in the selected fields manager. Never call them "columns".
- **Filter**: a jq expression that decides whether an entry is shown. A single filter is a **clause**. Clauses nest in AND/OR **groups**, forming the **filter tree**, which compiles to one jq expression. Clauses and groups can be enabled, negated, and labeled. Filters can be paused as a whole. They are managed in the filter manager.
- **Search**: highlights matching entries without hiding any. Hiding entries is always a filter, never a search.
- **List panel** and **detail panel**: the entry list and the tree view of the highlighted entry. The **inline tree** is the optional expanded tree shown inside list rows.
- **Highlighted entry**: the entry under the cursor in the list.
- **Follow** (`--follow`): live tailing of a file for new entries.
- **Session state**: per-file filters, selected fields, highlighted entry, panel state, and search term, saved on quit and restored on reopen.
- **Cut / yank / paste**: the clipboard actions in the filter and selected fields managers (not copy/paste).

## Commits

- `feat:` is reserved for user-facing features and changes. Internal capabilities, APIs, or infrastructure that users can't see use another type.
- Don't use `style:`. Formatter or lint cleanup is `refactor:`, and housekeeping (dead code, tooling bumps) is `chore:`. Changing user-visible behavior is never `chore:` (disabling a feature is `feat:`).
- `fix:` is only for bugs present in the last release, so every `fix:` commit matches a Fixed changelog entry. For a bug introduced since the last tag (`git log $(git describe --tags --abbrev=0)..HEAD`), use another type that fits the change.

## Changelog

`CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/en/2.0.0/) and must always be up to date. Every user-facing change updates the `[Unreleased]` section in the same commit, which means every `feat:` and `fix:` commit touches it.

- Use **Added** for new capabilities, **Changed** for changes to existing behavior, and **Fixed** for bugs present in the last release. Add **Removed** or **Deprecated** when needed.
- Compare against the last release, not HEAD. A change or fix to something that is still unreleased edits its existing entry instead of adding a new one.
- Write for users in full sentences. Describe the behavior, not the implementation: no class names, file names, commit types, or hashes. Put keys and expressions in backticks.
- Fixed entries describe the correct behavior, optionally followed by what used to happen ("... instead of ...").
- Purely internal changes (`refactor:`, `perf:` without a noticeable effect, `chore:`, `test:`, `docs:`) are not listed.
- Use the names from the Terminology section.

## Demos

`demos/` holds VHS recordings with PEP 723 generator scripts (see `demos/README.md`). An overview demo was attempted but VHS can't reliably script the deep detail-tree navigation it needs.
