"""
Event Stream - The Nervous System of the Royal Court
Real-time event bus for agent communication and observability
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
import uuid
import json

from .models import Event, EventType, AgentType


# Type for event handlers
EventHandler = Callable[[Event], None]
AsyncEventHandler = Callable[[Event], Any]


class EventBus:
    """
    Central event bus for the Royal Court.
    All agents communicate through this bus, creating full observability.
    """

    def __init__(self):
        self._handlers: Dict[EventType, List[AsyncEventHandler]] = defaultdict(list)
        self._global_handlers: List[AsyncEventHandler] = []
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._session_id = str(uuid.uuid4())[:8]
        self._running = False
        self._event_queue: asyncio.Queue = asyncio.Queue()

    @property
    def session_id(self) -> str:
        return self._session_id

    def subscribe(self, event_type: EventType, handler: AsyncEventHandler) -> None:
        """Subscribe to a specific event type"""
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: AsyncEventHandler) -> None:
        """Subscribe to all events (for logging, dashboard, etc.)"""
        self._global_handlers.append(handler)

    def unsubscribe(self, event_type: EventType, handler: AsyncEventHandler) -> None:
        """Unsubscribe from an event type"""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    async def emit(self, event: Event) -> None:
        """Emit an event to all subscribers"""
        # Set session ID if not set
        if not event.session_id:
            event.session_id = self._session_id

        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Notify specific handlers
        for handler in self._handlers[event.event_type]:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                print(f"Error in event handler: {e}")

        # Notify global handlers
        for handler in self._global_handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                print(f"Error in global event handler: {e}")

    def emit_sync(self, event: Event) -> None:
        """Synchronous emit for non-async contexts"""
        if not event.session_id:
            event.session_id = self._session_id

        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # For sync, we only call sync handlers
        for handler in self._handlers[event.event_type]:
            try:
                result = handler(event)
                # Skip if coroutine
                if not asyncio.iscoroutine(result):
                    pass
            except Exception as e:
                print(f"Error in event handler: {e}")

        for handler in self._global_handlers:
            try:
                result = handler(event)
                if not asyncio.iscoroutine(result):
                    pass
            except Exception as e:
                print(f"Error in global handler: {e}")

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        agent: Optional[AgentType] = None,
        limit: int = 100,
    ) -> List[Event]:
        """Get event history with optional filters"""
        events = self._event_history

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if agent:
            events = [e for e in events if e.agent == agent]

        return events[-limit:]

    def clear_history(self) -> None:
        """Clear event history"""
        self._event_history.clear()


class EventStream:
    """
    High-level event stream with convenience methods for emitting events.
    Used by agents to communicate.
    """

    def __init__(self, bus: EventBus, agent: AgentType):
        self.bus = bus
        self.agent = agent

    async def emit(
        self,
        event_type: EventType,
        payload: Dict[str, Any],
        parent_event_id: Optional[str] = None,
    ) -> Event:
        """Emit an event from this agent"""
        event = Event(
            event_type=event_type,
            agent=self.agent,
            payload=payload,
            parent_event_id=parent_event_id,
        )
        await self.bus.emit(event)
        return event

    def emit_sync(
        self,
        event_type: EventType,
        payload: Dict[str, Any],
        parent_event_id: Optional[str] = None,
    ) -> Event:
        """Synchronous emit"""
        event = Event(
            event_type=event_type,
            agent=self.agent,
            payload=payload,
            parent_event_id=parent_event_id,
        )
        self.bus.emit_sync(event)
        return event

    # Convenience methods for common events

    async def log(self, message: str, level: str = "info") -> Event:
        """Emit a log message event"""
        return await self.emit(
            EventType.LOG_MESSAGE,
            {"message": message, "level": level},
        )

    async def code_generated(self, code: str, language: str = "python", **kwargs) -> Event:
        """Emit code generated event"""
        return await self.emit(
            EventType.CODE_GENERATED,
            {"code": code, "language": language, **kwargs},
        )

    async def execution_start(self, code_id: str, tier: str = "repl") -> Event:
        """Emit execution start event"""
        return await self.emit(
            EventType.EXECUTION_START,
            {"code_id": code_id, "tier": tier},
        )

    async def execution_complete(
        self,
        code_id: str,
        success: bool,
        output: str = "",
        error: str = "",
        execution_time_ms: float = 0.0,
    ) -> Event:
        """Emit execution complete event"""
        return await self.emit(
            EventType.EXECUTION_COMPLETE,
            {
                "code_id": code_id,
                "success": success,
                "output": output,
                "error": error,
                "execution_time_ms": execution_time_ms,
            },
        )

    async def execution_output(self, code_id: str, output: str, stream: str = "stdout") -> Event:
        """Emit execution output event (for streaming)"""
        return await self.emit(
            EventType.EXECUTION_OUTPUT,
            {"code_id": code_id, "output": output, "stream": stream},
        )

    async def code_validated(self, validation_result: Dict[str, Any]) -> Event:
        """Emit code validated event"""
        return await self.emit(EventType.CODE_VALIDATED, validation_result)

    async def pattern_detected(self, pattern: str, confidence: float, **kwargs) -> Event:
        """Emit pattern detected event"""
        return await self.emit(
            EventType.PATTERN_DETECTED,
            {"pattern": pattern, "confidence": confidence, **kwargs},
        )

    async def intervention(
        self,
        trigger: str,
        action: str,
        message: str,
        options: List[str] = None,
    ) -> Event:
        """Emit intervention event"""
        return await self.emit(
            EventType.INTERVENTION_TRIGGERED,
            {
                "trigger": trigger,
                "action": action,
                "message": message,
                "options": options or [],
            },
        )

    async def thinking(self, message: str) -> Event:
        """Emit agent thinking event"""
        return await self.emit(
            EventType.AGENT_THINKING,
            {"message": message},
        )


# Global event bus singleton
_global_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus


def create_event_stream(agent: AgentType) -> EventStream:
    """Create an event stream for an agent"""
    return EventStream(get_event_bus(), agent)
