import logging
from collections.abc import Callable
from dataclasses import dataclass

from aioreactive import AsyncSubject

from jnav.field_detector import FieldDiscovery
from jnav.field_mapping import (
    RoleBinding,
    RoleMapping,
    TimeRoleBinding,
    detect_timestamp_format,
)
from jnav.json_model import JsonValue
from jnav.node_path import NodePath

logger = logging.getLogger(__name__)


def _build_timestamp(path: NodePath, value: JsonValue) -> TimeRoleBinding | None:
    fmt = detect_timestamp_format(value)
    return (
        TimeRoleBinding(expression=str(path), format=fmt) if fmt is not None else None
    )


def _build_string_role(path: NodePath, value: JsonValue) -> RoleBinding | None:
    if value in (None, ""):
        return None
    return RoleBinding(expression=str(path))


@dataclass(frozen=True)
class RoleSpec:
    name: str
    candidates: list[NodePath]
    build: Callable[[NodePath, JsonValue], RoleBinding | None]


def _candidate_priority(role: RoleSpec, binding: RoleBinding | None) -> int:
    if binding is None:
        return len(role.candidates)
    for i, candidate in enumerate(role.candidates):
        if str(candidate) == binding.expression:
            return i
    return len(role.candidates)


def _detect_role_updates(
    mapping: RoleMapping,
    entry: JsonValue,
    new_fields: list[NodePath],
) -> dict[str, RoleBinding | None]:
    """Detect updates to the field mapping based on a new entry.

    For each role, find the highest-priority candidate present in new_fields.
    If it outranks the currently bound candidate (or the role is unbound),
    record an update.
    """
    updates: dict[str, RoleBinding | None] = {}
    current = mapping.assignments()
    for role in ROLES:
        current_priority = _candidate_priority(role, current[role.name])
        for i, candidate in enumerate(role.candidates):
            if i >= current_priority:
                break
            if candidate not in new_fields:
                continue
            built = role.build(candidate, candidate.resolve(entry))
            if built is not None:
                updates[role.name] = built
                break
    return updates


ROLES: list[RoleSpec] = [
    RoleSpec(
        name="timestamp",
        candidates=[
            NodePath("@timestamp"),
            NodePath("timestamp"),
            NodePath("ts"),
            NodePath("time"),
            NodePath("@t"),
            NodePath("asctime"),
            NodePath("eventTime"),
            NodePath("Timestamp"),
        ],
        build=_build_timestamp,
    ),
    RoleSpec(
        name="level",
        candidates=[
            NodePath("level"),
            NodePath("severity"),
            NodePath("levelname"),
            NodePath("@l"),
            NodePath("log_level"),
            NodePath("loglevel"),
            NodePath("SeverityText"),
        ],
        build=_build_string_role,
    ),
    RoleSpec(
        name="message",
        candidates=[
            NodePath("message"),
            NodePath("msg"),
            NodePath("@m"),
            NodePath("event"),
            NodePath("Body"),
            NodePath("log"),
            NodePath(),
        ],
        build=_build_string_role,
    ),
]


class RoleMapper:
    """Tracks fields discovered in the data and the timestamp/level/message role mapping."""

    _override: RoleMapping | None
    _fallback: RoleMapping
    on_change: AsyncSubject[None]

    def __init__(self) -> None:
        self._override = None
        self._fallback = RoleMapping()

        self.on_change = AsyncSubject[None]()

    @property
    def mapping(self) -> RoleMapping:
        return self._resolve_mapping()

    def _resolve_mapping(self) -> RoleMapping:
        if self._override is not None:
            return self._override

        return self._fallback

    async def detect_roles(self, discovery: FieldDiscovery) -> None:
        updates = _detect_role_updates(
            mapping=self._fallback,
            entry=discovery.entry,
            new_fields=discovery.new_fields,
        )

        if not updates:
            return

        before = self._resolve_mapping()
        self._fallback = self._fallback.model_copy(update=updates)

        logger.debug(
            "Fallback mapping updated",
            extra={
                "old_mapping": before.model_dump(),
                "new_mapping": self._fallback.model_dump(),
            },
        )
        if self._resolve_mapping() == before:
            logger.debug("Active mapping unchanged (shadowed by override)")
            return
        await self.on_change.asend(None)

    async def set_overrides(
        self,
        overrides: RoleMapping | None,
    ) -> None:
        if overrides == self._override:
            # No change
            return

        if overrides:
            logger.debug(
                "Override mapping set",
                extra={"mapping": overrides.model_dump()},
            )
            self._override = overrides
        else:
            logger.debug("Override mapping cleared")
            self._override = None

        await self.on_change.asend(None)

    @property
    def overrides(self) -> RoleMapping | None:
        return self._override
