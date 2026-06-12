#!/usr/bin/env python3
"""
🎯 ربات پیشرفته عادت‌سازی و یادآوری دوره آموزشی
Advanced Habit Tracker & Course Reminder Bot v2.0

سه عادت ثابت:
1. تمرکز در نماز (🕌)
2. خواب منظم (🌙)
3. ورزش (💪)

هر عادت سه سطح دارد:
- لقمه کوچک (حالت عادی) 🟢
- لقمه ویژه (یک درجه کمتر) 🟡
- لقمه اضطراری (شرایط خاص) 🔴
"""

import os
import sys
import logging
import sqlite3
from datetime import datetime, timedelta, time
from typing import Optional

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
DB_PATH = os.environ.get("HABIT_DB_PATH", "habit_bot.db")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Habit Definitions (Fixed - 3 habits, 3 levels each)
# ─────────────────────────────────────────────────────────────────────────────

HABITS = {
    "namaz": {
        "name": "تمرکز در نماز",
        "icon": "🕌",
        "levels": {
            "small": {"name": "لقمه کوچک", "icon": "🟢", "desc": "نماز کامل با تمرکز بالا (۱۵ دقیقه)"},
            "special": {"name": "لقمه ویژه", "icon": "🟡", "desc": "نماز با حداقل تمرکز (۵ دقیقه)"},
            "emergency": {"name": "لقمه اضطراری", "icon": "🔴", "desc": "فقط نیت و حضور قلب (۱ دقیقه)"},
        },
    },
    "sleep": {
        "name": "خواب منظم",
        "icon": "🌙",
        "levels": {
            "small": {"name": "لقمه کوچک", "icon": "🟢", "desc": "خوابیدن قبل ۲۳ + بیدار شدن ۶ صبح"},
            "special": {"name": "لقمه ویژه", "icon": "🟡", "desc": "خوابیدن قبل ۲۴ + بیدار شدن ۷ صبح"},
            "emergency": {"name": "لقمه اضطراری", "icon": "🔴", "desc": "حداقل ۶ ساعت خواب"},
        },
    },
    "exercise": {
        "name": "ورزش",
        "icon": "💪",
        "levels": {
            "small": {"name": "لقمه کوچک", "icon": "🟢", "desc": "۱۵ دقیقه ورزش کامل"},
            "special": {"name": "لقمه ویژه", "icon": "🟡", "desc": "۵ دقیقه ورزش سبک"},
            "emergency": {"name": "لقمه اضطراری", "icon": "🔴", "desc": "۱ دقیقه حرکت (کشش/پیاده‌روی)"},
        },
    },
}

HABIT_ORDER = ["namaz", "sleep", "exercise"]

# ─────────────────────────────────────────────────────────────────────────────
# Reminder Schedule
# ─────────────────────────────────────────────────────────────────────────────

# Course reminders (multiple times per day)
COURSE_REMINDER_TIMES = [
    (8, 0),   # صبح
    (12, 30), # ظهر
    (17, 0),  # عصر
    (20, 30), # شب
    (22, 30), # آخر شب
]

# Habit reminders
HABIT_REMINDER_TIMES = [
    (7, 30),  # صبح زود - یادآوری شروع روز
    (13, 0),  # بعد ظهر
    (18, 30), # عصر
    (21, 0),  # شب - قبل خواب
]

# Daily summary
SUMMARY_TIME = (22, 45)

# ─────────────────────────────────────────────────────────────────────────────
# Motivational Messages
# ─────────────────────────────────────────────────────────────────────────────

MOTIVATIONAL_MSGS = [
    "💎 هر قدم کوچیک، یه پیروزی بزرگه!",
    "🌟 امروز بهتر از دیروز باش، همین کافیه!",
    "🔥 عادت‌ساز واقعی هر روز حاضر میشه، حتی اگه سخته!",
    "⭐ مهم نیست سرعتت چقدره، مهم اینه که متوقف نشی!",
    "🏆 تو الان داری کاری میکنی که ۹۹٪ آدما نمیکنن!",
    "💪 لقمه اضطراری هم یه پیروزیه! مهم ادامه دادنه!",
    "🎯 عادت = هویت جدید. تو داری خودت رو می‌سازی!",
    "🌱 درختِ بلند هم روزی یه دونه بود. ادامه بده!",
    "✨ هر بار که تیک میزنی، مغزت یه اتصال جدید می‌سازه!",
    "🧠 ۶۶ روز. فقط ۶۶ روز تا ساختن یه عادت دائمی!",
]

COURSE_MSGS = [
    "📚 وقتشه یه جلسه از دوره عادت‌سازی ببینی!\n\n🎯 حتی ۵ دقیقه دیدن هم ارزشمنده.",
    "🎬 یادت نره دوره رو ببینی!\n\n💡 هر چی بیشتر یاد بگیری، عادت‌سازی راحت‌تر میشه.",
    "📖 الان بهترین وقت برای یادگیریه!\n\n🧠 مغزت آماده جذب اطلاعات جدیده.",
    "⏰ یادآوری دوره آموزشی!\n\n🔑 علم + عمل = تغییر واقعی",
    "🚀 یه جلسه دوره ببین و انرژی بگیر!\n\n💎 سرمایه‌گذاری روی خودت بهترین سرمایه‌گذاریه.",
]

