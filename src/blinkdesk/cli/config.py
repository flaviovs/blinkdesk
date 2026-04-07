"""Config command handlers."""

import argparse
import sys

from blinkdesk import TicketingSystem
from ._helpers import _get_database_path

_BOOLEAN_CONFIG_KEYS = {"lock_entities", "require_operator", "audit_log"}


def _format_config_value(key: str, value: str | int) -> str:
    if key in _BOOLEAN_CONFIG_KEYS:
        if isinstance(value, int):
            return "true" if value else "false"
        return "true" if value == "1" else "false"
    return str(value)


def cmd_config_get(args: argparse.Namespace) -> None:
    """Get a config value."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        value = system.get_config(args.key)
        if value is None:
            print(f"Config key not found: {args.key}", file=sys.stderr)
            raise SystemExit(1)
        print(_format_config_value(args.key, value))
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
        if args.key in _BOOLEAN_CONFIG_KEYS:
            if args.value not in {"true", "false"}:
                print(
                    f"Invalid boolean value for {args.key}: {args.value}",
                    file=sys.stderr,
                )
                raise SystemExit(1)
        value: str | int = args.value
        if args.key in _BOOLEAN_CONFIG_KEYS:
            value = 1 if args.value == "true" else 0
        system.set_config(args.key, value)
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
            print(f"{row['key']} = {_format_config_value(row['key'], row['value'])}")
    finally:
        system.close()
