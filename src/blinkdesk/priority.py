"""Ticket priority value object and manager."""

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TicketPriority:
    """Represents a ticket priority."""

    priority_id: int
    slug: str

    def __post_init__(self) -> None:
        """Validate priority after initialization."""
        if not self.slug:
            raise ValueError("slug must be non-empty")

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "TicketPriority":
        """Create a TicketPriority from a database row.

        Args:
            row: Database row.

        Returns:
            A TicketPriority instance.
        """
        return cls(
            priority_id=row["priority_id"],
            slug=row["slug"],
        )


class TicketPriorityManager:
    """Manages ticket priorities."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Initialize the priority manager.

        Args:
            conn: Database connection.
        """
        self._conn = conn

    def get_all_priorities(self) -> list[TicketPriority]:
        """Get all ticket priorities.

        Returns:
            List of all ticket priorities ordered by priority_id.
        """
        cursor = self._conn.execute(
            "SELECT priority_id, slug FROM ticket_priorities ORDER BY priority_id"
        )
        return [TicketPriority.from_row(row) for row in cursor.fetchall()]

    def get_priority_by_slug(self, slug: str) -> TicketPriority | None:
        """Get a priority by its slug.

        Args:
            slug: Slug of the priority.

        Returns:
            The TicketPriority if found, None otherwise.
        """
        cursor = self._conn.execute(
            "SELECT priority_id, slug FROM ticket_priorities WHERE slug = ?",
            (slug,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return TicketPriority.from_row(row)

    def get_priority_by_id(self, priority_id: int) -> TicketPriority | None:
        """Get a priority by its ID.

        Args:
            priority_id: ID of the priority.

        Returns:
            The TicketPriority if found, None otherwise.
        """
        cursor = self._conn.execute(
            "SELECT priority_id, slug FROM ticket_priorities WHERE priority_id = ?",
            (priority_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return TicketPriority.from_row(row)

    def create_priority(self, slug: str) -> TicketPriority:
        """Create a new ticket priority.

        Args:
            slug: URL-friendly slug for the priority.

        Returns:
            The created TicketPriority.

        Raises:
            ValueError: If a priority with the same slug already exists.
        """
        cursor = self._conn.execute(
            "INSERT INTO ticket_priorities (slug) VALUES (?)",
            (slug,),
        )
        self._conn.commit()
        last_id = cursor.lastrowid
        if last_id is None:
            raise ValueError("Failed to create priority")
        return TicketPriority(priority_id=last_id, slug=slug)

    def rename_priority(self, old_slug: str, new_slug: str) -> TicketPriority:
        """Rename a priority's slug.

        Args:
            old_slug: Current slug of the priority.
            new_slug: New slug for the priority.

        Returns:
            The updated TicketPriority.

        Raises:
            ValueError: If priority not found or new slug already exists.
        """
        priority = self.get_priority_by_slug(old_slug)
        if priority is None:
            raise ValueError(f"Priority not found: {old_slug}")

        existing = self.get_priority_by_slug(new_slug)
        if existing is not None:
            raise ValueError(f"Priority already exists: {new_slug}")

        self._conn.execute(
            "UPDATE ticket_priorities SET slug = ? WHERE priority_id = ?",
            (new_slug, priority.priority_id),
        )
        self._conn.commit()
        return TicketPriority(priority_id=priority.priority_id, slug=new_slug)

    def delete_priority(self, priority: TicketPriority) -> bool:
        """Delete a priority if no tickets have this priority.

        Args:
            priority: Priority to delete.

        Returns:
            True if deleted, False if tickets exist with this priority.
        """
        cursor = self._conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE priority_id = ?",
            (priority.priority_id,),
        )
        count = cursor.fetchone()[0]
        if count > 0:
            return False
        self._conn.execute(
            "DELETE FROM ticket_priorities WHERE priority_id = ?",
            (priority.priority_id,),
        )
        self._conn.commit()
        return True

    def get_or_create_priority(self, slug: str) -> TicketPriority:
        """Get a priority by slug or create it if it doesn't exist.

        Args:
            slug: URL-friendly slug for the priority.

        Returns:
            The existing or newly created TicketPriority.
        """
        cursor = self._conn.execute(
            "SELECT priority_id, slug FROM ticket_priorities WHERE slug = ?",
            (slug,),
        )
        row = cursor.fetchone()
        if row is not None:
            return TicketPriority.from_row(row)
        return self.create_priority(slug)
