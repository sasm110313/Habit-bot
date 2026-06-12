"""
🤖 Handlers Module for Habit Bot v3.0
تمام هندلرهای ربات
"""

import random
import logging
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import ContextTypes

from config import (
    HABITS, HABIT_ORDER, ACHIEVEMENTS, LEVELS,
    MOTIVATIONAL_MSGS, XP_COURSE_WATCHED, XP_JOURNAL_WRITTEN,
    TOTAL_CHELLE, DAYS_PER_CHELLE, SESSION_DURATION_MINUTES,
    DAILY_CHALLENGES, XP_CHALLENGE_BONUS,
    JOURNEY_MILESTONES, NIGHTLY_QUESTIONS,
    COACH_TIPS, ANALYSIS_INTERVAL_DAYS,
)
from datetime import timedelta
from db import Database
from gamification import Gamification

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def today_str() -> str:
    return datetime.now().date().isoformat()


def main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        ["📋 وضعیت امروز", "📚 دوره"],
        ["🃏 چالش روز", "🗺️ نقشه سفر"],
        ["📊 آمار", "🏆 دستاوردها"],
        ["📝 تحلیل", "🔥 استریک"],
        ["📅 تقویم", "ℹ️ راهنما"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def _get_db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    return context.bot_data["db"]


def _get_gm(context: ContextTypes.DEFAULT_TYPE) -> Gamification:
    return context.bot_data["gamification"]


# ─────────────────────────────────────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────────────────────────────────────


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = _get_db(context)
    gm = _get_gm(context)
    db.get_or_create_user(user.id, user.username or "", user.first_name or "")

    # Check comeback
    gm.check_comeback(user.id, today_str())

    msg = f"""سلام {user.first_name}! 👋

به ربات عادت‌سازی v3.0 خوش اومدی! 🎯

━━━━━━━━━━━━━━━━━━━━━━━━
🕌  تمرکز در نماز
🌙  خواب منظم
💪  ورزش
━━━━━━━━━━━━━━━━━━━━━━━━

هر عادت ۳ سطح داره:
🟢 لقمه کوچک — حالت عادی (۳۰ XP)
🟡 لقمه ویژه — یه کم کمتر (۲۰ XP)
🔴 لقمه اضطراری — شرایط سخت (۱۰ XP)

📚 دوره آموزشی: ۹ چهله (۳۶۰ جلسه)
🎮 سیستم XP + لول + دستاورد!
📝 تحلیل شبانه
⏰ یادآوری هوشمند (فقط تا وقتی انجام ندادی!)

━━━━━━━━━━━━━━━━━━━━━━━━

📍 اول از همه:
الان جلسه چندم دوره هستی؟
عدد رو بفرست (مثلاً: 80)"""

    # Set state to expect course session number
    context.user_data["awaiting"] = "course_session"

    await update.message.reply_text(msg, reply_markup=main_keyboard())


# ─────────────────────────────────────────────────────────────────────────────
# /help
# ─────────────────────────────────────────────────────────────────────────────


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """📖 راهنمای ربات عادت‌سازی v3.0

━━━━━━━━━━━━━━━━━━━━━━━━
📋 عادت‌ها:
• «📋 وضعیت امروز» → ببین و تیک بزن
• هر عادت ۳ سطح داره
• حتی لقمه اضطراری هم XP میده!

📚 دوره آموزشی:
• «📚 دوره» → ثبت تماشای جلسه
• هر روز فقط ۱ جلسه!
• ۹ چهله (۳۶۰ جلسه)

🎮 گیمیفیکیشن:
• هر کار XP داره
• با XP لول‌آپ میکنی
• دستاوردها رو آنلاک کن!
• استریک نگه‌دار!

📝 تحلیل:
• «📝 تحلیل» → تحلیل شبانه بنویس
• هر شب قبل خواب
• ۱۵ XP برای نوشتن!

⏰ یادآوری:
• صبح: آیه قرآن + انگیزه
• روز: یادآوری عادت (تا وقتی انجام ندادی)
• دوره: ۵ بار در روز (تا وقتی ندیدی)
• شب: یادآور تحلیل + خلاصه روز

━━━━━━━━━━━━━━━━━━━━━━━━
/setsession ۸۰ — تنظیم شماره جلسه دوره
/pause — توقف یادآوری‌ها
/resume — ادامه یادآوری‌ها
/mystats — آمار کلی
━━━━━━━━━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(msg, reply_markup=main_keyboard())


# ─────────────────────────────────────────────────────────────────────────────
# Today Status (وضعیت امروز)
# ─────────────────────────────────────────────────────────────────────────────


async def show_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's status with habit buttons."""
    try:
        user_id = update.effective_user.id
        db = _get_db(context)
        gm = _get_gm(context)
        db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")

        msg, keyboard = _build_today_view(user_id, db, gm)
        await update.message.reply_text(msg, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"show_today error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ خطا: {e}\n\nلطفاً /start بزن.", reply_markup=main_keyboard())


def _build_today_view(user_id: int, db: Database, gm: Gamification) -> tuple:
    """Build today's status message and keyboard."""
    date = today_str()
    habits = db.get_today_habits(user_id, date)
    user = db.get_user(user_id)
    streaks = db.get_all_streaks(user_id)
    done = sum(1 for v in habits.values() if v is not None)

    # Progress header
    bars = ["🟩" if habits[k] else "⬜" for k in HABIT_ORDER]
    progress = "".join(bars)

    if done == 0:
        header = "شروع کن! 💪"
    elif done == 1:
        header = "ادامه بده! 🔥"
    elif done == 2:
        header = "یکی مونده! ⚡"
    else:
        header = "روز کامل! 🏆"

    # XP bar
    xp_bar = gm.format_xp_bar(user["xp"]) if user else ""

    msg = f"📋 وضعیت امروز — {date}\n\n"
    msg += f"{progress}  {done}/3  {header}\n"
    msg += f"{xp_bar}\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"

    # Habit details in message
    for key in HABIT_ORDER:
        habit = HABITS[key]
        log = habits[key]
        streak = streaks.get(key, {"current": 0})

        if log:
            level_info = habit["levels"][log["level"]]
            msg += f"✅ {habit['icon']} {habit['name']} — {level_info['icon']} {level_info['name']}"
        else:
            msg += f"⬜ {habit['icon']} {habit['name']}"

        if streak["current"] > 0:
            msg += f" 🔥{streak['current']}"
        msg += "\n"

    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"

    # Course status
    course_today = db.get_course_today(user_id, date)
    course_icon = "✅" if course_today else "⬜"
    msg += f"📚 دوره: {course_icon} جلسه {user['course_session']}\n"

    # Journal status
    journal = db.get_journal(user_id, date)
    journal_icon = "✅" if journal else "⬜"
    msg += f"📝 تحلیل: {journal_icon}\n"

    # Keyboard
    keyboard = []
    for key in HABIT_ORDER:
        habit = HABITS[key]
        log = habits[key]
        if log:
            level_info = habit["levels"][log["level"]]
            text = f"✅ {habit['icon']} {habit['name']} ({level_info['icon']})"
            keyboard.append([InlineKeyboardButton(text, callback_data=f"detail_{key}")])
        else:
            text = f"⬜ {habit['icon']} {habit['name']} — انجام بده!"
            keyboard.append([InlineKeyboardButton(text, callback_data=f"pick_{key}")])

    # Course button
    if not course_today:
        keyboard.append([InlineKeyboardButton("📚 دوره رو دیدم!", callback_data="course_done")])

    keyboard.append([InlineKeyboardButton("🔄 بروزرسانی", callback_data="show_today")])

    return msg, InlineKeyboardMarkup(keyboard)


# ─────────────────────────────────────────────────────────────────────────────
# Callback Handler (all inline buttons)
# ─────────────────────────────────────────────────────────────────────────────


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    db = _get_db(context)
    gm = _get_gm(context)
    date = today_str()

    # Ensure user exists
    db.get_or_create_user(user_id, query.from_user.username or "", query.from_user.first_name or "")

    # ── Show Today ───────────────────────────────────────────────────────
    if data == "show_today":
        msg, keyboard = _build_today_view(user_id, db, gm)
        await query.edit_message_text(msg, reply_markup=keyboard)
        await query.answer()
        return

    # ── Pick Habit (show levels) ─────────────────────────────────────────
    if data.startswith("pick_"):
        habit_key = data[5:]
        habit = HABITS[habit_key]
        streak = db.get_streak(user_id, habit_key)

        msg = f"{habit['icon']} {habit['name']}\n\n"
        msg += f"کدوم سطح رو انجام دادی?\n"
        if streak["current"] > 0:
            msg += f"🔥 استریک: {streak['current']} روز\n"
        msg += f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n"

        keyboard = []
        for level_key, level in habit["levels"].items():
            text = f"{level['icon']} {level['name']} — {level['desc']} (+{level['xp']} XP)"
            keyboard.append([InlineKeyboardButton(text, callback_data=f"log_{habit_key}_{level_key}")])
        keyboard.append([InlineKeyboardButton("↩️ برگشت", callback_data="show_today")])

        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        await query.answer()
        return

    # ── Detail (already done - show change option) ───────────────────────
    if data.startswith("detail_"):
        habit_key = data[7:]
        habit = HABITS[habit_key]
        log = db.get_today_habits(user_id, date).get(habit_key)

        if log:
            level_info = habit["levels"][log["level"]]
            msg = f"✅ {habit['icon']} {habit['name']}\n\n"
            msg += f"سطح: {level_info['icon']} {level_info['name']}\n"
            msg += f"📝 {level_info['desc']}\n"
            msg += f"⏰ ثبت: {log['completed_at'][:16]}\n"
            msg += f"✨ +{log['xp_earned']} XP\n\n"
            msg += f"می‌خوای عوضش کنی?\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━"
        else:
            msg = f"{habit['icon']} {habit['name']}\nکدوم سطح?"

        keyboard = []
        for level_key, level in habit["levels"].items():
            marker = " ← فعلی" if log and log["level"] == level_key else ""
            text = f"{level['icon']} {level['name']} (+{level['xp']} XP){marker}"
            keyboard.append([InlineKeyboardButton(text, callback_data=f"log_{habit_key}_{level_key}")])
        keyboard.append([InlineKeyboardButton("↩️ برگشت", callback_data="show_today")])

        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        await query.answer()
        return

    # ── Log Habit ────────────────────────────────────────────────────────
    if data.startswith("log_"):
        parts = data.split("_")
        habit_key = parts[1]
        level = parts[2]
        habit = HABITS[habit_key]
        level_info = habit["levels"][level]

        # Log in database
        result = db.log_habit(user_id, habit_key, date, level, level_info["xp"])

        if result["action"] == "removed":
            await query.answer(f"↩️ {habit['name']} برداشته شد.")
        else:
            # Award XP and check achievements
            reward = gm.award_habit_xp(user_id, habit_key, level, date)

            answer_text = f"✅ +{reward['xp_earned']} XP!"
            if reward["streak"] > 1:
                answer_text += f" 🔥{reward['streak']}"
            await query.answer(answer_text)

            # Send achievement notifications
            for ach in reward.get("achievements", []):
                ach_msg = gm.format_achievement_notification(ach)
                await context.bot.send_message(chat_id=user_id, text=ach_msg)

            # Level up notification
            if reward.get("level_up"):
                lvl_msg = gm.format_level_up_notification(reward["level_up"])
                await context.bot.send_message(chat_id=user_id, text=lvl_msg)

        # Refresh today view
        msg, keyboard = _build_today_view(user_id, db, gm)
        await query.edit_message_text(msg, reply_markup=keyboard)
        return

    # ── Course Done ──────────────────────────────────────────────────────
    if data == "course_done":
        user = db.get_user(user_id)
        session = user["course_session"] if user else 1

        # Log course
        is_new = db.log_course(user_id, date, session, XP_COURSE_WATCHED)

        if is_new:
            # Award XP
            reward = gm.award_course_xp(user_id, date)

            msg = f"✅ جلسه {session} ثبت شد! 🎉\n\n"
            msg += f"✨ +{reward['xp_earned']} XP\n"
            msg += f"🔥 استریک دوره: {reward['streak']} روز\n"
            msg += f"📍 جلسه بعدی: {session + 1}\n"
            msg += f"📊 چهله {user['course_chelle']} از {TOTAL_CHELLE}\n"

            # Achievement notifications
            for ach in reward.get("achievements", []):
                msg += f"\n🏅 {ach['icon']} {ach['name']}!"

            if reward.get("level_up"):
                msg += f"\n\n⬆️ لول آپ! {reward['level_up']['icon']} {reward['level_up']['name']}"

            msg += f"\n\n{random.choice(MOTIVATIONAL_MSGS)}"
        else:
            msg = f"↩️ ثبت جلسه امروز لغو شد."

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 برگشت به وضعیت", callback_data="show_today")],
        ])
        await query.edit_message_text(msg, reply_markup=keyboard)
        await query.answer("✅" if is_new else "↩️")
        return

    # ── Start Journal ────────────────────────────────────────────────────
    if data == "start_journal":
        msg = f"📝 تحلیل شبانه\n\n"
        msg += f"هرچی از دلت میاد بنویس:\n"
        msg += f"• حالت امروز چطور بود?\n"
        msg += f"• چه چالشی داشتی?\n"
        msg += f"• فردا چیکار می‌خوای بکنی?\n\n"
        msg += f"✨ نوشتن = +{XP_JOURNAL_WRITTEN} XP\n\n"
        msg += f"الان بنویس و بفرست (یک پیام):"

        context.user_data["awaiting"] = "journal"
        await query.edit_message_text(msg)
        await query.answer()
        return

    # ── Stats navigation ─────────────────────────────────────────────────
    if data == "stats_weekly":
        msg, kb = _build_weekly_stats(user_id, db, gm)
        await query.edit_message_text(msg, reply_markup=kb)
        await query.answer()
        return

    if data == "stats_total":
        msg, kb = _build_total_stats(user_id, db, gm)
        await query.edit_message_text(msg, reply_markup=kb)
        await query.answer()
        return

    # Fallback
    await query.answer("🤔")


