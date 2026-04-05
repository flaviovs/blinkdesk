"""Shared CLI helper functions."""

import argparse
import json
import os
from typing import Any, cast

from blinkdesk.comment import Comment
from blinkdesk.ticket_log import TicketLog


def _get_database_path(args: argparse.Namespace) -> str:
    """Get database path from args or environment."""
    db_path: str | None = cast(str | None, args.database_path)
    if db_path:
        return db_path
    env_path = os.environ.get("BLINKDESK_DATABASE")
    if env_path:
        return env_path
    raise ValueError(
        "Database path required: use -d/--database-path or BLINKDESK_DATABASE"
    )


def _format_table(
    tickets: list[dict[str, Any]],
    tickets_get: dict[str, Any] | None = None,
    prefix: str = "",
) -> None:
    """Print tickets in table format."""
    if tickets_get:
        t = tickets_get
        ticket_id = f"{prefix}{t['id']}" if prefix else str(t["id"])
        print(f"ID:       {ticket_id}")
        print(f"Title:    {t['title']}")
        print(f"State:    {t['state']}")
        print(f"Priority: {t['priority']}")
        print(f"Assignee: {t['assignee'] or '(none)'}")
        print(f"Created:  {t['created_at']}")
        print(f"Updated:  {t['updated_at']}")
        if t["description"]:
            print(f"\nDescription:\n{t['description']}")
        return

    if not tickets:
        print("No tickets found.")
        return

    print(f"{'ID':<5} {'Title':<30} {'State':<12} {'Priority':<10} {'Assignee'}")
    print("-" * 75)
    for t in tickets:
        assignee = t["assignee"] or "-"
        title = t["title"][:27] + "..." if len(t["title"]) > 30 else t["title"]
        ticket_id = f"{prefix}{t['id']}" if prefix else str(t["id"])
        print(
            f"{ticket_id:<5} {title:<30} {t['state']:<12} "
            f"{t['priority']:<10} {assignee}"
        )


def _format_json(data: list[dict[str, Any]] | dict[str, Any]) -> None:
    """Print data as JSON."""
    print(json.dumps(data, default=str, indent=2))


def _log_to_dict(log: TicketLog) -> dict[str, Any]:
    """Convert TicketLog to dict for JSON output."""
    return {
        "ticket_log_id": log.ticket_log_id,
        "ticket_id": log.ticket_id,
        "entity": log.entity.slug if log.entity else None,
        "action": log.action.value,
        "details": log.details,
        "created_at": log.created_at.isoformat(),
    }


def _comment_to_dict(comment: Comment) -> dict[str, Any]:
    """Convert Comment to dict for JSON output."""
    return {
        "comment_id": comment.comment_id,
        "ticket_id": comment.ticket_id,
        "entity": comment.entity.slug if comment.entity else None,
        "comment": comment.comment,
        "new_state": comment.new_state.slug if comment.new_state else None,
        "created_at": comment.created_at.isoformat(),
    }


def _format_logs_table(logs: list[TicketLog]) -> None:
    """Print logs in table format."""
    if not logs:
        return
    print("\nLogs:")
    for log in logs:
        entity_slug = log.entity.slug if log.entity else "system"
        created = log.created_at.isoformat()
        action = log.action.value
        details = f": {log.details}" if log.details else ""
        print(f"  {created} {action} by {entity_slug}{details}")


def _format_comments_table(comments: list[Comment]) -> None:
    """Print comments in table format."""
    if not comments:
        return
    print("\nComments:")
    for comment in comments:
        entity_slug = comment.entity.slug if comment.entity else "unknown"
        print(f"  {comment.created_at.isoformat()} {entity_slug}:")
        for line in comment.comment.splitlines():
            print(f"    {line}")
