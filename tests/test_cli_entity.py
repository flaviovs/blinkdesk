import argparse
import io
from contextlib import redirect_stderr, redirect_stdout

from blinkdesk.cli.entity import cmd_entity_add, cmd_entity_delete
from tests._base import BlinkDeskTestCase


class TestCliEntity(BlinkDeskTestCase):
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

        add_args = argparse.Namespace(
            database_path=self.db_path,
            slug="alice",
        )
        cmd_entity_add(add_args)

        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        delete_args = argparse.Namespace(
            database_path=self.db_path,
            entity_id=entity.entity_id,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_entity_delete(delete_args)
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
