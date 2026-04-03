"""MCP server implementation for BlinkDesk."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from blinkdesk.system import TicketingSystem

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def create_mcp_server(database_path: str, server_name: str = "BlinkDesk") -> "FastMCP":
    """Create an MCP server with BlinkDesk tools.

    Args:
        database_path: Path to the SQLite database.
        server_name: Name for the MCP server (default: "BlinkDesk").

    Returns:
        A FastMCP server instance.
    """
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(server_name, json_response=True)

    @mcp.tool()
    def find_tickets(
        state: str | None = None,
        assignee: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Use when searching for issue tickets matching specific criteria in the
        ticket tracking system. Returns paginated list of ticket summaries
        (id, title, state, assignee). Filter by state slug or assignee slug."""
        system = TicketingSystem(database_path)
        try:
            tickets = system.list_tickets()

            result = []
            count = 0
            for ticket in tickets:
                if state and ticket.state.slug != state:
                    continue
                if assignee and (
                    ticket.assignee is None or ticket.assignee.slug != assignee
                ):
                    continue

                if count >= offset and count < offset + limit:
                    result.append(
                        {
                            "id": ticket.id,
                            "title": ticket.title,
                            "state": ticket.state.slug,
                            "assignee": ticket.assignee.slug
                            if ticket.assignee
                            else None,
                        }
                    )
                count += 1
            return result
        finally:
            system.close()

    @mcp.tool()
    def get_ticket_details(ticket_id: int) -> dict[str, Any] | None:
        """Use when you need full details of a specific issue ticket by its ID in
        the ticket tracking system. Returns title, description, current state,
        assignee, and timestamps. Returns null if not found."""
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
    def create_ticket(title: str, description: str | None = None) -> dict[str, Any]:
        """Use when creating a new issue ticket in the ticket tracking system.
        Title is required, description optional. New tickets start in 'open' state
        with no assignee. Returns the created ticket with ID."""
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
    def update_ticket(
        ticket_id: int,
        title: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Use when modifying the title or description of an existing issue ticket
        in the ticket tracking system. Provide ticket_id and at least one of title
        or description. Returns the updated ticket. Throws if ticket not found."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.get_ticket(ticket_id)
            if ticket is None:
                formatted_ticket_id = system.format_ticket_id(ticket_id)
                raise ValueError(f"Ticket {formatted_ticket_id} not found")

            ticket = system.update_ticket(ticket, title or ticket.title, description)
            return {
                "id": ticket.id,
                "title": ticket.title,
                "description": ticket.description,
                "state": ticket.state.slug,
            }
        finally:
            system.close()

    @mcp.tool()
    def transition_ticket_state(ticket_id: int, new_state: str) -> dict[str, Any]:
        """Use when changing the state of an issue ticket in the ticket tracking
        system. Provide ticket_id and the target state slug (e.g., 'open', 'closed',
        'in_progress'). Returns the updated ticket. Throws if ticket or state not
        found."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.get_ticket(ticket_id)
            if ticket is None:
                formatted_ticket_id = system.format_ticket_id(ticket_id)
                raise ValueError(f"Ticket {formatted_ticket_id} not found")

            state_machine = system.get_state_machine()
            target_state = state_machine.get_state_by_slug(new_state)
            if target_state is None:
                raise ValueError(f"Unknown state: {new_state}")

            ticket = system.transition_ticket(ticket, target_state)
            return {
                "id": ticket.id,
                "title": ticket.title,
                "state": ticket.state.slug,
            }
        finally:
            system.close()

    @mcp.tool()
    def assign_ticket(ticket_id: int, assignee_slug: str) -> dict[str, Any]:
        """Use when assigning an issue ticket to a user or team in the ticket
        tracking system. Provide ticket_id and the entity slug of the assignee.
        Returns the updated ticket. Throws if ticket or entity not found."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.get_ticket(ticket_id)
            if ticket is None:
                formatted_ticket_id = system.format_ticket_id(ticket_id)
                raise ValueError(f"Ticket {formatted_ticket_id} not found")

            entity = system.get_entity_by_slug(assignee_slug)
            if entity is None:
                raise ValueError(f"Unknown entity: {assignee_slug}")

            ticket = system.assign_ticket(ticket, entity)
            return {
                "id": ticket.id,
                "title": ticket.title,
                "assignee": ticket.assignee.slug if ticket.assignee else None,
            }
        finally:
            system.close()

    @mcp.tool()
    def unassign_ticket(ticket_id: int) -> dict[str, Any]:
        """Use when unassigning an issue ticket (removing the assignee) in the
        ticket tracking system. Provide ticket_id. Returns the updated ticket.
        Throws if ticket not found."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.get_ticket(ticket_id)
            if ticket is None:
                formatted_ticket_id = system.format_ticket_id(ticket_id)
                raise ValueError(f"Ticket {formatted_ticket_id} not found")

            ticket = system.unassign_ticket(ticket)
            return {
                "id": ticket.id,
                "title": ticket.title,
                "assignee": None,
            }
        finally:
            system.close()

    @mcp.tool()
    def search_tickets(query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Use when searching issue tickets by keyword in title or description.
        Returns matching tickets with relevance ranking. Use for fuzzy search in
        the ticket tracking system."""
        system = TicketingSystem(database_path)
        try:
            tickets = system.list_tickets()
            query_lower = query.lower()

            result = []
            for ticket in tickets:
                if query_lower in ticket.title.lower() or (
                    ticket.description and query_lower in ticket.description.lower()
                ):
                    result.append(
                        {
                            "id": ticket.id,
                            "title": ticket.title,
                            "state": ticket.state.slug,
                        }
                    )
                    if len(result) >= limit:
                        break
            return result
        finally:
            system.close()

    @mcp.tool()
    def add_ticket_comment(
        ticket_id: int, author_slug: str, comment: str
    ) -> dict[str, Any]:
        """Use when adding a comment/note to an existing issue ticket in the
        ticket tracking system. Requires ticket_id, author entity slug, and
        comment text. Returns the updated ticket. Throws if ticket or author not
        found."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.get_ticket(ticket_id)
            if ticket is None:
                formatted_ticket_id = system.format_ticket_id(ticket_id)
                raise ValueError(f"Ticket {formatted_ticket_id} not found")

            entity = system.get_entity_by_slug(author_slug)
            if entity is None:
                raise ValueError(f"Unknown entity: {author_slug}")

            ticket = system.add_comment(ticket, entity, comment)
            return {
                "id": ticket.id,
                "title": ticket.title,
                "state": ticket.state.slug,
            }
        finally:
            system.close()

    @mcp.tool()
    def get_ticket_comments(ticket_id: int) -> list[dict[str, Any]]:
        """Use when you need to see all comments on an issue ticket. Returns
        chronologically ordered list with author and timestamp. Throws if ticket
        not found."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.get_ticket(ticket_id)
            if ticket is None:
                formatted_ticket_id = system.format_ticket_id(ticket_id)
                raise ValueError(f"Ticket {formatted_ticket_id} not found")

            comments = system.get_ticket_comments(ticket)
            return [
                {
                    "id": c.comment_id,
                    "author": c.entity.slug if c.entity else None,
                    "text": c.comment,
                    "created_at": c.created_at.isoformat(),
                }
                for c in comments
            ]
        finally:
            system.close()

    @mcp.tool()
    def get_ticket_history(ticket_id: int) -> list[dict[str, Any]]:
        """Use when you need audit trail of an issue ticket: state changes,
        assignments, updates. Returns chronological log of all modifications.
        Throws if ticket not found."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.get_ticket(ticket_id)
            if ticket is None:
                formatted_ticket_id = system.format_ticket_id(ticket_id)
                raise ValueError(f"Ticket {formatted_ticket_id} not found")

            logs = system.get_ticket_logs(ticket)
            return [
                {
                    "action": log.action,
                    "entity": log.entity.slug if log.entity else None,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ]
        finally:
            system.close()

    @mcp.tool()
    def list_ticket_states() -> list[dict[str, Any]]:
        """Use when you need to know valid states for issue tickets in the ticket
        tracking system. Returns all possible states with their slugs."""
        system = TicketingSystem(database_path)
        try:
            state_machine = system.get_state_machine()
            states = state_machine.get_all_states()
            return [{"id": s.state_id, "slug": s.slug} for s in states]
        finally:
            system.close()

    @mcp.tool()
    def find_entities(search: str | None = None) -> list[dict[str, Any]]:
        """Use when you need to list users or teams in the ticket tracking system.
        Entities are users or teams that can be assigned issue tickets or author
        comments. Returns id, slug, and name. Optionally filter by search term."""
        system = TicketingSystem(database_path)
        try:
            entities = system.list_entities()
            result = []
            for e in entities:
                if (
                    search is None
                    or search.lower() in e.slug.lower()
                    or search.lower() in e.name.lower()
                ):
                    result.append({"id": e.entity_id, "slug": e.slug, "name": e.name})
            return result
        finally:
            system.close()

    @mcp.tool()
    def get_entity(
        id: int | None = None, slug: str | None = None
    ) -> dict[str, Any] | None:
        """Use when you need details of a specific user or team in the ticket
        tracking system. Provide either numeric ID or slug string. Returns id,
        slug, name. Returns null if not found. Requires exactly one of id or slug."""
        if id is None and slug is None:
            raise ValueError("Either id or slug must be provided")
        if id is not None and slug is not None:
            raise ValueError("Provide only id OR slug, not both")

        system = TicketingSystem(database_path)
        try:
            if id is not None:
                entity = system.get_entity(id)
            else:
                entity = system.get_entity_by_slug(slug)  # type: ignore[arg-type]

            if entity is None:
                return None
            return {"id": entity.entity_id, "slug": entity.slug, "name": entity.name}
        finally:
            system.close()

    return mcp
