"""Database command handlers."""

import argparse
import os
import sqlite3
import sys

from blinkdesk import init_db
from ._helpers import _get_database_path
from blinkdesk.init import seed_db


_AUTO_VACUUM_MODE_TO_VALUE = {
    "none": 0,
    "full": 1,
    "incremental": 2,
}

_AUTO_VACUUM_VALUE_TO_MODE = {
    value: mode for mode, value in _AUTO_VACUUM_MODE_TO_VALUE.items()
}


def cmd_db_vacuum(args: argparse.Namespace) -> None:
    """Run VACUUM on the database."""
    db_path = _get_database_path(args)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("VACUUM")
        conn.commit()
        print("Database vacuumed successfully.")
    finally:
        conn.close()


def cmd_db_get_vacuum_mode(args: argparse.Namespace) -> None:
    """Get the current auto vacuum mode."""
    db_path = _get_database_path(args)

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("PRAGMA auto_vacuum")
        mode_value = cursor.fetchone()[0]
        mode = _AUTO_VACUUM_VALUE_TO_MODE.get(mode_value, "unknown")
        print(mode)
    finally:
        conn.close()


def cmd_db_set_vacuum_mode(args: argparse.Namespace) -> None:
    """Set the auto vacuum mode."""
    db_path = _get_database_path(args)
    mode = args.mode.lower()
    mode_value = _AUTO_VACUUM_MODE_TO_VALUE[mode]

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(f"PRAGMA auto_vacuum = {mode_value}")
        conn.execute("VACUUM")
        conn.commit()
        print(f"Database auto_vacuum mode set to: {mode}")
    finally:
        conn.close()


def cmd_db_get_journal_mode(args: argparse.Namespace) -> None:
    """Get the current journal mode."""
    db_path = _get_database_path(args)

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        print(mode.lower())
    finally:
        conn.close()


def cmd_db_set_journal_mode(args: argparse.Namespace) -> None:
    """Set the journal mode."""
    db_path = _get_database_path(args)
    mode = args.mode.upper()

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(f"PRAGMA journal_mode = {mode}")
        applied_mode = cursor.fetchone()[0]
        print(f"Database journal_mode set to: {applied_mode.lower()}")
    finally:
        conn.close()


def cmd_db_backup(args: argparse.Namespace) -> None:
    """Backup the database to a file."""
    db_path = _get_database_path(args)

    src = sqlite3.connect(db_path)
    dest = sqlite3.connect(args.output_path)
    try:
        src.backup(dest)
        print(f"Database backed up to: {args.output_path}")
    finally:
        src.close()
        dest.close()


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize a new database from a TOML schema file."""
    db_path = _get_database_path(args)
    config_path = args.config_path

    try:
        init_db(db_path)
    except FileExistsError:
        print(f"Database already exists: {db_path}", file=sys.stderr)
        sys.exit(1)

    try:
        seed_db(db_path, config_path)
        print(f"Database initialized: {db_path}")
    except Exception as e:
        os.remove(db_path)
        print(f"Failed to seed database: {e}", file=sys.stderr)
        sys.exit(1)
