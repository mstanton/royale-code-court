"""
The Scribe - Knowledge Keeper/Observer Agent
Patient, wise, sees patterns others miss
The "higher self" - wisdom, reflection, strategic thinking
"""

import ast
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from ..core.models import (
    AgentType,
    Event,
    EventType,
    CodePattern,
    ArchitecturalInsight,
    Intervention,
    InterventionAction,
    SeverityLevel,
    CodeEntity,
)
from ..core.event_stream import EventBus
from .base_agent import BaseAgent


# Design patterns to detect
DESIGN_PATTERNS = {
    "singleton": {
        "pattern": r'_instance\s*=\s*None.*def\s+get_instance',
        "category": "creational",
        "description": "Singleton pattern - ensures single instance",
    },
    "factory": {
        "pattern": r'def\s+create_\w+|class\s+\w*Factory',
        "category": "creational",
        "description": "Factory pattern - creates objects without exposing creation logic",
    },
    "decorator_pattern": {
        "pattern": r'def\s+\w+\s*\(.*func.*\).*def\s+wrapper',
        "category": "structural",
        "description": "Decorator pattern - adds behavior dynamically",
    },
    "observer": {
        "pattern": r'observers|subscribers|listeners.*(?:add|notify|subscribe)',
        "category": "behavioral",
        "description": "Observer pattern - notify dependents of state changes",
    },
    "strategy": {
        "pattern": r'class\s+\w*Strategy|def\s+execute\s*\(self.*strategy',
        "category": "behavioral",
        "description": "Strategy pattern - encapsulates algorithms",
    },
    "repository": {
        "pattern": r'class\s+\w*Repository.*def\s+(?:get|find|save|delete)',
        "category": "architectural",
        "description": "Repository pattern - data access abstraction",
    },
}

# Anti-patterns to detect
ANTI_PATTERNS = {
    "god_object": {
        "condition": lambda code: len(re.findall(r'def\s+\w+', code)) > 20,
        "severity": SeverityLevel.HIGH,
        "description": "God Object - class doing too much",
        "suggestion": "Consider breaking into smaller, focused classes",
    },
    "magic_numbers": {
        "pattern": r'(?<!["\'])\b(?:3\.14|365|24|60|1000|100)\b(?!["\'])',
        "severity": SeverityLevel.LOW,
        "description": "Magic numbers detected",
        "suggestion": "Consider using named constants",
    },
    "long_function": {
        "condition": lambda code: any(
            len(m.group(0).split('\n')) > 50
            for m in re.finditer(r'def\s+\w+.*?(?=\ndef\s+|\nclass\s+|\Z)', code, re.DOTALL)
        ),
        "severity": SeverityLevel.MEDIUM,
        "description": "Function exceeds 50 lines",
        "suggestion": "Consider breaking into smaller functions",
    },
    "deep_nesting": {
        "condition": lambda code: '                ' in code,  # 4+ levels of indentation
        "severity": SeverityLevel.MEDIUM,
        "description": "Deep nesting detected (4+ levels)",
        "suggestion": "Consider early returns or extracting methods",
    },
    "no_error_handling": {
        "condition": lambda code: 'def ' in code and 'try:' not in code and 'except' not in code,
        "severity": SeverityLevel.LOW,
        "description": "No error handling found",
        "suggestion": "Consider adding try/except for robust error handling",
    },
}


