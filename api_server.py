"""
🌐 API Server for Telegram Mini App
Serves REST endpoints for the webapp frontend
Runs alongside the bot on port 8090 (internal only, nginx proxies)
"""

import logging
import json
from datetime import datetime, timedelta
from aiohttp import web

from config import (
    HABITS, HABIT_ORDER, ACHIEVEMENTS, LEVELS,
    DAILY_CHALLENGES, JOURNEY_MILESTONES, TOTAL_CHELLE, DAYS_PER_CHELLE,
    DAILY_DHIKR, DAILY_HADITHS, DUAS_BEFORE_HABIT,
    SHOP_ITEMS, SPIN_WHEEL_PRIZES, XP_WEEKLY_PERFECT, XP_WEEKLY_GOOD, XP_WEEKLY_OK,
    XP_COURSE_WATCHED, XP_JOURNAL_WRITTEN, MOOD_TAGS,
    JOURNAL_START_HOUR, JOURNAL_END_HOUR, JOURNAL_NOT_ALLOWED_MSG,
)
from db import Database
from gamification import Gamification

logger = logging.getLogger(__name__)


def today_str() -> str:
    return datetime.now().date().isoformat()


def _get_today_challenge() -> dict:
    day_of_year = datetime.now().timetuple().tm_yday
    idx = day_of_year % len(DAILY_CHALLENGES)
    return DAILY_CHALLENGES[idx]


def _check_challenge_done(user_id: int, db: Database, challenge: dict, date: str) -> bool:
    """Simplified challenge check for API."""
    habits = db.get_today_habits(user_id, date)
    condition = challenge.get("condition", "")

    if condition == "all_small":
        return all(habits[k] and habits[k]["level"] == "small" for k in HABIT_ORDER)
    elif condition == "any_done":
        return any(v is not None for v in habits.values())
    elif condition == "all_done":
        return all(v is not None for v in habits.values())
    elif condition == "namaz_small":
        return habits.get("namaz") is not None and habits["namaz"]["level"] == "small"
    elif condition == "exercise_small":
        return habits.get("exercise") is not None and habits["exercise"]["level"] == "small"
    elif condition == "sleep_small":
        return habits.get("sleep") is not None and habits["sleep"]["level"] == "small"
    elif condition == "course_first":
        return db.get_course_today(user_id, date) is not None
    elif condition == "perfect_journal":
        done = sum(1 for v in habits.values() if v is not None)
        return done >= 3 and db.get_journal(user_id, date) is not None
    elif condition == "full_day":
        done = sum(1 for v in habits.values() if v is not None)
        return done >= 3 and db.get_course_today(user_id, date) is not None and db.get_journal(user_id, date) is not None
    elif condition == "has_small":
        return any(habits[k] and habits[k]["level"] == "small" for k in HABIT_ORDER)
    elif condition == "no_emergency":
        done = sum(1 for v in habits.values() if v is not None)
        if done == 0:
            return False
        return all(habits[k]["level"] != "emergency" for k in HABIT_ORDER if habits[k] is not None)
    elif condition == "all_special_plus":
        return all(habits[k] and habits[k]["level"] in ("small", "special") for k in HABIT_ORDER)
    return any(v is not None for v in habits.values())


