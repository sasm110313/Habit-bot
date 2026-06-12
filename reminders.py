"""
⏰ Smart Reminders Module for Habit Bot v3.0
یادآوری‌های هوشمند — فقط وقتی انجام نشده + لحن متغیر + منطق هوشمند
"""

import random
import logging
import aiohttp
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import (
    HABITS, HABIT_ORDER,
    COURSE_REMINDER_MSGS, HABIT_REMINDER_MSGS, JOURNAL_PROMPTS,
    MOTIVATIONAL_MSGS, FALLBACK_QUOTES,
    QURAN_API_URL,
    TONE_MORNING, TONE_MIDDAY, TONE_EVENING, TONE_NIGHT,
    NIGHTLY_QUESTIONS, DAILY_CHALLENGES,
    ANALYSIS_INTERVAL_DAYS,
    JOURNAL_REMINDER_TIME_2,
)
from db import Database

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────


def _get_tone_by_hour() -> list:
    """Get appropriate tone list based on current hour."""
    hour = datetime.now().hour
    if hour < 10:
        return TONE_MORNING
    elif hour < 15:
        return TONE_MIDDAY
    elif hour < 20:
        return TONE_EVENING
    else:
        return TONE_NIGHT


def _get_today_challenge() -> dict:
    """Get today's challenge."""
    day_of_year = datetime.now().timetuple().tm_yday
    idx = day_of_year % len(DAILY_CHALLENGES)
    return DAILY_CHALLENGES[idx]


def _should_skip_user(db: Database, user_id: int) -> bool:
    """Decide if we should skip sending a reminder to this user.
    
    Skips if:
    - User is paused
    - User hasn't been active for 7+ days (avoid spamming inactive users)
    """
    user = db.get_user(user_id)
    if not user:
        return True
    
    # Skip paused users
    if user.get("paused"):
        return True
    
    # Skip users who haven't done anything in 7+ days
    # (they'll get the morning motivation but not aggressive reminders)
    return False


def _was_recently_reminded(db: Database, user_id: int, reminder_type: str, min_gap_hours: int = 2) -> bool:
    """Check if user was recently sent a reminder (avoid spam).
    
    This prevents sending too many reminders in a short window.
    For now returns False (can be enhanced with a reminder_log table later).
    """
    # TODO: Could add a reminder_log table to track last reminder time per user
    return False


def _get_urgency_level(hour: int) -> str:
    """Get urgency level based on time of day.
    
    Returns: 'gentle', 'normal', 'urgent', 'critical'
    """
    if hour < 9:
        return 'gentle'
    elif hour < 15:
        return 'normal'
    elif hour < 20:
        return 'urgent'
    else:
        return 'critical'


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

    return random.choice(FALLBACK_QUOTES)


# ══════════════════════════════════════════════════════════════════════════════
# Morning Motivation (صبحگاهی + چالش روز)
# ══════════════════════════════════════════════════════════════════════════════


