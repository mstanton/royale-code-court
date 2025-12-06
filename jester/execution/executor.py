"""
Code Executor - Orchestrates tiered execution
Automatically selects the appropriate execution tier based on code analysis
"""

import ast
import re
import time
from dataclasses import dataclass
from typing import Optional, Set

from ..core.models import ExecutionResult, ExecutionTier, CodeSubmission
from ..core.event_stream import EventStream
from .repl_executor import REPLExecutor
from .container_executor import ContainerExecutor
try:
    from .tracer import ExecutionTracer
except ImportError:
    ExecutionTracer = None
# Also need Callable
from typing import Callable, Dict, Any


# Dangerous patterns that require container execution
CONTAINER_REQUIRED_PATTERNS = {
    # File system access
    r'\bopen\s*\(',
    r'\bwith\s+open',
    r'pathlib',
    r'os\.path',
    r'shutil\.',
    # Network access
    r'\brequests\.',
    r'\bhttpx\.',
    r'\burllib\.',
    r'\bsocket\.',
    r'\baiohttp\.',
    # Process/system access
    r'\bsubprocess\.',
    r'\bos\.system',
    r'\bos\.popen',
    r'\bos\.exec',
    # Complex imports
    r'\bimport\s+(?:pandas|numpy|scipy|sklearn)',
    r'\bfrom\s+(?:pandas|numpy|scipy|sklearn)',
}

# Absolutely blocked patterns (security risks)
BLOCKED_PATTERNS = {
    r'\beval\s*\([^)]*input',
    r'\bexec\s*\([^)]*input',
    r'__import__\s*\(\s*["\']os["\']\s*\)',
    r'rm\s+-rf\s+/',
    r'dd\s+if=',
}


@dataclass
class CodeAnalysis:
    """Result of static code analysis"""
    syntax_valid: bool
    error_message: str = ""
    complexity: int = 0
    requires_container: bool = False
    is_blocked: bool = False
    blocked_reason: str = ""
    imports: Set[str] = None
    functions: Set[str] = None
    classes: Set[str] = None

    def __post_init__(self):
        self.imports = self.imports or set()
        self.functions = self.functions or set()
        self.classes = self.classes or set()


class CodeExecutor:
    """
    Main code execution orchestrator.
    Selects appropriate tier and executes code safely.
    """

    def __init__(self, event_stream: Optional[EventStream] = None):
        self.event_stream = event_stream
        self.repl_executor = REPLExecutor()
        self.container_executor = ContainerExecutor()

        # Configuration
        self.max_execution_time = 5.0  # seconds
        self.max_memory_mb = 512

    def analyze_code(self, code: str, language: str = "python") -> CodeAnalysis:
        """
        Tier 1: Static analysis of code
        Returns analysis including syntax validity and security assessment
        """
        analysis = CodeAnalysis(syntax_valid=True)

        if language != "python":
            # For non-Python, just do pattern matching
            analysis.requires_container = True
            return analysis

        # Check for blocked patterns first
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                analysis.is_blocked = True
                analysis.blocked_reason = f"Blocked pattern detected: {pattern}"
                return analysis

        # Parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            analysis.syntax_valid = False
            analysis.error_message = f"Syntax error at line {e.lineno}: {e.msg}"
            return analysis

        # Extract information from AST
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    analysis.imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    analysis.imports.add(node.module.split('.')[0])
            elif isinstance(node, ast.FunctionDef):
                analysis.functions.add(node.name)
            elif isinstance(node, ast.ClassDef):
                analysis.classes.add(node.name)

        # Calculate complexity (simple McCabe-like)
        complexity = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        analysis.complexity = complexity

        # Check if container is required
        for pattern in CONTAINER_REQUIRED_PATTERNS:
            if re.search(pattern, code):
                analysis.requires_container = True
                break

        # Also check imports
        container_imports = {'pandas', 'numpy', 'scipy', 'sklearn', 'tensorflow', 'torch'}
        if analysis.imports & container_imports:
            analysis.requires_container = True

        return analysis

    async def execute(
        self,
        code: str,
        language: str = "python",
        force_tier: Optional[ExecutionTier] = None,
        timeout: Optional[float] = None,
        guard_callback: Optional[Callable[[Dict], None]] = None,
    ) -> ExecutionResult:
        """
        Execute code using the appropriate tier.

        Args:
            code: The code to execute
            language: Programming language
            force_tier: Force a specific execution tier
            timeout: Override default timeout

        Returns:
            ExecutionResult with output and metrics
        """
        start_time = time.time()
        timeout = timeout or self.max_execution_time

        # Tier 1: Static analysis
        analysis = self.analyze_code(code, language)

        if not analysis.syntax_valid:
            return ExecutionResult(
                success=False,
                error=analysis.error_message,
                execution_time_ms=(time.time() - start_time) * 1000,
                tier=ExecutionTier.STATIC,
            )

        if analysis.is_blocked:
            return ExecutionResult(
                success=False,
                error=f"Code blocked: {analysis.blocked_reason}",
                execution_time_ms=(time.time() - start_time) * 1000,
                tier=ExecutionTier.STATIC,
            )

        # Determine execution tier
        if force_tier:
            tier = force_tier
        elif analysis.requires_container:
            tier = ExecutionTier.CONTAINER
        else:
            tier = ExecutionTier.REPL

        # Emit event if stream available
        if self.event_stream:
            await self.event_stream.execution_start(code[:50] + "...", tier.value)

        # Execute based on tier
        if tier == ExecutionTier.REPL:
            result = await self._execute_repl(code, timeout, guard_callback)
        else:
            if guard_callback:
                # TODO: Implement tracing for container execution if possible
                pass
            result = await self._execute_container(code, language, timeout)

        # Set execution time
        result.execution_time_ms = (time.time() - start_time) * 1000
        result.tier = tier

        # Emit completion event
        if self.event_stream:
            await self.event_stream.execution_complete(
                code[:50] + "...",
                result.success,
                result.output[:200] if result.output else "",
                result.error[:200] if result.error else "",
                result.execution_time_ms,
            )

        return result

    async def _execute_repl(
        self, 
        code: str, 
        timeout: float, 
        guard_callback: Optional[Callable[[Dict], None]] = None
    ) -> ExecutionResult:
        """Execute using REPL (RestrictedPython)"""
        return await self.repl_executor.execute(code, timeout, guard_callback)

    async def _execute_container(
        self, code: str, language: str, timeout: float
    ) -> ExecutionResult:
        """Execute using container (Docker/Podman)"""
        return await self.container_executor.execute(code, language, timeout)

    def execute_sync(
        self,
        code: str,
        language: str = "python",
        force_tier: Optional[ExecutionTier] = None,
        timeout: Optional[float] = None,
    ) -> ExecutionResult:
        """Synchronous execution for non-async contexts"""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self.execute(code, language, force_tier, timeout)
        )
