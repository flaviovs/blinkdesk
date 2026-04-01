"""CLI commands for MCP server."""

import argparse
import os
import sys


def _check_mcp_installed() -> None:
    """Check if MCP package is installed."""
    try:
        import mcp  # noqa: F401
    except ImportError:
        print(
            "Error: MCP support not installed. Run: pip install blinkdesk[mcp]",
            file=sys.stderr,
        )
        sys.exit(1)


def _get_database_path(args: argparse.Namespace) -> str:
    """Get database path from args or environment."""
    db_path: str | None = args.database_path
    if db_path:
        return db_path
    env_path = os.environ.get("BLINKDESK_DATABASE")
    if env_path:
        return env_path
    raise ValueError(
        "Database path required: use --database-path or BLINKDESK_DATABASE"
    )


def cmd_mcp_stdio(args: argparse.Namespace) -> None:
    """Run MCP server with stdio transport."""
    _check_mcp_installed()
    database_path = _get_database_path(args)

    from blinkdesk._mcp import create_mcp_server

    mcp = create_mcp_server(database_path)
    mcp.run(transport="stdio")


def cmd_mcp_streamable_http(args: argparse.Namespace) -> None:
    """Run MCP server with streamable-http transport."""
    _check_mcp_installed()
    database_path = _get_database_path(args)

    from blinkdesk._mcp import create_mcp_server

    mcp = create_mcp_server(database_path)
    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport="streamable-http")


def cmd_mcp_sse(args: argparse.Namespace) -> None:
    """Run MCP server with SSE transport."""
    _check_mcp_installed()
    database_path = _get_database_path(args)

    from blinkdesk._mcp import create_mcp_server

    mcp = create_mcp_server(database_path)
    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport="sse")


def add_mcp_subparser(subparsers) -> None:  # type: ignore[no-untyped-def]
    """Add MCP subcommand to CLI."""
    p_mcp = subparsers.add_parser("mcp", help="MCP server commands")

    p_mcp_sub = p_mcp.add_subparsers(dest="mcp_command", required=True)

    p_stdio = p_mcp_sub.add_parser(
        "stdio", help="Start MCP server with stdio transport"
    )
    p_stdio.set_defaults(func=cmd_mcp_stdio)

    p_streamable = p_mcp_sub.add_parser(
        "streamable-http", help="Start MCP server with streamable-http transport"
    )
    p_streamable.add_argument(
        "--host", default="localhost", help="HTTP host (default: localhost)"
    )
    p_streamable.add_argument(
        "--port", type=int, default=8000, help="HTTP port (default: 8000)"
    )
    p_streamable.set_defaults(func=cmd_mcp_streamable_http)

    p_sse = p_mcp_sub.add_parser("sse", help="Start MCP server with SSE transport")
    p_sse.add_argument(
        "--host", default="localhost", help="HTTP host (default: localhost)"
    )
    p_sse.add_argument(
        "--port", type=int, default=8000, help="HTTP port (default: 8000)"
    )
    p_sse.set_defaults(func=cmd_mcp_sse)
