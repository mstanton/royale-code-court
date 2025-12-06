"""
Terminal Dashboard - Real-time observability using Rich
Shows events, metrics, and agent status in a beautiful terminal UI
"""

import asyncio
import sys
# Windows-specific keyboard handling since 'keyboard' lib requires root/admin often
if sys.platform == "win32":
    import msvcrt
from collections import deque
from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree
from rich import box

from ..core.models import AgentType, Event, EventType
from ..core.event_stream import EventBus
from ..core.metrics import MetricsCollector


# Agent emojis and colors
AGENT_STYLES = {
    AgentType.KING: {"emoji": "👑", "color": "gold1", "name": "King"},
    AgentType.JESTER: {"emoji": "🃏", "color": "bright_magenta", "name": "Jester"},
    AgentType.SCRIBE: {"emoji": "📜", "color": "bright_cyan", "name": "Scribe"},
    AgentType.WARRIOR: {"emoji": "⚔️", "color": "bright_red", "name": "Warrior"},
    AgentType.HUMAN: {"emoji": "👤", "color": "bright_green", "name": "Human"},
    AgentType.SYSTEM: {"emoji": "🖥️", "color": "bright_white", "name": "System"},
}


class TerminalDashboard:
    """
    Real-time terminal dashboard for Code Jester.
    Shows events, code, validation results, and metrics.
    """

    def __init__(
        self,
        event_bus: EventBus,
        metrics_collector: Optional[MetricsCollector] = None,
        max_events: int = 50,
        max_logs: int = 20,
    ):
        self.event_bus = event_bus
        self.metrics_collector = metrics_collector
        self.console = Console()
        self.max_events = max_events
        self.max_logs = max_logs

        # Event history
        self.events: Deque[Event] = deque(maxlen=max_events)
        self.logs: Deque[Dict[str, str]] = deque(maxlen=max_logs)

        # Current state
        self.current_code: str = ""
        self.current_language: str = "python"
        self.current_validation: Dict[str, Any] = {}
        self.current_thinking: str = ""
        self.agent_status: Dict[AgentType, str] = {}

        # Metrics
        self.total_executions = 0
        self.successful_executions = 0
        self.total_validations = 0
        self.total_validations = 0
        self.patterns_detected: List[str] = []
        self.opportunities: List[Dict] = []

        # UI state
        self._live: Optional[Live] = None
        self._running = False

        # Subscribe to all events
        event_bus.subscribe_all(self._handle_event)

    async def _handle_event(self, event: Event) -> None:
        """Handle incoming events and update state"""
        self.events.append(event)

        # Update based on event type
        if event.event_type == EventType.CODE_GENERATED:
            self.current_code = event.payload.get("code", "")[:2000]
            self.current_language = event.payload.get("language", "python")

        elif event.event_type == EventType.CODE_VALIDATED:
            self.current_validation = event.payload
            self.total_validations += 1
            patterns = event.payload.get("patterns_detected", [])
            self.patterns_detected.extend(patterns)

        elif event.event_type == EventType.EXECUTION_COMPLETE:
            self.total_executions += 1
            if event.payload.get("success", False):
                self.successful_executions += 1

        elif event.event_type == EventType.AGENT_THINKING:
            self.current_thinking = event.payload.get("message", "")
            self.agent_status[event.agent] = "thinking"

        elif event.event_type == EventType.LOG_MESSAGE:
            self.logs.append({
                "time": event.timestamp.strftime("%H:%M:%S"),
                "agent": event.agent.value,
                "message": event.payload.get("message", ""),
                "level": event.payload.get("level", "info"),
            })

        elif event.event_type == EventType.AGENT_STATUS_CHANGE:
            self.agent_status[event.agent] = event.payload.get("status", "idle")

        elif event.event_type == EventType.ANALYSIS_OPPORTUNITY:
            self.opportunities.append(event.payload)

    def _create_header(self) -> Panel:
        """Create the header panel"""
        title = Text()
        title.append("🃏 ", style="bright_magenta")
        title.append("Code Jester", style="bold bright_white")
        title.append(" - The Royal Court", style="dim")

        stats = Text()
        success_rate = (
            self.successful_executions / self.total_executions * 100
            if self.total_executions > 0
            else 0
        )
        stats.append(f"Executions: {self.total_executions} ", style="cyan")
        stats.append(f"| Success: {success_rate:.0f}% ", style="green")
        stats.append(f"| Validations: {self.total_validations}", style="yellow")

        content = Group(title, stats)
        return Panel(content, box=box.DOUBLE, style="bright_blue")

    def _create_event_stream(self) -> Panel:
        """Create the event stream panel"""
        table = Table(show_header=True, box=box.SIMPLE, expand=True)
        table.add_column("Time", style="dim", width=8)
        table.add_column("Agent", width=10)
        table.add_column("Event", style="cyan")
        table.add_column("Details", ratio=2)

        # Show recent events (newest first)
        for event in list(self.events)[-15:][::-1]:
            style = AGENT_STYLES.get(event.agent, {})
            agent_text = Text()
            agent_text.append(style.get("emoji", "•") + " ", style=style.get("color", "white"))
            agent_text.append(style.get("name", event.agent.value))

            # Format event type
            event_type = event.event_type.value.replace(".", " ").replace("_", " ").title()

            # Format details
            details = ""
            if event.event_type == EventType.CODE_GENERATED:
                details = f"{len(event.payload.get('code', ''))} chars"
            elif event.event_type == EventType.EXECUTION_COMPLETE:
                status = "✅" if event.payload.get("success") else "❌"
                time_ms = event.payload.get("execution_time_ms", 0)
                details = f"{status} {time_ms:.0f}ms"
            elif event.event_type == EventType.CODE_VALIDATED:
                tests = event.payload.get("tests_passed", 0)
                total = event.payload.get("tests_generated", 0)
                details = f"Tests: {tests}/{total}"
            elif event.event_type == EventType.PATTERN_DETECTED:
                details = event.payload.get("name", "")
            elif event.event_type == EventType.LOG_MESSAGE:
                details = event.payload.get("message", "")[:50]
            else:
                details = str(event.payload)[:50] if event.payload else ""

            table.add_row(
                event.timestamp.strftime("%H:%M:%S"),
                agent_text,
                event_type,
                details,
            )

        return Panel(
            table,
            title="📡 Event Stream",
            border_style="green",
            box=box.ROUNDED,
        )

    def _create_code_panel(self) -> Panel:
        """Create the current code panel"""
        if self.current_code:
            # Truncate for display
            code = self.current_code[:1500]
            if len(self.current_code) > 1500:
                code += "\n# ... (truncated)"

            syntax = Syntax(
                code,
                self.current_language,
                theme="monokai",
                line_numbers=True,
                word_wrap=True,
            )
            content = syntax
        else:
            content = Text("No code generated yet", style="dim")

        return Panel(
            content,
            title=f"👑 Generated Code ({self.current_language})",
            border_style="gold1",
            box=box.ROUNDED,
        )

    def _create_validation_panel(self) -> Panel:
        """Create the validation results panel"""
        if not self.current_validation:
            return Panel(
                Text("No validation results yet", style="dim"),
                title="🃏 Validation",
                border_style="magenta",
            )

        v = self.current_validation
        content = []

        # Status
        if v.get("overall_success"):
            content.append(Text("✅ PASSED", style="bold green"))
        else:
            content.append(Text("❌ FAILED", style="bold red"))

        content.append(Text(""))

        # Details table
        table = Table(show_header=False, box=None)
        table.add_column("", style="dim", width=15)
        table.add_column("")

        table.add_row("Syntax:", "✅" if v.get("syntax_valid") else "❌")
        table.add_row("Executes:", "✅" if v.get("executes") else "❌")
        table.add_row(
            "Tests:",
            f"{v.get('tests_passed', 0)}/{v.get('tests_generated', 0)} passed"
        )
        table.add_row("Complexity:", str(v.get("complexity_score", 0)))
        table.add_row(
            "Time:",
            f"{v.get('validation_time_ms', 0):.0f}ms"
        )

        content.append(table)

        # Patterns
        patterns = v.get("patterns_detected", [])
        if patterns:
            content.append(Text(""))
            content.append(Text("Patterns:", style="bold"))
            for p in patterns[:5]:
                content.append(Text(f"  • {p}", style="cyan"))

        # Issues
        issues = v.get("issues", [])
        if issues:
            content.append(Text(""))
            content.append(Text("Issues:", style="bold red"))
            for issue in issues[:3]:
                content.append(Text(f"  ⚠️ {issue[:60]}", style="yellow"))

        # Suggestions
        suggestions = v.get("suggestions", [])
        if suggestions:
            content.append(Text(""))
            content.append(Text("Suggestions:", style="bold cyan"))
            for sug in suggestions[:3]:
                content.append(Text(f"  💡 {sug[:60]}", style="dim"))

        return Panel(
            Group(*content),
            title="🃏 Validation Results",
            border_style="magenta",
            box=box.ROUNDED,
        )

    def _create_agent_status(self) -> Panel:
        """Create agent status panel"""
        content = []

        for agent_type in AgentType:
            style = AGENT_STYLES.get(agent_type, {})
            status = self.agent_status.get(agent_type, "idle")

            line = Text()
            line.append(style.get("emoji", "•") + " ", style=style.get("color", "white"))
            line.append(f"{style.get('name', agent_type.value):10}", style="bold")

            if status == "thinking":
                line.append(" 💭 ", style="yellow")
            elif status == "active":
                line.append(" ⚡ ", style="green")
            else:
                line.append(" 💤 ", style="dim")

            content.append(line)

        # Add current thinking
        if self.current_thinking:
            content.append(Text(""))
            content.append(Text("Current:", style="dim"))
            content.append(Text(f"  {self.current_thinking[:50]}", style="italic"))

        return Panel(
            Group(*content),
            title="🏰 Royal Court Status",
            border_style="blue",
            box=box.ROUNDED,
        )

    def _create_logs_panel(self) -> Panel:
        """Create logs panel"""
        content = []

        for log in list(self.logs)[-10:][::-1]:
            style = AGENT_STYLES.get(AgentType(log["agent"]), {})
            line = Text()
            line.append(f"[{log['time']}] ", style="dim")
            line.append(style.get("emoji", "•") + " ", style=style.get("color", "white"))

            level_style = {
                "info": "white",
                "warning": "yellow",
                "error": "red",
            }.get(log["level"], "white")

            line.append(log["message"][:60], style=level_style)
            content.append(line)

        if not content:
            content.append(Text("No logs yet", style="dim"))

        return Panel(
            Group(*content),
            title="📋 Logs",
            border_style="cyan",
            box=box.ROUNDED,
        )

    def _create_opportunities_panel(self) -> Panel:
        """Create opportunities panel"""
        if not self.opportunities:
            return Panel(
                Text("No pending analysis opportunities", style="dim"),
                title="🔍 Opportunities",
                border_style="yellow",
                box=box.ROUNDED,
            )

        table = Table(show_header=True, box=None, expand=True)
        table.add_column("File", style="cyan")
        table.add_column("Trigger", style="red")
        table.add_column("Suggestion", style="dim")

        for opp in list(self.opportunities)[-5:]:
            table.add_row(
                opp.get("file", "unknown"),
                opp.get("trigger", ""),
                opp.get("suggestion", "")
            )

        return Panel(
            title=f"🔍 Opportunities ({len(self.opportunities)}) [Press 'a' to approve]",
            border_style="yellow",
            box=box.ROUNDED,
        )

    def _create_rhythm_panel(self) -> Panel:
        """Create rhythmic patterns panel (Sparklines)"""
        if not self.metrics_collector:
            return Panel(Text("Metrics not available", style="dim"), title="📈 Rhythm")

        # 1. Event Activity (Last 60 mins)
        activity_data = self.metrics_collector.get_event_volume_history(minutes=60, bucket_size_minutes=2)
        # Normalize for display (simple bar characters)
        max_val = max(activity_data) if activity_data else 1
        bars = [" ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
        
        activity_str = ""
        for val in activity_data:
             idx = min(len(bars) - 1, int((val / max_val) * (len(bars) - 1))) if max_val > 0 else 0
             activity_str += bars[idx]

        # 2. Complexity Trend
        complexity_data = self.metrics_collector.get_metric_average_history("complexity", minutes=60, bucket_size_minutes=5)
        # Sparkline for complexity
        comp_str = ""
        max_comp = max(complexity_data) if complexity_data else 1
        for val in complexity_data:
             idx = min(len(bars) - 1, int((val / max_comp) * (len(bars) - 1))) if max_comp > 0 else 0
             comp_str += bars[idx]

        grid = Table.grid(expand=True)
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)
        
        grid.add_row(
            Panel(Text(activity_str, style="green"), title="Activity (1h)", box=None),
            Panel(Text(comp_str, style="red"), title="Complexity (1h)", box=None)
        )

        return Panel(
            grid,
            title="📈 Code Rhythm",
            border_style="blue",
            box=box.ROUNDED,
        )

    def _create_layout(self) -> Layout:
        """Create the dashboard layout"""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=5),
            Layout(name="main"),
            Layout(name="footer", size=12),
        )

        layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right"),
        )

        layout["left"].split_column(
            Layout(name="events", ratio=2),
            Layout(name="code", ratio=3),
        )

        layout["right"].split_column(
            Layout(name="validation", ratio=3),
            Layout(name="rhythm", ratio=2),
            Layout(name="opportunities", ratio=2),
            Layout(name="agents", ratio=2),
        )

        return layout

    def render(self) -> Layout:
        """Render the dashboard"""
        layout = self._create_layout()

        layout["header"].update(self._create_header())
        layout["events"].update(self._create_event_stream())
        layout["code"].update(self._create_code_panel())
        layout["validation"].update(self._create_validation_panel())
        layout["rhythm"].update(self._create_rhythm_panel())
        layout["opportunities"].update(self._create_opportunities_panel())
        layout["agents"].update(self._create_agent_status())
        layout["footer"].update(self._create_logs_panel())

        return layout

    async def run(self, refresh_rate: float = 0.5) -> None:
        """Run the dashboard with live updates"""
        self._running = True

        with Live(
            self.render(),
            console=self.console,
            refresh_per_second=int(1 / refresh_rate),
            screen=True,
        ) as live:
            self._live = live
            while self._running:
                live.update(self.render())
                
                # Check for input (Windows only for now)
                if sys.platform == "win32" and msvcrt.kbhit():
                    key = msvcrt.getch()
                    await self._handle_input(key)
                
                await asyncio.sleep(refresh_rate)

    async def _handle_input(self, key_bytes: bytes) -> None:
        """Handle keyboard input"""
        try:
            key = key_bytes.decode('utf-8').lower()
        except:
            return

        if key == 'a':
            # Approve pending opportunity
            if self.opportunities:
                opp = self.opportunities.pop() # LIFO for now (approve newest)
                await self.event_bus.emit(Event(
                    event_type=EventType.ANALYSIS_APPROVED,
                    agent=AgentType.HUMAN,
                    payload=opp
                ))

    def stop(self) -> None:
        """Stop the dashboard"""
        self._running = False

    def print_simple(self) -> None:
        """Print a simple, non-live version of the dashboard"""
        self.console.print(self._create_header())
        self.console.print(self._create_event_stream())
        self.console.print(self._create_code_panel())
        self.console.print(self._create_validation_panel())