# ─────────────────────────────────────────────────────────────────────────────
# Course
# ─────────────────────────────────────────────────────────────────────────────


async def show_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        db = _get_db(context)
        gm = _get_gm(context)
        db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")

        user = db.get_user(user_id)
        date = today_str()
        course_today = db.get_course_today(user_id, date)
        streak = db.get_streak(user_id, "course")

        session = user["course_session"]
        chelle = user["course_chelle"]
        progress_in_chelle = ((session - 1) % DAYS_PER_CHELLE) + 1

        # Chelle progress bar
        chelle_pct = progress_in_chelle / DAYS_PER_CHELLE * 100
        filled = int(chelle_pct / 10)
        chelle_bar = "█" * filled + "░" * (10 - filled)

        msg = f"📚 دوره آموزشی عادت‌سازی\n\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📍 جلسه: {session}\n"
        msg += f"🔄 چهله {chelle} از {TOTAL_CHELLE}\n"
        msg += f"📊 پیشرفت چهله: [{chelle_bar}] {progress_in_chelle}/{DAYS_PER_CHELLE}\n"
        msg += f"⏱ مدت هر جلسه: {SESSION_DURATION_MINUTES} دقیقه\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        if course_today:
            msg += f"✅ امروز دیدی! (جلسه {course_today['session_number']})\n"
        else:
            msg += f"⬜ امروز هنوز ندیدی!\n"

        msg += f"\n🔥 استریک: {streak['current']} روز"
        if streak["best"] > streak["current"]:
            msg += f" (بهترین: {streak['best']})"
        msg += "\n"

        # Button
        if course_today:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ لغو ثبت امروز", callback_data="course_done")],
                [InlineKeyboardButton("📋 وضعیت امروز", callback_data="show_today")],
            ])
        else:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"✅ جلسه {session} رو دیدم!", callback_data="course_done")],
                [InlineKeyboardButton("📋 وضعیت امروز", callback_data="show_today")],
            ])

        await update.message.reply_text(msg, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"show_course error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ خطا: {e}\n\n/start بزن.", reply_markup=main_keyboard())


