# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Support for any JSONL file, not just log records. Lines whose top-level value is not an object, such as arrays, strings or numbers, are shown instead of skipped. When no timestamp, level or message is detected, the summary shows the whole entry. Nested fields can be detected as the timestamp, level or message.
- A Field Roles dialog that shows which fields jnav uses as the timestamp, level and message, and lets you override them or restore the detected ones. Overrides are saved with the file's session. Open it with `vR` or from the command palette.
- A command palette (`Ctrl+P`) to open the filter manager, the selected fields manager or the Field Roles dialog, reset, take a screenshot, or quit.
- Custom names for selected fields, set with `r` in the selected fields manager. The name is shown instead of the jq expression in the manager, the log list and the detail panel.
- `P` pastes a filter or selected field above the cursor, as the counterpart to `p`. On a group, it pastes before the group.
- Collapsing a field in the detail panel collapses the same field in every entry. The collapsed fields are saved with the file's session.

### Changed

- `r` asks for confirmation before resetting filters, selected fields and search.
- The top line of the detail panel shows the same summary as the log list, instead of the entry number and timestamp.
- The cursor in the detail panel and filter manager is a subtle background highlight that keeps field colors readable.
- `p` on a group in the filter manager pastes as its first child when the group is expanded, and after it when collapsed. It used to paste as the group's last child.
- Pasting no longer empties the clipboard, so the same filter or selected field can be pasted several times.
- JSON strings that encode an empty object or array, such as `"{}"`, are expanded like other JSON strings.

### Fixed

- Messages that are not strings are shown in the summary as compact JSON, such as `{"a":1}`, `false` or `null`, instead of Python-style values like `{'a': 1}` or `False`.
- Filters and selected fields created from the detail panel work for keys that are not plain identifiers, such as `@timestamp` or `user-id`.
- Selected fields are shown in the order of the selected fields manager, both in the log list and in the detail panel. Their order used to be random, could change between runs, and did not follow reordering.
- Cutting and pasting a disabled selected field keeps it disabled.
- Multi-line messages no longer break the log list layout. Line breaks are shown as `↵`.
- The detail panel shows the first entry on startup when it was left open in the previous session.
- Reopening a file puts the cursor back on the entry it was on when the file was closed. If the file got shorter, the cursor goes to the last entry.
- The key hints at the bottom of the filter manager no longer jump in size when it opens.

## [1.0.0] - 2026-04-20

First release.

### Added

- Open a JSONL log file, or read entries from stdin.
- `--follow` to watch a file for new entries, like `tail -f`.
- A one-line summary per entry, built from its automatically detected timestamp, level and message, with a color per log level.
- A detail panel that shows the highlighted entry as a tree, with JSON-encoded strings expanded into nested objects.
- Filters written as jq expressions, combined in AND/OR groups that can be negated, with a preview of the resulting jq expression.
- Quick filters by text, by the value of a field, or by whether a field exists.
- Pausing and resuming all filters.
- Selected fields: jq expressions shown next to each entry's summary, managed in a dedicated screen where they can be reordered and toggled.
- An option to show only the selected fields in the detail panel.
- Search that highlights matches and jumps between them.
- Opening a field's value in `$EDITOR`.
- Vim-style keybindings, and a help screen that lists them.
- Filters, selected fields, panel state and search are saved per file and restored when it is reopened.
- `r` to reset filters, selected fields and search.
- `--version` to print the version.

[Unreleased]: https://github.com/XenotriX/jnav/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/XenotriX/jnav/releases/tag/v1.0.0
