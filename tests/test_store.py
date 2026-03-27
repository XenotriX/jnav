import pytest

from jnav.parsing import preprocess_entry
from jnav.store import IndexedEntry, Store

from .conftest import make_collector


class TestStore:
    @pytest.mark.asyncio
    async def test_append_entries_adds_to_list(self) -> None:
        store = Store()
        entries = [preprocess_entry({"a": 1}), preprocess_entry({"a": 2})]
        received, collect = make_collector()
        await store.on_append.subscribe_async(collect)
        await store.append_entries(entries)

        assert len(store) == 2
        assert [ie.entry for ie in store.all()] == entries
        assert len(received) == 1
        assert received[0] == [
            IndexedEntry(0, entries[0]),
            IndexedEntry(1, entries[1]),
        ]

    @pytest.mark.asyncio
    async def test_on_append_notifies_subscribers(self) -> None:
        store = Store()
        batches, collect = make_collector()
        await store.on_append.subscribe_async(collect)

        e1 = preprocess_entry({"x": 1})
        e2 = preprocess_entry({"x": 2})
        await store.append_entries([e1])
        await store.append_entries([e2])

        assert len(batches) == 2
        assert batches[0] == [IndexedEntry(0, e1)]
        assert batches[1] == [IndexedEntry(1, e2)]
