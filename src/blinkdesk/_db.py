"""Database initialization and schema management."""

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 3


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Get the schema version from the database.

    Args:
        conn: Database connection.

    Returns:
        The schema version, or 0 if not set.
    """
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    return version if version is not None else 0


def set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    """Set the schema version in the database.

    Args:
        conn: Database connection.
        version: Schema version to set.
    """
    conn.execute(f"PRAGMA user_version = {version}")
    logger.info("Set schema version to %d", version)


def init_db(db_path: str) -> sqlite3.Connection:
    """Initialize database connection and create schema.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        A connection to the database.

    Raises:
        FileExistsError: If the database file already exists.
    """
    path = Path(db_path)
    if path.exists():
        raise FileExistsError(f"Database file already exists: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA auto_vacuum = INCREMENTAL")
    _create_schema(conn)
    logger.info("Initialized new database: %s", db_path)
    return conn


def _init_db(db_path: str) -> sqlite3.Connection:
    """Initialize database connection and create schema (internal).

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        A connection to the database.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _create_schema(conn)
    logger.info("Initialized database schema: %s", db_path)
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    """Create database schema if it doesn't exist.

    Args:
        conn: Database connection.
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS entities (
            entity_id INTEGER PRIMARY KEY,
            slug TEXT COLLATE NOCASE UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ticket_states (
            state_id INTEGER PRIMARY KEY,
            slug TEXT COLLATE NOCASE UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ticket_priorities (
            priority_id INTEGER PRIMARY KEY,
            slug TEXT COLLATE NOCASE UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY,
            slug TEXT COLLATE NOCASE UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS state_transitions (
            from_state_id INTEGER REFERENCES ticket_states(state_id),
            to_state_id INTEGER REFERENCES ticket_states(state_id),
            PRIMARY KEY (from_state_id, to_state_id)
        ) WITHOUT ROWID;

        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            state_id INTEGER REFERENCES ticket_states(state_id),
            priority_id INTEGER REFERENCES ticket_priorities(priority_id),
            assignee_entity_id INTEGER REFERENCES entities(entity_id),
            category_id INTEGER REFERENCES categories(category_id),
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ticket_logs (
            ticket_id INTEGER NOT NULL REFERENCES tickets(ticket_id),
            ticket_log_id INTEGER NOT NULL,
            entity_id INTEGER REFERENCES entities(entity_id),
            action TEXT NOT NULL,
            details TEXT,
            created_at DATETIME NOT NULL,
            PRIMARY KEY (ticket_id, ticket_log_id)
        ) WITHOUT ROWID;

        CREATE TABLE IF NOT EXISTS comments (
            ticket_id INTEGER NOT NULL REFERENCES tickets(ticket_id),
            comment_id INTEGER NOT NULL,
            entity_id INTEGER REFERENCES entities(entity_id),
            comment TEXT NOT NULL,
            new_state_id INTEGER REFERENCES ticket_states(state_id),
            created_at DATETIME NOT NULL,
            PRIMARY KEY (ticket_id, comment_id)
        ) WITHOUT ROWID;

        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        ) WITHOUT ROWID;
        """
    )
    conn.commit()
    logger.info("Created or verified database schema")
