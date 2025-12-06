# Code Jester

**AI-Assisted Development Intelligence System**

Code Jester transforms AI code generation from "prompt and hope" into "validate, optimize, and learn." It's a local-first, privacy-preserving system that implements a multi-agent validation pipeline where code is tested, analyzed, and learned from before presentation to developers.

## Key Features

- **Code Validation Before Presentation** - All generated code is tested and validated before you see it
- **Automatic Pattern Learning** - Successful patterns are recognized and reused
- **Multi-Tier Execution** - Safe code execution from static analysis to containerized sandboxes
- **100% Local Computation** - Complete privacy with no external API calls (uses Ollama)
- **Human-in-the-Loop** - Developer maintains strategic control at all decision points
- **Multi-Realm Support** - Monitor and learn from multiple local projects simultaneously
- **Open Code Integration** - Flexible warrior provider support (Claude Code or Open Code)
- **Knowledge Graph Integration** - Architectural insights emerge from execution patterns
- **Performance Optimization Loop** - Iteratively improves code based on runtime metrics (`jester optimize`)

## The Royal Court Architecture

Code Jester uses a royal court metaphor for its multi-agent system:

| Agent | Role | Function |
|-------|------|----------|
| **King** | Code Generator | Local LLM via Ollama generates initial solutions |
| **Jester** | Validator/Tester | Tests code, finds bugs, detects patterns and security issues |
| **Scribe** | Knowledge Keeper | Observes activity, builds knowledge graph, provides insights |
| **Warrior** | Code Integrator | Applies validated changes to codebase via Claude Code or Open Code |
| **Human** | Strategic Director | Provides direction, approves changes, guides learning |

## Requirements

- **Python 3.11+** (3.11 or 3.12 recommended)
- **Ollama** (optional, for code generation) - [Download here](https://ollama.ai)

## Installation

```bash
# Clone repository
git clone https://github.com/your-org/royale-code-court.git
cd royale-code-court

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install with all dependencies
pip install -e ".[dev]"
```

### Setting up Ollama (Optional)

For code generation features:

```bash
# Start Ollama service
ollama serve

# Pull a coding model
ollama pull gemma3:4b
```

## Quick Start

### CLI Commands

```bash
# Validate code directly
jester validate "def add(a, b): return a + b"

# Validate from file
jester validate --file mycode.py

# Generate and validate code (requires Ollama)
jester generate "write a fibonacci function"

# Interactive REPL
jester repl

# Real-time dashboard
jester dashboard

# Multi-Realm Watcher
jester watch /path/to/project

# Optimization Loop
jester optimize "calculate fibonacci efficiently" --threshold 100

# Quick demo
jester demo
```

### Python API

```python
import asyncio
from jester.main import RoyalCourt

async def main():
    court = RoyalCourt()
    await court.start(use_dashboard=False)

    # Generate and validate code
    result = await court.generate_and_validate(
        "write a function to reverse a string",
        language="python"
    )

    print(f"Generated code:\n{result['code']}")
    print(f"Valid: {result['validation'].syntax_valid}")
    print(f"Executes: {result['validation'].executes}")

    await court.stop()

asyncio.run(main())
```

### Standalone Validation

```python
import asyncio
from jester.core.event_stream import get_event_bus
from jester.agents.jester import JesterAgent
from jester.execution.executor import CodeExecutor

async def validate_code():
    event_bus = get_event_bus()
    executor = CodeExecutor()
    jester = JesterAgent(event_bus, executor=executor)
    jester.start()

    code = "def hello(name):\n    return f'Hello, {name}!'"
    result = await jester.validate(code, "python")

    print(f"Syntax valid: {result.syntax_valid}")
    print(f"Executes: {result.executes}")
    print(f"Patterns detected: {result.patterns_detected}")

    jester.stop()

asyncio.run(validate_code())
```

## CLI Reference

| Command | Description | Example |
|---------|-------------|---------|
| `validate` | Validate code syntax and execution | `jester validate "code" --lang python` |
| `generate` | Generate code with LLM and validate | `jester generate "prompt" --model gemma3:4b` |
| `repl` | Interactive validation REPL | `jester repl` |
| `dashboard` | Real-time event stream UI | `jester dashboard` |
| `watch` | Monitor specific path or multiple realms | `jester watch .` |
| `optimize` | Iterative performance optimization | `jester optimize "task"` |
| `demo` | Run demonstration | `jester demo` |

### REPL Commands

- Type code and press Enter twice to validate
- `:g <prompt>` - Generate code with King
- `:q` - Quit REPL

## Configuration

### RoyalCourt Parameters

```python
court = RoyalCourt(
    ollama_model="gemma3:4b",  # LLM model
    ollama_url="http://localhost:11434",  # Ollama URL
    enable_scribe=True,  # Knowledge keeper
    enable_warrior=False,  # Claude Code/Open Code integration
    working_dir=None,  # Working directory
)
```

### Multi-Realm Configuration

Create a `jester.toml` file to configure multiple realms (projects) to watch:

```toml
[jester]
model = "gemma3:4b"
warrior_provider = "open-code" # or "claude-code"

[[jester.realms]]
name = "Backend"
path = "/path/to/backend"

[[jester.realms]]
name = "Frontend"
path = "/path/to/frontend"
```

### Environment Variables

Create a `.env` file in the project root:

```bash
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b
ENABLE_SCRIBE=true
```

## Code Execution Tiers

Code Jester uses tiered execution for safety and performance:

| Tier | Method | Speed | Use Case |
|------|--------|-------|----------|
| **Static** | AST Analysis | <5ms | Syntax, patterns |
| **REPL** | RestrictedPython | 10-50ms | Safe execution |
| **Container** | Docker/Podman | 50-200ms | Full isolation |

## Security Features

- Pattern-based threat detection (SQL injection, command injection, eval attacks)
- RestrictedPython sandboxing for untrusted code
- Container isolation for external dependencies
- Blocked dangerous operations (eval with input, exec, etc.)

## Project Structure

```
royale-code-court/
├── jester/                     # Main package
│   ├── main.py                 # CLI and RoyalCourt orchestrator
│   ├── core/                   # Event system, models, metrics
│   ├── agents/                 # Jester, Scribe agents
│   ├── execution/              # Code executors (REPL, container)
│   ├── integrations/           # Ollama, Claude Code
│   ├── knowledge/              # Knowledge graph
│   └── observability/          # Terminal UI
├── examples/                   # Usage examples
├── tests/                      # Unit tests
├── SPEC_0.0.1.md              # Full specification
└── pyproject.toml             # Project configuration
```

## Development

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=jester --cov-report=html

# Specific test file
pytest tests/test_jester.py -v
```

### Code Quality

```bash
# Format code
black jester/ tests/

# Lint
ruff check jester/ tests/

# Type check
mypy jester/
```

## Technology Stack

- **Python 3.11+** - Core language
- **Typer** - CLI framework
- **Rich** - Terminal UI
- **Pydantic 2.0+** - Data validation
- **NetworkX** - Knowledge graph
- **RestrictedPython** - Safe execution
- **HTTPx** - Async HTTP client
- **Ollama** - Local LLM integration

## Documentation

For detailed architecture and design decisions, see [SPEC_0.0.2.md](SPEC_0.0.2.md).

## License

MIT License

## Contributing

1. Read the [specification](SPEC_0.0.1.md) to understand the architecture
2. Fork the repository
3. Create a feature branch
4. Make your changes with tests
5. Submit a pull request

---

*Code Jester - Because every royal court needs someone to test the king's code.*
