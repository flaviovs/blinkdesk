"""Ticket value object."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from blinkdesk.entity import Entity
from blinkdesk.priority import TicketPriority
from blinkdesk.state import TicketState


@dataclass(frozen=True, slots=True)
class Ticket:
    """Represents a ticket in the system."""

    id: int
    title: str
    description: str | None
    state: TicketState
    priority: TicketPriority
    assignee: Entity | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        """Validate ticket after initialization."""
        if not self.title:
            raise ValueError("title must be non-empty")
        if self.created_at > self.updated_at:
            raise ValueError("created_at must be <= updated_at")

    @classmethod
    def from_row(
        cls,
        row: sqlite3.Row,
        state: TicketState,
        priority: TicketPriority,
        assignee: Entity | None,
    ) -> "Ticket":
        """Create a Ticket from a database row.

        Args:
            row: Database row.
            state: Current state of the ticket.
            priority: Priority of the ticket.
            assignee: Entity assigned to the ticket, if any.

        Returns:
            A Ticket instance.
        """
        return cls(
            id=row["ticket_id"],
            title=row["title"],
            description=row["description"] if row["description"] else None,
            state=state,
            priority=priority,
            assignee=assignee,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
