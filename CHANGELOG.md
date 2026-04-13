# Changelog

All notable changes to this project will be documented in this file.

The project follows [Semantic Versioning 2.0.0](https://semver.org/).

> **BC BREAK** marks backward-incompatible changes. These require a fresh database or manual migration. Review carefully before updating.

## [Unreleased]

### Added

- Add grouped ticket counts by assignee entity with optional state filter across Python API (`list_ticket_counts_by_entity`), CLI (`bd ticket count-by-entity`), and MCP (`count_tickets_by_entity`)
- Add category-on-create support for tickets in CLI (`bd ticket create -c/--category`) and MCP (`create_ticket(category=...)`) to match the existing Python API (`category_slug`)

### Removed

- **BC BREAK** Remove `add_category` and `delete_category` MCP tools (use schema init to create categories)

## [0.8.0] - 2026-04-07

### Added

- `bd ticket create -m/--description` now accepts `@<path>` to read the description from a file and `-` to read it from stdin
- Add optional ticket categories (`schema.categories`) across Python API, CLI, and MCP, including ticket set/remove operations plus `bd category delete --force` with per-ticket log entries when categories are cleared
- Ticket mutation operations now accept an optional operator entity (`-o/--operator` in CLI and `operator` in MCP/Python API), record that operator in ticket logs and library logs, and support `config require_operator` to enforce operator presence
- Ticket listing now supports cursor pagination with `after_id` and `limit` across Python API, CLI (`bd ticket list --after-id --limit`), and MCP (`find_tickets`)
- Add persistent audit logging (`config audit_log`) plus `bd audit list` and `bd audit prune`, with retention controlled by `config audit_prune_keep_days` (default: 30)
- Ticket listing now supports category filtering across Python API (`category_slug`), CLI (`-c/--category`), and MCP (`category`) alongside state/assignee/priority filters

### Changed

- **BC BREAK** `TicketingSystem` now validates referenced records during method execution and mutation/list APIs now accept IDs/slugs (for example `ticket_id`, `state_slug`, `assignee_slug`) instead of pre-resolved object instances
- **BC BREAK** MCP and CLI JSON ticket comment/history payloads now use `operator` for actor fields (replacing `author`/`entity`)
- Boolean config keys now persist as SQLite numeric booleans (`0`/`1`) while CLI output remains `true`/`false`

## [0.7.0] - 2026-04-04

### Added

- CLI commands `bd ticket assign <ticket_id> -a/--assignee`, `bd ticket unassign <ticket_id>`, `bd ticket transition <ticket_id> -s/--state`, and `bd ticket set-priority <ticket_id> -p/--priority`

### Changed

- `bd ticket comment` now supports `-s/--state` to transition a ticket while adding a comment
- Touched ticket subcommands now provide consistent short options (`-t/--title`, `-m/--description`, `-p/--priority`, `-e/--entity`, `-c/--comment`)
- Standardize remaining CLI flags with short/long pairs: `ticket update -t/--title`, `priority rename -p/--position`, and MCP transport networking options `-H/--host`, `-P/--port`

## [0.6.0] - 2026-04-04

### Changed

- **BC BREAK** TOML workflow definition keys now live under `[schema]` (`entities`, `states`, `priorities`, `transitions`) while runtime settings remain under `[options]`

## [0.5.0] - 2026-04-03

### Fixed

- Fix example.schema.toml parsing issue where all keys were incorrectly placed under `[options]` section
- Make Python API write operations atomic by using single-transaction boundaries for ticket/system updates, seeding, and migration steps
- Deleting entities, priorities, and states now reports a friendly "cannot delete" failure when rows are still referenced by tickets/comments
- `default_priority` now properly stored in config table (moved to `[options]` section)
- CLI now shows friendly error message when no database is specified (instead of stack trace)
- `bd config set` now validates that `default_priority` value is a valid priority slug

### Added

- Database migration system for schema version management
- TOML schema now supports priorities configuration (adds `priorities` option)
- Priority ordering via explicit positions: `bd priority add <slug> <position>`
- `bd priority rename` now supports `--position` to change priority order
- MCP `list_ticket_priorities` now returns ordered list of priority slugs
- CLI commands `bd entity add <slug>` and `bd entity delete <entity_id>`
- CLI commands to manage states: `bd state add`, `bd state delete`
- CLI commands to manage state transitions: `bd state transition list`, `bd state transition add`, `bd state transition delete`

### Changed

- MCP `find_tickets` tool now exposes `order` parameter as enum (discoverable by AI agents)
- Core library mutation and lifecycle operations now emit `logger.info` entries for better observability
- **BC BREAK** `update_ticket()` API no longer accepts description parameter (only title can be updated)
- **BC BREAK** Simplified schema: entities and states now use slug-only identifiers (no separate "name" field)
- **BC BREAK** TOML schema format simplified: `entities = ["john", "agent-1"]` instead of table-of-tables
- **BC BREAK** Removed `--slug` CLI flag (slugs are now used everywhere)

## [0.4.0] - 2026-04-02

### Added

- Add `--name` / `-n` flag to `bd mcp` subcommands to customize the MCP server name (default: "BlinkDesk")

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
