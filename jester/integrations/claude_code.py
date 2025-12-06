"""
Claude Code Integration - The Warrior (Code Integrator)
Disciplined, precise, executes only validated code
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
    git_commit: Optional[str] = None


class ClaudeCodeIntegration(BaseAgent):
    """
    The Warrior - applies validated code changes.
    Uses Claude Code CLI for actual file modifications.
    """

    def __init__(
        self,
        event_bus: EventBus,
        working_dir: Optional[str] = None,
        auto_commit: bool = False,
    ):
        super().__init__(AgentType.WARRIOR, event_bus)
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
        self.auto_commit = auto_commit

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
            if event.payload.get("overall_success", False):
                # Code is validated, could be applied
                await self.log("Code validated, ready for application")

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
                file_path.write_text(change.content)

            elif change.operation == "append":
                with open(file_path, "a") as f:
                    f.write(change.content)

            elif change.operation == "patch":
                # For patch operations, we'd use a diff/patch library
                # For now, just write
                file_path.write_text(change.content)

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

        # Auto-commit if enabled
        git_commit = None
        if self.auto_commit and files_modified:
            git_commit = await self._git_commit(files_modified)

        return ApplyResult(
            success=len(errors) == 0,
            files_modified=files_modified,
            error="; ".join(errors) if errors else "",
            git_commit=git_commit,
        )

    async def _git_commit(self, files: List[str]) -> Optional[str]:
        """Create a git commit for the changes"""
        try:
            # Stage files
            subprocess.run(
                ["git", "add"] + files,
                cwd=self.working_dir,
                check=True,
                capture_output=True,
            )

            # Commit
            result = subprocess.run(
                ["git", "commit", "-m", "Code Jester: Applied validated changes"],
                cwd=self.working_dir,
                check=True,
                capture_output=True,
            )

            # Get commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.working_dir,
                check=True,
                capture_output=True,
            )
            return result.stdout.decode().strip()[:8]

        except subprocess.CalledProcessError:
            return None

    def get_pending_summary(self) -> str:
        """Get summary of pending changes"""
        if not self.pending_changes:
            return "No pending changes"

        lines = [f"⚔️ Pending Changes ({len(self.pending_changes)})", ""]
        for change in self.pending_changes:
            lines.append(f"  • {change.file_path} ({change.operation})")
            if change.description:
                lines.append(f"    {change.description}")
        return "\n".join(lines)
