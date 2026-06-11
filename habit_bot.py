#!/usr/bin/env python3
"""
ربات تلگرام عادت‌سازی و یادآوری
Telegram Habit Tracker & Reminder Bot

Features:
- مدیریت عادت‌ها (اضافه/حذف)
- یادآوری چند بار در روز
- ثبت انجام عادت‌ها با تیک
- آمار هفتگی/ماهانه
- یادآوری دوره آموزشی عادت‌سازی
- استریک روزهای متوالی
- خلاصه شبانه
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
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
DB_PATH = os.environ.get("HABIT_DB_PATH", "habit_bot.db")
DEFAULT_REMINDER_TIMES = ["07:00", "12:00", "18:00", "21:00"]
COURSE_REMINDER_MSG = "📚 یادآوری: وقتشه دوره آموزشی عادت‌سازی رو ببینی! 🎯\nامروز چند دقیقه وقت بذار و یک درس جدید یاد بگیر."

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

(
    ADD_HABIT_NAME,
    ADD_HABIT_DESCRIPTION,
    ADD_HABIT_FREQUENCY,
) = range(3)


# ─────────────────────────────────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────────────────────────────────


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def init_db(self):
        conn = self.get_connection()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS habits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    frequency TEXT DEFAULT 'daily',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    sort_order INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
                CREATE TABLE IF NOT EXISTS habit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    habit_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    completed INTEGER DEFAULT 0,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (habit_id) REFERENCES habits(id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(habit_id, date)
                );
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    time TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    reminder_type TEXT DEFAULT 'habit',
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
                CREATE TABLE IF NOT EXISTS course_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    watched INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id, date)
                );
                CREATE INDEX IF NOT EXISTS idx_habit_logs_date ON habit_logs(date);
                CREATE INDEX IF NOT EXISTS idx_habit_logs_user ON habit_logs(user_id);
                CREATE INDEX IF NOT EXISTS idx_habits_user ON habits(user_id);
            """)
            conn.commit()
        finally:
            conn.close()

    def get_or_create_user(self, user_id: int, username: str = "", first_name: str = "") -> dict:
        conn = self.get_connection()
        try:
            user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if user is None:
                conn.execute(
                    "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                    (user_id, username, first_name),
                )
                for t in DEFAULT_REMINDER_TIMES:
                    conn.execute(
                        "INSERT INTO reminders (user_id, time, reminder_type) VALUES (?, ?, 'habit')",
                        (user_id, t),
                    )
                conn.execute(
                    "INSERT INTO reminders (user_id, time, reminder_type) VALUES (?, ?, 'course')",
                    (user_id, "09:00"),
                )
                conn.commit()
                user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return dict(user)
        finally:
            conn.close()

    def get_all_active_users(self) -> list:
        conn = self.get_connection()
        try:
            rows = conn.execute("SELECT * FROM users WHERE is_active = 1").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def add_habit(self, user_id: int, name: str, description: str = "", frequency: str = "daily") -> int:
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                "INSERT INTO habits (user_id, name, description, frequency) VALUES (?, ?, ?, ?)",
                (user_id, name, description, frequency),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_habits(self, user_id: int, active_only: bool = True) -> list:
        conn = self.get_connection()
        try:
            query = "SELECT * FROM habits WHERE user_id = ?"
            if active_only:
                query += " AND is_active = 1"
            query += " ORDER BY sort_order, id"
            rows = conn.execute(query, (user_id,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_habit(self, habit_id: int) -> Optional[dict]:
        conn = self.get_connection()
        try:
            row = conn.execute("SELECT * FROM habits WHERE id = ?", (habit_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def delete_habit(self, habit_id: int):
        conn = self.get_connection()
        try:
            conn.execute("UPDATE habits SET is_active = 0 WHERE id = ?", (habit_id,))
            conn.commit()
        finally:
            conn.close()

    def toggle_habit(self, habit_id: int, user_id: int, date: str) -> bool:
        conn = self.get_connection()
        try:
            existing = conn.execute(
                "SELECT * FROM habit_logs WHERE habit_id = ? AND date = ?",
                (habit_id, date),
            ).fetchone()
            if existing and existing["completed"]:
                conn.execute(
                    "UPDATE habit_logs SET completed = 0, completed_at = NULL WHERE habit_id = ? AND date = ?",
                    (habit_id, date),
                )
                conn.commit()
                return False
            else:
                conn.execute(
                    """INSERT INTO habit_logs (habit_id, user_id, date, completed, completed_at)
                       VALUES (?, ?, ?, 1, ?)
                       ON CONFLICT(habit_id, date) DO UPDATE SET completed = 1, completed_at = ?""",
                    (habit_id, user_id, date, datetime.now().isoformat(), datetime.now().isoformat()),
                )
                conn.commit()
                return True
        finally:
            conn.close()

    def get_today_status(self, user_id: int, date: str) -> list:
        conn = self.get_connection()
        try:
            rows = conn.execute(
                """SELECT h.id, h.name, h.description, h.frequency,
                          COALESCE(hl.completed, 0) as completed
                   FROM habits h
                   LEFT JOIN habit_logs hl ON h.id = hl.habit_id AND hl.date = ?
                   WHERE h.user_id = ? AND h.is_active = 1
                   ORDER BY h.sort_order, h.id""",
                (date, user_id),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_streak(self, habit_id: int) -> int:
        conn = self.get_connection()
        try:
            rows = conn.execute(
                """SELECT date FROM habit_logs
                   WHERE habit_id = ? AND completed = 1
                   ORDER BY date DESC""",
                (habit_id,),
            ).fetchall()
            if not rows:
                return 0
            streak = 0
            today = datetime.now().date()
            expected_date = today
            for row in rows:
                log_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
                if log_date == expected_date:
                    streak += 1
                    expected_date -= timedelta(days=1)
                elif log_date == expected_date - timedelta(days=1):
                    expected_date = log_date
                    streak += 1
                    expected_date -= timedelta(days=1)
                else:
                    break
            return streak
        finally:
            conn.close()

    def get_weekly_stats(self, user_id: int) -> dict:
        conn = self.get_connection()
        try:
            today = datetime.now().date()
            week_ago = today - timedelta(days=6)
            habits = self.get_habits(user_id)
            total_possible = len(habits) * 7
            completed = conn.execute(
                """SELECT COUNT(*) as count FROM habit_logs
                   WHERE user_id = ? AND completed = 1 AND date >= ? AND date <= ?""",
                (user_id, week_ago.isoformat(), today.isoformat()),
            ).fetchone()["count"]
            daily_stats = []
            for i in range(7):
                d = week_ago + timedelta(days=i)
                day_completed = conn.execute(
                    """SELECT COUNT(*) as count FROM habit_logs
                       WHERE user_id = ? AND completed = 1 AND date = ?""",
                    (user_id, d.isoformat()),
                ).fetchone()["count"]
                daily_stats.append({"date": d.isoformat(), "completed": day_completed, "total": len(habits)})
            return {
                "total_possible": total_possible,
                "total_completed": completed,
                "percentage": round(completed / total_possible * 100, 1) if total_possible > 0 else 0,
                "daily": daily_stats,
            }
        finally:
            conn.close()

    def get_monthly_stats(self, user_id: int) -> dict:
        conn = self.get_connection()
        try:
            today = datetime.now().date()
            month_ago = today - timedelta(days=29)
            habits = self.get_habits(user_id)
            total_possible = len(habits) * 30
            completed = conn.execute(
                """SELECT COUNT(*) as count FROM habit_logs
                   WHERE user_id = ? AND completed = 1 AND date >= ? AND date <= ?""",
                (user_id, month_ago.isoformat(), today.isoformat()),
            ).fetchone()["count"]
            return {
                "total_possible": total_possible,
                "total_completed": completed,
                "percentage": round(completed / total_possible * 100, 1) if total_possible > 0 else 0,
            }
        finally:
            conn.close()

    def get_reminders(self, user_id: int) -> list:
        conn = self.get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM reminders WHERE user_id = ? AND is_active = 1 ORDER BY time",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_all_reminders_at_time(self, time_str: str) -> list:
        conn = self.get_connection()
        try:
            rows = conn.execute(
                """SELECT r.*, u.user_id FROM reminders r
                   JOIN users u ON r.user_id = u.user_id
                   WHERE r.time = ? AND r.is_active = 1 AND u.is_active = 1""",
                (time_str,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def add_reminder(self, user_id: int, time_str: str, reminder_type: str = "habit") -> int:
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                "INSERT INTO reminders (user_id, time, reminder_type) VALUES (?, ?, ?)",
                (user_id, time_str, reminder_type),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def remove_reminder(self, reminder_id: int):
        conn = self.get_connection()
        try:
            conn.execute("UPDATE reminders SET is_active = 0 WHERE id = ?", (reminder_id,))
            conn.commit()
        finally:
            conn.close()

    def toggle_course_watched(self, user_id: int, date: str) -> bool:
        conn = self.get_connection()
        try:
            existing = conn.execute(
                "SELECT * FROM course_progress WHERE user_id = ? AND date = ?",
                (user_id, date),
            ).fetchone()
            if existing and existing["watched"]:
                conn.execute(
                    "UPDATE course_progress SET watched = 0 WHERE user_id = ? AND date = ?",
                    (user_id, date),
                )
                conn.commit()
                return False
            else:
                conn.execute(
                    """INSERT INTO course_progress (user_id, date, watched)
                       VALUES (?, ?, 1)
                       ON CONFLICT(user_id, date) DO UPDATE SET watched = 1""",
                    (user_id, date),
                )
                conn.commit()
                return True
        finally:
            conn.close()

    def get_course_streak(self, user_id: int) -> int:
        conn = self.get_connection()
        try:
            rows = conn.execute(
                """SELECT date FROM course_progress
                   WHERE user_id = ? AND watched = 1
                   ORDER BY date DESC""",
                (user_id,),
            ).fetchall()
            if not rows:
                return 0
            streak = 0
            today = datetime.now().date()
            expected_date = today
            for row in rows:
                log_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
                if log_date == expected_date:
                    streak += 1
                    expected_date -= timedelta(days=1)
                elif log_date == expected_date - timedelta(days=1):
                    expected_date = log_date
                    streak += 1
                    expected_date -= timedelta(days=1)
                else:
                    break
            return streak
        finally:
            conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Bot Handlers
# ─────────────────────────────────────────────────────────────────────────────

db = Database()


def get_today() -> str:
    return datetime.now().date().isoformat()


def get_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        ["📋 عادت‌های امروز", "➕ افزودن عادت"],
        ["📊 آمار هفتگی", "📈 آمار ماهانه"],
        ["📚 دوره آموزشی", "⏰ تنظیم یادآوری"],
        ["🗑 حذف عادت", "ℹ️ راهنما"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username or "", user.first_name or "")
    welcome_msg = f"""سلام {user.first_name}! 👋

به ربات عادت‌سازی خوش آمدی! 🎯

من کمکت می‌کنم تا:
✅ عادت‌های روزانه‌ات رو مدیریت کنی
⏰ یادآوری‌های منظم دریافت کنی
📚 دوره آموزشی عادت‌سازی رو فراموش نکنی
📊 پیشرفتت رو ببینی

از دکمه‌های زیر استفاده کن! 👇"""
    await update.message.reply_text(welcome_msg, reply_markup=get_main_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📖 راهنمای ربات عادت‌سازی

🔸 مدیریت عادت‌ها:
/add - افزودن عادت جدید
/habits - مشاهده و تیک زدن عادت‌ها
/delete - حذف عادت

🔸 آمار:
/stats - آمار هفتگی
/monthly - آمار ماهانه

🔸 دوره آموزشی:
/course - ثبت تماشای دوره

🔸 یادآوری:
/reminders - مشاهده یادآوری‌ها
/addreminder HH:MM - افزودن
/removereminder - حذف

🔸 تنظیمات:
/pause - توقف یادآوری‌ها
/resume - ادامه یادآوری‌ها"""
    await update.message.reply_text(help_text, reply_markup=get_main_keyboard())


async def show_habits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
    today = get_today()
    habits = db.get_today_status(user_id, today)

    if not habits:
        await update.message.reply_text(
            "هنوز عادتی اضافه نکردی! 🤔\nبرای شروع از /add استفاده کن.",
            reply_markup=get_main_keyboard(),
        )
        return

    completed_count = sum(1 for h in habits if h["completed"])
    total = len(habits)
    progress_pct = completed_count / total * 100
    filled = int(progress_pct / 10)
    progress_bar = "🟩" * filled + "⬜" * (10 - filled)

    msg = f"📋 عادت‌های امروز ({today}):\n\n"
    msg += f"پیشرفت: {progress_bar} {progress_pct:.0f}%\n"
    msg += f"انجام شده: {completed_count}/{total}\n\n"

    keyboard = []
    for habit in habits:
        status = "✅" if habit["completed"] else "⬜"
        streak = db.get_streak(habit["id"])
        streak_text = f" 🔥{streak}" if streak > 0 else ""
        btn_text = f"{status} {habit['name']}{streak_text}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"toggle_{habit['id']}")])
    keyboard.append([InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh_habits")])

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))


async def toggle_habit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    today = get_today()

    if query.data.startswith("toggle_"):
        habit_id = int(query.data.split("_")[1])
        new_state = db.toggle_habit(habit_id, user_id, today)
        habit = db.get_habit(habit_id)
        if new_state:
            await query.answer(f"✅ «{habit['name']}» انجام شد! 🎉")
        else:
            await query.answer(f"⬜ «{habit['name']}» برداشته شد.")
    elif query.data == "course_toggle":
        new_state = db.toggle_course_watched(user_id, today)
        if new_state:
            await query.answer("✅ دوره امروز تماشا شد! 🎉")
        else:
            await query.answer("⬜ لغو شد.")
        await _show_course_inline(query, user_id)
        return

    # Update habits message
    habits = db.get_today_status(user_id, today)
    completed_count = sum(1 for h in habits if h["completed"])
    total = len(habits)
    progress_pct = completed_count / total * 100 if total > 0 else 0
    filled = int(progress_pct / 10)
    progress_bar = "🟩" * filled + "⬜" * (10 - filled)

    msg = f"📋 عادت‌های امروز ({today}):\n\n"
    msg += f"پیشرفت: {progress_bar} {progress_pct:.0f}%\n"
    msg += f"انجام شده: {completed_count}/{total}\n\n"
    if completed_count == total and total > 0:
        msg += "🏆 تبریک! همه عادت‌ها انجام شد! 🎉\n\n"

    keyboard = []
    for habit in habits:
        status = "✅" if habit["completed"] else "⬜"
        streak = db.get_streak(habit["id"])
        streak_text = f" 🔥{streak}" if streak > 0 else ""
        btn_text = f"{status} {habit['name']}{streak_text}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"toggle_{habit['id']}")])
    keyboard.append([InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh_habits")])

    await query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(keyboard))


# ── Add Habit ────────────────────────────────────────────────────────────────

async def add_habit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "➕ نام عادت جدید رو بنویس:\n(مثلا: ورزش، مطالعه، مدیتیشن)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ADD_HABIT_NAME


async def add_habit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_habit_name"] = update.message.text.strip()
    await update.message.reply_text("📝 توضیحات (اختیاری):\n/skip برای رد شدن")
    return ADD_HABIT_DESCRIPTION


async def add_habit_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "/skip":
        context.user_data["new_habit_desc"] = ""
    else:
        context.user_data["new_habit_desc"] = update.message.text.strip()

    keyboard = [["روزانه", "روزهای کاری"], ["فقط آخر هفته", "سفارشی"]]
    await update.message.reply_text(
        "📅 تکرار عادت؟",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return ADD_HABIT_FREQUENCY


async def add_habit_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    freq_map = {"روزانه": "daily", "روزهای کاری": "weekdays", "فقط آخر هفته": "weekends", "سفارشی": "custom"}
    frequency = freq_map.get(update.message.text.strip(), "daily")
    user_id = update.effective_user.id
    name = context.user_data.get("new_habit_name", "")
    desc = context.user_data.get("new_habit_desc", "")
    db.add_habit(user_id, name, desc, frequency)

    await update.message.reply_text(
        f"✅ عادت «{name}» اضافه شد! 🎉\n/habits برای مشاهده",
        reply_markup=get_main_keyboard(),
    )
    context.user_data.pop("new_habit_name", None)
    context.user_data.pop("new_habit_desc", None)
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ لغو شد.", reply_markup=get_main_keyboard())
    return ConversationHandler.END


# ── Delete Habit ─────────────────────────────────────────────────────────────

async def delete_habit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    habits = db.get_habits(user_id)
    if not habits:
        await update.message.reply_text("عادتی نداری! 🤷‍♂️", reply_markup=get_main_keyboard())
        return

    keyboard = []
    for habit in habits:
        keyboard.append([InlineKeyboardButton(f"🗑 {habit['name']}", callback_data=f"delete_{habit['id']}")])
    keyboard.append([InlineKeyboardButton("❌ انصراف", callback_data="cancel_delete")])
    await update.message.reply_text("کدوم رو حذف کنم?", reply_markup=InlineKeyboardMarkup(keyboard))


async def delete_habit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel_delete":
        await query.edit_message_text("❌ لغو شد.")
        return
    if query.data.startswith("delete_"):
        habit_id = int(query.data.split("_")[1])
        habit = db.get_habit(habit_id)
        if habit:
            db.delete_habit(habit_id)
            await query.edit_message_text(f"✅ «{habit['name']}» حذف شد.")


# ── Statistics ───────────────────────────────────────────────────────────────

async def show_weekly_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
    stats = db.get_weekly_stats(user_id)
    habits = db.get_habits(user_id)

    if not habits:
        await update.message.reply_text("اول عادت اضافه کن! /add", reply_markup=get_main_keyboard())
        return

    msg = f"📊 آمار هفتگی:\n\n"
    msg += f"📈 درصد: {stats['percentage']}%\n"
    msg += f"✅ انجام: {stats['total_completed']}/{stats['total_possible']}\n\n"
    msg += "📅 جزئیات:\n"
    for day_stat in stats["daily"]:
        pct = (day_stat["completed"] / day_stat["total"] * 100) if day_stat["total"] > 0 else 0
        bar = "🟩" * int(pct / 20) + "⬜" * (5 - int(pct / 20))
        msg += f"  {day_stat['date']}: {bar} {day_stat['completed']}/{day_stat['total']}\n"

    msg += "\n🔥 استریک‌ها:\n"
    for habit in habits:
        streak = db.get_streak(habit["id"])
        if streak > 0:
            msg += f"  {habit['name']}: {streak} روز\n"

    await update.message.reply_text(msg, reply_markup=get_main_keyboard())


async def show_monthly_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
    stats = db.get_monthly_stats(user_id)
    habits = db.get_habits(user_id)

    if not habits:
        await update.message.reply_text("اول عادت اضافه کن! /add", reply_markup=get_main_keyboard())
        return

    msg = f"📈 آمار ماهانه (۳۰ روز):\n\n"
    msg += f"📊 درصد: {stats['percentage']}%\n"
    msg += f"✅ انجام: {stats['total_completed']}/{stats['total_possible']}\n\n"

    if stats["percentage"] >= 90:
        msg += "🏆 فوق‌العاده! ادامه بده! 💪"
    elif stats["percentage"] >= 70:
        msg += "👏 عالی! خوب پیش میری!"
    elif stats["percentage"] >= 50:
        msg += "💪 خوبه ولی بهتر هم میشه!"
    else:
        msg += "⚠️ بیشتر تلاش کن! از کوچیک شروع کن."

    await update.message.reply_text(msg, reply_markup=get_main_keyboard())


# ── Course ───────────────────────────────────────────────────────────────────

async def show_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
    today = get_today()
    streak = db.get_course_streak(user_id)

    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM course_progress WHERE user_id = ? AND date = ?", (user_id, today)
        ).fetchone()
        watched_today = row and row["watched"] if row else False
    finally:
        conn.close()

    status = "✅ دیدم" if watched_today else "⬜ هنوز ندیدم"
    msg = f"📚 دوره آموزشی عادت‌سازی\n\n📅 امروز: {status}\n🔥 استریک: {streak} روز\n"
    if not watched_today:
        msg += "\n💡 امروز حتما یه جلسه ببین!"

    keyboard = [[InlineKeyboardButton(
        "✅ امروز دیدم!" if not watched_today else "↩️ لغو",
        callback_data="course_toggle",
    )]]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))


async def _show_course_inline(query, user_id: int):
    today = get_today()
    streak = db.get_course_streak(user_id)
    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM course_progress WHERE user_id = ? AND date = ?", (user_id, today)
        ).fetchone()
        watched_today = row and row["watched"] if row else False
    finally:
        conn.close()

    status = "✅ دیدم" if watched_today else "⬜ هنوز ندیدم"
    msg = f"📚 دوره آموزشی عادت‌سازی\n\n📅 امروز: {status}\n🔥 استریک: {streak} روز\n"
    if watched_today:
        msg += "\n🎉 آفرین! ادامه بده!"
    else:
        msg += "\n💡 امروز حتما یه جلسه ببین!"

    keyboard = [[InlineKeyboardButton(
        "✅ امروز دیدم!" if not watched_today else "↩️ لغو",
        callback_data="course_toggle",
    )]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))


# ── Reminders ────────────────────────────────────────────────────────────────

async def show_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
    reminders = db.get_reminders(user_id)

    if not reminders:
        await update.message.reply_text("یادآوری نداری.\n/addreminder HH:MM", reply_markup=get_main_keyboard())
        return

    msg = "⏰ یادآوری‌ها:\n\n"
    for r in reminders:
        icon = "📚" if r["reminder_type"] == "course" else "📋"
        name = "دوره" if r["reminder_type"] == "course" else "عادت‌ها"
        msg += f"  {icon} {r['time']} - {name}\n"
    msg += "\n/addreminder HH:MM - افزودن\n/removereminder - حذف"
    await update.message.reply_text(msg, reply_markup=get_main_keyboard())


async def add_reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")

    if not context.args:
        await update.message.reply_text("مثال: /addreminder 08:30", reply_markup=get_main_keyboard())
        return

    time_str = context.args[0].strip()
    try:
        hour, minute = map(int, time_str.split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError()
        time_str = f"{hour:02d}:{minute:02d}"
    except (ValueError, IndexError):
        await update.message.reply_text("❌ فرمت اشتباه! مثال: 08:30", reply_markup=get_main_keyboard())
        return

    reminder_type = "habit"
    if len(context.args) > 1 and context.args[1].lower() in ("course", "دوره"):
        reminder_type = "course"

    db.add_reminder(user_id, time_str, reminder_type)
    await update.message.reply_text(f"✅ یادآوری {time_str} اضافه شد!", reply_markup=get_main_keyboard())


async def remove_reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reminders = db.get_reminders(user_id)
    if not reminders:
        await update.message.reply_text("یادآوری نداری! 🤷‍♂️", reply_markup=get_main_keyboard())
        return

    keyboard = []
    for r in reminders:
        icon = "📚" if r["reminder_type"] == "course" else "📋"
        keyboard.append([InlineKeyboardButton(f"{icon} {r['time']}", callback_data=f"rmreminder_{r['id']}")])
    keyboard.append([InlineKeyboardButton("❌ انصراف", callback_data="cancel_rmreminder")])
    await update.message.reply_text("کدوم رو حذف کنم?", reply_markup=InlineKeyboardMarkup(keyboard))


async def remove_reminder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel_rmreminder":
        await query.edit_message_text("❌ لغو شد.")
        return
    if query.data.startswith("rmreminder_"):
        reminder_id = int(query.data.split("_")[1])
        db.remove_reminder(reminder_id)
        await query.edit_message_text("✅ حذف شد.")


# ── Pause/Resume ─────────────────────────────────────────────────────────────

async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = db.get_connection()
    try:
        conn.execute("UPDATE users SET is_active = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()
    await update.message.reply_text("⏸ یادآوری‌ها متوقف شد.\n/resume برای ادامه", reply_markup=get_main_keyboard())


async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = db.get_connection()
    try:
        conn.execute("UPDATE users SET is_active = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()
    await update.message.reply_text("▶️ یادآوری‌ها فعال شد! 🔔", reply_markup=get_main_keyboard())


# ── Text Handler ─────────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    handlers = {
        "📋 عادت‌های امروز": show_habits,
        "📊 آمار هفتگی": show_weekly_stats,
        "📈 آمار ماهانه": show_monthly_stats,
        "📚 دوره آموزشی": show_course,
        "⏰ تنظیم یادآوری": show_reminders,
        "🗑 حذف عادت": delete_habit_start,
        "ℹ️ راهنما": help_command,
    }

    if text == "➕ افزودن عادت":
        await update.message.reply_text(
            "➕ نام عادت جدید رو بنویس:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ADD_HABIT_NAME

    handler = handlers.get(text)
    if handler:
        await handler(update, context)
    else:
        await update.message.reply_text("🤔 از دکمه‌ها یا /help استفاده کن.", reply_markup=get_main_keyboard())


# ─────────────────────────────────────────────────────────────────────────────
# Scheduled Jobs
# ─────────────────────────────────────────────────────────────────────────────

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    current_time = f"{now.hour:02d}:{now.minute:02d}"
    reminders = db.get_all_reminders_at_time(current_time)

    for reminder in reminders:
        user_id = reminder["user_id"]
        try:
            if reminder["reminder_type"] == "course":
                streak = db.get_course_streak(user_id)
                msg = COURSE_REMINDER_MSG
                if streak > 0:
                    msg += f"\n\n🔥 استریک: {streak} روز - نذار قطع بشه!"
                keyboard = [[InlineKeyboardButton("✅ الان دیدم!", callback_data="course_toggle")]]
                await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                today = get_today()
                habits = db.get_today_status(user_id, today)
                if not habits:
                    continue
                incomplete = [h for h in habits if not h["completed"]]
                if not incomplete:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="🏆 همه عادت‌ها انجام شده! آفرین! 💪",
                    )
                else:
                    msg = f"⏰ یادآوری!\n\n{len(incomplete)} عادت مونده:\n\n"
                    for h in incomplete:
                        msg += f"  ⬜ {h['name']}\n"
                    msg += "\n💪 الان یکی رو انجام بده!"
                    keyboard = []
                    for h in incomplete[:5]:
                        keyboard.append([InlineKeyboardButton(f"✅ {h['name']}", callback_data=f"toggle_{h['id']}")])
                    await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Reminder error for {user_id}: {e}")


async def daily_summary_job(context: ContextTypes.DEFAULT_TYPE):
    users = db.get_all_active_users()
    today = get_today()
    for user in users:
        user_id = user["user_id"]
        try:
            habits = db.get_today_status(user_id, today)
            if not habits:
                continue
            completed_count = sum(1 for h in habits if h["completed"])
            total = len(habits)
            pct = completed_count / total * 100 if total > 0 else 0

            msg = f"🌙 خلاصه امروز:\n\n✅ {completed_count}/{total} ({pct:.0f}%)\n\n"
            for h in habits:
                status = "✅" if h["completed"] else "❌"
                msg += f"  {status} {h['name']}\n"

            if pct == 100:
                msg += "\n🏆 عالی بود! فردا هم ادامه بده! 🎉"
            elif pct >= 50:
                msg += "\n👍 بد نبود! فردا بهتر! 💪"
            else:
                msg += "\n💡 فردا صبح زود شروع کن!"

            await context.bot.send_message(chat_id=user_id, text=msg)
        except Exception as e:
            logger.error(f"Summary error for {user_id}: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        sys.exit(1)

    print("🤖 Starting Habit Tracker Bot...")
    print(f"📂 Database: {DB_PATH}")

    app = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler
    add_habit_conv = ConversationHandler(
        entry_points=[CommandHandler("add", add_habit_start)],
        states={
            ADD_HABIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_habit_name)],
            ADD_HABIT_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.Regex("^/skip$"), add_habit_description),
                CommandHandler("skip", add_habit_description),
            ],
            ADD_HABIT_FREQUENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_habit_frequency)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        allow_reentry=True,
    )

    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("habits", show_habits))
    app.add_handler(CommandHandler("stats", show_weekly_stats))
    app.add_handler(CommandHandler("monthly", show_monthly_stats))
    app.add_handler(CommandHandler("course", show_course))
    app.add_handler(CommandHandler("reminders", show_reminders))
    app.add_handler(CommandHandler("addreminder", add_reminder_command))
    app.add_handler(CommandHandler("removereminder", remove_reminder_command))
    app.add_handler(CommandHandler("delete", delete_habit_start))
    app.add_handler(CommandHandler("pause", pause_command))
    app.add_handler(CommandHandler("resume", resume_command))
    app.add_handler(add_habit_conv)
    app.add_handler(CallbackQueryHandler(toggle_habit_callback, pattern=r"^(toggle_|refresh_habits|course_toggle)"))
    app.add_handler(CallbackQueryHandler(delete_habit_callback, pattern=r"^(delete_|cancel_delete)"))
    app.add_handler(CallbackQueryHandler(remove_reminder_callback, pattern=r"^(rmreminder_|cancel_rmreminder)"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Jobs
    job_queue = app.job_queue
    job_queue.run_repeating(send_reminder, interval=60, first=10)
    job_queue.run_daily(daily_summary_job, time=time(hour=22, minute=0))

    print("✅ Bot running! Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
