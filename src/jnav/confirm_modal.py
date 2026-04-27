from typing import ClassVar, override

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import Label

from jnav.modal import Modal


class ConfirmModal(Modal):
    DEFAULT_CSS = """
    ConfirmModal .modal-box {
        border: round $warning;
        border-title-color: $warning;
    }
    ConfirmModal .modal-box FooterKey .footer-key--key {
        color: $warning;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "confirm", "Confirm"),
        Binding("escape", "cancel", "Abort"),
    ]

    modal_title = "Confirm"
    modal_width = 50
    footer_columns = 2

    def __init__(self, prompt: str, title: str = "Confirm") -> None:
        super().__init__(title=title)
        self._prompt = prompt

    @override
    def compose_body(self) -> ComposeResult:
        yield Label(self._prompt)

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)

    @override
    def action_maybe_close(self) -> None:
        self.dismiss(False)
