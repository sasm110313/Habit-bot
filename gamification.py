"""
🎮 Gamification Module for Habit Bot v3.0
سیستم امتیازدهی، لول، دستاوردها
"""

from datetime import datetime
from config import (
    LEVELS, ACHIEVEMENTS, HABITS, HABIT_ORDER,
    XP_COURSE_WATCHED, XP_PERFECT_DAY, XP_JOURNAL_WRITTEN,
    XP_STREAK_BONUS_7, XP_STREAK_BONUS_14, XP_STREAK_BONUS_30, XP_STREAK_BONUS_40,
)


class Gamification:
    """Handles XP, levels, achievements, and rewards."""

    def __init__(self, db):
        self.db = db

    # ══════════════════════════════════════════════════════════════════════════
    # Level System
    # ══════════════════════════════════════════════════════════════════════════

    def get_level_info(self, xp: int) -> dict:
        """Get current level info based on total XP."""
        current_level = LEVELS[0]
        next_level = LEVELS[1] if len(LEVELS) > 1 else None

        for i, level in enumerate(LEVELS):
            if xp >= level["xp_needed"]:
                current_level = level
                next_level = LEVELS[i + 1] if i + 1 < len(LEVELS) else None
            else:
                break

        # Calculate progress to next level
        if next_level:
            xp_in_level = xp - current_level["xp_needed"]
            xp_for_next = next_level["xp_needed"] - current_level["xp_needed"]
            progress = min(xp_in_level / xp_for_next * 100, 100) if xp_for_next > 0 else 100
        else:
            progress = 100

        return {
            "level": current_level["level"],
            "name": current_level["name"],
            "icon": current_level["icon"],
            "xp": xp,
            "next_level": next_level,
            "progress": round(progress, 1),
            "xp_to_next": (next_level["xp_needed"] - xp) if next_level else 0,
        }

    def check_level_up(self, user_id: int, old_xp: int, new_xp: int):
        """Check if user leveled up. Returns new level info or None."""
        old_level = self.get_level_info(old_xp)
        new_level = self.get_level_info(new_xp)

        if new_level["level"] > old_level["level"]:
            self.db.set_level(user_id, new_level["level"])
            self.db.unlock_achievement(user_id, "level_up")
            return new_level
        return None

    def format_xp_bar(self, xp: int, width: int = 10) -> str:
        """Create a visual XP progress bar."""
        info = self.get_level_info(xp)
        filled = int(info["progress"] / 100 * width)
        bar = "█" * filled + "░" * (width - filled)
        return f"{info['icon']} Lv.{info['level']} [{bar}] {info['progress']:.0f}%"

    # ══════════════════════════════════════════════════════════════════════════
    # XP Calculation
    # ══════════════════════════════════════════════════════════════════════════

    def award_habit_xp(self, user_id: int, habit_key: str, level: str, date: str) -> dict:
        """
        Award XP for completing a habit.
        Returns {"xp_earned": int, "level_up": dict|None, "achievements": list}
        """
        habit = HABITS[habit_key]
        base_xp = habit["levels"][level]["xp"]
        total_xp = base_xp
        achievements = []

        # Get current user XP
        user = self.db.get_user(user_id)
        old_xp = user["xp"] if user else 0

        # Log the XP
        reason = f"عادت {habit['name']} ({habit['levels'][level]['name']})"
        new_xp = self.db.add_xp(user_id, base_xp, reason)

        # Check for perfect day bonus
        done_today = self.db.count_habits_today(user_id, date)
        if done_today >= 3:
            # Award perfect day bonus
            self.db.add_xp(user_id, XP_PERFECT_DAY, "روز کامل! 🏆")
            new_xp += XP_PERFECT_DAY
            total_xp += XP_PERFECT_DAY

            # Update perfect day streak
            streak = self.db.update_streak(user_id, "perfect_day", date)

            # Perfect day achievements
            pd_count = self.db.get_streak(user_id, "perfect_day")["current"]
            if pd_count >= 1 and self.db.unlock_achievement(user_id, "perfect_1"):
                achievements.append(ACHIEVEMENTS["perfect_1"])
            if pd_count >= 7 and self.db.unlock_achievement(user_id, "perfect_7"):
                achievements.append(ACHIEVEMENTS["perfect_7"])
            if pd_count >= 30 and self.db.unlock_achievement(user_id, "perfect_30"):
                achievements.append(ACHIEVEMENTS["perfect_30"])

        # Update habit streak
        streak_info = self.db.update_streak(user_id, habit_key, date)
        streak = streak_info["current"]

        # Streak-based achievements
        streak_achievements = [
            (3, "streak_3"),
            (7, "streak_7"),
            (14, "streak_14"),
            (21, "streak_21"),
            (30, "streak_30"),
            (40, "streak_40"),
            (66, "streak_66"),
        ]
        for threshold, ach_key in streak_achievements:
            if streak >= threshold and self.db.unlock_achievement(user_id, ach_key):
                achievements.append(ACHIEVEMENTS[ach_key])
                # Bonus XP for streak milestones
                ach_xp = ACHIEVEMENTS[ach_key]["xp"]
                if ach_xp > 0:
                    self.db.add_xp(user_id, ach_xp, f"دستاورد: {ACHIEVEMENTS[ach_key]['name']}")
                    new_xp += ach_xp
                    total_xp += ach_xp

        # Streak bonus XP (separate from achievements)
        if streak == 7:
            self.db.add_xp(user_id, XP_STREAK_BONUS_7, "بونوس ۷ روز متوالی")
            total_xp += XP_STREAK_BONUS_7
            new_xp += XP_STREAK_BONUS_7
        elif streak == 14:
            self.db.add_xp(user_id, XP_STREAK_BONUS_14, "بونوس ۱۴ روز متوالی")
            total_xp += XP_STREAK_BONUS_14
            new_xp += XP_STREAK_BONUS_14
        elif streak == 30:
            self.db.add_xp(user_id, XP_STREAK_BONUS_30, "بونوس ۳۰ روز متوالی")
            total_xp += XP_STREAK_BONUS_30
            new_xp += XP_STREAK_BONUS_30
        elif streak == 40:
            self.db.add_xp(user_id, XP_STREAK_BONUS_40, "بونوس یک چهله!")
            total_xp += XP_STREAK_BONUS_40
            new_xp += XP_STREAK_BONUS_40

        # First habit achievement
        if user and user["total_habits_done"] <= 1:
            if self.db.unlock_achievement(user_id, "first_habit"):
                achievements.append(ACHIEVEMENTS["first_habit"])

        # Emergency hero achievement
        if level == "emergency":
            emergency_count = self.db.count_emergency_habits(user_id)
            if emergency_count >= 10 and self.db.unlock_achievement(user_id, "emergency_hero"):
                achievements.append(ACHIEVEMENTS["emergency_hero"])

        # Time-based achievements
        hour = datetime.now().hour
        if hour >= 23 or hour < 5:
            if self.db.unlock_achievement(user_id, "night_owl"):
                achievements.append(ACHIEVEMENTS["night_owl"])
        elif hour < 7:
            if self.db.unlock_achievement(user_id, "early_bird"):
                achievements.append(ACHIEVEMENTS["early_bird"])

        # Check level up
        level_up = self.check_level_up(user_id, old_xp, new_xp)

        return {
            "xp_earned": total_xp,
            "new_xp": new_xp,
            "streak": streak,
            "level_up": level_up,
            "achievements": achievements,
        }

    def award_course_xp(self, user_id: int, date: str) -> dict:
        """Award XP for watching course."""
        user = self.db.get_user(user_id)
        old_xp = user["xp"] if user else 0

        new_xp = self.db.add_xp(user_id, XP_COURSE_WATCHED, "تماشای دوره آموزشی")
        achievements = []

        # Update course streak
        streak_info = self.db.update_streak(user_id, "course", date)
        streak = streak_info["current"]

        # Course achievements
        if streak >= 7 and self.db.unlock_achievement(user_id, "course_7"):
            achievements.append(ACHIEVEMENTS["course_7"])
        if streak >= 30 and self.db.unlock_achievement(user_id, "course_30"):
            achievements.append(ACHIEVEMENTS["course_30"])
        if streak >= 40 and self.db.unlock_achievement(user_id, "course_chelle"):
            achievements.append(ACHIEVEMENTS["course_chelle"])

        # Award achievement XP
        for ach in achievements:
            if ach["xp"] > 0:
                self.db.add_xp(user_id, ach["xp"], f"دستاورد: {ach['name']}")
                new_xp += ach["xp"]

        level_up = self.check_level_up(user_id, old_xp, new_xp)

        return {
            "xp_earned": XP_COURSE_WATCHED,
            "new_xp": new_xp,
            "streak": streak,
            "level_up": level_up,
            "achievements": achievements,
        }

    def award_journal_xp(self, user_id: int) -> dict:
        """Award XP for writing journal."""
        user = self.db.get_user(user_id)
        old_xp = user["xp"] if user else 0

        new_xp = self.db.add_xp(user_id, XP_JOURNAL_WRITTEN, "نوشتن تحلیل شبانه")
        achievements = []

        # First journal achievement
        if user and user["total_journals"] <= 1:
            if self.db.unlock_achievement(user_id, "first_journal"):
                achievements.append(ACHIEVEMENTS["first_journal"])
                self.db.add_xp(user_id, ACHIEVEMENTS["first_journal"]["xp"], "دستاورد: اولین تحلیل")
                new_xp += ACHIEVEMENTS["first_journal"]["xp"]

        level_up = self.check_level_up(user_id, old_xp, new_xp)

        return {
            "xp_earned": XP_JOURNAL_WRITTEN,
            "new_xp": new_xp,
            "level_up": level_up,
            "achievements": achievements,
        }

    def check_comeback(self, user_id: int, date: str) -> bool:
        """Check if user is coming back after absence."""
        last_date = self.db.get_last_activity_date(user_id)
        if not last_date:
            return False

        today = datetime.strptime(date, "%Y-%m-%d").date()
        last = datetime.strptime(last_date, "%Y-%m-%d").date()
        gap = (today - last).days

        if gap >= 3:
            if self.db.unlock_achievement(user_id, "comeback"):
                self.db.add_xp(user_id, ACHIEVEMENTS["comeback"]["xp"], "برگشت بعد از غیبت!")
                return True
        return False

    # ══════════════════════════════════════════════════════════════════════════
    # Display Helpers
    # ══════════════════════════════════════════════════════════════════════════

    def format_achievement_notification(self, achievement: dict) -> str:
        """Format a single achievement unlock notification."""
        return f"🏅 دستاورد جدید!\n{achievement['icon']} {achievement['name']}\n📝 {achievement['desc']}\n✨ +{achievement['xp']} XP"

    def format_level_up_notification(self, level_info: dict) -> str:
        """Format level up notification."""
        return (
            f"⬆️ لول آپ! 🎉\n\n"
            f"{level_info['icon']} سطح {level_info['level']}: {level_info['name']}\n\n"
            f"💪 به پیش! ادامه بده!"
        )

    def format_xp_gain(self, xp_earned: int, reason: str = "") -> str:
        """Format XP gain message."""
        return f"✨ +{xp_earned} XP" + (f" ({reason})" if reason else "")

    def get_rank_title(self, user_id: int) -> str:
        """Get user's display rank."""
        user = self.db.get_user(user_id)
        if not user:
            return "🌱 تازه‌کار"
        info = self.get_level_info(user["xp"])
        return f"{info['icon']} {info['name']} (Lv.{info['level']})"
