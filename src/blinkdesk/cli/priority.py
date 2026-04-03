"""Priority command handlers."""

import argparse
import sys

from blinkdesk import TicketingSystem
from ._helpers import _get_database_path


def cmd_priority_list(args: argparse.Namespace) -> None:
    """List all priorities."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        priorities = system.get_priority_machine().get_all_priorities()
        if not priorities:
            print("No priorities defined.")
            return
        for priority in priorities:
            print(f"{priority.priority_id}: {priority.slug}")
    finally:
        system.close()


def cmd_priority_add(args: argparse.Namespace) -> None:
    """Create a new priority."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        priority = system.get_priority_machine().create_priority(
            args.slug, args.position
        )
        print(f"Priority created: {priority.slug}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    finally:
        system.close()


def cmd_priority_delete(args: argparse.Namespace) -> None:
    """Delete a priority."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        priority = system.get_priority_machine().get_priority_by_slug(args.slug)
        if priority is None:
            print(f"Priority not found: {args.slug}", file=sys.stderr)
            sys.exit(1)

        deleted = system.get_priority_machine().delete_priority(priority)
        if not deleted:
            print(
                f"Cannot delete priority '{args.slug}': "
                f"tickets exist with this priority",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"Priority deleted: {args.slug}")
    finally:
        system.close()


def cmd_priority_rename(args: argparse.Namespace) -> None:
    """Rename a priority."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        priority = system.get_priority_machine().rename_priority(
            args.old_slug, args.new_slug, args.position
        )
        print(f"Priority renamed: {args.old_slug} -> {priority.slug}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    finally:
        system.close()
