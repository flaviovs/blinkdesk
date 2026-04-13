import sys
import types
from typing import Any
from unittest.mock import patch

from blinkdesk._mcp import create_mcp_server
from tests._base import BlinkDeskTestCase


class TestMcp(BlinkDeskTestCase):
    def test_count_tickets_by_entity_tool(self) -> None:
        data = {
            "entities": ["alice", "bob"],
            "states": ["open", "closed"],
            "transitions": [{"from": "open", "to": "closed"}],
        }
        system = self._init_system(data)
        alice_open = system.create_ticket("Alice open")
        alice_closed = system.create_ticket("Alice closed")
        system.create_ticket("Unassigned")
        system.assign_ticket(alice_open.id, "alice")
        system.assign_ticket(alice_closed.id, "alice")
        system.transition_ticket(alice_closed.id, "closed")
        system.close()

        fake_mcp = types.ModuleType("mcp")
        fake_server = types.ModuleType("mcp.server")
        fake_fastmcp = types.ModuleType("mcp.server.fastmcp")

        class FakeFastMCP:
            def __init__(self, *_args: Any, **_kwargs: Any) -> None:
                self.tools: dict[str, Any] = {}

            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func

                return decorator

        fake_fastmcp.FastMCP = FakeFastMCP
        fake_server.fastmcp = fake_fastmcp
        fake_mcp.server = fake_server

        with patch.dict(
            sys.modules,
            {
                "mcp": fake_mcp,
                "mcp.server": fake_server,
                "mcp.server.fastmcp": fake_fastmcp,
            },
        ):
            mcp = create_mcp_server(self.db_path)
            count_tickets_by_entity = mcp.tools["count_tickets_by_entity"]

            counts = count_tickets_by_entity()
            closed_counts = count_tickets_by_entity(state="closed")

        self.assertEqual(
            counts,
            [
                {"entity_id": 1, "entity": "alice", "ticket_count": 2},
                {"entity_id": None, "entity": None, "ticket_count": 1},
            ],
        )
        self.assertEqual(
            closed_counts,
            [{"entity_id": 1, "entity": "alice", "ticket_count": 1}],
        )

    def test_mcp_not_found_uses_display_prefix(self) -> None:
        data = {
            "states": ["open"],
            "options": {"display_prefix": "BD-"},
        }
        system = self._init_system(data)
        system.close()

        fake_mcp = types.ModuleType("mcp")
        fake_server = types.ModuleType("mcp.server")
        fake_fastmcp = types.ModuleType("mcp.server.fastmcp")

        class FakeFastMCP:
            def __init__(self, *_args: Any, **_kwargs: Any) -> None:
                self.tools: dict[str, Any] = {}

            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func

                return decorator

        fake_fastmcp.FastMCP = FakeFastMCP
        fake_server.fastmcp = fake_fastmcp
        fake_mcp.server = fake_server

        with patch.dict(
            sys.modules,
            {
                "mcp": fake_mcp,
                "mcp.server": fake_server,
                "mcp.server.fastmcp": fake_fastmcp,
            },
        ):
            mcp = create_mcp_server(self.db_path)
            update_ticket = mcp.tools["update_ticket"]
            with self.assertRaises(ValueError) as ctx:
                update_ticket(999, title="Nope")

        self.assertEqual(str(ctx.exception), "Ticket BD-999 not found")

    def test_mcp_custom_server_name(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)
        system.close()

        fake_mcp = types.ModuleType("mcp")
        fake_server = types.ModuleType("mcp.server")
        fake_fastmcp = types.ModuleType("mcp.server.fastmcp")

        captured_name: str = ""

        class FakeFastMCP:
            def __init__(self, name: str, *_args: Any, **_kwargs: Any) -> None:
                nonlocal captured_name
                captured_name = name
                self.tools: dict[str, Any] = {}

            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func

                return decorator

        fake_fastmcp.FastMCP = FakeFastMCP
        fake_server.fastmcp = fake_fastmcp
        fake_mcp.server = fake_server

        with patch.dict(
            sys.modules,
            {
                "mcp": fake_mcp,
                "mcp.server": fake_server,
                "mcp.server.fastmcp": fake_fastmcp,
            },
        ):
            create_mcp_server(self.db_path, "My Tickets")
            self.assertEqual(captured_name, "My Tickets")

        with patch.dict(
            sys.modules,
            {
                "mcp": fake_mcp,
                "mcp.server": fake_server,
                "mcp.server.fastmcp": fake_fastmcp,
            },
        ):
            create_mcp_server(self.db_path)
            self.assertEqual(captured_name, "BlinkDesk")

    def test_find_tickets_uses_after_id_and_limit(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)
        system.create_ticket("Ticket 1")
        system.create_ticket("Ticket 2")
        system.create_ticket("Ticket 3")
        system.close()

        fake_mcp = types.ModuleType("mcp")
        fake_server = types.ModuleType("mcp.server")
        fake_fastmcp = types.ModuleType("mcp.server.fastmcp")

        class FakeFastMCP:
            def __init__(self, *_args: Any, **_kwargs: Any) -> None:
                self.tools: dict[str, Any] = {}

            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func

                return decorator

        fake_fastmcp.FastMCP = FakeFastMCP
        fake_server.fastmcp = fake_fastmcp
        fake_mcp.server = fake_server

        with patch.dict(
            sys.modules,
            {
                "mcp": fake_mcp,
                "mcp.server": fake_server,
                "mcp.server.fastmcp": fake_fastmcp,
            },
        ):
            mcp = create_mcp_server(self.db_path)
            find_tickets = mcp.tools["find_tickets"]

            tickets = find_tickets(after_id=1, limit=1)
            self.assertEqual([t["id"] for t in tickets], [2])

            with self.assertRaises(TypeError):
                find_tickets(offset=1)

    def test_find_tickets_filters_by_priority_and_category(self) -> None:
        data = {
            "states": ["open"],
            "priorities": ["normal", "high"],
            "categories": ["support", "ops"],
        }
        system = self._init_system(data)
        support = system.create_ticket("Support", priority_slug="high")
        ops = system.create_ticket("Ops", priority_slug="normal")
        system.set_ticket_category(support.id, "support")
        system.set_ticket_category(ops.id, "ops")
        system.close()

        fake_mcp = types.ModuleType("mcp")
        fake_server = types.ModuleType("mcp.server")
        fake_fastmcp = types.ModuleType("mcp.server.fastmcp")

        class FakeFastMCP:
            def __init__(self, *_args: Any, **_kwargs: Any) -> None:
                self.tools: dict[str, Any] = {}

            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func

                return decorator

        fake_fastmcp.FastMCP = FakeFastMCP
        fake_server.fastmcp = fake_fastmcp
        fake_mcp.server = fake_server

        with patch.dict(
            sys.modules,
            {
                "mcp": fake_mcp,
                "mcp.server": fake_server,
                "mcp.server.fastmcp": fake_fastmcp,
            },
        ):
            mcp = create_mcp_server(self.db_path)
            find_tickets = mcp.tools["find_tickets"]

            tickets = find_tickets(priority="high", category="support")
            self.assertEqual([t["title"] for t in tickets], ["Support"])

    def test_mcp_category_tools_and_set_ticket_category(self) -> None:
        data = {
            "states": ["open"],
            "categories": ["support"],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Initial")
        system.close()

        fake_mcp = types.ModuleType("mcp")
        fake_server = types.ModuleType("mcp.server")
        fake_fastmcp = types.ModuleType("mcp.server.fastmcp")

        class FakeFastMCP:
            def __init__(self, *_args: Any, **_kwargs: Any) -> None:
                self.tools: dict[str, Any] = {}

            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func

                return decorator

        fake_fastmcp.FastMCP = FakeFastMCP
        fake_server.fastmcp = fake_fastmcp
        fake_mcp.server = fake_server

        with patch.dict(
            sys.modules,
            {
                "mcp": fake_mcp,
                "mcp.server": fake_server,
                "mcp.server.fastmcp": fake_fastmcp,
            },
        ):
            mcp = create_mcp_server(self.db_path)
            list_categories = mcp.tools["list_categories"]
            set_ticket_category = mcp.tools["set_ticket_category"]

            self.assertNotIn("add_category", mcp.tools)
            self.assertNotIn("delete_category", mcp.tools)

            categories = list_categories()
            self.assertEqual([c["slug"] for c in categories], ["support"])

            updated = set_ticket_category(ticket.id, "support")
            self.assertEqual(updated["category"], "support")

    def test_mcp_ticket_create_operator_enforcement(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
            "options": {"require_operator": True},
        }
        system = self._init_system(data)
        system.close()

        fake_mcp = types.ModuleType("mcp")
        fake_server = types.ModuleType("mcp.server")
        fake_fastmcp = types.ModuleType("mcp.server.fastmcp")

        class FakeFastMCP:
            def __init__(self, *_args: Any, **_kwargs: Any) -> None:
                self.tools: dict[str, Any] = {}

            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func

                return decorator

        fake_fastmcp.FastMCP = FakeFastMCP
        fake_server.fastmcp = fake_fastmcp
        fake_mcp.server = fake_server

        with patch.dict(
            sys.modules,
            {
                "mcp": fake_mcp,
                "mcp.server": fake_server,
                "mcp.server.fastmcp": fake_fastmcp,
            },
        ):
            mcp = create_mcp_server(self.db_path)
            create_ticket = mcp.tools["create_ticket"]

            with self.assertRaisesRegex(
                ValueError,
                "Operator is required for operation: create_ticket",
            ):
                create_ticket("No operator")

            created = create_ticket("With operator", operator="alice")
            self.assertEqual(created["title"], "With operator")

    def test_mcp_comment_and_history_use_operator_field(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Initial", operator="alice")
        system.add_comment(ticket.id, "Hello", operator="alice")
        system.close()

        fake_mcp = types.ModuleType("mcp")
        fake_server = types.ModuleType("mcp.server")
        fake_fastmcp = types.ModuleType("mcp.server.fastmcp")

        class FakeFastMCP:
            def __init__(self, *_args: Any, **_kwargs: Any) -> None:
                self.tools: dict[str, Any] = {}

            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func

                return decorator

        fake_fastmcp.FastMCP = FakeFastMCP
        fake_server.fastmcp = fake_fastmcp
        fake_mcp.server = fake_server

        with patch.dict(
            sys.modules,
            {
                "mcp": fake_mcp,
                "mcp.server": fake_server,
                "mcp.server.fastmcp": fake_fastmcp,
            },
        ):
            mcp = create_mcp_server(self.db_path)
            get_ticket_comments = mcp.tools["get_ticket_comments"]
            get_ticket_history = mcp.tools["get_ticket_history"]

            comments = get_ticket_comments(ticket.id)
            logs = get_ticket_history(ticket.id)

        self.assertTrue(comments)
        self.assertIn("operator", comments[0])
        self.assertNotIn("author", comments[0])
        self.assertNotIn("entity", comments[0])

        self.assertTrue(logs)
        self.assertIn("operator", logs[0])
        self.assertNotIn("entity", logs[0])
