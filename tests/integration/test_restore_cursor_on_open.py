import pytest

from jnav.app import JnavApp
from jnav.field_detector import FieldDetector
from jnav.filter_provider import FilterProvider
from jnav.log_list_view import LogListView
from jnav.log_model import LogModel
from jnav.parsing import ParsedEntry
from jnav.role_mapper import RoleMapper
from jnav.search_engine import SearchEngine
from jnav.selector_provider import SelectorProvider
from jnav.store import Store
from tests.conftest import make_entry


async def _make_app(*, entry_index: int, follow: bool = False) -> tuple[JnavApp, Store]:
    store = Store()
    filter_provider = FilterProvider()
    model = LogModel(store=store, filter_provider=filter_provider)
    field_detector = FieldDetector()
    role_mapper = RoleMapper()
    selectors = SelectorProvider()
    search = SearchEngine(model)
    await model.start()
    await search.start()
    await field_detector.on_discovery.subscribe_async(role_mapper.detect_roles)
    await store.on_append.subscribe_async(field_detector.process_entries)
    app = JnavApp(
        model=model,
        filter_provider=filter_provider,
        role_mapper=role_mapper,
        selectors=selectors,
        search=search,
        file_name="test.log",
        entry_index=entry_index,
        follow=follow,
    )
    return app, store


def _entries(start: int, stop: int) -> list[ParsedEntry]:
    return [
        make_entry({"level": "INFO", "message": f"m{i}"}) for i in range(start, stop)
    ]


class TestRestoreCursorOnOpen:
    @pytest.mark.asyncio
    async def test_cursor_lands_on_saved_entry_loaded_before_mount(self) -> None:
        app, store = await _make_app(entry_index=7)
        await store.append_entries(_entries(0, 10))

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            lv = app.query_one("#log-list", LogListView)
            assert lv.current_index() == 7

            lv.action_cursor_down()
            assert app.to_state().entry_index == 8

    @pytest.mark.asyncio
    async def test_cursor_lands_on_saved_entry_loaded_after_mount(self) -> None:
        app, store = await _make_app(entry_index=7)

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await store.append_entries(_entries(0, 10))
            await pilot.pause()
            lv = app.query_one("#log-list", LogListView)
            assert lv.current_index() == 7

    @pytest.mark.asyncio
    async def test_follow_lands_on_last_entry_loaded_before_mount(self) -> None:
        app, store = await _make_app(entry_index=3, follow=True)
        await store.append_entries(_entries(0, 10))

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            lv = app.query_one("#log-list", LogListView)
            assert lv.current_index() == 9
