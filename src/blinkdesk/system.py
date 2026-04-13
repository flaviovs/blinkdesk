"""Main entry point for the ticketing system."""

import logging
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from blinkdesk.audit import DEFAULT_AUDIT_PRUNE_KEEP_DAYS, SQLiteAuditLogHandler
from blinkdesk.category import Category
from blinkdesk.comment import Comment
from blinkdesk.entity import Entity
from blinkdesk.migrate import run_migrations
from blinkdesk.priority import TicketPriority, TicketPriorityManager
from blinkdesk.state import TicketState, TicketStateMachine
from blinkdesk.ticket import Ticket
from blinkdesk.ticket_log import TicketLog, TicketLogAction

logger = logging.getLogger(__name__)
_BLINKDESK_LOGGER_NAME = "blinkdesk"

_TICKET_SELECT_QUERY = """
SELECT
    t.ticket_id, t.title, t.description, t.state_id, t.priority_id,
    t.assignee_entity_id, t.category_id, t.created_at, t.updated_at,
    e.entity_id, e.slug AS entity_slug,
    c.category_id AS category_id_new,
    c.slug AS category_slug,
    ts.state_id AS state_id_new,
    ts.slug AS state_slug,
    tp.priority_id AS priority_id_new,
    tp.slug AS priority_slug
FROM tickets t
LEFT JOIN entities e ON t.assignee_entity_id = e.entity_id
LEFT JOIN categories c ON t.category_id = c.category_id
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
        if not Path(db_path).exists():
            raise FileNotFoundError(f"Database file not found: {db_path}")
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        run_migrations(self._conn)
        self._state_machine = TicketStateMachine(self._conn)
        self._priority_manager = TicketPriorityManager(self._conn)
        self._audit_handler: SQLiteAuditLogHandler | None = None
        self._previous_blinkdesk_logger_level: int | None = None
        self._configure_audit_logger()

    def close(self) -> None:
        """Close the database connection."""
        try:
            self._teardown_audit_logger()
            if random.random() < 0.01:
                self._conn.execute("PRAGMA main.incremental_vacuum")
        finally:
            self._conn.close()

    def _configure_audit_logger(self) -> None:
        """Attach the SQLite audit handler when audit logging is enabled."""
        if not self.audit_log:
            return
        blinkdesk_logger = logging.getLogger(_BLINKDESK_LOGGER_NAME)
        for existing_handler in blinkdesk_logger.handlers:
            if (
                isinstance(existing_handler, SQLiteAuditLogHandler)
                and existing_handler.db_path == self._db_path
            ):
                return
        self._previous_blinkdesk_logger_level = blinkdesk_logger.level
        blinkdesk_logger.setLevel(logging.INFO)
        handler = SQLiteAuditLogHandler(self._db_path)
        handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        blinkdesk_logger.addHandler(handler)
        self._audit_handler = handler

    def _teardown_audit_logger(self) -> None:
        """Detach the SQLite audit handler from the blinkdesk logger."""
        if self._audit_handler is None:
            return
        blinkdesk_logger = logging.getLogger(_BLINKDESK_LOGGER_NAME)
        blinkdesk_logger.removeHandler(self._audit_handler)
        if self._previous_blinkdesk_logger_level is not None:
            blinkdesk_logger.setLevel(self._previous_blinkdesk_logger_level)
            self._previous_blinkdesk_logger_level = None
        self._audit_handler.close()
        self._audit_handler = None

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

    def create_category(self, slug: str) -> Category:
        """Create a new category.

        Args:
            slug: URL-friendly slug for the category.

        Returns:
            The created Category.
        """
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO categories (slug) VALUES (?)",
                (slug,),
            )
        last_id = cursor.lastrowid
        if last_id is None:
            raise ValueError("Failed to create category")
        logger.info("Created category: %s", slug)
        return Category(category_id=last_id, slug=slug)

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

    def get_category(self, category_id: int) -> Category | None:
        """Get a category by ID.

        Args:
            category_id: ID of the category.

        Returns:
            The Category if found, None otherwise.
        """
        cursor = self._conn.execute(
            "SELECT category_id, slug FROM categories WHERE category_id = ?",
            (category_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return Category.from_row(row)

    def get_category_by_slug(self, slug: str) -> Category | None:
        """Get a category by slug.

        Args:
            slug: Slug of the category.

        Returns:
            The Category if found, None otherwise.
        """
        cursor = self._conn.execute(
            "SELECT category_id, slug FROM categories WHERE slug = ?",
            (slug,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return Category.from_row(row)

    def list_categories(self) -> list[Category]:
        """List all categories.

        Returns:
            List of all categories ordered by category_id.
        """
        cursor = self._conn.execute(
            "SELECT category_id, slug FROM categories ORDER BY category_id"
        )
        return [Category.from_row(row) for row in cursor.fetchall()]

    def rename_category(self, old_slug: str, new_slug: str) -> Category:
        """Rename a category.

        Args:
            old_slug: Current slug of the category.
            new_slug: New slug for the category.

        Returns:
            The updated Category.

        Raises:
            ValueError: If category not found or new slug already exists.
        """
        category = self.get_category_by_slug(old_slug)
        if category is None:
            raise ValueError(f"Category not found: {old_slug}")
        if old_slug != new_slug:
            existing = self.get_category_by_slug(new_slug)
            if existing is not None:
                raise ValueError(f"Category already exists: {new_slug}")

        with self._conn:
            self._conn.execute(
                "UPDATE categories SET slug = ? WHERE category_id = ?",
                (new_slug, category.category_id),
            )
        logger.info("Renamed category: %s -> %s", old_slug, new_slug)
        return Category(category_id=category.category_id, slug=new_slug)

    def delete_entity(self, slug: str) -> bool:
        """Delete an entity if it's not assigned to any tickets.

        Args:
            slug: Entity slug to delete.

        Returns:
            True if deleted, False if entity is assigned to tickets.

        Raises:
            ValueError: If the entity does not exist.
        """
        entity = self.get_entity_by_slug(slug)
        if entity is None:
            raise ValueError(f"Entity not found: {slug}")
        try:
            with self._conn:
                self._conn.execute(
                    "DELETE FROM entities WHERE entity_id = ?", (entity.entity_id,)
                )
        except sqlite3.IntegrityError:
            logger.info(
                "Skipped deleting entity %s: entity is linked to tickets",
                entity.slug,
            )
            return False
        logger.info("Deleted entity: %s", entity.slug)
        return True

    def delete_category(self, slug: str, force: bool = False) -> bool:
        """Delete a category, optionally clearing it from linked tickets.

        Args:
            slug: Category slug to delete.
            force: When True, remove category from linked tickets first.

        Returns:
            True if deleted, False if linked tickets exist and force=False.

        Raises:
            ValueError: If the category does not exist.
        """
        category = self.get_category_by_slug(slug)
        if category is None:
            raise ValueError(f"Category not found: {slug}")
        try:
            with self._conn:
                if force:
                    ticket_rows = self._conn.execute(
                        "SELECT ticket_id FROM tickets WHERE category_id = ? "
                        "ORDER BY ticket_id",
                        (category.category_id,),
                    ).fetchall()
                    for row in ticket_rows:
                        now = datetime.now(timezone.utc).isoformat()
                        self._conn.execute(
                            "UPDATE tickets SET category_id = NULL, updated_at = ? "
                            "WHERE ticket_id = ?",
                            (now, row["ticket_id"]),
                        )
                        self._log_ticket(
                            row["ticket_id"],
                            TicketLogAction.UPDATED,
                            details=(
                                "category cleared due to forced category "
                                f"deletion: {category.slug}"
                            ),
                        )

                self._conn.execute(
                    "DELETE FROM categories WHERE category_id = ?",
                    (category.category_id,),
                )
        except sqlite3.IntegrityError:
            logger.info(
                "Skipped deleting category %s: category is linked to tickets",
                category.slug,
            )
            return False
        logger.info("Deleted category: %s", category.slug)
        return True

    def _log_ticket(
        self,
        ticket_id: int,
        action: str,
        operator: Entity | None = None,
        details: str | None = None,
    ) -> None:
        """Log an action for a ticket.

        Args:
            ticket_id: ID of the ticket.
            action: Action performed.
            operator: Operator that performed the action, if any.
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
                operator.entity_id if operator else None,
                action,
                details,
                now,
            ),
        )

    def _resolve_operator(
        self,
        operator: str | None,
        operation: str,
    ) -> Entity | None:
        """Resolve and validate an operator for ticket mutation operations.

        Args:
            operator: Operator entity slug or None.
            operation: Operation name used in error messages.

        Returns:
            The resolved entity or None when optional and omitted.

        Raises:
            ValueError: If an operator slug is unknown or operator is required.
        """
        if operator is not None:
            operator = operator.strip()
            if operator == "":
                operator = None

        resolved_operator: Entity | None = None
        if operator is not None:
            resolved_operator = self.get_entity_by_slug(operator)
            if resolved_operator is None:
                raise ValueError(f"Operator not found: {operator}")

        if self.require_operator and resolved_operator is None:
            raise ValueError(f"Operator is required for operation: {operation}")

        return resolved_operator

    def _operator_slug(self, operator: Entity | None) -> str:
        """Return a human-friendly slug for an operator in logger messages."""
        return operator.slug if operator is not None else "*anonymous*"

    def _require_ticket(self, ticket_id: int) -> Ticket:
        """Resolve a ticket by ID or raise ValueError when missing."""
        ticket = self.get_ticket(ticket_id)
        if ticket is None:
            raise ValueError(f"Ticket {self.format_ticket_id(ticket_id)} not found")
        return ticket

    def _require_state_slug(self, state_slug: str) -> TicketState:
        """Resolve a state by slug or raise ValueError when missing."""
        state = self._state_machine.get_state_by_slug(state_slug)
        if state is None:
            raise ValueError(f"Unknown state: {state_slug}")
        return state

    def _require_priority_slug(self, priority_slug: str) -> TicketPriority:
        """Resolve a priority by slug or raise ValueError when missing."""
        priority = self._priority_manager.get_priority_by_slug(priority_slug)
        if priority is None:
            raise ValueError(f"Unknown priority: {priority_slug}")
        return priority

    def _require_entity_slug(self, entity_slug: str, *, context: str) -> Entity:
        """Resolve an entity by slug or raise ValueError when missing."""
        entity = self.get_entity_by_slug(entity_slug)
        if entity is None:
            raise ValueError(f"{context} not found: {entity_slug}")
        return entity

    def _require_category_slug(self, category_slug: str) -> Category:
        """Resolve a category by slug or raise ValueError when missing."""
        category = self.get_category_by_slug(category_slug)
        if category is None:
            raise ValueError(f"Category not found: {category_slug}")
        return category

    def create_ticket(
        self,
        title: str,
        description: str | None = None,
        priority_slug: str | None = None,
        category_slug: str | None = None,
        assignee_slug: str | None = None,
        operator: str | None = None,
    ) -> Ticket:
        """Create a new ticket.

        Args:
            title: Title of the ticket.
            description: Optional description of the ticket.
            priority_slug: Optional priority slug (defaults to "normal").
            category_slug: Optional category slug.
            assignee_slug: Optional assignee entity slug.
            operator: Optional operator slug performing this mutation.

        Returns:
            The created Ticket.

        Raises:
            ValueError: If no states are defined in the system.
        """
        operator_entity = self._resolve_operator(operator, operation="create_ticket")
        states = self._state_machine.get_all_states()
        if not states:
            raise ValueError("No states defined in the system")

        selected_priority_slug = (
            priority_slug if priority_slug is not None else "normal"
        )
        priority = self._priority_manager.get_priority_by_slug(selected_priority_slug)
        if priority is None:
            if priority_slug is None:
                raise ValueError("Default priority 'normal' not found")
            raise ValueError(f"Unknown priority: {selected_priority_slug}")

        category: Category | None = None
        if category_slug is not None:
            category = self._require_category_slug(category_slug)

        assignee: Entity | None = None
        if assignee_slug is not None:
            assignee = self._require_entity_slug(assignee_slug, context="Assignee")

        initial_state = states[0]
        now = datetime.now(timezone.utc).isoformat()
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO tickets (
                    title, description, state_id, priority_id,
                    assignee_entity_id, category_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    description,
                    initial_state.state_id,
                    priority.priority_id,
                    assignee.entity_id if assignee else None,
                    category.category_id if category else None,
                    now,
                    now,
                ),
            )
            last_id = cursor.lastrowid
            if last_id is None:
                raise ValueError("Failed to create ticket")
            self._log_ticket(last_id, TicketLogAction.CREATED, operator=operator_entity)
        logger.info(
            "Created ticket #%d: %s (%s)",
            last_id,
            title,
            self._operator_slug(operator_entity),
        )
        return Ticket(
            id=last_id,
            title=title,
            description=description,
            state=initial_state,
            priority=priority,
            assignee=assignee,
            category=category,
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
        state_slug: str | None = None,
        assignee_slug: str | None = None,
        priority_slug: str | None = None,
        category_slug: str | None = None,
        after_id: int | None = None,
        limit: int | None = None,
    ) -> list[Ticket]:
        """List all tickets.

        Args:
            state_slug: Optional state slug to filter by.
            assignee_slug: Optional assignee slug to filter by.
            priority_slug: Optional priority slug to filter by.
            category_slug: Optional category slug to filter by.
            after_id: Optional cursor ticket ID. When provided, only tickets
                with IDs greater than this value are returned.
            limit: Optional maximum number of tickets to return.

        Returns:
            List of all tickets ordered by ticket_id.

        Raises:
            ValueError: If after_id is negative or limit is less than 1.
        """
        if after_id is not None and after_id < 0:
            raise ValueError("after_id must be greater than or equal to 0")
        if limit is not None and limit < 1:
            raise ValueError("limit must be greater than or equal to 1")

        query = _TICKET_SELECT_QUERY
        conditions: list[str] = []
        params: list[int | str] = []

        if state_slug:
            conditions.append("ts.state_id = ?")
            params.append(self._require_state_slug(state_slug).state_id)
        if assignee_slug:
            conditions.append("t.assignee_entity_id = ?")
            params.append(
                self._require_entity_slug(assignee_slug, context="Assignee").entity_id
            )
        if priority_slug:
            conditions.append("tp.priority_id = ?")
            params.append(self._require_priority_slug(priority_slug).priority_id)
        if category_slug:
            conditions.append("t.category_id = ?")
            params.append(self._require_category_slug(category_slug).category_id)
        if after_id is not None:
            conditions.append("t.ticket_id > ?")
            params.append(after_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY t.ticket_id"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cursor = self._conn.execute(query, params)
        return [self._ticket_from_row(row) for row in cursor.fetchall()]

    def list_ticket_counts_by_entity(
        self,
        state_slug: str | None = None,
    ) -> list[dict[str, int | str | None]]:
        """List ticket counts grouped by assignee entity.

        Args:
            state_slug: Optional state slug to filter by.

        Returns:
            A list of grouped counts. Each row includes entity_id,
            entity (slug), and ticket_count. Unassigned tickets are represented
            with entity_id/entity as None and only appear when nonzero.

        Raises:
            ValueError: If state_slug is provided but does not exist.
        """
        query = (
            "SELECT e.entity_id, e.slug AS entity, COUNT(t.ticket_id) "
            "AS ticket_count "
            "FROM tickets t "
            "LEFT JOIN entities e ON t.assignee_entity_id = e.entity_id"
        )
        params: list[int] = []

        if state_slug:
            query += " WHERE t.state_id = ?"
            params.append(self._require_state_slug(state_slug).state_id)

        query += (
            " GROUP BY t.assignee_entity_id, e.entity_id, e.slug"
            " ORDER BY ticket_count DESC,"
            " CASE WHEN e.slug IS NULL THEN 1 ELSE 0 END,"
            " e.slug ASC,"
            " e.entity_id ASC"
        )

        cursor = self._conn.execute(query, params)
        return [
            {
                "entity_id": row["entity_id"],
                "entity": row["entity"],
                "ticket_count": row["ticket_count"],
            }
            for row in cursor.fetchall()
        ]

    def update_ticket(
        self,
        ticket_id: int,
        title: str,
        operator: str | None = None,
    ) -> Ticket:
        """Update a ticket's title.

        Args:
            ticket_id: Ticket ID to update.
            title: New title.
            operator: Optional operator slug performing this mutation.

        Returns:
            The updated Ticket.
        """
        ticket = self._require_ticket(ticket_id)
        operator_entity = self._resolve_operator(operator, operation="update_ticket")
        if title == ticket.title:
            logger.warning(
                "Ticket #%d title unchanged (same as current) (%s)",
                ticket.id,
                self._operator_slug(operator_entity),
            )
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
                operator=operator_entity,
                details=f"title changed from '{ticket.title}' to '{title}'",
            )
        logger.info(
            "Updated ticket #%d (%s)",
            ticket.id,
            self._operator_slug(operator_entity),
        )
        return self.get_ticket(ticket.id)  # type: ignore[return-value]

    def set_ticket_priority(
        self,
        ticket_id: int,
        priority_slug: str,
        operator: str | None = None,
    ) -> Ticket:
        """Set a ticket's priority.

        Args:
            ticket_id: Ticket ID to update.
            priority_slug: New priority slug.
            operator: Optional operator slug performing this mutation.

        Returns:
            The updated Ticket.
        """
        ticket = self._require_ticket(ticket_id)
        priority = self._require_priority_slug(priority_slug)
        operator_entity = self._resolve_operator(
            operator,
            operation="set_ticket_priority",
        )
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
                operator=operator_entity,
                details=f"priority changed to {priority.slug}",
            )
        logger.info(
            "Set priority of ticket #%d to %s (%s)",
            ticket.id,
            priority.slug,
            self._operator_slug(operator_entity),
        )
        return self.get_ticket(ticket.id)  # type: ignore[return-value]

    def set_ticket_category(
        self,
        ticket_id: int,
        category_slug: str,
        operator: str | None = None,
    ) -> Ticket:
        """Set a ticket's category.

        Args:
            ticket_id: Ticket ID to update.
            category_slug: New category slug.
            operator: Optional operator slug performing this mutation.

        Returns:
            The updated Ticket.
        """
        ticket = self._require_ticket(ticket_id)
        category = self._require_category_slug(category_slug)
        operator_entity = self._resolve_operator(
            operator,
            operation="set_ticket_category",
        )
        now = datetime.now(timezone.utc).isoformat()
        old_slug = ticket.category.slug if ticket.category else "(none)"
        with self._conn:
            self._conn.execute(
                """
                UPDATE tickets SET category_id = ?, updated_at = ?
                WHERE ticket_id = ?
                """,
                (category.category_id, now, ticket.id),
            )
            self._log_ticket(
                ticket.id,
                TicketLogAction.UPDATED,
                operator=operator_entity,
                details=f"category: {old_slug} => {category.slug}",
            )
        logger.info(
            "Set category of ticket #%d to %s (%s)",
            ticket.id,
            category.slug,
            self._operator_slug(operator_entity),
        )
        return self.get_ticket(ticket.id)  # type: ignore[return-value]

    def remove_ticket_category(
        self,
        ticket_id: int,
        operator: str | None = None,
    ) -> Ticket:
        """Remove a ticket's category.

        Args:
            ticket_id: Ticket ID to update.
            operator: Optional operator slug performing this mutation.

        Returns:
            The updated Ticket.
        """
        ticket = self._require_ticket(ticket_id)
        operator_entity = self._resolve_operator(
            operator,
            operation="remove_ticket_category",
        )
        old_slug = ticket.category.slug if ticket.category else "(none)"
        now = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                """
                UPDATE tickets SET category_id = NULL, updated_at = ?
                WHERE ticket_id = ?
                """,
                (now, ticket.id),
            )
            self._log_ticket(
                ticket.id,
                TicketLogAction.UPDATED,
                operator=operator_entity,
                details=f"category: {old_slug} => (none)",
            )
        logger.info(
            "Removed category from ticket #%d (%s)",
            ticket.id,
            self._operator_slug(operator_entity),
        )
        return self.get_ticket(ticket.id)  # type: ignore[return-value]

    def assign_ticket(
        self,
        ticket_id: int,
        assignee_slug: str,
        operator: str | None = None,
    ) -> Ticket:
        """Assign a ticket to an entity.

        Args:
            ticket_id: Ticket ID to assign.
            assignee_slug: Entity slug to assign the ticket to.
            operator: Optional operator slug performing this mutation.

        Returns:
            The updated Ticket.
        """
        ticket = self._require_ticket(ticket_id)
        entity = self._require_entity_slug(assignee_slug, context="Assignee")
        operator_entity = self._resolve_operator(operator, operation="assign_ticket")
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
                operator_entity,
                f"assigned to {entity.slug}",
            )
        logger.info(
            "Assigned ticket #%d to %s (%s)",
            ticket.id,
            entity.slug,
            self._operator_slug(operator_entity),
        )
        return self.get_ticket(ticket.id)  # type: ignore[return-value]

    def unassign_ticket(
        self,
        ticket_id: int,
        operator: str | None = None,
    ) -> Ticket:
        """Unassign a ticket.

        Args:
            ticket_id: Ticket ID to unassign.
            operator: Optional operator slug performing this mutation.

        Returns:
            The updated Ticket.
        """
        ticket = self._require_ticket(ticket_id)
        operator_entity = self._resolve_operator(operator, operation="unassign_ticket")
        now = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                """
                UPDATE tickets SET assignee_entity_id = NULL, updated_at = ?
                WHERE ticket_id = ?
                """,
                (now, ticket.id),
            )
            self._log_ticket(
                ticket.id,
                TicketLogAction.UNASSIGNED,
                operator=operator_entity,
            )
        logger.info(
            "Unassigned ticket #%d (%s)",
            ticket.id,
            self._operator_slug(operator_entity),
        )
        return self.get_ticket(ticket.id)  # type: ignore[return-value]

    def _transition_ticket_no_commit(
        self,
        ticket: Ticket,
        new_state: TicketState,
        operator: Entity | None = None,
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
            operator=operator,
            details=f"{ticket.state.slug} -> {new_state.slug}",
        )

    def transition_ticket(
        self,
        ticket_id: int,
        new_state_slug: str,
        operator: str | None = None,
    ) -> Ticket:
        """Transition a ticket to a new state.

        Args:
            ticket_id: Ticket ID to transition.
            new_state_slug: Target state slug.
            operator: Optional operator slug performing this mutation.

        Returns:
            The updated Ticket.

        Raises:
            ValueError: If the transition is not allowed.
        """
        ticket = self._require_ticket(ticket_id)
        new_state = self._require_state_slug(new_state_slug)
        operator_entity = self._resolve_operator(
            operator,
            operation="transition_ticket",
        )
        with self._conn:
            self._transition_ticket_no_commit(
                ticket, new_state, operator=operator_entity
            )
        logger.info(
            "Transitioned ticket #%d: %s -> %s (%s)",
            ticket.id,
            ticket.state.slug,
            new_state.slug,
            self._operator_slug(operator_entity),
        )
        return self.get_ticket(ticket.id)  # type: ignore[return-value]

    def get_ticket_logs(self, ticket_id: int) -> list[TicketLog]:
        """Get all logs for a ticket.

        Args:
            ticket_id: Ticket ID to get logs for.

        Returns:
            List of ticket logs ordered by log ID.
        """
        ticket = self._require_ticket(ticket_id)
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
        ticket_id: int,
        comment: str,
        new_state_slug: str | None = None,
        operator: str | None = None,
    ) -> Ticket:
        """Add a comment to a ticket.

        Args:
            ticket_id: Ticket ID to comment on.
            comment: Comment text.
            new_state_slug: Optional new state slug to transition to.
            operator: Operator slug of who is adding the comment.

        Returns:
            The updated Ticket.
        """
        ticket = self._require_ticket(ticket_id)
        new_state: TicketState | None = None
        if new_state_slug is not None:
            new_state = self._require_state_slug(new_state_slug)
        operator_entity = self._resolve_operator(operator, operation="add_comment")
        with self._conn:
            if new_state is not None:
                self._transition_ticket_no_commit(
                    ticket,
                    new_state,
                    operator=operator_entity,
                )

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
                    operator_entity.entity_id if operator_entity else None,
                    comment,
                    new_state.state_id if new_state else None,
                    now,
                ),
            )
        logger.info(
            "Added comment to ticket #%d (%s)",
            ticket.id,
            self._operator_slug(operator_entity),
        )
        return self.get_ticket(ticket.id)  # type: ignore[return-value]

    def get_ticket_comments(self, ticket_id: int) -> list[Comment]:
        """Get all comments for a ticket.

        Args:
            ticket_id: Ticket ID to get comments for.

        Returns:
            List of comments ordered by comment ID.
        """
        ticket = self._require_ticket(ticket_id)
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
        category: Category | None = None
        if row["category_id_new"] is not None:
            category = Category(
                category_id=row["category_id_new"],
                slug=row["category_slug"],
            )
        return Ticket(
            id=row["ticket_id"],
            title=row["title"],
            description=row["description"] if row["description"] else None,
            state=state,
            priority=priority,
            assignee=assignee,
            category=category,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def get_config(self, key: str) -> str | int | None:
        """Get a config value from the database.

        Args:
            key: Config key.

        Returns:
            Config value if found, None otherwise.
        """
        cursor = self._conn.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else None

    def set_config(self, key: str, value: str | int | bool) -> None:
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
        logger.info("Set config value: %s", key)

    @staticmethod
    def _config_value_as_bool(value: Any) -> bool:
        """Interpret a config value as a boolean.

        Args:
            value: Raw config value read from SQLite.

        Returns:
            Boolean interpretation of the value.
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, str):
            return value == "1"
        return False

    @property
    def lock_entities(self) -> bool:
        """Check if entities are locked.

        Returns:
            True if entities are locked, False otherwise.
        """
        value = self.get_config("lock_entities")
        return self._config_value_as_bool(value)

    @property
    def display_prefix(self) -> str:
        """Get the display prefix for ticket IDs.

        Returns:
            The display prefix, or empty string if not set.
        """
        value = self.get_config("display_prefix")
        return str(value) if value else ""

    @property
    def require_operator(self) -> bool:
        """Check whether ticket mutations require an operator.

        Returns:
            True when ticket mutation calls must provide an operator.
        """
        value = self.get_config("require_operator")
        return self._config_value_as_bool(value)

    @property
    def audit_log(self) -> bool:
        """Check whether persistent audit logging is enabled.

        Returns:
            True when audit logs should be recorded.
        """
        value = self.get_config("audit_log")
        if value is None:
            return True
        return self._config_value_as_bool(value)

    def list_audit_logs(self) -> list[tuple[str, str]]:
        """List audit log entries ordered from newest to oldest.

        Returns:
            List of (created_at, line) tuples.
        """
        cursor = self._conn.execute(
            "SELECT created_at, line FROM audit_logs ORDER BY created_at DESC"
        )
        return [(row["created_at"], row["line"]) for row in cursor.fetchall()]

    @property
    def audit_prune_keep_days(self) -> int:
        """Get audit retention in days.

        Returns:
            Number of days to keep in the audit log.

        Raises:
            ValueError: If the configured value is not a valid integer.
        """
        value = self.get_config("audit_prune_keep_days")
        if value is None:
            return DEFAULT_AUDIT_PRUNE_KEEP_DAYS
        try:
            keep_days = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Invalid config audit_prune_keep_days: must be an integer"
            ) from exc
        if keep_days < 0:
            raise ValueError(
                "Invalid config audit_prune_keep_days: must be greater "
                "than or equal to 0"
            )
        return keep_days

    def prune_audit_logs(self) -> int:
        """Delete audit log entries older than the retention period.

        Returns:
            Number of deleted rows.
        """
        keep_days = self.audit_prune_keep_days
        cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
        cutoff_iso = cutoff.isoformat()
        with self._conn:
            cursor = self._conn.execute(
                "DELETE FROM audit_logs WHERE created_at < ?",
                (cutoff_iso,),
            )
        return cursor.rowcount

    def format_ticket_id(self, ticket_id: int) -> str:
        """Format a ticket ID with the display prefix.

        Args:
            ticket_id: The ticket ID to format.

        Returns:
            The formatted ticket ID (e.g., "#123" or "123").
        """
        prefix = self.display_prefix
        return f"{prefix}{ticket_id}" if prefix else str(ticket_id)
