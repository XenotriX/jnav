from typing import TYPE_CHECKING, ClassVar, Self, override

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Static

from jnav.filter_provider import FilterProvider
from jnav.log_list_view import LogListView
from jnav.log_model import LogModel
from jnav.role_mapper import RoleMapper
from jnav.search_engine import SearchEngine
from jnav.selector_provider import SelectorProvider
from jnav.store import IndexedEntry
from jnav.text_input_screen import TextInputScreen
from jnav.virtual_list_view import VirtualListView

if TYPE_CHECKING:
    from textual import getters


class StatusBar(Static):
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        padding: 0 1;
        color: $text-muted;
        background: $background;
    }
    """


class LogListPanel(Vertical):
    class Selected(Message):
        pass

    class Highlighted(Message):
        def __init__(self, entry: IndexedEntry) -> None:
            super().__init__()
            self.entry = entry

    DEFAULT_CSS = """
    LogListPanel {
        opacity: 0.75;
        &.focused {
            opacity: 1.0;
            & > #status-bar { color: $primary; }
        }
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("slash", "start_search", "Search", key_display="/", show=False),
        Binding("n", "search_next", show=False),
        Binding("N", "search_prev", show=False),
        Binding("escape", "clear_search", show=False),
    ]

    if TYPE_CHECKING:
        app = getters.app(App[None])

    def __init__(
        self,
        *,
        model: LogModel,
        selectors: SelectorProvider,
        filter_provider: FilterProvider,
        search: SearchEngine,
        role_mapper: RoleMapper,
        start_following: bool = True,
        expanded_mode: bool = True,
    ) -> None:
        super().__init__()
        self._model = model
        self._selectors = selectors
        self._filter_provider = filter_provider
        self._search = search
        self._role_mapper = role_mapper
        self._start_following = start_following
        self._expanded_mode = expanded_mode
        self._search_pos: int = -1

    @override
    def compose(self) -> ComposeResult:
        yield LogListView(
            model=self._model,
            role_mapper=self._role_mapper,
            selectors=self._selectors,
            search=self._search,
            filter_provider=self._filter_provider,
            id="log-list",
            follow=self._start_following,
            expanded_mode=self._expanded_mode,
        )
        yield StatusBar(id="status-bar")

    async def on_mount(self) -> None:
        await self._model.on_append.subscribe_async(self._on_entries_changed)
        await self._model.on_rebuild.subscribe_async(self._on_entries_changed)
        await self._search.on_change.subscribe_async(self._on_search_changed)
        self._update_status_bar()
        self.query_one("#log-list", LogListView).focus()

    @override
    def focus(self, scroll_visible: bool = True) -> Self:
        self.query_one("#log-list", LogListView).focus(scroll_visible)
        return self

    @property
    def expanded_mode(self) -> bool:
        return self.query_one("#log-list", LogListView).expanded_mode

    def current_index(self) -> int:
        return self.query_one("#log-list", LogListView).current_index()

    def action_start_search(self) -> None:
        async def on_dismiss(term: str | None) -> None:
            if not term:
                return
            await self._search.set_term(term)
            if self._search.matches:
                self._search_pos = 0
                self.query_one("#log-list", LogListView).jump_to_index(
                    self._search.matches[0]
                )
            else:
                self.notify("No matches found", timeout=2)

        self.app.push_screen(TextInputScreen(), on_dismiss)

    def action_search_next(self) -> None:
        if not self._search.matches:
            return
        lv = self.query_one("#log-list", LogListView)
        current = lv.current_index()
        for i, store_idx in enumerate(self._search.matches):
            if store_idx > current:
                self._search_pos = i
                lv.jump_to_index(store_idx)
                self._update_status_bar()
                return
        self.notify("No more matches", timeout=1)

    def action_search_prev(self) -> None:
        if not self._search.matches:
            return
        lv = self.query_one("#log-list", LogListView)
        current = lv.current_index()
        for i in range(len(self._search.matches) - 1, -1, -1):
            if self._search.matches[i] < current:
                self._search_pos = i
                lv.jump_to_index(self._search.matches[i])
                self._update_status_bar()
                return
        self.notify("No more matches", timeout=1)

    async def action_clear_search(self) -> None:
        if self._search.active:
            await self._search.clear()

    @on(VirtualListView.Selected, "#log-list")
    def _relay_selected(self, event: VirtualListView.Selected) -> None:
        event.stop()
        self.post_message(self.Selected())

    @on(VirtualListView.Highlighted, "#log-list")
    def _relay_highlighted(self, event: VirtualListView.Highlighted) -> None:
        ie = event.item
        if isinstance(ie, IndexedEntry):
            event.stop()
            self.post_message(self.Highlighted(ie))

    async def _on_entries_changed(self, _: object) -> None:
        self._update_status_bar()

    async def _on_search_changed(self, _: None) -> None:
        self._search_pos = -1
        self._update_status_bar()

    def _update_status_bar(self) -> None:
        bar = self.query_one("#status-bar", StatusBar)
        total = self._model.total_count()
        shown = len(self._model.visible_indices)
        n_cols = sum(1 for s in self._selectors.selectors if s.enabled)

        parts: list[str] = [f"Showing {shown}/{total}"]
        if n_cols:
            parts.append(f"{n_cols} field{'s' if n_cols != 1 else ''}")
        if self._search.term:
            total = len(self._search.matches)
            pos = self._search_pos + 1 if total else 0
            parts.append(f"/{self._search.term} ({pos}/{total})")

        bar.update("  \u2502  ".join(parts))
