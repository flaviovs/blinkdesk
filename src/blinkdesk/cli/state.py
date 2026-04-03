"""State command handlers."""

import argparse
import sys

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


def cmd_state_add(args: argparse.Namespace) -> None:
    """Add a new state."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        state = system.get_state_machine().create_state(args.slug)
        print(f"State created: {state.slug}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    finally:
        system.close()


def cmd_state_delete(args: argparse.Namespace) -> None:
    """Delete a state."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        state = system.get_state_machine().get_state_by_slug(args.slug)
        if state is None:
            print(f"State not found: {args.slug}", file=sys.stderr)
            sys.exit(1)

        deleted = system.get_state_machine().delete_state(state)
        if not deleted:
            print(
                f"Cannot delete state '{args.slug}': tickets exist with this state",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"State deleted: {args.slug}")
    finally:
        system.close()


def cmd_state_transition_list(args: argparse.Namespace) -> None:
    """List all state transitions."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        transitions = system.get_state_machine().get_all_transitions()
        if not transitions:
            print("No transitions defined.")
            return
        for from_state, to_state in transitions:
            print(f"{from_state.slug} -> {to_state.slug}")
    finally:
        system.close()


def cmd_state_transition_add(args: argparse.Namespace) -> None:
    """Add a state transition."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        from_state = system.get_state_machine().get_state_by_slug(args.from_slug)
        if from_state is None:
            print(f"State not found: {args.from_slug}", file=sys.stderr)
            sys.exit(1)

        to_state = system.get_state_machine().get_state_by_slug(args.to_slug)
        if to_state is None:
            print(f"State not found: {args.to_slug}", file=sys.stderr)
            sys.exit(1)

        system.get_state_machine().add_transition(from_state, to_state)
        print(f"Transition added: {args.from_slug} -> {args.to_slug}")
    finally:
        system.close()


def cmd_state_transition_delete(args: argparse.Namespace) -> None:
    """Delete a state transition."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        from_state = system.get_state_machine().get_state_by_slug(args.from_slug)
        if from_state is None:
            print(f"State not found: {args.from_slug}", file=sys.stderr)
            sys.exit(1)

        to_state = system.get_state_machine().get_state_by_slug(args.to_slug)
        if to_state is None:
            print(f"State not found: {args.to_slug}", file=sys.stderr)
            sys.exit(1)

        deleted = system.get_state_machine().delete_transition(from_state, to_state)
        if not deleted:
            print(
                f"Transition not found: {args.from_slug} -> {args.to_slug}",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"Transition deleted: {args.from_slug} -> {args.to_slug}")
    finally:
        system.close()