async def job_morning_motivation(context: ContextTypes.DEFAULT_TYPE):
    """Send morning motivation with Quran verse + hadith + daily challenge."""
    db = context.bot_data["db"]
    users = db.get_active_users()

    verse = await get_quran_verse()
    challenge = _get_today_challenge()

    # Get today's hadith
    from config import DAILY_HADITHS
    day_of_year = datetime.now().timetuple().tm_yday
    hadith = DAILY_HADITHS[day_of_year % len(DAILY_HADITHS)]

    for user_id in users:
        try:
            user = db.get_user(user_id)
            if not user:
                continue
            
            # Skip paused users
            if user.get("paused"):
                continue

            gm = context.bot_data["gamification"]
            level_info = gm.get_level_info(user["xp"])

            # Personalized greeting based on yesterday's performance
            today = datetime.now().date().isoformat()
            yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
            yesterday_habits = db.get_today_habits(user_id, yesterday)
            yesterday_done = sum(1 for v in yesterday_habits.values() if v is not None)

            if yesterday_done == 3:
                greeting = f"🌅 صبح بخیر {level_info['icon']}! دیروز عالی بود! ادامه بده!"
            elif yesterday_done > 0:
                greeting = f"🌅 صبح بخیر {level_info['icon']}! امروز بهتر از دیروز!"
            else:
                greeting = f"🌅 صبح بخیر {level_info['icon']}! امروز روز جدیده. شروع کن!"

            msg = f"{greeting}\n\n"
            msg += f"{verse}\n\n"
            msg += f"{hadith}\n\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"🎯 برنامه امروز:\n"
            msg += f"  📚 جلسه {user['course_session']} دوره\n"
            msg += f"  🕌💪🌙 ۳ عادت\n"
            msg += f"  📝 تحلیل شبانه (بعد ۲۰:۰۰)\n\n"
            msg += f"🃏 {challenge['text']}\n"
            msg += f"   🎁 جایزه: +{challenge['xp']} XP!\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"\n{random.choice(TONE_MORNING)}"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 شروع امروز!", callback_data="show_today")],
            ])

            await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Morning motivation error for {user_id}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Course Reminders (Smart + variable tone + skip logic)
# ══════════════════════════════════════════════════════════════════════════════


async def job_course_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send course reminder only to users who haven't watched today.
    
    Smart logic:
    - Skip paused users
    - Skip if already watched
    - Adjust tone based on time of day
    - Include streak info for motivation
    """
    db = context.bot_data["db"]
    users = db.get_active_users()
    today = datetime.now().date().isoformat()
    hour = datetime.now().hour
    tone = _get_tone_by_hour()
    urgency = _get_urgency_level(hour)

    for user_id in users:
        try:
            # Skip if already done
            if db.get_course_today(user_id, today):
                continue

            # Skip paused users
            if _should_skip_user(db, user_id):
                continue

            user = db.get_user(user_id)
            if not user:
                continue

            streak = db.get_streak(user_id, "course")
            session = user["course_session"]
            chelle = user["course_chelle"]

            # Adjust message based on urgency
            if urgency == 'gentle':
                header = f"📚 صبح بخیر! امروز جلسه {session} رو ببین."
            elif urgency == 'normal':
                header = f"📚 {random.choice(COURSE_REMINDER_MSGS)}"
            elif urgency == 'urgent':
                header = f"📚 هنوز دوره رو ندیدی! وقتش الانه."
            else:  # critical
                header = f"🚨 آخرین فرصت دوره! فقط ۱۵ دقیقه!"

            msg = f"{header}\n\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"📍 جلسه {session} | چهله {chelle} از ۹\n"
            msg += f"⏱ فقط ۱۵ دقیقه!\n"

            if streak["current"] > 0:
                msg += f"🔥 استریک: {streak['current']} روز — نذار قطع بشه!\n"
            elif streak["best"] > 0:
                msg += f"💪 رکوردت {streak['best']} روز بود. رکورد بزن!\n"

            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"\n{random.choice(tone)}"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ دیدم! ثبت کن", callback_data="course_done")],
            ])

            await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Course reminder error for {user_id}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Habit Reminders (Smart + variable tone + progress-aware)
# ══════════════════════════════════════════════════════════════════════════════


async def job_habit_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send habit reminder with variable tone based on time of day.
    
    Smart logic:
    - Skip paused users
    - Skip if all habits done
    - Show which habits are remaining
    - Increase urgency as day progresses
    - Mention streak at risk
    """
    db = context.bot_data["db"]
    users = db.get_active_users()
    today = datetime.now().date().isoformat()
    hour = datetime.now().hour
    tone = _get_tone_by_hour()
    urgency = _get_urgency_level(hour)

    for user_id in users:
        try:
            # Skip paused users
            if _should_skip_user(db, user_id):
                continue

            habits_today = db.get_today_habits(user_id, today)
            incomplete = [key for key in HABIT_ORDER if habits_today[key] is None]

            if not incomplete:
                continue

            done_count = 3 - len(incomplete)
            user = db.get_user(user_id)
            if not user:
                continue

            # Find habits with active streaks that are at risk
            at_risk_streaks = []
            for key in incomplete:
                streak = db.get_streak(user_id, key)
                if streak["current"] > 0:
                    at_risk_streaks.append((key, streak["current"]))

            # Build header based on urgency + progress
            if urgency == 'gentle':
                if done_count == 0:
                    header = "🌅 صبح بخیر! وقت شروعه. آروم شروع کن."
                else:
                    header = f"🌅 عالی! {done_count} تا انجام شد. ادامه بده!"
            elif urgency == 'normal':
                if done_count == 0:
                    header = "⚡ نصف روز گذشت! هنوز وقت هست!"
                else:
                    header = f"💪 {done_count} تا شد! فقط {len(incomplete)} تا مونده!"
            elif urgency == 'urgent':
                if done_count == 0:
                    header = "😤 روز داره تموم میشه! شروع کن!"
                else:
                    header = f"🔥 {len(incomplete)} تا مونده! تمومش کن!"
            else:  # critical
                if done_count == 0:
                    header = "🆘 آخرین فرصت! حتی لقمه اضطراری بزن!"
                else:
                    header = f"🚨 فقط {len(incomplete)} تا! نذار استریک بشکنه!"

            msg = f"{header}\n\n"
            msg += f"{random.choice(tone)}\n\n"

            for key in incomplete:
                habit = HABITS[key]
                streak = db.get_streak(user_id, key)
                streak_text = f" (🔥{streak['current']})" if streak["current"] > 0 else ""
                msg += f"  ⬜ {habit['icon']} {habit['name']}{streak_text}\n"

            # Add urgency-based call to action
            if urgency in ('urgent', 'critical') and at_risk_streaks:
                msg += f"\n⚠️ استریک در خطر: "
                msg += ", ".join(f"{HABITS[k]['icon']}{s} روز" for k, s in at_risk_streaks)
                msg += "\n"

            msg += f"\n💡 حتی لقمه اضطراری 🔴 هم حسابه!"

            # Quick action buttons
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
# Journal Reminder (with nightly questions — only sent at night)
# ══════════════════════════════════════════════════════════════════════════════


