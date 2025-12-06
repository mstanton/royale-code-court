#!/usr/bin/env python3
"""
Feedback Loop Example
Demonstrates the real-time feedback loop with LLM integration.

This example shows how the King (Ollama) and Jester work together:
1. Human provides a prompt
2. King generates code
3. Jester validates in real-time
4. Results stream back to the human

Run with: python examples/feedback_loop.py
Requires Ollama running: ollama serve
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.syntax import Syntax
from rich import box

from jester.core.event_stream import get_event_bus, EventStream
from jester.core.models import AgentType, EventType
from jester.core.metrics import MetricsCollector
from jester.agents.jester import JesterAgent
from jester.agents.scribe import ScribeAgent
from jester.execution.executor import CodeExecutor
from jester.integrations.ollama_client import OllamaClient, KingAgent
from jester.observability.terminal_ui import SimpleLogDisplay

console = Console()


class FeedbackLoopDemo:
    """Interactive feedback loop demonstration."""

    def __init__(self):
        self.event_bus = get_event_bus()
        self.metrics = MetricsCollector(storage_path=Path("storage/feedback_metrics.db"))

        # Initialize agents
        self.executor = CodeExecutor(EventStream(self.event_bus, AgentType.JESTER))
        self.jester = JesterAgent(self.event_bus, executor=self.executor, metrics=self.metrics)
        self.scribe = ScribeAgent(self.event_bus)

        # King (Ollama) - will check availability
        self.ollama = OllamaClient()
        self.king = KingAgent(self.event_bus, ollama_client=self.ollama)

        # State
        self.current_code = ""
        self.current_validation = None
        self.ollama_available = False

    async def start(self):
        """Start all agents."""
        self.jester.start()
        self.scribe.start()
        self.king.start()

        # Check Ollama
        self.ollama_available = await self.king.is_available()

    async def stop(self):
        """Stop all agents."""
        self.jester.stop()
        self.scribe.stop()
        self.king.stop()
        await self.ollama.close()

    async def generate_and_validate(self, prompt: str):
        """Generate code from prompt and validate it."""
        if not self.ollama_available:
            console.print("[red]Ollama not available. Start with: ollama serve[/red]")
            return None

        console.print(f"[cyan]👑 King is generating code...[/cyan]")

        # Generate
        result = await self.king.generate_code(prompt)
        self.current_code = result.code

        console.print(f"[green]Generated {len(result.code)} chars in {result.generation_time_ms:.0f}ms[/green]")

        # Show code
        console.print()
        console.print(Panel(
            Syntax(result.code, "python", theme="monokai", line_numbers=True),
            title="👑 Generated Code",
            border_style="gold1",
        ))

        # Validate
        console.print()
        console.print("[cyan]🃏 Jester is validating...[/cyan]")

        validation = await self.jester.validate(result.code, result.language)
        self.current_validation = validation

        # Show validation
        console.print()
        console.print(self.jester.format_report(validation))

        return {
            "code": result.code,
            "validation": validation,
        }

    async def validate_code(self, code: str):
        """Validate provided code."""
        console.print("[cyan]🃏 Jester is validating...[/cyan]")

        validation = await self.jester.validate(code, "python")
        self.current_validation = validation

        console.print()
        console.print(self.jester.format_report(validation))

        return validation

    async def interactive_loop(self):
        """Run interactive prompt loop."""
        console.print(Panel(
            Text.assemble(
                ("🃏 Code Jester - Feedback Loop Demo\n\n", "bold bright_magenta"),
                ("Commands:\n", "bold"),
                ("  ", ""),
                (":g <prompt>", "cyan"), ("  - Generate code from prompt\n", ""),
                ("  ", ""),
                (":v", "cyan"), ("           - Validate pasted code\n", ""),
                ("  ", ""),
                (":m", "cyan"), ("           - Show metrics\n", ""),
                ("  ", ""),
                (":q", "cyan"), ("           - Quit\n", ""),
                ("\nOllama Status: ", ""),
                ("Online ✅" if self.ollama_available else "Offline ❌",
                 "green" if self.ollama_available else "red"),
            ),
            border_style="bright_blue",
        ))

        while True:
            try:
                console.print()
                user_input = console.input("[bright_magenta]>>> [/bright_magenta]").strip()

                if not user_input:
                    continue

                if user_input == ":q":
                    break

                elif user_input == ":m":
                    stats = self.metrics.get_execution_stats()
                    console.print(Panel(
                        f"Total Executions: {stats['total_executions']}\n"
                        f"Success Rate: {stats['success_rate']*100:.1f}%\n"
                        f"Avg Time: {stats['avg_execution_time_ms']:.1f}ms",
                        title="📊 Metrics",
                        border_style="cyan",
                    ))

                elif user_input.startswith(":g "):
                    prompt = user_input[3:].strip()
                    if prompt:
                        await self.generate_and_validate(prompt)
                    else:
                        console.print("[yellow]Please provide a prompt[/yellow]")

                elif user_input == ":v":
                    console.print("[dim]Paste code, then press Enter twice:[/dim]")
                    lines = []
                    empty_count = 0
                    while empty_count < 2:
                        try:
                            line = input()
                            if line == "":
                                empty_count += 1
                            else:
                                empty_count = 0
                                lines.append(line)
                        except EOFError:
                            break

                    if lines:
                        code = "\n".join(lines)
                        await self.validate_code(code)

                else:
                    # Treat as code to validate
                    await self.validate_code(user_input)

            except KeyboardInterrupt:
                console.print("\n[dim]Use :q to quit[/dim]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

        console.print("[dim]Goodbye from the Royal Court! 👋[/dim]")


async def main():
    demo = FeedbackLoopDemo()
    await demo.start()

    try:
        await demo.interactive_loop()
    finally:
        await demo.stop()


if __name__ == "__main__":
    asyncio.run(main())
