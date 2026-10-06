import json
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from jnav.field_mapping import RoleMapping
from jnav.filtering import FilterGroup
from jnav.selector_provider import Selector
from jnav.state_migrations import STATE_VERSION, migrate


class AppState(BaseModel):
    version: int = STATE_VERSION
    filter_root: FilterGroup = Field(default_factory=FilterGroup)
    selectors: list[Selector] = Field(default_factory=list)
    role_overrides: RoleMapping | None = None
    search_term: str = ""
    filtering_enabled: bool = True
    expanded_mode: bool = True
    detail_visible: bool = False
    show_selected_only: bool = False
    entry_index: int = 0
    collapsed_paths: set[str] = Field(default_factory=set)


def load(path: Path) -> AppState:
    if not path.exists():
        return AppState()
    try:
        data = migrate(json.loads(path.read_text()))
        return AppState.model_validate(data)
    except ValidationError, OSError, ValueError, KeyError, AttributeError, TypeError:
        return AppState()


def save(path: Path, state: AppState) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(state.model_dump_json())
    except OSError:
        pass