# ─────────────────────────────────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────────────────────────────────


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        conn = self._conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT DEFAULT '',
                    first_name TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    is_paused INTEGER DEFAULT 0,
                    total_perfect_days INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS habit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    habit_key TEXT NOT NULL,
                    date TEXT NOT NULL,
                    level TEXT DEFAULT NULL,
                    completed_at TEXT DEFAULT NULL,
                    UNIQUE(user_id, habit_key, date)
                );
                CREATE TABLE IF NOT EXISTS course_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    watched INTEGER DEFAULT 0,
                    completed_at TEXT DEFAULT NULL,
                    UNIQUE(user_id, date)
                );
                CREATE TABLE IF NOT EXISTS streaks (
                    user_id INTEGER NOT NULL,
                    habit_key TEXT NOT NULL,
                    current_streak INTEGER DEFAULT 0,
                    best_streak INTEGER DEFAULT 0,
                    last_date TEXT DEFAULT '',
                    PRIMARY KEY(user_id, habit_key)
                );
                CREATE TABLE IF NOT EXISTS course_streaks (
                    user_id INTEGER PRIMARY KEY,
                    current_streak INTEGER DEFAULT 0,
                    best_streak INTEGER DEFAULT 0,
                    last_date TEXT DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_logs_user_date ON habit_logs(user_id, date);
                CREATE INDEX IF NOT EXISTS idx_course_user_date ON course_logs(user_id, date);
            """)
            conn.commit()
        finally:
            conn.close()

    # ── User ─────────────────────────────────────────────────────────────────

    def get_or_create_user(self, user_id: int, username: str = "", first_name: str = "") -> dict:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                    (user_id, username, first_name),
                )
                # Initialize streaks
                for key in HABIT_ORDER:
                    conn.execute(
                        "INSERT OR IGNORE INTO streaks (user_id, habit_key) VALUES (?, ?)",
                        (user_id, key),
                    )
                conn.execute(
                    "INSERT OR IGNORE INTO course_streaks (user_id) VALUES (?)", (user_id,)
                )
                conn.commit()
                row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row)
        finally:
            conn.close()

    def get_all_active_users(self) -> list:
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

    # ── Habit Logs ───────────────────────────────────────────────────────────

    def log_habit(self, user_id: int, habit_key: str, date: str, level: str) -> bool:
        """Log a habit completion at a specific level. Returns True if new."""
        conn = self._conn()
        try:
            existing = conn.execute(
                "SELECT * FROM habit_logs WHERE user_id = ? AND habit_key = ? AND date = ?",
                (user_id, habit_key, date),
            ).fetchone()

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if existing:
                if existing["level"] == level:
                    # Same level - remove it (toggle off)
                    conn.execute(
                        "DELETE FROM habit_logs WHERE user_id = ? AND habit_key = ? AND date = ?",
                        (user_id, habit_key, date),
                    )
                    conn.commit()
                    self._update_streak(user_id, habit_key)
                    return False
                else:
                    # Different level - update
                    conn.execute(
                        "UPDATE habit_logs SET level = ?, completed_at = ? WHERE user_id = ? AND habit_key = ? AND date = ?",
                        (level, now, user_id, habit_key, date),
                    )
                    conn.commit()
                    self._update_streak(user_id, habit_key)
                    return True
            else:
                conn.execute(
                    "INSERT INTO habit_logs (user_id, habit_key, date, level, completed_at) VALUES (?, ?, ?, ?, ?)",
                    (user_id, habit_key, date, level, now),
                )
                conn.commit()
                self._update_streak(user_id, habit_key)
                return True
        finally:
            conn.close()

    def get_today_status(self, user_id: int, date: str) -> dict:
        """Get status of all 3 habits for today."""
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

    def get_habit_log(self, user_id: int, habit_key: str, date: str) -> Optional[dict]:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM habit_logs WHERE user_id = ? AND habit_key = ? AND date = ?",
                (user_id, habit_key, date),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # ── Streaks ──────────────────────────────────────────────────────────────

    def _update_streak(self, user_id: int, habit_key: str):
        conn = self._conn()
        try:
            # Calculate streak from logs
            rows = conn.execute(
                "SELECT DISTINCT date FROM habit_logs WHERE user_id = ? AND habit_key = ? ORDER BY date DESC",
                (user_id, habit_key),
            ).fetchall()

            if not rows:
                conn.execute(
                    "UPDATE streaks SET current_streak = 0, last_date = '' WHERE user_id = ? AND habit_key = ?",
                    (user_id, habit_key),
                )
                conn.commit()
                return

            streak = 0
            today = datetime.now().date()
            expected = today

            for row in rows:
                log_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
                if log_date == expected:
                    streak += 1
                    expected -= timedelta(days=1)
                elif log_date == today - timedelta(days=1) and streak == 0:
                    # Yesterday counts if today hasn't been logged yet
                    expected = log_date
                    streak += 1
                    expected -= timedelta(days=1)
                else:
                    break

            # Update streak record
            current = conn.execute(
                "SELECT best_streak FROM streaks WHERE user_id = ? AND habit_key = ?",
                (user_id, habit_key),
            ).fetchone()
            best = max(current["best_streak"] if current else 0, streak)

            conn.execute(
                """INSERT INTO streaks (user_id, habit_key, current_streak, best_streak, last_date)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, habit_key) DO UPDATE SET
                   current_streak = ?, best_streak = ?, last_date = ?""",
                (user_id, habit_key, streak, best, today.isoformat(),
                 streak, best, today.isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_streak(self, user_id: int, habit_key: str) -> dict:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM streaks WHERE user_id = ? AND habit_key = ?",
                (user_id, habit_key),
            ).fetchone()
            return dict(row) if row else {"current_streak": 0, "best_streak": 0}
        finally:
            conn.close()

    def get_all_streaks(self, user_id: int) -> dict:
        result = {}
        for key in HABIT_ORDER:
            result[key] = self.get_streak(user_id, key)
        return result

    # ── Course ───────────────────────────────────────────────────────────────

    def log_course(self, user_id: int, date: str) -> bool:
        """Toggle course watched. Returns new state."""
        conn = self._conn()
        try:
            existing = conn.execute(
                "SELECT * FROM course_logs WHERE user_id = ? AND date = ?",
                (user_id, date),
            ).fetchone()

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if existing and existing["watched"]:
                conn.execute(
                    "UPDATE course_logs SET watched = 0, completed_at = NULL WHERE user_id = ? AND date = ?",
                    (user_id, date),
                )
                conn.commit()
                self._update_course_streak(user_id)
                return False
            else:
                conn.execute(
                    """INSERT INTO course_logs (user_id, date, watched, completed_at) VALUES (?, ?, 1, ?)
                       ON CONFLICT(user_id, date) DO UPDATE SET watched = 1, completed_at = ?""",
                    (user_id, date, now, now),
                )
                conn.commit()
                self._update_course_streak(user_id)
                return True
        finally:
            conn.close()

    def get_course_today(self, user_id: int, date: str) -> bool:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT watched FROM course_logs WHERE user_id = ? AND date = ?",
                (user_id, date),
            ).fetchone()
            return bool(row and row["watched"])
        finally:
            conn.close()

    def _update_course_streak(self, user_id: int):
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT date FROM course_logs WHERE user_id = ? AND watched = 1 ORDER BY date DESC",
                (user_id,),
            ).fetchall()

            if not rows:
                conn.execute(
                    "UPDATE course_streaks SET current_streak = 0 WHERE user_id = ?", (user_id,)
                )
                conn.commit()
                return

            streak = 0
            today = datetime.now().date()
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

            current = conn.execute(
                "SELECT best_streak FROM course_streaks WHERE user_id = ?", (user_id,)
            ).fetchone()
            best = max(current["best_streak"] if current else 0, streak)

            conn.execute(
                """INSERT INTO course_streaks (user_id, current_streak, best_streak, last_date)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                   current_streak = ?, best_streak = ?, last_date = ?""",
                (user_id, streak, best, today.isoformat(), streak, best, today.isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_course_streak(self, user_id: int) -> dict:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM course_streaks WHERE user_id = ?", (user_id,)
            ).fetchone()
            return dict(row) if row else {"current_streak": 0, "best_streak": 0}
        finally:
            conn.close()

    # ── Statistics ───────────────────────────────────────────────────────────

    def get_weekly_stats(self, user_id: int) -> dict:
        conn = self._conn()
        try:
            today = datetime.now().date()
            week_ago = today - timedelta(days=6)
            total_possible = 3 * 7  # 3 habits * 7 days

            completed = conn.execute(
                """SELECT COUNT(*) as c FROM habit_logs
                   WHERE user_id = ? AND date >= ? AND date <= ?""",
                (user_id, week_ago.isoformat(), today.isoformat()),
            ).fetchone()["c"]

            # Per-habit stats
            per_habit = {}
            for key in HABIT_ORDER:
                count = conn.execute(
                    """SELECT COUNT(*) as c FROM habit_logs
                       WHERE user_id = ? AND habit_key = ? AND date >= ? AND date <= ?""",
                    (user_id, key, week_ago.isoformat(), today.isoformat()),
                ).fetchone()["c"]
                per_habit[key] = count

            # Perfect days (all 3 done)
            perfect_days = 0
            for i in range(7):
                d = (week_ago + timedelta(days=i)).isoformat()
                day_count = conn.execute(
                    "SELECT COUNT(*) as c FROM habit_logs WHERE user_id = ? AND date = ?",
                    (user_id, d),
                ).fetchone()["c"]
                if day_count >= 3:
                    perfect_days += 1

            return {
                "total_possible": total_possible,
                "total_completed": completed,
                "percentage": round(completed / total_possible * 100) if total_possible > 0 else 0,
                "per_habit": per_habit,
                "perfect_days": perfect_days,
            }
        finally:
            conn.close()

    def get_monthly_stats(self, user_id: int) -> dict:
        conn = self._conn()
        try:
            today = datetime.now().date()
            month_ago = today - timedelta(days=29)
            total_possible = 3 * 30

            completed = conn.execute(
                """SELECT COUNT(*) as c FROM habit_logs
                   WHERE user_id = ? AND date >= ? AND date <= ?""",
                (user_id, month_ago.isoformat(), today.isoformat()),
            ).fetchone()["c"]

            # Level breakdown
            levels = {"small": 0, "special": 0, "emergency": 0}
            for level in levels:
                levels[level] = conn.execute(
                    """SELECT COUNT(*) as c FROM habit_logs
                       WHERE user_id = ? AND level = ? AND date >= ? AND date <= ?""",
                    (user_id, level, month_ago.isoformat(), today.isoformat()),
                ).fetchone()["c"]

            # Course days
            course_days = conn.execute(
                """SELECT COUNT(*) as c FROM course_logs
                   WHERE user_id = ? AND watched = 1 AND date >= ? AND date <= ?""",
                (user_id, month_ago.isoformat(), today.isoformat()),
            ).fetchone()["c"]

            return {
                "total_possible": total_possible,
                "total_completed": completed,
                "percentage": round(completed / total_possible * 100) if total_possible > 0 else 0,
                "levels": levels,
                "course_days": course_days,
            }
        finally:
            conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Bot Instance
# ─────────────────────────────────────────────────────────────────────────────

db = Database()


def today_str() -> str:
    return datetime.now().date().isoformat()


def get_motivational() -> str:
    import random
    return random.choice(MOTIVATIONAL_MSGS)


# ─────────────────────────────────────────────────────────────────────────────
# Keyboards
# ─────────────────────────────────────────────────────────────────────────────


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        ["📋 وضعیت امروز"],
        ["📚 دوره آموزشی", "📊 آمار"],
        ["🔥 استریک‌ها", "ℹ️ راهنما"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def habit_inline_keyboard(user_id: int, date: str) -> InlineKeyboardMarkup:
    """Generate the main habits status keyboard."""
    status = db.get_today_status(user_id, date)
    streaks = db.get_all_streaks(user_id)
    keyboard = []

    for key in HABIT_ORDER:
        habit = HABITS[key]
        log = status[key]
        streak_info = streaks[key]
        streak_num = streak_info["current_streak"]

        if log:
            level = log["level"]
            level_info = habit["levels"][level]
            # Completed - show with check and level
            text = f"✅ {habit['icon']} {habit['name']} ({level_info['icon']} {level_info['name']})"
            if streak_num > 0:
                text += f" 🔥{streak_num}"
            keyboard.append([InlineKeyboardButton(text, callback_data=f"detail_{key}")])
        else:
            # Not done - show action button
            text = f"⬜ {habit['icon']} {habit['name']}"
            if streak_num > 0:
                text += f" 🔥{streak_num}"
            keyboard.append([InlineKeyboardButton(text, callback_data=f"pick_{key}")])

    # Bottom row
    keyboard.append([
        InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh"),
    ])

    return InlineKeyboardMarkup(keyboard)


def level_picker_keyboard(habit_key: str) -> InlineKeyboardMarkup:
    """Show the 3 levels for a habit."""
    habit = HABITS[habit_key]
    keyboard = []

    for level_key, level in habit["levels"].items():
        text = f"{level['icon']} {level['name']} — {level['desc']}"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"log_{habit_key}_{level_key}")])

    keyboard.append([InlineKeyboardButton("↩️ برگشت", callback_data="back_to_habits")])
    return InlineKeyboardMarkup(keyboard)


# ─────────────────────────────────────────────────────────────────────────────
# Handlers
# ─────────────────────────────────────────────────────────────────────────────


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username or "", user.first_name or "")

    msg = f"""سلام {user.first_name}! 👋

