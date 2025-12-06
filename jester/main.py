"""
Code Jester - Main Entry Point
The Royal Court orchestrator and CLI
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .core.event_stream import EventBus, EventStream, get_event_bus
from .core.models import AgentType, EventType
from .agents.base_agent import BaseAgent
from .core.metrics import MetricsCollector
from .agents.jester import JesterAgent
from .core.scratchpad import ScratchPad
from .analysis.trend_analyzer import TrendAnalyzer
from .config import JesterConfig
from .agents.scribe import ScribeAgent
from .execution.executor import CodeExecutor
from .integrations.ollama_client import OllamaClient, KingAgent
from .integrations.claude_code import ClaudeCodeIntegration
from .integrations.open_code import OpenCodeIntegration
from .observability.terminal_ui import TerminalDashboard, SimpleLogDisplay
from .observability.watcher import RealmWatcher

app = typer.Typer(
    name="jester",
    help="Code Jester - AI-Assisted Development Intelligence System",
    add_completion=False,
)

console = Console()


class RoyalCourt:
    """
    The Royal Court - Main orchestrator for all agents.
    Coordinates the feedback loop between code generation, validation, and learning.
    """

    def __init__(
        self,
        ollama_model: str = "gemma3:4b",
        ollama_url: str = "http://localhost:11434",
        enable_scribe: bool = True,
        enable_warrior: bool = True,
        working_dir: Optional[str] = "./working_dir",
    ):
        # Core event system
        self.event_bus = get_event_bus()
        
        # Load config to check preferences
        self.config = JesterConfig.load()
        if ollama_model == "gemma3:4b" and self.config.model: # Override default if config present
             ollama_model = self.config.model

        self.metrics = MetricsCollector(
            storage_path=Path("storage/metrics.db")
        )
        self.scratchpad = ScratchPad(storage_path=Path("storage/metrics.db"))
        self.trend_analyzer = TrendAnalyzer(storage_path=Path("storage/metrics.db"))

        # Create human event stream for user input
        self.human_stream = EventStream(self.event_bus, AgentType.HUMAN)

        # Initialize agents
        self.executor = CodeExecutor(EventStream(self.event_bus, AgentType.JESTER))

        # The Jester (always enabled - core validator)
        self.jester = JesterAgent(
            self.event_bus,
            executor=self.executor,
            metrics=self.metrics,
        )

        # The King (Ollama code generator)
        self.ollama = OllamaClient(base_url=ollama_url, default_model=ollama_model)
        self.king = KingAgent(self.event_bus, ollama_client=self.ollama, model=ollama_model)

        # The Scribe (knowledge keeper)
        self.scribe: Optional[ScribeAgent] = None
        if enable_scribe:
            self.scribe = ScribeAgent(self.event_bus)

        # The Warrior (code integrator)
        self.warrior: Optional[BaseAgent] = None
        if enable_warrior:
            if self.config.warrior_provider == "claude-code":
                self.warrior = ClaudeCodeIntegration(
                    self.event_bus,
                    working_dir=working_dir,
                )
            else:
                # Default to Open Code (Linear Warrior)
                self.warrior = OpenCodeIntegration(
                    self.event_bus,
                    ollama_agent=self.king,
                    working_dir=working_dir,
                )

        # Dashboard
        self.dashboard: Optional[TerminalDashboard] = None
        self.simple_log: Optional[SimpleLogDisplay] = None

        # Subscribe event persister
        self.event_bus.subscribe_all(self._persist_event)

    async def _persist_event(self, event) -> None:
        """Persist event to SQLite for cross-process visibility"""
        # Skip if already from persistence to avoid loops
        if hasattr(event, "from_persistence") and event.from_persistence:
            return

        # Skip high-volume internal events that don't need history
        if event.event_type in [EventType.EXECUTION_OUTPUT]:
            return

        try:
            self.metrics.record_event(event.to_dict())
        except Exception as e:
            # Don't let logging failures crash the app
            pass

    async def start(self, use_dashboard: bool = True) -> None:
        """Start all agents"""
        console.print(Panel(
            Text.assemble(
                ("🃏 ", "bright_magenta"),
                ("Code Jester", "bold white"),
                (" - The Royal Court is assembling...", "dim"),
            ),
            border_style="bright_blue",
        ))

        # Start agents
        self.jester.start()
        self.king.start()
        if self.scribe:
            self.scribe.start()
        if self.warrior:
            self.warrior.start()

        # Check Ollama availability
        if await self.king.is_available():
            console.print("  👑 King (Ollama) - [green]Online[/green]")
        else:
            console.print("  👑 King (Ollama) - [yellow]Offline[/yellow] (will use validation only)")

        console.print("  🃏 Jester (Validator) - [green]Online[/green]")
        if self.scribe:
            console.print("  📜 Scribe (Knowledge) - [green]Online[/green]")
        if self.warrior:
            console.print("  ⚔️ Warrior (Integrator) - [green]Online[/green]")

        # Start dashboard or simple log
        if use_dashboard:
            self.dashboard = TerminalDashboard(self.event_bus, metrics_collector=self.metrics)
        else:
            self.simple_log = SimpleLogDisplay(self.event_bus)

        console.print()

    async def stop(self) -> None:
        """Stop all agents"""
        if self.dashboard:
            self.dashboard.stop()

        self.jester.stop()
        self.king.stop()
        if self.scribe:
            self.scribe.stop()
        if self.warrior:
            self.warrior.stop()

        await self.ollama.close()

    async def generate_and_validate(
        self,
        prompt: str,
        language: str = "python",
    ) -> dict:
        """
        Main workflow: Generate code and validate it.
        Returns the validation result.
        """
        # Emit human input
        await self.human_stream.emit(
            EventType.HUMAN_INPUT,
            {"prompt": prompt, "language": language},
        )

        # Generate code
        result = await self.king.generate_code(prompt, language)

        # Validate (Jester will pick up the CODE_GENERATED event automatically)
        validation = await self.jester.validate(result.code, language)

        return {
            "code": result.code,
            "language": result.language,
            "validation": validation,
            "generation_time_ms": result.generation_time_ms,
        }

    async def validate_code(self, code: str, language: str = "python") -> dict:
        """
        Validate existing code (without generation).
        """
        # Emit code received
        await EventStream(self.event_bus, AgentType.SYSTEM).emit(
            EventType.CODE_RECEIVED,
            {"code": code, "language": language},
        )

        # Validate
        validation = await self.jester.validate(code, language)

        return {
            "code": code,
            "language": language,
            "validation": validation,
        }

    async def interactive_session(self) -> None:
        """Run an interactive session with the dashboard"""
        if self.dashboard:
            # Run dashboard in background
            dashboard_task = asyncio.create_task(self.dashboard.run())

            try:
                # Wait for user to close
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                self.dashboard.stop()
                await dashboard_task

    def get_metrics(self) -> dict:
        """Get current metrics"""
        return {
            "execution_stats": self.metrics.get_execution_stats(),
            "pattern_stats": self.metrics.get_pattern_stats(),
            "recent": self.metrics.get_recent_metrics(),
        }


@app.command()
def validate(
    code: str = typer.Argument(None, help="Code to validate (or use --file)"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File to validate"),
    language: str = typer.Option("python", "--lang", "-l", help="Programming language"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Validate code using the Jester"""

    if file:
        if not file.exists():
            console.print(f"[red]Error:[/red] File not found: {file}")
            raise typer.Exit(1)
        code = file.read_text()

    if not code:
        console.print("[red]Error:[/red] No code provided")
        raise typer.Exit(1)

    async def run():
        court = RoyalCourt(enable_scribe=False)
        await court.start(use_dashboard=False)

        result = await court.validate_code(code, language)

        if json_output:
            import json
            print(json.dumps({
                "syntax_valid": result["validation"].syntax_valid,
                "executes": result["validation"].executes,
                "tests_passed": result["validation"].tests_passed,
                "tests_failed": result["validation"].tests_failed,
                "patterns": result["validation"].patterns_detected,
                "issues": result["validation"].issues,
                "overall_success": result["validation"].overall_success,
            }, indent=2))
        else:
            console.print(court.jester.format_report(result["validation"]))

        await court.stop()

    asyncio.run(run())


