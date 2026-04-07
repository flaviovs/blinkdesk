import sqlite3
from unittest.mock import patch

import blinkdesk.migrate as migrate_module
from blinkdesk._db import CURRENT_SCHEMA_VERSION
from blinkdesk.init import init_db
from blinkdesk.init import seed_db_from_dict
from tests._base import BlinkDeskTestCase


class TestMigrations(BlinkDeskTestCase):
    def test_migrate_v2_to_v3_adds_categories(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.executescript(
                """
                CREATE TABLE entities (
                    entity_id INTEGER PRIMARY KEY,
                    slug TEXT COLLATE NOCASE UNIQUE NOT NULL
                );

                CREATE TABLE ticket_states (
                    state_id INTEGER PRIMARY KEY,
                    slug TEXT COLLATE NOCASE UNIQUE NOT NULL
                );

                CREATE TABLE ticket_priorities (
                    priority_id INTEGER PRIMARY KEY,
                    slug TEXT COLLATE NOCASE UNIQUE NOT NULL
                );

                CREATE TABLE tickets (
                    ticket_id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    state_id INTEGER REFERENCES ticket_states(state_id),
                    priority_id INTEGER REFERENCES ticket_priorities(priority_id),
                    assignee_entity_id INTEGER REFERENCES entities(entity_id),
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                );
                """
            )
            conn.execute("PRAGMA user_version = 2")

            migrate_module.run_migrations(conn)

            user_version = conn.execute("PRAGMA user_version").fetchone()[0]
            self.assertEqual(user_version, CURRENT_SCHEMA_VERSION)
            categories = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'categories'"
            ).fetchone()
            self.assertIsNotNone(categories)
            audit_logs = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'audit_logs'"
            ).fetchone()
            self.assertIsNotNone(audit_logs)

            ticket_cols = conn.execute("PRAGMA table_info(tickets)").fetchall()
            self.assertTrue(any(col[1] == "category_id" for col in ticket_cols))
        finally:
            conn.close()

    def test_run_migrations_logs_when_up_to_date(self) -> None:
        init_db(self.db_path)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION}")
            with self.assertLogs("blinkdesk.migrate", level="INFO") as cm:
                migrate_module.run_migrations(conn)

            self.assertTrue(
                any("Database schema is up to date" in msg for msg in cm.output)
            )
        finally:
            conn.close()

    def test_seed_db_from_dict_rolls_back_on_error(self) -> None:
        init_db(self.db_path)

        with self.assertRaises(ValueError):
            seed_db_from_dict(
                self.db_path,
                {
                    "schema": {
                        "entities": ["alice"],
                        "states": ["open"],
                    },
                    "options": {"default_priority": "urgent"},
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

    def test_migration_step_rolls_back_on_error(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA user_version = 0")
            conn.execute("CREATE TABLE migration_probe (id INTEGER PRIMARY KEY)")

            def bad_migration(connection: sqlite3.Connection) -> None:
                connection.execute("INSERT INTO migration_probe (id) VALUES (1)")
                raise RuntimeError("broken migration")

            with patch.object(migrate_module, "_MIGRATIONS", [(0, bad_migration)]):
                with self.assertRaises(RuntimeError):
                    migrate_module.run_migrations(conn)

            row = conn.execute("SELECT id FROM migration_probe WHERE id = 1").fetchone()
            self.assertIsNone(row)
            user_version = conn.execute("PRAGMA user_version").fetchone()[0]
            self.assertEqual(user_version, 0)
        finally:
            conn.close()