به ربات عادت‌سازی خوش اومدی! 🎯

━━━━━━━━━━━━━━━━━━━━━━━━
🕌  تمرکز در نماز
🌙  خواب منظم
💪  ورزش
━━━━━━━━━━━━━━━━━━━━━━━━

هر عادت ۳ سطح داره:
🟢 لقمه کوچک — حالت عادی
🟡 لقمه ویژه — یه درجه کمتر
🔴 لقمه اضطراری — شرایط خاص

📚 دوره آموزشی عادت‌سازی هم هر روز بهت یادآوری میشه!

{get_motivational()}

از دکمه‌های زیر شروع کن! 👇"""

    await update.message.reply_text(msg, reply_markup=main_menu_keyboard())


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """📖 راهنمای ربات

━━━━━━━━━━━━━━━━━━━━━━━━
📋 وضعیت امروز — دیدن و تیک زدن عادت‌ها
📚 دوره آموزشی — ثبت تماشای دوره
📊 آمار — آمار هفتگی و ماهانه
🔥 استریک‌ها — روزهای متوالی

⏰ یادآوری‌ها:
• دوره: ۸:۰۰ | ۱۲:۳۰ | ۱۷:۰۰ | ۲۰:۳۰ | ۲۲:۳۰
• عادت‌ها: ۷:۳۰ | ۱۳:۰۰ | ۱۸:۳۰ | ۲۱:۰۰
• خلاصه شبانه: ۲۲:۴۵

