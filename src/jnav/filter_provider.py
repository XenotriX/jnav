from typing import Literal

from aioreactive import AsyncSubject
from jnav.filtering import Filter

class FilterProvider:
    _filters: list[Filter]
    on_change: AsyncSubject[None]

    def __init__(self):
        self._filters = []
        self.on_change = AsyncSubject[None]()

    async def add_filter(
        self,
        expr: str,
        label: str | None = None,
        combine: Literal["and", "or"] = "and",
    ) -> None:
        """Add a new filter."""
        existing = {f["expr"] for f in self._filters}
        if expr not in existing:
            entry: Filter = {
                "expr": expr,
                "enabled": True,
                "combine": combine,
            }
            if label:
                entry["label"] = label
            self._filters.append(entry)
            await self.on_change.asend(None)

    def clear_filters(self) -> None:
        self._filters.clear()

    def get_filters(self) -> list[Filter]:
        return self._filters

    def set_filters(self, filters: list[Filter]) -> None:
        self._filters = filters
