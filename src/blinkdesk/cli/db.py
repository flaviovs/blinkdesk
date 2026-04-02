"""Database command handlers."""

import argparse
import os
import sqlite3
import sys

from blinkdesk import init_db
from ._helpers import _get_database_path
from blinkdesk.init import seed_db


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
