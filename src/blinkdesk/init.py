"""Database initialization and seeding from TOML config."""

import sqlite3
from pathlib import Path
from typing import Any

import tomllib

from blinkdesk._db import init_db as _init_db


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
    """Seed the database from a TOML config file.

    Args:
        db_path: Path to the SQLite database file.
        config_path: Path to the TOML configuration file.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        ValueError: If the configuration is invalid.
    """
    config_path_obj = Path(config_path)
    if not config_path_obj.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        _seed_entities(conn, config.get("entities", {}))
        _seed_states(conn, config.get("states", {}))
        _seed_transitions(conn, config.get("transitions", {}))
        _seed_options(conn, config.get("options", {}))
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
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        entities = data.get("entities", [])
        if entities:
            entities_dict = {}
            for ent in entities:
                slug = ent.get("slug", ent.get("name", "").lower().replace(" ", "-"))
                entities_dict[slug] = {"name": ent.get("name", slug)}
            _seed_entities(conn, entities_dict)

        states = data.get("states", [])
        if states:
            states_dict = {}
            for state in states:
                name = state.get("name", "")
                slug = state.get("slug", name.lower().replace(" ", "-"))
                states_dict[slug] = {"name": name}
            _seed_states(conn, states_dict)

        transitions = data.get("transitions", [])
        if transitions:
            transitions_dict: dict[str, list[str]] = {}
            for trans in transitions:
                from_slug = trans.get("from_state", "").lower().replace(" ", "-")
                to_slug = trans.get("to_state", "").lower().replace(" ", "-")
                if from_slug not in transitions_dict:
                    transitions_dict[from_slug] = []
                transitions_dict[from_slug].append(to_slug)
            _seed_transitions(conn, transitions_dict)

        options = data.get("options", {})
        if options:
            _seed_options(conn, options)
    finally:
        conn.close()


def _seed_entities(conn: sqlite3.Connection, entities: dict[str, Any]) -> None:
    """Seed entities from config.

    Args:
        conn: Database connection.
        entities: Dict of entity slug -> {name}.
    """
    for slug, data in entities.items():
        name = data.get("name", slug)
        conn.execute(
            "INSERT INTO entities (slug, name) VALUES (?, ?)",
            (slug, name),
        )
    conn.commit()


def _seed_states(conn: sqlite3.Connection, states: dict[str, Any]) -> None:
    """Seed states from config.

    Args:
        conn: Database connection.
        states: Dict of state slug -> {name}.
    """
    for slug, data in states.items():
        name = data.get("name", slug)
        conn.execute(
            "INSERT INTO ticket_states (slug, name) VALUES (?, ?)",
            (slug, name),
        )
    conn.commit()


def _seed_transitions(conn: sqlite3.Connection, transitions: dict[str, Any]) -> None:
    """Seed transitions from config.

    Args:
        conn: Database connection.
        transitions: Dict of from_slug -> [to_slug, ...].
    """
    for from_slug, to_slugs in transitions.items():
        from_cursor = conn.execute(
            "SELECT state_id FROM ticket_states WHERE slug = ?",
            (from_slug,),
        )
        from_row = from_cursor.fetchone()
        if from_row is None:
            raise ValueError(f"Transition references unknown state: {from_slug}")
        from_id = from_row["state_id"]

        for to_slug in to_slugs:
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
