"""
The Royal Guard (The Bumper)
Monitors execution in real-time and provides defensive feedback.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
import asyncio
from ..core.event_stream import EventBus, EventType, Event, AgentType
from ..execution.tracer import TraceEvent

class GuardMode(Enum):
    STRICT = "strict"      # Defensive: Block on any risk
    LEARNING = "learning"  # Exploratory: Allow risks, warn only

class RoyalGuard:
    """
    The Royal Guard Agent.
    Analyzes trace events and emits interventions.
    """
    def __init__(self, event_bus: EventBus, mode: GuardMode = GuardMode.STRICT):
        self.event_bus = event_bus
        self.mode = mode
        self.violations = []
        
        # Limits
        self.MAX_LOOPS = 100 if mode == GuardMode.STRICT else 1000
        self.loop_counters = {} # Line-based counters

    def handle_trace(self, event: TraceEvent):
        """
        Callback for the ExecutionTracer.
        Analyzes a single step of execution.
        """
        # Simplify access whether it's an object or dict
        if isinstance(event, dict):
            event_type = event.get('execution_event_type', event.get('event_type'))
            function = event.get('function')
            lineno = event.get('lineno')
            variables = event.get('variables', {})
        else:
            event_type = event.event_type
            function = event.function
            lineno = event.lineno
            variables = event.variables

        # 1. Loop Detection
        if event_type == 'line':
            loc_id = f"{function}:{lineno}"
            self.loop_counters[loc_id] = self.loop_counters.get(loc_id, 0) + 1
            
            if self.loop_counters[loc_id] > self.MAX_LOOPS:
                self._intervene(f"Infinite loop suspected at {loc_id} (Count: {self.loop_counters[loc_id]})", "high")
        
        # 2. Variable Checks (Bumpers)
        # Check for dangerous values or types
        # (Simplified example: Check for extremely large lists)
        for name, value in variables.items():
            if name.endswith("_len") and value > 10000:
                 if self.mode == GuardMode.STRICT:
                     self._intervene(f"Variable {name} exceeds size limit (Size: {value})", "critical")
                 else:
                     # Just warn in learning mode
                     pass

    def _intervene(self, message: str, severity: str):
        """Emit intervention event (The "Bumper" hit)"""
        # In a real sync trace, we can't await, so we might store or print.
        # Ideally, we queue this for the async loop or raise an exception to stop execution.
        print(f"🛡️ GUARD INTERVENTION [{severity.upper()}]: {message}")
        
        if (severity == "critical" or severity == "high") and self.mode == GuardMode.STRICT:
             raise RuntimeError(f"Guard Block: {message}")

        self.violations.append({
            "message": message,
            "severity": severity,
            "timestamp": "now" # placeholder
        })
