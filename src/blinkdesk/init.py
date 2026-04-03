"""Database initialization and seeding from a TOML schema file."""

import sqlite3
from pathlib import Path
from typing import Any

import tomllib

from blinkdesk._db import (
    CURRENT_SCHEMA_VERSION,
    init_db as _init_db,
    set_schema_version,
)


def _validate_no_name_field(config: dict[str, Any], section: str) -> None:
    """Validate that config section doesn't use deprecated 'name' field.

    Args:
        config: Parsed TOML config.
        section: Section name to validate.

    Raises:
        ValueError: If deprecated 'name' field is used.
    """
    items = config.get(section, [])
    for item in items:
        if isinstance(item, dict) and "name" in item:
            raise ValueError(
                f"Invalid schema: '{section}' uses deprecated 'name' field. "
                f"Use slug-only format: {section} = ['slug1', 'slug2']"
            )


def _validate_config(config: dict[str, Any]) -> None:
    """Validate TOML config doesn't use deprecated format.

    Args:
        config: Parsed TOML config.

    Raises:
        ValueError: If deprecated format is detected.
    """
    for section in ["entities", "states"]:
        _validate_no_name_field(config, section)


def init_db(db_path: str) -> sqlite3.Connection:
    """Initialize a new database.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        A connection to the database.

    Raises:
        FileExistsError: If the database file already exists.
    """
    return _init_db(db_path)


def seed_db(db_path: str, config_path: str) -> None:
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

    _validate_config(config)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        entities = config.get("entities", [])
        states = config.get("states", [])
        _seed_entities(conn, entities)
        _seed_states(conn, states)
        _seed_priorities(
            conn,
            config.get("priorities", []),
            config.get("default_priority", "normal"),
        )
        _seed_transitions(conn, config.get("transitions", []))
        _seed_options(conn, config.get("options", {}))
        set_schema_version(conn, CURRENT_SCHEMA_VERSION)
    finally:
        conn.close()


def seed_db_from_dict(db_path: str, data: dict[str, Any]) -> None:
    """Seed the database from a dictionary (useful for tests).

    Args:
        db_path: Path to the SQLite database file.
        data: Configuration dictionary with entities, states, transitions, options.

    Raises:
        ValueError: If the configuration is invalid.
    """
    _validate_config(data)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        _seed_entities(conn, data.get("entities", []))
        _seed_states(conn, data.get("states", []))
        _seed_priorities(
            conn,
            data.get("priorities", []),
            data.get("default_priority", "normal"),
        )
        _seed_transitions(conn, data.get("transitions", []))
        _seed_options(conn, data.get("options", {}))
        set_schema_version(conn, CURRENT_SCHEMA_VERSION)
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
    conn.commit()


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
    conn.commit()


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

    for slug in priorities:
        conn.execute(
            "INSERT OR IGNORE INTO ticket_priorities (slug) VALUES (?)",
            (slug,),
        )

    cursor = conn.execute(
        "SELECT priority_id FROM ticket_priorities WHERE slug = ?",
        (default_priority,),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Default priority '{default_priority}' not found")

    conn.commit()


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
    conn.commit()


def _seed_options(conn: sqlite3.Connection, options: dict[str, Any]) -> None:
    """Seed options from config.

    Args:
        conn: Database connection.
        options: Dict of option key -> value.
    """
    for key, value in options.items():
        if isinstance(value, bool):
            value = str(value).lower()
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

    conn.commit()


def get_config(db_path: str, key: str) -> str | None:
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


def set_config(db_path: str, key: str, value: str) -> None:
    """Set a config value in the database.

    Args:
        db_path: Path to the SQLite database file.
        key: Config key.
        value: Config value.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()
