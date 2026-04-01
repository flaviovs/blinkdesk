"""Shared CLI helper functions."""

import argparse
import json
import os
from typing import Any, cast


def _get_database_path(args: argparse.Namespace) -> str:
    """Get database path from args or environment."""
    db_path: str | None = cast(str | None, args.database_path)
    if db_path:
        return db_path
    env_path = os.environ.get("BLINKDESK_DATABASE")
    if env_path:
        return env_path
    raise ValueError(
        "Database path required: use --database-path or BLINKDESK_DATABASE"
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
        print(f"ID:      {ticket_id}")
        print(f"Title:   {t['title']}")
        print(f"State:   {t['state']}")
        print(f"Assignee: {t['assignee'] or '(none)'}")
        print(f"Created: {t['created_at']}")
        print(f"Updated: {t['updated_at']}")
        if t["description"]:
            print(f"\nDescription:\n{t['description']}")
        return

    if not tickets:
        print("No tickets found.")
        return

    print(f"{'ID':<5} {'Title':<30} {'State':<12} {'Assignee'}")
    print("-" * 60)
    for t in tickets:
        assignee = t["assignee"] or "-"
        title = t["title"][:27] + "..." if len(t["title"]) > 30 else t["title"]
        ticket_id = f"{prefix}{t['id']}" if prefix else str(t["id"])
        print(f"{ticket_id:<5} {title:<30} {t['state']:<12} {assignee}")


def _format_json(data: list[dict[str, Any]] | dict[str, Any]) -> None:
    """Print data as JSON."""
    print(json.dumps(data, default=str, indent=2))
