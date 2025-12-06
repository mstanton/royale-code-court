# Changelog

All notable changes to Royale Code Court (Code Jester) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2025-12-06

### Added
- **MCP Server** (`jester/server/mcp.py`) - Model Context Protocol server for Claude Desktop and Cursor integration
  - `execute_code` tool - Execute Python in secure sandbox
  - `validate_code` tool - Full validation pipeline
  - `analyze_error` tool - Error analysis with fix suggestions
  - `check_security` tool - Security vulnerability scanning
  - `get_execution_stats` tool - Execution statistics and patterns
- **Learning Store** (`jester/persistence/store.py`) - Persistent SQLite storage for execution history
  - Code hash-based deduplication
  - Pattern extraction from successful executions
  - Error pattern tracking
  - Training data export for fine-tuning
- **Pattern Extractor** (`jester/persistence/patterns.py`) - Extract patterns from code
  - Structural patterns (functions, classes, decorators)
  - Idiom patterns (comprehensions, context managers)
  - Design pattern detection (singleton, factory, etc.)
- **Claude Desktop Integration** - Configuration and documentation for Claude Desktop
- **Comprehensive Test Suite** - Tests for executor, MCP server, and persistence

### Changed
- Renamed project from "code-jester" to "royale-code-court"
- Updated project structure with new `server/` and `persistence/` directories
- Updated pyproject.toml with MCP optional dependency
- Enhanced README with MCP integration documentation
- Added ARCHITECTURE.md and API.md documentation

### Fixed
- Package structure for proper imports

## [0.4.0] - 2025-12-XX

### Added
- Guard Agent for real-time execution monitoring
- Execution tracing for security enforcement
- Remote tracer for subprocess monitoring
- Performance optimization loop (`jester optimize`)
- Multi-realm watcher with file monitoring
- Open Code integration as alternative to Claude Code

### Changed
- Tiered execution with Static, REPL, and Container tiers
- Enhanced pattern detection with more categories
- Improved security scanning

## [0.3.0] - 2025-XX-XX

### Added
- SQLite-backed metrics collection
- Event persistence for cross-process visibility
- Terminal dashboard with real-time updates
- Knowledge graph integration via NetworkX

## [0.2.0] - 2025-XX-XX

### Added
- Scribe Agent for pattern recognition
- Knowledge graph building
- Architectural insights generation
- Multi-agent event system

## [0.1.0] - 2025-XX-XX

### Initial Release
- Jester Agent for code validation
- King Agent with Ollama integration
- Basic code execution sandbox
- CLI commands: validate, generate, repl, demo
- WebSocket server foundation
- RestrictedPython sandboxing

---

## Version History Summary

| Version | Highlights |
|---------|------------|
| 0.5.0 | MCP server, persistent learning, Claude Desktop integration |
| 0.4.0 | Guard agent, execution tracing, optimization loop |
| 0.3.0 | Metrics persistence, dashboard, knowledge graph |
| 0.2.0 | Scribe agent, multi-agent architecture |
| 0.1.0 | Initial release with core validation |