# ─────────────────────────────────────────────────────────────────────────────
# Set Course Session
# ─────────────────────────────────────────────────────────────────────────────


async def cmd_setsession(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        db = _get_db(context)
        db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")

        if not context.args:
            await update.message.reply_text(
                "مثال: /setsession 80\nعدد جلسه فعلیت رو بنویس.",
                reply_markup=main_keyboard(),
            )
            return

        raw = _normalize_persian_digits(context.args[0].strip())
        try:
            session = int(raw)
            if session < 1 or session > 365:
                raise ValueError()
        except ValueError:
            await update.message.reply_text("❌ عدد ۱ تا ۳۶۵ وارد کن.", reply_markup=main_keyboard())
            return

        db.set_course_session(user_id, session)
        chelle = (session // DAYS_PER_CHELLE) + 1

        await update.message.reply_text(
            f"✅ جلسه دوره روی {session} تنظیم شد!\n📍 چهله {min(chelle, TOTAL_CHELLE)} از {TOTAL_CHELLE}",
            reply_markup=main_keyboard(),
        )
    except Exception as e:
        logger.error(f"cmd_setsession error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ خطا: {e}", reply_markup=main_keyboard())


# ─────────────────────────────────────────────────────────────────────────────
# Statistics
# ─────────────────────────────────────────────────────────────────────────────


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = _get_db(context)
    gm = _get_gm(context)
    db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار هفتگی", callback_data="stats_weekly")],
        [InlineKeyboardButton("📈 آمار کلی", callback_data="stats_total")],
    ])
    await update.message.reply_text("📊 کدوم آمار؟", reply_markup=keyboard)


