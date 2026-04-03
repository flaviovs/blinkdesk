"""State command handlers."""

import argparse

from blinkdesk import TicketingSystem
from ._helpers import _get_database_path


def cmd_state_list(args: argparse.Namespace) -> None:
    """List all states."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        states = system.get_state_machine().get_all_states()
        if not states:
            print("No states defined.")
            return
        for state in states:
            print(state.slug)
    finally:
        system.close()
