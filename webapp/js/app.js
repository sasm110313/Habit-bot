/* ═══════════════════════════════════════════════════════════════════
   App — Core application logic, state, navigation, utilities
   ═══════════════════════════════════════════════════════════════════ */

// ═══════════════════ Telegram WebApp Init ═══════════════════

const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();
tg.enableClosingConfirmation();
tg.setHeaderColor('#0A0B0D');
tg.setBackgroundColor('#050507');

// ═══════════════════ App State ═══════════════════

const App = {
    user: tg.initDataUnsafe?.user || null,
    userId: tg.initDataUnsafe?.user?.id || 0,
    currentPage: 'today',
    data: {
        habits: {},
        course: null,
        challenge: null,
        xp: 0,
        level: 1,
        mood: 0,
        streaks: {},
    },
};

// ═══════════════════ Haptic Feedback ═══════════════════

const Haptic = {
    light() {
        if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
    },
    medium() {
        if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
    },
    heavy() {
        if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('heavy');
    },
    selection() {
        if (tg.HapticFeedback) tg.HapticFeedback.selectionChanged();
    },
    success() {
        if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
    },
    error() {
        if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
    },
};

// ═══════════════════ Toast Notifications ═══════════════════

function showToast(msg, duration = 2500) {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.classList.add('show');
    clearTimeout(el._timer);
    el._timer = setTimeout(() => el.classList.remove('show'), duration);
}

// ═══════════════════ Page Navigation ═══════════════════

function switchPage(page, el) {
    if (page === App.currentPage) return;

    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-item').forEach(t => t.classList.remove('active'));

    const pageEl = document.getElementById(`page-${page}`);
    if (pageEl) {
        pageEl.classList.add('active');
    }

    if (el) {
        el.classList.add('active');
    }

    App.currentPage = page;
    Haptic.selection();

    // Load page data
    switch (page) {
        case 'today': loadToday(); break;
        case 'stats': loadStats(); break;
        case 'journey': loadJourney(); break;
        case 'achievements': loadAchievements(); break;
        case 'more': loadMore(); break;
    }
}

// ═══════════════════ Date Helpers ═══════════════════

function getPersianDate() {
    const now = new Date();
    return now.toLocaleDateString('fa-IR', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
    });
}

// ═══════════════════ Today Page ═══════════════════

async function loadToday() {
    const data = await apiGet('/today');
    if (!data) return;

    App.data = { ...App.data, ...data };
    renderHeroCard(data);
    renderHabits(data);
    renderCourse(data);
    renderChallenge(data);
}

function renderHeroCard(data) {
    const li = data.level_info || {};
    document.getElementById('heroXP').textContent = data.xp || 0;
    document.getElementById('heroLevelName').textContent = li.name || 'تازه‌کار';
    document.getElementById('heroLevelSub').textContent = `سطح ${li.level || 1}`;
    document.getElementById('heroProgressFill').style.width = `${li.progress || 0}%`;
    document.getElementById('heroProgressCurrent').textContent = `${data.xp || 0} XP`;

    if (li.next_level) {
        document.getElementById('heroProgressNext').textContent = `${li.next_level.xp_needed} XP`;
    } else {
        document.getElementById('heroProgressNext').textContent = 'MAX';
    }
}

function renderHabits(data) {
    ['namaz', 'sleep', 'exercise'].forEach(key => {
        const habit = data.habits[key];
        const checkEl = document.getElementById(`check-${key}`);
        const levelsEl = document.getElementById(`levels-${key}`);

        if (habit) {
            checkEl.classList.add('visible');
            levelsEl.querySelectorAll('.level-btn').forEach(btn => {
                btn.classList.toggle('selected', btn.dataset.level === habit.level);
            });
        } else {
            checkEl.classList.remove('visible');
            levelsEl.querySelectorAll('.level-btn').forEach(btn => {
                btn.classList.remove('selected');
            });
        }

        // Streak
        const streak = data.streaks[key]?.current || 0;
        const streakEl = document.getElementById(`streak-${key}`);
        if (streak > 0) {
            streakEl.innerHTML = `<svg viewBox="0 0 24 24" fill="#F97316" stroke="none" style="width:14px;height:14px"><path d="M12 2c.5 3.5-1.5 6-1.5 6s2.5.5 3.5 3c.7 1.7.3 3.5-.5 5 2.5-1 4-3.5 4-6.5 0-4.5-3.5-7-5.5-7.5z"/></svg> ${streak} روز`;
        } else {
            streakEl.textContent = '';
        }
    });
}

