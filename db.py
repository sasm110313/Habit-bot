"""
🗄️ Database Module for Habit Bot v3.0
ماژول دیتابیس
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional
from config import DB_PATH, HABIT_ORDER


class Database:
    """SQLite database manager."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        conn = self._conn()
        try:
            conn.executescript("""
                -- کاربران
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT DEFAULT '',
                    first_name TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    is_paused INTEGER DEFAULT 0,
                    course_session INTEGER DEFAULT 1,
                    course_chelle INTEGER DEFAULT 1,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    total_perfect_days INTEGER DEFAULT 0,
                    total_habits_done INTEGER DEFAULT 0,
                    total_journals INTEGER DEFAULT 0,
                    last_active_date TEXT DEFAULT ''
                );

                -- لاگ عادت‌ها
                CREATE TABLE IF NOT EXISTS habit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    habit_key TEXT NOT NULL,
                    date TEXT NOT NULL,
                    level TEXT NOT NULL,
                    completed_at TEXT DEFAULT (datetime('now','localtime')),
                    xp_earned INTEGER DEFAULT 0,
                    UNIQUE(user_id, habit_key, date)
                );

                -- لاگ دوره آموزشی
                CREATE TABLE IF NOT EXISTS course_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    session_number INTEGER DEFAULT 0,
                    watched INTEGER DEFAULT 1,
                    completed_at TEXT DEFAULT (datetime('now','localtime')),
                    xp_earned INTEGER DEFAULT 0,
                    UNIQUE(user_id, date)
                );

                -- استریک‌ها
                CREATE TABLE IF NOT EXISTS streaks (
                    user_id INTEGER NOT NULL,
                    streak_type TEXT NOT NULL,
                    current_streak INTEGER DEFAULT 0,
                    best_streak INTEGER DEFAULT 0,
                    last_date TEXT DEFAULT '',
                    PRIMARY KEY(user_id, streak_type)
                );

                -- دستاوردها
                CREATE TABLE IF NOT EXISTS achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    achievement_key TEXT NOT NULL,
                    unlocked_at TEXT DEFAULT (datetime('now','localtime')),
                    UNIQUE(user_id, achievement_key)
                );

                -- ژورنال/تحلیل شبانه
                CREATE TABLE IF NOT EXISTS journals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    content TEXT DEFAULT '',
                    mood_score INTEGER DEFAULT 0,
                    written_at TEXT DEFAULT (datetime('now','localtime')),
                    xp_earned INTEGER DEFAULT 0,
                    UNIQUE(user_id, date)
                );

                -- لاگ XP
                CREATE TABLE IF NOT EXISTS xp_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    reason TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                );

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_habit_logs_user_date ON habit_logs(user_id, date);
                CREATE INDEX IF NOT EXISTS idx_course_logs_user_date ON course_logs(user_id, date);
                CREATE INDEX IF NOT EXISTS idx_journals_user_date ON journals(user_id, date);
                CREATE INDEX IF NOT EXISTS idx_xp_logs_user ON xp_logs(user_id);
            """)
            conn.commit()
        finally:
            conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # User Operations
    # ══════════════════════════════════════════════════════════════════════════

    def get_or_create_user(self, user_id: int, username: str = "", first_name: str = "") -> dict:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                    (user_id, username, first_name),
                )
                # Initialize streaks for all habits + course + overall
                for key in HABIT_ORDER:
                    conn.execute(
                        "INSERT OR IGNORE INTO streaks (user_id, streak_type) VALUES (?, ?)",
                        (user_id, key),
                    )
                conn.execute(
                    "INSERT OR IGNORE INTO streaks (user_id, streak_type) VALUES (?, ?)",
                    (user_id, "course"),
                )
                conn.execute(
                    "INSERT OR IGNORE INTO streaks (user_id, streak_type) VALUES (?, ?)",
                    (user_id, "perfect_day"),
                )
                conn.commit()
                row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row)
        finally:
            conn.close()

    def get_user(self, user_id: int) -> Optional[dict]:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_active_users(self) -> list:
        conn = self._conn()
        try:
            rows = conn.execute("SELECT user_id FROM users WHERE is_paused = 0").fetchall()
            return [r["user_id"] for r in rows]
        finally:
            conn.close()

    def set_paused(self, user_id: int, paused: bool):
        conn = self._conn()
        try:
            conn.execute("UPDATE users SET is_paused = ? WHERE user_id = ?", (1 if paused else 0, user_id))
            conn.commit()
        finally:
            conn.close()

    def update_user(self, user_id: int, **kwargs):
        conn = self._conn()
        try:
            fields = ", ".join(f"{k} = ?" for k in kwargs)
            values = list(kwargs.values()) + [user_id]
            conn.execute(f"UPDATE users SET {fields} WHERE user_id = ?", values)
            conn.commit()
        finally:
            conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # XP Operations
    # ══════════════════════════════════════════════════════════════════════════

    def add_xp(self, user_id: int, amount: int, reason: str = "") -> int:
        """Add XP and return new total."""
        conn = self._conn()
        try:
            conn.execute(
                "UPDATE users SET xp = xp + ? WHERE user_id = ?", (amount, user_id)
            )
            conn.execute(
                "INSERT INTO xp_logs (user_id, amount, reason) VALUES (?, ?, ?)",
                (user_id, amount, reason),
            )
            conn.commit()
            row = conn.execute("SELECT xp FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return row["xp"] if row else 0
        finally:
            conn.close()

    def set_level(self, user_id: int, level: int):
        conn = self._conn()
        try:
            conn.execute("UPDATE users SET level = ? WHERE user_id = ?", (level, user_id))
            conn.commit()
        finally:
            conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # Habit Operations
    # ══════════════════════════════════════════════════════════════════════════

    def log_habit(self, user_id: int, habit_key: str, date: str, level: str, xp: int) -> dict:
        """
        Log or update a habit. Returns:
        {"action": "logged"|"changed"|"removed", "old_level": str|None}
        """
        conn = self._conn()
        try:
            existing = conn.execute(
                "SELECT * FROM habit_logs WHERE user_id = ? AND habit_key = ? AND date = ?",
                (user_id, habit_key, date),
            ).fetchone()

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if existing:
                old_level = existing["level"]
                if old_level == level:
                    # Toggle off
                    conn.execute(
                        "DELETE FROM habit_logs WHERE user_id = ? AND habit_key = ? AND date = ?",
                        (user_id, habit_key, date),
                    )
                    conn.commit()
                    return {"action": "removed", "old_level": old_level}
                else:
                    # Change level
                    conn.execute(
                        """UPDATE habit_logs SET level = ?, completed_at = ?, xp_earned = ?
                           WHERE user_id = ? AND habit_key = ? AND date = ?""",
                        (level, now, xp, user_id, habit_key, date),
                    )
                    conn.commit()
                    return {"action": "changed", "old_level": old_level}
            else:
                # New log
                conn.execute(
                    """INSERT INTO habit_logs (user_id, habit_key, date, level, completed_at, xp_earned)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (user_id, habit_key, date, level, now, xp),
                )
                conn.execute(
                    "UPDATE users SET total_habits_done = total_habits_done + 1 WHERE user_id = ?",
                    (user_id,),
                )
                conn.commit()
                return {"action": "logged", "old_level": None}
        finally:
            conn.close()

    def get_today_habits(self, user_id: int, date: str) -> dict:
        """Get all habits status for today. Returns {habit_key: row_dict or None}"""
        conn = self._conn()
        try:
            result = {}
            for key in HABIT_ORDER:
                row = conn.execute(
                    "SELECT * FROM habit_logs WHERE user_id = ? AND habit_key = ? AND date = ?",
                    (user_id, key, date),
                ).fetchone()
                result[key] = dict(row) if row else None
            return result
        finally:
            conn.close()

    def count_habits_today(self, user_id: int, date: str) -> int:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as c FROM habit_logs WHERE user_id = ? AND date = ?",
                (user_id, date),
            ).fetchone()
            return row["c"]
        finally:
            conn.close()

    def count_emergency_habits(self, user_id: int) -> int:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as c FROM habit_logs WHERE user_id = ? AND level = 'emergency'",
                (user_id,),
            ).fetchone()
            return row["c"]
        finally:
            conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # Course Operations
    # ══════════════════════════════════════════════════════════════════════════

    def log_course(self, user_id: int, date: str, session_number: int, xp: int) -> bool:
        """Log course watching. Returns True if newly logged."""
        conn = self._conn()
        try:
            existing = conn.execute(
                "SELECT * FROM course_logs WHERE user_id = ? AND date = ?",
                (user_id, date),
            ).fetchone()

            if existing:
                # Toggle off
                conn.execute("DELETE FROM course_logs WHERE user_id = ? AND date = ?", (user_id, date))
                # Decrement session
                conn.execute(
                    "UPDATE users SET course_session = course_session - 1 WHERE user_id = ? AND course_session > 1",
                    (user_id,),
                )
                conn.commit()
                return False
            else:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.execute(
                    """INSERT INTO course_logs (user_id, date, session_number, watched, completed_at, xp_earned)
                       VALUES (?, ?, ?, 1, ?, ?)""",
                    (user_id, date, session_number, now, xp),
                )
                # Advance session
                conn.execute(
                    "UPDATE users SET course_session = ? WHERE user_id = ?",
                    (session_number + 1, user_id),
                )
                # Update chelle
                chelle = (session_number // 40) + 1
                conn.execute(
                    "UPDATE users SET course_chelle = ? WHERE user_id = ?",
                    (min(chelle, 9), user_id),
                )
                conn.commit()
                return True
        finally:
            conn.close()

    def get_course_today(self, user_id: int, date: str) -> Optional[dict]:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM course_logs WHERE user_id = ? AND date = ?",
                (user_id, date),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def set_course_session(self, user_id: int, session: int):
        conn = self._conn()
        try:
            chelle = (session // 40) + 1
            conn.execute(
                "UPDATE users SET course_session = ?, course_chelle = ? WHERE user_id = ?",
                (session, min(chelle, 9), user_id),
            )
            conn.commit()
        finally:
            conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # Streak Operations
    # ══════════════════════════════════════════════════════════════════════════

    def update_streak(self, user_id: int, streak_type: str, date: str) -> dict:
        """Recalculate streak. Returns {"current": int, "best": int, "new_best": bool}"""
        conn = self._conn()
        try:
            # Get dates based on streak type
            if streak_type in HABIT_ORDER:
                rows = conn.execute(
                    "SELECT DISTINCT date FROM habit_logs WHERE user_id = ? AND habit_key = ? ORDER BY date DESC",
                    (user_id, streak_type),
                ).fetchall()
            elif streak_type == "course":
                rows = conn.execute(
                    "SELECT DISTINCT date FROM course_logs WHERE user_id = ? AND watched = 1 ORDER BY date DESC",
                    (user_id,),
                ).fetchall()
            elif streak_type == "perfect_day":
                # Days with all 3 habits done
                rows = conn.execute(
                    """SELECT date FROM habit_logs WHERE user_id = ?
                       GROUP BY date HAVING COUNT(DISTINCT habit_key) >= 3
                       ORDER BY date DESC""",
                    (user_id,),
                ).fetchall()
            else:
                return {"current": 0, "best": 0, "new_best": False}

            if not rows:
                conn.execute(
                    """INSERT INTO streaks (user_id, streak_type, current_streak, best_streak, last_date)
                       VALUES (?, ?, 0, 0, '') ON CONFLICT(user_id, streak_type)
                       DO UPDATE SET current_streak = 0""",
                    (user_id, streak_type),
                )
                conn.commit()
                return {"current": 0, "best": 0, "new_best": False}

            # Calculate streak
            streak = 0
            today = datetime.strptime(date, "%Y-%m-%d").date()
            expected = today

            for row in rows:
                log_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
                if log_date == expected:
                    streak += 1
                    expected -= timedelta(days=1)
                elif log_date == today - timedelta(days=1) and streak == 0:
                    expected = log_date
                    streak += 1
                    expected -= timedelta(days=1)
                else:
                    break

            # Get current best
            old = conn.execute(
                "SELECT best_streak FROM streaks WHERE user_id = ? AND streak_type = ?",
                (user_id, streak_type),
            ).fetchone()
            old_best = old["best_streak"] if old else 0
            new_best = streak > old_best
            best = max(old_best, streak)

            conn.execute(
                """INSERT INTO streaks (user_id, streak_type, current_streak, best_streak, last_date)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, streak_type) DO UPDATE SET
                   current_streak = ?, best_streak = ?, last_date = ?""",
                (user_id, streak_type, streak, best, date, streak, best, date),
            )
            conn.commit()
            return {"current": streak, "best": best, "new_best": new_best}
        finally:
            conn.close()

    def get_streak(self, user_id: int, streak_type: str) -> dict:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM streaks WHERE user_id = ? AND streak_type = ?",
                (user_id, streak_type),
            ).fetchone()
            if row:
                return {"current": row["current_streak"], "best": row["best_streak"]}
            return {"current": 0, "best": 0}
        finally:
            conn.close()

    def get_all_streaks(self, user_id: int) -> dict:
        result = {}
        for key in HABIT_ORDER + ["course", "perfect_day"]:
            result[key] = self.get_streak(user_id, key)
        return result

    # ══════════════════════════════════════════════════════════════════════════
    # Achievement Operations
    # ══════════════════════════════════════════════════════════════════════════

    def has_achievement(self, user_id: int, key: str) -> bool:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT 1 FROM achievements WHERE user_id = ? AND achievement_key = ?",
                (user_id, key),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def unlock_achievement(self, user_id: int, key: str) -> bool:
        """Unlock an achievement. Returns True if newly unlocked."""
        conn = self._conn()
        try:
            try:
                conn.execute(
                    "INSERT INTO achievements (user_id, achievement_key) VALUES (?, ?)",
                    (user_id, key),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False  # Already unlocked
        finally:
            conn.close()

    def get_achievements(self, user_id: int) -> list:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM achievements WHERE user_id = ? ORDER BY unlocked_at DESC",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # Journal Operations
    # ══════════════════════════════════════════════════════════════════════════

    def save_journal(self, user_id: int, date: str, content: str, mood: int = 0, xp: int = 0) -> bool:
        """Save journal entry. Returns True if new."""
        conn = self._conn()
        try:
            existing = conn.execute(
                "SELECT * FROM journals WHERE user_id = ? AND date = ?", (user_id, date)
            ).fetchone()

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if existing:
                conn.execute(
                    "UPDATE journals SET content = ?, mood_score = ?, written_at = ? WHERE user_id = ? AND date = ?",
                    (content, mood, now, user_id, date),
                )
                conn.commit()
                return False
            else:
                conn.execute(
                    "INSERT INTO journals (user_id, date, content, mood_score, written_at, xp_earned) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, date, content, mood, now, xp),
                )
                conn.execute(
                    "UPDATE users SET total_journals = total_journals + 1 WHERE user_id = ?",
                    (user_id,),
                )
                conn.commit()
                return True
        finally:
            conn.close()

    def get_journal(self, user_id: int, date: str) -> Optional[dict]:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM journals WHERE user_id = ? AND date = ?", (user_id, date)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_recent_journals(self, user_id: int, days: int = 10) -> list:
        conn = self._conn()
        try:
            since = (datetime.now().date() - timedelta(days=days)).isoformat()
            rows = conn.execute(
                "SELECT * FROM journals WHERE user_id = ? AND date >= ? ORDER BY date DESC",
                (user_id, since),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # Statistics
    # ══════════════════════════════════════════════════════════════════════════

    def get_weekly_stats(self, user_id: int) -> dict:
        conn = self._conn()
        try:
            today = datetime.now().date()
            week_ago = (today - timedelta(days=6)).isoformat()
            today_s = today.isoformat()

            total_habits = conn.execute(
                "SELECT COUNT(*) as c FROM habit_logs WHERE user_id = ? AND date >= ? AND date <= ?",
                (user_id, week_ago, today_s),
            ).fetchone()["c"]

            # Per habit
            per_habit = {}
            for key in HABIT_ORDER:
                per_habit[key] = conn.execute(
                    "SELECT COUNT(*) as c FROM habit_logs WHERE user_id = ? AND habit_key = ? AND date >= ? AND date <= ?",
                    (user_id, key, week_ago, today_s),
                ).fetchone()["c"]

            # Perfect days
            perfect = conn.execute(
                """SELECT COUNT(*) as c FROM (
                    SELECT date FROM habit_logs WHERE user_id = ? AND date >= ? AND date <= ?
                    GROUP BY date HAVING COUNT(DISTINCT habit_key) >= 3
                )""",
                (user_id, week_ago, today_s),
            ).fetchone()["c"]

            # Course days
            course_days = conn.execute(
                "SELECT COUNT(*) as c FROM course_logs WHERE user_id = ? AND date >= ? AND date <= ?",
                (user_id, week_ago, today_s),
            ).fetchone()["c"]

            # XP earned this week
            xp_week = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) as s FROM xp_logs WHERE user_id = ? AND created_at >= ?",
                (user_id, week_ago),
            ).fetchone()["s"]

            # Level breakdown
            levels = {}
            for lvl in ["small", "special", "emergency"]:
                levels[lvl] = conn.execute(
                    "SELECT COUNT(*) as c FROM habit_logs WHERE user_id = ? AND level = ? AND date >= ? AND date <= ?",
                    (user_id, lvl, week_ago, today_s),
                ).fetchone()["c"]

            return {
                "total_possible": 21,
                "total_done": total_habits,
                "percentage": round(total_habits / 21 * 100) if 21 > 0 else 0,
                "per_habit": per_habit,
                "perfect_days": perfect,
                "course_days": course_days,
                "xp_earned": xp_week,
                "levels": levels,
            }
        finally:
            conn.close()

    def get_chelle_stats(self, user_id: int, chelle_num: int) -> dict:
        """Stats for a specific chelle (40-day period)."""
        conn = self._conn()
        try:
            # This is approximate - based on registration date + chelle number
            user = self.get_user(user_id)
            if not user:
                return {}

            # Calculate date range for this chelle
            # For simplicity, use course_session to determine
            start_session = (chelle_num - 1) * 40 + 1
            end_session = chelle_num * 40

            total_course = conn.execute(
                "SELECT COUNT(*) as c FROM course_logs WHERE user_id = ? AND session_number >= ? AND session_number <= ?",
                (user_id, start_session, end_session),
            ).fetchone()["c"]

            return {
                "chelle": chelle_num,
                "course_done": total_course,
                "course_total": 40,
            }
        finally:
            conn.close()

    def get_total_stats(self, user_id: int) -> dict:
        conn = self._conn()
        try:
            user = self.get_user(user_id)
            if not user:
                return {}

            total_habits = conn.execute(
                "SELECT COUNT(*) as c FROM habit_logs WHERE user_id = ?", (user_id,)
            ).fetchone()["c"]

            total_course = conn.execute(
                "SELECT COUNT(*) as c FROM course_logs WHERE user_id = ?", (user_id,)
            ).fetchone()["c"]

            total_journals = conn.execute(
                "SELECT COUNT(*) as c FROM journals WHERE user_id = ?", (user_id,)
            ).fetchone()["c"]

            total_achievements = conn.execute(
                "SELECT COUNT(*) as c FROM achievements WHERE user_id = ?", (user_id,)
            ).fetchone()["c"]

            return {
                "xp": user["xp"],
                "level": user["level"],
                "total_habits": total_habits,
                "total_course": total_course,
                "total_journals": total_journals,
                "total_achievements": total_achievements,
                "course_session": user["course_session"],
                "course_chelle": user["course_chelle"],
            }
        finally:
            conn.close()

    def get_last_activity_date(self, user_id: int) -> Optional[str]:
        """Get the last date user logged anything."""
        conn = self._conn()
        try:
            row = conn.execute(
                """SELECT MAX(date) as last_date FROM (
                    SELECT date FROM habit_logs WHERE user_id = ?
                    UNION ALL
                    SELECT date FROM course_logs WHERE user_id = ?
                )""",
                (user_id, user_id),
            ).fetchone()
            return row["last_date"] if row and row["last_date"] else None
        finally:
            conn.close()
