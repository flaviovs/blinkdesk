import argparse
import io
import json
from contextlib import redirect_stdout

from blinkdesk.cli.ticket import cmd_ticket_get, cmd_ticket_list
from tests._base import BlinkDeskTestCase


class TestCliTicket(BlinkDeskTestCase):
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
