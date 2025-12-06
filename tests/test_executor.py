"""Tests for CodeExecutor and execution tiers"""

import pytest
import asyncio

from jester.execution.executor import CodeExecutor, CodeAnalysis
from jester.execution.repl_executor import REPLExecutor
from jester.core.models import ExecutionResult, ExecutionTier


@pytest.fixture
def executor():
    """Create a CodeExecutor instance for testing"""
    return CodeExecutor()


@pytest.fixture
def repl_executor():
    """Create a REPLExecutor instance for testing"""
    return REPLExecutor()


class TestCodeAnalysis:
    """Tests for static code analysis"""

    def test_valid_syntax(self, executor):
        """Test that valid Python code passes syntax check"""
        code = "def hello(): return 'world'"
        analysis = executor.analyze_code(code)
        assert analysis.syntax_valid is True
        assert analysis.error_message == ""

    def test_invalid_syntax(self, executor):
        """Test that invalid Python code fails syntax check"""
        code = "def broken("
        analysis = executor.analyze_code(code)
        assert analysis.syntax_valid is False
        assert "syntax" in analysis.error_message.lower() or "Syntax" in analysis.error_message

    def test_import_detection(self, executor):
        """Test that imports are detected"""
        code = """
import math
from collections import defaultdict
import json
"""
        analysis = executor.analyze_code(code)
        assert "math" in analysis.imports
        assert "collections" in analysis.imports
        assert "json" in analysis.imports

    def test_function_detection(self, executor):
        """Test that function definitions are detected"""
        code = """
def foo(): pass
def bar(x, y): return x + y
"""
        analysis = executor.analyze_code(code)
        assert "foo" in analysis.functions
        assert "bar" in analysis.functions

    def test_class_detection(self, executor):
        """Test that class definitions are detected"""
        code = """
class MyClass:
    pass

class AnotherClass:
    def __init__(self):
        pass
"""
        analysis = executor.analyze_code(code)
        assert "MyClass" in analysis.classes
        assert "AnotherClass" in analysis.classes

    def test_complexity_calculation(self, executor):
        """Test that complexity is calculated"""
        simple_code = "x = 1"
        complex_code = """
def complex_func(items):
    result = []
    for item in items:
        if item > 0:
            if item % 2 == 0:
                result.append(item)
            else:
                for i in range(item):
                    if i > 5:
                        result.append(i)
    return result
"""
        simple_analysis = executor.analyze_code(simple_code)
        complex_analysis = executor.analyze_code(complex_code)
        assert complex_analysis.complexity > simple_analysis.complexity

    def test_blocked_patterns(self, executor):
        """Test that dangerous patterns are blocked"""
        dangerous_code = "eval(input())"
        analysis = executor.analyze_code(dangerous_code)
        assert analysis.is_blocked is True

    def test_container_required_detection(self, executor):
        """Test that code requiring container execution is detected"""
        network_code = "import requests; requests.get('http://example.com')"
        analysis = executor.analyze_code(network_code)
        assert analysis.requires_container is True


class TestCodeExecution:
    """Tests for code execution"""

    @pytest.mark.asyncio
    async def test_simple_execution(self, executor):
        """Test simple code execution"""
        code = "print(2 + 2)"
        result = await executor.execute(code)
        assert result.success is True
        assert "4" in result.output

    @pytest.mark.asyncio
    async def test_syntax_error_handling(self, executor):
        """Test that syntax errors are handled gracefully"""
        code = "def broken("
        result = await executor.execute(code)
        assert result.success is False
        assert "syntax" in result.error.lower() or "Syntax" in result.error

    @pytest.mark.asyncio
    async def test_runtime_error_handling(self, executor):
        """Test that runtime errors are handled gracefully"""
        code = "1 / 0"
        result = await executor.execute(code)
        assert result.success is False
        assert "ZeroDivision" in result.error or "division" in result.error.lower()

    @pytest.mark.asyncio
    async def test_timeout_handling(self, executor):
        """Test that long-running code times out"""
        code = """
import time
time.sleep(10)
"""
        result = await executor.execute(code, timeout=1.0)
        assert result.success is False
        assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execution_time_tracking(self, executor):
        """Test that execution time is tracked"""
        code = "x = sum(range(1000))"
        result = await executor.execute(code)
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_output_capture(self, executor):
        """Test that stdout is captured"""
        code = """
print("Hello")
print("World")
"""
        result = await executor.execute(code)
        assert result.success is True
        assert "Hello" in result.output
        assert "World" in result.output

    @pytest.mark.asyncio
    async def test_exception_in_code(self, executor):
        """Test handling of exceptions in code"""
        code = "raise ValueError('test error')"
        result = await executor.execute(code)
        assert result.success is False
        assert "ValueError" in result.error


class TestREPLExecutor:
    """Tests for REPL executor specifically"""

    @pytest.mark.asyncio
    async def test_basic_execution(self, repl_executor):
        """Test basic REPL execution"""
        code = "print('hello from repl')"
        result = await repl_executor.execute(code)
        assert result.success is True
        assert "hello from repl" in result.output

    @pytest.mark.asyncio
    async def test_multiline_code(self, repl_executor):
        """Test multiline code execution"""
        code = """
def greet(name):
    return f"Hello, {name}!"

result = greet("World")
print(result)
"""
        result = await repl_executor.execute(code)
        assert result.success is True
        assert "Hello, World!" in result.output

    @pytest.mark.asyncio
    async def test_import_safe_modules(self, repl_executor):
        """Test that safe modules can be imported"""
        code = """
import math
import json
print(math.pi)
print(json.dumps({"a": 1}))
"""
        result = await repl_executor.execute(code)
        assert result.success is True
        assert "3.14" in result.output

    @pytest.mark.asyncio
    async def test_tier_assignment(self, repl_executor):
        """Test that REPL tier is correctly assigned"""
        code = "x = 1"
        result = await repl_executor.execute(code)
        assert result.tier == ExecutionTier.REPL


class TestExecutionTierSelection:
    """Tests for automatic tier selection"""

    @pytest.mark.asyncio
    async def test_simple_code_uses_repl(self, executor):
        """Test that simple code uses REPL tier"""
        code = "x = [i**2 for i in range(10)]"
        result = await executor.execute(code)
        assert result.tier == ExecutionTier.REPL

    @pytest.mark.asyncio
    async def test_force_tier(self, executor):
        """Test that tier can be forced"""
        code = "print('test')"
        result = await executor.execute(code, force_tier=ExecutionTier.REPL)
        assert result.tier == ExecutionTier.REPL

    def test_container_detection_for_network(self, executor):
        """Test that network code requires container"""
        code = "import requests"
        analysis = executor.analyze_code(code)
        assert analysis.requires_container is True

    def test_container_detection_for_file_ops(self, executor):
        """Test that file operations require container"""
        code = "with open('file.txt') as f: pass"
        analysis = executor.analyze_code(code)
        assert analysis.requires_container is True