@app.command()
def generate(
    prompt: str = typer.Argument(..., help="What to generate"),
    language: str = typer.Option("python", "--lang", "-l", help="Programming language"),
    model: str = typer.Option("gemma3:4b", "--model", "-m", help="Ollama model"),
    validate_code: bool = typer.Option(True, "--validate/--no-validate", help="Validate after generation"),
):
    """Generate code using the King (Ollama) and validate with the Jester"""

    async def run():
        court = RoyalCourt(ollama_model=model)
        await court.start(use_dashboard=False)

        try:
            if not await court.king.is_available():
                console.print("[red]Error:[/red] Ollama is not running. Start it with: ollama serve")
                raise typer.Exit(1)

            console.print(f"[cyan]Generating {language} code...[/cyan]")
            result = await court.generate_and_validate(prompt, language)

            console.print()
            console.print(Panel(
                result["code"],
                title=f"👑 Generated Code ({result['language']})",
                border_style="gold1",
            ))

            if validate_code:
                console.print()
                console.print(court.jester.format_report(result["validation"]))

        finally:
            await court.stop()

    asyncio.run(run())


@app.command()
def optimize(
    prompt: str = typer.Argument(..., help="What to generate and optimize"),
    language: str = typer.Option("python", "--lang", "-l", help="Programming language"),
    model: str = typer.Option("gemma3:4b", "--model", "-m", help="Ollama model"),
    max_attempts: int = typer.Option(5, "--attempts", "-n", help="Max optimization attempts"),
    threshold_ms: float = typer.Option(500.0, "--threshold", "-t", help="Performance threshold (ms)"),
):
    """Iteratively generate and optimize code for performance"""

    async def run():
        court = RoyalCourt(ollama_model=model)
        await court.start(use_dashboard=False)

        try:
            if not await court.king.is_available():
                console.print("[red]Error:[/red] Ollama is not running.")
                raise typer.Exit(1)

            console.print(Panel(
                f"Task: {prompt}\nTarget: < {threshold_ms}ms execution time",
                title="🚀 Code Optimization Loop",
                border_style="green"
            ))

            feedback_history = []
            best_code = None
            best_time = float('inf')

            for i in range(max_attempts):
                console.print(f"\n[bold cyan]Attempt {i+1}/{max_attempts}[/bold cyan]")
                
                # Generate
                if i == 0:
                     # First attempt
                     result = await court.king.generate_code(prompt, language)
                else:
                     # Optimization attempt
                     console.print("  🔄 Optimizing based on feedback...")
                     result = await court.king.generate_code(prompt, language, feedback_history=feedback_history)

                console.print(f"  ✨ Generated {len(result.code)} chars")

                # Validate
                validation = await court.jester.validate(result.code, language)
                console.print(court.jester.format_report(validation))

                time_ms = validation.execution_stats.get("time_ms", 0)
                
                # Check success
                if validation.overall_success:
                    if time_ms < best_time:
                         best_time = time_ms
                         best_code = result.code
                    
                    if time_ms <= threshold_ms:
                        console.print(f"\n[bold green]✅ Success! Optimized code runs in {time_ms:.2f}ms[/bold green]")
                        console.print(Panel(result.code, title="🏆 Optimized Code", border_style="green"))
                        break
                    else:
                        console.print(f"  ⚠️  Too slow ({time_ms:.2f}ms > {threshold_ms}ms). Retrying...")
                        feedback_history.append({
                            "code": result.code,
                            "feedback": validation.feedback,
                            "metrics": validation.execution_stats
                        })
                else:
                    console.print("  ❌ Validation failed. Retrying with error feedback...")
                    feedback_history.append({
                        "code": result.code,
                        "feedback": validation.feedback,
                        "metrics": validation.execution_stats
                    })

            else:
                console.print(f"\n[bold yellow]⚠️  Max attempts reached without hitting threshold.[/bold yellow]")
                if best_code:
                     console.print(f"Best run: {best_time:.2f}ms")
                     console.print(Panel(best_code, title="Best Attempt", border_style="yellow"))

        finally:
            await court.stop()

    asyncio.run(run())


