from typing import TypeVar, override

from rich.style import Style
from rich.text import Text
from textual.widgets import Tree as _Tree
from textual.widgets.tree import TreeNode

T = TypeVar("T")


class Tree(_Tree[T]):
    """Tree subclass that lets per-segment label colors survive the cursor highlight.

    Textual's Tree applies the `tree--cursor` component style with `partial=False`,
    so its `color` is forced onto every character of the cursor row, flattening any
    explicit colors set on individual label segments. This override drops `color`
    from the overlay on the cursor row while keeping `bgcolor` and text-style flags,
    so segment colors win and only the background reflects the highlight.
    """

    @override
    def render_label(
        self,
        node: TreeNode[T],
        base_style: Style,
        style: Style,
    ) -> Text:
        if node is self.cursor_node:
            style = Style(
                bgcolor=style.bgcolor,
                bold=style.bold,
                dim=style.dim,
                italic=style.italic,
                underline=style.underline,
                blink=style.blink,
                blink2=style.blink2,
                reverse=style.reverse,
                conceal=style.conceal,
                strike=style.strike,
            )
        return super().render_label(node, base_style, style)