🎯 نکته مهم:
حتی در بدترین شرایط، لقمه اضطراری رو بزن!
مهم ادامه دادنه، نه کامل بودن! 💪

/pause — توقف یادآوری
/resume — ادامه یادآوری
━━━━━━━━━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(msg, reply_markup=main_menu_keyboard())


async def show_today_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's habits status."""
    user_id = update.effective_user.id
    db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
    date = today_str()
    status = db.get_today_status(user_id, date)

    # Count completed
    done = sum(1 for v in status.values() if v is not None)
    total = 3

    # Progress visualization
    if done == 0:
        progress = "⬜⬜⬜"
        header = "🌅 هنوز شروع نکردی!"
    elif done == 1:
        progress = "🟩⬜⬜"
        header = "👍 یکی انجام شد! ادامه بده!"
    elif done == 2:
        progress = "🟩🟩⬜"
        header = "🔥 عالی! فقط یکی مونده!"
    else:
        progress = "🟩🟩🟩"
        header = "🏆 تبریک! روز کامل! 🎉"

    msg = f"""📋 وضعیت امروز — {date}

{progress}  {done}/3  {header}

━━━━━━━━━━━━━━━━━━━━━━━━
روی هر عادت کلیک کن تا سطحش رو انتخاب کنی:
━━━━━━━━━━━━━━━━━━━━━━━━"""

    keyboard = habit_inline_keyboard(user_id, date)
    await update.message.reply_text(msg, reply_markup=keyboard)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all inline keyboard callbacks."""
    query = update.callback_query
    user_id = query.from_user.id
    date = today_str()
    data = query.data

    if data == "refresh" or data == "back_to_habits":
        # Refresh habits view
        status = db.get_today_status(user_id, date)
        done = sum(1 for v in status.values() if v is not None)

        if done == 0:
            progress = "⬜⬜⬜"
            header = "🌅 هنوز شروع نکردی!"
        elif done == 1:
            progress = "🟩⬜⬜"
            header = "👍 یکی انجام شد!"
        elif done == 2:
            progress = "🟩🟩⬜"
            header = "🔥 فقط یکی مونده!"
        else:
            progress = "🟩🟩🟩"
            header = "🏆 روز کامل! 🎉"

        msg = f"""📋 وضعیت امروز — {date}

