#!/usr/bin/env python3
"""
🎯 Habit Tracker Bot v3.0 — Main Entry Point
ربات پیشرفته عادت‌سازی

Features:
- ۳ عادت ثابت با ۳ سطح (لقمه کوچک/ویژه/اضطراری)
- سیستم XP + لول + دستاوردها
- ۹ چهله دوره آموزشی
- یادآوری هوشمند (فقط تا وقتی انجام نشده)
- تحلیل/ژورنال شبانه
- آیه قرآن صبحگاهی
- استریک با رکوردشکنی
- آمار هفتگی و کلی
"""

import sys
import os
import logging
from datetime import time

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from config import (
    BOT_TOKEN,
    HABITS,
    MORNING_MOTIVATION_TIME,
    COURSE_REMINDER_TIMES,
    HABIT_REMINDER_TIMES,
    JOURNAL_REMINDER_TIME,
    SUMMARY_TIME,
    ANALYSIS_INTERVAL_DAYS,
)
from db import Database
from gamification import Gamification
from handlers import (
    cmd_start,
    cmd_help,
    cmd_pause,
    cmd_resume,
    cmd_setsession,
    cmd_mystats,
    cmd_journal,
    show_today,
    show_course,
    show_stats,
    show_achievements,
    show_streaks,
    show_journal,
    show_daily_challenge,
    show_journey_map,
    show_monthly_calendar,
    show_auto_analysis,
    show_spin_wheel,
    show_shop,
    show_dhikr,
    show_journal_archive,
    pin_status,
    callback_handler,
    handle_text,
)
from reminders import (
    job_morning_motivation,
    job_course_reminder,
    job_habit_reminder,
    job_journal_reminder,
    job_daily_summary,
    job_10day_analysis,
)

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main():
    if not BOT_TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN not set!")
        print("   export TELEGRAM_BOT_TOKEN='your-token'")
        sys.exit(1)

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🎯 Habit Tracker Bot v3.0")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Initialize database and gamification
    db = Database()
    gm = Gamification(db)

    print(f"📂 Database: {db.db_path}")
    print(f"🕌 Habits: نماز | خواب | ورزش")
    print(f"🎮 Gamification: 10 levels, {len(HABITS)} habits")

    # Build application
    app = Application.builder().token(BOT_TOKEN).build()

    # Store shared instances in bot_data
    app.bot_data["db"] = db
    app.bot_data["gamification"] = gm

    # ── Command Handlers ─────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("habits", show_today))
    app.add_handler(CommandHandler("today", show_today))
    app.add_handler(CommandHandler("course", show_course))
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(CommandHandler("mystats", cmd_mystats))
    app.add_handler(CommandHandler("achievements", show_achievements))
    app.add_handler(CommandHandler("streaks", show_streaks))
    app.add_handler(CommandHandler("journal", cmd_journal))
    app.add_handler(CommandHandler("setsession", cmd_setsession))
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("resume", cmd_resume))
    app.add_handler(CommandHandler("analysis", show_auto_analysis))
    app.add_handler(CommandHandler("challenge", show_daily_challenge))
    app.add_handler(CommandHandler("journey", show_journey_map))
    app.add_handler(CommandHandler("calendar", show_monthly_calendar))
    app.add_handler(CommandHandler("spin", show_spin_wheel))
    app.add_handler(CommandHandler("shop", show_shop))
    app.add_handler(CommandHandler("dhikr", show_dhikr))
    app.add_handler(CommandHandler("archive", show_journal_archive))
    app.add_handler(CommandHandler("pin", pin_status))

    # ── Callback Query Handler ───────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(callback_handler))

    # ── Text Message Handler ─────────────────────────────────────────────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # ── Global Error Handler ─────────────────────────────────────────────
    async def error_handler(update, context):
        """Log errors and notify user."""
        logger.error(f"Exception: {context.error}", exc_info=context.error)
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    f"❌ خطای داخلی: {context.error}\n\n/start رو بزن."
                )
            except Exception:
                pass

    app.add_error_handler(error_handler)

    # ── Scheduled Jobs ───────────────────────────────────────────────────
    job_queue = app.job_queue

    # Morning motivation with Quran verse
    h, m = MORNING_MOTIVATION_TIME
    job_queue.run_daily(job_morning_motivation, time=time(hour=h, minute=m), name="morning")
    print(f"  🌅 Morning motivation: {h:02d}:{m:02d}")

    # Course reminders (multiple per day)
    for h, m in COURSE_REMINDER_TIMES:
        job_queue.run_daily(
            job_course_reminder,
            time=time(hour=h, minute=m),
            name=f"course_{h:02d}{m:02d}",
        )
    print(f"  📚 Course reminders: {', '.join(f'{h:02d}:{m:02d}' for h, m in COURSE_REMINDER_TIMES)}")

    # Habit reminders (multiple per day)
    for h, m in HABIT_REMINDER_TIMES:
        job_queue.run_daily(
            job_habit_reminder,
            time=time(hour=h, minute=m),
            name=f"habit_{h:02d}{m:02d}",
        )
    print(f"  💪 Habit reminders: {', '.join(f'{h:02d}:{m:02d}' for h, m in HABIT_REMINDER_TIMES)}")

    # Journal reminder
    h, m = JOURNAL_REMINDER_TIME
    job_queue.run_daily(job_journal_reminder, time=time(hour=h, minute=m), name="journal")
    print(f"  📝 Journal reminder: {h:02d}:{m:02d}")

    # Journal second reminder (more urgent)
    from config import JOURNAL_REMINDER_TIME_2
    h2, m2 = JOURNAL_REMINDER_TIME_2
    job_queue.run_daily(job_journal_reminder, time=time(hour=h2, minute=m2), name="journal_2")
    print(f"  📝 Journal reminder 2: {h2:02d}:{m2:02d}")

    # Daily summary
    h, m = SUMMARY_TIME
    job_queue.run_daily(job_daily_summary, time=time(hour=h, minute=m), name="summary")
    print(f"  🌙 Daily summary: {h:02d}:{m:02d}")

    # 10-day auto analysis (runs daily at 12:00, triggers every 10 days)
    job_queue.run_daily(job_10day_analysis, time=time(hour=12, minute=0), name="analysis_10day")
    print(f"  📊 Auto analysis: every {ANALYSIS_INTERVAL_DAYS} days")

    # ── Start API Server (for Mini App) ────────────────────────────────
    import asyncio
    import threading
    from aiohttp import web
    from api_server import create_api_app

    api_app = create_api_app(db, gm)
    API_PORT = int(os.environ.get("API_PORT", "8090"))

    async def start_api():
        runner = web.AppRunner(api_app)
        await runner.setup()
        site = web.TCPSite(runner, '127.0.0.1', API_PORT)
        await site.start()
        logger.info(f"🌐 API server running on 127.0.0.1:{API_PORT}")

    # Run API in background
    loop = asyncio.new_event_loop()

    def run_api_loop():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_api())
        loop.run_forever()

    api_thread = threading.Thread(target=run_api_loop, daemon=True)
    api_thread.start()
    print(f"  🌐 API server: 127.0.0.1:{API_PORT}")

    # ── Start Bot ────────────────────────────────────────────────────────
    print("")
    print("✅ Bot + API running! Press Ctrl+C to stop.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    app.run_polling(allowed_updates=["message", "callback_query"], drop_pending_updates=True)


if __name__ == "__main__":
    main()