@dataclass
class KnowledgeEntry:
    """An entry in the knowledge graph"""
    entity_id: str
    entity_type: str
    name: str
    code_hash: str
    patterns: List[str] = field(default_factory=list)
    relationships: Dict[str, List[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)


class ScribeAgent(BaseAgent):
    """
    The Scribe observes, learns, and provides architectural wisdom.
    Can interrupt processes when detecting critical issues.
    Gates the memory system - decides what's worth remembering.
    """

    def __init__(self, event_bus: EventBus):
        super().__init__(AgentType.SCRIBE, event_bus)

        # Knowledge graph (in-memory for now, can be NetworkX/Neo4j)
        self.knowledge: Dict[str, KnowledgeEntry] = {}
        self.pattern_history: Dict[str, List[Dict]] = {}
        self.insights: List[ArchitecturalInsight] = []
        self.pending_interventions: List[Intervention] = []

        # Subscribe to events
        self.subscribe([
            EventType.CODE_GENERATED,
            EventType.CODE_VALIDATED,
            EventType.EXECUTION_COMPLETE,
            EventType.HUMAN_DECISION,
        ])

    async def on_event(self, event: Event) -> None:
        """Handle incoming events"""
        if event.event_type == EventType.CODE_GENERATED:
            code = event.payload.get("code", "")
            if code:
                await self.analyze_code(code, event)

        elif event.event_type == EventType.CODE_VALIDATED:
            await self._process_validation(event)

        elif event.event_type == EventType.EXECUTION_COMPLETE:
            await self._process_execution(event)

        elif event.event_type == EventType.HUMAN_DECISION:
            await self._learn_from_decision(event)

    async def analyze_code(self, code: str, source_event: Optional[Event] = None) -> Dict[str, Any]:
        """
        Comprehensive code analysis.
        Returns patterns, insights, and potential interventions.
        """
        analysis = {
            "patterns": [],
            "anti_patterns": [],
            "insights": [],
            "interventions": [],
            "entities": [],
        }

        await self.thinking("Analyzing code patterns...")

        # Detect design patterns
        for pattern_name, pattern_info in DESIGN_PATTERNS.items():
            if re.search(pattern_info["pattern"], code, re.DOTALL | re.IGNORECASE):
                pattern = CodePattern(
                    pattern_id=pattern_name,
                    name=pattern_name.replace('_', ' ').title(),
                    category=pattern_info["category"],
                    description=pattern_info["description"],
                    confidence=0.85,
                )
                analysis["patterns"].append(pattern)
                await self._emit_pattern(pattern)

        # Detect anti-patterns
        for anti_name, anti_info in ANTI_PATTERNS.items():
            detected = False
            if "pattern" in anti_info:
                detected = bool(re.search(anti_info["pattern"], code))
            elif "condition" in anti_info:
                try:
                    detected = anti_info["condition"](code)
                except Exception:
                    pass

            if detected:
                analysis["anti_patterns"].append({
                    "name": anti_name,
                    "severity": anti_info["severity"],
                    "description": anti_info["description"],
                    "suggestion": anti_info["suggestion"],
                })

                # Create insight
                insight = ArchitecturalInsight(
                    insight_type="smell",
                    title=anti_info["description"],
                    description=anti_info["suggestion"],
                    severity=anti_info["severity"],
                    suggested_action=anti_info["suggestion"],
                    confidence=0.8,
                )
                analysis["insights"].append(insight)

                # Create intervention for critical issues
                if anti_info["severity"] == SeverityLevel.CRITICAL:
                    intervention = Intervention(
                        trigger="architecture",
                        action=InterventionAction.BLOCK,
                        message=anti_info["description"],
                        options=[
                            "Fix automatically",
                            "Show me how to fix",
                            "Proceed anyway",
                        ],
                        blocking=True,
                    )
                    analysis["interventions"].append(intervention)
                    await self._emit_intervention(intervention)

        # Extract code entities
        entities = self._extract_entities(code)
        analysis["entities"] = entities

        # Check for similar code in knowledge base
        similar = await self._find_similar_code(code)
        if similar:
            analysis["insights"].append(ArchitecturalInsight(
                insight_type="opportunity",
                title="Similar code exists",
                description=f"Found {len(similar)} similar code snippets in knowledge base",
                severity=SeverityLevel.INFO,
                suggested_action="Consider reusing existing code",
                confidence=0.7,
            ))

        return analysis

    def _extract_entities(self, code: str) -> List[CodeEntity]:
        """Extract code entities (functions, classes, etc.)"""
        entities = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return entities

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                entities.append(CodeEntity(
                    entity_id=f"func_{node.name}",
                    entity_type="function",
                    name=node.name,
                    complexity=self._node_complexity(node),
                ))
            elif isinstance(node, ast.ClassDef):
                entities.append(CodeEntity(
                    entity_id=f"class_{node.name}",
                    entity_type="class",
                    name=node.name,
                    complexity=self._node_complexity(node),
                ))

        return entities

    def _node_complexity(self, node: ast.AST) -> int:
        """Calculate complexity for an AST node"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    async def _find_similar_code(self, code: str) -> List[KnowledgeEntry]:
        """Find similar code in knowledge base"""
        # Simple hash-based similarity for now
        # In production, use embeddings and vector similarity
        code_hash = hash(code.strip())
        similar = []

        for entry in self.knowledge.values():
            # Very basic similarity - in production use proper embeddings
            if abs(hash(entry.code_hash) - code_hash) < 1000:
                similar.append(entry)

        return similar[:5]  # Top 5 similar

    async def _process_validation(self, event: Event) -> None:
        """Process validation results and update knowledge"""
        payload = event.payload
        patterns = payload.get("patterns_detected", [])
        success = payload.get("overall_success", False)

        # Update pattern history
        for pattern in patterns:
            if pattern not in self.pattern_history:
                self.pattern_history[pattern] = []
            self.pattern_history[pattern].append({
                "success": success,
                "timestamp": datetime.now().isoformat(),
            })

    async def _process_execution(self, event: Event) -> None:
        """Process execution results and learn"""
        payload = event.payload
        success = payload.get("success", False)
        execution_time = payload.get("execution_time_ms", 0)

        # Track performance insights
        if execution_time > 1000:  # > 1 second
            insight = ArchitecturalInsight(
                insight_type="performance",
                title="Slow execution detected",
                description=f"Execution took {execution_time:.0f}ms",
                severity=SeverityLevel.MEDIUM,
                suggested_action="Consider optimizing the code",
                confidence=0.9,
            )
            self.insights.append(insight)
            await self.emit(EventType.PERFORMANCE_INSIGHT, {
                "execution_time_ms": execution_time,
                "insight": insight.title,
            })

    async def _learn_from_decision(self, event: Event) -> None:
        """Learn from human decisions"""
        decision = event.payload.get("decision", "")
        context = event.payload.get("context", {})

        await self.log(f"Learning from decision: {decision}")
        # In production, update weights/preferences based on decisions

    async def _emit_pattern(self, pattern: CodePattern) -> None:
        """Emit pattern detected event"""
        await self.emit(EventType.PATTERN_DETECTED, {
            "pattern_id": pattern.pattern_id,
            "name": pattern.name,
            "category": pattern.category,
            "description": pattern.description,
            "confidence": pattern.confidence,
        })

    async def _emit_intervention(self, intervention: Intervention) -> None:
        """Emit intervention event"""
        self.pending_interventions.append(intervention)
        await self.emit(EventType.INTERVENTION_TRIGGERED, {
            "trigger": intervention.trigger,
            "action": intervention.action.value,
            "message": intervention.message,
            "options": intervention.options,
            "blocking": intervention.blocking,
        })

    def should_remember(self, event: Event) -> bool:
        """
        Memory gatekeeper logic.
        Decides what's worth storing in long-term memory.
        """
        # Always remember security issues
        if event.event_type == EventType.SECURITY_ALERT:
            return True

        # Remember successful patterns
        if event.event_type == EventType.PATTERN_DETECTED:
            return True

        # Remember failures for learning
        if event.event_type == EventType.EXECUTION_ERROR:
            return True

        # Remember human decisions
        if event.event_type == EventType.HUMAN_DECISION:
            return True

        # Don't remember routine successful executions
        if event.event_type == EventType.EXECUTION_COMPLETE:
            return event.payload.get("success", True) is False

        return False

    def get_pattern_success_rate(self, pattern_name: str) -> float:
        """Get success rate for a pattern"""
        history = self.pattern_history.get(pattern_name, [])
        if not history:
            return 0.0
        successes = sum(1 for h in history if h.get("success", False))
        return successes / len(history)

    def format_insights_report(self) -> str:
        """Format insights for display"""
        if not self.insights:
            return "📜 No architectural insights yet."

        lines = ["📜 Scribe's Architectural Insights", "=" * 40, ""]

        for insight in self.insights[-10:]:  # Last 10 insights
            severity_emoji = {
                SeverityLevel.INFO: "ℹ️",
                SeverityLevel.LOW: "💭",
                SeverityLevel.MEDIUM: "⚠️",
                SeverityLevel.HIGH: "🔶",
                SeverityLevel.CRITICAL: "🚨",
            }.get(insight.severity, "•")

            lines.append(f"{severity_emoji} {insight.title}")
            lines.append(f"   {insight.description}")
            if insight.suggested_action:
                lines.append(f"   💡 {insight.suggested_action}")
            lines.append("")

        return "\n".join(lines)