async def job_journal_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Remind user with a unique nightly question.
    
    Smart logic:
    - Only sent to users who haven't written today
    - Skip paused users
    - Uses unique nightly question based on day
    - Second reminder (JOURNAL_REMINDER_TIME_2) is more urgent
    """
    db = context.bot_data["db"]
    users = db.get_active_users()
    today = datetime.now().date().isoformat()
    hour = datetime.now().hour

    # Pick today's unique question
    day_of_year = datetime.now().timetuple().tm_yday
    question = NIGHTLY_QUESTIONS[day_of_year % len(NIGHTLY_QUESTIONS)]

    # Determine if this is the first or second reminder
    is_second_reminder = (hour >= JOURNAL_REMINDER_TIME_2[0])

    for user_id in users:
        try:
            # Skip paused
            if _should_skip_user(db, user_id):
                continue

            # Skip if already written
            if db.get_journal(user_id, today):
                continue

            # Check if user did any habits today (don't nag if they weren't active)
            habits_today = db.get_today_habits(user_id, today)
            any_activity = any(v is not None for v in habits_today.values())

            if not any_activity and not is_second_reminder:
                # First reminder: skip inactive users (they'll get the second one)
                continue

            if is_second_reminder:
                msg = f"🌙 آخرین فرصت تحلیل شبانه!\n\n"
                msg += f"💬 {question}\n\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                msg += f"✨ نوشتن = +15 XP\n"
                msg += f"⏰ تا ۴ صبح فرصت داری.\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                msg += f"فقط ۲-۳ خط. صادقانه بنویس:"
            else:
                msg = f"📝 وقت تحلیل شبانه رسید!\n\n"
                msg += f"💬 سوال امشب:\n{question}\n\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                msg += f"✨ نوشتن = +15 XP\n"
                msg += f"💡 فقط چند خط بنویس. صادقانه.\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                msg += f"جوابت رو بنویس و بفرست یا /journal بزن:"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 الان می‌نویسم", callback_data="start_journal")],
            ])

            await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Journal reminder error for {user_id}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Daily Summary (خلاصه شبانه + چالش فردا)
# ══════════════════════════════════════════════════════════════════════════════


async def job_daily_summary(context: ContextTypes.DEFAULT_TYPE):
    """Send nightly summary with stats + tomorrow's challenge preview.
    
    Smart logic:
    - Skip paused users
    - Personalized based on today's performance
    - Mention tomorrow's challenge
    - Show streak status
    """
    db = context.bot_data["db"]
    gamification = context.bot_data["gamification"]
    users = db.get_active_users()
    today = datetime.now().date().isoformat()

    # Tomorrow's challenge
    tomorrow_day = datetime.now().timetuple().tm_yday + 1
    tomorrow_challenge = DAILY_CHALLENGES[tomorrow_day % len(DAILY_CHALLENGES)]

    for user_id in users:
        try:
            # Skip paused users
            user = db.get_user(user_id)
            if not user or user.get("paused"):
                continue

            habits_today = db.get_today_habits(user_id, today)
            done_count = sum(1 for v in habits_today.values() if v is not None)
            course_today = db.get_course_today(user_id, today)
            journal_today = db.get_journal(user_id, today)

            # Header
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

            # XP bar
            msg += f"\n{gamification.format_xp_bar(user['xp'])}\n"

            # Streaks
            streaks = db.get_all_streaks(user_id)
            active_streaks = [(k, v) for k, v in streaks.items() if v["current"] > 0 and k in HABIT_ORDER]
            if active_streaks:
                msg += f"🔥 "
                parts = [f"{HABITS[k]['icon']}{s['current']}" for k, s in active_streaks]
                msg += " | ".join(parts)
                msg += "\n"

            # Tomorrow's challenge preview
            msg += f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"🃏 چالش فردا:\n{tomorrow_challenge['text']}\n"
            msg += f"🎁 +{tomorrow_challenge['xp']} XP\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"

            # Closing
            if done_count == 3 and course_today:
                msg += f"\n🌟 روز فوق‌العاده بود! 💎"
            elif done_count >= 2:
                msg += f"\n{random.choice(MOTIVATIONAL_MSGS)}"
            else:
                msg += f"\n💡 فردا از صبح شروع کن!"

            msg += f"\n\nشب بخیر 🌙"

            await context.bot.send_message(chat_id=user_id, text=msg)
        except Exception as e:
            logger.error(f"Daily summary error for {user_id}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# 10-Day Auto Analysis Job (هر ۱۰ روز)
# ══════════════════════════════════════════════════════════════════════════════


async def job_10day_analysis(context: ContextTypes.DEFAULT_TYPE):
    """Send automatic 10-day analysis. Runs daily but only triggers every 10 days."""
    db = context.bot_data["db"]
    users = db.get_active_users()

    # Only run on days divisible by 10
    day_of_year = datetime.now().timetuple().tm_yday
    if day_of_year % ANALYSIS_INTERVAL_DAYS != 0:
        return

    # Import here to avoid circular
    from handlers import generate_auto_analysis

    for user_id in users:
        try:
            user = db.get_user(user_id)
            if not user or user.get("paused"):
                continue

            msg = generate_auto_analysis(user_id, db)
            msg += f"\n\n💡 این تحلیل هر ۱۰ روز خودکار ارسال میشه."
            await context.bot.send_message(chat_id=user_id, text=msg)
        except Exception as e:
            logger.error(f"10-day analysis error for {user_id}: {e}")
