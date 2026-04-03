from tests._base import BlinkDeskTestCase


class TestStateMachine(BlinkDeskTestCase):
    def test_delete_state_with_tickets_fails(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        system.create_ticket("Test")
        open_state = system.get_state_machine().get_state_by_slug("open")
        assert open_state is not None
        result = system.get_state_machine().delete_state(open_state)
        self.assertFalse(result)

    def test_delete_state_without_tickets_succeeds(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed", "wontfix"],
            "transitions": [
                {"from": "open", "to": "closed"},
                {"from": "open", "to": "wontfix"},
            ],
        }
        system = self._init_system(data)
        wontfix = system.get_state_machine().get_state_by_slug("wontfix")
        assert wontfix is not None
        result = system.get_state_machine().delete_state(wontfix)
        self.assertTrue(result)
        states = system.get_state_machine().get_all_states()
        self.assertEqual(len(states), 2)
        self.assertNotIn("wontfix", [state.slug for state in states])

    def test_delete_state_removes_transitions(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "pending", "closed"],
            "transitions": [
                {"from": "open", "to": "pending"},
                {"from": "pending", "to": "closed"},
            ],
        }
        system = self._init_system(data)
        pending = system.get_state_machine().get_state_by_slug("pending")
        assert pending is not None
        result = system.get_state_machine().delete_state(pending)
        self.assertTrue(result)
        transitions = system.get_state_machine().get_all_transitions()
        self.assertEqual(len(transitions), 0)

    def test_get_all_transitions(self) -> None:
        data = {
            "states": ["open", "pending", "closed"],
            "transitions": [
                {"from": "open", "to": "pending"},
                {"from": "pending", "to": "closed"},
            ],
        }
        system = self._init_system(data)
        transitions = system.get_state_machine().get_all_transitions()
        self.assertEqual(len(transitions), 2)
        self.assertEqual(transitions[0][0].slug, "open")
        self.assertEqual(transitions[0][1].slug, "pending")
        self.assertEqual(transitions[1][0].slug, "pending")
        self.assertEqual(transitions[1][1].slug, "closed")

    def test_delete_transition(self) -> None:
        data = {
            "states": ["open", "pending", "closed"],
            "transitions": [
                {"from": "open", "to": "pending"},
                {"from": "pending", "to": "closed"},
            ],
        }
        system = self._init_system(data)
        open_state = system.get_state_machine().get_state_by_slug("open")
        pending_state = system.get_state_machine().get_state_by_slug("pending")
        assert open_state is not None
        assert pending_state is not None

        result = system.get_state_machine().delete_transition(open_state, pending_state)
        self.assertTrue(result)

        transitions = system.get_state_machine().get_all_transitions()
        self.assertEqual(len(transitions), 1)

        result = system.get_state_machine().delete_transition(open_state, pending_state)
        self.assertFalse(result)
