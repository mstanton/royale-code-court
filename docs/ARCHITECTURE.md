# Code Jester Architecture

## Overview

Code Jester is an AI-Assisted Development Intelligence System that implements a multi-agent validation pipeline. The core innovation is the "validate before present" paradigm:

```
Traditional AI: Generate -> Present -> Human Tests -> Human Reports Error -> Generate Again
Code Jester:    Generate -> Test -> Learn -> Improve -> Present Working Code
```

## System Architecture

```
+------------------+     +------------------+     +------------------+
|    AI Client     |     |   Code Jester    |     |   Persistence    |
| (Claude/Cursor)  |<--->|   MCP Server     |<--->|   (SQLite)       |
+------------------+     +------------------+     +------------------+
         |                       |
         |                       v
         |               +------------------+
         |               |   Royal Court    |
         |               |   Orchestrator   |
         |               +------------------+
         |                       |
         v                       v
+------------------+     +------------------+
|   Human User     |<--->|     Agents       |
|                  |     | King | Jester |  |
+------------------+     | Scribe | Guard | |
                         +------------------+
                                 |
                                 v
                         +------------------+
                         |    Executors     |
                         | REPL | Container |
                         +------------------+
```

## Component Details

### 1. MCP Server (`jester/server/mcp.py`)

The Model Context Protocol (MCP) server exposes Code Jester's capabilities to AI clients like Claude Desktop and Cursor.

**Tools Exposed:**
- `execute_code` - Execute Python code in sandbox
- `validate_code` - Full validation pipeline
- `analyze_error` - Error analysis and fix suggestions
- `get_execution_stats` - Execution statistics
- `check_security` - Security vulnerability scanning

**Flow:**
```
AI Client -> MCP Request -> Tool Handler -> Executor/Jester -> Response -> AI Client
```

### 2. Royal Court Orchestrator (`jester/main.py`)

The central orchestrator that coordinates all agents.

**Responsibilities:**
- Initialize and manage agent lifecycle
- Route events between agents
- Handle CLI commands
- Manage event persistence

**Key Classes:**
- `RoyalCourt` - Main orchestrator class
- CLI commands: `validate`, `generate`, `optimize`, `dashboard`, `repl`, `watch`

### 3. Agents (`jester/agents/`)

#### King Agent (`integrations/ollama_client.py`)
- Code generator using local LLM (Ollama)
- Generates code from natural language prompts
- Supports feedback loop for iterative improvement

#### Jester Agent (`agents/jester.py`)
- Core validator and tester
- Multi-stage validation pipeline:
  1. Syntax validation (AST parsing)
  2. Pattern detection
  3. Security analysis
  4. Complexity analysis
  5. Code execution
  6. Test generation

#### Scribe Agent (`agents/scribe.py`)
- Knowledge keeper
- Builds knowledge graph from code
- Provides architectural insights
- Detects patterns and antipatterns

#### Guard Agent (`agents/guard.py`)
- Security enforcement
- Real-time execution monitoring
- Blocks dangerous operations
- Modes: STRICT, PERMISSIVE, REPORT_ONLY

### 4. Execution Tiers (`jester/execution/`)

Code execution uses a tiered approach for safety and performance:

| Tier | Implementation | Speed | Safety | Use Case |
|------|---------------|-------|--------|----------|
| Static | AST Analysis | <5ms | Safest | Syntax, patterns |
| REPL | Subprocess | 10-50ms | Safe | Simple execution |
| Container | Docker/Podman | 50-200ms | Isolated | External deps |

**Tier Selection Logic:**
1. Static analysis first (always)
2. Check for blocked patterns (security)
3. Check for container-required patterns (network, file I/O)
4. Default to REPL for simple code

### 5. Persistence Layer (`jester/persistence/`)

#### LearningStore (`persistence/store.py`)
- SQLite-based execution history
- Code entity tracking (functions, classes)
- Pattern success/failure statistics
- Error pattern analysis
- Training data export

#### PatternExtractor (`persistence/patterns.py`)
- Structural pattern extraction (AST-based)
- Idiom detection (regex-based)
- Design pattern heuristics
- Pattern comparison for code evolution

### 6. Core Components (`jester/core/`)

#### Event System (`core/event_stream.py`)
- Async event bus for agent communication
- Event types for all system activities
- Cross-process event sharing via SQLite

#### Models (`core/models.py`)
- Data classes for all system entities
- `Event`, `ValidationResult`, `ExecutionResult`
- Agent types, event types, severity levels

#### Metrics (`core/metrics.py`)
- Execution metrics collection
- Pattern statistics
- Performance tracking

## Data Flow

### Validation Flow

```
1. Code Input (CLI/MCP/Event)
          |
          v
2. Jester.validate()
          |
          v
3. Syntax Check (AST)
          |
          v
4. Pattern Detection
          |
          v
5. Security Analysis
          |
          v
6. Complexity Calculation
          |
          v
7. Tier Selection
          |
          v
8. Execution (REPL/Container)
          |
          v
9. Result Aggregation
          |
          v
10. Event Emission
          |
          v
11. Persistence (Learning Store)
          |
          v
12. Response to Client
```

### Event Flow

```
Agent A -> EventBus.emit(Event) -> All Subscribers -> Agent B, C, D...
                     |
                     v
              MetricsCollector
                     |
                     v
                 SQLite DB
```

## Security Model

### Execution Sandbox

1. **Pattern-Based Blocking**
   - `eval(input())`, `exec()` with user input
   - `os.system()` with dynamic commands
   - Direct shell access patterns

2. **Module Restrictions (REPL)**
   - Allowed: math, json, collections, datetime, etc.
   - Blocked: os, subprocess, socket, etc.

3. **Container Isolation**
   - Network disabled
   - Filesystem limited to temp
   - Resource limits (CPU, memory)

### Guard Agent Modes

| Mode | Behavior |
|------|----------|
| STRICT | Block immediately on threat |
| PERMISSIVE | Warn but continue |
| REPORT_ONLY | Log threats, no blocking |

## Extension Points

### Adding New Tools (MCP)

```python
# In jester/server/mcp.py
@server.list_tools()
async def list_tools():
    return [
        Tool(name="my_new_tool", ...),
        # existing tools...
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "my_new_tool":
        return await _handle_my_new_tool(arguments)
```

### Adding New Patterns

```python
# In jester/agents/jester.py
PATTERN_DETECTORS = {
    "my_pattern": r'regex_here',
    # existing patterns...
}
```

### Adding New Execution Tier

1. Create executor in `jester/execution/`
2. Add tier to `ExecutionTier` enum
3. Update tier selection logic in `CodeExecutor`

## Performance Considerations

### Caching

- Code hash-based execution caching
- Similar code lookup for pattern reuse
- In-memory metrics buffer

### Async Design

- All I/O operations are async
- Event bus supports concurrent handlers
- Subprocess execution with timeout

### Database Optimization

- Indexed queries for common patterns
- Separate tables for hot/cold data
- Configurable cleanup policy

## Configuration

### Environment Variables

```bash
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b
ENABLE_SCRIBE=true
```

### Config File (`jester.toml`)

```toml
[jester]
model = "gemma3:4b"
warrior_provider = "open-code"

[[jester.realms]]
name = "Backend"
path = "/path/to/backend"
```

## Deployment Modes

1. **CLI Mode** - Direct command execution
2. **REPL Mode** - Interactive validation
3. **Dashboard Mode** - Real-time monitoring
4. **MCP Mode** - AI client integration
5. **Watch Mode** - Multi-realm file monitoring
