import logging
from dataclasses import dataclass

from aioreactive import AsyncSubject

from jnav.json_model import JsonValue
from jnav.node_path import NodePath, walk
from jnav.store import IndexedEntry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FieldDiscovery:
    entry: JsonValue
    new_fields: list[NodePath]


class FieldDetector:
    on_discovery: AsyncSubject[FieldDiscovery]

    def __init__(self) -> None:
        self._all_fields: set[NodePath] = set()
        self.on_discovery = AsyncSubject[FieldDiscovery]()

    @property
    def all_fields(self) -> set[str]:
        return {str(f) for f in self._all_fields}

    async def process_entries(self, entries: list[IndexedEntry]) -> None:
        for ie in entries:
            await self.detect_fields(ie.entry.expanded)

    async def detect_fields(self, entry: JsonValue) -> None:
        if not isinstance(entry, dict):
            return
        entry_fields = {p for _, p in walk(entry)}
        new_fields = entry_fields - self._all_fields
        self._all_fields.update(new_fields)

        for field in new_fields:
            logger.debug(
                "New field discovered",
                extra={"field": str(field)},
            )

        await self.on_discovery.asend(FieldDiscovery(entry, list(new_fields)))
