import argparse
import io
import json
import os
import sqlite3
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
from typing import Any

from blinkdesk import TicketingSystem, init_db
from blinkdesk._mcp import create_mcp_server
from blinkdesk.cli.db import cmd_db_get_journal_mode, cmd_db_set_journal_mode
from blinkdesk.cli.entity import cmd_entity_add, cmd_entity_delete
from blinkdesk.cli.ticket import cmd_ticket_list, cmd_ticket_get
from blinkdesk.init import seed_db_from_dict


class TestBlinkDesk(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")

    def tearDown(self) -> None:
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def _init_system(self, data: dict[str, Any]) -> TicketingSystem:
        """Helper to initialize system from test data."""
        init_db(self.db_path)
        seed_db_from_dict(self.db_path, data)
        return TicketingSystem(self.db_path)

    def test_from_dict_creates_system(self) -> None:
        data = {
            "states": ["open", "closed"],
            "transitions": [
                {"from": "open", "to": "closed"},
            ],
        }
        system = self._init_system(data)
        states = system.get_state_machine().get_all_states()
        self.assertEqual(len(states), 2)
        self.assertEqual(states[0].slug, "open")
        self.assertEqual(states[1].slug, "closed")

    def test_from_dict_with_entities(self) -> None:
        data = {
            "entities": ["alice", "support"],
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        entities = system.list_entities()
        self.assertEqual(len(entities), 2)
        self.assertEqual(entities[0].slug, "alice")
        self.assertEqual(entities[1].slug, "support")

    def test_single_state_allowed(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)
        states = system.get_state_machine().get_all_states()
        self.assertEqual(len(states), 1)
        self.assertEqual(states[0].slug, "open")

        ticket = system.create_ticket("Test")
        self.assertEqual(ticket.state.slug, "open")

    def test_create_and_get_ticket(self) -> None:
        data = {
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test ticket", "Description")
        self.assertEqual(ticket.title, "Test ticket")
        self.assertEqual(ticket.description, "Description")
        self.assertEqual(ticket.state.slug, "open")
        self.assertIsNone(ticket.assignee)

        fetched = system.get_ticket(ticket.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.title, "Test ticket")

    def test_update_ticket(self) -> None:
        data = {
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Old title")
        updated = system.update_ticket(ticket, "New title")
        self.assertEqual(updated.title, "New title")

    def test_assign_and_unassign_ticket(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        assigned = system.assign_ticket(ticket, entity)
        self.assertEqual(assigned.assignee, entity)

        unassigned = system.unassign_ticket(assigned)
        self.assertIsNone(unassigned.assignee)

    def test_transition_ticket(self) -> None:
        data = {
            "states": ["open", "in_progress", "closed"],
            "transitions": [
                {"from": "open", "to": "in_progress"},
                {"from": "in_progress", "to": "closed"},
            ],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        in_progress = system.get_state_machine().get_state_by_slug("in_progress")
        assert in_progress is not None

        transitioned = system.transition_ticket(ticket, in_progress)
        self.assertEqual(transitioned.state.slug, "in_progress")

    def test_transition_invalid_raises(self) -> None:
        data = {
            "states": ["open", "in_progress", "closed"],
            "transitions": [
                {"from": "open", "to": "in_progress"},
                {"from": "in_progress", "to": "closed"},
            ],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        closed = system.get_state_machine().get_state_by_slug("closed")
        assert closed is not None

        with self.assertRaises(ValueError) as ctx:
            system.transition_ticket(ticket, closed)
        self.assertIn("Invalid transition", str(ctx.exception))

    def test_delete_entity_with_tickets_fails(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.assign_ticket(ticket, entity)

        result = system.delete_entity(entity)
        self.assertFalse(result)

    def test_delete_entity_without_tickets_succeeds(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        result = system.delete_entity(entity)
        self.assertTrue(result)

        deleted = system.get_entity(entity.entity_id)
        self.assertIsNone(deleted)

    def test_list_tickets(self) -> None:
        data = {
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        assigned = system.assign_ticket(ticket, entity)
        self.assertEqual(assigned.assignee, entity)

        unassigned = system.unassign_ticket(assigned)
        self.assertIsNone(unassigned.assignee)

    def test_transition_ticket(self) -> None:
        data = {
            "states": [
                "open",
                "in_progress",
                "closed",
            ],
            "transitions": [
                {"from": "open", "to": "in_progress"},
                {"from": "in_progress", "to": "closed"},
            ],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        in_progress = system.get_state_machine().get_state_by_slug("in_progress")
        assert in_progress is not None

        transitioned = system.transition_ticket(ticket, in_progress)
        self.assertEqual(transitioned.state.slug, "in_progress")

    def test_transition_invalid_raises(self) -> None:
        data = {
            "states": [
                "open",
                "in_progress",
                "closed",
            ],
            "transitions": [
                {"from": "open", "to": "in_progress"},
                {"from": "in_progress", "to": "closed"},
            ],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        closed = system.get_state_machine().get_state_by_slug("closed")
        assert closed is not None

        with self.assertRaises(ValueError) as ctx:
            system.transition_ticket(ticket, closed)
        self.assertIn("Invalid transition", str(ctx.exception))

    def test_delete_entity_with_tickets_fails(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.assign_ticket(ticket, entity)

        result = system.delete_entity(entity)
        self.assertFalse(result)

    def test_delete_entity_without_tickets_succeeds(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        result = system.delete_entity(entity)
        self.assertTrue(result)

        deleted = system.get_entity(entity.entity_id)
        self.assertIsNone(deleted)

    def test_list_tickets(self) -> None:
        data = {
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        system.create_ticket("Ticket 1")
        system.create_ticket("Ticket 2")

        tickets = system.list_tickets()
        self.assertEqual(len(tickets), 2)
        self.assertEqual(tickets[0].title, "Ticket 1")
        self.assertEqual(tickets[1].title, "Ticket 2")

    def test_entity_add(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)

        args = argparse.Namespace(
            database_path=self.db_path,
            slug="alice",
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_entity_add(args)
        output = out.getvalue()
        self.assertIn("Entity added: alice", output)

        entity = system.get_entity_by_slug("alice")
        self.assertIsNotNone(entity)
        self.assertEqual(entity.slug, "alice")

    def test_entity_delete_succeeds(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)

        args = argparse.Namespace(
            database_path=self.db_path,
            slug="alice",
        )
        cmd_entity_add(args)

        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        args = argparse.Namespace(
            database_path=self.db_path,
            entity_id=entity.entity_id,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_entity_delete(args)
        output = out.getvalue()
        self.assertIn("Entity deleted: alice", output)

        deleted = system.get_entity(entity.entity_id)
        self.assertIsNone(deleted)

    def test_entity_delete_linked_to_ticket(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.assign_ticket(ticket, entity)

        args = argparse.Namespace(
            database_path=self.db_path,
            entity_id=entity.entity_id,
        )
        out = io.StringIO()
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stdout(out), redirect_stderr(err):
                cmd_entity_delete(args)
        output = err.getvalue()
        self.assertIn("Cannot delete entity 'alice'", output)

    def test_close(self) -> None:
        data = {
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        system.close()
        with self.assertRaises(Exception):
            system.list_tickets()

    def test_config_get_set(self) -> None:
        data = {
            "states": ["open", "closed"],
            "options": {"lock_entities": "true"},
        }
        system = self._init_system(data)

        value = system.get_config("lock_entities")
        self.assertEqual(value, "true")

        system.set_config("test_key", "test_value")
        value = system.get_config("test_key")
        self.assertEqual(value, "test_value")

        self.assertIsNone(system.get_config("nonexistent"))

    def test_db_get_and_set_journal_mode(self) -> None:
        init_db(self.db_path)

        set_args = argparse.Namespace(database_path=self.db_path, mode="wal")
        set_out = io.StringIO()
        with redirect_stdout(set_out):
            cmd_db_set_journal_mode(set_args)
        self.assertIn("journal_mode set to: wal", set_out.getvalue().strip())

        get_args = argparse.Namespace(database_path=self.db_path)
        get_out = io.StringIO()
        with redirect_stdout(get_out):
            cmd_db_get_journal_mode(get_args)
        self.assertEqual(get_out.getvalue().strip(), "wal")

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("PRAGMA journal_mode")
            self.assertEqual(cursor.fetchone()[0].lower(), "wal")
        finally:
            conn.close()

    def test_lock_entities_property(self) -> None:
        data = {
            "states": ["open"],
            "options": {"lock_entities": "true"},
        }
        system = self._init_system(data)
        self.assertTrue(system.lock_entities)

        system.set_config("lock_entities", "false")
        self.assertFalse(system.lock_entities)

    def test_add_and_get_comment(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.add_comment(ticket, entity, "This is a comment")

        comments = system.get_ticket_comments(ticket)
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].comment, "This is a comment")
        self.assertEqual(comments[0].entity, entity)

    def test_comment_with_state_transition(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed"],
            "transitions": [
                {"from": "open", "to": "closed"},
            ],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        closed = system.get_state_machine().get_state_by_slug("closed")
        assert closed is not None

        system.add_comment(ticket, entity, "Closing ticket", new_state=closed)

        comments = system.get_ticket_comments(ticket)
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].new_state, closed)

    def test_get_ticket_logs(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        logs = system.get_ticket_logs(ticket)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].action.value, "created")

    def test_display_prefix_property(self) -> None:
        data = {
            "states": ["open"],
            "options": {"display_prefix": "#"},
        }
        system = self._init_system(data)
        self.assertEqual(system.display_prefix, "#")

    def test_format_ticket_id(self) -> None:
        data = {
            "states": ["open"],
            "options": {"display_prefix": "#"},
        }
        system = self._init_system(data)
        self.assertEqual(system.format_ticket_id(123), "#123")

    def test_format_ticket_id_no_prefix(self) -> None:
        data = {
            "states": ["open"],
            "options": {"display_prefix": ""},
        }
        system = self._init_system(data)
        self.assertEqual(system.format_ticket_id(123), "123")

    def test_ticket_list_table(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.assign_ticket(ticket, entity)

        args = argparse.Namespace(
            database_path=self.db_path,
            output_format="table",
            state=None,
            assignee=None,
            priority=None,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_list(args)
        output = out.getvalue()
        self.assertIn("open", output)
        self.assertIn("alice", output)

    def test_ticket_list_json(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.assign_ticket(ticket, entity)

        args = argparse.Namespace(
            database_path=self.db_path,
            output_format="json",
            state=None,
            assignee=None,
            priority=None,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_list(args)
        output = json.loads(out.getvalue())

        self.assertEqual(output[0]["state"], "open")
        self.assertEqual(output[0]["assignee"], "alice")

    def test_ticket_get_table(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.assign_ticket(ticket, entity)

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            output_format="table",
            no_logs=False,
            no_comments=False,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_get(args)
        output = out.getvalue()
        self.assertIn("open", output)
        self.assertIn("alice", output)

    def test_ticket_get_json(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.assign_ticket(ticket, entity)

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            output_format="json",
            no_logs=False,
            no_comments=False,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_get(args)
        output = json.loads(out.getvalue())

        self.assertEqual(output["state"], "open")
        self.assertEqual(output["assignee"], "alice")

    def test_ticket_list_table_applies_prefix_once(self) -> None:
        data = {
            "states": ["open"],
            "options": {"display_prefix": "BD-"},
        }
        system = self._init_system(data)
        system.create_ticket("Test")

        args = argparse.Namespace(
            database_path=self.db_path,
            output_format="table",
            state=None,
            assignee=None,
            priority=None,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_list(args)
        output = out.getvalue()

        self.assertIn("BD-1", output)
        self.assertNotIn("BD-BD-1", output)

    def test_ticket_get_table_applies_prefix_once(self) -> None:
        data = {
            "states": ["open"],
            "options": {"display_prefix": "BD-"},
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            output_format="table",
            no_logs=False,
            no_comments=False,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_get(args)
        output = out.getvalue()

        self.assertIn("ID:       BD-1", output)
        self.assertNotIn("BD-BD-1", output)

    def test_ticket_get_table_includes_logs_and_comments(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.add_comment(ticket, entity, "Test comment")

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            output_format="table",
            no_logs=False,
            no_comments=False,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_get(args)
        output = out.getvalue()
        self.assertIn("Logs:", output)
        self.assertIn("Comments:", output)
        self.assertIn("Test comment", output)

    def test_ticket_get_json_includes_logs_and_comments(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.add_comment(ticket, entity, "Test comment")

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            output_format="json",
            no_logs=False,
            no_comments=False,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_get(args)
        output = json.loads(out.getvalue())

        self.assertIn("logs", output)
        self.assertIn("comments", output)
        self.assertEqual(len(output["logs"]), 1)
        self.assertEqual(len(output["comments"]), 1)
        self.assertEqual(output["comments"][0]["comment"], "Test comment")

    def test_ticket_get_json_excludes_logs(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.add_comment(ticket, entity, "Test comment")

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            output_format="json",
            no_logs=True,
            no_comments=False,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_get(args)
        output = json.loads(out.getvalue())

        self.assertNotIn("logs", output)
        self.assertIn("comments", output)

    def test_ticket_get_json_excludes_comments(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.add_comment(ticket, entity, "Test comment")

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            output_format="json",
            no_logs=False,
            no_comments=True,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_get(args)
        output = json.loads(out.getvalue())

        self.assertIn("logs", output)
        self.assertNotIn("comments", output)

    def test_ticket_get_table_excludes_logs_and_comments_with_flags(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.add_comment(ticket, entity, "Test comment")

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            output_format="table",
            no_logs=True,
            no_comments=True,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_get(args)
        output = out.getvalue()

        self.assertNotIn("Logs:", output)
        self.assertNotIn("Comments:", output)
        self.assertNotIn("Test comment", output)

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
            mcp = create_mcp_server(self.db_path, "My Tickets")
            self.assertEqual(captured_name, "My Tickets")

        with patch.dict(
            sys.modules,
            {
                "mcp": fake_mcp,
                "mcp.server": fake_server,
                "mcp.server.fastmcp": fake_fastmcp,
            },
        ):
            mcp = create_mcp_server(self.db_path)
            self.assertEqual(captured_name, "BlinkDesk")


if __name__ == "__main__":
    unittest.main()
