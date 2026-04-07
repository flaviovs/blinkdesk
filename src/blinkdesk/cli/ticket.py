"""Ticket command handlers."""

import argparse
import sys

from blinkdesk import TicketingSystem
from ._helpers import (
    _comment_to_dict,
    _format_comments_table,
    _format_json,
    _format_logs_table,
    _format_table,
    _get_database_path,
    _log_to_dict,
)


def cmd_ticket_create(args: argparse.Namespace) -> None:
    """Create a new ticket."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        priority = system.get_priority_machine().get_priority_by_slug(args.priority)
        if priority is None:
            print(f"Priority not found: {args.priority}", file=sys.stderr)
            sys.exit(1)
        ticket = system.create_ticket(args.title, args.description, priority)
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

        priority = None
        if args.priority:
            priority = system.get_priority_machine().get_priority_by_slug(args.priority)
            if priority is None:
                print(f"Priority not found: {args.priority}", file=sys.stderr)
                sys.exit(1)

        tickets = system.list_tickets(state=state, assignee=assignee)
        if priority:
            tickets = [
                t for t in tickets if t.priority.priority_id == priority.priority_id
            ]
        prefix = system.display_prefix
        data = [
            {
                "id": t.id,
                "title": t.title,
                "state": t.state.slug,
                "priority": t.priority.slug,
                "assignee": t.assignee.slug if t.assignee else None,
                "category": t.category.slug if t.category else None,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat(),
                "description": t.description,
            }
            for t in tickets
        ]
        if args.output_format == "json":
            if prefix:
                data = [{**d, "id": f"{prefix}{d['id']}"} for d in data]
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
            ticket_id = system.format_ticket_id(args.ticket_id)
            print(f"Ticket not found: {ticket_id}", file=sys.stderr)
            sys.exit(1)

        logs = [] if args.no_logs else system.get_ticket_logs(ticket)
        comments = [] if args.no_comments else system.get_ticket_comments(ticket)

        data = {
            "id": ticket.id,
            "title": ticket.title,
            "state": ticket.state.slug,
            "priority": ticket.priority.slug,
            "assignee": ticket.assignee.slug if ticket.assignee else None,
            "category": ticket.category.slug if ticket.category else None,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat(),
            "description": ticket.description,
        }
        if args.output_format == "json":
            if prefix:
                data["id"] = f"{prefix}{data['id']}"
            if not args.no_logs:
                data["logs"] = [_log_to_dict(log) for log in logs]
            if not args.no_comments:
                data["comments"] = [_comment_to_dict(comment) for comment in comments]
            _format_json(data)
        else:
            _format_table([], data, prefix=prefix)
            _format_logs_table(logs)
            _format_comments_table(comments)
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

        state_slug = getattr(args, "state", None)
        new_state = None
        if state_slug:
            new_state = system.get_state_machine().get_state_by_slug(state_slug)
            if new_state is None:
                print(f"State not found: {state_slug}", file=sys.stderr)
                sys.exit(1)

        ticket = system.add_comment(ticket, entity, args.comment, new_state=new_state)
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Comment added to ticket {ticket_id}")
    finally:
        system.close()


def cmd_ticket_assign(args: argparse.Namespace) -> None:
    """Assign a ticket to an entity."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        ticket = system.get_ticket(args.ticket_id)
        if ticket is None:
            ticket_id = system.format_ticket_id(args.ticket_id)
            print(f"Ticket not found: {ticket_id}", file=sys.stderr)
            sys.exit(1)

        assignee = system.get_entity_by_slug(args.assignee)
        if assignee is None:
            print(f"Assignee not found: {args.assignee}", file=sys.stderr)
            sys.exit(1)

        ticket = system.assign_ticket(ticket, assignee)
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Ticket assigned: {ticket_id}")
    finally:
        system.close()


def cmd_ticket_unassign(args: argparse.Namespace) -> None:
    """Unassign a ticket."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        ticket = system.get_ticket(args.ticket_id)
        if ticket is None:
            ticket_id = system.format_ticket_id(args.ticket_id)
            print(f"Ticket not found: {ticket_id}", file=sys.stderr)
            sys.exit(1)

        ticket = system.unassign_ticket(ticket)
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Ticket unassigned: {ticket_id}")
    finally:
        system.close()


def cmd_ticket_transition(args: argparse.Namespace) -> None:
    """Transition a ticket to a new state."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        ticket = system.get_ticket(args.ticket_id)
        if ticket is None:
            ticket_id = system.format_ticket_id(args.ticket_id)
            print(f"Ticket not found: {ticket_id}", file=sys.stderr)
            sys.exit(1)

        state = system.get_state_machine().get_state_by_slug(args.state)
        if state is None:
            print(f"State not found: {args.state}", file=sys.stderr)
            sys.exit(1)

        ticket = system.transition_ticket(ticket, state)
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Ticket transitioned: {ticket_id}")
    finally:
        system.close()


def cmd_ticket_set_priority(args: argparse.Namespace) -> None:
    """Set a ticket's priority."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        ticket = system.get_ticket(args.ticket_id)
        if ticket is None:
            ticket_id = system.format_ticket_id(args.ticket_id)
            print(f"Ticket not found: {ticket_id}", file=sys.stderr)
            sys.exit(1)

        priority = system.get_priority_machine().get_priority_by_slug(args.priority)
        if priority is None:
            print(f"Priority not found: {args.priority}", file=sys.stderr)
            sys.exit(1)

        ticket = system.set_ticket_priority(ticket, priority)
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Ticket priority set: {ticket_id}")
    finally:
        system.close()


def cmd_ticket_set_category(args: argparse.Namespace) -> None:
    """Set a ticket's category."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        ticket = system.get_ticket(args.ticket_id)
        if ticket is None:
            ticket_id = system.format_ticket_id(args.ticket_id)
            print(f"Ticket not found: {ticket_id}", file=sys.stderr)
            sys.exit(1)

        category = system.get_category_by_slug(args.category)
        if category is None:
            print(f"Category not found: {args.category}", file=sys.stderr)
            sys.exit(1)

        ticket = system.set_ticket_category(ticket, category)
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Ticket category set: {ticket_id}")
    finally:
        system.close()


def cmd_ticket_remove_category(args: argparse.Namespace) -> None:
    """Remove a ticket's category."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        ticket = system.get_ticket(args.ticket_id)
        if ticket is None:
            ticket_id = system.format_ticket_id(args.ticket_id)
            print(f"Ticket not found: {ticket_id}", file=sys.stderr)
            sys.exit(1)

        ticket = system.remove_ticket_category(ticket)
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Ticket category removed: {ticket_id}")
    finally:
        system.close()
