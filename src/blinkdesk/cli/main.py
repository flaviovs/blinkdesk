"""Command-line interface for BlinkDesk."""

import argparse
import logging
import sys

from .config import (
    cmd_config_get,
    cmd_config_list,
    cmd_config_set,
)
from .db import (
    cmd_db_backup,
    cmd_db_get_journal_mode,
    cmd_db_get_vacuum_mode,
    cmd_db_set_journal_mode,
    cmd_db_set_vacuum_mode,
    cmd_db_vacuum,
    cmd_init,
)
from .entity import cmd_entity_add, cmd_entity_delete, cmd_entity_list
from .mcp import add_mcp_subparser
from .priority import (
    cmd_priority_add,
    cmd_priority_delete,
    cmd_priority_list,
    cmd_priority_rename,
)
from .state import (
    cmd_state_add,
    cmd_state_delete,
    cmd_state_list,
    cmd_state_transition_add,
    cmd_state_transition_delete,
    cmd_state_transition_list,
)
from .ticket import (
    cmd_ticket_assign,
    cmd_ticket_comment,
    cmd_ticket_create,
    cmd_ticket_get,
    cmd_ticket_list,
    cmd_ticket_set_priority,
    cmd_ticket_transition,
    cmd_ticket_unassign,
    cmd_ticket_update,
)