@app.command()
def dashboard(
    model: str = typer.Option("gemma3:4b", "--model", "-m", help="Ollama model"),
    scribe: bool = typer.Option(True, "--scribe/--no-scribe", help="Enable Scribe agent"),
):
    """Run the interactive dashboard"""

    async def run():
        court = RoyalCourt(ollama_model=model, enable_scribe=scribe)
        await court.start(use_dashboard=True)

        try:
            # Start dashboard polling in background
            polling_task = asyncio.create_task(_poll_events(court))
            await court.interactive_session()
        except KeyboardInterrupt:
            pass
        finally:
            if polling_task:
                polling_task.cancel()
            await court.stop()

    async def _poll_events(court: RoyalCourt):
        """Poll for new events from other processes"""
        last_id = 0
        from .core.models import Event, EventType, AgentType

        while True:
            try:
                # Get new events
                new_events = court.metrics.get_new_events(last_id)
                for event_data in new_events:
                    last_id = max(last_id, event_data["id"])
                    
                    # Convert string timestamp back to datetime object
                    timestamp_str = event_data["timestamp"]
                    # Handle both with and without milliseconds for robustness
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                    except ValueError:
                         # Fallback if isoformat fails
                         timestamp = datetime.now()

                    # Reconstruct event
                    event = Event(
                        event_type=EventType(event_data["event_type"]),
                        agent=AgentType(event_data["agent"]),
                        payload=event_data["payload"],
                        event_id=event_data["event_id"],
                        timestamp=timestamp,
                        session_id=event_data["session_id"]
                    )
                    
                    # Mark as from persistence to avoid infinite loop
                    event.from_persistence = True
                    
                    # Emit to local bus (skip local handlers to avoid double processing if needed)
                    # But here we WANT local handlers (Dashboard) to see it.
                    # The recursion check in _persist_event prevents writing it back.
                    await court.event_bus.emit(event)

            except Exception as e:
                # console.print(f"[dim]Polling error: {e}[/dim]")
                pass
            
            await asyncio.sleep(0.5)

    asyncio.run(run())


