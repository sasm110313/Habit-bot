# 🤖 ربات تلگرام عادت‌سازی | Habit Tracker Bot

ربات تلگرام برای مدیریت عادت‌ها، یادآوری دوره آموزشی، و پیگیری پیشرفت روزانه.

---

## ✨ امکانات

- ➕ افزودن و حذف عادت‌ها
- ✅ تیک زدن روزانه با دکمه اینلاین
- ⏰ یادآوری خودکار چند بار در روز (پیش‌فرض: ۷، ۱۲، ۱۸، ۲۱)
- 📚 پیگیری تماشای دوره آموزشی عادت‌سازی
- 🔥 محاسبه استریک (روزهای متوالی)
- 📊 آمار هفتگی و ماهانه
- 🌙 خلاصه شبانه خودکار (ساعت ۲۲)
- ⏸ توقف/ادامه یادآوری‌ها

---

## 🚀 نصب روی سرور لینوکسی (یک دستور!)

### پیش‌نیاز
توکن ربات از [@BotFather](https://t.me/BotFather) بگیر.

### اجرا

```bash
# 1. کلون ریپو
git clone https://github.com/sasm110313/Habit-bot.git
cd Habit-bot

# 2. نصب و اجرا (با توکن خودت)
sudo bash install.sh "YOUR_BOT_TOKEN_HERE"
```

تمام! ✅ ربات اجرا شد. برو تو تلگرام و `/start` بزن.

---

## 📱 دستورات ربات

| دستور | توضیح |
|--------|--------|
| `/start` | شروع |
| `/habits` | لیست عادت‌ها + تیک |
| `/add` | عادت جدید |
| `/delete` | حذف عادت |
| `/stats` | آمار هفتگی |
| `/monthly` | آمار ماهانه |
| `/course` | دوره آموزشی |
| `/reminders` | یادآوری‌ها |
| `/addreminder HH:MM` | افزودن یادآوری |
| `/removereminder` | حذف یادآوری |
| `/pause` | توقف یادآوری |
| `/resume` | ادامه یادآوری |
| `/help` | راهنما |

---

## 🛠 مدیریت

```bash
# وضعیت
sudo systemctl status habit-bot

# ریستارت
sudo systemctl restart habit-bot

# لاگ
sudo journalctl -u habit-bot -f

# توقف
sudo systemctl stop habit-bot
```

---

## 🔒 امنیت

- هیچ پورتی باز نمی‌کنه (polling)
- تداخلی با nginx/tailscale/سایر سرویس‌ها نداره
- محیط مجازی جداگانه Python
- دیتابیس SQLite در `/opt/habit-bot/data/`

---

## 📝 ساختار

```
Habit-bot/
├── habit_bot.py       ← کد اصلی ربات
├── requirements.txt   ← وابستگی‌ها
├── install.sh         ← اسکریپت نصب خودکار
└── README.md          ← این فایل
```
