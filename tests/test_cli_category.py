import argparse
import io
from contextlib import redirect_stderr, redirect_stdout

from blinkdesk.cli.category import (
    cmd_category_add,
    cmd_category_delete,
    cmd_category_rename,
)
from tests._base import BlinkDeskTestCase


class TestCliCategory(BlinkDeskTestCase):
    def test_category_add_and_rename(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)

        add_args = argparse.Namespace(database_path=self.db_path, slug="support")
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_category_add(add_args)
        self.assertIn("Category added: support", out.getvalue())

        rename_args = argparse.Namespace(
            database_path=self.db_path,
            old_slug="support",
            new_slug="helpdesk",
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_category_rename(rename_args)
        self.assertIn("Category renamed: support -> helpdesk", out.getvalue())

        category = system.get_category_by_slug("helpdesk")
        self.assertIsNotNone(category)

    def test_category_delete_requires_force_when_linked(self) -> None:
        data = {
            "states": ["open"],
            "categories": ["support"],
        }
        system = self._init_system(data)
        category = system.get_category_by_slug("support")
        assert category is not None
        ticket = system.create_ticket("Test")
        system.set_ticket_category(ticket, category)

        args = argparse.Namespace(
            database_path=self.db_path,
            slug="support",
            force=False,
        )
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stderr(err):
                cmd_category_delete(args)
        self.assertIn("Cannot delete category 'support'", err.getvalue())

    def test_category_delete_force_clears_ticket_and_logs(self) -> None:
        data = {
            "states": ["open"],
            "categories": ["support"],
        }
        system = self._init_system(data)
        category = system.get_category_by_slug("support")
        assert category is not None
        ticket = system.create_ticket("Test")
        system.set_ticket_category(ticket, category)

        args = argparse.Namespace(
            database_path=self.db_path,
            slug="support",
            force=True,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_category_delete(args)
        self.assertIn("Category deleted: support", out.getvalue())

        refreshed = system.get_ticket(ticket.id)
        assert refreshed is not None
        self.assertIsNone(refreshed.category)
        logs = system.get_ticket_logs(refreshed)
        self.assertTrue(
            any(
                log.details
                == "category cleared due to forced category deletion: support"
                for log in logs
            )
        )
