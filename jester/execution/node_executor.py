"""
Node Executor - Executes JavaScript using Node.js
"""

import asyncio
import os
import tempfile
import time
from typing import Optional

from ..core.models import ExecutionResult, ExecutionTier

class NodeExecutor:
    """
    Executes JavaScript code using Node.js.
    """

    def __init__(self):
        self.default_timeout = 5.0

    async def execute(
        self,
        code: str,
        timeout: Optional[float] = None
    ) -> ExecutionResult:
        """
        Execute JavaScript code.
        """
        timeout = timeout or self.default_timeout
        start_time = time.time()

        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.js',
            delete=False
        ) as f:
            f.write(code)
            temp_path = f.name

        try:
            # Execute using node
            proc = await asyncio.create_subprocess_exec(
                "node", temp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
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
                error="Node.js executable not found. Please install Node.js.",
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
            try:
                os.unlink(temp_path)
            except OSError:
                pass
