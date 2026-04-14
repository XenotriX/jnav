from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding, BindingsMap

if TYPE_CHECKING:
    from textual.events import Key


# pyright: reportUninitializedInstanceVariable=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false


@dataclass(frozen=True)
class KeySequence:
    keys: str
    action: str
    description: str = ""
    show: bool = True
    id: str | None = None


class KeySequenceMixin:
    """Mixin that adds multi-key sequence support to a Textual widget.

    Usage::

        class MyWidget(KeySequenceMixin, Tree):
            SEQUENCES = [
                KeySequence("ff", "filter_and", "Filter AND"),
                KeySequence("fo", "filter_or", "Filter OR"),
            ]
            SEQUENCE_GROUPS = {"f": "Filter..."}

            async def on_key(self, event: Key) -> None:
                if await self._handle_sequence_key(event):
                    return

    SEQUENCES maps key strings (min 2 chars) to actions.
    SEQUENCE_GROUPS maps a prefix character to a label shown in the
    footer (e.g. ``"f"`` -> ``"Filter..."``). Prefixes without an
    entry still work but won't show a footer hint.
    """

    SEQUENCES: ClassVar[list[KeySequence]] = []
    SEQUENCE_GROUPS: ClassVar[dict[str, str]] = {}

    _seq_buffer: str = ""
    _seq_pending: bool = False
    _seq_saved_bindings: BindingsMap | None = None
    _seq_saved_ancestor_bindings: list[tuple[object, BindingsMap]] = []  # noqa: RUF012
    _seq_keymap: dict[str, str] = {}  # noqa: RUF012
    _seq_lookup: dict[str, KeySequence] = {}  # noqa: RUF012
    _seq_prefixes: dict[str, str] = {}  # noqa: RUF012
    _seq_base_bindings: BindingsMap | None = None

    async def on_mount(self) -> None:
        self._seq_buffer = ""
        self._seq_pending = False
        self._seq_saved_bindings = None
        self._seq_base_bindings = None
        self._rebuild_sequences()

    def _rebuild_sequences(self) -> None:
        if self._seq_pending:
            self._seq_pending = False
            self._seq_buffer = ""
            if self._seq_saved_bindings is not None:
                self._bindings = self._seq_saved_bindings
                self._seq_saved_bindings = None

        self._seq_lookup = self._build_seq_lookup()
        self._seq_prefixes = self._build_seq_prefixes()

        if self._seq_base_bindings is None:
            self._seq_base_bindings = self._bindings.copy()
        else:
            self._bindings = self._seq_base_bindings.copy()

        self._inject_prefix_bindings()

    def _build_seq_lookup(self) -> dict[str, KeySequence]:
        lookup: dict[str, KeySequence] = {}
        for seq in self.SEQUENCES:
            keys = seq.keys
            if seq.id and seq.id in self._seq_keymap:
                keys = self._seq_keymap[seq.id]
            if len(keys) < 2:
                msg = f"Sequence keys must be at least 2 characters, got {keys!r}"
                raise ValueError(msg)
            lookup[keys] = seq
        return lookup

    def _build_seq_prefixes(self) -> dict[str, str]:
        prefixes: dict[str, str] = {}
        for keys in self._seq_lookup:
            char = keys[0]
            if char not in prefixes:
                prefixes[char] = self.SEQUENCE_GROUPS.get(char, "")
        return prefixes

    def _inject_prefix_bindings(self) -> None:
        # Build prefix bindings first, then prepend them so they appear before
        # the widget's own bindings in the footer.
        prefix_entries: list[tuple[str, Binding]] = []
        for char, label in self._seq_prefixes.items():
            self._bindings.key_to_bindings.pop(char, None)
            if label:
                prefix_entries.append((
                    char,
                    Binding(char, f"_seq_prefix_{char}", label),
                ))
        if not prefix_entries:
            return
        existing = dict(self._bindings.key_to_bindings)
        self._bindings.key_to_bindings.clear()
        for char, binding in prefix_entries:
            self._bindings.key_to_bindings[char] = [binding]
        for key, bindings in existing.items():
            self._bindings.key_to_bindings[key] = bindings

    async def _handle_sequence_key(self, event: Key) -> bool:
        if self._seq_pending:
            event.prevent_default()
            event.stop()

            if event.key == "escape":
                self._reset_sequence()
                return True

            self._seq_buffer += event.key

            has_longer = any(
                k.startswith(self._seq_buffer) and k != self._seq_buffer
                for k in self._seq_lookup
            )
            if has_longer:
                self._show_continuations(self._seq_buffer)
                return True

            if self._seq_buffer in self._seq_lookup:
                seq = self._seq_lookup[self._seq_buffer]
                self._reset_sequence()
                await self.run_action(seq.action)
                return True

            self._reset_sequence()
            return True

        if event.key in self._seq_prefixes:
            self._seq_pending = True
            self._seq_buffer = event.key
            event.prevent_default()
            event.stop()
            self._show_continuations(event.key)
            return True

        return False

    def _show_continuations(self, prefix: str) -> None:
        if self._seq_saved_bindings is None:
            self._seq_saved_bindings = self._bindings
            self._hide_ancestor_bindings()

        continuations: list[Binding] = []
        seen: set[str] = set()
        for keys, seq in self._seq_lookup.items():
            if keys.startswith(prefix) and len(keys) > len(prefix):
                next_char = keys[len(prefix)]
                if next_char not in seen:
                    seen.add(next_char)
                    continuations.append(
                        Binding(
                            next_char,
                            f"_seq_cont_{seq.action}",
                            seq.description,
                            show=seq.show,
                        )
                    )
        continuations.append(Binding("escape", "_seq_cancel", "Cancel", show=False))
        self._bindings = BindingsMap(continuations)
        self.refresh_bindings()

    def _reset_sequence(self) -> None:
        self._seq_pending = False
        self._seq_buffer = ""
        if self._seq_saved_bindings is not None:
            self._bindings = self._seq_saved_bindings
            self._seq_saved_bindings = None
        self._restore_ancestor_bindings()
        self.refresh_bindings()

    def _hide_ancestor_bindings(self) -> None:
        self._seq_saved_ancestor_bindings = []
        for ancestor in self.ancestors_with_self[1:]:
            if hasattr(ancestor, "_bindings"):
                self._seq_saved_ancestor_bindings.append((ancestor, ancestor._bindings))
                ancestor._bindings = BindingsMap([])

    def _restore_ancestor_bindings(self) -> None:
        for ancestor, bindings in self._seq_saved_ancestor_bindings:
            ancestor._bindings = bindings
        self._seq_saved_ancestor_bindings = []

    def set_sequence_keymap(self, keymap: dict[str, str]) -> None:
        self._seq_keymap = keymap
        self._rebuild_sequences()
        self.refresh_bindings()
