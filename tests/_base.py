import os
import tempfile
import unittest
from typing import Any

from blinkdesk import TicketingSystem, init_db
from blinkdesk.init import seed_db_from_dict


class BlinkDeskTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")

    def tearDown(self) -> None:
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def _init_system(self, data: dict[str, Any]) -> TicketingSystem:
        init_db(self.db_path)
        schema_keys = {"entities", "states", "priorities", "transitions"}

        if "schema" not in data:
            schema: dict[str, Any] = {
                key: data[key] for key in schema_keys if key in data
            }
            normalized_data = {
                key: value for key, value in data.items() if key not in schema_keys
            }
            normalized_data["schema"] = schema
        else:
            normalized_data = data

        schema = normalized_data.get("schema", {})
        if not isinstance(schema, dict):
            schema = {}

        states = schema.get("states")
        if not isinstance(states, list) or not states:
            states = ["open"]
            schema["states"] = states

        entities = schema.get("entities")
        if not isinstance(entities, list) or not entities:
            schema["entities"] = ["seed"]

        priorities = schema.get("priorities")
        if not isinstance(priorities, list) or not priorities:
            schema["priorities"] = ["low", "normal", "high"]

        transitions = schema.get("transitions")
        if not isinstance(transitions, list) or not transitions:
            schema["transitions"] = [{"from": states[0], "to": states[0]}]

        normalized_data["schema"] = schema

        seed_db_from_dict(self.db_path, normalized_data)
        return TicketingSystem(self.db_path)
