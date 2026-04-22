from dataclasses import dataclass
from typing import cast, overload, override

Segment = str | int


@dataclass(frozen=True)
class NodePath:
    segments: tuple[Segment, ...] = ()

    def __truediv__(self, segment: Segment) -> NodePath:
        return NodePath(self.segments + (segment,))

    def __len__(self) -> int:
        return len(self.segments)

    @overload
    def __getitem__(self, i: int) -> Segment: ...

    @overload
    def __getitem__(self, i: slice) -> NodePath: ...

    def __getitem__(self, i: int | slice) -> Segment | NodePath:
        if isinstance(i, slice):
            return NodePath(self.segments[i])
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
        out = ""
        for seg in self.segments:
            if isinstance(seg, int):
                out += f"[{seg}]"
            elif seg.isidentifier():
                out += f".{seg}"
            else:
                out += f'["{seg}"]'
        return out