def _build_weekly_stats(user_id: int, db: Database, gm: Gamification) -> tuple:
    stats = db.get_weekly_stats(user_id)
    user = db.get_user(user_id)

    pct = stats["percentage"]
    filled = int(pct / 10)
    bar = "🟩" * filled + "⬜" * (10 - filled)

    msg = f"📊 آمار ۷ روز اخیر\n\n"
    msg += f"{bar} {pct}%\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"✅ انجام: {stats['total_done']}/21\n"
    msg += f"🏆 روز کامل: {stats['perfect_days']}/7\n"
    msg += f"📚 دوره: {stats['course_days']}/7\n"
    msg += f"✨ XP هفته: +{stats['xp_earned']}\n\n"

    msg += f"📋 عملکرد:\n"
    for key in HABIT_ORDER:
        habit = HABITS[key]
        count = stats["per_habit"][key]
        h_bar = "🟩" * count + "⬜" * (7 - count)
        msg += f"  {habit['icon']} {h_bar} {count}/7\n"

    msg += f"\n📊 توزیع سطوح:\n"
    msg += f"  🟢 کوچک: {stats['levels']['small']}\n"
    msg += f"  🟡 ویژه: {stats['levels']['special']}\n"
    msg += f"  🔴 اضطراری: {stats['levels']['emergency']}\n"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 آمار کلی", callback_data="stats_total")],
    ])
    return msg, keyboard


def _build_total_stats(user_id: int, db: Database, gm: Gamification) -> tuple:
    stats = db.get_total_stats(user_id)
    user = db.get_user(user_id)

    if not stats or not user:
        return "آماری نیست!", InlineKeyboardMarkup([])

    level_info = gm.get_level_info(stats["xp"])

    msg = f"📈 آمار کلی\n\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"{gm.format_xp_bar(stats['xp'])}\n"
    msg += f"✨ XP کل: {stats['xp']}\n"
    if level_info["next_level"]:
        msg += f"⬆️ تا لول بعدی: {level_info['xp_to_next']} XP\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    msg += f"📋 عادت‌ها: {stats['total_habits']} بار\n"
    msg += f"📚 دوره: {stats['total_course']} جلسه\n"
    msg += f"📝 تحلیل: {stats['total_journals']} بار\n"
    msg += f"🏅 دستاوردها: {stats['total_achievements']}\n\n"

    msg += f"📍 دوره: جلسه {stats['course_session']} (چهله {stats['course_chelle']})\n"

    # All-time streaks
    streaks = db.get_all_streaks(user_id)
    msg += f"\n🔥 بهترین استریک‌ها:\n"
    for key in HABIT_ORDER:
        habit = HABITS[key]
        s = streaks.get(key, {"current": 0, "best": 0})
        msg += f"  {habit['icon']} فعلی: {s['current']} | بهترین: {s['best']}\n"
    cs = streaks.get("course", {"current": 0, "best": 0})
    msg += f"  📚 دوره: {cs['current']} | بهترین: {cs['best']}\n"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار هفتگی", callback_data="stats_weekly")],
    ])
    return msg, keyboard


async def cmd_mystats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        db = _get_db(context)
        gm = _get_gm(context)
        db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")

        msg, kb = _build_total_stats(user_id, db, gm)
        await update.message.reply_text(msg, reply_markup=kb)
    except Exception as e:
        logger.error(f"cmd_mystats error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ خطا: {e}", reply_markup=main_keyboard())


# ─────────────────────────────────────────────────────────────────────────────
# Achievements
# ─────────────────────────────────────────────────────────────────────────────


async def show_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = _get_db(context)
    db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")

    unlocked = db.get_achievements(user_id)
    unlocked_keys = {a["achievement_key"] for a in unlocked}

    msg = f"🏆 دستاوردها ({len(unlocked)}/{len(ACHIEVEMENTS)})\n\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"

    # Show unlocked
    if unlocked:
        msg += f"\n✅ آنلاک شده:\n"
        for ach in unlocked:
            key = ach["achievement_key"]
            if key in ACHIEVEMENTS:
                a = ACHIEVEMENTS[key]
                msg += f"  {a['icon']} {a['name']} — {a['desc']}\n"

    # Show locked (teaser)
    locked = [k for k in ACHIEVEMENTS if k not in unlocked_keys]
    if locked:
        msg += f"\n🔒 قفل ({len(locked)}):\n"
        for key in locked[:8]:  # Show max 8 locked
            a = ACHIEVEMENTS[key]
            msg += f"  🔒 ??? — {a['desc']}\n"
        if len(locked) > 8:
            msg += f"  ... و {len(locked) - 8} تای دیگه!\n"

    msg += f"\n━━━━━━━━━━━━━━━━━━━━━━━━"
    await update.message.reply_text(msg, reply_markup=main_keyboard())


