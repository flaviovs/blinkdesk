"""Command-line interface for Blink Desk."""

import argparse
import logging

from .config import (
    cmd_config_get,
    cmd_config_list,
    cmd_config_set,
)
from .db import cmd_db_backup, cmd_db_vacuum, cmd_init
from .mcp import add_mcp_subparser
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
    lst.set_defaults(func=cmd_ticket_list)

    # ticket get
    get = p_create_sub.add_parser("get", help="Get a ticket")
    get.add_argument("ticket_id", type=int, help="Ticket ID")
    get.add_argument(
        "-f", "--output-format", choices=["json", "table"], default="table"
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

    # init
    p_init = subparsers.add_parser("init", help="Initialize a new database")
    p_init.add_argument("config_path", help="Path to TOML config file")
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