@app.command()
def demo():
    """Run a demo of the validation pipeline"""

    demo_code = '''
def fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)

def is_prime(n):
    """Check if a number is prime."""
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

# Test the functions
print(f"Fibonacci(10) = {fibonacci(10)}")
print(f"Is 17 prime? {is_prime(17)}")
'''

    async def run():
        court = RoyalCourt(enable_scribe=True)
        await court.start(use_dashboard=False)

        console.print(Panel(
            "[bold]Running Demo[/bold]\n"
            "This demo validates a sample Python file with two functions.",
            title="🃏 Code Jester Demo",
            border_style="bright_magenta",
        ))

        console.print()
        console.print(Panel(demo_code, title="📝 Sample Code", border_style="cyan"))
        console.print()

        console.print("[cyan]Validating...[/cyan]")
        result = await court.validate_code(demo_code)

        console.print()
        console.print(court.jester.format_report(result["validation"]))

        if court.scribe:
            console.print()
            console.print(court.scribe.format_insights_report())

        await court.stop()

    asyncio.run(run())


@app.command()
def repl():
    """Start an interactive REPL for code validation"""

    async def run():
        court = RoyalCourt(enable_scribe=True)
        await court.start(use_dashboard=False)

        console.print(Panel(
            "[bold]Code Jester REPL[/bold]\n"
            "Enter Python code to validate. Use :q to quit, :g <prompt> to generate.\n"
            "Multi-line input: end with a blank line.",
            title="🃏 Interactive Mode",
            border_style="bright_magenta",
        ))

        try:
            while True:
                console.print()
                console.print("[cyan]>>> [/cyan]", end="")

                # Read input (multi-line support)
                lines = []
                try:
                    while True:
                        line = input()
                        if line.strip() == "":
                            break
                        lines.append(line)
                except EOFError:
                    break

                if not lines:
                    continue

                input_text = "\n".join(lines)

                # Handle commands
                if input_text.strip() == ":q":
                    break
                elif input_text.strip().startswith(":g "):
                    prompt = input_text[3:].strip()
                    if await court.king.is_available():
                        result = await court.generate_and_validate(prompt)
                        console.print(Panel(result["code"], title="Generated", border_style="gold1"))
                        console.print(court.jester.format_report(result["validation"]))
                    else:
                        console.print("[yellow]Ollama not available[/yellow]")
                else:
                    result = await court.validate_code(input_text)
                    console.print(court.jester.format_report(result["validation"]))

        except KeyboardInterrupt:
            pass
        finally:
            console.print("\n[dim]Goodbye from the Royal Court![/dim]")
            await court.stop()

    asyncio.run(run())


