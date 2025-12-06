"""Tests for MCP Server"""

import pytest
import asyncio
import sys
from unittest.mock import Mock, patch, AsyncMock

# Import conditionally since MCP may not be installed
try:
    from jester.server.mcp import (
        create_mcp_server,
        _handle_execute_code,
        _handle_validate_code,
        _handle_analyze_error,
        _handle_get_stats,
        _handle_check_security,
        MCP_AVAILABLE
    )
except ImportError:
    MCP_AVAILABLE = False


@pytest.fixture
def mock_executor():
    """Create a mock executor"""
    executor = Mock()
    executor.execute = AsyncMock()
    return executor


@pytest.fixture
def mock_jester():
    """Create a mock jester agent"""
    jester = Mock()
    jester.validate = AsyncMock()
    jester._check_security = Mock(return_value=[])
    return jester


@pytest.fixture
def mock_metrics():
    """Create a mock metrics collector"""
    metrics = Mock()
    metrics.get_execution_stats = Mock(return_value={
        "total_executions": 100,
        "success_rate": 0.85,
        "avg_execution_time_ms": 50.0,
        "by_tier": {"repl": {"count": 90, "avg_time_ms": 45.0}}
    })
    metrics.get_pattern_stats = Mock(return_value=[
        {"name": "list_comprehension", "occurrences": 20, "success_rate": 0.9}
    ])
    return metrics


@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP package not installed")
class TestMCPServerCreation:
    """Tests for MCP server creation"""

    def test_create_server(self):
        """Test that MCP server can be created"""
        server = create_mcp_server()
        assert server is not None
        assert server.name == "royale-code-court"


class TestExecuteCodeHandler:
    """Tests for execute_code tool handler"""

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_executor):
        """Test successful code execution"""
        from jester.core.models import ExecutionResult, ExecutionTier

        mock_executor.execute.return_value = ExecutionResult(
            success=True,
            output="42\n",
            execution_time_ms=10.5,
            tier=ExecutionTier.REPL,
            memory_usage_mb=1.0
        )

        result = await _handle_execute_code(
            {"code": "print(42)"},
            mock_executor
        )

        assert len(result) == 1
        assert "successfully" in result[0].text
        assert "42" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_failure(self, mock_executor):
        """Test failed code execution"""
        from jester.core.models import ExecutionResult, ExecutionTier

        mock_executor.execute.return_value = ExecutionResult(
            success=False,
            error="ZeroDivisionError: division by zero",
            execution_time_ms=5.0,
            tier=ExecutionTier.REPL
        )

        result = await _handle_execute_code(
            {"code": "1/0"},
            mock_executor
        )

        assert len(result) == 1
        assert "failed" in result[0].text
        assert "ZeroDivision" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_empty_code(self, mock_executor):
        """Test execution with empty code"""
        result = await _handle_execute_code(
            {"code": "   "},
            mock_executor
        )

        assert len(result) == 1
        assert "No code provided" in result[0].text


class TestValidateCodeHandler:
    """Tests for validate_code tool handler"""

    @pytest.mark.asyncio
    async def test_validate_success(self, mock_jester):
        """Test successful validation"""
        from jester.core.models import ValidationResult, ExecutionResult, ExecutionTier

        mock_jester.validate.return_value = ValidationResult(
            code_id="test123",
            syntax_valid=True,
            executes=True,
            complexity_score=5,
            patterns_detected=["list_comprehension"],
            execution_result=ExecutionResult(
                success=True,
                execution_time_ms=10.0,
                tier=ExecutionTier.REPL
            )
        )

        result = await _handle_validate_code(
            {"code": "x = [i for i in range(10)]"},
            mock_jester
        )

        assert len(result) == 1
        assert "PASSED" in result[0].text
        assert "Syntax valid: Yes" in result[0].text

    @pytest.mark.asyncio
    async def test_validate_failure(self, mock_jester):
        """Test failed validation"""
        from jester.core.models import ValidationResult

        mock_jester.validate.return_value = ValidationResult(
            code_id="test123",
            syntax_valid=False,
            executes=False,
            issues=["Syntax error at line 1"]
        )

        result = await _handle_validate_code(
            {"code": "def broken("},
            mock_jester
        )

        assert len(result) == 1
        assert "FAILED" in result[0].text


class TestAnalyzeErrorHandler:
    """Tests for analyze_error tool handler"""

    @pytest.mark.asyncio
    async def test_analyze_syntax_error(self):
        """Test analysis of syntax error"""
        result = await _handle_analyze_error({
            "code": "def broken(",
            "error": "SyntaxError: unexpected EOF while parsing"
        })

        assert len(result) == 1
        assert "SyntaxError" in result[0].text
        assert "missing" in result[0].text.lower() or "parentheses" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_analyze_name_error(self):
        """Test analysis of name error"""
        result = await _handle_analyze_error({
            "code": "print(undefined_var)",
            "error": "NameError: name 'undefined_var' is not defined"
        })

        assert len(result) == 1
        assert "NameError" in result[0].text
        assert "defined" in result[0].text.lower() or "typo" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_analyze_type_error(self):
        """Test analysis of type error"""
        result = await _handle_analyze_error({
            "code": "'hello' + 5",
            "error": "TypeError: can only concatenate str (not 'int') to str"
        })

        assert len(result) == 1
        assert "TypeError" in result[0].text

    @pytest.mark.asyncio
    async def test_analyze_empty_error(self):
        """Test analysis with empty error"""
        result = await _handle_analyze_error({
            "code": "x = 1",
            "error": ""
        })

        assert len(result) == 1
        assert "No error message" in result[0].text


class TestGetStatsHandler:
    """Tests for get_execution_stats tool handler"""

    @pytest.mark.asyncio
    async def test_get_stats(self, mock_metrics):
        """Test getting execution stats"""
        result = await _handle_get_stats(mock_metrics)

        assert len(result) == 1
        assert "Total executions: 100" in result[0].text
        assert "85" in result[0].text  # Success rate


class TestCheckSecurityHandler:
    """Tests for check_security tool handler"""

    @pytest.mark.asyncio
    async def test_check_security_clean(self, mock_jester):
        """Test security check with clean code"""
        mock_jester._check_security.return_value = []

        result = await _handle_check_security(
            {"code": "x = 1 + 2"},
            mock_jester
        )

        assert len(result) == 1
        assert "PASSED" in result[0].text

    @pytest.mark.asyncio
    async def test_check_security_issues(self, mock_jester):
        """Test security check with issues"""
        from jester.core.models import SeverityLevel

        mock_jester._check_security.return_value = [
            ("sql_injection", SeverityLevel.CRITICAL, "SQL Injection detected")
        ]

        result = await _handle_check_security(
            {"code": "query = f'SELECT * FROM users WHERE id = {user_id}'"},
            mock_jester
        )

        assert len(result) == 1
        assert "ISSUES FOUND" in result[0].text
        assert "CRITICAL" in result[0].text

    @pytest.mark.asyncio
    async def test_check_security_empty_code(self, mock_jester):
        """Test security check with empty code"""
        result = await _handle_check_security(
            {"code": ""},
            mock_jester
        )

        assert len(result) == 1
        assert "No code provided" in result[0].text
