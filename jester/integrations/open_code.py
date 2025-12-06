"""
Open Code Integration - The Local Warrior
Power to the People. Applies changes locally using Ollama for intelligence.
"""

import asyncio
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.models import AgentType, Event, EventType
from ..core.event_stream import EventBus
from ..agents.base_agent import BaseAgent
from .ollama_client import KingAgent

@dataclass
class CodeChange:
    """A code change to apply"""
    file_path: str
    content: str
    operation: str = "write"  # write, append, patch
    description: str = ""


@dataclass
class ApplyResult:
    """Result of applying code changes"""
    success: bool
    files_modified: List[str]
    error: str = ""


class OpenCodeIntegration(BaseAgent):
    """
    The Local Warrior - applies validated code changes intelligently.
    Uses Ollama for smart patching (fuzzy matching) when simple application fails.
    """

    def __init__(
        self,
        event_bus: EventBus,
        ollama_agent: KingAgent,
        working_dir: Optional[str] = None,
    ):
        super().__init__(AgentType.WARRIOR, event_bus)
        self.ollama_agent = ollama_agent
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
        
        # Track pending changes
        self.pending_changes: List[CodeChange] = []
        self.applied_changes: List[CodeChange] = []

        # Subscribe to validation events
        self.subscribe([
            EventType.CODE_VALIDATED,
            EventType.HUMAN_DECISION,
        ])

    async def on_event(self, event: Event) -> None:
        """Handle incoming events"""
        if event.event_type == EventType.CODE_VALIDATED:
            payload = event.payload
            # If code is valid, we acknowledge it. The HUMAN must approve application.
            if payload.get("overall_success", False):
                await self.log(f"Received validated code. Waiting for 'apply' command.")

        elif event.event_type == EventType.HUMAN_DECISION:
            decision = event.payload.get("decision", "")
            if decision == "apply":
                await self.apply_pending_changes()

    async def queue_change(self, change: CodeChange) -> None:
        """Queue a code change for application"""
        self.pending_changes.append(change)
        await self.log(f"Queued change for {change.file_path}")

    async def apply_change(self, change: CodeChange) -> ApplyResult:
        """Apply a single code change"""
        await self.thinking(f"Applying change to {change.file_path}...")

        try:
            file_path = self.working_dir / change.file_path

            if change.operation == "write":
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(change.content, encoding="utf-8")

            elif change.operation == "append":
                if not file_path.exists():
                     file_path.parent.mkdir(parents=True, exist_ok=True) # Fallback to create
                
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(change.content)

            elif change.operation == "patch":
                # Smart Patching
                if not file_path.exists():
                     return ApplyResult(False, [], f"Cannot patch non-existent file: {change.file_path}")
                
                original_content = file_path.read_text(encoding="utf-8")
                patched_content = await self._smart_patch(original_content, change.content)
                file_path.write_text(patched_content, encoding="utf-8")

            self.applied_changes.append(change)

            await self.emit(EventType.CODE_APPLIED, {
                "file_path": str(change.file_path),
                "operation": change.operation,
                "description": change.description,
            })

            return ApplyResult(
                success=True,
                files_modified=[str(change.file_path)],
            )

        except Exception as e:
            return ApplyResult(
                success=False,
                files_modified=[],
                error=str(e),
            )

    async def _smart_patch(self, original: str, patch: str) -> str:
        """Use Ollama to apply a smart patch"""
        prompt = f"""
        Original Code:
        ```python
        {original}
        ```

        Patch Instruction/Diff:
        {patch}

        Task: Apply the patch to the original code. Return ONLY the full updated code.
        Do not add markdown formatting or comments.
        """
        result = await self.ollama_agent.generate_code(prompt, "python")
        return result.code

    async def apply_pending_changes(self) -> ApplyResult:
        """Apply all pending changes"""
        if not self.pending_changes:
            return ApplyResult(success=True, files_modified=[])

        await self.thinking(f"Applying {len(self.pending_changes)} changes...")

        files_modified = []
        errors = []

        for change in self.pending_changes:
            result = await self.apply_change(change)
            if result.success:
                files_modified.extend(result.files_modified)
            else:
                errors.append(f"{change.file_path}: {result.error}")

        self.pending_changes.clear()

        return ApplyResult(
            success=len(errors) == 0,
            files_modified=files_modified,
            error="; ".join(errors) if errors else "",
        )
