"""
⏰ Smart Reminders Module for Habit Bot v3.0
یادآوری‌های هوشمند — فقط وقتی انجام نشده
"""

import random
import logging
import aiohttp
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import (
    HABITS, HABIT_ORDER,
    COURSE_REMINDER_MSGS, HABIT_REMINDER_MSGS, JOURNAL_PROMPTS,
    MOTIVATIONAL_MSGS, FALLBACK_QUOTES,
    QURAN_API_URL,
)
from db import Database

logger = logging.getLogger(__name__)


async def get_quran_verse() -> str:
    """Fetch a random Quran verse with Persian translation."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(QURAN_API_URL) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    verse = data["data"]
                    text = verse["text"]
                    surah = verse["surah"]["name"]
                    ayah = verse["numberInSurah"]
                    surah_num = verse["surah"]["number"]
                    return f"📖 {text}\n\n— سوره {surah} آیه {ayah} ({surah_num}:{ayah})"
    except Exception as e:
        logger.warning(f"Quran API failed: {e}")

    # Fallback
    return random.choice(FALLBACK_QUOTES)


# ══════════════════════════════════════════════════════════════════════════════
# Morning Motivation
# ══════════════════════════════════════════════════════════════════════════════


async def job_morning_motivation(context: ContextTypes.DEFAULT_TYPE):
    """Send morning motivation with Quran verse."""
    db = context.bot_data["db"]
    users = db.get_active_users()
    today = datetime.now().date().isoformat()

    verse = await get_quran_verse()

    for user_id in users:
        try:
            user = db.get_user(user_id)
            if not user:
                continue

            msg = f"🌅 صبح بخیر!\n\n{verse}\n\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"🎯 امروز رو با انرژی شروع کن!\n"
            msg += f"📚 جلسه {user['course_session']} منتظرته\n"
            msg += f"💪 ۳ عادت امروز رو انجام بده\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"\n{random.choice(MOTIVATIONAL_MSGS)}"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 شروع امروز!", callback_data="show_today")],
            ])

            await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Morning motivation error for {user_id}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Course Reminders (Smart - only if not watched)
# ══════════════════════════════════════════════════════════════════════════════


async def job_course_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send course reminder only to users who haven't watched today."""
    db = context.bot_data["db"]
    users = db.get_active_users()
    today = datetime.now().date().isoformat()

    for user_id in users:
        try:
            # Skip if already watched today
            if db.get_course_today(user_id, today):
                continue

            user = db.get_user(user_id)
            if not user:
                continue

            streak = db.get_streak(user_id, "course")
            session = user["course_session"]
            chelle = user["course_chelle"]

            msg = f"📚 {random.choice(COURSE_REMINDER_MSGS)}\n\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"📍 جلسه {session} | چهله {chelle} از ۹\n"
            msg += f"⏱ فقط ۱۵ دقیقه!\n"

            if streak["current"] > 0:
                msg += f"🔥 استریک: {streak['current']} روز — نذار قطع بشه!\n"
            elif streak["best"] > 0:
                msg += f"💪 رکوردت {streak['best']} روز بود. رکورد بزن!\n"

            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ دیدم! ثبت کن", callback_data="course_done")],
            ])

            await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Course reminder error for {user_id}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Habit Reminders (Smart - only incomplete habits)
# ══════════════════════════════════════════════════════════════════════════════


