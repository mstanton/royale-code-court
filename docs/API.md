# Code Jester API Reference

## MCP Server API

The MCP (Model Context Protocol) server exposes tools for AI clients.

### Tools

#### `execute_code`

Execute Python code in a secure sandbox.

**Input Schema:**
```json
{
  "code": "string (required) - Python code to execute",
  "language": "string (default: 'python')",
  "timeout": "number (default: 5.0) - Timeout in seconds"
}
```

**Response Format:**
```
Success:
- Code executed successfully
- Output: <stdout content>
- Performance metrics (time, tier, memory)
- Status: PASSED

Failure:
- Code execution failed
- Error: <error message>
- Status: FAILED
```

**Example:**
```json
{
  "code": "print(sum(range(10)))"
}
```

---

#### `validate_code`

Perform comprehensive code validation.

**Input Schema:**
```json
{
  "code": "string (required) - Code to validate",
  "language": "string (default: 'python')",
  "generate_tests": "boolean (default: true)"
}
```

**Response Format:**
```
VALIDATION PASSED/FAILED

Syntax valid: Yes/No
Executes: Yes/No
Complexity score: <number>
Execution time: <ms>

Patterns detected: <list>
Issues found: <list>
Suggestions: <list>
Execution output: <content>
```

---

#### `analyze_error`

Analyze an error and suggest fixes.

**Input Schema:**
```json
{
  "code": "string (required) - Code that produced error",
  "error": "string (required) - Error message"
}
```

**Response Format:**
```
Error Analysis

Error type: <type>
Original error: <message>

Likely causes and fixes:
- <suggestion 1>
- <suggestion 2>

Recommended approach:
1. Review the specific line
2. Apply fix
3. Re-execute
```

---

#### `get_execution_stats`

Get execution history statistics.

**Input Schema:**
```json
{}
```

**Response Format:**
```
Execution Statistics

Total executions: <count>
Success rate: <percentage>
Average execution time: <ms>

By execution tier:
- repl: <count>, <avg time>
- container: <count>, <avg time>

Learned patterns:
- <pattern>: <occurrences>, <success rate>
```

---

#### `check_security`

Scan code for security vulnerabilities.

**Input Schema:**
```json
{
  "code": "string (required)"
}
```

**Response Format:**
```
Security Check: PASSED/ISSUES FOUND

[SEVERITY] <issue description>
   Pattern: <pattern name>

Recommendation: <action>
```

---

## Python API

### RoyalCourt

Main orchestrator class.

```python
from jester.main import RoyalCourt

court = RoyalCourt(
    ollama_model="gemma3:4b",      # LLM model for code generation
    ollama_url="http://localhost:11434",
    enable_scribe=True,            # Enable knowledge keeper
    enable_warrior=True,           # Enable code integrator
    working_dir="./working_dir"
)

# Start the court
await court.start(use_dashboard=True)

# Generate and validate code
result = await court.generate_and_validate(
    prompt="write a fibonacci function",
    language="python"
)

# Validate existing code
result = await court.validate_code(code, language="python")

# Get metrics
metrics = court.get_metrics()

# Stop
await court.stop()
```

### JesterAgent

Core validator agent.

```python
from jester.agents.jester import JesterAgent
from jester.core.event_stream import get_event_bus
from jester.execution.executor import CodeExecutor

event_bus = get_event_bus()
executor = CodeExecutor()
jester = JesterAgent(event_bus, executor=executor)
jester.start()

# Validate code
result = await jester.validate(
    code="def add(a, b): return a + b",
    language="python",
    generate_tests=True
)

# Access validation result
print(f"Syntax valid: {result.syntax_valid}")
print(f"Executes: {result.executes}")
print(f"Patterns: {result.patterns_detected}")
print(f"Issues: {result.issues}")

# Format as report
report = jester.format_report(result)
print(report)

jester.stop()
```

### CodeExecutor

Direct code execution.

```python
from jester.execution.executor import CodeExecutor
from jester.core.models import ExecutionTier

executor = CodeExecutor()

# Execute code
result = await executor.execute(
    code="print('Hello, World!')",
    language="python",
    timeout=5.0,
    force_tier=ExecutionTier.REPL  # Optional
)

print(f"Success: {result.success}")
print(f"Output: {result.output}")
print(f"Error: {result.error}")
print(f"Time: {result.execution_time_ms}ms")
print(f"Tier: {result.tier.value}")

# Analyze code without execution
analysis = executor.analyze_code(code)
print(f"Syntax valid: {analysis.syntax_valid}")
print(f"Imports: {analysis.imports}")
print(f"Functions: {analysis.functions}")
print(f"Requires container: {analysis.requires_container}")
```

