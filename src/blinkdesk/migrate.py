"""Database migration system."""

import sqlite3
from collections.abc import Callable

from blinkdesk._db import (
    CURRENT_SCHEMA_VERSION,
    get_schema_version,
    set_schema_version,
)

MIGRATIONS: list[tuple[int, Callable[[sqlite3.Connection], None]]] = []


def _migrate_v0_to_v1(conn: sqlite3.Connection) -> None:
    """Migrate from schema v0 to v1: add ticket_priorities table."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ticket_priorities (
            priority_id INTEGER PRIMARY KEY,
            slug TEXT COLLATE NOCASE UNIQUE NOT NULL
        );

        ALTER TABLE tickets ADD COLUMN priority_id INTEGER
            REFERENCES ticket_priorities(priority_id);

        INSERT INTO ticket_priorities (slug) VALUES ('low');
        INSERT INTO ticket_priorities (slug) VALUES ('normal');
        INSERT INTO ticket_priorities (slug) VALUES ('high');

        UPDATE tickets SET priority_id = (
            SELECT priority_id FROM ticket_priorities WHERE slug = 'normal'
        );
        """
    )
    conn.commit()


MIGRATIONS = [
    (0, _migrate_v0_to_v1),
]


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
