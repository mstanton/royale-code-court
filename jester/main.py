"""
Code Jester - Main Entry Point
The Royal Court orchestrator and CLI
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .core.event_stream import EventBus, EventStream, get_event_bus
from .core.models import AgentType, EventType
from .core.metrics import MetricsCollector
from .agents.jester import JesterAgent
from .agents.scribe import ScribeAgent
from .execution.executor import CodeExecutor
from .integrations.ollama_client import OllamaClient, KingAgent
from .integrations.claude_code import ClaudeCodeIntegration
from .observability.terminal_ui import TerminalDashboard, SimpleLogDisplay

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
        ollama_model: str = "qwen2.5-coder:7b",
        ollama_url: str = "http://localhost:11434",
        enable_scribe: bool = True,
        enable_warrior: bool = False,
        working_dir: Optional[str] = None,
    ):
        # Core event system
        self.event_bus = get_event_bus()
        self.metrics = MetricsCollector(
            storage_path=Path("storage/metrics.db")
        )

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
        self.warrior: Optional[ClaudeCodeIntegration] = None
        if enable_warrior:
            self.warrior = ClaudeCodeIntegration(
                self.event_bus,
                working_dir=working_dir,
            )

        # Dashboard
        self.dashboard: Optional[TerminalDashboard] = None
        self.simple_log: Optional[SimpleLogDisplay] = None

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
            self.dashboard = TerminalDashboard(self.event_bus)
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
    model: str = typer.Option("qwen2.5-coder:7b", "--model", "-m", help="Ollama model"),
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
def dashboard(
    model: str = typer.Option("qwen2.5-coder:7b", "--model", "-m", help="Ollama model"),
    scribe: bool = typer.Option(True, "--scribe/--no-scribe", help="Enable Scribe agent"),
):
    """Run the interactive dashboard"""

    async def run():
        court = RoyalCourt(ollama_model=model, enable_scribe=scribe)
        await court.start(use_dashboard=True)

        try:
            await court.interactive_session()
        except KeyboardInterrupt:
            pass
        finally:
            await court.stop()

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


def main():
    """Main entry point"""
    app()


if __name__ == "__main__":
    main()
