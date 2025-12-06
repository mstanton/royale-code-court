"""
Persistent storage for execution history and learned patterns.
Extends the existing MetricsCollector with learning capabilities.
"""

import ast
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.models import ValidationResult, ExecutionResult


class LearningStore:
    """
    Persistent storage for execution history and learned patterns.

    Provides:
    - Execution recording with code hashing for deduplication
    - Pattern extraction from successful code
    - Similar execution lookup
    - Training data export for fine-tuning
    """

    def __init__(self, db_path: str = "~/.royale-code-court/learning.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database with learning tables"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    code_hash TEXT NOT NULL,
                    code TEXT NOT NULL,
                    language TEXT DEFAULT 'python',
                    success INTEGER NOT NULL,
                    output TEXT,
                    error TEXT,
                    execution_time_ms REAL,
                    memory_mb REAL,
                    tier TEXT,
                    complexity_score INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT NOT NULL,
                    pattern_key TEXT UNIQUE NOT NULL,
                    description TEXT,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    avg_time_ms REAL DEFAULT 0,
                    common_errors TEXT DEFAULT '[]',
                    last_seen TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS code_entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    code_hash TEXT NOT NULL,
                    signature TEXT,
                    docstring TEXT,
                    complexity INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    avg_time_ms REAL DEFAULT 0,
                    last_seen TEXT NOT NULL,
                    UNIQUE(entity_type, name, code_hash)
                );

                CREATE TABLE IF NOT EXISTS error_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_type TEXT NOT NULL,
                    error_pattern TEXT NOT NULL,
                    occurrence_count INTEGER DEFAULT 1,
                    fix_suggestions TEXT DEFAULT '[]',
                    last_seen TEXT NOT NULL,
                    UNIQUE(error_type, error_pattern)
                );

                CREATE INDEX IF NOT EXISTS idx_code_hash ON executions(code_hash);
                CREATE INDEX IF NOT EXISTS idx_pattern_key ON patterns(pattern_key);
                CREATE INDEX IF NOT EXISTS idx_entity_name ON code_entities(name);
                CREATE INDEX IF NOT EXISTS idx_error_type ON error_patterns(error_type);
            """)

    def record_execution(
        self,
        code: str,
        result: ValidationResult,
        language: str = "python"
    ) -> int:
        """
        Record an execution for learning.

        Args:
            code: The code that was executed
            result: ValidationResult from the Jester
            language: Programming language

        Returns:
            The execution record ID
        """
        code_hash = self._hash_code(code)

        success = result.overall_success
        output = ""
        error = ""
        execution_time_ms = 0.0
        memory_mb = 0.0
        tier = "unknown"

        if result.execution_result:
            output = result.execution_result.output or ""
            error = result.execution_result.error or ""
            execution_time_ms = result.execution_result.execution_time_ms
            memory_mb = result.execution_result.memory_usage_mb
            tier = result.execution_result.tier.value

        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("""
                INSERT INTO executions
                (timestamp, code_hash, code, language, success, output, error,
                 execution_time_ms, memory_mb, tier, complexity_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                code_hash,
                code,
                language,
                1 if success else 0,
                output[:5000],  # Limit output size
                error[:5000],
                execution_time_ms,
                memory_mb,
                tier,
                result.complexity_score
            ))

            execution_id = cursor.lastrowid

        # Update patterns from successful executions
        if success:
            self._extract_and_update_patterns(code, result)
        else:
            self._record_error_pattern(error)

        return execution_id

    def _hash_code(self, code: str) -> str:
        """Generate a hash for code (for deduplication)"""
        # Normalize whitespace for consistent hashing
        normalized = " ".join(code.split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _extract_and_update_patterns(
        self,
        code: str,
        result: ValidationResult
    ) -> None:
        """Extract and update patterns from successful code"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return

        execution_time = 0.0
        if result.execution_result:
            execution_time = result.execution_result.execution_time_ms

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._update_entity(
                    "function",
                    node.name,
                    code,
                    self._get_function_signature(node),
                    ast.get_docstring(node),
                    result.complexity_score,
                    True,
                    execution_time
                )
            elif isinstance(node, ast.ClassDef):
                self._update_entity(
                    "class",
                    node.name,
                    code,
                    None,
                    ast.get_docstring(node),
                    result.complexity_score,
                    True,
                    execution_time
                )

        # Update detected patterns
        for pattern_name in result.patterns_detected:
            self._update_pattern(
                "functional",
                pattern_name,
                True,
                execution_time
            )

    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        """Extract function signature from AST node"""
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                try:
                    arg_str += f": {ast.unparse(arg.annotation)}"
                except:
                    pass
            args.append(arg_str)

        return_str = ""
        if node.returns:
            try:
                return_str = f" -> {ast.unparse(node.returns)}"
            except:
                pass

        return f"def {node.name}({', '.join(args)}){return_str}"

    def _update_entity(
        self,
        entity_type: str,
        name: str,
        code: str,
        signature: Optional[str],
        docstring: Optional[str],
        complexity: int,
        success: bool,
        execution_time: float
    ) -> None:
        """Update or create a code entity record"""
        code_hash = self._hash_code(code)

        with sqlite3.connect(str(self.db_path)) as conn:
            existing = conn.execute(
                """SELECT id, success_count, failure_count, avg_time_ms
                   FROM code_entities
                   WHERE entity_type = ? AND name = ? AND code_hash = ?""",
                (entity_type, name, code_hash)
            ).fetchone()

            if existing:
                new_success = existing[1] + (1 if success else 0)
                new_failure = existing[2] + (0 if success else 1)
                total = new_success + new_failure
                new_avg = ((existing[3] * (total - 1)) + execution_time) / total if total > 0 else 0

                conn.execute("""
                    UPDATE code_entities
                    SET success_count = ?, failure_count = ?, avg_time_ms = ?, last_seen = ?
                    WHERE id = ?
                """, (new_success, new_failure, new_avg, datetime.now().isoformat(), existing[0]))
            else:
                conn.execute("""
                    INSERT INTO code_entities
                    (entity_type, name, code_hash, signature, docstring, complexity,
                     success_count, failure_count, avg_time_ms, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entity_type,
                    name,
                    code_hash,
                    signature,
                    docstring[:1000] if docstring else None,
                    complexity,
                    1 if success else 0,
                    0 if success else 1,
                    execution_time,
                    datetime.now().isoformat()
                ))

    def _update_pattern(
        self,
        pattern_type: str,
        pattern_key: str,
        success: bool,
        execution_time: float
    ) -> None:
        """Update pattern statistics"""
        with sqlite3.connect(str(self.db_path)) as conn:
            existing = conn.execute(
                "SELECT id, success_count, failure_count, avg_time_ms FROM patterns WHERE pattern_key = ?",
                (pattern_key,)
            ).fetchone()

            if existing:
                new_success = existing[1] + (1 if success else 0)
                new_failure = existing[2] + (0 if success else 1)
                total = new_success + new_failure
                new_avg = ((existing[3] * (total - 1)) + execution_time) / total if total > 0 else 0

                conn.execute("""
                    UPDATE patterns
                    SET success_count = ?, failure_count = ?, avg_time_ms = ?, last_seen = ?
                    WHERE pattern_key = ?
                """, (new_success, new_failure, new_avg, datetime.now().isoformat(), pattern_key))
            else:
                conn.execute("""
                    INSERT INTO patterns
                    (pattern_type, pattern_key, success_count, failure_count, avg_time_ms, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    pattern_type,
                    pattern_key,
                    1 if success else 0,
                    0 if success else 1,
                    execution_time,
                    datetime.now().isoformat()
                ))

    def _record_error_pattern(self, error: str) -> None:
        """Record an error pattern for learning"""
        if not error:
            return

        # Extract error type
        error_type = "Unknown"
        if ":" in error:
            error_type = error.split(":")[0].split()[-1]

        # Normalize error for pattern matching
        # Remove specific file paths and line numbers
        import re
        normalized = re.sub(r'File "[^"]+", line \d+', 'File "...", line N', error)
        normalized = re.sub(r'line \d+', 'line N', normalized)

        with sqlite3.connect(str(self.db_path)) as conn:
            existing = conn.execute(
                "SELECT id, occurrence_count FROM error_patterns WHERE error_type = ? AND error_pattern = ?",
                (error_type, normalized[:500])
            ).fetchone()

            if existing:
                conn.execute("""
                    UPDATE error_patterns
                    SET occurrence_count = occurrence_count + 1, last_seen = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), existing[0]))
            else:
                conn.execute("""
                    INSERT INTO error_patterns
                    (error_type, error_pattern, occurrence_count, last_seen)
                    VALUES (?, ?, 1, ?)
                """, (error_type, normalized[:500], datetime.now().isoformat()))

    def get_similar_executions(self, code: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar past executions by code hash"""
        code_hash = self._hash_code(code)

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM executions
                WHERE code_hash = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (code_hash, limit)).fetchall()

            return [dict(row) for row in rows]

    def get_function_stats(self, function_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a function by name"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT * FROM code_entities
                WHERE entity_type = 'function' AND name = ?
                ORDER BY last_seen DESC LIMIT 1
            """, (function_name,)).fetchone()

            return dict(row) if row else None

    def get_pattern_stats(self, pattern_key: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a pattern"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM patterns WHERE pattern_key = ?",
                (pattern_key,)
            ).fetchone()

            return dict(row) if row else None

    def get_common_errors(self, error_type: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get common error patterns for an error type"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM error_patterns
                WHERE error_type = ?
                ORDER BY occurrence_count DESC LIMIT ?
            """, (error_type, limit)).fetchall()

            return [dict(row) for row in rows]

    def export_training_data(self, output_path: str, min_success_count: int = 1) -> int:
        """
        Export successful executions for fine-tuning.

        Exports data in JSONL format suitable for LLM fine-tuning:
        {"instruction": "...", "input": "...", "output": "..."}

        Args:
            output_path: Path to write JSONL file
            min_success_count: Minimum success count to include

        Returns:
            Number of records exported
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute("""
                SELECT code, output, complexity_score FROM executions
                WHERE success = 1
                ORDER BY timestamp DESC
            """).fetchall()

        count = 0
        with open(output_path, 'w') as f:
            for code, output, complexity in rows:
                # Skip very simple or empty code
                if len(code.strip()) < 20:
                    continue

                training_item = {
                    "instruction": "Write Python code that performs the described task",
                    "input": f"Task: Write working Python code\nExpected behavior: Produces output similar to:\n{output[:200] if output else '(no output)'}",
                    "output": code
                }
                f.write(json.dumps(training_item) + "\n")
                count += 1

        return count

    def get_global_stats(self) -> Dict[str, Any]:
        """Get overall learning statistics"""
        with sqlite3.connect(str(self.db_path)) as conn:
            total = conn.execute("SELECT COUNT(*) FROM executions").fetchone()[0]
            success = conn.execute("SELECT COUNT(*) FROM executions WHERE success = 1").fetchone()[0]
            patterns = conn.execute("SELECT COUNT(*) FROM patterns").fetchone()[0]
            entities = conn.execute("SELECT COUNT(*) FROM code_entities").fetchone()[0]
            error_patterns = conn.execute("SELECT COUNT(*) FROM error_patterns").fetchone()[0]

            avg_time = conn.execute(
                "SELECT AVG(execution_time_ms) FROM executions WHERE success = 1"
            ).fetchone()[0] or 0

            return {
                "total_executions": total,
                "successful_executions": success,
                "success_rate": success / total if total > 0 else 0,
                "learned_patterns": patterns,
                "code_entities": entities,
                "error_patterns": error_patterns,
                "avg_success_time_ms": avg_time
            }

    def cleanup_old_records(self, days: int = 30) -> int:
        """Remove execution records older than specified days"""
        from datetime import timedelta

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "DELETE FROM executions WHERE timestamp < ?",
                (cutoff,)
            )
            return cursor.rowcount