async def job_habit_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send habit reminder only for incomplete habits."""
    db = context.bot_data["db"]
    users = db.get_active_users()
    today = datetime.now().date().isoformat()

    for user_id in users:
        try:
            habits_today = db.get_today_habits(user_id, today)
            incomplete = [key for key in HABIT_ORDER if habits_today[key] is None]

            if not incomplete:
                continue  # All done! No reminder needed

            done_count = 3 - len(incomplete)
            user = db.get_user(user_id)
            if not user:
                continue

            # Build message based on progress
            if done_count == 0:
                header = "⏰ هنوز شروع نکردی!"
                emoji = "😅"
            elif done_count == 1:
                header = "⏰ یکی انجام شد، دوتا مونده!"
                emoji = "💪"
            else:
                header = "⏰ فقط یکی مونده! تمومش کن!"
                emoji = "🔥"

            msg = f"{header} {emoji}\n\n"
            msg += f"{random.choice(HABIT_REMINDER_MSGS)}\n\n"

            for key in incomplete:
                habit = HABITS[key]
                streak = db.get_streak(user_id, key)
                streak_text = f" (🔥{streak['current']})" if streak["current"] > 0 else ""
                msg += f"  ⬜ {habit['icon']} {habit['name']}{streak_text}\n"

            msg += f"\n💡 حتی لقمه اضطراری 🔴 هم حسابه!"

            # Quick action buttons for incomplete habits
            keyboard = []
            for key in incomplete:
                habit = HABITS[key]
                keyboard.append([InlineKeyboardButton(
                    f"{habit['icon']} {habit['name']} — انجام بده!",
                    callback_data=f"pick_{key}",
                )])

            await context.bot.send_message(
                chat_id=user_id,
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except Exception as e:
            logger.error(f"Habit reminder error for {user_id}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Journal Reminder
# ══════════════════════════════════════════════════════════════════════════════


async def job_journal_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Remind user to write nightly analysis."""
    db = context.bot_data["db"]
    users = db.get_active_users()
    today = datetime.now().date().isoformat()

    for user_id in users:
        try:
            # Skip if already wrote today
            if db.get_journal(user_id, today):
                continue

            msg = f"📝 {random.choice(JOURNAL_PROMPTS)}\n\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"✨ نوشتن تحلیل = +15 XP\n"
            msg += f"💡 فقط چند خط بنویس. هرچی از دلت میاد.\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            msg += f"برای نوشتن، /journal رو بزن یا همینجا بنویس:"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 الان می‌نویسم", callback_data="start_journal")],
            ])

            await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Journal reminder error for {user_id}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Daily Summary
# ══════════════════════════════════════════════════════════════════════════════


async def job_daily_summary(context: ContextTypes.DEFAULT_TYPE):
    """Send nightly summary with full stats."""
    db = context.bot_data["db"]
    gamification = context.bot_data["gamification"]
    users = db.get_active_users()
    today = datetime.now().date().isoformat()

    for user_id in users:
        try:
            user = db.get_user(user_id)
            if not user:
                continue

            habits_today = db.get_today_habits(user_id, today)
            done_count = sum(1 for v in habits_today.values() if v is not None)
            course_today = db.get_course_today(user_id, today)
            journal_today = db.get_journal(user_id, today)

            # Header with progress
            if done_count == 3:
                progress = "🟩🟩🟩"
                header = "🏆 روز عالی!"
            elif done_count == 2:
                progress = "🟩🟩⬜"
                header = "👍 خوب بود!"
            elif done_count == 1:
                progress = "🟩⬜⬜"
                header = "بد نبود!"
            else:
                progress = "⬜⬜⬜"
                header = "فردا جبران کن 💪"

            msg = f"🌙 خلاصه امشب\n\n"
            msg += f"{progress}  عادت‌ها: {done_count}/3 — {header}\n\n"

            # Habit details
            for key in HABIT_ORDER:
                habit = HABITS[key]
                log = habits_today[key]
                if log:
                    level_info = habit["levels"][log["level"]]
                    msg += f"  ✅ {habit['icon']} {habit['name']} ({level_info['icon']})\n"
                else:
                    msg += f"  ❌ {habit['icon']} {habit['name']}\n"

            msg += f"\n📚 دوره: {'✅' if course_today else '❌'}\n"
            msg += f"📝 تحلیل: {'✅' if journal_today else '❌'}\n"

            # XP summary
            level_info = gamification.get_level_info(user["xp"])
            msg += f"\n{gamification.format_xp_bar(user['xp'])}\n"
            msg += f"📊 XP کل: {user['xp']}\n"

            # Streaks
            streaks = db.get_all_streaks(user_id)
            active_streaks = [(k, v) for k, v in streaks.items() if v["current"] > 0 and k in HABIT_ORDER]
            if active_streaks:
                msg += f"\n🔥 استریک: "
                parts = []
                for key, s in active_streaks:
                    parts.append(f"{HABITS[key]['icon']}{s['current']}")
                msg += " | ".join(parts)
                msg += "\n"

            # Motivational closing
            if done_count == 3 and course_today:
                msg += f"\n🌟 روز فوق‌العاده‌ای بود! فردا هم همینطور! 💎"
            elif done_count >= 2:
                msg += f"\n{random.choice(MOTIVATIONAL_MSGS)}"
            else:
                msg += f"\n💡 فردا از صبح شروع کن. یادت باشه: لقمه اضطراری هم قبوله!"

            msg += f"\n\nشب بخیر 🌙"

            await context.bot.send_message(chat_id=user_id, text=msg)
        except Exception as e:
            logger.error(f"Daily summary error for {user_id}: {e}")
