"""Ticket command handlers."""

import argparse
import sys

from blinkdesk import TicketingSystem
from ._helpers import (
    _format_json,
    _format_table,
    _get_database_path,
)


def cmd_ticket_create(args: argparse.Namespace) -> None:
    """Create a new ticket."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        ticket = system.create_ticket(args.title, args.description)
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Ticket created: {ticket_id}")
    finally:
        system.close()


def cmd_ticket_update(args: argparse.Namespace) -> None:
    """Update a ticket's title."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        ticket = system.get_ticket(args.ticket_id)
        if ticket is None:
            ticket_id = system.format_ticket_id(args.ticket_id)
            print(f"Ticket not found: {ticket_id}", file=sys.stderr)
            sys.exit(1)
        ticket = system.update_ticket(ticket, args.title)
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Ticket updated: {ticket_id}")
    finally:
        system.close()


def cmd_ticket_list(args: argparse.Namespace) -> None:
    """List all tickets."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        state = None
        if args.state:
            state = system._state_machine.get_state_by_slug(args.state)
            if state is None:
                print(f"State not found: {args.state}", file=sys.stderr)
                sys.exit(1)

        assignee = None
        if args.assignee:
            assignee = system.get_entity_by_slug(args.assignee)
            if assignee is None:
                print(f"Assignee not found: {args.assignee}", file=sys.stderr)
                sys.exit(1)

        tickets = system.list_tickets(state=state, assignee=assignee)
        prefix = system.display_prefix
        data = [
            {
                "id": f"{prefix}{t.id}" if prefix else t.id,
                "title": t.title,
                "state": t.state.name,
                "assignee": t.assignee.name if t.assignee else None,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat(),
                "description": t.description,
            }
            for t in tickets
        ]
        if args.output_format == "json":
            _format_json(data)
        else:
            _format_table(data, prefix=prefix)
    finally:
        system.close()


def cmd_ticket_get(args: argparse.Namespace) -> None:
    """Get a ticket by ID."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        ticket = system.get_ticket(args.ticket_id)
        prefix = system.display_prefix
        if ticket is None:
            ticket_id = f"{prefix}{args.ticket_id}" if prefix else str(args.ticket_id)
            print(f"Ticket not found: {ticket_id}", file=sys.stderr)
            sys.exit(1)
        data = {
            "id": f"{prefix}{ticket.id}" if prefix else ticket.id,
            "title": ticket.title,
            "state": ticket.state.name,
            "assignee": ticket.assignee.name if ticket.assignee else None,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat(),
            "description": ticket.description,
        }
        if args.output_format == "json":
            _format_json(data)
        else:
            _format_table([], data, prefix=prefix)
    finally:
        system.close()


def cmd_ticket_comment(args: argparse.Namespace) -> None:
    """Add a comment to a ticket."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        ticket = system.get_ticket(args.ticket_id)
        if ticket is None:
            ticket_id = system.format_ticket_id(args.ticket_id)
            print(f"Ticket not found: {ticket_id}", file=sys.stderr)
            sys.exit(1)

        entity = system.get_entity_by_slug(args.entity)
        if entity is None:
            print(f"Entity not found: {args.entity}", file=sys.stderr)
            sys.exit(1)

        ticket = system.add_comment(ticket, entity, args.comment)
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Comment added to ticket {ticket_id}")
    finally:
        system.close()
