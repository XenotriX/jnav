from dataclasses import dataclass
from typing import cast, overload, override

Segment = str | int


@dataclass(frozen=True)
class NodePath:
    segments: tuple[Segment, ...] = ()

    def __init__(self, *segments: Segment) -> None:
        object.__setattr__(self, "segments", segments)

    def __truediv__(self, segment: Segment) -> NodePath:
        return NodePath(*self.segments + (segment,))

    def __len__(self) -> int:
        return len(self.segments)

    @overload
    def __getitem__(self, i: int) -> Segment: ...

    @overload
    def __getitem__(self, i: slice) -> NodePath: ...

    def __getitem__(self, i: int | slice) -> Segment | NodePath:
        if isinstance(i, slice):
            return NodePath(*self.segments[i])
        return self.segments[i]

    def resolve(self, document: object) -> object:
        node = document
        for seg in self.segments:
            if isinstance(seg, int):
                if not isinstance(node, list):
                    raise TypeError(
                        f"Expected list at {self}, got {type(node).__name__}"
                    )
                node = cast(list[object], node)
                node = node[seg]
            else:
                if not isinstance(node, dict):
                    raise TypeError(
                        f"Expected dict at {self}, got {type(node).__name__}"
                    )
                node = cast(dict[str, object], node)
                node = node[seg]
        return node

    @override
    def __str__(self) -> str:
        if len(self.segments) == 0:
            return "."

        parts: list[str] = []
        for seg in self.segments:
            if isinstance(seg, int):
                parts.append(f"[{seg}]")
            elif seg.isidentifier():
                parts.append(f".{seg}")
            else:
                parts.append(f'.["{seg}"]')
        if isinstance(self.segments[0], int):
            parts.insert(0, ".")
        return "".join(parts)
