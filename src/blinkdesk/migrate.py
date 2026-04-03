"""Database migration system."""

import sqlite3
from collections.abc import Callable

from blinkdesk._db import (
    CURRENT_SCHEMA_VERSION,
    get_schema_version,
    set_schema_version,
)

MIGRATIONS: list[tuple[int, Callable[[sqlite3.Connection], None]]] = []


def run_migrations(conn: sqlite3.Connection) -> None:
    """Run migrations to bring the database schema up to date.

    Args:
        conn: Database connection.

    Raises:
        RuntimeError: If the database schema version is newer than supported.
    """
    db_version = get_schema_version(conn)
    target = CURRENT_SCHEMA_VERSION

    if db_version > target:
        raise RuntimeError(
            f"Database schema version {db_version} is newer than "
            f"supported version {target}"
        )

    for from_ver, migrate_fn in MIGRATIONS:
        if from_ver >= db_version:
            migrate_fn(conn)
            db_version = from_ver + 1
            set_schema_version(conn, db_version)
