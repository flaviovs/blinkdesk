"""Entity value object (users/teams)."""

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Entity:
    """Represents an entity (user or team) in the system."""

    entity_id: int
    slug: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Entity":
        """Create an Entity from a database row.

        Args:
            row: Database row.

        Returns:
            An Entity instance.
        """
        return cls(
            entity_id=row["entity_id"],
            slug=row["slug"],
        )