function renderCourse(data) {
    const btn = document.getElementById('courseBtn');
    if (data.course) {
        btn.textContent = 'انجام شد';
        btn.classList.add('done');
    } else {
        btn.textContent = 'ثبت';
        btn.classList.remove('done');
    }
    document.getElementById('courseSession').textContent =
        `جلسه ${data.course_session} | چهله ${data.course_chelle}`;
}

function renderChallenge(data) {
    if (!data.challenge) return;
    document.getElementById('challengeText').textContent = data.challenge.text;
    document.getElementById('challengeReward').textContent = `+${data.challenge.xp} XP`;

    const statusEl = document.getElementById('challengeStatus');
    if (data.challenge_done) {
        statusEl.textContent = 'انجام شد';
        statusEl.classList.add('done');
    } else {
        statusEl.textContent = 'در انتظار';
        statusEl.classList.remove('done');
    }
}

// ═══════════════════ Habit Actions ═══════════════════

async function logHabit(key, level) {
    Haptic.medium();
    const data = await apiPost('/habit', { habit_key: key, level });
    if (data) {
        if (data.action === 'removed') {
            showToast('↩️ لغو شد');
        } else {
            showToast(`+${data.xp_earned} XP`);
            Haptic.success();
        }
        loadToday();
    }
}

async function logCourse() {
    Haptic.medium();
    const data = await apiPost('/course');
    if (data) {
        showToast(data.logged ? `+${data.xp_earned} XP` : '↩️ لغو شد');
        if (data.logged) Haptic.success();
        loadToday();
    }
}

// ═══════════════════ Journal Actions ═══════════════════

function selectMood(score) {
    App.data.mood = score;
    document.querySelectorAll('.mood-btn').forEach(btn => {
        btn.classList.toggle('selected', btn.dataset.mood == score);
    });
    Haptic.selection();
}

async function saveJournal() {
    const content = document.getElementById('journalText').value.trim();
    if (!content) {
        showToast('یه چیزی بنویس!');
        Haptic.error();
        return;
    }

    Haptic.medium();
    const res = await apiPost('/journal', { content, mood: App.data.mood });

    // Check for time restriction error
    if (res && res.error === 'time_restricted') {
        showToast('🌙 تحلیل فقط بین ۲۰:۰۰ تا ۰۴:۰۰ مجازه!', 4000);
        Haptic.error();
        return;
    }

    if (res && !res.error) {
        showToast(`+${res.xp_earned} XP — ثبت شد`);
        Haptic.success();
        document.getElementById('journalText').value = '';
        document.querySelectorAll('.mood-btn').forEach(btn => btn.classList.remove('selected'));
        App.data.mood = 0;
    }
}

// ═══════════════════ Shop Actions ═══════════════════

async function buyItem(id) {
    Haptic.heavy();

    // Confirm purchase
    if (!confirm('مطمئنی میخوای بخری؟')) return;

    const data = await apiPost('/buy', { item_id: id });
    if (data?.success) {
        showToast(`✅ ${data.item_name || 'خرید موفق!'}`);
        Haptic.success();
        loadMore();
        loadToday();
    } else if (data?.error === 'not_enough_xp') {
        showToast(data.message || 'XP کافی نیست');
        Haptic.error();
    } else {
        showToast('خطا در خرید');
        Haptic.error();
    }
}

// ═══════════════════ Delete Account ═══════════════════

async function deleteAccount() {
    if (!confirm('⚠️ آیا مطمئنی؟ تمام اطلاعاتت حذف میشه و غیرقابل بازگشته!')) return;
    if (!confirm('❌ بار آخر: واقعاً حذف بشه؟')) return;

    Haptic.heavy();
    const data = await apiPost('/delete_account', { confirm: true });
    if (data?.success) {
        showToast('حساب حذف شد. خداحافظ! 👋', 5000);
        setTimeout(() => {
            if (tg.close) tg.close();
        }, 3000);
    } else {
        showToast('خطا در حذف');
        Haptic.error();
    }
}

// ═══════════════════ Initialize ═══════════════════

window.addEventListener('load', () => {
    // Set date
    const dateEl = document.getElementById('todayDate');
    if (dateEl) dateEl.textContent = getPersianDate();

    // Check user
    if (!App.userId) {
        const page = document.querySelector('.page.active');
        if (page) {
            page.innerHTML = '<div class="empty-state">لطفاً از طریق تلگرام باز کنید</div>';
        }
        return;
    }

    // Load initial data
    loadToday();
});
