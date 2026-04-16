from typing import ClassVar, override

from rich.text import Text
from textual.widgets import Static


class Header(Static):
    COMPONENT_CLASSES: ClassVar[set[str]] = {
        "header--bracket",
        "header--text",
        "header--file",
    }

    DEFAULT_CSS = """
    Header {
        height: 1;
        background: $surface;
    }
    Header > .header--bracket {
        color: $accent;
        text-style: bold;
    }
    Header > .header--text {
        color: $foreground;
        text-style: bold;
    }
    Header > .header--file {
        color: $text-muted;
        text-style: italic;
    }
    """

    def __init__(self, file_name: str) -> None:
        super().__init__()
        self._file_name = file_name

    @override
    def render(self) -> Text:
        bracket = self.get_component_rich_style("header--bracket")
        text = self.get_component_rich_style("header--text")
        file_name = self.get_component_rich_style("header--file")
        return Text.assemble(
            ("[", bracket),
            ("J", text),
            ("]", bracket),
            ("NAV", text),
            (f" {self._file_name}", file_name),
        )
