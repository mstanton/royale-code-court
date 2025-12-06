"""
The Jester - Validator/Tester Agent
Quick-witted, catches errors, always testing
The "subconscious" - rapid, instinctive testing
"""

import ast
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import re

from ..core.models import (
    AgentType,
    Event,
    EventType,
    CodeSubmission,
    ExecutionResult,
    ValidationResult,
    CodePattern,
    SeverityLevel,
)
from ..core.event_stream import EventBus
from ..core.metrics import MetricsCollector, ExecutionMetric, ValidationMetric
from ..execution.executor import CodeExecutor
from .base_agent import BaseAgent


# Common patterns the Jester can detect
PATTERN_DETECTORS = {
    "input_validation": r'if\s+.*(?:not|is\s+None|==|!=|<|>)',
    "error_handling": r'try\s*:.*except',
    "list_comprehension": r'\[.*for.*in.*\]',
    "generator_expression": r'\(.*for.*in.*\)',
    "decorator_usage": r'@\w+',
    "context_manager": r'with\s+.*:',
    "lambda_function": r'lambda\s+',
    "recursion": r'def\s+(\w+).*\1\s*\(',
    "class_definition": r'class\s+\w+',
    "type_hints": r'def\s+\w+\([^)]*:\s*\w+',
    "f_string": r'f["\']',
    "async_await": r'async\s+def|await\s+',
}

# Security issues to detect
SECURITY_ISSUES = {
    "sql_injection": (r'f["\'].*SELECT.*{|\.format\(.*SELECT', SeverityLevel.CRITICAL),
    "command_injection": (r'os\.system\(.*\+|subprocess.*shell=True.*\+', SeverityLevel.CRITICAL),
    "eval_injection": (r'eval\s*\(.*input|eval\s*\(.*request', SeverityLevel.CRITICAL),
    "hardcoded_password": (r'password\s*=\s*["\'][^"\']+["\']', SeverityLevel.HIGH),
    "hardcoded_secret": (r'(?:secret|api_key|token)\s*=\s*["\'][^"\']+["\']', SeverityLevel.HIGH),
}


@dataclass
class TestCase:
    """A generated test case"""
    name: str
    input_data: Any
    expected_output: Any = None
    actual_output: Any = None
    passed: bool = False
    error: str = ""


