"""
Metrics Collection for Code Jester
Tracks execution times, success rates, and patterns
"""

import sqlite3
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import defaultdict
import threading


@dataclass
class ExecutionMetric:
    """Single execution metric"""
    code_id: str
    success: bool
    execution_time_ms: float
    tier: str
    memory_mb: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ValidationMetric:
    """Validation cycle metric"""
    code_id: str
    syntax_valid: bool
    executes: bool
    tests_passed: int
    tests_failed: int
    patterns_detected: List[str] = field(default_factory=list)
    validation_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class MetricsCollector:
    """
    Collects and stores metrics for the Code Jester system.
    Uses SQLite for persistence.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("storage/metrics.db")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._in_memory_metrics: Dict[str, List[Dict]] = defaultdict(list)

        # Initialize database
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database"""
        with sqlite3.connect(str(self.storage_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code_id TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    execution_time_ms REAL NOT NULL,
                    tier TEXT NOT NULL,
                    memory_mb REAL DEFAULT 0,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS validations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code_id TEXT NOT NULL,
                    syntax_valid INTEGER NOT NULL,
                    executes INTEGER NOT NULL,
                    tests_passed INTEGER DEFAULT 0,
                    tests_failed INTEGER DEFAULT 0,
                    patterns TEXT DEFAULT '[]',
                    validation_time_ms REAL DEFAULT 0,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_name TEXT NOT NULL,
                    occurrences INTEGER DEFAULT 1,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    last_seen TEXT NOT NULL
                )
            """)
            conn.commit()

    def record_execution(self, metric: ExecutionMetric) -> None:
        """Record an execution metric"""
        with self._lock:
            self._in_memory_metrics["executions"].append({
                "code_id": metric.code_id,
                "success": metric.success,
                "execution_time_ms": metric.execution_time_ms,
                "tier": metric.tier,
                "memory_mb": metric.memory_mb,
                "timestamp": metric.timestamp.isoformat(),
            })

        with sqlite3.connect(str(self.storage_path)) as conn:
            conn.execute(
                """INSERT INTO executions
                   (code_id, success, execution_time_ms, tier, memory_mb, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    metric.code_id,
                    int(metric.success),
                    metric.execution_time_ms,
                    metric.tier,
                    metric.memory_mb,
                    metric.timestamp.isoformat(),
                ),
            )
            conn.commit()

    def record_validation(self, metric: ValidationMetric) -> None:
        """Record a validation metric"""
        with self._lock:
            self._in_memory_metrics["validations"].append({
                "code_id": metric.code_id,
                "syntax_valid": metric.syntax_valid,
                "executes": metric.executes,
                "tests_passed": metric.tests_passed,
                "tests_failed": metric.tests_failed,
                "patterns": metric.patterns_detected,
                "validation_time_ms": metric.validation_time_ms,
                "timestamp": metric.timestamp.isoformat(),
            })

        with sqlite3.connect(str(self.storage_path)) as conn:
            conn.execute(
                """INSERT INTO validations
                   (code_id, syntax_valid, executes, tests_passed, tests_failed,
                    patterns, validation_time_ms, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    metric.code_id,
                    int(metric.syntax_valid),
                    int(metric.executes),
                    metric.tests_passed,
                    metric.tests_failed,
                    json.dumps(metric.patterns_detected),
                    metric.validation_time_ms,
                    metric.timestamp.isoformat(),
                ),
            )
            conn.commit()

    def record_pattern(self, pattern_name: str, success: bool) -> None:
        """Record a pattern occurrence"""
        with sqlite3.connect(str(self.storage_path)) as conn:
            # Check if pattern exists
            result = conn.execute(
                "SELECT id, occurrences, success_count, failure_count FROM patterns WHERE pattern_name = ?",
                (pattern_name,),
            ).fetchone()

            if result:
                # Update existing pattern
                conn.execute(
                    """UPDATE patterns SET
                       occurrences = occurrences + 1,
                       success_count = success_count + ?,
                       failure_count = failure_count + ?,
                       last_seen = ?
                       WHERE id = ?""",
                    (int(success), int(not success), datetime.now().isoformat(), result[0]),
                )
            else:
                # Insert new pattern
                conn.execute(
                    """INSERT INTO patterns
                       (pattern_name, occurrences, success_count, failure_count, last_seen)
                       VALUES (?, 1, ?, ?, ?)""",
                    (pattern_name, int(success), int(not success), datetime.now().isoformat()),
                )
            conn.commit()

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get overall execution statistics"""
        with sqlite3.connect(str(self.storage_path)) as conn:
            total = conn.execute("SELECT COUNT(*) FROM executions").fetchone()[0]
            if total == 0:
                return {
                    "total_executions": 0,
                    "success_rate": 0.0,
                    "avg_execution_time_ms": 0.0,
                    "by_tier": {},
                }

            success = conn.execute(
                "SELECT COUNT(*) FROM executions WHERE success = 1"
            ).fetchone()[0]
            avg_time = conn.execute(
                "SELECT AVG(execution_time_ms) FROM executions"
            ).fetchone()[0]

            # By tier
            tier_stats = {}
            for row in conn.execute(
                """SELECT tier, COUNT(*), AVG(execution_time_ms),
                          SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END)
                   FROM executions GROUP BY tier"""
            ).fetchall():
                tier_stats[row[0]] = {
                    "count": row[1],
                    "avg_time_ms": row[2] or 0,
                    "success_count": row[3],
                }

            return {
                "total_executions": total,
                "success_rate": success / total if total > 0 else 0.0,
                "avg_execution_time_ms": avg_time or 0.0,
                "by_tier": tier_stats,
            }

    def get_pattern_stats(self) -> List[Dict[str, Any]]:
        """Get pattern statistics"""
        with sqlite3.connect(str(self.storage_path)) as conn:
            patterns = []
            for row in conn.execute(
                """SELECT pattern_name, occurrences, success_count, failure_count, last_seen
                   FROM patterns ORDER BY occurrences DESC"""
            ).fetchall():
                total = row[2] + row[3]
                patterns.append({
                    "name": row[0],
                    "occurrences": row[1],
                    "success_rate": row[2] / total if total > 0 else 0.0,
                    "last_seen": row[4],
                })
            return patterns

    def get_recent_metrics(self, limit: int = 10) -> Dict[str, List[Dict]]:
        """Get recent metrics for display"""
        with self._lock:
            return {
                "executions": self._in_memory_metrics["executions"][-limit:],
                "validations": self._in_memory_metrics["validations"][-limit:],
            }

    def clear_in_memory(self) -> None:
        """Clear in-memory metrics"""
        with self._lock:
            self._in_memory_metrics.clear()
