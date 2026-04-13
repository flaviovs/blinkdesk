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
        ticket = system.create_ticket(
            args.title,
            args.description,
            priority_slug=args.priority,
            category_slug=args.category,
            assignee_slug=args.assignee,
            operator=args.operator,
        )
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Ticket created: {ticket_id}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    finally:
        system.close()


def cmd_ticket_update(args: argparse.Namespace) -> None:
    """Update a ticket's title."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        ticket = system.update_ticket(
            args.ticket_id,
            args.title,
            operator=args.operator,
        )
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Ticket updated: {ticket_id}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    finally:
        system.close()


def cmd_ticket_list(args: argparse.Namespace) -> None:
    """List all tickets."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        tickets = system.list_tickets(
            state_slug=args.state,
            assignee_slug=args.assignee,
            priority_slug=args.priority,
            category_slug=args.category,
            after_id=args.after_id,
            limit=args.limit,
        )
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
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    finally:
        system.close()


def cmd_ticket_count_by_entity(args: argparse.Namespace) -> None:
    """List ticket counts grouped by entity."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        counts = system.list_ticket_counts_by_entity(state_slug=args.state)
        if args.output_format == "json":
            _format_json(counts)
            return

        if not counts:
            print("No tickets found.")
            return

        print(f"{'Entity':<20} {'Count'}")
        print("-" * 28)
        for row in counts:
            entity = row["entity"] if row["entity"] is not None else "-"
            print(f"{entity:<20} {row['ticket_count']}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
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

        logs = [] if args.no_logs else system.get_ticket_logs(ticket.id)
        comments = [] if args.no_comments else system.get_ticket_comments(ticket.id)

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
        ticket = system.add_comment(
            args.ticket_id,
            args.comment,
            new_state_slug=args.state,
            operator=args.operator,
        )
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Comment added to ticket {ticket_id}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    finally:
        system.close()


def cmd_ticket_assign(args: argparse.Namespace) -> None:
    """Assign a ticket to an entity."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        ticket = system.assign_ticket(
            args.ticket_id,
            args.assignee,
            operator=args.operator,
        )
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Ticket assigned: {ticket_id}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    finally:
        system.close()


def cmd_ticket_unassign(args: argparse.Namespace) -> None:
    """Unassign a ticket."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        ticket = system.unassign_ticket(args.ticket_id, operator=args.operator)
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Ticket unassigned: {ticket_id}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    finally:
        system.close()


def cmd_ticket_transition(args: argparse.Namespace) -> None:
    """Transition a ticket to a new state."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        ticket = system.transition_ticket(
            args.ticket_id,
            args.state,
            operator=args.operator,
        )
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Ticket transitioned: {ticket_id}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    finally:
        system.close()


def cmd_ticket_set_priority(args: argparse.Namespace) -> None:
    """Set a ticket's priority."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        ticket = system.set_ticket_priority(
            args.ticket_id,
            args.priority,
            operator=args.operator,
        )
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Ticket priority set: {ticket_id}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    finally:
        system.close()


def cmd_ticket_set_category(args: argparse.Namespace) -> None:
    """Set a ticket's category."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        ticket = system.set_ticket_category(
            args.ticket_id,
            args.category,
            operator=args.operator,
        )
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Ticket category set: {ticket_id}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    finally:
        system.close()


def cmd_ticket_remove_category(args: argparse.Namespace) -> None:
    """Remove a ticket's category."""
    db_path = _get_database_path(args)
    system = TicketingSystem(db_path)
    try:
        ticket = system.remove_ticket_category(
            args.ticket_id,
            operator=args.operator,
        )
        ticket_id = system.format_ticket_id(ticket.id)
        print(f"Ticket category removed: {ticket_id}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    finally:
        system.close()
