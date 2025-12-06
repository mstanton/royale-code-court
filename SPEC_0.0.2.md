# 📜 Product Requirements Document (PRD)
# Code Jester: AI-Assisted Development Intelligence System

**Version:** 0.0.2
**Date:** December 2025
**Status:** Implemented Specification (Phases 1-4 Complete)
**Project Codename:** The Royal Court

---

## Executive Summary

**Code Jester** is a local-first, privacy-preserving AI development intelligence system. It implements a **multi-agent validation pipeline** that transforms code generation from "prompt and hope" into "validate, optimize, and learn."

The system has evolved to support:
1.  **Multi-Realm Monitoring:** Watching multiple distinct project directories simultaneously.
2.  **Provider Flexibility:** Choosing between Claude Code or Open Code (Ollama-based) for integration.
3.  **Performance Optimization Loops:** Iteratively refining code based on actual runtime metrics.

---

## The Royal Court: Agent Architecture

The system uses a **metaphorical architecture** where different AI agents play specific roles:

### 👑 **The KING (Code Generator)**
- **Technology:** Ollama (local LLM - Qwen2.5-Coder, Gemma, DeepSeek)
- **Role:** Generates initial code solutions and iterates based on feedback.
- **New Capability:** Accepts `feedback_history` to learn from previous failed or slow attempts.

### 🃏 **The JESTER (Validator/Tester)**
- **Technology:** Python-based validation engine.
- **Role:** Tests the King's code, finds bugs, measures performance.
- **Capabilities:**
    - **Syntax Check:** Immediate AST validation.
    - **Execution:** Safe execution in REPL (RestrictedPython) or Container.
    - **Performance Analysis:** Flags code exceeding time thresholds (e.g., >500ms).
    - **Feedback Generation:** Produces specific feedback for the King (e.g., "Execution successful but SLOW").

### 📜 **The SCRIBE (Knowledge Keeper/Observer)**
- **Technology:** SQLite (Events/Metrics) + Future Graph.
- **Role:** Observes all activity across all realms.
- **Capabilities:**
    - **Metric Aggregation:** Tracks churn, complexity, and success rates over time.
    - **Pattern Recognition:** (Planned) Identifies structural patterns.

### ⚔️ **The WARRIOR (Code Integrator)**
- **Technology:** Pluggable Provider (Claude Code or Open Code).
- **Role:** The Sword. Applies validated changes to the filesystem.
- **Configuration:** Selectable via `jester.toml` (`warrior_provider`).

### 🛡️ **The GUARD (Royal Guard)**
- **Technology:** Python `sys.settrace` (Step Debugger).
- **Role:** The Shield / Bumpers.
- **Function:** Provides realtime "defensive" guard rails.
- **Modes:**
    - **Strict (Defensive):** Enforces hard limits (loops, memory, types) from the start.
    - **Learning (Exploratory):** Relaxes rules to allow risky innovation ("higher potential risks").

### 👤 **The HUMAN (Strategic Director)**
- **Technology:** Terminal UI / CLI.
- **Role:** Provides strategic direction and approves critical actions.

---

## System Architecture

### Event Bus & Persistence
All agents communicate via an asynchronous `EventBus`. Events are persisted to an SQLite database for:
- Historical analysis.
- Dashboard visualization (churn, patterns).
- Resuming sessions.

### Multi-Realm Support
The `RealmWatcher` component allows Jester to monitor multiple directories defined in `jester.toml`:
```toml
[[jester.realms]]
name = "Core API"
path = "./backend"

[[jester.realms]]
name = "Web UI"
path = "./frontend"
```

### The Optimization Loop (Phase 4)
A closed-loop system for performance tuning:

1.  **Generate:** King generates code.
2.  **Validate:** Jester executes and measures (e.g., Time: 600ms).
3.  **Evaluate:** If Time > Threshold (500ms):
    *   Construct Feedback: "Too slow (600ms). Target < 500ms."
    *   **Loop:** Feed code + feedback back to King.
4.  **Refine:** King generates v2 using feedback context.
5.  **Success:** When Time < Threshold.

**CLI Command:**
```bash
jester optimize "Calculate Fibonacci sequence" --threshold 100
```

---

### The Squad Workflow (Phase 5)
A stateful orchestration of the code layer:

```
┌─────────────────────────────────────────────────────────────┐
│                       The SQUAD                             │
│                                                             │
│  ┌───────────┐       ┌───────────┐       ┌───────────┐      │
│  │  WARRIOR  │──────▶│   GUARD   │──────▶│   JESTER  │      │
│  │ (Action)  │       │ (Defense) │       │(Validation)│     │
│  └───────────┘       └───────────┘       └───────────┘      │
│        ▲                   │                   │            │
│        │                   │ Realtime          │ Final      │
│        │                   ▼ Feedback          ▼ Verdict    │
│        │             ┌───────────┐       ┌───────────┐      │
│        └─────────────│ OPEN CODE │◀──────│  SCRIBE   │      │
│           Command    │ (Context) │       │(Knowledge)│      │
│                      └───────────┘       └───────────┘      │
└─────────────────────────────────────────────────────────────┘
```

1. **Warrior** initiates action (The Sword).
2. **Guard** watches every step (The Shield/Bumpers). 
   - *Strict Mode*: Blocks immediately on violation.
   - *Learning Mode*: Observes and advises (allows "risk").
3. **Jester** validates the final result (The Judge).
4. **Scribe** records the entire session (The Historian).

---

## Data Models

### ValidationResult
Enhanced to support the optimization loop:
```python
@dataclass
class ValidationResult:
    syntax_valid: bool
    executes: bool
    execution_result: Optional[ExecutionResult]
    execution_stats: Dict[str, Any]  # {'time_ms': 120, 'memory_mb': 15}
    feedback: str  # "Execution failed: ZeroDivisionError"
    patterns_detected: List[str]
    overall_success: bool
```

### ExecutionResult
Captures the raw runtime data:
```python
@dataclass
class ExecutionResult:
    success: bool
    execution_time_ms: float
    memory_usage_mb: float
    error: Optional[str]
    tier: ExecutionTier
```

---

## Implementation Roadmap (Status)

### Phase 1: Foundation (✅ Complete)
- Event system, Dashboard, Ollama integration, Basic REPL execution.

### Phase 2: The Kingdom (✅ Complete)
- `jester.toml` configuration.
- Multi-realm watching logic.
- SQLite metric aggregation.

### Phase 2b: Open Code (✅ Complete)
- `OpenCodeIntegration` creation.
- Provider switching logic (Claude Code vs Open Code).

### Phase 3: Guidance (✅ Complete)
- Dashboard "Rhythm" metrics (churn/complexity over time).

### Phase 4: Performance Loop (✅ Complete)
- `jester optimize` command.
- Feedback-driven generation.
- Performance thresholds.

---

## Future Directions
- **Deep Graph Analysis:** Move Scribe from SQLite metrics to full Neo4j/NetworkX graph analysis for architectural patterns.
- **Containerization:** Harden the `execution_tier` with full Docker support for untrusted code.
- **IDE Integration:** exposing Jester via LSP.