### LearningStore

Persistent execution history.

```python
from jester.persistence.store import LearningStore

store = LearningStore(db_path="~/.royale-code-court/learning.db")

# Record execution
exec_id = store.record_execution(
    code="def foo(): pass",
    result=validation_result,
    language="python"
)

# Find similar executions
similar = store.get_similar_executions(code, limit=5)

# Get function statistics
stats = store.get_function_stats("fibonacci")

# Get pattern statistics
pattern_stats = store.get_pattern_stats("list_comprehension")

# Get global statistics
global_stats = store.get_global_stats()

# Export training data
count = store.export_training_data("training.jsonl")

# Cleanup old records
removed = store.cleanup_old_records(days=30)
```

### PatternExtractor

Extract patterns from code.

```python
from jester.persistence.patterns import PatternExtractor

extractor = PatternExtractor()

# Extract patterns
patterns = extractor.extract_patterns(code)

for pattern in patterns:
    print(f"{pattern.name}: {pattern.description}")
    print(f"  Type: {pattern.pattern_type}")
    print(f"  Confidence: {pattern.confidence}")
    print(f"  Lines: {pattern.locations}")

# Get summary
summary = extractor.get_pattern_summary(patterns)
print(f"Total patterns: {summary['total']}")
print(f"By type: {summary['by_type']}")

# Compare patterns between versions
comparison = extractor.compare_patterns(old_patterns, new_patterns)
print(f"Added: {comparison['added']}")
print(f"Removed: {comparison['removed']}")
```

---

## CLI Reference

### Commands

```bash
# Validate code
jester validate "def add(a, b): return a + b"
jester validate --file mycode.py
jester validate "code" --lang python --json

# Generate code (requires Ollama)
jester generate "write a prime number checker"
jester generate "prompt" --model gemma3:4b --no-validate

# Optimization loop
jester optimize "calculate fibonacci efficiently" --threshold 100
jester optimize "task" --attempts 5

# Interactive modes
jester repl          # Interactive validation
jester dashboard     # Real-time monitoring

# File watching
jester watch .                      # Watch current directory
jester watch /path/to/project       # Watch specific path
jester watch --config jester.toml   # Use config file

# Demo
jester demo
```

### REPL Commands

```
>>> code here         # Validate code (end with blank line)
>>> :g prompt         # Generate code with prompt
>>> :q                # Quit
```

---

## Data Models

### ValidationResult

```python
@dataclass
class ValidationResult:
    code_id: str
    syntax_valid: bool = False
    executes: bool = False
    execution_result: Optional[ExecutionResult] = None
    tests_generated: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    complexity_score: int = 0
    patterns_detected: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    validation_time_ms: float = 0.0
    execution_stats: Dict[str, Any] = field(default_factory=dict)
    feedback: str = ""

    @property
    def overall_success(self) -> bool:
        return self.syntax_valid and self.executes and len(self.issues) == 0
```

### ExecutionResult

```python
@dataclass
class ExecutionResult:
    success: bool
    output: str = ""
    error: str = ""
    execution_time_ms: float = 0.0
    tier: ExecutionTier = ExecutionTier.REPL
    memory_usage_mb: float = 0.0
    return_value: Any = None
```

### ExecutionTier

```python
class ExecutionTier(str, Enum):
    STATIC = "static"       # AST analysis only
    REPL = "repl"          # Subprocess execution
    CONTAINER = "container" # Docker/Podman isolation
```

### Event

```python
@dataclass
class Event:
    event_type: EventType
    agent: AgentType
    payload: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: str = ""
    parent_event_id: Optional[str] = None
```

---

## Error Codes

| Code | Description |
|------|-------------|
| `SYNTAX_ERROR` | Code has syntax errors |
| `TIMEOUT` | Execution exceeded timeout |
| `BLOCKED` | Code contains blocked patterns |
| `SECURITY_VIOLATION` | Security check failed |
| `EXECUTION_ERROR` | Runtime error during execution |

---

## Rate Limits

The MCP server has no built-in rate limits, but:
- Default timeout: 5 seconds per execution
- Maximum output: 30,000 characters
- Container execution: 50-200ms typical

---

## WebSocket Protocol (Future)

Reserved for future real-time event streaming.

```json
{
  "type": "event",
  "data": {
    "event_type": "code.validated",
    "agent": "jester",
    "payload": {...}
  }
}
```