def create_api_app(db: Database, gm: Gamification) -> web.Application:
    """Create the aiohttp web application with all API routes."""

    app = web.Application()

    # ── CORS middleware ──────────────────────────────────────────────────
    @web.middleware
    async def cors_middleware(request, handler):
        if request.method == 'OPTIONS':
            response = web.Response(status=200)
        else:
            response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    app.middlewares.append(cors_middleware)

    # ══════════════════════════════════════════════════════════════════════
    # GET /api/today - Today's full status
    # ══════════════════════════════════════════════════════════════════════

    async def get_today(request):
        user_id = int(request.query.get('user_id', 0))
        if not user_id:
            return web.json_response({"error": "user_id required"}, status=400)

        db.get_or_create_user(user_id)
        date = today_str()
        user = db.get_user(user_id)
        habits = db.get_today_habits(user_id, date)
        streaks = db.get_all_streaks(user_id)
        course = db.get_course_today(user_id, date)
        challenge = _get_today_challenge()
        challenge_done = _check_challenge_done(user_id, db, challenge, date)
        level_info = gm.get_level_info(user["xp"])

        return web.json_response({
            "habits": {k: (dict(v) if v else None) for k, v in habits.items()},
            "streaks": streaks,
            "course": dict(course) if course else None,
            "course_session": user["course_session"],
            "course_chelle": user["course_chelle"],
            "xp": user["xp"],
            "level": user["level"],
            "level_info": {
                "level": level_info["level"],
                "name": level_info["name"],
                "icon": level_info["icon"],
                "progress": level_info["progress"],
                "xp_to_next": level_info["xp_to_next"],
                "next_level": level_info["next_level"],
            },
            "challenge": {
                "id": challenge["id"],
                "text": challenge["text"],
                "xp": challenge["xp"],
                "condition": challenge["condition"],
            },
            "challenge_done": challenge_done,
        })

    # ══════════════════════════════════════════════════════════════════════
    # POST /api/habit - Log a habit
    # ══════════════════════════════════════════════════════════════════════

    async def post_habit(request):
        data = await request.json()
        user_id = int(data.get('user_id', 0))
        habit_key = data.get('habit_key', '')
        level = data.get('level', '')

        if not user_id or habit_key not in HABIT_ORDER or level not in ('small', 'special', 'emergency'):
            return web.json_response({"error": "invalid params"}, status=400)

        db.get_or_create_user(user_id)
        date = today_str()
        xp = HABITS[habit_key]["levels"][level]["xp"]

        result = db.log_habit(user_id, habit_key, date, level, xp)

        if result["action"] == "removed":
            return web.json_response({"action": "removed", "xp_earned": 0})

        reward = gm.award_habit_xp(user_id, habit_key, level, date)
        return web.json_response({
            "action": result["action"],
            "xp_earned": reward["xp_earned"],
            "streak": reward["streak"],
            "achievements": [a["name"] for a in reward.get("achievements", [])],
            "level_up": reward["level_up"]["name"] if reward.get("level_up") else None,
        })

    # ══════════════════════════════════════════════════════════════════════
    # POST /api/course - Log course watched
    # ══════════════════════════════════════════════════════════════════════

    async def post_course(request):
        data = await request.json()
        user_id = int(data.get('user_id', 0))
        if not user_id:
            return web.json_response({"error": "user_id required"}, status=400)

        db.get_or_create_user(user_id)
        date = today_str()
        user = db.get_user(user_id)
        session = user["course_session"]

        is_new = db.log_course(user_id, date, session, XP_COURSE_WATCHED)

        if is_new:
            reward = gm.award_course_xp(user_id, date)
            return web.json_response({
                "logged": True,
                "xp_earned": reward["xp_earned"],
                "streak": reward["streak"],
                "next_session": session + 1,
            })
        else:
            return web.json_response({"logged": False, "xp_earned": 0})

    # ══════════════════════════════════════════════════════════════════════
    # POST /api/journal - Save journal
    # ══════════════════════════════════════════════════════════════════════

    async def post_journal(request):
        data = await request.json()
        user_id = int(data.get('user_id', 0))
        content = data.get('content', '').strip()
        mood = int(data.get('mood', 0))

        if not user_id or not content:
            return web.json_response({"error": "user_id and content required"}, status=400)

        # Check time restriction: journal only allowed between 20:00 and 04:00
        current_hour = datetime.now().hour
        if JOURNAL_END_HOUR <= current_hour < JOURNAL_START_HOUR:
            return web.json_response({
                "error": "time_restricted",
                "message": JOURNAL_NOT_ALLOWED_MSG,
                "allowed_start": JOURNAL_START_HOUR,
                "allowed_end": JOURNAL_END_HOUR,
            }, status=403)

        db.get_or_create_user(user_id)
        date = today_str()
        is_new = db.save_journal(user_id, date, content, mood=mood, xp=XP_JOURNAL_WRITTEN)

        if is_new:
            reward = gm.award_journal_xp(user_id)
            return web.json_response({
                "saved": True,
                "is_new": True,
                "xp_earned": reward["xp_earned"],
            })
        else:
            return web.json_response({"saved": True, "is_new": False, "xp_earned": 0})

    # ══════════════════════════════════════════════════════════════════════
    # GET /api/stats - Weekly stats + calendar
    # ══════════════════════════════════════════════════════════════════════

    async def get_stats(request):
        user_id = int(request.query.get('user_id', 0))
        if not user_id:
            return web.json_response({"error": "user_id required"}, status=400)

        db.get_or_create_user(user_id)
        stats = db.get_weekly_stats(user_id)
        streaks = db.get_all_streaks(user_id)

        # Build calendar (30 days)
        today = datetime.now().date()
        calendar = []
        for i in range(30):
            d = (today - timedelta(days=29 - i))
            d_str = d.isoformat()
            habits = db.get_today_habits(user_id, d_str)
            done = sum(1 for v in habits.values() if v is not None)
            calendar.append({
                "date": d_str,
                "done": done,
                "is_today": d == today,
            })

        # Daily stats for chart
        daily = []
        week_ago = today - timedelta(days=6)
        for i in range(7):
            d = (week_ago + timedelta(days=i)).isoformat()
            habits = db.get_today_habits(user_id, d)
            done = sum(1 for v in habits.values() if v is not None)
            daily.append({"date": d, "done": done})

        return web.json_response({
            "percentage": stats["percentage"],
            "perfect_days": stats["perfect_days"],
            "course_days": stats["course_days"],
            "xp_earned": stats["xp_earned"],
            "streaks": streaks,
            "calendar": calendar,
            "daily": daily,
        })

    # ══════════════════════════════════════════════════════════════════════
    # GET /api/achievements
    # ══════════════════════════════════════════════════════════════════════

    async def get_achievements(request):
        user_id = int(request.query.get('user_id', 0))
        if not user_id:
            return web.json_response({"error": "user_id required"}, status=400)

        db.get_or_create_user(user_id)
        achs = db.get_achievements(user_id)
        unlocked = [a["achievement_key"] for a in achs]

        return web.json_response({"unlocked": unlocked, "total": len(ACHIEVEMENTS)})

    # ══════════════════════════════════════════════════════════════════════
    # GET /api/journey
    # ══════════════════════════════════════════════════════════════════════

    async def get_journey(request):
        user_id = int(request.query.get('user_id', 0))
        if not user_id:
            return web.json_response({"error": "user_id required"}, status=400)

        db.get_or_create_user(user_id)
        user = db.get_user(user_id)
        session = user["course_session"]
        chelle = user["course_chelle"]
        progress_in = ((session - 1) % DAYS_PER_CHELLE) + 1
        progress_pct = int(progress_in / DAYS_PER_CHELLE * 100)

        return web.json_response({
            "current_chelle": chelle,
            "session": session,
            "progress_in_chelle": progress_in,
            "progress_pct": progress_pct,
            "total_chelle": TOTAL_CHELLE,
        })

    # ══════════════════════════════════════════════════════════════════════
    # GET /api/shop
    # ══════════════════════════════════════════════════════════════════════

    async def get_shop(request):
        user_id = int(request.query.get('user_id', 0))
        if not user_id:
            return web.json_response({"error": "user_id required"}, status=400)

        db.get_or_create_user(user_id)
        user = db.get_user(user_id)

        items = []
        for item in SHOP_ITEMS:
            items.append({
                "id": item["id"],
                "name": item["name"],
                "cost": item["cost"],
                "type": item["type"],
            })

        return web.json_response({"items": items, "xp": user["xp"]})

    # ══════════════════════════════════════════════════════════════════════
    # POST /api/buy
    # ══════════════════════════════════════════════════════════════════════

    async def post_buy(request):
        data = await request.json()
        user_id = int(data.get('user_id', 0))
        item_id = data.get('item_id', '')

        if not user_id or not item_id:
            return web.json_response({"error": "invalid"}, status=400)

        db.get_or_create_user(user_id)
        user = db.get_user(user_id)
        item = next((i for i in SHOP_ITEMS if i["id"] == item_id), None)

        if not item:
            return web.json_response({"success": False, "error": "item not found"})
        if user["xp"] < item["cost"]:
            return web.json_response({"success": False, "error": "not enough XP"})

        db.add_xp(user_id, -item["cost"], f"خرید: {item['name']}")
        db.add_purchase(user_id, item["id"])
        return web.json_response({"success": True, "new_xp": user["xp"] - item["cost"]})

    # ══════════════════════════════════════════════════════════════════════
    # POST /api/spin
    # ══════════════════════════════════════════════════════════════════════

    async def post_spin(request):
        import random
        data = await request.json()
        user_id = int(data.get('user_id', 0))
        if not user_id:
            return web.json_response({"error": "user_id required"}, status=400)

        db.get_or_create_user(user_id)
        stats = db.get_weekly_stats(user_id)
        if stats["perfect_days"] < 7:
            return web.json_response({"success": False, "error": "need 7 perfect days"})

        weights = [p["weight"] for p in SPIN_WHEEL_PRIZES]
        prize = random.choices(SPIN_WHEEL_PRIZES, weights=weights, k=1)[0]
        total_xp = prize["xp"] + XP_WEEKLY_PERFECT
        db.add_xp(user_id, total_xp, f"چرخ: {prize['name']}")

        return web.json_response({
            "success": True,
            "prize": prize["name"],
            "prize_icon": prize["icon"],
            "prize_xp": prize["xp"],
            "bonus_xp": XP_WEEKLY_PERFECT,
            "total_xp": total_xp,
        })

    # ══════════════════════════════════════════════════════════════════════
    # GET /api/dhikr
    # ══════════════════════════════════════════════════════════════════════

    async def get_dhikr(request):
        day_of_year = datetime.now().timetuple().tm_yday
        dhikr = DAILY_DHIKR[day_of_year % len(DAILY_DHIKR)]
        hadith = DAILY_HADITHS[day_of_year % len(DAILY_HADITHS)]

        return web.json_response({
            "text": dhikr["text"],
            "meaning": dhikr["meaning"],
            "count": dhikr["count"],
            "hadith": hadith,
        })

    # ══════════════════════════════════════════════════════════════════════
    # Register routes
    # ══════════════════════════════════════════════════════════════════════

    app.router.add_get('/api/today', get_today)
    app.router.add_post('/api/habit', post_habit)
    app.router.add_post('/api/course', post_course)
    app.router.add_post('/api/journal', post_journal)
    app.router.add_get('/api/stats', get_stats)
    app.router.add_get('/api/achievements', get_achievements)
    app.router.add_get('/api/journey', get_journey)
    app.router.add_get('/api/shop', get_shop)
    app.router.add_post('/api/buy', post_buy)
    app.router.add_post('/api/spin', post_spin)
    app.router.add_get('/api/dhikr', get_dhikr)

    return app
