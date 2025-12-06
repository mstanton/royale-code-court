#!/usr/bin/env python3
"""
Simple Workflow Example
Demonstrates the basic Code Jester feedback loop:
1. Submit code
2. Validate with Jester
3. See results

This is the minimal working example for testing.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from jester.core.event_stream import get_event_bus, EventStream
from jester.core.models import AgentType, EventType
from jester.agents.jester import JesterAgent
from jester.execution.executor import CodeExecutor


async def validate_single_code(code: str, language: str = "python"):
    """Validate a single piece of code and return results."""

    # Initialize minimal components
    event_bus = get_event_bus()
    executor = CodeExecutor()
    jester = JesterAgent(event_bus, executor=executor)

    # Start the Jester
    jester.start()

    # Validate
    result = await jester.validate(code, language)

    # Stop
    jester.stop()

    return result


async def main():
    print("🃏 Code Jester - Simple Workflow")
    print("=" * 40)

    # Example 1: Valid Python code
    code1 = '''
def add(a, b):
    return a + b

result = add(5, 3)
print(f"5 + 3 = {result}")
'''

    print("\n📝 Example 1: Simple addition function")
    print("-" * 40)
    result1 = await validate_single_code(code1)
    print(f"✅ Syntax Valid: {result1.syntax_valid}")
    print(f"⚡ Executes: {result1.executes}")
    print(f"🧪 Tests: {result1.tests_passed}/{result1.tests_generated} passed")
    print(f"📊 Complexity: {result1.complexity_score}")
    print(f"🔍 Patterns: {', '.join(result1.patterns_detected)}")
    if result1.execution_result:
        print(f"📤 Output: {result1.execution_result.output.strip()}")

    # Example 2: Code with syntax error
    code2 = '''
def broken(
    return "missing parenthesis"
'''

    print("\n📝 Example 2: Code with syntax error")
    print("-" * 40)
    result2 = await validate_single_code(code2)
    print(f"❌ Syntax Valid: {result2.syntax_valid}")
    if result2.issues:
        print(f"⚠️  Issue: {result2.issues[0]}")

    # Example 3: Code with runtime error
    code3 = '''
def divide(a, b):
    return a / b

result = divide(10, 0)
print(result)
'''

    print("\n📝 Example 3: Code with runtime error")
    print("-" * 40)
    result3 = await validate_single_code(code3)
    print(f"✅ Syntax Valid: {result3.syntax_valid}")
    print(f"❌ Executes: {result3.executes}")
    if result3.execution_result and result3.execution_result.error:
        error_first_line = result3.execution_result.error.split('\n')[0]
        print(f"⚠️  Error: {error_first_line}")

    # Example 4: Complex code with patterns
    code4 = '''
class DataProcessor:
    """Process data with various transformations."""

    def __init__(self, data):
        self.data = data
        self._cache = {}

    def transform(self, func):
        """Apply transformation with caching."""
        key = func.__name__
        if key not in self._cache:
            self._cache[key] = [func(x) for x in self.data]
        return self._cache[key]

    def filter_by(self, predicate):
        """Filter data by predicate."""
        return [x for x in self.data if predicate(x)]

# Usage
processor = DataProcessor([1, 2, 3, 4, 5])
squared = processor.transform(lambda x: x**2)
evens = processor.filter_by(lambda x: x % 2 == 0)
print(f"Squared: {squared}")
print(f"Evens: {evens}")
'''

    print("\n📝 Example 4: Complex class with patterns")
    print("-" * 40)
    result4 = await validate_single_code(code4)
    print(f"✅ Syntax Valid: {result4.syntax_valid}")
    print(f"⚡ Executes: {result4.executes}")
    print(f"📊 Complexity: {result4.complexity_score}")
    print(f"🔍 Patterns: {', '.join(result4.patterns_detected)}")
    if result4.execution_result:
        print(f"📤 Output:\n{result4.execution_result.output.strip()}")

    print("\n" + "=" * 40)
    print("✨ Workflow complete!")


if __name__ == "__main__":
    asyncio.run(main())
