"""Ticket state and state machine."""

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TicketState:
    """Represents a ticket state."""

    state_id: int
    slug: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "TicketState":
        """Create a TicketState from a database row.

        Args:
            row: Database row.

        Returns:
            A TicketState instance.
        """
        return cls(
            state_id=row["state_id"],
            slug=row["slug"],
        )


class TicketStateMachine:
    """Manages ticket states and transitions."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Initialize the state machine.

        Args:
            conn: Database connection.
        """
        self._conn = conn

    def get_all_states(self) -> list[TicketState]:
        """Get all ticket states.

        Returns:
            List of all ticket states ordered by state_id.
        """
        cursor = self._conn.execute(
            "SELECT state_id, slug FROM ticket_states ORDER BY state_id"
        )
        return [TicketState.from_row(row) for row in cursor.fetchall()]

    def get_state_by_slug(self, slug: str) -> TicketState | None:
        """Get a state by its slug.

        Args:
            slug: Slug of the state.

        Returns:
            The TicketState if found, None otherwise.
        """
        cursor = self._conn.execute(
            "SELECT state_id, slug FROM ticket_states WHERE slug = ?",
            (slug,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return TicketState.from_row(row)

    def create_state(self, slug: str) -> TicketState:
        """Create a new ticket state.

        Args:
            slug: URL-friendly slug for the state.

        Returns:
            The created TicketState.
        """
        cursor = self._conn.execute(
            "INSERT INTO ticket_states (slug) VALUES (?)",
            (slug,),
        )
        self._conn.commit()
        last_id = cursor.lastrowid
        if last_id is None:
            raise ValueError("Failed to create state")
        return TicketState(state_id=last_id, slug=slug)

    def get_allowed_transitions(self, from_state: TicketState) -> list[TicketState]:
        """Get allowed transitions from a given state.

        Args:
            from_state: The state to get transitions from.

        Returns:
            List of states that can be transitioned to.
        """
        cursor = self._conn.execute(
            """
            SELECT ts.state_id, ts.slug
            FROM state_transitions st
            JOIN ticket_states ts ON st.to_state_id = ts.state_id
            WHERE st.from_state_id = ?
            """,
            (from_state.state_id,),
        )
        return [TicketState.from_row(row) for row in cursor.fetchall()]

    def add_transition(self, from_state: TicketState, to_state: TicketState) -> None:
        """Add a state transition.

        Args:
            from_state: The source state.
            to_state: The destination state.
        """
        self._conn.execute(
            """
            INSERT OR IGNORE INTO state_transitions (from_state_id, to_state_id)
            VALUES (?, ?)
            """,
            (from_state.state_id, to_state.state_id),
        )
        self._conn.commit()

    def get_or_create_state(self, slug: str) -> TicketState:
        """Get a state by slug or create it if it doesn't exist.

        Args:
            slug: URL-friendly slug for the state.

        Returns:
            The existing or newly created TicketState.
        """
        cursor = self._conn.execute(
            "SELECT state_id, slug FROM ticket_states WHERE slug = ?",
            (slug,),
        )
        row = cursor.fetchone()
        if row is not None:
            return TicketState.from_row(row)
        return self.create_state(slug)

    def get_all_transitions(self) -> list[tuple[TicketState, TicketState]]:
        """Get all state transitions.

        Returns:
            List of (from_state, to_state) tuples.
        """
        cursor = self._conn.execute(
            """
            SELECT ts_from.state_id, ts_from.slug, ts_to.state_id, ts_to.slug
            FROM state_transitions st
            JOIN ticket_states ts_from ON st.from_state_id = ts_from.state_id
            JOIN ticket_states ts_to ON st.to_state_id = ts_to.state_id
            ORDER BY ts_from.slug, ts_to.slug
            """
        )
        return [
            (
                TicketState(state_id=row[0], slug=row[1]),
                TicketState(state_id=row[2], slug=row[3]),
            )
            for row in cursor.fetchall()
        ]

    def delete_transition(self, from_state: TicketState, to_state: TicketState) -> bool:
        """Delete a state transition.

        Args:
            from_state: The source state.
            to_state: The destination state.

        Returns:
            True if deleted, False if not found.
        """
        cursor = self._conn.execute(
            "DELETE FROM state_transitions WHERE from_state_id = ? AND to_state_id = ?",
            (from_state.state_id, to_state.state_id),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def delete_state(self, state: TicketState) -> bool:
        """Delete a state if no tickets have this state.

        Args:
            state: State to delete.

        Returns:
            True if deleted, False if tickets exist with this state.
        """
        cursor = self._conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE state_id = ?",
            (state.state_id,),
        )
        count = cursor.fetchone()[0]
        if count > 0:
            return False
        self._conn.execute(
            "DELETE FROM state_transitions WHERE from_state_id = ? OR to_state_id = ?",
            (state.state_id, state.state_id),
        )
        self._conn.execute(
            "DELETE FROM ticket_states WHERE state_id = ?",
            (state.state_id,),
        )
        self._conn.commit()
        return True
