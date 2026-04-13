import argparse
import io
import json
import os
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from blinkdesk.cli.main import main as cli_main
from blinkdesk.cli.ticket import (
    cmd_ticket_assign,
    cmd_ticket_comment,
    cmd_ticket_count_by_entity,
    cmd_ticket_get,
    cmd_ticket_list,
    cmd_ticket_remove_category,
    cmd_ticket_set_category,
    cmd_ticket_set_priority,
    cmd_ticket_transition,
    cmd_ticket_unassign,
)
from tests._base import BlinkDeskTestCase


class TestCliTicket(BlinkDeskTestCase):
    def test_ticket_count_by_entity_json(self) -> None:
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

        args = argparse.Namespace(
            database_path=self.db_path,
            output_format="json",
            state=None,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_count_by_entity(args)
        output = json.loads(out.getvalue())

        self.assertEqual(output[0]["entity"], "alice")
        self.assertEqual(output[0]["ticket_count"], 2)
        self.assertEqual(output[1]["entity"], None)
        self.assertEqual(output[1]["ticket_count"], 1)

    def test_cli_ticket_count_by_entity_supports_state_filter(self) -> None:
        data = {
            "entities": ["alice", "bob"],
            "states": ["open", "closed"],
            "transitions": [{"from": "open", "to": "closed"}],
        }
        system = self._init_system(data)
        alice_open = system.create_ticket("Alice open")
        alice_closed = system.create_ticket("Alice closed")
        system.assign_ticket(alice_open.id, "alice")
        system.assign_ticket(alice_closed.id, "alice")
        system.transition_ticket(alice_closed.id, "closed")

        out = io.StringIO()
        with patch(
            "sys.argv",
            [
                "bd",
                "-d",
                self.db_path,
                "ticket",
                "count-by-entity",
                "--output-format",
                "json",
                "--state",
                "closed",
            ],
        ):
            with redirect_stdout(out):
                cli_main()

        output = json.loads(out.getvalue())
        self.assertEqual(
            output, [{"entity_id": 1, "entity": "alice", "ticket_count": 1}]
        )

    def test_ticket_count_by_entity_fails_for_invalid_state(self) -> None:
        data = {
            "states": ["open"],
        }
        self._init_system(data)

        args = argparse.Namespace(
            database_path=self.db_path,
            output_format="table",
            state="missing",
        )
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stderr(err):
                cmd_ticket_count_by_entity(args)

        self.assertIn("Unknown state: missing", err.getvalue())

    def test_ticket_list_table(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.assign_ticket(ticket.id, entity.slug)

        args = argparse.Namespace(
            database_path=self.db_path,
            output_format="table",
            state=None,
            assignee=None,
            priority=None,
            category=None,
            after_id=None,
            limit=None,
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
        system.assign_ticket(ticket.id, entity.slug)

        args = argparse.Namespace(
            database_path=self.db_path,
            output_format="json",
            state=None,
            assignee=None,
            priority=None,
            category=None,
            after_id=None,
            limit=None,
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
        system.assign_ticket(ticket.id, entity.slug)

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
        system.assign_ticket(ticket.id, entity.slug)

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
            category=None,
            after_id=None,
            limit=None,
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

    def test_ticket_list_json_supports_after_id_and_limit(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)
        system.create_ticket("Ticket 1")
        system.create_ticket("Ticket 2")
        system.create_ticket("Ticket 3")

        args = argparse.Namespace(
            database_path=self.db_path,
            output_format="json",
            state=None,
            assignee=None,
            priority=None,
            category=None,
            after_id=1,
            limit=1,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_list(args)
        output = json.loads(out.getvalue())

        self.assertEqual(len(output), 1)
        self.assertTrue(str(output[0]["id"]).endswith("2"))

    def test_ticket_list_json_filters_by_category(self) -> None:
        data = {
            "states": ["open"],
            "categories": ["support", "ops"],
        }
        system = self._init_system(data)
        ticket_support = system.create_ticket("Support ticket")
        ticket_ops = system.create_ticket("Ops ticket")
        system.set_ticket_category(ticket_support.id, "support")
        system.set_ticket_category(ticket_ops.id, "ops")

        args = argparse.Namespace(
            database_path=self.db_path,
            output_format="json",
            state=None,
            assignee=None,
            priority=None,
            category="support",
            after_id=None,
            limit=None,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_list(args)
        output = json.loads(out.getvalue())

        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]["title"], "Support ticket")
        self.assertEqual(output[0]["category"], "support")

    def test_ticket_get_table_includes_logs_and_comments(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.add_comment(ticket.id, "Test comment", operator=entity.slug)

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
        system.add_comment(ticket.id, "Test comment", operator=entity.slug)

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
        self.assertIn("operator", output["logs"][0])
        self.assertNotIn("entity", output["logs"][0])
        self.assertIn("operator", output["comments"][0])
        self.assertNotIn("entity", output["comments"][0])
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
        system.add_comment(ticket.id, "Test comment", operator=entity.slug)

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
        system.add_comment(ticket.id, "Test comment", operator=entity.slug)

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
        system.add_comment(ticket.id, "Test comment", operator=entity.slug)

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

    def test_ticket_assign(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            assignee="alice",
            operator=None,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_assign(args)
        self.assertIn("Ticket assigned:", out.getvalue())

        refreshed = system.get_ticket(ticket.id)
        assert refreshed is not None
        assert refreshed.assignee is not None
        self.assertEqual(refreshed.assignee.slug, "alice")

    def test_ticket_assign_fails_when_assignee_not_found(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            assignee="missing",
            operator=None,
        )
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stderr(err):
                cmd_ticket_assign(args)
        self.assertIn("Assignee not found: missing", err.getvalue())

    def test_ticket_unassign(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.assign_ticket(ticket.id, entity.slug)

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            operator=None,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_unassign(args)
        self.assertIn("Ticket unassigned:", out.getvalue())

        refreshed = system.get_ticket(ticket.id)
        assert refreshed is not None
        self.assertIsNone(refreshed.assignee)

    def test_ticket_transition(self) -> None:
        data = {
            "states": ["open", "in_progress", "closed"],
            "transitions": [
                {"from": "open", "to": "in_progress"},
                {"from": "in_progress", "to": "closed"},
            ],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            state="in_progress",
            operator=None,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_transition(args)
        self.assertIn("Ticket transitioned:", out.getvalue())

        refreshed = system.get_ticket(ticket.id)
        assert refreshed is not None
        self.assertEqual(refreshed.state.slug, "in_progress")

    def test_ticket_transition_fails_when_state_not_found(self) -> None:
        data = {
            "states": ["open", "closed"],
            "transitions": [{"from": "open", "to": "closed"}],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            state="missing",
            operator=None,
        )
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stderr(err):
                cmd_ticket_transition(args)
        self.assertIn("Unknown state: missing", err.getvalue())

    def test_ticket_transition_fails_when_invalid_transition(self) -> None:
        data = {
            "states": ["open", "in_progress", "closed"],
            "transitions": [{"from": "open", "to": "in_progress"}],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            state="closed",
            operator=None,
        )
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stderr(err):
                cmd_ticket_transition(args)
        self.assertIn("Invalid transition", err.getvalue())

    def test_ticket_set_priority(self) -> None:
        data = {
            "states": ["open"],
            "priorities": ["low", "normal", "high"],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            priority="high",
            operator=None,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_set_priority(args)
        self.assertIn("Ticket priority set:", out.getvalue())

        refreshed = system.get_ticket(ticket.id)
        assert refreshed is not None
        self.assertEqual(refreshed.priority.slug, "high")

    def test_ticket_set_priority_fails_when_priority_not_found(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            priority="missing",
            operator=None,
        )
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stderr(err):
                cmd_ticket_set_priority(args)
        self.assertIn("Unknown priority: missing", err.getvalue())

    def test_ticket_set_category_and_remove_category(self) -> None:
        data = {
            "states": ["open"],
            "categories": ["support"],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        set_args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            category="support",
            operator=None,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_set_category(set_args)
        self.assertIn("Ticket category set:", out.getvalue())

        refreshed = system.get_ticket(ticket.id)
        assert refreshed is not None
        assert refreshed.category is not None
        self.assertEqual(refreshed.category.slug, "support")

        remove_args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            operator=None,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_remove_category(remove_args)
        self.assertIn("Ticket category removed:", out.getvalue())

        refreshed = system.get_ticket(ticket.id)
        assert refreshed is not None
        self.assertIsNone(refreshed.category)

    def test_ticket_set_category_fails_when_category_not_found(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            category="missing",
            operator=None,
        )
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stderr(err):
                cmd_ticket_set_category(args)
        self.assertIn("Category not found: missing", err.getvalue())

    def test_ticket_comment_with_state_transition(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed"],
            "transitions": [{"from": "open", "to": "closed"}],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            operator="alice",
            comment="Closing",
            state="closed",
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ticket_comment(args)
        self.assertIn("Comment added to ticket", out.getvalue())

        refreshed = system.get_ticket(ticket.id)
        assert refreshed is not None
        self.assertEqual(refreshed.state.slug, "closed")

    def test_ticket_comment_fails_when_state_not_found(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        args = argparse.Namespace(
            database_path=self.db_path,
            ticket_id=ticket.id,
            operator="alice",
            comment="Trying state",
            state="missing",
        )
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stderr(err):
                cmd_ticket_comment(args)
        self.assertIn("Unknown state: missing", err.getvalue())

    def test_cli_main_supports_short_flags_for_ticket_subcommands(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed"],
            "priorities": ["low", "normal", "high"],
            "transitions": [{"from": "open", "to": "closed"}],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Initial")

        out = io.StringIO()
        with patch(
            "sys.argv",
            [
                "bd",
                "-d",
                self.db_path,
                "ticket",
                "create",
                "-t",
                "Short title",
                "-m",
                "Short description",
                "-p",
                "high",
            ],
        ):
            with redirect_stdout(out):
                cli_main()

        with patch(
            "sys.argv",
            [
                "bd",
                "-d",
                self.db_path,
                "ticket",
                "assign",
                str(ticket.id),
                "-a",
                "alice",
            ],
        ):
            with redirect_stdout(out):
                cli_main()

        with patch(
            "sys.argv",
            [
                "bd",
                "-d",
                self.db_path,
                "ticket",
                "set-priority",
                str(ticket.id),
                "-p",
                "high",
            ],
        ):
            with redirect_stdout(out):
                cli_main()

        with patch(
            "sys.argv",
            [
                "bd",
                "-d",
                self.db_path,
                "ticket",
                "comment",
                str(ticket.id),
                "-o",
                "alice",
                "-c",
                "Done",
                "-s",
                "closed",
            ],
        ):
            with redirect_stdout(out):
                cli_main()

        output = out.getvalue()
        self.assertIn("Ticket created:", output)
        self.assertIn("Ticket assigned:", output)
        self.assertIn("Ticket priority set:", output)
        self.assertIn("Comment added to ticket", output)

    def test_cli_main_supports_stdin_description_for_ticket_create(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)

        out = io.StringIO()
        with patch(
            "sys.argv",
            [
                "bd",
                "-d",
                self.db_path,
                "ticket",
                "create",
                "-t",
                "From stdin",
                "-m",
                "-",
            ],
        ):
            with patch("sys.stdin", io.StringIO("Body from stdin\nSecond line")):
                with redirect_stdout(out):
                    cli_main()

        created = system.get_ticket(1)
        assert created is not None
        self.assertEqual(created.description, "Body from stdin\nSecond line")
        self.assertIn("Ticket created:", out.getvalue())

    def test_cli_main_supports_file_description_for_ticket_create(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)
        description_path = os.path.join(self.temp_dir, "description.txt")
        with open(description_path, "w", encoding="utf-8") as f:
            f.write("Body from file\nSecond line")

        out = io.StringIO()
        with patch(
            "sys.argv",
            [
                "bd",
                "-d",
                self.db_path,
                "ticket",
                "create",
                "-t",
                "From file",
                "-m",
                f"@{description_path}",
            ],
        ):
            with redirect_stdout(out):
                cli_main()

        os.remove(description_path)

        created = system.get_ticket(1)
        assert created is not None
        self.assertEqual(created.description, "Body from file\nSecond line")
        self.assertIn("Ticket created:", out.getvalue())

    def test_cli_main_supports_short_flag_for_ticket_update_title(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Initial")

        out = io.StringIO()
        with patch(
            "sys.argv",
            [
                "bd",
                "-d",
                self.db_path,
                "ticket",
                "update",
                str(ticket.id),
                "-t",
                "Updated via short option",
            ],
        ):
            with redirect_stdout(out):
                cli_main()

        refreshed = system.get_ticket(ticket.id)
        assert refreshed is not None
        self.assertEqual(refreshed.title, "Updated via short option")
        self.assertIn("Ticket updated:", out.getvalue())

    def test_cli_main_supports_short_flag_for_priority_rename_position(self) -> None:
        with patch("blinkdesk.cli.main.cmd_priority_rename") as mock_cmd:
            with patch(
                "sys.argv",
                [
                    "bd",
                    "-d",
                    self.db_path,
                    "priority",
                    "rename",
                    "normal",
                    "urgent",
                    "-p",
                    "7",
                ],
            ):
                cli_main()

        mock_cmd.assert_called_once()
        args = mock_cmd.call_args[0][0]
        self.assertEqual(args.old_slug, "normal")
        self.assertEqual(args.new_slug, "urgent")
        self.assertEqual(args.position, 7)

    def test_cli_main_supports_short_flags_for_mcp_streamable_http(self) -> None:
        with patch("blinkdesk.cli.mcp.cmd_mcp_streamable_http") as mock_cmd:
            with patch(
                "sys.argv",
                [
                    "bd",
                    "-d",
                    self.db_path,
                    "mcp",
                    "streamable-http",
                    "-n",
                    "Desk",
                    "-H",
                    "0.0.0.0",
                    "-P",
                    "9001",
                ],
            ):
                cli_main()

        mock_cmd.assert_called_once()
        args = mock_cmd.call_args[0][0]
        self.assertEqual(args.name, "Desk")
        self.assertEqual(args.host, "0.0.0.0")
        self.assertEqual(args.port, 9001)

    def test_cli_main_supports_short_flags_for_mcp_sse(self) -> None:
        with patch("blinkdesk.cli.mcp.cmd_mcp_sse") as mock_cmd:
            with patch(
                "sys.argv",
                [
                    "bd",
                    "-d",
                    self.db_path,
                    "mcp",
                    "sse",
                    "-n",
                    "Desk SSE",
                    "-H",
                    "127.0.0.1",
                    "-P",
                    "8123",
                ],
            ):
                cli_main()

        mock_cmd.assert_called_once()
        args = mock_cmd.call_args[0][0]
        self.assertEqual(args.name, "Desk SSE")
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8123)

    def test_cli_error_mentions_short_and_long_database_flags(self) -> None:
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            with patch("sys.argv", ["bd", "ticket", "list"]):
                with redirect_stderr(err):
                    cli_main()

        self.assertIn("-d/--database-path", err.getvalue())

    def test_cli_ticket_list_supports_after_id_and_limit(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)
        system.create_ticket("Ticket 1")
        system.create_ticket("Ticket 2")
        system.create_ticket("Ticket 3")

        out = io.StringIO()
        with patch(
            "sys.argv",
            [
                "bd",
                "-d",
                self.db_path,
                "ticket",
                "list",
                "--output-format",
                "json",
                "--after-id",
                "1",
                "--limit",
                "1",
            ],
        ):
            with redirect_stdout(out):
                cli_main()

        output = json.loads(out.getvalue())
        self.assertEqual(len(output), 1)
        self.assertTrue(str(output[0]["id"]).endswith("2"))

    def test_cli_ticket_list_supports_category_filter(self) -> None:
        data = {
            "states": ["open"],
            "categories": ["support", "ops"],
        }
        system = self._init_system(data)
        support = system.create_ticket("Support")
        ops = system.create_ticket("Ops")
        system.set_ticket_category(support.id, "support")
        system.set_ticket_category(ops.id, "ops")

        out = io.StringIO()
        with patch(
            "sys.argv",
            [
                "bd",
                "-d",
                self.db_path,
                "ticket",
                "list",
                "--output-format",
                "json",
                "--category",
                "support",
            ],
        ):
            with redirect_stdout(out):
                cli_main()

        output = json.loads(out.getvalue())
        self.assertEqual([ticket["title"] for ticket in output], ["Support"])

    def test_ticket_list_fails_for_invalid_after_id(self) -> None:
        data = {
            "states": ["open"],
        }
        self._init_system(data)

        args = argparse.Namespace(
            database_path=self.db_path,
            output_format="table",
            state=None,
            assignee=None,
            priority=None,
            category=None,
            after_id=-1,
            limit=None,
        )
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stderr(err):
                cmd_ticket_list(args)

        self.assertIn("after_id must be greater than or equal to 0", err.getvalue())

    def test_cli_ticket_create_accepts_operator(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        self._init_system(data)

        out = io.StringIO()
        with patch(
            "sys.argv",
            [
                "bd",
                "-d",
                self.db_path,
                "ticket",
                "create",
                "-t",
                "With operator",
                "-o",
                "alice",
            ],
        ):
            with redirect_stdout(out):
                cli_main()

        self.assertIn("Ticket created:", out.getvalue())

    def test_cli_ticket_create_accepts_category(self) -> None:
        data = {
            "states": ["open"],
            "categories": ["support"],
        }
        system = self._init_system(data)

        out = io.StringIO()
        with patch(
            "sys.argv",
            [
                "bd",
                "-d",
                self.db_path,
                "ticket",
                "create",
                "-t",
                "With category",
                "-c",
                "support",
            ],
        ):
            with redirect_stdout(out):
                cli_main()

        created = system.get_ticket(1)
        assert created is not None
        assert created.category is not None
        self.assertEqual(created.category.slug, "support")
        self.assertIn("Ticket created:", out.getvalue())

    def test_cli_ticket_create_fails_for_unknown_category(self) -> None:
        data = {
            "states": ["open"],
            "categories": ["support"],
        }
        self._init_system(data)

        err = io.StringIO()
        with self.assertRaises(SystemExit):
            with patch(
                "sys.argv",
                [
                    "bd",
                    "-d",
                    self.db_path,
                    "ticket",
                    "create",
                    "-t",
                    "Unknown category",
                    "-c",
                    "ghost",
                ],
            ):
                with redirect_stderr(err):
                    cli_main()

        self.assertIn("Category not found: ghost", err.getvalue())

    def test_cli_ticket_create_fails_without_operator_when_required(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
            "options": {"require_operator": True},
        }
        self._init_system(data)

        err = io.StringIO()
        with self.assertRaises(SystemExit):
            with patch(
                "sys.argv",
                [
                    "bd",
                    "-d",
                    self.db_path,
                    "ticket",
                    "create",
                    "-t",
                    "Needs operator",
                ],
            ):
                with redirect_stderr(err):
                    cli_main()

        self.assertIn(
            "Operator is required for operation: create_ticket",
            err.getvalue(),
        )

    def test_cli_ticket_create_fails_for_unknown_operator(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        self._init_system(data)

        err = io.StringIO()
        with self.assertRaises(SystemExit):
            with patch(
                "sys.argv",
                [
                    "bd",
                    "-d",
                    self.db_path,
                    "ticket",
                    "create",
                    "-t",
                    "Unknown operator",
                    "-o",
                    "ghost",
                ],
            ):
                with redirect_stderr(err):
                    cli_main()

        self.assertIn("Operator not found: ghost", err.getvalue())
