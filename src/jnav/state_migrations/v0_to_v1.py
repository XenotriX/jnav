from typing import Any

_REMOVED_KEYS = {"filter_tree", "filters_paused", "role_mapping"}


def migrate(data: dict[str, Any]) -> dict[str, Any]:
    """Convert the unversioned state written by v1.0.0."""
    migrated = {k: v for k, v in data.items() if k not in _REMOVED_KEYS}
    if "filter_tree" in data:
        migrated["filter_root"] = data["filter_tree"]
    if "selectors" in data:
        migrated["selectors"] = [
            {**{k: v for k, v in s.items() if k != "path"}, "expression": s["path"]}
            for s in data["selectors"]
        ]
    if "filters_paused" in data:
        migrated["filtering_enabled"] = not data["filters_paused"]
    return migrated
