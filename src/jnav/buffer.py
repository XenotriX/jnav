import asyncio
from typing import TypeVar
from collections.abc import AsyncIterable

from aioreactive import AsyncObservable, to_async_iterable

T = TypeVar("T")


async def buffer_time_or_count(
    source: AsyncObservable[T],
    max_count: int = 500,
    timeout: float = 0.1,
) -> AsyncIterable[list[T]]:
    batch: list[T] = []
    aiter = to_async_iterable(source).__aiter__()

    while True:
        try:
            entry = await asyncio.wait_for(aiter.__anext__(), timeout=timeout)
            batch.append(entry)
            if len(batch) >= max_count:
                yield batch
                batch = []
        except TimeoutError:
            if batch:
                yield batch
                batch = []
        except StopAsyncIteration:
            if batch:
                yield batch
            return
