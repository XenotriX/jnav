# pyright: reportPrivateUsage=false

import pytest
from textual.app import App
from textual.widgets import OptionList

from jnav.field_mapping import RoleBinding, RoleMapping, TimeRoleBinding
from jnav.role_mapper import RoleMapper
from jnav.role_mapping_screen import _ROLE_LABELS, _ROLE_NAMES, RoleMappingScreen


class _Host(App[None]):
    def __init__(self, role_mapper: RoleMapper) -> None:
        super().__init__()
        self._rm = role_mapper

    def on_mount(self) -> None:
        self.push_screen(RoleMappingScreen(self._rm))


def _mapper() -> RoleMapper:
    rm = RoleMapper()
    rm._fallback = RoleMapping(
        timestamp=TimeRoleBinding(expression=".ts", format="iso8601"),
        level=RoleBinding(expression=".level"),
    )
    return rm


class TestRoleMappingScreen:
    @pytest.mark.asyncio
    async def test_highlight_maps_to_role(self) -> None:
        app = _Host(_mapper())
        async with app.run_test() as pilot:
            screen = app.screen
            assert isinstance(screen, RoleMappingScreen)
            await pilot.press("m", "j")
            assert screen._highlighted_role()[0] == "level"
            await pilot.press("j")
            assert screen._highlighted_role()[0] == "message"

    @pytest.mark.asyncio
    async def test_list_has_no_cursor_in_auto_mode(self) -> None:
        rm = _mapper()
        app = _Host(rm)
        async with app.run_test() as pilot:
            await pilot.pause()
            ol = app.screen.query_one("#role-list", OptionList)
            assert ol.highlighted is None
            await pilot.press("j", "k")
            assert ol.highlighted is None
            await pilot.press("m")
            await pilot.pause()
            assert ol.highlighted == 0
            await pilot.press("j", "m", "m")
            await pilot.pause()
            assert ol.highlighted == 1

    @pytest.mark.asyncio
    async def test_editing_is_locked_in_auto_mode(self) -> None:
        rm = _mapper()
        app = _Host(rm)
        async with app.run_test() as pilot:
            screen = app.screen
            assert isinstance(screen, RoleMappingScreen)
            for action in ("edit", "clear", "reset_role", "edit_format"):
                assert not screen.check_action(action, ())
            assert screen.check_action("toggle_mode", ())
            await pilot.press("d")
            await pilot.pause()
            assert rm.overrides is None

    @pytest.mark.asyncio
    async def test_unlock_starts_override_seeded_from_auto_detected(self) -> None:
        rm = _mapper()
        app = _Host(rm)
        async with app.run_test() as pilot:
            await pilot.press("m")
            await pilot.pause()
            assert rm.overrides == rm.fallback
            screen = app.screen
            assert isinstance(screen, RoleMappingScreen)
            assert screen.check_action("edit", ())
            assert screen.check_action("toggle_mode", ())

    @pytest.mark.asyncio
    async def test_unset_in_custom_mode_applies_without_confirmation(self) -> None:
        rm = _mapper()
        app = _Host(rm)
        async with app.run_test() as pilot:
            await pilot.press("m", "j", "d")
            await pilot.pause()
            assert rm.overrides is not None
            assert rm.overrides.level is None
            assert rm.overrides.timestamp == rm.fallback.timestamp

    @pytest.mark.asyncio
    async def test_reset_role_restores_auto_detected_binding(self) -> None:
        rm = _mapper()
        app = _Host(rm)
        async with app.run_test() as pilot:
            await pilot.press("m", "j", "d", "r")
            await pilot.pause()
            assert rm.overrides == rm.fallback

    @pytest.mark.asyncio
    async def test_locking_without_changes_needs_no_confirmation(self) -> None:
        rm = _mapper()
        app = _Host(rm)
        async with app.run_test() as pilot:
            await pilot.press("m", "m")
            await pilot.pause()
            assert rm.overrides is None

    @pytest.mark.asyncio
    async def test_locking_with_changes_asks_then_discards(self) -> None:
        rm = _mapper()
        app = _Host(rm)
        async with app.run_test() as pilot:
            await pilot.press("m", "j", "d", "m")
            await pilot.pause()
            assert rm.overrides is not None
            await pilot.press("enter")
            await pilot.pause()
            assert rm.overrides is None

    @pytest.mark.asyncio
    async def test_declining_lock_keeps_custom_mapping(self) -> None:
        rm = _mapper()
        app = _Host(rm)
        async with app.run_test() as pilot:
            await pilot.press("m", "j", "d", "m")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert rm.overrides is not None

    def test_every_role_has_a_label(self) -> None:
        assert set(_ROLE_LABELS) == set(_ROLE_NAMES)
