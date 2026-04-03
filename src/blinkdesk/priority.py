"""Ticket priority value object and manager."""

import logging
import sqlite3
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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

    def create_priority(self, slug: str, position: int) -> TicketPriority:
        """Create a new ticket priority.

        Args:
            slug: URL-friendly slug for the priority.
            position: Position/order (higher number = higher priority/more urgent).

        Returns:
            The created TicketPriority.

        Raises:
            ValueError: If a priority with the same slug or position already exists.
        """
        existing = self.get_priority_by_slug(slug)
        if existing is not None:
            raise ValueError(f"Priority already exists: {slug}")

        existing_pos = self.get_priority_by_id(position)
        if existing_pos is not None:
            raise ValueError(
                f"Position {position} already in use by priority '{existing_pos.slug}'"
            )

        with self._conn:
            self._conn.execute(
                "INSERT INTO ticket_priorities (priority_id, slug) VALUES (?, ?)",
                (position, slug),
            )
        logger.info("Created priority: %s (position=%d)", slug, position)
        return TicketPriority(priority_id=position, slug=slug)

    def rename_priority(
        self, old_slug: str, new_slug: str, new_position: int | None = None
    ) -> TicketPriority:
        """Rename a priority's slug and optionally change its position.

        Args:
            old_slug: Current slug of the priority.
            new_slug: New slug for the priority.
            new_position: New position/order (optional).

        Returns:
            The updated TicketPriority.

        Raises:
            ValueError: If priority not found, new slug already exists, or new position
                is already in use.
        """
        priority = self.get_priority_by_slug(old_slug)
        if priority is None:
            raise ValueError(f"Priority not found: {old_slug}")

        if new_slug != old_slug:
            existing = self.get_priority_by_slug(new_slug)
            if existing is not None:
                raise ValueError(f"Priority already exists: {new_slug}")

        if new_position is not None and new_position != priority.priority_id:
            existing_pos = self.get_priority_by_id(new_position)
            if existing_pos is not None:
                raise ValueError(
                    f"Position {new_position} already in use by "
                    f"priority '{existing_pos.slug}'"
                )

        with self._conn:
            self._conn.execute(
                "UPDATE ticket_priorities SET slug = ?, priority_id = ? "
                "WHERE priority_id = ?",
                (
                    new_slug,
                    new_position if new_position is not None else priority.priority_id,
                    priority.priority_id,
                ),
            )
        logger.info(
            "Renamed priority: %s -> %s (position=%d)",
            old_slug,
            new_slug,
            new_position if new_position is not None else priority.priority_id,
        )
        return TicketPriority(
            priority_id=new_position
            if new_position is not None
            else priority.priority_id,
            slug=new_slug,
        )

    def delete_priority(self, priority: TicketPriority) -> bool:
        """Delete a priority if no tickets have this priority.

        Args:
            priority: Priority to delete.

        Returns:
            True if deleted, False if tickets exist with this priority.
        """
        with self._conn:
            cursor = self._conn.execute(
                "SELECT COUNT(*) FROM tickets WHERE priority_id = ?",
                (priority.priority_id,),
            )
            count = cursor.fetchone()[0]
            if count > 0:
                logger.info(
                    "Skipped deleting priority %s: priority is used by tickets",
                    priority.slug,
                )
                return False
            self._conn.execute(
                "DELETE FROM ticket_priorities WHERE priority_id = ?",
                (priority.priority_id,),
            )
        logger.info("Deleted priority: %s", priority.slug)
        return True
