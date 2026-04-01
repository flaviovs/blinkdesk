"""MCP server implementation for Blink Desk."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from blinkdesk.system import TicketingSystem

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def create_mcp_server(database_path: str) -> "FastMCP":
    """Create an MCP server with Blink Desk tools.

    Args:
        database_path: Path to the SQLite database.

    Returns:
        A FastMCP server instance.
    """
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("Blink Desk", json_response=True)

    @mcp.tool()
    def ticket_list(
        state: str | None = None,
        assignee: str | None = None,
    ) -> list[dict[str, Any]]:
        """List tickets with optional filters."""
        system = TicketingSystem(database_path)
        try:
            tickets = system.list_tickets()

            result = []
            for ticket in tickets:
                if state and ticket.state.slug != state:
                    continue
                if assignee and (
                    ticket.assignee is None or ticket.assignee.slug != assignee
                ):
                    continue

                result.append(
                    {
                        "id": ticket.id,
                        "title": ticket.title,
                        "description": ticket.description,
                        "state": ticket.state.slug,
                        "assignee": ticket.assignee.slug if ticket.assignee else None,
                        "created_at": ticket.created_at.isoformat(),
                        "updated_at": ticket.updated_at.isoformat(),
                    }
                )
            return result
        finally:
            system.close()

    @mcp.tool()
    def ticket_get(ticket_id: int) -> dict[str, Any] | None:
        """Get a ticket by ID."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.get_ticket(ticket_id)
            if ticket is None:
                return None
            return {
                "id": ticket.id,
                "title": ticket.title,
                "description": ticket.description,
                "state": ticket.state.slug,
                "assignee": ticket.assignee.slug if ticket.assignee else None,
                "created_at": ticket.created_at.isoformat(),
                "updated_at": ticket.updated_at.isoformat(),
            }
        finally:
            system.close()

    @mcp.tool()
    def ticket_create(title: str, description: str | None = None) -> dict[str, Any]:
        """Create a new ticket."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.create_ticket(title, description)
            return {
                "id": ticket.id,
                "title": ticket.title,
                "description": ticket.description,
                "state": ticket.state.slug,
            }
        finally:
            system.close()

    @mcp.tool()
    def ticket_update(
        ticket_id: int,
        title: str | None = None,
        description: str | None = None,
        state: str | None = None,
        assignee: str | None = None,
    ) -> dict[str, Any]:
        """Update a ticket."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.get_ticket(ticket_id)
            if ticket is None:
                raise ValueError(f"Ticket #{ticket_id} not found")

            if title or description:
                ticket = system.update_ticket(
                    ticket, title or ticket.title, description
                )

            if state:
                state_machine = system.get_state_machine()
                target_state = state_machine.get_state_by_slug(state)
                if target_state is None:
                    raise ValueError(f"Unknown state: {state}")
                ticket = system.transition_ticket(ticket, target_state)

            if assignee is not None:
                if assignee:
                    entity = system.get_entity_by_slug(assignee)
                    if entity is None:
                        raise ValueError(f"Unknown entity: {assignee}")
                    ticket = system.assign_ticket(ticket, entity)
                else:
                    ticket = system.unassign_ticket(ticket)

            return {
                "id": ticket.id,
                "title": ticket.title,
                "description": ticket.description,
                "state": ticket.state.slug,
                "assignee": ticket.assignee.slug if ticket.assignee else None,
            }
        finally:
            system.close()

    @mcp.tool()
    def ticket_comment_add(ticket_id: int, entity: str, comment: str) -> dict[str, Any]:
        """Add a comment to a ticket."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.get_ticket(ticket_id)
            if ticket is None:
                raise ValueError(f"Ticket #{ticket_id} not found")

            entity_obj = system.get_entity_by_slug(entity)
            if entity_obj is None:
                raise ValueError(f"Unknown entity: {entity}")

            ticket = system.add_comment(ticket, entity_obj, comment)
            return {
                "id": ticket.id,
                "title": ticket.title,
                "state": ticket.state.slug,
            }
        finally:
            system.close()

    @mcp.tool()
    def entity_list() -> list[dict[str, Any]]:
        """List all entities."""
        system = TicketingSystem(database_path)
        try:
            entities = system.list_entities()
            return [
                {"id": e.entity_id, "slug": e.slug, "name": e.name} for e in entities
            ]
        finally:
            system.close()

    @mcp.tool()
    def entity_get(
        id: int | None = None, slug: str | None = None
    ) -> dict[str, Any] | None:
        """Get an entity by ID or slug."""
        if id is None and slug is None:
            raise ValueError("Either id or slug must be provided")

        system = TicketingSystem(database_path)
        try:
            if id:
                entity = system.get_entity(id)
            else:
                entity = system.get_entity_by_slug(slug)  # type: ignore[arg-type]

            if entity is None:
                return None
            return {"id": entity.entity_id, "slug": entity.slug, "name": entity.name}
        finally:
            system.close()

    return mcp
