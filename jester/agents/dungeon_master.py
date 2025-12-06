"""
The Dungeon Master - Keeper of the Containers
Manages Docker/Podman resources, image lifecycles, and environment isolation.
"""

from typing import List, Optional
import asyncio

from ..core.models import AgentType, Event, EventType
from ..core.event_stream import EventBus
from ..execution.container_executor import ContainerExecutor
from .base_agent import BaseAgent

class DungeonMaster(BaseAgent):
    """
    Manages the container execution environment.
    """
    
    def __init__(self, event_bus: EventBus, container_executor: Optional[ContainerExecutor] = None):
        super().__init__(AgentType.RELIABILITY, event_bus) # Using RELIABILITY type for Ops
        self.executor = container_executor or ContainerExecutor()
        
        self.subscribe([
            EventType.SYSTEM_STARTUP,
            EventType.CLEANUP_REQUESTED
        ])

    async def on_event(self, event: Event) -> None:
        """Handle system events"""
        if event.event_type == EventType.SYSTEM_STARTUP:
            await self.prepare_dungeon()
        elif event.event_type == EventType.CLEANUP_REQUESTED:
            await self.cleanup_dungeon()

    async def prepare_dungeon(self):
        """Pre-pull common images to reduce first-run latency"""
        if not self.executor.is_container_available():
            await self.thinking("No container runtime detected. The Dungeon is closed.")
            return

        await self.thinking("Preparing The Dungeon (Pulling base images)...")
        tasks = []
        for lang in ["python", "javascript", "bash"]:
            tasks.append(self.executor._ensure_image(lang))
        
        try:
            await asyncio.gather(*tasks)
            await self.thinking("The Dungeon is ready.")
        except Exception as e:
            await self.thinking(f"Failed to prepare Dungeon: {e}")

    async def cleanup_dungeon(self):
        """Clean up potential leftover resources"""
        if not self.executor.is_container_available():
            return
            
        await self.thinking("Cleaning up the Dungeon...")
        # In a real implementation this might run 'docker system prune' or similar
        # For now, we just pass.
        pass
