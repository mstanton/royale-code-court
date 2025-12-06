"""
Basic tests for Code Jester components
Run with: pytest tests/test_basic.py -v
"""

import asyncio
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from jester.core.event_stream import EventBus, EventStream, get_event_bus
from jester.core.models import AgentType, EventType, Event
from jester.execution.executor import CodeExecutor
from jester.execution.repl_executor import REPLExecutor


class TestEventBus:
    """Test the event bus system."""

    def test_create_event_bus(self):
        """Test creating an event bus."""
        bus = EventBus()
        assert bus.session_id is not None

    @pytest.mark.asyncio
    async def test_emit_and_receive(self):
        """Test emitting and receiving events."""
        bus = EventBus()
        received_events = []

        async def handler(event):
            received_events.append(event)

        bus.subscribe(EventType.LOG_MESSAGE, handler)

        event = Event(
            event_type=EventType.LOG_MESSAGE,
            agent=AgentType.SYSTEM,
            payload={"message": "test"},
        )
        await bus.emit(event)

        assert len(received_events) == 1
        assert received_events[0].payload["message"] == "test"

    @pytest.mark.asyncio
    async def test_global_handler(self):
        """Test global event handler."""
        bus = EventBus()
        received_events = []

        async def global_handler(event):
            received_events.append(event)

        bus.subscribe_all(global_handler)

        # Emit different event types
        await bus.emit(Event(EventType.LOG_MESSAGE, AgentType.SYSTEM, {}))
        await bus.emit(Event(EventType.CODE_GENERATED, AgentType.KING, {}))

        assert len(received_events) == 2


class TestEventStream:
    """Test the event stream wrapper."""

    @pytest.mark.asyncio
    async def test_create_stream(self):
        """Test creating an event stream."""
        bus = EventBus()
        stream = EventStream(bus, AgentType.JESTER)

        event = await stream.emit(EventType.LOG_MESSAGE, {"test": True})
        assert event.agent == AgentType.JESTER

    @pytest.mark.asyncio
    async def test_convenience_methods(self):
        """Test convenience methods."""
        bus = EventBus()
        stream = EventStream(bus, AgentType.JESTER)

        event = await stream.log("Test message")
        assert event.event_type == EventType.LOG_MESSAGE


class TestREPLExecutor:
    """Test the REPL executor."""

    @pytest.mark.asyncio
    async def test_simple_execution(self):
        """Test simple code execution."""
        executor = REPLExecutor()
        result = await executor.execute("print('Hello')")

        assert result.success is True
        assert "Hello" in result.output

    @pytest.mark.asyncio
    async def test_syntax_error(self):
        """Test handling syntax errors."""
        executor = REPLExecutor()
        result = await executor.execute("def broken(")

        assert result.success is False
        assert "error" in result.error.lower() or "syntax" in result.error.lower()

    @pytest.mark.asyncio
    async def test_runtime_error(self):
        """Test handling runtime errors."""
        executor = REPLExecutor()
        result = await executor.execute("x = 1/0")

        assert result.success is False
        assert "ZeroDivision" in result.error

    @pytest.mark.asyncio
    async def test_timeout(self):
        """Test execution timeout."""
        executor = REPLExecutor()
        # Infinite loop should timeout
        result = await executor.execute(
            "while True: pass",
            timeout=0.5
        )

        assert result.success is False
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_allowed_imports(self):
        """Test allowed module imports."""
        executor = REPLExecutor()
        result = await executor.execute("import math; print(math.pi)")

        assert result.success is True
        assert "3.14" in result.output

    @pytest.mark.asyncio
    async def test_subprocess_isolation(self):
        """Test subprocess doesn't affect main process."""
        executor = REPLExecutor()
        # This should run in isolation
        result = await executor.execute("import os; print(os.getpid())")

        assert result.success is True
        # Should have output (a PID number)
        assert result.output.strip().isdigit()


class TestCodeExecutor:
    """Test the main code executor."""

    def test_analyze_code(self):
        """Test static code analysis."""
        executor = CodeExecutor()

        # Valid code
        analysis = executor.analyze_code("x = 1 + 2")
        assert analysis.syntax_valid is True

        # Invalid syntax
        analysis = executor.analyze_code("def broken(")
        assert analysis.syntax_valid is False

    def test_complexity_analysis(self):
        """Test complexity calculation."""
        executor = CodeExecutor()

        simple_code = "x = 1"
        complex_code = """
def foo(x):
    if x > 0:
        for i in range(x):
            if i % 2 == 0:
                print(i)
            else:
                print(-i)
    else:
        while True:
            break
"""
        simple_analysis = executor.analyze_code(simple_code)
        complex_analysis = executor.analyze_code(complex_code)

        assert complex_analysis.complexity > simple_analysis.complexity

    def test_blocked_patterns(self):
        """Test detection of blocked patterns."""
        executor = CodeExecutor()

        # SQL injection-like pattern
        analysis = executor.analyze_code("eval(input())")
        assert analysis.is_blocked is True

    @pytest.mark.asyncio
    async def test_execute_simple(self):
        """Test simple execution."""
        executor = CodeExecutor()
        result = await executor.execute("result = 2 + 2; print(result)")

        assert result.success is True
        assert "4" in result.output


class TestModels:
    """Test data models."""

    def test_event_creation(self):
        """Test event creation."""
        event = Event(
            event_type=EventType.CODE_GENERATED,
            agent=AgentType.KING,
            payload={"code": "print('hi')"},
        )

        assert event.event_id is not None
        assert event.timestamp is not None
        assert event.event_type == EventType.CODE_GENERATED

    def test_event_to_dict(self):
        """Test event serialization."""
        event = Event(
            event_type=EventType.LOG_MESSAGE,
            agent=AgentType.SYSTEM,
            payload={"message": "test"},
        )

        data = event.to_dict()
        assert "event_id" in data
        assert data["event_type"] == "log.message"
        assert data["agent"] == "system"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