# ─────────────────────────────────────────────────────────────────────────────
# Streaks
# ─────────────────────────────────────────────────────────────────────────────


async def show_streaks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        db = _get_db(context)
        db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")

        streaks = db.get_all_streaks(user_id)

        msg = f"🔥 استریک‌ها\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n"

        for key in HABIT_ORDER:
            habit = HABITS[key]
            s = streaks.get(key, {"current": 0, "best": 0})
            current = s["current"]
            best = s["best"]

            if current >= 40:
                fire = "🏅"
            elif current >= 21:
                fire = "💎"
            elif current >= 7:
                fire = "🔥"
            elif current >= 3:
                fire = "✨"
            elif current > 0:
                fire = "🌱"
            else:
                fire = "💤"

            msg += f"\n{habit['icon']} {habit['name']}\n"
            msg += f"  {fire} فعلی: {current} روز\n"
            msg += f"  🏆 بهترین: {best} روز\n"

            milestones = [3, 7, 14, 21, 30, 40, 66]
            next_milestone = next((m for m in milestones if m > current), None)
            if next_milestone:
                remaining = next_milestone - current
                msg += f"  🎯 تا {next_milestone} روز: {remaining} روز مونده\n"

        cs = streaks.get("course", {"current": 0, "best": 0})
        msg += f"\n📚 دوره آموزشی\n"
        msg += f"  {'🔥' if cs['current'] > 0 else '💤'} فعلی: {cs['current']} روز\n"
        msg += f"  🏆 بهترین: {cs['best']} روز\n"

        ps = streaks.get("perfect_day", {"current": 0, "best": 0})
        msg += f"\n🏆 روز کامل\n"
        msg += f"  {'🔥' if ps['current'] > 0 else '💤'} فعلی: {ps['current']} روز\n"
        msg += f"  🏆 بهترین: {ps['best']} روز\n"

        msg += f"\n━━━━━━━━━━━━━━━━━━━━━━━━"
        msg += f"\n\n{random.choice(MOTIVATIONAL_MSGS)}"

        await update.message.reply_text(msg, reply_markup=main_keyboard())
    except Exception as e:
        logger.error(f"show_streaks error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ خطا: {e}", reply_markup=main_keyboard())


# ─────────────────────────────────────────────────────────────────────────────
# Journal (تحلیل)
# ─────────────────────────────────────────────────────────────────────────────


async def show_journal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = _get_db(context)
    db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")

    date = today_str()
    existing = db.get_journal(user_id, date)

    if existing:
        msg = f"📝 تحلیل امروز ({date}):\n\n"
        msg += f"«{existing['content']}»\n\n"
        msg += f"✨ +{existing['xp_earned']} XP\n"
        msg += f"⏰ نوشته شده: {existing['written_at'][:16]}\n\n"
        msg += f"برای ویرایش دوباره بنویس:"
    else:
        msg = f"📝 تحلیل شبانه — {date}\n\n"
        msg += f"هرچی از دلت میاد بنویس:\n"
        msg += f"• حالت چطور بود?\n"
        msg += f"• چه چالشی داشتی?\n"
        msg += f"• فردا چیکار کنی بهتره?\n"
        msg += f"• از ۱ تا ۱۰ امروز چند بود?\n\n"
        msg += f"✨ نوشتن = +{XP_JOURNAL_WRITTEN} XP\n\n"
        msg += f"بنویس و بفرست:"

    # Show recent journals
    recent = db.get_recent_journals(user_id, 5)
    if recent and len(recent) > 1:
        msg += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📜 تحلیل‌های اخیر:\n"
        for j in recent[:3]:
            if j["date"] != date:
                preview = j["content"][:40] + "..." if len(j["content"]) > 40 else j["content"]
                msg += f"  {j['date']}: {preview}\n"

    context.user_data["awaiting"] = "journal"
    await update.message.reply_text(msg, reply_markup=main_keyboard())


