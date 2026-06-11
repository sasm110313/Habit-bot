#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# Habit Bot - One-Command Installer
# Safe: does NOT touch nginx, tailscale, or any other services
# ══════════════════════════════════════════════════════════════════════════════

set -e

echo "🤖 نصب ربات عادت‌سازی تلگرام..."
echo ""

# ── 1. Check for bot token ────────────────────────────────────────────────────
if [ -z "$1" ]; then
    echo "❌ لطفاً توکن ربات رو وارد کن!"
    echo ""
    echo "Usage: bash install.sh YOUR_BOT_TOKEN"
    echo ""
    echo "توکن رو از @BotFather در تلگرام بگیر."
    exit 1
fi

BOT_TOKEN="$1"
BOT_DIR="/opt/habit-bot"

echo "📁 ساخت پوشه‌ها..."
mkdir -p "$BOT_DIR/data"

# ── 2. Install Python venv if needed ─────────────────────────────────────────
echo "🐍 بررسی Python..."
if ! command -v python3 &> /dev/null; then
    echo "  نصب Python3..."
    apt-get update -qq && apt-get install -y -qq python3 python3-venv python3-pip > /dev/null 2>&1
fi

# Ensure python3-venv is available
if ! python3 -m venv --help > /dev/null 2>&1; then
    echo "  نصب python3-venv..."
    apt-get update -qq && apt-get install -y -qq python3-venv > /dev/null 2>&1
fi

# ── 3. Create virtual environment ────────────────────────────────────────────
echo "📦 ساخت محیط مجازی..."
python3 -m venv "$BOT_DIR/venv"
"$BOT_DIR/venv/bin/pip" install --quiet --upgrade pip
"$BOT_DIR/venv/bin/pip" install --quiet -r requirements.txt

# ── 4. Copy bot file ─────────────────────────────────────────────────────────
echo "📝 کپی فایل ربات..."
cp habit_bot.py "$BOT_DIR/habit_bot.py"

# ── 5. Create systemd service ────────────────────────────────────────────────
echo "⚙️ ساخت سرویس systemd..."
cat > /etc/systemd/system/habit-bot.service << EOF
[Unit]
Description=Telegram Habit Tracker Bot
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

# ── 7. Enable and start ──────────────────────────────────────────────────────
echo "🚀 فعال‌سازی و اجرا..."
systemctl daemon-reload
systemctl enable habit-bot
systemctl restart habit-bot

# ── 8. Verify ─────────────────────────────────────────────────────────────────
sleep 3
if systemctl is-active --quiet habit-bot; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "✅ ربات با موفقیت نصب و اجرا شد! 🎉"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "📱 الان برو تو تلگرام و /start رو بزن!"
    echo ""
    echo "🛠 دستورات مفید:"
    echo "   systemctl status habit-bot   - وضعیت"
    echo "   systemctl restart habit-bot  - ریستارت"
    echo "   journalctl -u habit-bot -f   - لاگ‌ها"
    echo ""
else
    echo ""
    echo "❌ مشکلی پیش اومد. لاگ رو ببین:"
    journalctl -u habit-bot -n 20 --no-pager
    echo ""
fi