{progress}  {done}/3  {header}

━━━━━━━━━━━━━━━━━━━━━━━━
روی هر عادت کلیک کن تا سطحش رو انتخاب کنی:
━━━━━━━━━━━━━━━━━━━━━━━━"""

        keyboard = habit_inline_keyboard(user_id, date)
        await query.edit_message_text(msg, reply_markup=keyboard)
        await query.answer()

    elif data.startswith("pick_"):
        # Show level picker for a habit
        habit_key = data.replace("pick_", "")
        habit = HABITS[habit_key]

        msg = f"""{habit['icon']} {habit['name']}

کدوم سطح رو امروز انجام دادی?

━━━━━━━━━━━━━━━━━━━━━━━━"""

        keyboard = level_picker_keyboard(habit_key)
        await query.edit_message_text(msg, reply_markup=keyboard)
        await query.answer()

    elif data.startswith("detail_"):
        # Show detail of completed habit (allow changing level)
        habit_key = data.replace("detail_", "")
        habit = HABITS[habit_key]
        log = db.get_habit_log(user_id, habit_key, date)

        if log:
            level_info = habit["levels"][log["level"]]
            msg = f"""✅ {habit['icon']} {habit['name']}

سطح انجام: {level_info['icon']} {level_info['name']}
📝 {level_info['desc']}
⏰ ثبت شده: {log['completed_at'][:16] if log['completed_at'] else ''}

می‌خوای سطح رو عوض کنی?
━━━━━━━━━━━━━━━━━━━━━━━━"""
        else:
            msg = f"""{habit['icon']} {habit['name']}

کدوم سطح رو انجام دادی?
━━━━━━━━━━━━━━━━━━━━━━━━"""

        keyboard = level_picker_keyboard(habit_key)
        await query.edit_message_text(msg, reply_markup=keyboard)
        await query.answer()

    elif data.startswith("log_"):
        # Log habit at specific level
        parts = data.split("_")
        habit_key = parts[1]
        level = parts[2]
        habit = HABITS[habit_key]
        level_info = habit["levels"][level]

        result = db.log_habit(user_id, habit_key, date, level)

        if result:
            await query.answer(f"✅ {habit['name']} — {level_info['name']} ثبت شد! 🎉")
        else:
            await query.answer(f"↩️ {habit['name']} برداشته شد.")

        # Go back to habits view
        status = db.get_today_status(user_id, date)
        done = sum(1 for v in status.values() if v is not None)

        if done == 0:
            progress = "⬜⬜⬜"
            header = "🌅 هنوز شروع نکردی!"
        elif done == 1:
            progress = "🟩⬜⬜"
            header = "👍 یکی انجام شد!"
        elif done == 2:
            progress = "🟩🟩⬜"
            header = "🔥 فقط یکی مونده!"
        else:
            progress = "🟩🟩🟩"
            header = "🏆 روز کامل! 🎉"

        msg = f"""📋 وضعیت امروز — {date}

