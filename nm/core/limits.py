from __future__ import annotations
import os
import sqlite3
from datetime import date


class LimitTracker:
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = os.environ.get("NM_LIMITS_DB")
        if db_path is None:
            db_dir = os.path.join(os.path.dirname(__file__), "..", "db")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "limits.sqlite")
        self._db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_counts (
                    category TEXT,
                    day TEXT,
                    count INTEGER DEFAULT 0,
                    PRIMARY KEY (category, day)
                )
            """)

    def _today(self) -> str:
        return date.today().isoformat()

    def get_count(self, category: str) -> int:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT count FROM daily_counts WHERE category = ? AND day = ?",
                (category, self._today()),
            ).fetchone()
            return row[0] if row else 0

    def check_and_increment(self, category: str, max_limit: int | None) -> bool:
        if max_limit is None:
            return True
        with sqlite3.connect(self._db_path) as conn:
            current = self.get_count(category)
            if current >= max_limit:
                return False
            conn.execute(
                """INSERT INTO daily_counts (category, day, count) VALUES (?, ?, 1)
                   ON CONFLICT(category, day) DO UPDATE SET count = count + 1""",
                (category, self._today()),
            )
            return True

    def reset_all(self):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM daily_counts")

    def status_report(self, limits: dict) -> str:
        lines = []
        for category, max_limit in sorted(limits.items()):
            current = self.get_count(category)
            lines.append(f"{category}: {current}/{max_limit}")
        return " | ".join(lines)
