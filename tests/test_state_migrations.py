import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest

from jnav import state as app_state
from jnav.state_migrations import STATE_VERSION, Migration, migrate, v0_to_v1


def recording_migration(name: str) -> Migration:
    def step(data: dict[str, Any]) -> dict[str, Any]:
        steps = cast(list[str], data.get("steps", []))
        return {**data, "steps": [*steps, name]}

    return step


class TestMigrate:
    def test_applies_migrations_from_the_file_version_onward(self) -> None:
        migrations = [recording_migration("0to1"), recording_migration("1to2")]

        assert migrate({"version": 1}, migrations=migrations) == {
            "version": 2,
            "steps": ["1to2"],
        }

    def test_unversioned_data_starts_from_the_first_migration(self) -> None:
        migrations = [recording_migration("0to1"), recording_migration("1to2")]

        assert migrate({}, migrations=migrations) == {
            "version": 2,
            "steps": ["0to1", "1to2"],
        }

    def test_current_version_is_unchanged(self) -> None:
        data = {"version": STATE_VERSION, "search_term": "x"}

        assert migrate(data) == data

    def test_newer_version_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            migrate({"version": STATE_VERSION + 1})

    def test_state_from_a_newer_version_loads_as_default(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        path.write_text(json.dumps({"version": STATE_VERSION + 1}))

        assert app_state.load(path) == app_state.AppState()

    @pytest.mark.parametrize("version", [True, False, 1.0, "1", None, -1])
    def test_invalid_version_is_rejected(self, version: object) -> None:
        with pytest.raises(ValueError):
            migrate({"version": version})


class TestV0ToV1:
    def test_empty_state_is_unchanged(self) -> None:
        assert v0_to_v1.migrate({}) == {}

    def test_empty_selectors_stay_empty(self) -> None:
        assert v0_to_v1.migrate({"selectors": []}) == {"selectors": []}

    def test_nested_filter_tree_is_moved_as_is(self) -> None:
        tree = {
            "type": "group",
            "children": [
                {"type": "group", "children": [{"type": "leaf", "expr": ".a"}]}
            ],
        }

        assert v0_to_v1.migrate({"filter_tree": tree}) == {"filter_root": tree}

    def test_selector_keys_other_than_path_are_kept(self) -> None:
        migrated = v0_to_v1.migrate({"selectors": [{"path": ".a", "enabled": False}]})

        assert migrated == {"selectors": [{"enabled": False, "expression": ".a"}]}

    def test_unrelated_keys_pass_through(self) -> None:
        data = {"search_term": "x", "entry_index": 3, "detail_visible": True}

        assert v0_to_v1.migrate(data) == data

    def test_input_is_not_mutated(self) -> None:
        data = {
            "filter_tree": {"type": "group"},
            "selectors": [{"path": ".a", "enabled": True}],
            "filters_paused": True,
            "role_mapping": {},
        }
        snapshot = copy.deepcopy(data)

        _ = v0_to_v1.migrate(data)

        assert data == snapshot
