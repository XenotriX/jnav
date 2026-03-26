from aioreactive import AsyncSubject

from jnav.parsing import ParsedEntry

LogEntry = ParsedEntry


class Store:
    entries: list[LogEntry]
    on_append: AsyncSubject[list[LogEntry]]

    def __init__(self) -> None:
        self.entries = []
        self.on_append = AsyncSubject[list[LogEntry]]()

    async def append_entries(self, new_entries: list[LogEntry]) -> None:
        self.entries.extend(new_entries)
        await self.on_append.asend(new_entries)

    def get(self, index: int) -> LogEntry:
        return self.entries[index]

    def all(self) -> list[LogEntry]:
        return self.entries

    def __len__(self) -> int:
        return len(self.entries)