@app.command()
def watch(
    path: Path = typer.Argument(None, help="Path to watch (overrides config)"),
    config: Path = typer.Option(None, "--config", "-c", help="Path to jester.toml"),
    model: str = typer.Option(None, "--model", "-m", help="Ollama model (overrides config)"),
):
    """Start the Passive Observer (Multi-Realm Watcher)"""
    
    # Load configuration
    jester_config = JesterConfig.load(config)
    
    # Overrides
    target_model = model or jester_config.model
    
    # Determine realms to watch
    realms_to_watch = []
    
    if path:
        # CLI path overrides everything - watch single realm
        if not path.exists():
            console.print(f"[red]Error:[/red] Path not found: {path}")
            raise typer.Exit(1)
        realms_to_watch.append(("Current", path))
    elif jester_config.realms:
        # Use config realms
        for r in jester_config.realms:
            realms_to_watch.append((r.name, r.path))
    else:
        # Default to current dir
        realms_to_watch.append(("Current", Path(".")))

    async def run():
        court = RoyalCourt(ollama_model=target_model, enable_scribe=True)
        # Enable persisted events so dashboard can see watcher events
        await court.start(use_dashboard=True)
        
        watchers = []
        console.print(Panel(f"Starting {len(realms_to_watch)} Realm Watchers...", style="green"))
        
        for name, r_path in realms_to_watch:
            if not r_path.exists():
                console.print(f"[yellow]Warning:[/yellow] Realm path not found: {r_path}")
                continue
                
            watcher = RealmWatcher(court.human_stream, str(r_path), realm_name=name)
            watcher.start()
            watchers.append(watcher)
            console.print(f"  👁️  Watching realm: [bold]{name}[/bold] ({r_path})")

        try:
            # We run dashboard polling here too, so the dashboard updates
            polling_task = asyncio.create_task(_poll_events(court))
            
            # Interactive session (Dashboard)
            await court.interactive_session()
            
        except KeyboardInterrupt:
            pass
        finally:
            if polling_task:
                polling_task.cancel()
            
            for w in watchers:
                w.stop()
                
            await court.stop()

    asyncio.run(run())


@app.command()
def lab():
    """Enter the Laboratory (Interactive Scratchpad)"""
    
    async def run():
        court = RoyalCourt(enable_scribe=False)
        await court.start(use_dashboard=False)
        
        console.print(Panel(
            "[bold]Welcome to The Laboratory[/bold]\n"
            "Commands:\n"
            "  save <name> <code>   : Save code snippet\n"
            "  run <name>           : Execute snippet\n"
            "  list                 : List snippets\n"
            "  trend                : Show performance trends\n"
            "  exit                 : Leave the lab",
            title="🧪 Jester Lab",
            border_style="cyan"
        ))

        while True:
            try:
                console.print("\n[cyan]🧪 lab>[/cyan] ", end="")
                cmd_line = input().strip()
                if not cmd_line:
                    continue
                
                parts = cmd_line.split(maxsplit=1)
                cmd = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""

                if cmd == "exit":
                    break
                
                elif cmd == "list":
                    snippets = court.scratchpad.list_snippets()
                    if not snippets:
                        console.print("No snippets found.")
                    else:
                        for s in snippets:
                            console.print(f"• [bold]{s['name']}[/bold] ({s['language']}) - Runs: {s['run_count']}")
                            
                elif cmd == "save":
                    if not args:
                        console.print("[red]Usage: save <name>[/red]")
                        continue
                    
                    name = args
                    console.print(f"Enter code for '{name}' (end with empty line):")
                    lines = []
                    while True:
                        line = input()
                        if line == "":
                            break
                        lines.append(line)
                    code = "\n".join(lines)
                    
                    court.scratchpad.save_snippet(name, code)
                    console.print(f"✅ Saved '{name}'")

                elif cmd == "run":
                    if not args:
                        console.print("[red]Usage: run <name>[/red]")
                        continue
                        
                    name = args
                    snippet = court.scratchpad.get_snippet(name)
                    if not snippet:
                        console.print(f"[red]Snippet '{name}' not found[/red]")
                        continue
                        
                    console.print(f"[dim]Running '{name}'...[/dim]")
                    result = await court.executor.execute(snippet.code, language=snippet.language)
                    
                    # Record result in scratchpad
                    court.scratchpad.record_run(name, result.output or result.error)
                    
                    if result.success:
                        console.print(Panel(result.output, title=f"Output ({result.execution_time_ms:.2f}ms)", border_style="green"))
                    else:
                        console.print(Panel(result.error, title="Error", border_style="red"))

                elif cmd == "trend":
                     # Show recent trend
                     trend = court.trend_analyzer.get_recent_performance_trend()
                     console.print(Panel(str(trend), title="Recent Performance Trend", border_style="magenta"))

                else:
                    console.print(f"[red]Unknown command: {cmd}[/red]")

            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        
        await court.stop()

    asyncio.run(run())


def main():
    """Main entry point"""
    app()


if __name__ == "__main__":
    main()
