# Changelog

All notable changes to this project will be documented in this file.

The project follows [Semantic Versioning 2.0.0](https://semver.org/).

## [0.2.0] - Unreleased

### Added

- CLI commands `entity list` and `state list`
- Filter options (`-s/--state`, `-a/--assignee`) for `ticket list` command
- MCP server support with FastMCP
- New CLI commands: `bd mcp stdio`, `bd mcp streamable-http`, `bd mcp sse`
- MCP tools: ticket_list, ticket_get, ticket_create, ticket_update, ticket_comment_add, entity_list, entity_get
- Database option commands for auto vacuum mode: `bd db get vacuum_mode` and `bd db set vacuum_mode <none|full|incremental>`
- New databases default to SQLite `auto_vacuum = INCREMENTAL`
- `TicketingSystem.close()` now runs `PRAGMA incremental_vacuum` with 1% probability when auto vacuum mode is incremental
- Database option commands for journal mode: `bd db get journal_mode` and `bd db set journal_mode <delete|truncate|persist|memory|wal|off>`

## [0.1.0] - Unreleased

- Initial release with core ticketing features (tickets, entities, comments, audit log)
- SQLite database with no external dependencies
- CLI with subcommands (ticket, config, db, init)