def _parse_ticket_description(value: str) -> str:
    """Parse ticket description from inline text, file, or stdin.

    Args:
        value: Description argument value.

    Returns:
        The resolved description text.

    Raises:
        argparse.ArgumentTypeError: If the referenced file cannot be read.
    """
    if value == "-":
        return sys.stdin.read()

    if value.startswith("@"):
        file_path = value[1:]
        if not file_path:
            raise argparse.ArgumentTypeError(
                "description file path cannot be empty after '@'"
            )
        try:
            with open(file_path, "r", encoding="utf-8") as file_obj:
                return file_obj.read()
        except OSError as exc:
            raise argparse.ArgumentTypeError(
                f"cannot read description file '{file_path}': {exc}"
            ) from exc

    return value


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(prog="bd", description="BlinkDesk CLI")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose (INFO) logging",
    )
    parser.add_argument(
        "-d",
        "--database-path",
        help="Path to database (or use BLINKDESK_DATABASE env var)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ticket create
    p_create = subparsers.add_parser("ticket", help="Ticket operations")
    p_create_sub = p_create.add_subparsers(dest="ticket_command", required=True)

    create = p_create_sub.add_parser("create", help="Create a ticket")
    create.add_argument("-t", "--title", required=True, help="Ticket title")
    create.add_argument(
        "-m",
        "--description",
        type=_parse_ticket_description,
        help="Ticket description text, @file, or - for stdin",
    )
    create.add_argument(
        "-p", "--priority", default="normal", help="Priority slug (default: normal)"
    )
    create.set_defaults(func=cmd_ticket_create)

    # ticket update
    update = p_create_sub.add_parser("update", help="Update a ticket")
    update.add_argument("ticket_id", type=int, help="Ticket ID")
    update.add_argument("-t", "--title", required=True, help="New ticket title")
    update.set_defaults(func=cmd_ticket_update)

    # ticket list
    lst = p_create_sub.add_parser("list", help="List tickets")
    lst.add_argument(
        "-f", "--output-format", choices=["json", "table"], default="table"
    )
    lst.add_argument("-s", "--state", help="Filter by state slug (e.g., open, closed)")
    lst.add_argument("-a", "--assignee", help="Filter by assignee slug")
    lst.add_argument("-p", "--priority", help="Filter by priority slug")
    lst.set_defaults(func=cmd_ticket_list)

    # ticket get
    get = p_create_sub.add_parser("get", help="Get a ticket")
    get.add_argument("ticket_id", type=int, help="Ticket ID")
    get.add_argument(
        "-f", "--output-format", choices=["json", "table"], default="table"
    )
    get.add_argument(
        "-L", "--no-logs", action="store_true", help="Don't show ticket logs"
    )
    get.add_argument(
        "-C", "--no-comments", action="store_true", help="Don't show ticket comments"
    )
    get.set_defaults(func=cmd_ticket_get)

    # ticket comment
    comment = p_create_sub.add_parser("comment", help="Add a comment")
    comment.add_argument("ticket_id", type=int, help="Ticket ID")
    comment.add_argument(
        "-e", "--entity", required=True, help="Entity (user) adding the comment"
    )
    comment.add_argument("-c", "--comment", required=True, help="Comment text")
    comment.add_argument(
        "-s",
        "--state",
        help="Optional state slug to transition ticket while commenting",
    )
    comment.set_defaults(func=cmd_ticket_comment)

    # ticket assign
    assign = p_create_sub.add_parser("assign", help="Assign a ticket")
    assign.add_argument("ticket_id", type=int, help="Ticket ID")
    assign.add_argument("-a", "--assignee", required=True, help="Assignee entity slug")
    assign.set_defaults(func=cmd_ticket_assign)

    # ticket unassign
    unassign = p_create_sub.add_parser("unassign", help="Unassign a ticket")
    unassign.add_argument("ticket_id", type=int, help="Ticket ID")
    unassign.set_defaults(func=cmd_ticket_unassign)

    # ticket transition
    transition = p_create_sub.add_parser("transition", help="Transition ticket state")
    transition.add_argument("ticket_id", type=int, help="Ticket ID")
    transition.add_argument("-s", "--state", required=True, help="Target state slug")
    transition.set_defaults(func=cmd_ticket_transition)

    # ticket set-priority
    set_priority = p_create_sub.add_parser("set-priority", help="Set ticket priority")
    set_priority.add_argument("ticket_id", type=int, help="Ticket ID")
    set_priority.add_argument("-p", "--priority", required=True, help="Priority slug")
    set_priority.set_defaults(func=cmd_ticket_set_priority)

    # db vacuum
    p_db = subparsers.add_parser("db", help="Database operations")
    p_db_sub = p_db.add_subparsers(dest="db_command", required=True)

    vacuum = p_db_sub.add_parser("vacuum", help="Run VACUUM")
    vacuum.set_defaults(func=cmd_db_vacuum)

    backup = p_db_sub.add_parser("backup", help="Backup database")
    backup.add_argument("output_path", help="Output file path")
    backup.set_defaults(func=cmd_db_backup)

    db_get = p_db_sub.add_parser("get", help="Get database option")
    db_get_sub = db_get.add_subparsers(dest="db_get_key", required=True)
    db_get_vacuum_mode = db_get_sub.add_parser(
        "vacuum_mode",
        help="Get auto vacuum mode",
    )
    db_get_vacuum_mode.set_defaults(func=cmd_db_get_vacuum_mode)

    db_get_journal_mode = db_get_sub.add_parser(
        "journal_mode",
        help="Get journal mode",
    )
    db_get_journal_mode.set_defaults(func=cmd_db_get_journal_mode)

    db_set = p_db_sub.add_parser("set", help="Set database option")
    db_set_sub = db_set.add_subparsers(dest="db_set_key", required=True)
    db_set_vacuum_mode = db_set_sub.add_parser(
        "vacuum_mode",
        help="Set auto vacuum mode",
    )
    db_set_vacuum_mode.add_argument(
        "mode",
        choices=["none", "full", "incremental"],
        help="Auto vacuum mode",
    )
    db_set_vacuum_mode.set_defaults(func=cmd_db_set_vacuum_mode)

    db_set_journal_mode = db_set_sub.add_parser(
        "journal_mode",
        help="Set journal mode",
    )
    db_set_journal_mode.add_argument(
        "mode",
        choices=["delete", "truncate", "persist", "memory", "wal", "off"],
        help="SQLite journal mode",
    )
    db_set_journal_mode.set_defaults(func=cmd_db_set_journal_mode)

    # init
    p_init = subparsers.add_parser("init", help="Initialize a new database")
    p_init.add_argument("config_path", help="Path to TOML schema file")
    p_init.set_defaults(func=cmd_init)

    # config
    p_config = subparsers.add_parser("config", help="Manage config")
    p_config_sub = p_config.add_subparsers(dest="config_command", required=True)

    config_get = p_config_sub.add_parser("get", help="Get a config value")
    config_get.add_argument("key", help="Config key")
    config_get.set_defaults(func=cmd_config_get)

    config_set = p_config_sub.add_parser("set", help="Set a config value")
    config_set.add_argument("key", help="Config key")
    config_set.add_argument("value", help="Config value")
    config_set.set_defaults(func=cmd_config_set)

    config_list = p_config_sub.add_parser("list", help="List all config values")
    config_list.set_defaults(func=cmd_config_list)

    # entity
    p_entity = subparsers.add_parser("entity", help="Entity operations")
    p_entity_sub = p_entity.add_subparsers(dest="entity_command", required=True)

    entity_list = p_entity_sub.add_parser("list", help="List all entities")
    entity_list.set_defaults(func=cmd_entity_list)

    entity_add = p_entity_sub.add_parser("add", help="Add an entity")
    entity_add.add_argument("slug", help="Entity slug")
    entity_add.set_defaults(func=cmd_entity_add)

    entity_delete = p_entity_sub.add_parser("delete", help="Delete an entity")
    entity_delete.add_argument("entity_id", type=int, help="Entity ID")
    entity_delete.set_defaults(func=cmd_entity_delete)

    # state
    p_state = subparsers.add_parser("state", help="State operations")
    p_state_sub = p_state.add_subparsers(dest="state_command", required=True)

    state_list = p_state_sub.add_parser("list", help="List all states")
    state_list.set_defaults(func=cmd_state_list)

    state_add = p_state_sub.add_parser("add", help="Add a state")
    state_add.add_argument("slug", help="State slug")
    state_add.set_defaults(func=cmd_state_add)

    state_delete = p_state_sub.add_parser("delete", help="Delete a state")
    state_delete.add_argument("slug", help="State slug")
    state_delete.set_defaults(func=cmd_state_delete)

    state_trans = p_state_sub.add_parser(
        "transition", help="State transition operations"
    )
    p_state_trans = state_trans.add_subparsers(
        dest="state_transition_command", required=True
    )

    state_trans_list = p_state_trans.add_parser("list", help="List all transitions")
    state_trans_list.set_defaults(func=cmd_state_transition_list)

    state_trans_add = p_state_trans.add_parser("add", help="Add a transition")
    state_trans_add.add_argument("from_slug", help="From state slug")
    state_trans_add.add_argument("to_slug", help="To state slug")
    state_trans_add.set_defaults(func=cmd_state_transition_add)

    state_trans_delete = p_state_trans.add_parser("delete", help="Delete a transition")
    state_trans_delete.add_argument("from_slug", help="From state slug")
    state_trans_delete.add_argument("to_slug", help="To state slug")
    state_trans_delete.set_defaults(func=cmd_state_transition_delete)

    # priority
    p_priority = subparsers.add_parser("priority", help="Priority operations")
    p_priority_sub = p_priority.add_subparsers(dest="priority_command", required=True)

    priority_list = p_priority_sub.add_parser("list", help="List all priorities")
    priority_list.set_defaults(func=cmd_priority_list)

    priority_add = p_priority_sub.add_parser("add", help="Add a priority")
    priority_add.add_argument("slug", help="Priority slug")
    priority_add.add_argument(
        "position", help="Priority position (lower = higher priority)", type=int
    )
    priority_add.set_defaults(func=cmd_priority_add)

    priority_delete = p_priority_sub.add_parser("delete", help="Delete a priority")
    priority_delete.add_argument("slug", help="Priority slug")
    priority_delete.set_defaults(func=cmd_priority_delete)

    priority_rename = p_priority_sub.add_parser("rename", help="Rename a priority")
    priority_rename.add_argument("old_slug", help="Current priority slug")
    priority_rename.add_argument("new_slug", help="New priority slug")
    priority_rename.add_argument(
        "-p", "--position", help="New priority position", type=int, default=None
    )
    priority_rename.set_defaults(func=cmd_priority_rename)

    # mcp
    add_mcp_subparser(subparsers)

    args = parser.parse_args()

    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(name)s: %(message)s",
    )

    try:
        args.func(args)
    except ValueError as e:
        parser.error(str(e))


if __name__ == "__main__":
    main()
