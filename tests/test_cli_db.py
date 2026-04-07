import argparse
import io
import sqlite3
from contextlib import redirect_stdout

from blinkdesk.init import init_db
from blinkdesk.cli.db import cmd_db_get_journal_mode, cmd_db_set_journal_mode
from tests._base import BlinkDeskTestCase


class TestCliDb(BlinkDeskTestCase):
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
