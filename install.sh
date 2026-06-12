#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# Habit Bot v2.0 - One-Command Installer / Updater
# Safe: does NOT touch nginx, tailscale, or any other services
# ══════════════════════════════════════════════════════════════════════════════

set -e

echo "🤖 نصب/بروزرسانی ربات عادت‌سازی v2.0..."
echo ""

# ── 1. Check for bot token ────────────────────────────────────────────────────
if [ -z "$1" ]; then
    # Check if already installed (update mode)
    if [ -f /etc/systemd/system/habit-bot.service ]; then
        echo "🔄 حالت بروزرسانی (توکن از سرویس قبلی استفاده میشه)"
        BOT_TOKEN=$(grep -oP 'TELEGRAM_BOT_TOKEN=\K.*' /etc/systemd/system/habit-bot.service 2>/dev/null || echo "")
        if [ -z "$BOT_TOKEN" ]; then
            echo "❌ توکن پیدا نشد! لطفاً توکن رو وارد کن."
            echo "Usage: bash install.sh YOUR_BOT_TOKEN"
            exit 1
        fi
        echo "✅ توکن قبلی پیدا شد."
    else
        echo "❌ لطفاً توکن ربات رو وارد کن!"
        echo ""
        echo "Usage: bash install.sh YOUR_BOT_TOKEN"
        echo ""
        echo "توکن رو از @BotFather در تلگرام بگیر."
        exit 1
    fi
else
    BOT_TOKEN="$1"
fi

BOT_DIR="/opt/habit-bot"

echo "📁 ساخت پوشه‌ها..."
mkdir -p "$BOT_DIR/data"

# ── 2. Install Python venv if needed ─────────────────────────────────────────
echo "🐍 بررسی Python..."
if ! command -v python3 &> /dev/null; then
    echo "  نصب Python3..."
    apt-get update -qq && apt-get install -y -qq python3 python3-venv python3-pip > /dev/null 2>&1
fi

if ! python3 -m venv --help > /dev/null 2>&1; then
    echo "  نصب python3-venv..."
    apt-get update -qq && apt-get install -y -qq python3-venv > /dev/null 2>&1
fi

# ── 3. Create/update virtual environment ─────────────────────────────────────
echo "📦 ساخت/بروزرسانی محیط مجازی..."
if [ ! -d "$BOT_DIR/venv" ]; then
    python3 -m venv "$BOT_DIR/venv"
fi
"$BOT_DIR/venv/bin/pip" install --quiet --upgrade pip
"$BOT_DIR/venv/bin/pip" install --quiet -r requirements.txt

# ── 4. Copy bot file ─────────────────────────────────────────────────────────
echo "📝 کپی فایل ربات..."
cp habit_bot.py "$BOT_DIR/habit_bot.py"

# ── 5. Create systemd service ────────────────────────────────────────────────
echo "⚙️ ساخت/بروزرسانی سرویس..."
cat > /etc/systemd/system/habit-bot.service << EOF
[Unit]
Description=Telegram Habit Tracker Bot v2.0
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/habit-bot
Environment=TELEGRAM_BOT_TOKEN=${BOT_TOKEN}
Environment=HABIT_DB_PATH=/opt/habit-bot/data/habit_bot.db
ExecStart=/opt/habit-bot/venv/bin/python habit_bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# ── 6. Set timezone ──────────────────────────────────────────────────────────
echo "🕐 تنظیم تایم‌زون تهران..."
timedatectl set-timezone Asia/Tehran 2>/dev/null || true

# ── 7. Enable and restart ────────────────────────────────────────────────────
echo "🚀 فعال‌سازی و ریستارت..."
systemctl daemon-reload
systemctl enable habit-bot
systemctl restart habit-bot

# ── 8. Verify ─────────────────────────────────────────────────────────────────
sleep 3
if systemctl is-active --quiet habit-bot; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "✅ ربات v2.0 با موفقیت نصب/بروزرسانی شد! 🎉"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "📱 الان برو تو تلگرام و /start رو بزن!"
    echo ""
    echo "🕌 عادت‌ها: تمرکز در نماز | خواب منظم | ورزش"
    echo "📚 یادآوری دوره: ۸:۰۰ | ۱۲:۳۰ | ۱۷:۰۰ | ۲۰:۳۰ | ۲۲:۳۰"
    echo "⏰ یادآوری عادت: ۷:۳۰ | ۱۳:۰۰ | ۱۸:۳۰ | ۲۱:۰۰"
    echo "🌙 خلاصه شبانه: ۲۲:۴۵"
    echo ""
    echo "🛠 دستورات:"
    echo "   systemctl status habit-bot   - وضعیت"
    echo "   systemctl restart habit-bot  - ریستارت"
    echo "   journalctl -u habit-bot -f   - لاگ"
    echo ""
else
    echo ""
    echo "❌ مشکلی پیش اومد:"
    journalctl -u habit-bot -n 20 --no-pager
    echo ""
fi
