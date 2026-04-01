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

## [0.1.0] - Unreleased

- Initial release with core ticketing features (tickets, entities, comments, audit log)
- SQLite database with no external dependencies
- CLI with subcommands (ticket, config, db, init)