async def cmd_journal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shortcut /journal command."""
    await show_journal(update, context)


# ─────────────────────────────────────────────────────────────────────────────
# Pause/Resume
# ─────────────────────────────────────────────────────────────────────────────


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = _get_db(context)
    db.set_paused(update.effective_user.id, True)
    await update.message.reply_text(
        "⏸ یادآوری‌ها متوقف شد.\n/resume برای ادامه",
        reply_markup=main_keyboard(),
    )


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = _get_db(context)
    db.set_paused(update.effective_user.id, False)
    await update.message.reply_text(
        "▶️ یادآوری‌ها فعال شد! 🔔",
        reply_markup=main_keyboard(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Text Message Handler (menu buttons + journal input)
# ─────────────────────────────────────────────────────────────────────────────


def _normalize_persian_digits(text: str) -> str:
    """Convert Persian/Arabic digits to English digits."""
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    result = text
    for i, (p, a) in enumerate(zip(persian_digits, arabic_digits)):
        result = result.replace(p, str(i)).replace(a, str(i))
    return result


def _is_menu_button(text: str) -> bool:
    """Check if text is a menu button."""
    menu_items = [
        "📋 وضعیت امروز", "📚 دوره", "📊 آمار",
        "🏆 دستاوردها", "📝 تحلیل", "🔥 استریک", "ℹ️ راهنما",
        "🃏 چالش روز", "🗺️ نقشه سفر", "📅 تقویم",
    ]
    return text in menu_items


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    db = _get_db(context)
    gm = _get_gm(context)

    # ── ALWAYS handle menu buttons first (even during awaiting states) ───
    if _is_menu_button(text):
        # Cancel any awaiting state when user clicks menu
        context.user_data.pop("awaiting", None)

        if text == "📋 وضعیت امروز":
            await show_today(update, context)
        elif text == "📚 دوره":
            await show_course(update, context)
        elif text == "📊 آمار":
            await show_stats(update, context)
        elif text == "🏆 دستاوردها":
            await show_achievements(update, context)
        elif text == "📝 تحلیل":
            await show_journal(update, context)
        elif text == "🔥 استریک":
            await show_streaks(update, context)
        elif text == "🃏 چالش روز":
            await show_daily_challenge(update, context)
        elif text == "🗺️ نقشه سفر":
            await show_journey_map(update, context)
        elif text == "📅 تقویم":
            await show_monthly_calendar(update, context)
        elif text == "ℹ️ راهنما":
            await cmd_help(update, context)
        return

    # ── Check if we're awaiting specific input ───────────────────────────
    awaiting = context.user_data.get("awaiting")

    if awaiting == "course_session":
        # User is setting their course session number
        # Normalize Persian digits and strip whitespace
        normalized = _normalize_persian_digits(text).strip()
        try:
            session = int(normalized)
            if 1 <= session <= 365:
                db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
                db.set_course_session(user_id, session)
                chelle = (session // DAYS_PER_CHELLE) + 1
                context.user_data.pop("awaiting", None)
                await update.message.reply_text(
                    f"✅ عالی! جلسه {session} ثبت شد.\n"
                    f"📍 چهله {min(chelle, TOTAL_CHELLE)} از {TOTAL_CHELLE}\n\n"
                    f"حالا از دکمه «📋 وضعیت امروز» شروع کن! 🚀",
                    reply_markup=main_keyboard(),
                )
                return
            else:
                await update.message.reply_text(
                    "❌ عدد باید بین ۱ تا ۳۶۵ باشه.\nمثلاً: 80\n\nیا از دکمه‌های منو استفاده کن (جلسه پیش‌فرض: ۱)",
                    reply_markup=main_keyboard(),
                )
                return
        except ValueError:
            # Not a number - cancel awaiting and set default
            context.user_data.pop("awaiting", None)
            db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
            await update.message.reply_text(
                "⏭ جلسه دوره بعداً تنظیم کن با /setsession\n"
                "الان از دکمه‌های منو استفاده کن! 👇",
                reply_markup=main_keyboard(),
            )
            return

    if awaiting == "journal":
        # User is writing their journal
        db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
        date = today_str()
        is_new = db.save_journal(user_id, date, text, xp=XP_JOURNAL_WRITTEN)
        context.user_data.pop("awaiting", None)

        if is_new:
            reward = gm.award_journal_xp(user_id)
            msg = f"✅ تحلیل ثبت شد! 📝\n\n"
            msg += f"✨ +{reward['xp_earned']} XP\n"

            for ach in reward.get("achievements", []):
                msg += f"\n🏅 {ach['icon']} {ach['name']}!"

            if reward.get("level_up"):
                msg += f"\n\n⬆️ لول آپ! {reward['level_up']['icon']} {reward['level_up']['name']}"

            msg += f"\n\n{random.choice(MOTIVATIONAL_MSGS)}"
        else:
            msg = f"✅ تحلیل بروزرسانی شد! 📝"

        await update.message.reply_text(msg, reply_markup=main_keyboard())
        return

    # ── Unknown text ─────────────────────────────────────────────────────
    await update.message.reply_text(
        "🤔 از دکمه‌های منو استفاده کن!\n/help برای راهنما",
        reply_markup=main_keyboard(),
    )



# ─────────────────────────────────────────────────────────────────────────────
# 🃏 Daily Challenge (چالش روزانه)
# ─────────────────────────────────────────────────────────────────────────────


def _get_today_challenge() -> dict:
    """Get today's challenge based on day of year."""
    day_of_year = datetime.now().timetuple().tm_yday
    idx = day_of_year % len(DAILY_CHALLENGES)
    return DAILY_CHALLENGES[idx]


async def show_daily_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's daily challenge."""
    try:
        user_id = update.effective_user.id
        db = _get_db(context)
        gm = _get_gm(context)
        db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")

        challenge = _get_today_challenge()
        user = db.get_user(user_id)
        date = today_str()

        # Check if challenge is completed
        challenge_done = _check_challenge_complete(user_id, db, challenge, date)

        msg = f"🃏 چالش روزانه\n\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"{challenge['text']}\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        msg += f"🎁 جایزه: +{challenge['xp']} XP بونوس!\n\n"

        if challenge_done:
            msg += f"✅ چالش امروز انجام شد! 🎉\n"
            msg += f"✨ +{challenge['xp']} XP دریافت کردی!"
        else:
            msg += f"⬜ هنوز انجام نشده\n"
            msg += f"💡 عادت‌هات رو انجام بده تا چالش تکمیل بشه!"

        await update.message.reply_text(msg, reply_markup=main_keyboard())
    except Exception as e:
        logger.error(f"show_daily_challenge error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ خطا: {e}", reply_markup=main_keyboard())


