from unittest.mock import patch

from tests._base import BlinkDeskTestCase


class TestSystemCore(BlinkDeskTestCase):
    def test_from_dict_creates_system(self) -> None:
        data = {
            "states": ["open", "closed"],
            "transitions": [
                {"from": "open", "to": "closed"},
            ],
        }
        system = self._init_system(data)
        states = system.get_state_machine().get_all_states()
        self.assertEqual(len(states), 2)
        self.assertEqual(states[0].slug, "open")
        self.assertEqual(states[1].slug, "closed")

    def test_from_dict_with_entities(self) -> None:
        data = {
            "entities": ["alice", "support"],
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        entities = system.list_entities()
        self.assertEqual(len(entities), 2)
        self.assertEqual(entities[0].slug, "alice")
        self.assertEqual(entities[1].slug, "support")

    def test_single_state_allowed(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)
        states = system.get_state_machine().get_all_states()
        self.assertEqual(len(states), 1)
        self.assertEqual(states[0].slug, "open")

        ticket = system.create_ticket("Test")
        self.assertEqual(ticket.state.slug, "open")

    def test_create_and_get_ticket(self) -> None:
        data = {
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test ticket", "Description")
        self.assertEqual(ticket.title, "Test ticket")
        self.assertEqual(ticket.description, "Description")
        self.assertEqual(ticket.state.slug, "open")
        self.assertIsNone(ticket.assignee)

        fetched = system.get_ticket(ticket.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.title, "Test ticket")

    def test_update_ticket(self) -> None:
        data = {
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Old title")
        updated = system.update_ticket(ticket.id, "New title")
        self.assertEqual(updated.title, "New title")

    def test_assign_and_unassign_ticket(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        assigned = system.assign_ticket(ticket.id, entity.slug)
        self.assertEqual(assigned.assignee, entity)

        unassigned = system.unassign_ticket(assigned.id)
        self.assertIsNone(unassigned.assignee)

    def test_transition_ticket(self) -> None:
        data = {
            "states": ["open", "in_progress", "closed"],
            "transitions": [
                {"from": "open", "to": "in_progress"},
                {"from": "in_progress", "to": "closed"},
            ],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        in_progress = system.get_state_machine().get_state_by_slug("in_progress")
        assert in_progress is not None

        transitioned = system.transition_ticket(ticket.id, in_progress.slug)
        self.assertEqual(transitioned.state.slug, "in_progress")

    def test_transition_invalid_raises(self) -> None:
        data = {
            "states": ["open", "in_progress", "closed"],
            "transitions": [
                {"from": "open", "to": "in_progress"},
                {"from": "in_progress", "to": "closed"},
            ],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        closed = system.get_state_machine().get_state_by_slug("closed")
        assert closed is not None

        with self.assertRaises(ValueError) as ctx:
            system.transition_ticket(ticket.id, closed.slug)
        self.assertIn("Invalid transition", str(ctx.exception))

    def test_delete_entity_with_tickets_fails(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.assign_ticket(ticket.id, entity.slug)

        result = system.delete_entity(entity.slug)
        self.assertFalse(result)

    def test_delete_entity_without_tickets_succeeds(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        result = system.delete_entity(entity.slug)
        self.assertTrue(result)

        deleted = system.get_entity(entity.entity_id)
        self.assertIsNone(deleted)

    def test_list_tickets_assign_and_unassign_roundtrip(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        assigned = system.assign_ticket(ticket.id, entity.slug)
        self.assertEqual(assigned.assignee, entity)

        unassigned = system.unassign_ticket(assigned.id)
        self.assertIsNone(unassigned.assignee)

    def test_transition_ticket_multiline_duplicate(self) -> None:
        data = {
            "states": [
                "open",
                "in_progress",
                "closed",
            ],
            "transitions": [
                {"from": "open", "to": "in_progress"},
                {"from": "in_progress", "to": "closed"},
            ],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        in_progress = system.get_state_machine().get_state_by_slug("in_progress")
        assert in_progress is not None

        transitioned = system.transition_ticket(ticket.id, in_progress.slug)
        self.assertEqual(transitioned.state.slug, "in_progress")

    def test_transition_invalid_raises_multiline_duplicate(self) -> None:
        data = {
            "states": [
                "open",
                "in_progress",
                "closed",
            ],
            "transitions": [
                {"from": "open", "to": "in_progress"},
                {"from": "in_progress", "to": "closed"},
            ],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        closed = system.get_state_machine().get_state_by_slug("closed")
        assert closed is not None

        with self.assertRaises(ValueError) as ctx:
            system.transition_ticket(ticket.id, closed.slug)
        self.assertIn("Invalid transition", str(ctx.exception))

    def test_delete_entity_with_tickets_fails_duplicate(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.assign_ticket(ticket.id, entity.slug)

        result = system.delete_entity(entity.slug)
        self.assertFalse(result)

    def test_delete_entity_without_tickets_succeeds_duplicate(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        result = system.delete_entity(entity.slug)
        self.assertTrue(result)

        deleted = system.get_entity(entity.entity_id)
        self.assertIsNone(deleted)

    def test_list_tickets(self) -> None:
        data = {
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        system.create_ticket("Ticket 1")
        system.create_ticket("Ticket 2")

        tickets = system.list_tickets()
        self.assertEqual(len(tickets), 2)
        self.assertEqual(tickets[0].title, "Ticket 1")
        self.assertEqual(tickets[1].title, "Ticket 2")

    def test_list_tickets_with_after_id_and_limit(self) -> None:
        data = {
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        system.create_ticket("Ticket 1")
        system.create_ticket("Ticket 2")
        system.create_ticket("Ticket 3")

        tickets = system.list_tickets(after_id=1, limit=1)
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0].id, 2)

    def test_list_tickets_filters_by_all_supported_fields(self) -> None:
        data = {
            "entities": ["alice", "bob"],
            "states": ["open", "closed"],
            "priorities": ["normal", "high"],
            "categories": ["support", "ops"],
            "transitions": [{"from": "open", "to": "closed"}],
        }
        system = self._init_system(data)

        ticket = system.create_ticket("Matching", priority_slug="high")
        system.assign_ticket(ticket.id, "alice")
        system.set_ticket_category(ticket.id, "support")

        other = system.create_ticket("Non-matching", priority_slug="normal")
        system.assign_ticket(other.id, "bob")
        system.set_ticket_category(other.id, "ops")
        system.transition_ticket(other.id, "closed")

        tickets = system.list_tickets(
            state_slug="open",
            assignee_slug="alice",
            priority_slug="high",
            category_slug="support",
        )

        self.assertEqual([t.title for t in tickets], ["Matching"])

    def test_list_tickets_rejects_invalid_after_id_and_limit(self) -> None:
        data = {
            "states": ["open", "closed"],
        }
        system = self._init_system(data)

        with self.assertRaisesRegex(
            ValueError, "after_id must be greater than or equal to 0"
        ):
            system.list_tickets(after_id=-1)

        with self.assertRaisesRegex(
            ValueError, "limit must be greater than or equal to 1"
        ):
            system.list_tickets(limit=0)

    def test_close(self) -> None:
        data = {
            "states": ["open", "closed"],
        }
        system = self._init_system(data)
        system.close()
        with self.assertRaises(Exception):
            system.list_tickets()

    def test_config_get_set(self) -> None:
        data = {
            "states": ["open", "closed"],
            "options": {"lock_entities": True},
        }
        system = self._init_system(data)

        value = system.get_config("lock_entities")
        self.assertEqual(value, "1")

        system.set_config("test_key", "test_value")
        value = system.get_config("test_key")
        self.assertEqual(value, "test_value")

        self.assertIsNone(system.get_config("nonexistent"))

    def test_set_config_logs_info(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)

        with self.assertLogs("blinkdesk.system", level="INFO") as cm:
            system.set_config("lock_entities", 1)

        self.assertTrue(
            any("Set config value: lock_entities" in msg for msg in cm.output)
        )

    def test_priority_manager_logs_info_for_mutations(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)
        manager = system.get_priority_machine()

        with self.assertLogs("blinkdesk.priority", level="INFO") as cm:
            created = manager.create_priority("urgent", 40)
            renamed = manager.rename_priority("urgent", "critical", 50)
            deleted = manager.delete_priority(renamed)

        self.assertEqual(created.slug, "urgent")
        self.assertEqual(renamed.slug, "critical")
        self.assertTrue(deleted)
        self.assertTrue(any("Created priority: urgent" in msg for msg in cm.output))
        self.assertTrue(
            any("Renamed priority: urgent -> critical" in msg for msg in cm.output)
        )
        self.assertTrue(any("Deleted priority: critical" in msg for msg in cm.output))

    def test_delete_priority_with_tickets_fails(self) -> None:
        data = {
            "states": ["open"],
            "priorities": ["normal", "high"],
        }
        system = self._init_system(data)
        high = system.get_priority_machine().get_priority_by_slug("high")
        assert high is not None

        ticket = system.create_ticket("Test")
        system.set_ticket_priority(ticket.id, high.slug)

        result = system.get_priority_machine().delete_priority(high)
        self.assertFalse(result)

    def test_lock_entities_property(self) -> None:
        data = {
            "states": ["open"],
            "options": {"lock_entities": True},
        }
        system = self._init_system(data)
        self.assertTrue(system.lock_entities)

        system.set_config("lock_entities", 0)
        self.assertFalse(system.lock_entities)

    def test_require_operator_property(self) -> None:
        data = {
            "states": ["open"],
            "options": {"require_operator": True},
        }
        system = self._init_system(data)
        self.assertTrue(system.require_operator)

        system.set_config("require_operator", 0)
        self.assertFalse(system.require_operator)

    def test_create_ticket_requires_operator_when_enabled(self) -> None:
        data = {
            "states": ["open"],
            "options": {"require_operator": True},
        }
        system = self._init_system(data)

        with self.assertRaisesRegex(
            ValueError,
            "Operator is required for operation: create_ticket",
        ):
            system.create_ticket("Needs operator")

    def test_create_ticket_with_unknown_operator_slug_fails(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)

        with self.assertRaisesRegex(ValueError, "Operator not found: ghost"):
            system.create_ticket("Needs known operator", operator="ghost")

    def test_ticket_mutation_logs_include_operator_slug(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        operator = system.get_entity_by_slug("alice")
        assert operator is not None

        with self.assertLogs("blinkdesk.system", level="INFO") as cm:
            ticket = system.create_ticket("Test", operator=operator.slug)

        logs = system.get_ticket_logs(ticket.id)
        self.assertEqual(logs[0].entity, operator)
        self.assertTrue(any("(alice)" in msg for msg in cm.output))

    def test_add_comment_uses_operator_as_comment_actor(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
            "options": {"require_operator": True},
        }
        system = self._init_system(data)
        operator = system.get_entity_by_slug("alice")
        assert operator is not None

        ticket = system.create_ticket("Test", operator=operator.slug)
        updated = system.add_comment(ticket.id, "hello", operator=operator.slug)
        comments = system.get_ticket_comments(updated.id)

        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].entity, operator)

    def test_add_and_get_comment(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        system.add_comment(ticket.id, "This is a comment", operator=entity.slug)

        comments = system.get_ticket_comments(ticket.id)
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].comment, "This is a comment")
        self.assertEqual(comments[0].entity, entity)

    def test_comment_with_state_transition(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed"],
            "transitions": [
                {"from": "open", "to": "closed"},
            ],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        closed = system.get_state_machine().get_state_by_slug("closed")
        assert closed is not None

        system.add_comment(
            ticket.id,
            "Closing ticket",
            new_state_slug=closed.slug,
            operator=entity.slug,
        )

        comments = system.get_ticket_comments(ticket.id)
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].new_state, closed)

    def test_get_ticket_logs(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open"],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        assert entity is not None

        ticket = system.create_ticket("Test")
        logs = system.get_ticket_logs(ticket.id)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].action.value, "created")

    def test_display_prefix_property(self) -> None:
        data = {
            "states": ["open"],
            "options": {"display_prefix": "#"},
        }
        system = self._init_system(data)
        self.assertEqual(system.display_prefix, "#")

    def test_format_ticket_id(self) -> None:
        data = {
            "states": ["open"],
            "options": {"display_prefix": "#"},
        }
        system = self._init_system(data)
        self.assertEqual(system.format_ticket_id(123), "#123")

    def test_format_ticket_id_no_prefix(self) -> None:
        data = {
            "states": ["open"],
            "options": {"display_prefix": ""},
        }
        system = self._init_system(data)
        self.assertEqual(system.format_ticket_id(123), "123")

    def test_create_ticket_rolls_back_when_log_fails(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)

        with patch.object(system, "_log_ticket", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                system.create_ticket("Will rollback")

        self.assertEqual(system.list_tickets(), [])

    def test_update_ticket_rolls_back_when_log_fails(self) -> None:
        data = {
            "states": ["open"],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Old title")

        with patch.object(system, "_log_ticket", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                system.update_ticket(ticket.id, "New title")

        fetched = system.get_ticket(ticket.id)
        assert fetched is not None
        self.assertEqual(fetched.title, "Old title")

    def test_add_comment_transition_rolls_back_on_failure(self) -> None:
        data = {
            "entities": ["alice"],
            "states": ["open", "closed"],
            "transitions": [
                {"from": "open", "to": "closed"},
            ],
        }
        system = self._init_system(data)
        entity = system.get_entity_by_slug("alice")
        closed = system.get_state_machine().get_state_by_slug("closed")
        assert entity is not None
        assert closed is not None

        ticket = system.create_ticket("Test")
        with patch.object(system, "_log_ticket", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                system.add_comment(
                    ticket.id,
                    "Closing ticket",
                    new_state_slug=closed.slug,
                    operator=entity.slug,
                )

        refreshed = system.get_ticket(ticket.id)
        assert refreshed is not None
        self.assertEqual(refreshed.state.slug, "open")
        self.assertEqual(system.get_ticket_comments(ticket.id), [])

    def test_category_crud_and_ticket_assignment(self) -> None:
        data = {
            "states": ["open"],
            "categories": ["support"],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")

        created = system.create_category("ops")
        self.assertEqual(created.slug, "ops")

        categories = system.list_categories()
        self.assertEqual([c.slug for c in categories], ["support", "ops"])

        support = system.get_category_by_slug("support")
        assert support is not None
        updated = system.set_ticket_category(ticket.id, support.slug)
        assert updated.category is not None
        self.assertEqual(updated.category.slug, "support")

        removed = system.remove_ticket_category(updated.id)
        self.assertIsNone(removed.category)

    def test_set_ticket_category_logs_old_to_new(self) -> None:
        data = {
            "states": ["open"],
            "categories": ["frontend", "backend"],
        }
        system = self._init_system(data)
        ticket = system.create_ticket("Test")
        frontend = system.get_category_by_slug("frontend")
        backend = system.get_category_by_slug("backend")
        assert frontend is not None
        assert backend is not None

        ticket = system.set_ticket_category(ticket.id, frontend.slug)
        ticket = system.set_ticket_category(ticket.id, backend.slug)

        logs = system.get_ticket_logs(ticket.id)
        self.assertTrue(
            any(log.details == "category: (none) => frontend" for log in logs)
        )
        self.assertTrue(
            any(log.details == "category: frontend => backend" for log in logs)
        )

    def test_delete_category_force_clears_tickets_and_logs(self) -> None:
        data = {
            "states": ["open"],
            "categories": ["support"],
        }
        system = self._init_system(data)
        category = system.get_category_by_slug("support")
        assert category is not None
        ticket_a = system.create_ticket("A")
        ticket_b = system.create_ticket("B")
        system.set_ticket_category(ticket_a.id, category.slug)
        system.set_ticket_category(ticket_b.id, category.slug)

        deleted = system.delete_category(category.slug, force=True)
        self.assertTrue(deleted)

        refreshed_a = system.get_ticket(ticket_a.id)
        refreshed_b = system.get_ticket(ticket_b.id)
        assert refreshed_a is not None
        assert refreshed_b is not None
        self.assertIsNone(refreshed_a.category)
        self.assertIsNone(refreshed_b.category)

        logs_a = system.get_ticket_logs(refreshed_a.id)
        logs_b = system.get_ticket_logs(refreshed_b.id)
        self.assertTrue(
            any(
                log.details
                == "category cleared due to forced category deletion: support"
                for log in logs_a
            )
        )
        self.assertTrue(
            any(
                log.details
                == "category cleared due to forced category deletion: support"
                for log in logs_b
            )
        )
