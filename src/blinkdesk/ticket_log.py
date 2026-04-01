"""Ticket log value object and actions."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from blinkdesk.entity import Entity


class TicketLogAction(str, Enum):
    """Actions that can be logged for a ticket."""

    CREATED = "created"
    UPDATED = "updated"
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"
    STATE_CHANGED = "state_changed"


@dataclass(frozen=True, slots=True)
class TicketLog:
    """Represents a log entry for a ticket."""

    ticket_log_id: int
    ticket_id: int
    entity: Entity | None
    action: TicketLogAction
    details: str | None
    created_at: datetime

    @classmethod
    def from_row(cls, row: sqlite3.Row, entity: Entity | None) -> "TicketLog":
        """Create a TicketLog from a database row.

        Args:
            row: Database row.
            entity: Entity associated with the log entry, if any.

        Returns:
            A TicketLog instance.
        """
        return cls(
            ticket_log_id=row["ticket_log_id"],
            ticket_id=row["ticket_id"],
            entity=entity,
            action=TicketLogAction(row["action"]),
            details=row["details"] if row["details"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
        )