def _check_challenge_complete(user_id: int, db: Database, challenge: dict, date: str) -> bool:
    """Check if today's challenge is completed."""
    habits = db.get_today_habits(user_id, date)
    condition = challenge["condition"]

    if condition == "all_small":
        return all(habits[k] and habits[k]["level"] == "small" for k in HABIT_ORDER)
    elif condition == "early_habit":
        for k in HABIT_ORDER:
            if habits[k] and habits[k]["completed_at"]:
                hour = int(habits[k]["completed_at"][11:13])
                if hour < 8:
                    return True
        return False
    elif condition == "course_first":
        course = db.get_course_today(user_id, date)
        return course is not None
    elif condition == "perfect_journal":
        done = sum(1 for v in habits.values() if v is not None)
        journal = db.get_journal(user_id, date)
        return done >= 3 and journal is not None
    elif condition == "namaz_small":
        return habits["namaz"] is not None and habits["namaz"]["level"] == "small"
    elif condition == "exercise_small":
        return habits["exercise"] is not None and habits["exercise"]["level"] == "small"
    elif condition == "sleep_small":
        return habits["sleep"] is not None and habits["sleep"]["level"] == "small"
    elif condition == "any_done":
        return any(v is not None for v in habits.values())
    elif condition == "fast_complete":
        done = sum(1 for v in habits.values() if v is not None)
        if done < 3:
            return False
        for k in HABIT_ORDER:
            if habits[k] and habits[k]["completed_at"]:
                hour = int(habits[k]["completed_at"][11:13])
                if hour >= 15:
                    return False
        return True
    elif condition == "full_day":
        done = sum(1 for v in habits.values() if v is not None)
        course = db.get_course_today(user_id, date)
        journal = db.get_journal(user_id, date)
        return done >= 3 and course is not None and journal is not None
    return False


# ─────────────────────────────────────────────────────────────────────────────
# 🗺️ Journey Map (نقشه سفر)
# ─────────────────────────────────────────────────────────────────────────────


async def show_journey_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the 9-chelle journey map."""
    try:
        user_id = update.effective_user.id
        db = _get_db(context)
        gm = _get_gm(context)
        db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")

        user = db.get_user(user_id)
        current_chelle = user["course_chelle"] if user else 1
        total_stats = db.get_total_stats(user_id)

        msg = f"🗺️ نقشه سفر عادت‌سازی\n\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"

        for milestone in JOURNEY_MILESTONES:
            chelle_num = milestone["chelle"]
            if chelle_num < current_chelle:
                # Completed
                msg += f"  ✅ {milestone['icon']} چهله {chelle_num}: {milestone['name']}\n"
            elif chelle_num == current_chelle:
                # Current - with progress
                session = user["course_session"] if user else 1
                progress_in = ((session - 1) % DAYS_PER_CHELLE) + 1
                pct = int(progress_in / DAYS_PER_CHELLE * 100)
                bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
                msg += f"  ▶️ {milestone['icon']} چهله {chelle_num}: {milestone['name']}\n"
                msg += f"     [{bar}] {pct}% ({progress_in}/{DAYS_PER_CHELLE})\n"
                msg += f"     📝 {milestone['desc']}\n"
            else:
                # Future
                msg += f"  🔒 ⬜ چهله {chelle_num}: ???\n"

        msg += f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n"

        # Overall progress
        total_days = (current_chelle - 1) * DAYS_PER_CHELLE
        session = user["course_session"] if user else 1
        total_days += ((session - 1) % DAYS_PER_CHELLE) + 1
        overall_pct = int(total_days / (TOTAL_CHELLE * DAYS_PER_CHELLE) * 100)
        msg += f"\n📊 پیشرفت کلی: {overall_pct}% ({total_days}/{TOTAL_CHELLE * DAYS_PER_CHELLE} روز)\n"
        msg += f"✨ XP کل: {total_stats.get('xp', 0)}\n"
        msg += f"{gm.format_xp_bar(user['xp']) if user else ''}\n"

        # XP Prediction
        prediction = _predict_level_up(user_id, db, gm)
        if prediction:
            msg += f"\n📈 {prediction}"

        await update.message.reply_text(msg, reply_markup=main_keyboard())
    except Exception as e:
        logger.error(f"show_journey_map error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ خطا: {e}", reply_markup=main_keyboard())


# ─────────────────────────────────────────────────────────────────────────────
# 📅 Monthly Calendar (تقویم ماهانه)
# ─────────────────────────────────────────────────────────────────────────────


async def show_monthly_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a 30-day emoji calendar."""
    try:
        user_id = update.effective_user.id
        db = _get_db(context)
        db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")

        today = datetime.now().date()
        msg = f"📅 تقویم ۳۰ روز اخیر\n\n"
        msg += f"🟩=کامل  🟨=ناقص  ⬜=خالی  📚=دوره\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        # Build calendar rows (6 rows of 5 days)
        perfect_count = 0
        partial_count = 0
        empty_count = 0

        for row in range(6):
            line = ""
            for col in range(5):
                day_offset = row * 5 + col
                if day_offset >= 30:
                    break
                d = (today - timedelta(days=29 - day_offset)).isoformat()

                # Check status for this day
                habits = db.get_today_habits(user_id, d)
                done = sum(1 for v in habits.values() if v is not None)
                course = db.get_course_today(user_id, d)

                if done == 3:
                    emoji = "🟩"
                    perfect_count += 1
                elif done > 0:
                    emoji = "🟨"
                    partial_count += 1
                else:
                    emoji = "⬜"
                    empty_count += 1

                # Add course indicator
                if course:
                    emoji += "·"
                else:
                    emoji += " "

                line += emoji
            msg += f"  {line}\n"

        msg += f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🟩 کامل: {perfect_count} روز\n"
        msg += f"🟨 ناقص: {partial_count} روز\n"
        msg += f"⬜ خالی: {empty_count} روز\n"

        # Percentage
        active_days = perfect_count + partial_count
        pct = int(active_days / 30 * 100) if 30 > 0 else 0
        msg += f"\n📊 فعال بودن: {pct}% ({active_days}/30 روز)\n"

        if perfect_count >= 25:
            msg += f"\n🏆 فوق‌العاده! ماه درخشان!"
        elif perfect_count >= 20:
            msg += f"\n⭐ عالی! خیلی خوب پیش میری!"
        elif active_days >= 20:
            msg += f"\n💪 خوبه! سعی کن روزای کامل بیشتر بشه!"
        else:
            msg += f"\n🌱 هر روز فرصت جدیدیه. ادامه بده!"

        await update.message.reply_text(msg, reply_markup=main_keyboard())
    except Exception as e:
        logger.error(f"show_monthly_calendar error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ خطا: {e}", reply_markup=main_keyboard())


