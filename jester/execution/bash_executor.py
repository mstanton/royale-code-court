"""
Bash Executor - Executes Bash scripts securely
"""

import asyncio
import os
import sys
import tempfile
import time
from typing import Optional, Dict

from ..core.models import ExecutionResult, ExecutionTier

class BashExecutor:
    """
    Executes Bash scripts using subprocess.
    """

    def __init__(self):
        self.default_timeout = 5.0

    async def execute(
        self,
        code: str,
        timeout: Optional[float] = None
    ) -> ExecutionResult:
        """
        Execute Bash code.
        """
        timeout = timeout or self.default_timeout
        start_time = time.time()

        try:
            # Execute via stdin to avoid path mapping issues on Windows
            proc = await asyncio.create_subprocess_exec(
                "bash", 
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=code.encode('utf-8')),
                    timeout=timeout
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

        except FileNotFoundError:
             return ExecutionResult(
                success=False,
                error="Bash executable not found. Please install Git Bash or WSL.",
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
