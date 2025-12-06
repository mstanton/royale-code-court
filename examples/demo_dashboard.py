#!/usr/bin/env python3
"""
Demo Dashboard - Live demonstration of Code Jester
Shows the real-time feedback loop with simulated code generation and validation
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from jester.core.event_stream import get_event_bus, EventStream
from jester.core.models import AgentType, EventType
from jester.core.metrics import MetricsCollector
from jester.agents.jester import JesterAgent
from jester.agents.scribe import ScribeAgent
from jester.execution.executor import CodeExecutor
from jester.observability.terminal_ui import TerminalDashboard, SimpleLogDisplay


# Sample code snippets to demonstrate
DEMO_CODES = [
    {
        "name": "Simple Function",
        "code": '''
def greet(name):
    """Return a greeting message."""
    return f"Hello, {name}!"

print(greet("World"))
''',
    },
    {
        "name": "Fibonacci",
        "code": '''
def fibonacci(n):
    """Calculate Fibonacci number iteratively."""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

# Test
for i in range(10):
    print(f"F({i}) = {fibonacci(i)}")
''',
    },
    {
        "name": "List Processing",
        "code": '''
def process_numbers(numbers):
    """Process a list of numbers with various operations."""
    if not numbers:
        return {}

    return {
        'sum': sum(numbers),
        'average': sum(numbers) / len(numbers),
        'min': min(numbers),
        'max': max(numbers),
        'even_count': len([n for n in numbers if n % 2 == 0]),
    }

data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
result = process_numbers(data)
print(result)
''',
    },
    {
        "name": "Class with Pattern",
        "code": '''
class Calculator:
    """Simple calculator with history."""

    def __init__(self):
        self.history = []

    def add(self, a, b):
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result

    def multiply(self, a, b):
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result

    def get_history(self):
        return self.history

calc = Calculator()
print(calc.add(5, 3))
print(calc.multiply(4, 7))
print(calc.get_history())
''',
    },
    {
        "name": "Error Handling",
        "code": '''
def safe_divide(a, b):
    """Safely divide two numbers."""
    try:
        result = a / b
        return {"success": True, "result": result}
    except ZeroDivisionError:
        return {"success": False, "error": "Division by zero"}
    except TypeError as e:
        return {"success": False, "error": str(e)}

print(safe_divide(10, 2))
print(safe_divide(10, 0))
print(safe_divide(10, "2"))
''',
    },
]


async def run_demo_with_logs():
    """Run demo with simple log output (no dashboard)"""
    print("🃏 Code Jester - Demo with Live Logs")
    print("=" * 50)

    # Initialize components
    event_bus = get_event_bus()
    metrics = MetricsCollector(storage_path=Path("storage/demo_metrics.db"))
    executor = CodeExecutor(EventStream(event_bus, AgentType.JESTER))
    jester = JesterAgent(event_bus, executor=executor, metrics=metrics)
    scribe = ScribeAgent(event_bus)

    # Simple log display
    log_display = SimpleLogDisplay(event_bus)

    # Start agents
    jester.start()
    scribe.start()

    print("\n📡 Event stream starting...\n")

    # Process each demo code
    for i, demo in enumerate(DEMO_CODES, 1):
        print(f"\n{'='*50}")
        print(f"Demo {i}: {demo['name']}")
        print(f"{'='*50}")

        # Emit code received event
        await EventStream(event_bus, AgentType.KING).emit(
            EventType.CODE_GENERATED,
            {"code": demo["code"], "language": "python"},
        )

        # Validate
        result = await jester.validate(demo["code"], "python")

        # Print formatted report
        print()
        print(jester.format_report(result))

        # Small delay between demos
        await asyncio.sleep(1)

    # Print final metrics
    print("\n" + "=" * 50)
    print("📊 Final Metrics")
    print("=" * 50)

    stats = metrics.get_execution_stats()
    print(f"Total Executions: {stats['total_executions']}")
    print(f"Success Rate: {stats['success_rate']*100:.1f}%")
    print(f"Avg Execution Time: {stats['avg_execution_time_ms']:.1f}ms")

    pattern_stats = metrics.get_pattern_stats()
    if pattern_stats:
        print("\nPatterns Detected:")
        for p in pattern_stats[:10]:
            print(f"  • {p['name']}: {p['occurrences']} times ({p['success_rate']*100:.0f}% success)")

    # Print Scribe insights
    print()
    print(scribe.format_insights_report())

    # Stop agents
    jester.stop()
    scribe.stop()


async def run_demo_with_dashboard():
    """Run demo with the full dashboard"""
    # Initialize components
    event_bus = get_event_bus()
    metrics = MetricsCollector(storage_path=Path("storage/demo_metrics.db"))
    executor = CodeExecutor(EventStream(event_bus, AgentType.JESTER))
    jester = JesterAgent(event_bus, executor=executor, metrics=metrics)
    scribe = ScribeAgent(event_bus)
    dashboard = TerminalDashboard(event_bus)

    # Start agents
    jester.start()
    scribe.start()

    # Run dashboard and demo concurrently
    async def run_demos():
        await asyncio.sleep(2)  # Let dashboard initialize

        for demo in DEMO_CODES:
            # Emit code generated
            await EventStream(event_bus, AgentType.KING).emit(
                EventType.CODE_GENERATED,
                {"code": demo["code"], "language": "python"},
            )

            # Validate
            await jester.validate(demo["code"], "python")

            # Wait before next demo
            await asyncio.sleep(3)

        # Keep dashboard running for a bit
        await asyncio.sleep(10)
        dashboard.stop()

    try:
        await asyncio.gather(
            dashboard.run(),
            run_demos(),
        )
    except asyncio.CancelledError:
        pass
    finally:
        jester.stop()
        scribe.stop()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Code Jester Demo")
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Use interactive dashboard (requires terminal)",
    )
    args = parser.parse_args()

    if args.dashboard:
        asyncio.run(run_demo_with_dashboard())
    else:
        asyncio.run(run_demo_with_logs())


if __name__ == "__main__":
    main()
