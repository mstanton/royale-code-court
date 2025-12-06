"""
Trend Analyzer - Evolution Tracker
Analyzes execution history to find trends and improvements.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
import statistics

class TrendAnalyzer:
    """
    Analyzes historical metrics to track code evolution.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("storage/metrics.db")

    def analyze_function_evolution(self, code_id_prefix: str) -> Dict[str, Any]:
        """
        Analyze evolution of a function (grouping by code_id prefix or session).
        NOTE: This assumes code_ids are related (e.g. 'sort_algo_v1', 'sort_algo_v2').
        If we don't have explicit versioning, we might look at 'recent executions of snippets with same name'.
        For now, let's analyze by snippet name if referencing ScratchPad, or just recent executions.
        """
        # Placeholder for complex evolution tracking.
        # Currently Code Jester generates unique code_ids per run.
        # We can analyze GLOBAL trends or trends for a specific Session.
        pass

    def get_recent_performance_trend(self, limit: int = 20) -> Dict[str, Any]:
        """
        Analyze the last N executions to see if we are getting faster or slower.
        """
        with sqlite3.connect(str(self.storage_path)) as conn:
            rows = conn.execute("""
                SELECT execution_time_ms, success, timestamp 
                FROM executions 
                ORDER BY id DESC LIMIT ?
            """, (limit,)).fetchall()

        if not rows:
            return {"status": "insufficient_data"}

        times = [r[0] for r in rows if r[1]] # Only successful runs
        
        if len(times) < 5:
            return {"status": "insufficient_data"}

        # Reverse to chronological order (oldest first)
        times.reverse()
        
        # Simple trend: Compare first half avg vs second half avg
        mid = len(times) // 2
        first_half = times[:mid]
        second_half = times[mid:]
        
        avg_1 = statistics.mean(first_half)
        avg_2 = statistics.mean(second_half)
        
        improvement_pct = ((avg_1 - avg_2) / avg_1) * 100 if avg_1 > 0 else 0
        
        return {
            "status": "analyzed",
            "sample_size": len(times),
            "avg_ms_first_half": avg_1,
            "avg_ms_second_half": avg_2,
            "improvement_pct": improvement_pct,
            "trend": "improving" if improvement_pct > 5 else "regressing" if improvement_pct < -5 else "stable"
        }
