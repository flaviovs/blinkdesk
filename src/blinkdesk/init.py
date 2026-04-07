"""Database initialization and seeding from a TOML schema file."""

import logging
import sqlite3
from pathlib import Path
from typing import Any

import tomllib

from blinkdesk._db import (
    CURRENT_SCHEMA_VERSION,
    init_db as _init_db,
    set_schema_version,
)

logger = logging.getLogger(__name__)


def _validate_schema_section(schema: dict[str, Any]) -> None:
    """Validate required schema keys.

    Args:
        schema: Schema section data.

    Raises:
        ValueError: If a required schema key is missing or empty.
    """
    for key in ("entities", "states", "priorities", "transitions"):
        value = schema.get(key)
        if not isinstance(value, list) or not value:
            raise ValueError(f"schema.{key} must be a non-empty list")

    categories = schema.get("categories", [])
    if not isinstance(categories, list):
        raise ValueError("schema.categories must be a list")


def init_db(db_path: str) -> sqlite3.Connection:
    """Initialize a new database.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        A connection to the database.

    Raises:
        FileExistsError: If the database file already exists.
    """
    conn = _init_db(db_path)
    logger.info("Initialized database connection: %s", db_path)
    return conn


def seed_db_from_toml(db_path: str, config_path: str) -> None:
    """Seed the database from a TOML schema file.

    Args:
        db_path: Path to the SQLite database file.
        config_path: Path to the TOML schema file.

    Raises:
        FileNotFoundError: If the schema file doesn't exist.
        ValueError: If the schema definition is invalid.
    """
    config_path_obj = Path(config_path)
    if not config_path_obj.exists():
        raise FileNotFoundError(f"Schema file not found: {config_path}")

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    logger.info("Seeding database from schema file: %s", config_path)
    seed_db_from_dict(db_path, config)


def seed_db_from_dict(db_path: str, data: dict[str, Any]) -> None:
    """Seed the database from a dictionary (useful for tests).

    Args:
        db_path: Path to the SQLite database file.
        data: Configuration dictionary with "schema" and optional "options".

    Raises:
        ValueError: If the configuration is invalid.
    """
    logger.info("Seeding database from in-memory schema")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            schema = data.get("schema", {})
            options = data.get("options", {})

            if not isinstance(schema, dict):
                schema = {}
            if not isinstance(options, dict):
                options = {}

            _validate_schema_section(schema)

            _seed_entities(conn, schema.get("entities", []))
            _seed_states(conn, schema.get("states", []))
            _seed_priorities(
                conn,
                schema.get("priorities", []),
                options.get("default_priority", "normal"),
            )
            _seed_categories(conn, schema.get("categories", []))
            _seed_transitions(conn, schema.get("transitions", []))
            _seed_options(conn, options)
            set_schema_version(conn, CURRENT_SCHEMA_VERSION)
            logger.info("Seeded database from in-memory schema")
    finally:
        conn.close()


def _seed_entities(conn: sqlite3.Connection, entities: list[str]) -> None:
    """Seed entities from config.

    Args:
        conn: Database connection.
        entities: List of entity slugs.
    """
    for slug in entities:
        conn.execute(
            "INSERT INTO entities (slug) VALUES (?)",
            (slug,),
        )
    if entities:
        logger.info("Seeded entities: count=%d", len(entities))


def _seed_states(conn: sqlite3.Connection, states: list[str]) -> None:
    """Seed states from config.

    Args:
        conn: Database connection.
        states: List of state slugs.
    """
    for slug in states:
        conn.execute(
            "INSERT INTO ticket_states (slug) VALUES (?)",
            (slug,),
        )
    if states:
        logger.info("Seeded states: count=%d", len(states))


def _seed_priorities(
    conn: sqlite3.Connection, priorities: list[str], default_priority: str
) -> None:
    """Seed priorities from config.

    Args:
        conn: Database connection.
        priorities: List of priority slugs.
        default_priority: Slug of the default priority.
    """
    if not priorities:
        priorities = ["low", "normal", "high"]

    positions = (
        [10, 20, 30]
        if len(priorities) == 3
        else list(range(10, 10 + len(priorities) * 10, 10))
    )

    for slug, pos in zip(priorities, positions):
        conn.execute(
            "INSERT OR IGNORE INTO ticket_priorities (priority_id, slug) VALUES (?, ?)",
            (pos, slug),
        )
    logger.info("Seeded priorities: count=%d", len(priorities))

    cursor = conn.execute(
        "SELECT priority_id FROM ticket_priorities WHERE slug = ?",
        (default_priority,),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Default priority '{default_priority}' not found")


def _seed_transitions(
    conn: sqlite3.Connection, transitions: list[dict[str, str]]
) -> None:
    """Seed transitions from config.

    Args:
        conn: Database connection.
        transitions: List of transition dicts with 'from' and 'to' keys.
    """
    for trans in transitions:
        from_slug = trans.get("from", "").lower().replace(" ", "-")
        to_slug = trans.get("to", "").lower().replace(" ", "-")

        from_cursor = conn.execute(
            "SELECT state_id FROM ticket_states WHERE slug = ?",
            (from_slug,),
        )
        from_row = from_cursor.fetchone()
        if from_row is None:
            raise ValueError(f"Transition references unknown state: {from_slug}")
        from_id = from_row["state_id"]

        to_cursor = conn.execute(
            "SELECT state_id FROM ticket_states WHERE slug = ?",
            (to_slug,),
        )
        to_row = to_cursor.fetchone()
        if to_row is None:
            raise ValueError(f"Transition references unknown state: {to_slug}")
        to_id = to_row["state_id"]

        conn.execute(
            "INSERT OR IGNORE INTO state_transitions "
            "(from_state_id, to_state_id) VALUES (?, ?)",
            (from_id, to_id),
        )
    if transitions:
        logger.info("Seeded transitions: count=%d", len(transitions))


def _seed_categories(conn: sqlite3.Connection, categories: list[str]) -> None:
    """Seed categories from config.

    Args:
        conn: Database connection.
        categories: List of category slugs.
    """
    for slug in categories:
        conn.execute(
            "INSERT INTO categories (slug) VALUES (?)",
            (slug,),
        )
    if categories:
        logger.info("Seeded categories: count=%d", len(categories))


def _seed_options(conn: sqlite3.Connection, options: dict[str, Any]) -> None:
    """Seed options from config.

    Args:
        conn: Database connection.
        options: Dict of option key -> value.
    """
    for key, value in options.items():
        if isinstance(value, bool):
            value = int(value)
        elif not isinstance(value, str):
            value = str(value)
        conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, value),
        )

    if "display_prefix" not in options:
        conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            ("display_prefix", "#"),
        )

    if "require_operator" not in options:
        conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            ("require_operator", 0),
        )

    logger.info("Seeded config options: count=%d", len(options))


def get_config(db_path: str, key: str) -> str | int | None:
    """Get a config value from the database.

    Args:
        db_path: Path to the SQLite database file.
        key: Config key.

    Returns:
        Config value if found, None otherwise.
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def set_config(db_path: str, key: str, value: str | int | bool) -> None:
    """Set a config value in the database.

    Args:
        db_path: Path to the SQLite database file.
        key: Config key.
        value: Config value.
    """
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                (key, value),
            )
        logger.info("Set config value: %s", key)
    finally:
        conn.close()
