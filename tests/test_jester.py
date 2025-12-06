"""
Tests for the Jester agent
Run with: pytest tests/test_jester.py -v
"""

import asyncio
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from jester.core.event_stream import EventBus
from jester.core.models import EventType
from jester.agents.jester import JesterAgent
from jester.execution.executor import CodeExecutor


@pytest.fixture
def event_bus():
    """Create a fresh event bus for each test."""
    return EventBus()


@pytest.fixture
def jester(event_bus):
    """Create a Jester agent."""
    executor = CodeExecutor()
    return JesterAgent(event_bus, executor=executor)


class TestJesterValidation:
    """Test Jester validation capabilities."""

    @pytest.mark.asyncio
    async def test_validate_simple_code(self, jester):
        """Test validating simple code."""
        jester.start()

        code = """
def add(a, b):
    return a + b

print(add(2, 3))
"""
        result = await jester.validate(code)

        assert result.syntax_valid is True
        assert result.executes is True
        assert "5" in result.execution_result.output

        jester.stop()

    @pytest.mark.asyncio
    async def test_detect_patterns(self, jester):
        """Test pattern detection."""
        jester.start()

        code = """
# List comprehension pattern
squares = [x**2 for x in range(10)]

# Error handling pattern
try:
    result = 1/0
except ZeroDivisionError:
    result = 0

# Lambda pattern
double = lambda x: x * 2

print(squares[:5])
"""
        result = await jester.validate(code)

        assert "List Comprehension" in result.patterns_detected
        assert "Error Handling" in result.patterns_detected
        assert "Lambda Function" in result.patterns_detected

        jester.stop()

    @pytest.mark.asyncio
    async def test_complexity_scoring(self, jester):
        """Test complexity scoring."""
        jester.start()

        simple_code = "x = 1"
        complex_code = """
def process(items):
    result = []
    for item in items:
        if item > 0:
            for i in range(item):
                if i % 2 == 0:
                    result.append(i)
                elif i % 3 == 0:
                    result.append(-i)
    return result
"""
        simple_result = await jester.validate(simple_code)
        complex_result = await jester.validate(complex_code)

        assert complex_result.complexity_score > simple_result.complexity_score

        jester.stop()

    @pytest.mark.asyncio
    async def test_test_generation(self, jester):
        """Test automatic test generation."""
        jester.start()

        code = """
def multiply(a, b):
    return a * b

def is_even(n):
    return n % 2 == 0
"""
        result = await jester.validate(code, generate_tests=True)

        assert result.tests_generated > 0
        # Most basic tests should pass
        assert result.tests_passed >= result.tests_generated - 1

        jester.stop()

    @pytest.mark.asyncio
    async def test_security_detection(self, jester):
        """Test security issue detection."""
        jester.start()

        # Code with potential security issues
        code = '''
password = "secret123"
api_key = "sk-123456"

def query(user_id):
    return f"SELECT * FROM users WHERE id = {user_id}"
'''
        result = await jester.validate(code)

        # Should detect security issues
        assert len(result.issues) > 0 or len(result.suggestions) > 0

        jester.stop()

    @pytest.mark.asyncio
    async def test_format_report(self, jester):
        """Test report formatting."""
        jester.start()

        code = "print('Hello, World!')"
        result = await jester.validate(code)
        report = jester.format_report(result)

        assert "Jester" in report
        assert "Syntax" in report
        assert "Executes" in report

        jester.stop()


class TestJesterEvents:
    """Test Jester event handling."""

    @pytest.mark.asyncio
    async def test_emits_validation_event(self, jester, event_bus):
        """Test that validation emits events."""
        jester.start()

        received_events = []

        async def handler(event):
            received_events.append(event)

        event_bus.subscribe(EventType.CODE_VALIDATED, handler)

        await jester.validate("x = 1 + 1")

        # Should have received a validation event
        assert len(received_events) == 1
        assert received_events[0].payload["syntax_valid"] is True

        jester.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
