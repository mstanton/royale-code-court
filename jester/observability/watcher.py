"""
Realm Watcher - The eyes of the Royal Court
Monitors the filesystem for changes and calculates deterministic metrics.
"""

import ast
import asyncio
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Set

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from ..core.event_stream import EventStream
from ..core.models import AgentType, EventType


@dataclass
class FileMetrics:
    """Deterministic metrics for a single file"""
    path: str
    line_count: int
    complexity: int
    function_count: int
    class_count: int
    last_modified: float


class MetricCalculator:
    """Calculates metrics using AST (free/local)"""
    
    @staticmethod
    def analyze_file(path: Path) -> Optional[FileMetrics]:
        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content)
            
            # Basic AST traversal
            func_count = 0
            class_count = 0
            complexity = 1  # Base complexity
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_count += 1
                    complexity += 1
                elif isinstance(node, ast.ClassDef):
                    class_count += 1
                elif isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.AsyncWith)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1
            
            return FileMetrics(
                path=str(path),
                line_count=len(content.splitlines()),
                complexity=complexity,
                function_count=func_count,
                class_count=class_count,
                last_modified=time.time()
            )
        except Exception:
            # Squelch errors for non-python files or parse errors
            return None


class RealmWatcher(FileSystemEventHandler):
    """
    Watches a directory (Realm) for changes.
    Calculates metrics on save and emits events.
    """

    def __init__(self, event_stream: EventStream, root_path: str):
        self.event_stream = event_stream
        self.root_path = Path(root_path).resolve()
        self.observer = Observer()
        self._last_events: Dict[str, float] = {}
        self._debounce_seconds = 1.0
        self._loop = None

    def start(self):
        """Start watching"""
        self._loop = asyncio.get_running_loop()
        self.observer.schedule(self, str(self.root_path), recursive=True)
        self.observer.start()
        
        # Initial scan
        asyncio.create_task(self._initial_scan())

    def stop(self):
        """Stop watching"""
        self.observer.stop()
        self.observer.join()

    async def _initial_scan(self):
        """Perform initial scan of the realm"""
        for root, _, files in os.walk(self.root_path):
            if ".git" in root or "__pycache__" in root or ".venv" in root:
                continue
                
            for file in files:
                if file.endswith(".py"):
                    await self._process_file(Path(root) / file, is_initial=True)

    def on_modified(self, event: FileSystemEvent):
        if event.is_directory or not event.src_path.endswith(".py"):
            return
        
        # Debounce
        now = time.time()
        last = self._last_events.get(event.src_path, 0)
        if now - last < self._debounce_seconds:
            return
        self._last_events[event.src_path] = now

        # Run async processing in the event loop
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self._process_file(Path(event.src_path)),
                self._loop
            )

    async def _process_file(self, path: Path, is_initial: bool = False):
        """Process a changed file"""
        metrics = MetricCalculator.analyze_file(path)
        if not metrics:
            return

        # Emit metrics updated event
        await self.event_stream.emit(
            EventType.METRICS_UPDATED,
            {
                "file": str(path.relative_to(self.root_path)),
                "absolute_path": str(path.absolute()),
                "metrics": {
                    "loc": metrics.line_count,
                    "complexity": metrics.complexity,
                    "functions": metrics.function_count,
                    "classes": metrics.class_count
                },
                "is_initial": is_initial
            }
        )
        
        # Check for hotspots (simple rule-based gating)
        # Rule: Complexity > 20 or LOC > 200 is a "Hotspot"
        if not is_initial:
            if metrics.complexity > 20 or metrics.line_count > 200:
                await self.event_stream.emit(
                    EventType.ANALYSIS_OPPORTUNITY,
                    {
                        "trigger": "High Complexity",
                        "file": str(path.relative_to(self.root_path)),
                        "absolute_path": str(path.absolute()),
                        "details": f"Complexity: {metrics.complexity}, LOC: {metrics.line_count}",
                        "suggestion": "Consider refactoring into smaller components."
                    }
                )
