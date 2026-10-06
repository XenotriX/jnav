import json
from pathlib import Path

import pytest

from jnav import state as app_state
from jnav.field_mapping import RoleBinding, RoleMapping
from jnav.filtering import Filter, FilterGroup
from jnav.selector_provider import Selector
from jnav.state_migrations import STATE_VERSION

V1_0_0_STATE = {
    "filter_tree": {
        "type": "group",
        "operator": "or",
        "enabled": True,
        "negated": False,
        "label": None,
        "collapsed": False,
        "children": [
            {
                "type": "leaf",
                "expr": '.level == "error"',
                "enabled": True,
                "negated": False,
                "label": None,
            }
        ],
    },
    "selectors": [
        {"path": ".data.role", "enabled": True},
        {"path": ".data.id", "enabled": False},
    ],
    "role_mapping": {
        "timestamp": {"path": "ts", "format": "iso8601"},
        "level": "level",
        "message": "message",
    },
    "expanded_mode": False,
    "filters_paused": True,
    "search_term": "boom",
    "entry_index": 7,
    "detail_visible": True,
    "show_selected_only": True,
}


class TestLoad:
    def test_missing_file_gives_default_state(self, tmp_path: Path) -> None:
        assert app_state.load(tmp_path / "missing.json") == app_state.AppState()

    def test_invalid_json_gives_default_state(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        path.write_text("{not json")

        assert app_state.load(path) == app_state.AppState()

    def test_current_state_round_trips(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        state = app_state.AppState(
            selectors=[Selector(expression=".a", label="A")],
            role_overrides=RoleMapping(message=RoleBinding(expression=".msg")),
            search_term="x",
        )

        app_state.save(path, state)

        assert app_state.load(path) == state

    def test_saved_state_carries_current_version(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"

        app_state.save(path, app_state.AppState())

        assert json.loads(path.read_text())["version"] == STATE_VERSION


class TestLoadFallback:
    @pytest.mark.parametrize("content", ["[]", '"x"', "3", "null"])
    def test_non_object_json_gives_default_state(
        self, tmp_path: Path, content: str
    ) -> None:
        path = tmp_path / "state.json"
        path.write_text(content)

        assert app_state.load(path) == app_state.AppState()

    def test_v1_0_0_selector_without_path_gives_default_state(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "state.json"
        path.write_text(json.dumps({"selectors": [{"enabled": True}]}))

        assert app_state.load(path) == app_state.AppState()

    def test_v1_0_0_invalid_filter_tree_gives_default_state(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "state.json"
        path.write_text(json.dumps({"filter_tree": {"type": "bogus"}}))

        assert app_state.load(path) == app_state.AppState()


class TestV1_0_0Migration:
    def load_v1_0_0(self, tmp_path: Path) -> app_state.AppState:
        path = tmp_path / "state.json"
        path.write_text(json.dumps(V1_0_0_STATE))
        return app_state.load(path)

    def test_filter_tree_is_kept(self, tmp_path: Path) -> None:
        state = self.load_v1_0_0(tmp_path)

        assert state.filter_root == FilterGroup(
            operator="or",
            children=[Filter(expr='.level == "error"')],
        )

    def test_selectors_are_kept(self, tmp_path: Path) -> None:
        state = self.load_v1_0_0(tmp_path)

        assert state.selectors == [
            Selector(expression=".data.role", enabled=True),
            Selector(expression=".data.id", enabled=False),
        ]

    def test_paused_filters_disable_filtering(self, tmp_path: Path) -> None:
        assert self.load_v1_0_0(tmp_path).filtering_enabled is False

    def test_unpaused_filters_enable_filtering(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        path.write_text(json.dumps({**V1_0_0_STATE, "filters_paused": False}))

        assert app_state.load(path).filtering_enabled is True

    def test_role_mapping_is_dropped(self, tmp_path: Path) -> None:
        assert self.load_v1_0_0(tmp_path).role_overrides is None

    def test_unchanged_fields_are_kept(self, tmp_path: Path) -> None:
        state = self.load_v1_0_0(tmp_path)

        assert state.expanded_mode is False
        assert state.search_term == "boom"
        assert state.entry_index == 7
        assert state.detail_visible is True
        assert state.show_selected_only is True

    def test_migrated_state_is_current_version(self, tmp_path: Path) -> None:
        assert self.load_v1_0_0(tmp_path).version == STATE_VERSION

    def test_minimal_state_loads_with_defaults(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        path.write_text(json.dumps({"search_term": "x"}))

        assert app_state.load(path) == app_state.AppState(search_term="x")

    def test_collapsed_paths_default_to_empty(self, tmp_path: Path) -> None:
        assert self.load_v1_0_0(tmp_path).collapsed_paths == set()

    def test_migrated_state_reloads_unchanged_after_saving(
        self, tmp_path: Path
    ) -> None:
        migrated = self.load_v1_0_0(tmp_path)
        resaved = tmp_path / "resaved.json"

        app_state.save(resaved, migrated)

        assert app_state.load(resaved) == migrated
