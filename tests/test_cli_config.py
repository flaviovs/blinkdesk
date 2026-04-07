import argparse
import io
from contextlib import redirect_stderr, redirect_stdout

from blinkdesk.cli.config import cmd_config_set
from tests._base import BlinkDeskTestCase


class TestCliConfig(BlinkDeskTestCase):
    def test_config_set_require_operator_accepts_boolean(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)

        args = argparse.Namespace(
            database_path=self.db_path,
            key="require_operator",
            value="true",
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_config_set(args)

        self.assertIn("Config set: require_operator = true", out.getvalue())
        self.assertEqual(system.get_config("require_operator"), "1")

    def test_config_set_require_operator_rejects_non_boolean(self) -> None:
        data = {
            "states": ["open"],
        }
        self._init_system(data)

        args = argparse.Namespace(
            database_path=self.db_path,
            key="require_operator",
            value="yes",
        )
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stderr(err):
                cmd_config_set(args)

        self.assertIn("Invalid boolean value for require_operator: yes", err.getvalue())

    def test_config_set_audit_log_accepts_boolean(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)

        args = argparse.Namespace(
            database_path=self.db_path,
            key="audit_log",
            value="false",
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_config_set(args)

        self.assertIn("Config set: audit_log = false", out.getvalue())
        self.assertEqual(system.get_config("audit_log"), "0")

    def test_config_set_audit_log_rejects_non_boolean(self) -> None:
        data = {
            "states": ["open"],
        }
        self._init_system(data)

        args = argparse.Namespace(
            database_path=self.db_path,
            key="audit_log",
            value="off",
        )
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stderr(err):
                cmd_config_set(args)

        self.assertIn("Invalid boolean value for audit_log: off", err.getvalue())
