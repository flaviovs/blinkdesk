"""Main entry point for the ticketing system."""

import logging
import random
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from blinkdesk.comment import Comment
from blinkdesk.entity import Entity
from blinkdesk.migrate import run_migrations
from blinkdesk.priority import TicketPriority, TicketPriorityManager
from blinkdesk.state import TicketState, TicketStateMachine
from blinkdesk.ticket import Ticket
from blinkdesk.ticket_log import TicketLog, TicketLogAction

logger = logging.getLogger(__name__)

_TICKET_SELECT_QUERY = """
SELECT
    t.ticket_id, t.title, t.description, t.state_id, t.priority_id,
    t.assignee_entity_id, t.created_at, t.updated_at,
    e.entity_id, e.slug AS entity_slug,
    ts.state_id AS state_id_new,
    ts.slug AS state_slug,
    tp.priority_id AS priority_id_new,
    tp.slug AS priority_slug
FROM tickets t
LEFT JOIN entities e ON t.assignee_entity_id = e.entity_id
JOIN ticket_states ts ON t.state_id = ts.state_id
LEFT JOIN ticket_priorities tp ON t.priority_id = tp.priority_id
"""


class TicketingSystem:
    """Main entry point for the ticketing system."""

    def __init__(self, db_path: str) -> None:
        """Initialize the ticketing system.

        Args:
            db_path: Path to the SQLite database file.

        Raises:
            FileNotFoundError: If the database file doesn't exist.
        """
        self._db_path = db_path
        if not Path(db_path).exists():
            raise FileNotFoundError(f"Database file not found: {db_path}")
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        run_migrations(self._conn)
        self._state_machine = TicketStateMachine(self._conn)
        self._priority_manager = TicketPriorityManager(self._conn)

    def close(self) -> None:
        """Close the database connection."""
        try:
            if random.random() < 0.01:
                self._conn.execute("PRAGMA main.incremental_vacuum")
        finally:
            self._conn.close()

    def create_entity(self, slug: str) -> Entity:
        """Create a new entity.

        Args:
            slug: URL-friendly slug for the entity.

        Returns:
            The created Entity.
        """
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO entities (slug) VALUES (?)",
                (slug,),
            )
        last_id = cursor.lastrowid
        if last_id is None:
            raise ValueError("Failed to create entity")
        logger.info("Created entity: %s", slug)
        return Entity(
            entity_id=last_id,
            slug=slug,
        )

    def get_entity(self, entity_id: int) -> Entity | None:
        """Get an entity by ID.

        Args:
            entity_id: ID of the entity.

        Returns:
            The Entity if found, None otherwise.
        """
        cursor = self._conn.execute(
            "SELECT entity_id, slug FROM entities WHERE entity_id = ?",
            (entity_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return Entity.from_row(row)

    def get_entity_by_slug(self, slug: str) -> Entity | None:
        """Get an entity by slug.

        Args:
            slug: Slug of the entity.

        Returns:
            The Entity if found, None otherwise.
        """
        cursor = self._conn.execute(
            "SELECT entity_id, slug FROM entities WHERE slug = ?",
            (slug,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return Entity.from_row(row)

    def list_entities(self) -> list[Entity]:
        """List all entities.

        Returns:
            List of all entities ordered by entity_id.
        """
        cursor = self._conn.execute(
            "SELECT entity_id, slug FROM entities ORDER BY entity_id"
        )
        return [Entity.from_row(row) for row in cursor.fetchall()]

    def delete_entity(self, entity: Entity) -> bool:
        """Delete an entity if it's not assigned to any tickets.

        Args:
            entity: Entity to delete.

        Returns:
            True if deleted, False if entity is assigned to tickets.
        """
        with self._conn:
            cursor = self._conn.execute(
                "SELECT COUNT(*) FROM tickets WHERE assignee_entity_id = ?",
                (entity.entity_id,),
            )
            count = cursor.fetchone()[0]
            if count > 0:
                return False
            self._conn.execute(
                "DELETE FROM entities WHERE entity_id = ?", (entity.entity_id,)
            )
        logger.info("Deleted entity: %s", entity.slug)
        return True

    def _log_ticket(
        self,
        ticket_id: int,
        action: str,
        entity: Entity | None = None,
        details: str | None = None,
    ) -> None:
        """Log an action for a ticket.

        Args:
            ticket_id: ID of the ticket.
            action: Action performed.
            entity: Entity that performed the action, if any.
            details: Additional details about the action.
        """
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            "SELECT COALESCE(MAX(ticket_log_id), 0) + 1 "
            "FROM ticket_logs WHERE ticket_id = ?",
            (ticket_id,),
        )
        log_id = cursor.fetchone()[0]
        self._conn.execute(
            """
            INSERT INTO ticket_logs (
                ticket_id, ticket_log_id, entity_id, action, details, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_id,
                log_id,
                entity.entity_id if entity else None,
                action,
                details,
                now,
            ),
        )

    def create_ticket(
        self,
        title: str,
        description: str | None = None,
        priority: TicketPriority | None = None,
    ) -> Ticket:
        """Create a new ticket.

        Args:
            title: Title of the ticket.
            description: Optional description of the ticket.
            priority: Optional priority (defaults to "normal").

        Returns:
            The created Ticket.

        Raises:
            ValueError: If no states are defined in the system.
        """
        states = self._state_machine.get_all_states()
        if not states:
            raise ValueError("No states defined in the system")

        if priority is None:
            priority = self._priority_manager.get_priority_by_slug("normal")
            if priority is None:
                raise ValueError("Default priority 'normal' not found")

        initial_state = states[0]
        now = datetime.now(timezone.utc).isoformat()
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO tickets (
                    title, description, state_id, priority_id,
                    assignee_entity_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    title,
                    description,
                    initial_state.state_id,
                    priority.priority_id,
                    now,
                    now,
                ),
            )
            last_id = cursor.lastrowid
            if last_id is None:
                raise ValueError("Failed to create ticket")
            self._log_ticket(last_id, TicketLogAction.CREATED)
        logger.info("Created ticket #%d: %s", last_id, title)
        return Ticket(
            id=last_id,
            title=title,
            description=description,
            state=initial_state,
            priority=priority,
            assignee=None,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        )

    def get_ticket(self, ticket_id: int) -> Ticket | None:
        """Get a ticket by ID.

        Args:
            ticket_id: ID of the ticket.

        Returns:
            The Ticket if found, None otherwise.
        """
        cursor = self._conn.execute(
            f"{_TICKET_SELECT_QUERY} WHERE t.ticket_id = ?",
            (ticket_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._ticket_from_row(row)

    def list_tickets(
        self,
        state: TicketState | None = None,
        assignee: Entity | None = None,
    ) -> list[Ticket]:
        """List all tickets.

        Args:
            state: Optional state to filter by.
            assignee: Optional assignee to filter by.

        Returns:
            List of all tickets ordered by ticket_id.
        """
        query = _TICKET_SELECT_QUERY
        conditions: list[str] = []
        params: list[int | str] = []

        if state:
            conditions.append("ts.state_id = ?")
            params.append(state.state_id)
        if assignee:
            conditions.append("t.assignee_entity_id = ?")
            params.append(assignee.entity_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY t.ticket_id"

        cursor = self._conn.execute(query, params)
        return [self._ticket_from_row(row) for row in cursor.fetchall()]

    def update_ticket(self, ticket: Ticket, title: str) -> Ticket:
        """Update a ticket's title.

        Args:
            ticket: Ticket to update.
            title: New title.

        Returns:
            The updated Ticket.
        """
        if title == ticket.title:
            logger.warning("Ticket #%d title unchanged (same as current)", ticket.id)
            return ticket
        now = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                """
                UPDATE tickets SET title = ?, updated_at = ?
                WHERE ticket_id = ?
                """,
                (title, now, ticket.id),
            )
            self._log_ticket(
                ticket.id,
                TicketLogAction.UPDATED,
                details=f"title changed from '{ticket.title}' to '{title}'",
            )
        logger.info("Updated ticket #%d", ticket.id)
        return self.get_ticket(ticket.id)  # type: ignore[return-value]

    def set_ticket_priority(self, ticket: Ticket, priority: TicketPriority) -> Ticket:
        """Set a ticket's priority.

        Args:
            ticket: Ticket to update.
            priority: New priority.

        Returns:
            The updated Ticket.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                """
                UPDATE tickets SET priority_id = ?, updated_at = ?
                WHERE ticket_id = ?
                """,
                (priority.priority_id, now, ticket.id),
            )
            self._log_ticket(
                ticket.id,
                TicketLogAction.UPDATED,
                details=f"priority changed to {priority.slug}",
            )
        logger.info("Set priority of ticket #%d to %s", ticket.id, priority.slug)
        return self.get_ticket(ticket.id)  # type: ignore[return-value]

    def assign_ticket(self, ticket: Ticket, entity: Entity) -> Ticket:
        """Assign a ticket to an entity.

        Args:
            ticket: Ticket to assign.
            entity: Entity to assign the ticket to.

        Returns:
            The updated Ticket.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                """
                UPDATE tickets SET assignee_entity_id = ?, updated_at = ?
                WHERE ticket_id = ?
                """,
                (entity.entity_id, now, ticket.id),
            )
            self._log_ticket(
                ticket.id,
                TicketLogAction.ASSIGNED,
                entity,
                f"assigned to {entity.slug}",
            )
        logger.info("Assigned ticket #%d to %s", ticket.id, entity.slug)
        return self.get_ticket(ticket.id)  # type: ignore[return-value]

    def unassign_ticket(self, ticket: Ticket) -> Ticket:
        """Unassign a ticket.

        Args:
            ticket: Ticket to unassign.

        Returns:
            The updated Ticket.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                """
                UPDATE tickets SET assignee_entity_id = NULL, updated_at = ?
                WHERE ticket_id = ?
                """,
                (now, ticket.id),
            )
            self._log_ticket(ticket.id, TicketLogAction.UNASSIGNED)
        logger.info("Unassigned ticket #%d", ticket.id)
        return self.get_ticket(ticket.id)  # type: ignore[return-value]

    def _transition_ticket_no_commit(
        self,
        ticket: Ticket,
        new_state: TicketState,
    ) -> None:
        """Transition a ticket to a new state without committing."""
        allowed = self._state_machine.get_allowed_transitions(ticket.state)
        if new_state not in allowed:
            logger.warning(
                "Invalid transition for ticket #%d: %s -> %s",
                ticket.id,
                ticket.state.slug,
                new_state.slug,
            )
            raise ValueError(
                f"Invalid transition from {ticket.state.slug} to {new_state.slug}"
            )
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            UPDATE tickets SET state_id = ?, updated_at = ?
            WHERE ticket_id = ?
            """,
            (new_state.state_id, now, ticket.id),
        )
        self._log_ticket(
            ticket.id,
            TicketLogAction.STATE_CHANGED,
            details=f"{ticket.state.slug} -> {new_state.slug}",
        )

    def transition_ticket(self, ticket: Ticket, new_state: TicketState) -> Ticket:
        """Transition a ticket to a new state.

        Args:
            ticket: Ticket to transition.
            new_state: Target state.

        Returns:
            The updated Ticket.

        Raises:
            ValueError: If the transition is not allowed.
        """
        with self._conn:
            self._transition_ticket_no_commit(ticket, new_state)
        logger.info(
            "Transitioned ticket #%d: %s -> %s",
            ticket.id,
            ticket.state.slug,
            new_state.slug,
        )
        return self.get_ticket(ticket.id)  # type: ignore[return-value]

    def get_ticket_logs(self, ticket: Ticket) -> list[TicketLog]:
        """Get all logs for a ticket.

        Args:
            ticket: Ticket to get logs for.

        Returns:
            List of ticket logs ordered by log ID.
        """
        cursor = self._conn.execute(
            """
            SELECT
                tl.ticket_id, tl.ticket_log_id, tl.entity_id, tl.action,
                tl.details, tl.created_at,
                e.entity_id AS entity_id_new,
                e.slug AS entity_slug
            FROM ticket_logs tl
            LEFT JOIN entities e ON tl.entity_id = e.entity_id
            WHERE tl.ticket_id = ?
            ORDER BY tl.ticket_log_id
            """,
            (ticket.id,),
        )
        logs: list[TicketLog] = []
        for row in cursor.fetchall():
            entity: Entity | None = None
            if row["entity_id_new"] is not None:
                entity = Entity(
                    entity_id=row["entity_id_new"],
                    slug=row["entity_slug"],
                )
            logs.append(TicketLog.from_row(row, entity))
        return logs

    def add_comment(
        self,
        ticket: Ticket,
        entity: Entity,
        comment: str,
        new_state: TicketState | None = None,
    ) -> Ticket:
        """Add a comment to a ticket.

        Args:
            ticket: Ticket to comment on.
            entity: Entity adding the comment.
            comment: Comment text.
            new_state: Optional new state to transition to.

        Returns:
            The updated Ticket.
        """
        with self._conn:
            if new_state is not None:
                self._transition_ticket_no_commit(ticket, new_state)

            now = datetime.now(timezone.utc).isoformat()
            cursor = self._conn.execute(
                "SELECT COALESCE(MAX(comment_id), 0) + 1 "
                "FROM comments WHERE ticket_id = ?",
                (ticket.id,),
            )
            comment_id = cursor.fetchone()[0]
            self._conn.execute(
                """
                INSERT INTO comments (
                    ticket_id, comment_id, entity_id, comment, new_state_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket.id,
                    comment_id,
                    entity.entity_id,
                    comment,
                    new_state.state_id if new_state else None,
                    now,
                ),
            )
        logger.info("Added comment to ticket #%d", ticket.id)
        return self.get_ticket(ticket.id)  # type: ignore[return-value]

    def get_ticket_comments(self, ticket: Ticket) -> list[Comment]:
        """Get all comments for a ticket.

        Args:
            ticket: Ticket to get comments for.

        Returns:
            List of comments ordered by comment ID.
        """
        cursor = self._conn.execute(
            """
            SELECT
                c.ticket_id, c.comment_id, c.entity_id, c.comment,
                c.new_state_id, c.created_at,
                e.entity_id AS entity_id_new,
                e.slug AS entity_slug,
                ts.state_id AS new_state_id_new,
                ts.slug AS new_state_slug
            FROM comments c
            LEFT JOIN entities e ON c.entity_id = e.entity_id
            LEFT JOIN ticket_states ts ON c.new_state_id = ts.state_id
            WHERE c.ticket_id = ?
            ORDER BY c.comment_id
            """,
            (ticket.id,),
        )
        comments: list[Comment] = []
        for row in cursor.fetchall():
            entity: Entity | None = None
            if row["entity_id_new"] is not None:
                entity = Entity(
                    entity_id=row["entity_id_new"],
                    slug=row["entity_slug"],
                )
            new_state: TicketState | None = None
            if row["new_state_id_new"] is not None:
                new_state = TicketState(
                    state_id=row["new_state_id_new"],
                    slug=row["new_state_slug"],
                )
            comments.append(Comment.from_row(row, entity, new_state))
        return comments

    def get_state_machine(self) -> TicketStateMachine:
        """Get the state machine.

        Returns:
            The TicketStateMachine instance.
        """
        return self._state_machine

    def get_priority_machine(self) -> TicketPriorityManager:
        """Get the priority manager.

        Returns:
            The TicketPriorityManager instance.
        """
        return self._priority_manager

    def _ticket_from_row(self, row: sqlite3.Row) -> Ticket:
        """Create a Ticket from a database row.

        Args:
            row: Database row.

        Returns:
            A Ticket instance.
        """
        state = TicketState(
            state_id=row["state_id_new"],
            slug=row["state_slug"],
        )
        priority = TicketPriority(
            priority_id=row["priority_id_new"],
            slug=row["priority_slug"],
        )
        assignee: Entity | None = None
        if row["entity_id"] is not None:
            assignee = Entity(
                entity_id=row["entity_id"],
                slug=row["entity_slug"],
            )
        return Ticket(
            id=row["ticket_id"],
            title=row["title"],
            description=row["description"] if row["description"] else None,
            state=state,
            priority=priority,
            assignee=assignee,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def get_config(self, key: str) -> str | None:
        """Get a config value from the database.

        Args:
            key: Config key.

        Returns:
            Config value if found, None otherwise.
        """
        cursor = self._conn.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else None

    def set_config(self, key: str, value: str) -> None:
        """Set a config value in the database.

        Args:
            key: Config key.
            value: Config value.
        """
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                (key, value),
            )

    @property
    def lock_entities(self) -> bool:
        """Check if entities are locked.

        Returns:
            True if entities are locked, False otherwise.
        """
        value = self.get_config("lock_entities")
        return value == "true"

    @property
    def display_prefix(self) -> str:
        """Get the display prefix for ticket IDs.

        Returns:
            The display prefix, or empty string if not set.
        """
        value = self.get_config("display_prefix")
        return value if value else ""

    def format_ticket_id(self, ticket_id: int) -> str:
        """Format a ticket ID with the display prefix.

        Args:
            ticket_id: The ticket ID to format.

        Returns:
            The formatted ticket ID (e.g., "#123" or "123").
        """
        prefix = self.display_prefix
        return f"{prefix}{ticket_id}" if prefix else str(ticket_id)
