"""
REPL Executor - Fast Python execution
Uses subprocess for isolated but fast execution
"""

import asyncio
import io
import os
import sys
import tempfile
import time
import traceback
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.models import ExecutionResult, ExecutionTier


# Safe modules that can be imported
ALLOWED_MODULES = {
    'math', 'random', 'string', 'json', 'datetime',
    'collections', 'itertools', 'functools', 're',
    'typing', 'dataclasses', 'enum', 'decimal', 'fractions',
}


class REPLExecutor:
    """
    Fast Python execution using subprocess.
    Executes code in an isolated process for safety.
    Typically executes in 50-200ms.
    """

    def __init__(self):
        self.default_timeout = 5.0  # 5 seconds default

    async def execute(
        self,
        code: str,
        timeout: Optional[float] = None
    ) -> ExecutionResult:
        """
        Execute Python code in an isolated subprocess.

        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds

        Returns:
            ExecutionResult with output and metrics
        """
        timeout = timeout or self.default_timeout
        start_time = time.time()

        # Create temporary file with the code
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False
        ) as f:
            f.write(code)
            temp_path = f.name

        try:
            # Execute in subprocess
            proc = await asyncio.create_subprocess_exec(
                sys.executable, temp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tempfile.gettempdir(),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ExecutionResult(
                    success=False,
                    error=f"Execution timed out after {timeout}s",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    tier=ExecutionTier.REPL,
                )

            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')

            return ExecutionResult(
                success=proc.returncode == 0,
                output=stdout_str,
                error=stderr_str,
                execution_time_ms=(time.time() - start_time) * 1000,
                tier=ExecutionTier.REPL,
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"{type(e).__name__}: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
                tier=ExecutionTier.REPL,
            )
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    def execute_sync(self, code: str, timeout: Optional[float] = None) -> ExecutionResult:
        """Synchronous execution wrapper"""
        return asyncio.get_event_loop().run_until_complete(self.execute(code, timeout))
