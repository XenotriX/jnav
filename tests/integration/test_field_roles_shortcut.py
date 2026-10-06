# pyright: reportPrivateUsage=false

import pytest

from jnav.detail_tree import DetailTree
from jnav.log_list_view import LogListView
from jnav.role_mapping_screen import RoleMappingScreen
from tests.conftest import make_entry
from tests.integration.test_detail_view_on_open import _make_app


class TestFieldRolesShortcut:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("focused", [LogListView, DetailTree])
    async def test_v_shift_r_opens_field_roles(
        self, focused: type[LogListView | DetailTree]
    ) -> None:
        app, store = await _make_app(detail_visible=True)
        await store.append_entries([make_entry({"level": "INFO", "message": "hi"})])

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.query_one(focused).focus()
            await pilot.pause()

            await pilot.press("v", "R")
            await pilot.pause()

            assert isinstance(app.screen, RoleMappingScreen)