class SimpleLogDisplay:
    """
    Simpler log-based display for non-interactive use.
    Prints events as they happen.
    """

    def __init__(self, event_bus: EventBus):
        self.console = Console()
        event_bus.subscribe_all(self._handle_event)

    async def _handle_event(self, event: Event) -> None:
        """Print events as they happen"""
        style = AGENT_STYLES.get(event.agent, {})
        emoji = style.get("emoji", "•")
        color = style.get("color", "white")
        name = style.get("name", event.agent.value)

        # Format timestamp
        time_str = event.timestamp.strftime("%H:%M:%S.%f")[:-3]

        # Format event type
        event_type = event.event_type.value.replace("_", " ").title()

        # Build message
        msg = Text()
        msg.append(f"[{time_str}] ", style="dim")
        msg.append(f"{emoji} {name:8} ", style=color)
        msg.append(f"│ {event_type:25} ", style="cyan")

        # Add payload summary
        payload = event.payload
        if event.event_type == EventType.CODE_GENERATED:
            msg.append(f"({len(payload.get('code', ''))} chars)", style="green")
        elif event.event_type == EventType.EXECUTION_COMPLETE:
            status = "✅" if payload.get("success") else "❌"
            msg.append(f"{status} {payload.get('execution_time_ms', 0):.0f}ms", style="yellow")
        elif event.event_type == EventType.CODE_VALIDATED:
            status = "✅" if payload.get("overall_success") else "❌"
            msg.append(f"{status}", style="magenta")
        elif event.event_type == EventType.LOG_MESSAGE:
            msg.append(payload.get("message", ""), style="dim")
        elif event.event_type == EventType.AGENT_THINKING:
            msg.append(payload.get("message", ""), style="italic")

        self.console.print(msg)
