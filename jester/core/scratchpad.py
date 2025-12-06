"""
ScratchPad - The Laboratory Notebook
Stores code snippets, experiments, and half-baked ideas.
"""

import sqlite3
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

@dataclass
class Snippet:
    """A snippet of code in the scratchpad"""
    name: str
    code: str
    language: str
    created_at: str
    updated_at: str
    run_count: int = 0
    tags: List[str] = None
    last_result: Optional[str] = None

class ScratchPad:
    """
    Manages persistent code snippets.
    Backed by SQLite (same DB as metrics).
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("storage/metrics.db")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize snippets table"""
        with sqlite3.connect(str(self.storage_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snippets (
                    name TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    language TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    run_count INTEGER DEFAULT 0,
                    tags TEXT DEFAULT '[]',
                    last_result TEXT
                )
            """)
            conn.commit()

    def save_snippet(self, name: str, code: str, language: str = "python", tags: List[str] = None) -> None:
        """Save or update a snippet"""
        now = datetime.now().isoformat()
        tags_json = json.dumps(tags or [])
        
        with sqlite3.connect(str(self.storage_path)) as conn:
            # Upsert
            cursor = conn.execute("SELECT created_at FROM snippets WHERE name = ?", (name,))
            row = cursor.fetchone()
            
            if row:
                # Update
                conn.execute("""
                    UPDATE snippets 
                    SET code = ?, language = ?, updated_at = ?, tags = ?
                    WHERE name = ?
                """, (code, language, now, tags_json, name))
            else:
                # Insert
                conn.execute("""
                    INSERT INTO snippets (name, code, language, created_at, updated_at, tags)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (name, code, language, now, now, tags_json))
            conn.commit()

    def get_snippet(self, name: str) -> Optional[Snippet]:
        """Retrieve a snippet by name"""
        with sqlite3.connect(str(self.storage_path)) as conn:
            row = conn.execute(
                "SELECT name, code, language, created_at, updated_at, run_count, tags, last_result FROM snippets WHERE name = ?",
                (name,)
            ).fetchone()
            
            if not row:
                return None
                
            return Snippet(
                name=row[0],
                code=row[1],
                language=row[2],
                created_at=row[3],
                updated_at=row[4],
                run_count=row[5],
                tags=json.loads(row[6]),
                last_result=row[7]
            )

    def list_snippets(self) -> List[Dict[str, Any]]:
        """List all snippets (summary)"""
        with sqlite3.connect(str(self.storage_path)) as conn:
            rows = conn.execute(
                "SELECT name, language, updated_at, run_count FROM snippets ORDER BY updated_at DESC"
            ).fetchall()
            
            return [
                {
                    "name": r[0],
                    "language": r[1],
                    "updated_at": r[2],
                    "run_count": r[3]
                }
                for r in rows
            ]

    def record_run(self, name: str, result: str) -> None:
        """Update run count and last result"""
        with sqlite3.connect(str(self.storage_path)) as conn:
            conn.execute("""
                UPDATE snippets 
                SET run_count = run_count + 1, last_result = ?
                WHERE name = ?
            """, (result[:1000], name)) # Truncate result
            conn.commit()

    def delete_snippet(self, name: str) -> bool:
        """Delete a snippet"""
        with sqlite3.connect(str(self.storage_path)) as conn:
            res = conn.execute("DELETE FROM snippets WHERE name = ?", (name,))
            conn.commit()
            return res.rowcount > 0
