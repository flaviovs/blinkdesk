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
        """
    )

    has_priority_col = conn.execute("PRAGMA table_info(tickets)").fetchall()
    has_priority_data = any(col[1] == "priority" for col in has_priority_col)

    if has_priority_data:
        row = conn.execute(
            """
            SELECT priority FROM tickets
            GROUP BY priority
            ORDER BY COUNT(*) DESC
            LIMIT 1
            """
        ).fetchone()
        default_slug = row["priority"] if row else "normal"
    else:
        default_slug = "normal"

    conn.execute(
        "UPDATE tickets SET priority_id = ("
        "SELECT priority_id FROM ticket_priorities WHERE slug = ?)",
        (default_slug,),
    )


def _migrate_v1_to_v2(conn: sqlite3.Connection) -> None:
    """Migrate from schema v1 to v2: remove name columns from entities."""
    conn.execute("ALTER TABLE entities DROP COLUMN name")
    conn.execute("ALTER TABLE ticket_states DROP COLUMN name")


MIGRATIONS = [
    (0, _migrate_v0_to_v1),
    (1, _migrate_v1_to_v2),
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
            with conn:
                migrate_fn(conn)
                db_version = from_ver + 1
                set_schema_version(conn, db_version)
