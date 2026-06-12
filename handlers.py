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
)
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
        ["📊 آمار", "🏆 دستاوردها"],
        ["📝 تحلیل", "🔥 استریک"],
        ["ℹ️ راهنما"],
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
