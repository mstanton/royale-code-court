#!/usr/bin/env python3
"""
MCP Server for Royale Code Court / Code Jester
Exposes execution environment to Claude Desktop and compatible clients

This enables the AI learning loop where Claude can:
1. Execute code before presenting it to users
2. Analyze errors and get suggestions
3. Learn from execution patterns

Install: pip install mcp
"""

import asyncio
import sys
from typing import Any, Dict, List, Optional

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    Server = None
    stdio_server = None
    Tool = None
    TextContent = None

from ..core.event_stream import get_event_bus, EventStream
from ..core.models import AgentType, ExecutionTier
from ..execution.executor import CodeExecutor
from ..agents.jester import JesterAgent
from ..core.metrics import MetricsCollector


def create_mcp_server(
    metrics_path: str = "storage/metrics.db"
) -> Optional["Server"]:
    """
    Create and configure the MCP server for Code Jester.

    Args:
        metrics_path: Path to the SQLite metrics database

    Returns:
        Configured MCP Server instance, or None if MCP not available
    """
    if not MCP_AVAILABLE:
        return None

    server = Server("royale-code-court")

    # Initialize core components
    event_bus = get_event_bus()
    executor = CodeExecutor(EventStream(event_bus, AgentType.JESTER))
    metrics = MetricsCollector()
    jester = JesterAgent(event_bus, executor=executor, metrics=metrics)
    jester.start()

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """Expose available tools to AI clients"""
        return [
            Tool(
                name="execute_code",
                description="""Execute Python code in a secure sandbox.

Use this tool to:
- Test code BEFORE presenting to user
- Verify syntax and logic
- Check for runtime errors
- Measure performance

The execution is sandboxed with:
- 5 second default timeout
- Process isolation
- Pattern-based security checks
- Blocked dangerous operations

Returns execution results, errors, patterns detected, and suggestions.

IMPORTANT: Use this tool to validate any code you generate before showing it to the user.
This creates a "validate before present" workflow that catches errors early.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute"
                        },
                        "language": {
                            "type": "string",
                            "default": "python",
                            "description": "Programming language (python supported)"
                        },
                        "timeout": {
                            "type": "number",
                            "default": 5.0,
                            "description": "Execution timeout in seconds"
                        }
                    },
                    "required": ["code"]
                }
            ),
            Tool(
                name="validate_code",
                description="""Perform full validation on code including:
- Syntax checking
- Pattern detection (design patterns, security issues)
- Complexity analysis
- Test execution
- Security scanning

Use this for comprehensive code review before presenting to users.
More thorough than execute_code but takes longer.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Code to validate"
                        },
                        "language": {
                            "type": "string",
                            "default": "python",
                            "description": "Programming language"
                        },
                        "generate_tests": {
                            "type": "boolean",
                            "default": True,
                            "description": "Generate and run test cases"
                        }
                    },
                    "required": ["code"]
                }
            ),
            Tool(
                name="analyze_error",
                description="""Analyze a code error and suggest fixes.

Provide the code and error message to get:
- Root cause analysis
- Suggested fixes based on error type
- Common patterns that cause this error
- Example corrections

Use when code execution fails to understand why and how to fix it.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The code that produced the error"
                        },
                        "error": {
                            "type": "string",
                            "description": "The error message"
                        }
                    },
                    "required": ["code", "error"]
                }
            ),
            Tool(
                name="get_execution_stats",
                description="""Get statistics about code execution history.

Returns:
- Total executions
- Success rate
- Average execution time
- Breakdown by execution tier
- Learned patterns and their success rates

Use to understand the execution environment's performance and patterns.""",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="check_security",
                description="""Check code for security vulnerabilities.

Scans for:
- SQL injection patterns
- Command injection risks
- Eval/exec with user input
- Hardcoded secrets/passwords
- Other OWASP top 10 vulnerabilities

Returns severity levels and specific concerns.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Code to check for security issues"
                        }
                    },
                    "required": ["code"]
                }
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> List[TextContent]:
        """Handle tool calls from AI clients"""

        if name == "execute_code":
            return await _handle_execute_code(arguments, executor)

        elif name == "validate_code":
            return await _handle_validate_code(arguments, jester)

        elif name == "analyze_error":
            return await _handle_analyze_error(arguments)

        elif name == "get_execution_stats":
            return await _handle_get_stats(metrics)

        elif name == "check_security":
            return await _handle_check_security(arguments, jester)

        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

    return server


async def _handle_execute_code(
    arguments: dict,
    executor: CodeExecutor
) -> List["TextContent"]:
    """Handle execute_code tool call"""
    code = arguments.get("code", "")
    language = arguments.get("language", "python")
    timeout = arguments.get("timeout", 5.0)

    if not code.strip():
        return [TextContent(
            type="text",
            text="Error: No code provided"
        )]

    result = await executor.execute(code, language, timeout=timeout)

    if result.success:
        output_text = result.output.strip() if result.output else "(no output)"
        return [TextContent(
            type="text",
            text=f"""Code executed successfully

Output:
{output_text}

Performance:
- Execution time: {result.execution_time_ms:.1f}ms
- Execution tier: {result.tier.value}
- Memory usage: {result.memory_usage_mb:.2f}MB

Status: PASSED - Code is ready to present to user."""
        )]
    else:
        error_text = result.error.strip() if result.error else "Unknown error"
        return [TextContent(
            type="text",
            text=f"""Code execution failed

Error:
{error_text}

Execution tier: {result.tier.value}
Execution time: {result.execution_time_ms:.1f}ms

Status: FAILED - Fix the error before presenting to user.

Suggestion: Analyze the error and modify the code to fix the issue."""
        )]


async def _handle_validate_code(
    arguments: dict,
    jester: JesterAgent
) -> List["TextContent"]:
    """Handle validate_code tool call"""
    code = arguments.get("code", "")
    language = arguments.get("language", "python")
    generate_tests = arguments.get("generate_tests", True)

    if not code.strip():
        return [TextContent(
            type="text",
            text="Error: No code provided"
        )]

    result = await jester.validate(code, language, generate_tests=generate_tests)

    # Build comprehensive report
    lines = []

    if result.overall_success:
        lines.append("VALIDATION PASSED")
        lines.append("")
    else:
        lines.append("VALIDATION FAILED")
        lines.append("")

    # Details
    lines.append(f"Syntax valid: {'Yes' if result.syntax_valid else 'No'}")
    lines.append(f"Executes: {'Yes' if result.executes else 'No'}")
    lines.append(f"Complexity score: {result.complexity_score}")

    if result.execution_result:
        lines.append(f"Execution time: {result.execution_result.execution_time_ms:.1f}ms")
        lines.append(f"Execution tier: {result.execution_result.tier.value}")

    if result.patterns_detected:
        lines.append(f"\nPatterns detected: {', '.join(result.patterns_detected[:5])}")

    if result.issues:
        lines.append("\nIssues found:")
        for issue in result.issues:
            lines.append(f"  - {issue}")

    if result.suggestions:
        lines.append("\nSuggestions:")
        for suggestion in result.suggestions:
            lines.append(f"  - {suggestion}")

    if result.execution_result and result.execution_result.output:
        lines.append(f"\nExecution output:\n{result.execution_result.output[:500]}")

    lines.append(f"\nTotal validation time: {result.validation_time_ms:.1f}ms")

    return [TextContent(
        type="text",
        text="\n".join(lines)
    )]


async def _handle_analyze_error(arguments: dict) -> List["TextContent"]:
    """Handle analyze_error tool call"""
    code = arguments.get("code", "")
    error = arguments.get("error", "")

    if not error.strip():
        return [TextContent(
            type="text",
            text="Error: No error message provided"
        )]

    # Parse error type
    error_type = "Unknown"
    if ":" in error:
        error_type = error.split(":")[0].strip()

    # Generate suggestions based on error type
    suggestions = []

    if "SyntaxError" in error_type:
        suggestions = [
            "Check for missing colons after if/for/while/def/class statements",
            "Ensure all parentheses, brackets, and braces are matched",
            "Check for proper indentation",
            "Look for missing commas in lists/dicts",
            "Verify string quotes are properly closed"
        ]
    elif "NameError" in error_type:
        suggestions = [
            "Variable or function may not be defined before use",
            "Check for typos in variable/function names",
            "Ensure imports are at the top of the file",
            "Check variable scope - it may be defined in a different scope"
        ]
    elif "TypeError" in error_type:
        suggestions = [
            "Check argument types being passed to functions",
            "Ensure you're not calling non-callable objects",
            "Verify operand types are compatible for the operation",
            "Check for None values where objects are expected"
        ]
    elif "IndexError" in error_type:
        suggestions = [
            "Check list/array bounds before accessing",
            "Verify the container is not empty",
            "Use len() to check size before indexing",
            "Consider using try/except or .get() for safe access"
        ]
    elif "KeyError" in error_type:
        suggestions = [
            "Key does not exist in dictionary",
            "Use .get(key, default) for safe access",
            "Check key spelling and case",
            "Verify dictionary is populated before access"
        ]
    elif "AttributeError" in error_type:
        suggestions = [
            "Object doesn't have the specified attribute",
            "Check object type - it may be None",
            "Verify spelling of attribute name",
            "Ensure class has the method/property defined"
        ]
    elif "ValueError" in error_type:
        suggestions = [
            "Invalid value passed to function",
            "Check input data format and range",
            "Validate input before processing",
            "Consider using try/except for conversions"
        ]
    elif "ZeroDivisionError" in error_type:
        suggestions = [
            "Check for zero before division",
            "Add guard clause: if divisor != 0",
            "Consider what should happen when divisor is 0"
        ]
    elif "ImportError" in error_type or "ModuleNotFoundError" in error_type:
        suggestions = [
            "Module may not be installed",
            "Check spelling of module name",
            "Verify the module is available in the execution environment",
            "Some modules are restricted in sandbox mode"
        ]
    else:
        suggestions = [
            "Review the error message carefully",
            "Check the line number mentioned in the traceback",
            "Verify input data and types",
            "Consider adding error handling"
        ]

    return [TextContent(
        type="text",
        text=f"""Error Analysis

Error type: {error_type}

Original error:
{error}

Likely causes and fixes:
{chr(10).join('- ' + s for s in suggestions)}

Recommended approach:
1. Review the specific line mentioned in the error
2. Apply the most relevant fix from above
3. Re-execute to verify the fix works"""
    )]


async def _handle_get_stats(metrics: MetricsCollector) -> List["TextContent"]:
    """Handle get_execution_stats tool call"""
    exec_stats = metrics.get_execution_stats()
    pattern_stats = metrics.get_pattern_stats()

    lines = ["Execution Statistics", "=" * 40, ""]

    lines.append(f"Total executions: {exec_stats['total_executions']}")
    lines.append(f"Success rate: {exec_stats['success_rate']*100:.1f}%")
    lines.append(f"Average execution time: {exec_stats['avg_execution_time_ms']:.1f}ms")

    if exec_stats['by_tier']:
        lines.append("\nBy execution tier:")
        for tier, stats in exec_stats['by_tier'].items():
            lines.append(f"  {tier}: {stats['count']} executions, "
                        f"{stats['avg_time_ms']:.1f}ms avg")

    if pattern_stats:
        lines.append("\nLearned patterns:")
        for pattern in pattern_stats[:10]:
            lines.append(f"  - {pattern['name']}: {pattern['occurrences']} occurrences, "
                        f"{pattern['success_rate']*100:.0f}% success")

    return [TextContent(
        type="text",
        text="\n".join(lines)
    )]


async def _handle_check_security(
    arguments: dict,
    jester: JesterAgent
) -> List["TextContent"]:
    """Handle check_security tool call"""
    code = arguments.get("code", "")

    if not code.strip():
        return [TextContent(
            type="text",
            text="Error: No code provided"
        )]

    # Use jester's security check
    issues = jester._check_security(code)

    if not issues:
        return [TextContent(
            type="text",
            text="""Security Check: PASSED

No security vulnerabilities detected.

Note: This is a pattern-based check. It may not catch all security issues.
Always review code manually for sensitive operations."""
        )]

    lines = ["Security Check: ISSUES FOUND", ""]

    for issue_name, severity, description in issues:
        emoji = {
            "critical": "CRITICAL",
            "high": "HIGH",
            "medium": "MEDIUM",
            "low": "LOW",
            "info": "INFO"
        }.get(severity.value, "UNKNOWN")

        lines.append(f"[{emoji}] {description}")
        lines.append(f"   Pattern: {issue_name}")
        lines.append("")

    lines.append("Recommendation: Fix all CRITICAL and HIGH severity issues before presenting code.")

    return [TextContent(
        type="text",
        text="\n".join(lines)
    )]


async def run_mcp_server():
    """Run the MCP server"""
    if not MCP_AVAILABLE:
        print("Error: MCP package not installed. Install with: pip install mcp", file=sys.stderr)
        sys.exit(1)

    server = create_mcp_server()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


def main():
    """Entry point for MCP server"""
    asyncio.run(run_mcp_server())


if __name__ == "__main__":
    main()
