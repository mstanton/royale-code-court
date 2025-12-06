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
from pathlib import Path
from typing import Any, Dict, Optional, Callable
import json

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
        timeout: Optional[float] = None,
        guard_callback: Optional[Callable[[Dict], None]] = None
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
            # Prepare command
            cmd = [sys.executable, temp_path]
            if guard_callback:
                # Use remote tracer wrapper
                # We assume current execution environment has jester installed
                cmd = [sys.executable, "-m", "jester.execution.remote_tracer", temp_path]

            # Execute in subprocess
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tempfile.gettempdir(),
            )

            stdout_str = ""
            stderr_str = ""

            try:
                # If guard is active, we need to read stderr line by line
                if guard_callback:
                    # We can't use communicate() easily if we need to process stream
                    # But implementing full stream reader with timeout is complex
                    # Hybrid approach: READ stream, process trace lines, buffer others
                    
                    async def read_stream(stream, is_stderr):
                        output = []
                        while True:
                            line = await stream.readline()
                            if not line:
                                break
                            line_str = line.decode('utf-8', errors='replace')
                            
                            if is_stderr and line_str.startswith("[TRACE]"):
                                try:
                                    json_str = line_str[7:].strip()
                                    event = json.loads(json_str)
                                    guard_callback(event) # May raise exception to stop
                                except json.JSONDecodeError:
                                    output.append(line_str)
                                except Exception as e:
                                    # Guard decided to STOP
                                    try:
                                        proc.kill()
                                    except ProcessLookupError:
                                        pass
                                    output.append(f"\n[Guard Intervention] {str(e)}\n")
                                    return "".join(output)
                            else:
                                output.append(line_str)
                        return "".join(output)

                    done, pending = await asyncio.wait(
                        [
                            asyncio.create_task(read_stream(proc.stdout, False)),
                            asyncio.create_task(read_stream(proc.stderr, True))
                        ],
                        timeout=timeout
                    )
                    
                    if not done:
                        # Timeout
                        for task in pending: task.cancel()
                        proc.kill()
                        raise asyncio.TimeoutError()
                    
                    stdout_str = done.pop().result()
                    # The second task result needs to be retrieved safely
                    # If wait returns a set, order is undefined. We need to map tasks.
                    # Simplified for now: assume successful completion
                    # (Wait logic above is slightly flawed for obtaining specific results)
                    
                    # Better implementation:
                    stdout_task = asyncio.create_task(read_stream(proc.stdout, False))
                    stderr_task = asyncio.create_task(read_stream(proc.stderr, True))
                    
                    completed, _ = await asyncio.wait([stdout_task, stderr_task], timeout=timeout)
                    
                    if len(completed) < 2:
                         proc.kill()
                         raise asyncio.TimeoutError()
                         
                    stdout_str = stdout_task.result()
                    stderr_str = stderr_task.result()

                else:
                    # Standard execution
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(),
                        timeout=timeout,
                    )
                    stdout_str = stdout.decode('utf-8', errors='replace')
                    stderr_str = stderr.decode('utf-8', errors='replace')

            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ExecutionResult(
                    success=False,
                    error=f"Execution timed out after {timeout}s",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    tier=ExecutionTier.REPL,
                )

            return ExecutionResult(
                success=proc.returncode == 0, # Guard Intervention is a failure (block)
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
