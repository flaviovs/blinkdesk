import argparse
import io
from contextlib import redirect_stderr, redirect_stdout

from blinkdesk.cli.state import (
    cmd_state_add,
    cmd_state_delete,
    cmd_state_transition_add,
    cmd_state_transition_delete,
    cmd_state_transition_list,
)
from tests._base import BlinkDeskTestCase


class TestCliState(BlinkDeskTestCase):
    def test_state_add(self) -> None:
        data = {
            "states": ["open", "closed"],
        }
        system = self._init_system(data)

        args = argparse.Namespace(
            database_path=self.db_path,
            slug="pending",
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_state_add(args)
        output = out.getvalue()
        self.assertIn("State created: pending", output)

        state = system.get_state_machine().get_state_by_slug("pending")
        self.assertIsNotNone(state)
        self.assertEqual(state.slug, "pending")

    def test_state_delete_succeeds(self) -> None:
        data = {
            "states": ["open", "closed", "pending"],
        }
        system = self._init_system(data)

        args = argparse.Namespace(
            database_path=self.db_path,
            slug="pending",
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_state_delete(args)
        output = out.getvalue()
        self.assertIn("State deleted: pending", output)

        state = system.get_state_machine().get_state_by_slug("pending")
        self.assertIsNone(state)

    def test_state_delete_with_tickets_fails(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed"],
            "transitions": [{"from": "open", "to": "closed"}],
        }
        system = self._init_system(data)
        open_state = system.get_state_machine().get_state_by_slug("open")
        assert open_state is not None
        system.create_ticket("Test")

        args = argparse.Namespace(
            database_path=self.db_path,
            slug="open",
        )
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stderr(err):
                cmd_state_delete(args)
        output = err.getvalue()
        self.assertIn("Cannot delete state 'open'", output)

    def test_state_transition_list(self) -> None:
        data = {
            "states": ["open", "pending", "closed"],
            "transitions": [
                {"from": "open", "to": "pending"},
                {"from": "pending", "to": "closed"},
            ],
        }
        self._init_system(data)

        args = argparse.Namespace(database_path=self.db_path)
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_state_transition_list(args)
        output = out.getvalue()
        self.assertIn("open -> pending", output)
        self.assertIn("pending -> closed", output)

    def test_state_transition_add(self) -> None:
        data = {
            "states": ["open", "closed"],
            "transitions": [{"from": "open", "to": "open"}],
        }
        system = self._init_system(data)

        args = argparse.Namespace(
            database_path=self.db_path,
            from_slug="open",
            to_slug="closed",
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_state_transition_add(args)
        output = out.getvalue()
        self.assertIn("Transition added: open -> closed", output)

        transitions = system.get_state_machine().get_all_transitions()
        self.assertEqual(len(transitions), 2)

    def test_state_transition_delete(self) -> None:
        data = {
            "states": ["open", "pending", "closed"],
            "transitions": [
                {"from": "open", "to": "pending"},
                {"from": "pending", "to": "closed"},
            ],
        }
        system = self._init_system(data)

        args = argparse.Namespace(
            database_path=self.db_path,
            from_slug="open",
            to_slug="pending",
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_state_transition_delete(args)
        output = out.getvalue()
        self.assertIn("Transition deleted: open -> pending", output)

        transitions = system.get_state_machine().get_all_transitions()
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0][1].slug, "closed")