{progress}  {done}/3  {header}

━━━━━━━━━━━━━━━━━━━━━━━━
روی هر عادت کلیک کن تا سطحش رو انتخاب کنی:
━━━━━━━━━━━━━━━━━━━━━━━━"""

        if done == 3 and result:
            msg += f"\n\n{get_motivational()}"

        keyboard = habit_inline_keyboard(user_id, date)
        await query.edit_message_text(msg, reply_markup=keyboard)

    elif data == "course_toggle":
        new_state = db.log_course(user_id, date)
        streak = db.get_course_streak(user_id)

        if new_state:
            await query.answer("✅ دوره امروز ثبت شد! 🎉")
        else:
            await query.answer("↩️ لغو شد.")

        # Update course view
        watched = db.get_course_today(user_id, date)
        await _edit_course_message(query, user_id, date, watched, streak)

    elif data == "stats_weekly":
        await _show_weekly_inline(query, user_id)
        await query.answer()

    elif data == "stats_monthly":
        await _show_monthly_inline(query, user_id)
        await query.answer()


# ── Course ───────────────────────────────────────────────────────────────────


async def show_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
    date = today_str()
    watched = db.get_course_today(user_id, date)
    streak = db.get_course_streak(user_id)

    msg = _course_message(watched, streak)
    keyboard = _course_keyboard(watched)
    await update.message.reply_text(msg, reply_markup=keyboard)


def _course_message(watched: bool, streak: dict) -> str:
    status = "✅ دیدم" if watched else "⬜ هنوز ندیدم"
    fire = f"🔥 {streak['current_streak']} روز متوالی" if streak["current_streak"] > 0 else "💤 هنوز استریکی نداری"
    best = f"🏆 بهترین: {streak['best_streak']} روز" if streak["best_streak"] > 0 else ""

    msg = f"""📚 دوره آموزشی عادت‌سازی

━━━━━━━━━━━━━━━━━━━━━━━━
📅 امروز: {status}
{fire}
{best}
━━━━━━━━━━━━━━━━━━━━━━━━"""

    if not watched:
        msg += "\n\n💡 حتی ۵ دقیقه هم ارزشمنده! شروع کن!"

    return msg


def _course_keyboard(watched: bool) -> InlineKeyboardMarkup:
    if watched:
        btn = InlineKeyboardButton("↩️ لغو ثبت امروز", callback_data="course_toggle")
    else:
        btn = InlineKeyboardButton("✅ امروز دوره رو دیدم!", callback_data="course_toggle")
    return InlineKeyboardMarkup([[btn]])


async def _edit_course_message(query, user_id: int, date: str, watched: bool, streak: dict):
    msg = _course_message(watched, streak)
    keyboard = _course_keyboard(watched)
    await query.edit_message_text(msg, reply_markup=keyboard)


# ── Statistics ───────────────────────────────────────────────────────────────


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار هفتگی", callback_data="stats_weekly")],
        [InlineKeyboardButton("📈 آمار ماهانه", callback_data="stats_monthly")],
    ])

    await update.message.reply_text("📊 کدوم آمار رو می‌خوای ببینی?", reply_markup=keyboard)


async def _show_weekly_inline(query, user_id: int):
    stats = db.get_weekly_stats(user_id)

    # Progress bar
    pct = stats["percentage"]
    filled = int(pct / 10)
    bar = "🟩" * filled + "⬜" * (10 - filled)

    msg = f"""📊 آمار ۷ روز اخیر

{bar} {pct}%
━━━━━━━━━━━━━━━━━━━━━━━━

✅ انجام شده: {stats['total_completed']}/{stats['total_possible']}
🏆 روزهای کامل: {stats['perfect_days']}/7

📋 عملکرد هر عادت:
"""
    for key in HABIT_ORDER:
        habit = HABITS[key]
        count = stats["per_habit"][key]
        h_bar = "🟩" * count + "⬜" * (7 - count)
        msg += f"  {habit['icon']} {habit['name']}: {h_bar} {count}/7\n"

    streaks = db.get_all_streaks(user_id)
    msg += "\n🔥 استریک فعلی:\n"
    for key in HABIT_ORDER:
        habit = HABITS[key]
        s = streaks[key]
        msg += f"  {habit['icon']} {s['current_streak']} روز (بهترین: {s['best_streak']})\n"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 آمار ماهانه", callback_data="stats_monthly")],
    ])
    await query.edit_message_text(msg, reply_markup=keyboard)


async def _show_monthly_inline(query, user_id: int):
    stats = db.get_monthly_stats(user_id)

    pct = stats["percentage"]
    filled = int(pct / 10)
    bar = "🟩" * filled + "⬜" * (10 - filled)

    msg = f"""📈 آمار ۳۰ روز اخیر

