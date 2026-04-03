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
        seed_db_from_dict(self.db_path, data)
        return TicketingSystem(self.db_path)
