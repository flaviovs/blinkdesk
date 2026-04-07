import argparse
import io
import sqlite3
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from blinkdesk.cli.audit import cmd_audit_list, cmd_audit_prune
from blinkdesk.cli.main import main as cli_main
from tests._base import BlinkDeskTestCase


class TestCliAudit(BlinkDeskTestCase):
    def test_audit_list_prints_entries(self) -> None:
        system = self._init_system({"states": ["open"]})
        system.close()
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO audit_logs (created_at, line) VALUES (?, ?)",
                (now, "blinkdesk.system: test line"),
            )
            conn.commit()
        finally:
            conn.close()

        out = io.StringIO()
        args = argparse.Namespace(database_path=self.db_path)
        with redirect_stdout(out):
            cmd_audit_list(args)

        self.assertIn("blinkdesk.system: test line", out.getvalue())

    def test_audit_prune_defaults_to_thirty_days(self) -> None:
        system = self._init_system({"states": ["open"]})
        system.close()
        now = datetime.now(timezone.utc)
        old = (now - timedelta(days=40)).isoformat()
        recent = (now - timedelta(days=5)).isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO audit_logs (created_at, line) VALUES (?, ?)",
                (old, "old entry"),
            )
            conn.execute(
                "INSERT INTO audit_logs (created_at, line) VALUES (?, ?)",
                (recent, "recent entry"),
            )
            conn.commit()
        finally:
            conn.close()

        out = io.StringIO()
        args = argparse.Namespace(database_path=self.db_path)
        with redirect_stdout(out):
            cmd_audit_prune(args)
        self.assertIn("Pruned 1 audit log entry.", out.getvalue())

        conn = sqlite3.connect(self.db_path)
        try:
            lines = [
                row[0]
                for row in conn.execute(
                    "SELECT line FROM audit_logs ORDER BY created_at"
                ).fetchall()
            ]
        finally:
            conn.close()
        self.assertEqual(lines, ["recent entry"])

    def test_audit_prune_uses_configured_keep_days(self) -> None:
        system = self._init_system({"states": ["open"]})
        system.set_config("audit_prune_keep_days", "7")
        system.close()

        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO audit_logs (created_at, line) VALUES (?, ?)",
                (old, "old entry"),
            )
            conn.commit()
        finally:
            conn.close()

        with patch("sys.argv", ["bd", "-d", self.db_path, "audit", "prune"]):
            cli_main()

        conn = sqlite3.connect(self.db_path)
        try:
            lines = [
                row[0] for row in conn.execute("SELECT line FROM audit_logs").fetchall()
            ]
        finally:
            conn.close()
        self.assertFalse(any(line == "old entry" for line in lines))
