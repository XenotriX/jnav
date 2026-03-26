from aioreactive import AsyncSubject

from jnav.filter_provider import FilterProvider
from jnav.store import LogEntry, Store


class LogModel:
    on_append: AsyncSubject[list[LogEntry]]
    on_rebuild: AsyncSubject[None]

    def __init__(
        self,
        store: Store,
        filter_provider: FilterProvider,
    ):
        self._store = store
        self._filter_provider = filter_provider
        self.on_append = AsyncSubject[list[LogEntry]]()
        self.on_rebuild = AsyncSubject[None]()

    async def _on_new_entries(self, new_entries: list[LogEntry]) -> None:
        await self.on_append.asend(new_entries)

    async def start(self) -> None:
        await self._store.on_append.subscribe_async(self._on_new_entries)

    def count(self) -> int:
        return len(self._store)

    def all(self) -> list[LogEntry]:
        return self._store.all()

    def is_empty(self) -> bool:
        return self.count() == 0

    def get(self, index: int) -> LogEntry:
        return self._store.get(index)

    async def refilter(self) -> None:
        await self.on_rebuild.asend(None)