class JesterAgent(BaseAgent):
    """
    The Jester validates and tests code from the King.
    Fast, thorough, and catches issues before they reach developers.
    """

    def __init__(
        self,
        event_bus: EventBus,
        executor: Optional[CodeExecutor] = None,
        metrics: Optional[MetricsCollector] = None,
    ):
        super().__init__(AgentType.JESTER, event_bus)
        self.executor = executor or CodeExecutor(self.event_stream)
        self.metrics = metrics or MetricsCollector()

        # Subscribe to relevant events
        self.subscribe([
            EventType.CODE_GENERATED,
            EventType.CODE_RECEIVED,
            EventType.HUMAN_INPUT,
        ])

    async def on_event(self, event: Event) -> None:
        """Handle incoming events"""
        if event.event_type in [EventType.CODE_GENERATED, EventType.CODE_RECEIVED]:
            code = event.payload.get("code", "")
            language = event.payload.get("language", "python")
            if code:
                await self.validate(code, language)

    async def validate(
        self,
        code: str,
        language: str = "python",
        generate_tests: bool = True,
    ) -> ValidationResult:
        """
        Validate code through multiple stages.

        1. Syntax validation
        2. Static analysis (patterns, security)
        3. Execution
        4. Test generation and execution

        Returns comprehensive ValidationResult
        """
        start_time = time.time()
        code_id = f"code_{int(time.time() * 1000)}"

        await self.thinking("Analyzing code...")

        result = ValidationResult(code_id=code_id)

        # Stage 1: Syntax validation
        syntax_result = self._check_syntax(code, language)
        result.syntax_valid = syntax_result[0]
        if not result.syntax_valid:
            result.issues.append(syntax_result[1])
            result.validation_time_ms = (time.time() - start_time) * 1000
            await self._emit_validation_result(result)
            return result

        await self.thinking("Syntax valid. Checking for patterns...")

        # Stage 2: Pattern detection
        patterns = self._detect_patterns(code)
        result.patterns_detected = [p.name for p in patterns]

        # Stage 3: Security analysis
        security_issues = self._check_security(code)
        for issue_name, severity, description in security_issues:
            if severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]:
                result.issues.append(f"🚨 {severity.value.upper()}: {description}")
            else:
                result.suggestions.append(f"⚠️ {description}")

        # Stage 4: Complexity analysis
        result.complexity_score = self._calculate_complexity(code)
        if result.complexity_score > 15:
            result.suggestions.append(
                f"High complexity score ({result.complexity_score}). Consider breaking into smaller functions."
            )

        # Stage 5: Execution
        await self.thinking("Executing code...")
        exec_result = await self.executor.execute(code, language)
        result.executes = exec_result.success
        result.execution_result = exec_result

        if not exec_result.success:
            result.issues.append(f"Execution failed: {exec_result.error}")
        else:
            await self.thinking("Execution successful!")

        # Record execution metric
        self.metrics.record_execution(ExecutionMetric(
            code_id=code_id,
            success=exec_result.success,
            execution_time_ms=exec_result.execution_time_ms,
            tier=exec_result.tier.value,
            memory_mb=exec_result.memory_usage_mb,
        ))

        # Stage 6: Test generation and execution
        if generate_tests and result.executes and language == "python":
            await self.thinking("Generating tests...")
            tests = self._generate_tests(code)
            result.tests_generated = len(tests)

            if tests:
                await self.thinking(f"Running {len(tests)} tests...")
                passed, failed = await self._run_tests(code, tests)
                result.tests_passed = passed
                result.tests_failed = failed

        result.validation_time_ms = (time.time() - start_time) * 1000

        # Record validation metric
        self.metrics.record_validation(ValidationMetric(
            code_id=code_id,
            syntax_valid=result.syntax_valid,
            executes=result.executes,
            tests_passed=result.tests_passed,
            tests_failed=result.tests_failed,
            patterns_detected=result.patterns_detected,
            validation_time_ms=result.validation_time_ms,
        ))

        # Record patterns
        for pattern_name in result.patterns_detected:
            self.metrics.record_pattern(pattern_name, result.overall_success)

        await self._emit_validation_result(result)
        return result

    def _check_syntax(self, code: str, language: str) -> Tuple[bool, str]:
        """Check code syntax"""
        if language == "python":
            try:
                ast.parse(code)
                return True, ""
            except SyntaxError as e:
                return False, f"Syntax error at line {e.lineno}: {e.msg}"
        # For other languages, assume valid (container will catch errors)
        return True, ""

    def _detect_patterns(self, code: str) -> List[CodePattern]:
        """Detect code patterns"""
        patterns = []
        for pattern_name, pattern_regex in PATTERN_DETECTORS.items():
            if re.search(pattern_regex, code, re.DOTALL | re.IGNORECASE):
                patterns.append(CodePattern(
                    pattern_id=pattern_name,
                    name=pattern_name.replace('_', ' ').title(),
                    category="functional",
                    description=f"Detected {pattern_name.replace('_', ' ')}",
                    confidence=0.9,
                ))
        return patterns

    def _check_security(self, code: str) -> List[Tuple[str, SeverityLevel, str]]:
        """Check for security issues"""
        issues = []
        for issue_name, (pattern, severity) in SECURITY_ISSUES.items():
            if re.search(pattern, code, re.IGNORECASE):
                description = issue_name.replace('_', ' ').title()
                issues.append((issue_name, severity, description))
        return issues

    def _calculate_complexity(self, code: str) -> int:
        """Calculate McCabe-like complexity"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return 0

        complexity = 1  # Base complexity
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                complexity += 1

        return complexity

    def _generate_tests(self, code: str) -> List[TestCase]:
        """Generate basic test cases for the code"""
        tests = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return tests

        # Find function definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                # Get argument names
                args = [arg.arg for arg in node.args.args]

                # Generate basic test cases based on function signature
                if args:
                    # Test with basic inputs
                    test_inputs = self._generate_test_inputs(args)
                    for i, inputs in enumerate(test_inputs):
                        tests.append(TestCase(
                            name=f"test_{func_name}_{i}",
                            input_data={"func": func_name, "args": inputs},
                        ))
                else:
                    # No args function
                    tests.append(TestCase(
                        name=f"test_{func_name}_no_args",
                        input_data={"func": func_name, "args": []},
                    ))

        return tests[:5]  # Limit to 5 tests

    def _generate_test_inputs(self, args: List[str]) -> List[List[Any]]:
        """Generate test inputs based on argument names"""
        inputs = []
        # Generate 3 test cases
        for i in range(3):
            case = []
            for arg in args:
                arg_lower = arg.lower()
                if 'num' in arg_lower or 'count' in arg_lower or 'n' == arg_lower:
                    case.append([0, 5, -1][i])
                elif 'str' in arg_lower or 'name' in arg_lower or 'text' in arg_lower:
                    case.append(["", "test", "hello world"][i])
                elif 'list' in arg_lower or 'items' in arg_lower or 'arr' in arg_lower:
                    case.append([[], [1, 2, 3], [1]][i])
                elif 'dict' in arg_lower or 'data' in arg_lower:
                    case.append([{}, {"a": 1}, {"key": "value"}][i])
                elif 'flag' in arg_lower or 'is_' in arg_lower or 'bool' in arg_lower:
                    case.append([True, False, True][i])
                else:
                    # Default to integer
                    case.append([0, 1, -1][i])
            inputs.append(case)
        return inputs

    async def _run_tests(
        self, code: str, tests: List[TestCase]
    ) -> Tuple[int, int]:
        """Run generated test cases"""
        passed = 0
        failed = 0

        for test in tests:
            try:
                func_name = test.input_data["func"]
                args = test.input_data["args"]

                # Create test code
                args_str = ", ".join(repr(a) for a in args)
                test_code = f"{code}\n\nresult = {func_name}({args_str})\nprint(repr(result))"

                # Execute test
                result = await self.executor.execute(test_code, timeout=2.0)

                if result.success:
                    test.passed = True
                    test.actual_output = result.output.strip()
                    passed += 1
                else:
                    test.passed = False
                    test.error = result.error
                    failed += 1

            except Exception as e:
                test.passed = False
                test.error = str(e)
                failed += 1

        return passed, failed

    async def _emit_validation_result(self, result: ValidationResult) -> None:
        """Emit validation complete event"""
        await self.emit(EventType.CODE_VALIDATED, {
            "code_id": result.code_id,
            "syntax_valid": result.syntax_valid,
            "executes": result.executes,
            "tests_passed": result.tests_passed,
            "tests_failed": result.tests_failed,
            "tests_generated": result.tests_generated,
            "patterns_detected": result.patterns_detected,
            "issues": result.issues,
            "suggestions": result.suggestions,
            "complexity_score": result.complexity_score,
            "validation_time_ms": result.validation_time_ms,
            "overall_success": result.overall_success,
            "execution_time_ms": (
                result.execution_result.execution_time_ms
                if result.execution_result else 0
            ),
            "execution_output": (
                result.execution_result.output[:500]
                if result.execution_result else ""
            ),
        })

    def format_report(self, result: ValidationResult) -> str:
        """Format a human-readable validation report"""
        lines = []
        lines.append(f"🃏 Jester Validation Report")
        lines.append(f"{'=' * 40}")

        # Status
        if result.overall_success:
            lines.append("✅ Overall: PASSED")
        else:
            lines.append("❌ Overall: FAILED")

        lines.append("")

        # Details
        lines.append(f"📝 Syntax: {'✅ Valid' if result.syntax_valid else '❌ Invalid'}")
        lines.append(f"⚡ Executes: {'✅ Yes' if result.executes else '❌ No'}")

        if result.execution_result:
            lines.append(
                f"⏱️  Time: {result.execution_result.execution_time_ms:.1f}ms "
                f"({result.execution_result.tier.value})"
            )

        if result.tests_generated > 0:
            lines.append(
                f"🧪 Tests: {result.tests_passed}/{result.tests_generated} passed"
            )

        lines.append(f"📊 Complexity: {result.complexity_score}")

        if result.patterns_detected:
            lines.append(f"🔍 Patterns: {', '.join(result.patterns_detected[:5])}")

        if result.issues:
            lines.append("")
            lines.append("⚠️ Issues:")
            for issue in result.issues:
                lines.append(f"  • {issue}")

        if result.suggestions:
            lines.append("")
            lines.append("💡 Suggestions:")
            for suggestion in result.suggestions:
                lines.append(f"  • {suggestion}")

        lines.append("")
        lines.append(f"Total validation time: {result.validation_time_ms:.1f}ms")

        return "\n".join(lines)