{bar} {pct}%
━━━━━━━━━━━━━━━━━━━━━━━━

✅ انجام شده: {stats['total_completed']}/{stats['total_possible']}
📚 دوره تماشا شده: {stats['course_days']}/30 روز

📊 توزیع سطوح:
  🟢 لقمه کوچک: {stats['levels']['small']} بار
  🟡 لقمه ویژه: {stats['levels']['special']} بار
  🔴 لقمه اضطراری: {stats['levels']['emergency']} بار
"""

    # Motivational based on percentage
    if pct >= 90:
        msg += "\n🏆 فوق‌العاده‌ای! ادامه بده! 💎"
    elif pct >= 70:
        msg += "\n👏 عالی! خیلی خوب پیش میری!"
    elif pct >= 50:
        msg += "\n💪 خوبه! هر روز یکم بهتر!"
    elif pct >= 30:
        msg += "\n🌱 شروع خوبیه! ادامه بده!"
    else:
        msg += "\n⚡ امروز رو با انرژی شروع کن!"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار هفتگی", callback_data="stats_weekly")],
    ])
    await query.edit_message_text(msg, reply_markup=keyboard)


# ── Streaks ──────────────────────────────────────────────────────────────────


async def show_streaks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
    streaks = db.get_all_streaks(user_id)
    course_streak = db.get_course_streak(user_id)

    msg = """🔥 استریک‌های من

━━━━━━━━━━━━━━━━━━━━━━━━
"""
    for key in HABIT_ORDER:
        habit = HABITS[key]
        s = streaks[key]
        current = s["current_streak"]
        best = s["best_streak"]

        # Visual streak indicator
        if current >= 30:
            fire = "🌟"
        elif current >= 14:
            fire = "💎"
        elif current >= 7:
            fire = "🔥"
        elif current >= 3:
            fire = "✨"
        else:
            fire = "💤"

        msg += f"\n{habit['icon']} {habit['name']}\n"
        msg += f"  {fire} فعلی: {current} روز\n"
        msg += f"  🏆 بهترین: {best} روز\n"

    msg += f"\n📚 دوره آموزشی\n"
    msg += f"  {'🔥' if course_streak['current_streak'] > 0 else '💤'} فعلی: {course_streak['current_streak']} روز\n"
    msg += f"  🏆 بهترین: {course_streak['best_streak']} روز\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━"
    msg += f"\n\n{get_motivational()}"

    await update.message.reply_text(msg, reply_markup=main_menu_keyboard())


# ── Pause/Resume ─────────────────────────────────────────────────────────────


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.set_paused(user_id, True)
    await update.message.reply_text(
        "⏸ یادآوری‌ها متوقف شد.\n\n/resume برای فعال‌سازی مجدد",
        reply_markup=main_menu_keyboard(),
    )


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.set_paused(user_id, False)
    await update.message.reply_text(
        "▶️ یادآوری‌ها فعال شد! 🔔\n\nمنتظر یادآوری‌های بعدی باش!",
        reply_markup=main_menu_keyboard(),
    )


# ── Text Message Handler ─────────────────────────────────────────────────────


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "📋 وضعیت امروز":
        await show_today_status(update, context)
    elif text == "📚 دوره آموزشی":
        await show_course(update, context)
    elif text == "📊 آمار":
        await show_stats(update, context)
    elif text == "🔥 استریک‌ها":
        await show_streaks(update, context)
    elif text == "ℹ️ راهنما":
        await cmd_help(update, context)
    else:
        await update.message.reply_text(
            "🤔 از دکمه‌های منو استفاده کن!\n\n/help برای راهنما",
            reply_markup=main_menu_keyboard(),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Scheduled Jobs (Reminders)
# ─────────────────────────────────────────────────────────────────────────────


async def job_course_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send course reminder to all active users who haven't watched today."""
    import random
    date = today_str()
    users = db.get_all_active_users()

    for user_id in users:
        try:
            if db.get_course_today(user_id, date):
                continue  # Already watched

            streak = db.get_course_streak(user_id)
            msg = random.choice(COURSE_MSGS)

            if streak["current_streak"] > 0:
                msg += f"\n\n🔥 استریک: {streak['current_streak']} روز — نذار قطع بشه!"
            elif streak["best_streak"] > 0:
                msg += f"\n\n💪 بهترین رکوردت {streak['best_streak']} روز بود. بیا رکورد بزن!"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ الان دیدم!", callback_data="course_toggle")],
            ])
            await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Course reminder error for {user_id}: {e}")


