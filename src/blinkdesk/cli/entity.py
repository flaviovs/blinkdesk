"""Entity command handlers."""

import argparse
import sys

from blinkdesk import TicketingSystem
from ._helpers import _get_database_path


def cmd_entity_add(args: argparse.Namespace) -> None:
    """Add a new entity."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        entity = system.create_entity(args.slug)
        print(f"Entity added: {entity.slug} (id={entity.entity_id})")
    finally:
        system.close()


def cmd_entity_delete(args: argparse.Namespace) -> None:
    """Delete an entity."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        entity = system.get_entity(args.entity_id)
        if entity is None:
            print(f"Entity not found: {args.entity_id}", file=sys.stderr)
            sys.exit(1)
        if not system.delete_entity(entity):
            print(
                f"Cannot delete entity '{entity.slug}' - it is linked to ticket(s)",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"Entity deleted: {entity.slug} (id={entity.entity_id})")
    finally:
        system.close()


def cmd_entity_list(args: argparse.Namespace) -> None:
    """List all entities."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        entities = system.list_entities()
        if not entities:
            print("No entities found.")
            return
        for entity in entities:
            print(entity.slug)
    finally:
        system.close()
