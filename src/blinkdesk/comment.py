"""Comment value object."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from blinkdesk.entity import Entity
from blinkdesk.state import TicketState


@dataclass(frozen=True, slots=True)
class Comment:
    """Represents a comment on a ticket."""

    comment_id: int
    ticket_id: int
    entity: Entity | None
    comment: str
    new_state: TicketState | None
    created_at: datetime

    def __post_init__(self) -> None:
        """Validate comment after initialization."""
        if not self.comment:
            raise ValueError("comment must be non-empty")

    @classmethod
    def from_row(
        cls,
        row: sqlite3.Row,
        entity: Entity | None,
        new_state: TicketState | None,
    ) -> "Comment":
        """Create a Comment from a database row.

        Args:
            row: Database row.
            entity: Entity that created the comment, if any.
            new_state: New state after the comment, if any.

        Returns:
            A Comment instance.
        """
        return cls(
            comment_id=row["comment_id"],
            ticket_id=row["ticket_id"],
            entity=entity,
            comment=row["comment"],
            new_state=new_state,
            created_at=datetime.fromisoformat(row["created_at"]),
        )