async def job_habit_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send habit reminder to users with incomplete habits."""
    date = today_str()
    users = db.get_all_active_users()

    for user_id in users:
        try:
            status = db.get_today_status(user_id, date)
            incomplete = [key for key in HABIT_ORDER if status[key] is None]

            if not incomplete:
                continue  # All done!

            done = 3 - len(incomplete)

            if done == 0:
                msg = "⏰ یادآوری عادت‌ها!\n\nهنوز هیچ‌کدوم رو انجام ندادی 😅\n"
            elif done == 1:
                msg = "⏰ یکی انجام شده! دوتای دیگه مونده 💪\n"
            else:
                msg = "⏰ فقط یکی مونده! تمومش کن! 🔥\n"

            msg += "\n"
            for key in incomplete:
                habit = HABITS[key]
                msg += f"  ⬜ {habit['icon']} {habit['name']}\n"

            msg += f"\n💡 یادت باشه: حتی لقمه اضطراری هم حساب میشه!"
            msg += f"\n\n{get_motivational()}"

            # Quick action buttons
            keyboard = []
            for key in incomplete[:3]:
                habit = HABITS[key]
                keyboard.append([InlineKeyboardButton(
                    f"{habit['icon']} {habit['name']} انجام بده!",
                    callback_data=f"pick_{key}",
                )])

            await context.bot.send_message(
                chat_id=user_id,
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except Exception as e:
            logger.error(f"Habit reminder error for {user_id}: {e}")


async def job_daily_summary(context: ContextTypes.DEFAULT_TYPE):
    """Send nightly summary."""
    date = today_str()
    users = db.get_all_active_users()

    for user_id in users:
        try:
            status = db.get_today_status(user_id, date)
            done = sum(1 for v in status.values() if v is not None)
            course_watched = db.get_course_today(user_id, date)

            # Build summary
            if done == 3:
                progress = "🟩🟩🟩"
                header = "🏆 روز عالی بود!"
            elif done == 2:
                progress = "🟩🟩⬜"
                header = "👍 بد نبود!"
            elif done == 1:
                progress = "🟩⬜⬜"
                header = "یکی بهتر از هیچی!"
            else:
                progress = "⬜⬜⬜"
                header = "فردا جبران کن! 💪"

            msg = f"🌙 خلاصه امروز\n\n{progress} {done}/3 — {header}\n\n"

            for key in HABIT_ORDER:
                habit = HABITS[key]
                log = status[key]
                if log:
                    level_info = habit["levels"][log["level"]]
                    msg += f"  ✅ {habit['icon']} {habit['name']} ({level_info['icon']})\n"
                else:
                    msg += f"  ❌ {habit['icon']} {habit['name']}\n"

            msg += f"\n📚 دوره: {'✅ دیدم' if course_watched else '❌ ندیدم'}\n"

            # Streaks preview
            streaks = db.get_all_streaks(user_id)
            msg += "\n🔥 استریک‌ها: "
            streak_parts = []
            for key in HABIT_ORDER:
                s = streaks[key]["current_streak"]
                if s > 0:
                    streak_parts.append(f"{HABITS[key]['icon']}{s}")
            if streak_parts:
                msg += " | ".join(streak_parts)
            else:
                msg += "—"

            msg += f"\n\n{'🌟 ' + get_motivational() if done > 0 else '💡 فردا صبح از نو شروع کن!'}"
            msg += "\n\nشب بخیر! 🌙"

            await context.bot.send_message(chat_id=user_id, text=msg)
        except Exception as e:
            logger.error(f"Summary error for {user_id}: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main():
    if not BOT_TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable not set!")
        print("   export TELEGRAM_BOT_TOKEN='your-token'")
        sys.exit(1)

    print("🤖 Habit Tracker Bot v2.0 Starting...")
    print(f"📂 Database: {DB_PATH}")
    print(f"🕌 Habits: {', '.join(h['name'] for h in HABITS.values())}")

    app = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("habits", show_today_status))
    app.add_handler(CommandHandler("today", show_today_status))
    app.add_handler(CommandHandler("course", show_course))
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(CommandHandler("streaks", show_streaks))
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("resume", cmd_resume))

    # Callback handler (all inline buttons)
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Text handler (reply keyboard)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # ── Schedule Jobs ────────────────────────────────────────────────────────

    job_queue = app.job_queue

    # Course reminders (multiple per day)
    for hour, minute in COURSE_REMINDER_TIMES:
        job_queue.run_daily(
            job_course_reminder,
            time=time(hour=hour, minute=minute),
            name=f"course_{hour:02d}{minute:02d}",
        )

    # Habit reminders
    for hour, minute in HABIT_REMINDER_TIMES:
        job_queue.run_daily(
            job_habit_reminder,
            time=time(hour=hour, minute=minute),
            name=f"habit_{hour:02d}{minute:02d}",
        )

    # Daily summary
    job_queue.run_daily(
        job_daily_summary,
        time=time(hour=SUMMARY_TIME[0], minute=SUMMARY_TIME[1]),
        name="daily_summary",
    )

    # ── Run ──────────────────────────────────────────────────────────────────

    print("✅ Bot running! Press Ctrl+C to stop.")
    print(f"⏰ Course reminders: {', '.join(f'{h:02d}:{m:02d}' for h, m in COURSE_REMINDER_TIMES)}")
    print(f"⏰ Habit reminders: {', '.join(f'{h:02d}:{m:02d}' for h, m in HABIT_REMINDER_TIMES)}")
    print(f"🌙 Daily summary: {SUMMARY_TIME[0]:02d}:{SUMMARY_TIME[1]:02d}")

    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
