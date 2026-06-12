# 📱 راهنمای نصب مینی اپ تلگرام

## پیش‌نیازها
- ✅ ربات نصب شده و کار می‌کنه
- ✅ دامنه `telegram.acadeo.ir` به سرور وصله
- ✅ nginx نصبه

---

## 🚀 گام‌های نصب (بدون تداخل با بقیه سایت‌ها)

### ۱. آپدیت کد ربات

```bash
cd ~/Habit-bot
git pull
sudo bash install.sh
```

### ۲. کپی فایل‌های مینی اپ

```bash
sudo mkdir -p /opt/habit-bot/webapp
sudo cp webapp/index.html /opt/habit-bot/webapp/
```

### ۳. گرفتن SSL (فقط یکبار)

```bash
sudo certbot certonly --nginx -d telegram.acadeo.ir
```

> اگه certbot نداری: `sudo apt install certbot python3-certbot-nginx`

### ۴. کپی کانفیگ nginx

```bash
sudo cp nginx-telegram.conf /etc/nginx/sites-available/telegram.acadeo.ir
sudo ln -sf /etc/nginx/sites-available/telegram.acadeo.ir /etc/nginx/sites-enabled/
```

### ۵. تست و ریلود nginx

```bash
sudo nginx -t
sudo systemctl reload nginx
```

> ⚠️ اگه `nginx -t` خطا داد، **ریلود نکن** و خطا رو بفرست تا فیکسش کنم.

### ۶. ریستارت ربات (برای فعال شدن API)

```bash
sudo systemctl restart habit-bot
```

### ۷. تست API

```bash
curl https://telegram.acadeo.ir/api/dhikr
```

باید JSON برگرده.

### ۸. تنظیم مینی اپ در BotFather

1. به @BotFather پیام بده
2. `/mybots` → ربات → `Bot Settings` → `Menu Button`
3. URL بذار: `https://telegram.acadeo.ir`
4. Button text بذار: `📱 مینی اپ`

**یا** از طریق دستور:
```
/setmenubutton
```
URL: `https://telegram.acadeo.ir`
Title: `📱 عادت‌ساز`

---

## ✅ تست نهایی

1. ربات رو تو تلگرام باز کن
2. دکمه «📱 عادت‌ساز» کنار فیلد پیام رو بزن
3. مینی اپ باید باز بشه!

---

## 🔒 امنیت

| نکته | وضعیت |
|------|--------|
| HTTPS | ✅ SSL/TLS |
| API محدود | ✅ فقط localhost:8090 (nginx proxy) |
| پورت جدید باز نمیشه | ✅ API روی 127.0.0.1 (داخلی) |
| nginx موجود | ✅ فایل جدا — بقیه سایت‌ها دست‌نخورده |
| tailscale | ✅ بی‌تاثیر |

---

## 🛠 عیب‌یابی

```bash
# وضعیت ربات + API
sudo systemctl status habit-bot

# لاگ ربات
sudo journalctl -u habit-bot -f

# تست API مستقیم
curl http://127.0.0.1:8090/api/dhikr

# تست nginx
sudo nginx -t
```

---

## 📁 ساختار فایل‌ها بعد نصب

```
/opt/habit-bot/
├── bot.py
├── api_server.py         ← API server (جدید)
├── config.py
├── db.py
├── gamification.py
├── handlers.py
├── reminders.py
├── venv/
├── data/
│   └── habit_bot.db
└── webapp/
    └── index.html        ← مینی اپ (جدید)

/etc/nginx/sites-available/
└── telegram.acadeo.ir    ← nginx config (جدید)
```
