from collections.abc import Callable, Sequence
from typing import Any

from jnav.state_migrations import v0_to_v1

Migration = Callable[[dict[str, Any]], dict[str, Any]]

# MIGRATIONS[n] upgrades a state dict from version n to version n + 1. Files
# without a version are version 0. To change the schema
# incompatibly, add a module with a `migrate` function and append it here.
MIGRATIONS: list[Migration] = [v0_to_v1.migrate]

STATE_VERSION = len(MIGRATIONS)


def migrate(
    data: dict[str, Any],
    *,
    migrations: Sequence[Migration] = MIGRATIONS,
) -> dict[str, Any]:
    """Upgrade `data` to the latest version by applying each missing migration.

    Raises ValueError if `data` was written by a newer version.
    """
    version = data.get("version", 0)
    if (
        not isinstance(version, int)
        or isinstance(version, bool)
        or version < 0
        or version > len(migrations)
    ):
        raise ValueError(f"unsupported state version: {version!r}")
    for step in migrations[version:]:
        data = step(data)
    return {**data, "version": len(migrations)}
