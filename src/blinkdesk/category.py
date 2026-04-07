"""Ticket category value object."""

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Category:
    """Represents a ticket category."""

    category_id: int
    slug: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Category":
        """Create a Category from a database row.

        Args:
            row: Database row.

        Returns:
            A Category instance.
        """
        return cls(
            category_id=row["category_id"],
            slug=row["slug"],
        )
