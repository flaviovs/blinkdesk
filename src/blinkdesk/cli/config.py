"""Config command handlers."""

import argparse
import sys

from blinkdesk import TicketingSystem
from ._helpers import _get_database_path


def cmd_config_get(args: argparse.Namespace) -> None:
    """Get a config value."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        value = system.get_config(args.key)
        if value is None:
            print(f"Config key not found: {args.key}", file=sys.stderr)
            raise SystemExit(1)
        print(value)
    finally:
        system.close()


def cmd_config_set(args: argparse.Namespace) -> None:
    """Set a config value."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        if args.key == "default_priority":
            priority = system.get_priority_machine().get_priority_by_slug(args.value)
            if priority is None:
                print(f"Invalid priority: {args.value}", file=sys.stderr)
                raise SystemExit(1)
        if args.key in {"lock_entities", "require_operator"}:
            if args.value not in {"true", "false"}:
                print(
                    f"Invalid boolean value for {args.key}: {args.value}",
                    file=sys.stderr,
                )
                raise SystemExit(1)
        system.set_config(args.key, args.value)
        print(f"Config set: {args.key} = {args.value}")
    finally:
        system.close()


def cmd_config_list(args: argparse.Namespace) -> None:
    """List all config values."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        cursor = system._conn.execute("SELECT key, value FROM config ORDER BY key")
        rows = cursor.fetchall()
        if not rows:
            print("No config values set.")
            return
        for row in rows:
            print(f"{row['key']} = {row['value']}")
    finally:
        system.close()
