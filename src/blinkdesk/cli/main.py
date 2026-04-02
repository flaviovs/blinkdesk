"""Command-line interface for Blink Desk."""

import argparse
import logging

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
from .entity import cmd_entity_list
from .mcp import add_mcp_subparser
from .state import cmd_state_list
from .ticket import (
    cmd_ticket_comment,
    cmd_ticket_create,
    cmd_ticket_get,
    cmd_ticket_list,
    cmd_ticket_update,
)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(prog="bd", description="Blink Desk CLI")
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
    create.add_argument("--title", required=True, help="Ticket title")
    create.add_argument("--description", help="Ticket description")
    create.set_defaults(func=cmd_ticket_create)

    # ticket update
    update = p_create_sub.add_parser("update", help="Update a ticket")
    update.add_argument("ticket_id", type=int, help="Ticket ID")
    update.add_argument("--title", required=True, help="New ticket title")
    update.set_defaults(func=cmd_ticket_update)

    # ticket list
    lst = p_create_sub.add_parser("list", help="List tickets")
    lst.add_argument(
        "-f", "--output-format", choices=["json", "table"], default="table"
    )
    lst.add_argument("-s", "--state", help="Filter by state slug (e.g., open, closed)")
    lst.add_argument("-a", "--assignee", help="Filter by assignee slug")
    lst.add_argument(
        "--slug", action="store_true", help="Show slug instead of name in table output"
    )
    lst.set_defaults(func=cmd_ticket_list)

    # ticket get
    get = p_create_sub.add_parser("get", help="Get a ticket")
    get.add_argument("ticket_id", type=int, help="Ticket ID")
    get.add_argument(
        "-f", "--output-format", choices=["json", "table"], default="table"
    )
    get.add_argument(
        "--slug", action="store_true", help="Show slug instead of name in table output"
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
        "--entity", required=True, help="Entity (user) adding the comment"
    )
    comment.add_argument("--comment", required=True, help="Comment text")
    comment.set_defaults(func=cmd_ticket_comment)

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

    # state
    p_state = subparsers.add_parser("state", help="State operations")
    p_state_sub = p_state.add_subparsers(dest="state_command", required=True)

    state_list = p_state_sub.add_parser("list", help="List all states")
    state_list.set_defaults(func=cmd_state_list)

    # mcp
    add_mcp_subparser(subparsers)

    args = parser.parse_args()

    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(name)s: %(message)s",
    )

    args.func(args)


if __name__ == "__main__":
    main()
