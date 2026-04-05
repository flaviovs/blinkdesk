import os
import sqlite3

from blinkdesk import init_db
from blinkdesk.init import seed_db_from_dict, seed_db_from_toml
from tests._base import BlinkDeskTestCase


class TestInit(BlinkDeskTestCase):
    def test_seed_db_from_toml_reads_schema_section(self) -> None:
        init_db(self.db_path)
        schema_path = f"{self.temp_dir}/schema.toml"

        with open(schema_path, "w", encoding="utf-8") as schema_file:
            schema_file.write(
                """[schema]
entities = [\"alice\", \"bob\"]
states = [\"open\", \"closed\"]
priorities = [\"low\", \"normal\", \"high\"]

[[schema.transitions]]
from = \"open\"
to = \"closed\"

[options]
display_prefix = \"BD-\"
lock_entities = false
default_priority = \"normal\"
"""
            )

        seed_db_from_toml(self.db_path, schema_path)

        conn = sqlite3.connect(self.db_path)
        try:
            entities = conn.execute(
                "SELECT slug FROM entities ORDER BY entity_id"
            ).fetchall()
            states = conn.execute(
                "SELECT slug FROM ticket_states ORDER BY state_id"
            ).fetchall()
            transitions = conn.execute(
                "SELECT COUNT(*) FROM state_transitions"
            ).fetchone()[0]
            display_prefix = conn.execute(
                "SELECT value FROM config WHERE key = 'display_prefix'"
            ).fetchone()[0]

            self.assertEqual([row[0] for row in entities], ["alice", "bob"])
            self.assertEqual([row[0] for row in states], ["open", "closed"])
            self.assertEqual(transitions, 1)
            self.assertEqual(display_prefix, "BD-")
        finally:
            conn.close()
            os.remove(schema_path)

    def test_seed_db_from_dict_reads_schema_section(self) -> None:
        init_db(self.db_path)

        seed_db_from_dict(
            self.db_path,
            {
                "schema": {
                    "entities": ["alice", "bob"],
                    "states": ["open", "closed"],
                    "priorities": ["low", "normal", "high"],
                    "transitions": [{"from": "open", "to": "closed"}],
                },
                "options": {
                    "display_prefix": "BD-",
                    "lock_entities": False,
                    "default_priority": "normal",
                },
            },
        )

        conn = sqlite3.connect(self.db_path)
        try:
            entities = conn.execute(
                "SELECT slug FROM entities ORDER BY entity_id"
            ).fetchall()
            states = conn.execute(
                "SELECT slug FROM ticket_states ORDER BY state_id"
            ).fetchall()
            transitions = conn.execute(
                "SELECT COUNT(*) FROM state_transitions"
            ).fetchone()[0]
            display_prefix = conn.execute(
                "SELECT value FROM config WHERE key = 'display_prefix'"
            ).fetchone()[0]

            self.assertEqual([row[0] for row in entities], ["alice", "bob"])
            self.assertEqual([row[0] for row in states], ["open", "closed"])
            self.assertEqual(transitions, 1)
            self.assertEqual(display_prefix, "BD-")
        finally:
            conn.close()

    def test_top_level_schema_keys_are_not_seeded(self) -> None:
        init_db(self.db_path)

        with self.assertRaisesRegex(
            ValueError, "schema.entities must be a non-empty list"
        ):
            seed_db_from_dict(
                self.db_path,
                {
                    "entities": ["alice"],
                    "states": ["open"],
                    "options": {"default_priority": "normal"},
                },
            )

        conn = sqlite3.connect(self.db_path)
        try:
            entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            states = conn.execute("SELECT COUNT(*) FROM ticket_states").fetchone()[0]
            self.assertEqual(entities, 0)
            self.assertEqual(states, 0)
        finally:
            conn.close()

    def test_schema_lists_must_be_non_empty(self) -> None:
        init_db(self.db_path)

        for key in ("entities", "states", "priorities", "transitions"):
            with self.subTest(key=key):
                with self.assertRaisesRegex(
                    ValueError, f"schema.{key} must be a non-empty list"
                ):
                    seed_db_from_dict(
                        self.db_path,
                        {
                            "schema": {
                                "entities": ["alice"],
                                "states": ["open"],
                                "priorities": ["normal"],
                                "transitions": [{"from": "open", "to": "open"}],
                                key: [],
                            },
                            "options": {"default_priority": "normal"},
                        },
                    )
