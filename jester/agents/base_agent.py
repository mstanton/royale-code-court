"""
Base Agent - Foundation for all Royal Court agents
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import asyncio

from ..core.models import AgentType, Event, EventType
from ..core.event_stream import EventBus, EventStream


class BaseAgent(ABC):
    """
    Base class for all agents in the Royal Court.
    Provides common functionality for event handling and communication.
    """

    def __init__(
        self,
        agent_type: AgentType,
        event_bus: EventBus,
    ):
        self.agent_type = agent_type
        self.event_bus = event_bus
        self.event_stream = EventStream(event_bus, agent_type)
        self._running = False
        self._subscribed_events: List[EventType] = []

    @property
    def name(self) -> str:
        """Agent name for display"""
        return self.agent_type.value.title()

    @property
    def emoji(self) -> str:
        """Agent emoji for display"""
        emojis = {
            AgentType.KING: "👑",
            AgentType.JESTER: "🃏",
            AgentType.SCRIBE: "📜",
            AgentType.WARRIOR: "⚔️",
            AgentType.HUMAN: "👤",
            AgentType.SYSTEM: "🖥️",
        }
        return emojis.get(self.agent_type, "🤖")

    def subscribe(self, event_types: List[EventType]) -> None:
        """Subscribe to specific event types"""
        for event_type in event_types:
            self.event_bus.subscribe(event_type, self._handle_event)
            self._subscribed_events.append(event_type)

    async def _handle_event(self, event: Event) -> None:
        """Internal event handler wrapper"""
        if self._running:
            await self.on_event(event)

    @abstractmethod
    async def on_event(self, event: Event) -> None:
        """Handle incoming events - must be implemented by subclasses"""
        pass

    async def emit(self, event_type: EventType, payload: Dict[str, Any]) -> Event:
        """Emit an event"""
        return await self.event_stream.emit(event_type, payload)

    async def log(self, message: str, level: str = "info") -> None:
        """Emit a log message"""
        await self.event_stream.log(message, level)

    async def thinking(self, message: str) -> None:
        """Emit a thinking status"""
        await self.event_stream.thinking(message)

    def start(self) -> None:
        """Start the agent"""
        self._running = True

    def stop(self) -> None:
        """Stop the agent"""
        self._running = False

    async def __aenter__(self):
        self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.stop()