# ─────────────────────────────────────────────────────────────────────────────
# 📈 XP Prediction (پیش‌بینی)
# ─────────────────────────────────────────────────────────────────────────────


def _predict_level_up(user_id: int, db: Database, gm: Gamification) -> str:
    """Predict when user will reach next level."""
    user = db.get_user(user_id)
    if not user:
        return ""

    current_xp = user["xp"]
    level_info = gm.get_level_info(current_xp)

    if not level_info.get("next_level"):
        return "🏆 تو بالاترین سطحی! افسانه‌ای!"

    xp_to_next = level_info["xp_to_next"]

    # Calculate average daily XP (from last 7 days)
    stats = db.get_weekly_stats(user_id)
    xp_week = stats.get("xp_earned", 0)
    avg_daily = xp_week / 7 if xp_week > 0 else 50  # Default estimate

    if avg_daily > 0:
        days_to_next = int(xp_to_next / avg_daily)
        if days_to_next <= 0:
            return f"پیش‌بینی: امروز لول‌آپ میکنی! ⬆️"
        elif days_to_next <= 7:
            return f"پیش‌بینی: تا {days_to_next} روز دیگه لول {level_info['next_level']['level']} میشی! 🚀"
        else:
            return f"پیش‌بینی: ~{days_to_next} روز تا لول {level_info['next_level']['level']} ({level_info['next_level']['icon']})"
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# 📊 10-Day Auto Analysis (تحلیل خودکار ۱۰ روزه)
# ─────────────────────────────────────────────────────────────────────────────


def generate_auto_analysis(user_id: int, db: Database) -> str:
    """Generate smart 10-day analysis with coaching tips."""
    today = datetime.now().date()
    start = (today - timedelta(days=9)).isoformat()
    end = today.isoformat()

    # Gather data
    total_habits = 0
    per_habit = {"namaz": 0, "sleep": 0, "exercise": 0}
    levels_count = {"small": 0, "special": 0, "emergency": 0}
    course_days = 0
    journal_days = 0

    for i in range(10):
        d = (today - timedelta(days=i)).isoformat()
        habits = db.get_today_habits(user_id, d)
        for key in HABIT_ORDER:
            if habits[key]:
                total_habits += 1
                per_habit[key] += 1
                levels_count[habits[key]["level"]] += 1

        if db.get_course_today(user_id, d):
            course_days += 1
        if db.get_journal(user_id, d):
            journal_days += 1

    total_possible = 30  # 3 habits × 10 days
    pct = int(total_habits / total_possible * 100)

    # Build analysis message
    msg = f"📊 تحلیل خودکار ۱۰ روزه\n\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📈 درصد انجام: {pct}%\n"
    msg += f"✅ عادت‌ها: {total_habits}/{total_possible}\n"
    msg += f"📚 دوره: {course_days}/10 روز\n"
    msg += f"📝 تحلیل: {journal_days}/10 شب\n\n"

    # Per-habit breakdown
    msg += f"📋 عملکرد هر عادت:\n"
    for key in HABIT_ORDER:
        habit = HABITS[key]
        count = per_habit[key]
        bar = "🟩" * count + "⬜" * (10 - count)
        msg += f"  {habit['icon']} {bar} {count}/10\n"

    # Level distribution
    msg += f"\n📊 توزیع سطوح:\n"
    msg += f"  🟢 کوچک: {levels_count['small']} | "
    msg += f"🟡 ویژه: {levels_count['special']} | "
    msg += f"🔴 اضطراری: {levels_count['emergency']}\n"

    # Smart coaching tips
    msg += f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"🤖 کوچ هوشمند:\n\n"

    tips_added = 0

    # Weak habits
    for key in HABIT_ORDER:
        if per_habit[key] <= 4:
            msg += f"• {COACH_TIPS[f'weak_{key}']}\n"
            tips_added += 1
        elif per_habit[key] >= 8:
            msg += f"• {COACH_TIPS[f'strong_{key}']}\n"
            tips_added += 1

    # Level distribution tips
    if levels_count["emergency"] > levels_count["small"] + levels_count["special"]:
        msg += f"• {COACH_TIPS['all_emergency']}\n"
        tips_added += 1

    # Journal tip
    if journal_days < 3:
        msg += f"• {COACH_TIPS['no_journal']}\n"
        tips_added += 1

    # Course tip
    if course_days < 5:
        msg += f"• {COACH_TIPS['no_course']}\n"
        tips_added += 1

    # Consistency
    if pct >= 80:
        msg += f"• {COACH_TIPS['consistent']}\n"
        tips_added += 1

    if tips_added == 0:
        msg += f"• خوب پیش میری! ادامه بده! 💪\n"

    msg += f"\n━━━━━━━━━━━━━━━━━━━━━━━━"
    return msg


async def show_auto_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the 10-day auto analysis."""
    try:
        user_id = update.effective_user.id
        db = _get_db(context)
        db.get_or_create_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")

        msg = generate_auto_analysis(user_id, db)
        await update.message.reply_text(msg, reply_markup=main_keyboard())
    except Exception as e:
        logger.error(f"show_auto_analysis error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ خطا: {e}", reply_markup=main_keyboard())
