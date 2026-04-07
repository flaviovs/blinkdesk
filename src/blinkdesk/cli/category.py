"""Category command handlers."""

import argparse
import sys

from blinkdesk import TicketingSystem
from ._helpers import _get_database_path


def cmd_category_add(args: argparse.Namespace) -> None:
    """Add a new category."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        category = system.create_category(args.slug)
        print(f"Category added: {category.slug} (id={category.category_id})")
    finally:
        system.close()


def cmd_category_list(args: argparse.Namespace) -> None:
    """List all categories."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        categories = system.list_categories()
        if not categories:
            print("No categories found.")
            return
        for category in categories:
            print(category.slug)
    finally:
        system.close()


def cmd_category_rename(args: argparse.Namespace) -> None:
    """Rename a category."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        category = system.rename_category(args.old_slug, args.new_slug)
        print(f"Category renamed: {args.old_slug} -> {category.slug}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    finally:
        system.close()


def cmd_category_delete(args: argparse.Namespace) -> None:
    """Delete a category."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        category = system.get_category_by_slug(args.slug)
        if category is None:
            print(f"Category not found: {args.slug}", file=sys.stderr)
            sys.exit(1)

        deleted = system.delete_category(category, force=args.force)
        if not deleted:
            print(
                f"Cannot delete category '{args.slug}': "
                f"tickets exist with this category (use --force)",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"Category deleted: {args.slug}")
    finally:
        system.close()
