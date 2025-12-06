"""
Container Executor - Isolated code execution using Docker/Podman
For code that requires file I/O, network, or complex dependencies
"""

import asyncio
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional

from ..core.models import ExecutionResult, ExecutionTier


class ContainerExecutor:
    """
    Executes code in isolated containers.
    Falls back to subprocess if no container runtime available.
    """

    def __init__(self):
        self.runtime = self._detect_runtime()
        self.default_timeout = 5.0
        self.max_memory = "512m"
        self.max_cpu = "1"

        # Base images for each language
        self.images = {
            "python": "python:3.11-slim",
            "javascript": "node:20-slim",
            "bash": "bash:5.2",
        }

    def _detect_runtime(self) -> Optional[str]:
        """Detect available container runtime"""
        for runtime in ["podman", "docker"]:
            if shutil.which(runtime):
                return runtime
        return None

    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout: Optional[float] = None,
    ) -> ExecutionResult:
        """
        Execute code in a container.

        Args:
            code: Code to execute
            language: Programming language
            timeout: Maximum execution time

        Returns:
            ExecutionResult with output and metrics
        """
        timeout = timeout or self.default_timeout
        start_time = time.time()

        if not self.runtime:
            # Fall back to subprocess execution
            return await self._execute_subprocess(code, language, timeout)

        try:
            return await self._execute_container(code, language, timeout)
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Container execution failed: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
                tier=ExecutionTier.CONTAINER,
            )

    async def _execute_container(
        self,
        code: str,
        language: str,
        timeout: float,
    ) -> ExecutionResult:
        """Execute using container runtime"""
        start_time = time.time()

        # Create temp directory with code
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write code to file
            if language == "python":
                code_file = Path(tmpdir) / "code.py"
                cmd_in_container = ["python", "/code/code.py"]
            elif language == "javascript":
                code_file = Path(tmpdir) / "code.js"
                cmd_in_container = ["node", "/code/code.js"]
            elif language == "bash":
                code_file = Path(tmpdir) / "code.sh"
                cmd_in_container = ["bash", "/code/code.sh"]
            else:
                return ExecutionResult(
                    success=False,
                    error=f"Unsupported language: {language}",
                    tier=ExecutionTier.CONTAINER,
                )

            code_file.write_text(code)

            # Build container command
            image = self.images.get(language, self.images["python"])
            cmd = [
                self.runtime, "run",
                "--rm",
                "--network=none",  # No network access
                f"--memory={self.max_memory}",
                f"--cpus={self.max_cpu}",
                "--read-only",
                "-v", f"{tmpdir}:/code:ro",
                image,
            ] + cmd_in_container

            # Execute
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
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
                        tier=ExecutionTier.CONTAINER,
                    )

                return ExecutionResult(
                    success=proc.returncode == 0,
                    output=stdout.decode('utf-8', errors='replace'),
                    error=stderr.decode('utf-8', errors='replace'),
                    execution_time_ms=(time.time() - start_time) * 1000,
                    tier=ExecutionTier.CONTAINER,
                )

            except Exception as e:
                return ExecutionResult(
                    success=False,
                    error=f"Container error: {str(e)}",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    tier=ExecutionTier.CONTAINER,
                )

    async def _execute_subprocess(
        self,
        code: str,
        language: str,
        timeout: float,
    ) -> ExecutionResult:
        """Fallback execution using subprocess (less secure)"""
        start_time = time.time()

        with tempfile.TemporaryDirectory() as tmpdir:
            if language == "python":
                code_file = Path(tmpdir) / "code.py"
                cmd = ["python", str(code_file)]
            elif language == "javascript":
                code_file = Path(tmpdir) / "code.js"
                cmd = ["node", str(code_file)]
            elif language == "bash":
                code_file = Path(tmpdir) / "code.sh"
                cmd = ["bash", str(code_file)]
            else:
                return ExecutionResult(
                    success=False,
                    error=f"Unsupported language: {language}",
                    tier=ExecutionTier.CONTAINER,
                )

            code_file.write_text(code)

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=tmpdir,
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
                        tier=ExecutionTier.CONTAINER,
                    )

                return ExecutionResult(
                    success=proc.returncode == 0,
                    output=stdout.decode('utf-8', errors='replace'),
                    error=stderr.decode('utf-8', errors='replace'),
                    execution_time_ms=(time.time() - start_time) * 1000,
                    tier=ExecutionTier.CONTAINER,
                )

            except FileNotFoundError:
                return ExecutionResult(
                    success=False,
                    error=f"Interpreter for {language} not found",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    tier=ExecutionTier.CONTAINER,
                )
            except Exception as e:
                return ExecutionResult(
                    success=False,
                    error=f"Subprocess error: {str(e)}",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    tier=ExecutionTier.CONTAINER,
                )

    def is_container_available(self) -> bool:
        """Check if container runtime is available"""
        return self.runtime is not None
