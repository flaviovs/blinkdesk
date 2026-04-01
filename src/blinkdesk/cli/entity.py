"""Entity command handlers."""

import argparse

from blinkdesk import TicketingSystem
from ._helpers import _get_database_path


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
            print(f"{entity.slug} ({entity.name})")
    finally:
        system.close()
