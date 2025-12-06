"""
Core data models for Code Jester
Based on the Royal Court architecture specification
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class AgentType(str, Enum):
    """The agents of the Royal Court"""
    KING = "king"           # Code Generator (Ollama)
    JESTER = "jester"       # Validator/Tester
    SCRIBE = "scribe"       # Knowledge Keeper
    WARRIOR = "warrior"     # Code Integrator (Claude Code)
    HUMAN = "human"         # Strategic Director
    SYSTEM = "system"       # System events


class EventType(str, Enum):
    """All event types in the system"""
    # Code Lifecycle
    CODE_GENERATED = "code.generated"
    CODE_RECEIVED = "code.received"
    CODE_VALIDATED = "code.validated"
    CODE_APPLIED = "code.applied"
    FILE_CHANGED = "file.changed"

    # Analysis & Metrics
    METRICS_UPDATED = "metrics.updated"
    ANALYSIS_OPPORTUNITY = "analysis.opportunity"
    ANALYSIS_APPROVED = "analysis.approved"

    # Execution
    EXECUTION_START = "execution.start"
    EXECUTION_COMPLETE = "execution.complete"
    EXECUTION_ERROR = "execution.error"
    EXECUTION_OUTPUT = "execution.output"

    # Testing
    TEST_GENERATION_START = "test.generation.start"
    TEST_GENERATION_COMPLETE = "test.generation.complete"
    TEST_EXECUTION_COMPLETE = "test.execution.complete"

    # Optimization
    OPTIMIZATION_START = "optimization.start"
    OPTIMIZATION_COMPLETE = "optimization.complete"
    VARIANT_TESTED = "variant.tested"

    # Scribe - Pattern Recognition
    PATTERN_DETECTED = "pattern.detected"
    PATTERN_LEARNED = "pattern.learned"
    ANTIPATTERN_DETECTED = "antipattern.detected"

    # Scribe - Knowledge Graph
    RELATIONSHIP_DISCOVERED = "relationship.discovered"
    KNOWLEDGE_GRAPH_UPDATE = "knowledge.graph.update"
    ENTITY_CREATED = "entity.created"

    # Scribe - Insights
    ARCHITECTURAL_INSIGHT = "architectural.insight"
    REFACTORING_SUGGESTED = "refactoring.suggested"
    DESIGN_SUGGESTION = "design.suggestion"
    PERFORMANCE_INSIGHT = "performance.insight"

    # Scribe - Interventions
    INTERVENTION_TRIGGERED = "intervention.triggered"
    SECURITY_ALERT = "security.alert"
    QUALITY_GATE_FAILED = "quality.gate.failed"

    # Human Interaction
    HITL_REQUEST = "hitl.request"
    HITL_RESPONSE = "hitl.response"
    HUMAN_DECISION = "human.decision"
    HUMAN_FEEDBACK = "human.feedback"
    HUMAN_INPUT = "human.input"

    # Memory
    MEMORY_QUERY = "memory.query"
    MEMORY_UPDATE = "memory.update"
    MEMORY_GATE_DECISION = "memory.gate.decision"

    # Agent Status
    AGENT_STATUS_CHANGE = "agent.status"
    AGENT_ERROR = "agent.error"
    AGENT_THINKING = "agent.thinking"

    # System
    SESSION_START = "session.start"
    SESSION_END = "session.end"
    SYSTEM_ERROR = "system.error"
    LOG_MESSAGE = "log.message"


class ExecutionTier(str, Enum):
    """Tiered execution strategy"""
    STATIC = "static"       # AST analysis (1-5ms)
    REPL = "repl"          # RestrictedPython (10-50ms)
    CONTAINER = "container" # Docker/Podman (50-200ms)


class SeverityLevel(str, Enum):
    """Severity levels for insights and interventions"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InterventionAction(str, Enum):
    """Actions the Scribe can take"""
    NOTIFY = "notify"       # Information to show
    REQUEST = "request"     # Request human input
    BLOCK = "block"         # Block the operation


@dataclass
class Event:
    """Core event that flows through the system"""
    event_type: EventType
    agent: AgentType
    payload: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: str = ""
    parent_event_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "agent": self.agent.value,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "parent_event_id": self.parent_event_id,
            "payload": self.payload,
        }


@dataclass
class CodeSubmission:
    """Code submitted for validation"""
    code: str
    language: str = "python"
    context: str = ""
    requirements: str = ""
    submission_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionResult:
    """Result from code execution"""
    success: bool
    output: str = ""
    error: str = ""
    execution_time_ms: float = 0.0
    tier: ExecutionTier = ExecutionTier.REPL
    memory_usage_mb: float = 0.0
    return_value: Any = None

    @property
    def status_emoji(self) -> str:
        return "✅" if self.success else "❌"


@dataclass
class ValidationResult:
    """Complete validation result from Jester"""
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

    @property
    def all_tests_pass(self) -> bool:
        return self.tests_failed == 0 and self.tests_passed > 0

    @property
    def overall_success(self) -> bool:
        return self.syntax_valid and self.executes and len(self.issues) == 0


@dataclass
class CodePattern:
    """A detected code pattern"""
    pattern_id: str
    name: str
    category: str  # design, functional, architectural, antipattern
    description: str
    confidence: float = 0.0
    occurrences: int = 0
    success_rate: float = 0.0


@dataclass
class ArchitecturalInsight:
    """Insight from the Scribe"""
    insight_type: str  # recommendation, smell, opportunity, risk
    title: str
    description: str
    severity: SeverityLevel = SeverityLevel.INFO
    suggested_action: Optional[str] = None
    evidence: List[Dict] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class Intervention:
    """Intervention from the Scribe"""
    trigger: str  # security, performance, architecture, duplication
    action: InterventionAction
    message: str
    options: List[str] = field(default_factory=list)
    deadline: Optional[datetime] = None
    blocking: bool = False


@dataclass
class CodeEntity:
    """Entity in the knowledge graph"""
    entity_id: str
    entity_type: str  # function, class, module
    name: str
    file_path: Optional[str] = None
    patterns_used: List[str] = field(default_factory=list)
    complexity: int = 0
    performance_profile: Dict[str, float] = field(default_factory=dict)


@dataclass
class SessionState:
    """Current session state"""
    session_id: str
    started_at: datetime = field(default_factory=datetime.now)
    events: List[Event] = field(default_factory=list)
    code_submissions: List[CodeSubmission] = field(default_factory=list)
    validations: List[ValidationResult] = field(default_factory=list)
    human_decisions: List[Dict] = field(default_factory=list)
    active: bool = True
