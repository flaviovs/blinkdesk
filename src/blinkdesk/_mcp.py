"""MCP server implementation for BlinkDesk."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

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
        priority: str | None = None,
        category: str | None = None,
        order: Literal["id-asc", "id-desc", "priority-asc", "priority-desc"] = "id-asc",
        limit: int = 50,
        after_id: int = 0,
    ) -> list[dict[str, Any]]:
        """Use when searching for issue tickets matching specific criteria in the
        ticket tracking system. Returns cursor-paginated list of ticket summaries
        (id, title, state, priority, assignee). Filter by state, assignee,
        priority, or category slug. Sort by id or priority, ascending or
        descending."""
        if limit < 1:
            raise ValueError("limit must be greater than or equal to 1")

        system = TicketingSystem(database_path)
        try:
            tickets = system.list_tickets(
                state_slug=state,
                assignee_slug=assignee,
                priority_slug=priority,
                category_slug=category,
                after_id=after_id,
            )

            result: list[dict[str, Any]] = []
            for ticket in tickets:
                result.append(
                    {
                        "id": ticket.id,
                        "title": ticket.title,
                        "state": ticket.state.slug,
                        "priority": ticket.priority.slug,
                        "assignee": ticket.assignee.slug if ticket.assignee else None,
                        "category": ticket.category.slug if ticket.category else None,
                        "_priority_order": ticket.priority.priority_id,
                    }
                )

            if order == "id-desc":
                result.sort(key=lambda x: x["id"], reverse=True)
            elif order == "priority-asc":
                result.sort(key=lambda x: int(x["_priority_order"]))
            elif order == "priority-desc":
                result.sort(key=lambda x: int(x["_priority_order"]), reverse=True)
            else:
                result.sort(key=lambda x: x["id"])

            for r in result:
                del r["_priority_order"]

            return result[:limit]
        finally:
            system.close()

    @mcp.tool()
    def get_ticket_details(ticket_id: int) -> dict[str, Any] | None:
        """Use when you need full details of a specific issue ticket by its ID in
        the ticket tracking system. Returns title, description, current state,
        priority, assignee, and timestamps. Returns null if not found."""
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
                "priority": ticket.priority.slug,
                "assignee": ticket.assignee.slug if ticket.assignee else None,
                "category": ticket.category.slug if ticket.category else None,
                "created_at": ticket.created_at.isoformat(),
                "updated_at": ticket.updated_at.isoformat(),
            }
        finally:
            system.close()

    @mcp.tool()
    def count_tickets_by_entity(state: str | None = None) -> list[dict[str, Any]]:
        """Use when you need ticket workload totals grouped by assignee entity
        in the ticket tracking system. Optionally filter by state slug. Includes
        an unassigned bucket only when there are unassigned tickets."""
        system = TicketingSystem(database_path)
        try:
            return system.list_ticket_counts_by_entity(state_slug=state)
        finally:
            system.close()

    @mcp.tool()
    def create_ticket(
        title: str,
        description: str | None = None,
        priority: str = "normal",
        category: str | None = None,
        assignee: str | None = None,
        operator: str | None = None,
    ) -> dict[str, Any]:
        """Use when creating a new issue ticket in the ticket tracking system.
        Title is required, description optional. Priority defaults to 'normal',
        and category/assignee are optional. New tickets start in 'open' state.
        If provided, operator must be a known non-empty entity slug; blank values
        are treated as omitted. Returns the created ticket with ID."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.create_ticket(
                title,
                description,
                priority_slug=priority,
                category_slug=category,
                assignee_slug=assignee,
                operator=operator,
            )
            return {
                "id": ticket.id,
                "title": ticket.title,
                "description": ticket.description,
                "state": ticket.state.slug,
                "priority": ticket.priority.slug,
                "assignee": ticket.assignee.slug if ticket.assignee else None,
                "category": ticket.category.slug if ticket.category else None,
            }
        finally:
            system.close()

    @mcp.tool()
    def update_ticket(
        ticket_id: int,
        title: str,
        operator: str | None = None,
    ) -> dict[str, Any]:
        """Use when modifying the title of an existing issue ticket
        in the ticket tracking system. Provide ticket_id and the new title.
        Returns the updated ticket. Throws if ticket not found."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.update_ticket(ticket_id, title, operator=operator)
            return {
                "id": ticket.id,
                "title": ticket.title,
                "description": ticket.description,
                "state": ticket.state.slug,
                "priority": ticket.priority.slug,
                "category": ticket.category.slug if ticket.category else None,
            }
        finally:
            system.close()

    @mcp.tool()
    def transition_ticket_state(
        ticket_id: int,
        new_state: str,
        operator: str | None = None,
    ) -> dict[str, Any]:
        """Use when changing the state of an issue ticket in the ticket tracking
        system. Provide ticket_id and the target state slug (e.g., 'open', 'closed',
        'in_progress'). Returns the updated ticket. Throws if ticket or state not
        found."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.transition_ticket(
                ticket_id,
                new_state,
                operator=operator,
            )
            return {
                "id": ticket.id,
                "title": ticket.title,
                "state": ticket.state.slug,
                "category": ticket.category.slug if ticket.category else None,
            }
        finally:
            system.close()

    @mcp.tool()
    def assign_ticket(
        ticket_id: int,
        assignee_slug: str,
        operator: str | None = None,
    ) -> dict[str, Any]:
        """Use when assigning an issue ticket to a user or team in the ticket
        tracking system. Provide ticket_id and the entity slug of the assignee.
        Returns the updated ticket. Throws if ticket or entity not found."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.assign_ticket(ticket_id, assignee_slug, operator=operator)
            return {
                "id": ticket.id,
                "title": ticket.title,
                "assignee": ticket.assignee.slug if ticket.assignee else None,
                "category": ticket.category.slug if ticket.category else None,
            }
        finally:
            system.close()

    @mcp.tool()
    def unassign_ticket(ticket_id: int, operator: str | None = None) -> dict[str, Any]:
        """Use when unassigning an issue ticket (removing the assignee) in the
        ticket tracking system. Provide ticket_id. Returns the updated ticket.
        Throws if ticket not found."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.unassign_ticket(ticket_id, operator=operator)
            return {
                "id": ticket.id,
                "title": ticket.title,
                "assignee": None,
                "category": ticket.category.slug if ticket.category else None,
            }
        finally:
            system.close()

    @mcp.tool()
    def search_tickets(
        query: str,
        limit: int = 20,
        include_comments: bool = False,
    ) -> list[dict[str, Any]]:
        """Use when searching issue tickets by keyword in title, description,
        or optionally comments. All words in the query must match (AND logic).
        Results ordered by relevance (title matches first, then description,
        then comments). Provide query string and optional limit."""
        if limit < 1:
            raise ValueError("limit must be greater than or equal to 1")

        system = TicketingSystem(database_path)
        try:
            tickets = system.search_tickets(
                query,
                limit=limit,
                include_comments=include_comments,
            )
            return [
                {
                    "id": ticket.id,
                    "title": ticket.title,
                    "state": ticket.state.slug,
                    "priority": ticket.priority.slug,
                    "assignee": ticket.assignee.slug if ticket.assignee else None,
                    "category": ticket.category.slug if ticket.category else None,
                }
                for ticket in tickets
            ]
        finally:
            system.close()

    @mcp.tool()
    def add_ticket_comment(
        ticket_id: int,
        comment: str,
        operator: str | None = None,
    ) -> dict[str, Any]:
        """Use when adding a comment/note to an existing issue ticket in the
        ticket tracking system. Requires ticket_id and
        comment text. Returns the updated ticket. Throws if ticket or operator not
        found."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.add_comment(ticket_id, comment, operator=operator)
            return {
                "id": ticket.id,
                "title": ticket.title,
                "state": ticket.state.slug,
                "category": ticket.category.slug if ticket.category else None,
            }
        finally:
            system.close()

    @mcp.tool()
    def get_ticket_comments(ticket_id: int) -> list[dict[str, Any]]:
        """Use when you need to see all comments on an issue ticket. Returns
        chronologically ordered list with operator and timestamp. Throws if ticket
        not found."""
        system = TicketingSystem(database_path)
        try:
            comments = system.get_ticket_comments(ticket_id)
            return [
                {
                    "id": c.comment_id,
                    "operator": c.entity.slug if c.entity else None,
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
            logs = system.get_ticket_logs(ticket_id)
            return [
                {
                    "action": log.action,
                    "operator": log.entity.slug if log.entity else None,
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
    def list_ticket_priorities() -> list[str]:
        """Use when you need to know valid priorities for issue tickets in the
        ticket tracking system. Returns all possible priority slugs ordered by
        position (higher position = higher priority/more urgent)."""
        system = TicketingSystem(database_path)
        try:
            priority_manager = system.get_priority_machine()
            priorities = priority_manager.get_all_priorities()
            return [p.slug for p in priorities]
        finally:
            system.close()

    @mcp.tool()
    def set_ticket_priority(
        ticket_id: int,
        priority: str,
        operator: str | None = None,
    ) -> dict[str, Any]:
        """Use when setting/changing the priority of an issue ticket in the ticket
        tracking system. Provide ticket_id and the target priority slug
        (e.g., 'low', 'normal', 'high'). Returns the updated ticket.
        Throws if ticket or priority not found."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.set_ticket_priority(ticket_id, priority, operator=operator)
            return {
                "id": ticket.id,
                "title": ticket.title,
                "priority": ticket.priority.slug,
                "category": ticket.category.slug if ticket.category else None,
            }
        finally:
            system.close()

    @mcp.tool()
    def list_categories() -> list[dict[str, Any]]:
        """Use when you need all ticket categories. Returns id and slug for
        each category."""
        system = TicketingSystem(database_path)
        try:
            categories = system.list_categories()
            return [{"id": c.category_id, "slug": c.slug} for c in categories]
        finally:
            system.close()

    @mcp.tool()
    def set_ticket_category(
        ticket_id: int,
        category_slug: str,
        operator: str | None = None,
    ) -> dict[str, Any]:
        """Use when setting/changing the category of an issue ticket in the
        ticket tracking system. Provide ticket_id and target category slug.
        Returns the updated ticket. Throws if ticket or category not found."""
        system = TicketingSystem(database_path)
        try:
            ticket = system.set_ticket_category(
                ticket_id,
                category_slug,
                operator=operator,
            )
            return {
                "id": ticket.id,
                "title": ticket.title,
                "category": ticket.category.slug if ticket.category else None,
            }
        finally:
            system.close()

    @mcp.tool()
    def find_entities(search: str | None = None) -> list[dict[str, Any]]:
        """Use when you need to list users or teams in the ticket tracking system.
        Entities are users or teams that can be assigned issue tickets or add
        comments. Returns id and slug. Optionally filter by search term."""
        system = TicketingSystem(database_path)
        try:
            entities = system.list_entities()
            result = []
            for e in entities:
                if search is None or search.lower() in e.slug.lower():
                    result.append({"id": e.entity_id, "slug": e.slug})
            return result
        finally:
            system.close()

    @mcp.tool()
    def get_entity(
        id: int | None = None, slug: str | None = None
    ) -> dict[str, Any] | None:
        """Use when you need details of a specific user or team in the ticket
        tracking system. Provide either numeric ID or slug string. Returns id and
        slug. Returns null if not found. Requires exactly one of id or slug."""
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
            return {"id": entity.entity_id, "slug": entity.slug}
        finally:
            system.close()

    return mcp
