# Changelog

All notable changes to this project will be documented in this file.

The project follows [Semantic Versioning 2.0.0](https://semver.org/).

> **BC BREAK** marks backward-incompatible changes. These require a fresh database or manual migration. Review carefully before updating.

## [0.4.0] - 2026-04-02

### Added

- Add `--name` / `-n` flag to `bd mcp` subcommands to customize the MCP server name (default: "BlinkDesk")

## [Unreleased]

### Added

- Database migration system for schema version management
- TOML schema now supports priorities configuration (adds `priorities` option)

### Fixed

- `default_priority` now properly stored in config table (moved to `[options]` section)

### Changed

- **BC BREAK** Simplified schema: entities and states now use slug-only identifiers (no separate "name" field)
- **BC BREAK** TOML schema format simplified: `entities = ["john", "agent-1"]` instead of table-of-tables
- **BC BREAK** Removed `--slug` CLI flag (slugs are now used everywhere)

## [0.3.0] - 2026-04-02

### Added

- `bd ticket get` now shows logs and comments by default. Use `--no-logs` / `-L` and `--no-comments` / `-C` to hide them.

### Fixed

- Ticket ID display prefix is now applied exactly once in CLI table output and is now respected by MCP "ticket not found" errors

## [0.2.1] - 2026-04-01

### Fixed

- `seed_db` now correctly handles TOML list format (`[[entities]]`, `[[states]]`, `[[transitions]]`) in schema files

### Changed

- Move OPTIONS section to beginning of example schema file for better readability

## [0.2.0] - 2026-04-01

### Fixed

- `bd init` now correctly parses TOML list format (`[[entities]]`, `[[states]]`, `[[transitions]]`) in schema files

### Added

- CLI commands `entity list` and `state list`
- Filter options (`-s/--state`, `-a/--assignee`) for `ticket list` command
- `--slug` option to `ticket list` and `ticket get` to show slug instead of name in table output (JSON always includes both)
- MCP server support with FastMCP
- New CLI commands: `bd mcp stdio`, `bd mcp streamable-http`, `bd mcp sse`
- Improved MCP tools with better descriptions and LLM-optimized naming
- Database option commands for auto vacuum mode: `bd db get vacuum_mode` and `bd db set vacuum_mode <none|full|incremental>`
- Database option commands for journal mode: `bd db get journal_mode` and `bd db set journal_mode <delete|truncate|persist|memory|wal|off>`
- New databases default to SQLite `auto_vacuum = INCREMENTAL`
- `TicketingSystem.close()` now runs `PRAGMA main.incremental_vacuum` with 1% probability when auto vacuum mode is incremental

## [0.1.0] - Unreleased

- Initial release with core ticketing features (tickets, entities, comments, audit log)
- SQLite database with no external dependencies
- CLI with subcommands (ticket, config, db, init)
