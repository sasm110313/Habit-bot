/* ═══════════════════════════════════════════════════════════════════
   Pages — Stats, Journey, Achievements, More rendering
   ═══════════════════════════════════════════════════════════════════ */

// ═══════════════════ Stats Page ═══════════════════

async function loadStats() {
    const data = await apiGet('/stats');
    if (!data) return;

    document.getElementById('statPercent').textContent = `${data.percentage}%`;
    document.getElementById('statPerfect').textContent = data.perfect_days;
    document.getElementById('statCourse').textContent = data.course_days;
    document.getElementById('statXP').textContent = data.xp_earned;

    renderWeeklyChart(data.daily);
    renderCalendar(data.calendar);
}

function renderWeeklyChart(daily) {
    const chart = document.getElementById('weeklyChart');
    if (!chart) return;
    chart.innerHTML = '';

    const days = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج'];

    if (daily && daily.length) {
        daily.forEach((d, i) => {
            const pct = (d.done / 3) * 100;
            const col = document.createElement('div');
            col.className = 'chart-col';
            col.innerHTML = `
                <div class="chart-bar" style="height:${Math.max(pct, 6)}%"></div>
                <span class="chart-day">${days[i % 7]}</span>
            `;
            chart.appendChild(col);
        });
    }
}

function renderCalendar(calendar) {
    const cal = document.getElementById('calendarGrid');
    if (!cal) return;
    cal.innerHTML = '';

    if (calendar && calendar.length) {
        calendar.forEach(day => {
            const cls = day.done === 3 ? 'perfect'
                      : day.done > 0 ? 'partial'
                      : 'empty';
            const today = day.is_today ? ' today' : '';
            const icon = day.done === 3
                ? `<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>`
                : '';

            const cell = document.createElement('div');
            cell.className = `cal-cell ${cls}${today}`;
            cell.innerHTML = icon;
            cal.appendChild(cell);
        });
    }
}

// ═══════════════════ Journey Page ═══════════════════

const JOURNEY_MILESTONES = [
    { chelle: 1, name: 'آغاز سفر', color: '#10B981' },
    { chelle: 2, name: 'مسیر ادامه', color: '#5AC8FA' },
    { chelle: 3, name: 'استقامت', color: '#2AABEE' },
    { chelle: 4, name: 'بلوغ', color: '#5856D6' },
    { chelle: 5, name: 'تسلط', color: '#F59E0B' },
    { chelle: 6, name: 'قدرت', color: '#FF2D55' },
    { chelle: 7, name: 'حکمت', color: '#AF52DE' },
    { chelle: 8, name: 'استادی', color: '#FFCC00' },
    { chelle: 9, name: 'عادت‌ساز', color: '#EF4444' },
];

async function loadJourney() {
    const data = await apiGet('/journey');
    if (!data) return;

    const container = document.getElementById('journeyPath');
    if (!container) return;
    container.innerHTML = '';

    JOURNEY_MILESTONES.forEach(m => {
        let cls, desc, progressHTML = '';

        if (m.chelle < data.current_chelle) {
            cls = 'completed';
            desc = 'تکمیل شده';
        } else if (m.chelle === data.current_chelle) {
            cls = 'current';
            desc = `${data.progress_pct}% انجام شده`;
            progressHTML = `
                <div class="journey-progress">
                    <div class="journey-progress-fill" style="width:${data.progress_pct}%"></div>
                </div>`;
        } else {
            cls = 'locked';
            desc = 'قفل';
        }

        const iconSvg = cls === 'locked'
            ? '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>'
            : cls === 'completed'
                ? '<polyline points="20 6 9 17 4 12"/>'
                : '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>';

        const node = document.createElement('div');
        node.className = `journey-item ${cls}`;
        node.innerHTML = `
            <div class="journey-icon" style="background:${m.color}15">
                <svg viewBox="0 0 24 24" fill="none" stroke="${m.color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    ${iconSvg}
                </svg>
            </div>
            <div class="journey-info">
                <div class="journey-name">چهله ${m.chelle}: ${m.name}</div>
                <div class="journey-desc">${desc}</div>
                ${progressHTML}
            </div>
        `;
        container.appendChild(node);
    });
}

// ═══════════════════ Achievements Page ═══════════════════

const ACHIEVEMENTS_DATA = [
    { key: 'first_habit', name: 'شروع', color: '#10B981', d: '<path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>' },
    { key: 'streak_3', name: '۳ روزه', color: '#F97316', d: '<path d="M12 2c.5 3.5-1.5 6-1.5 6s2.5.5 3.5 3c.7 1.7.3 3.5-.5 5 2.5-1 4-3.5 4-6.5 0-4.5-3.5-7-5.5-7.5z"/>' },
    { key: 'streak_7', name: 'هفته‌ای', color: '#F97316', d: '<path d="M12 2c.5 3.5-1.5 6-1.5 6s2.5.5 3.5 3c.7 1.7.3 3.5-.5 5 2.5-1 4-3.5 4-6.5 0-4.5-3.5-7-5.5-7.5z"/>' },
    { key: 'streak_14', name: '۲ هفته', color: '#F59E0B', d: '<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>' },
    { key: 'streak_21', name: '۳ هفته', color: '#F59E0B', d: '<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>' },
    { key: 'streak_30', name: 'ماهانه', color: '#5856D6', d: '<path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>' },
    { key: 'streak_40', name: 'چهله', color: '#AF52DE', d: '<circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>' },
    { key: 'streak_66', name: 'عادت‌ساز', color: '#FF2D55', d: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>' },
    { key: 'perfect_1', name: 'روز کامل', color: '#FFCC00', d: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>' },
    { key: 'perfect_7', name: 'هفته طلایی', color: '#FFCC00', d: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>' },
    { key: 'perfect_30', name: 'ماه درخشان', color: '#FF9500', d: '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>' },
    { key: 'course_7', name: 'دانش‌آموز', color: '#2AABEE', d: '<path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z"/><path d="M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z"/>' },
    { key: 'course_30', name: 'دانشجو', color: '#2AABEE', d: '<path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>' },
    { key: 'course_chelle', name: 'فارغ‌التحصیل', color: '#5856D6', d: '<path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 7 3 10 0v-5"/>' },
    { key: 'first_journal', name: 'تحلیل‌گر', color: '#5AC8FA', d: '<path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>' },
    { key: 'comeback', name: 'برگشت', color: '#10B981', d: '<polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 102.13-9.36L1 10"/>' },
    { key: 'early_bird', name: 'سحرخیز', color: '#FF9500', d: '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>' },
    { key: 'night_owl', name: 'جغد شب', color: '#5856D6', d: '<path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>' },
    { key: 'emergency_hero', name: 'قهرمان', color: '#FF2D55', d: '<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>' },
];

async function loadAchievements() {
    const data = await apiGet('/achievements');
    if (!data) return;

    const grid = document.getElementById('achGrid');
    if (!grid) return;
    grid.innerHTML = '';

    const unlocked = new Set(data.unlocked || []);

    ACHIEVEMENTS_DATA.forEach((ach, i) => {
        const isLocked = !unlocked.has(ach.key);
        const item = document.createElement('div');
        item.className = `ach-item ${isLocked ? 'locked' : ''}`;
        item.style.animationDelay = `${i * 40}ms`;
        item.innerHTML = `
            <div class="ach-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="${ach.color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    ${ach.d}
                </svg>
            </div>
            <div class="ach-name">${ach.name}</div>
        `;
        grid.appendChild(item);
    });
}

// ═══════════════════ More Page ═══════════════════

async function loadMore() {
    await Promise.all([
        loadDhikr(),
        loadStreaks(),
        loadShop(),
    ]);
}

async function loadDhikr() {
    const dhikr = await apiGet('/dhikr');
    if (!dhikr) return;

    document.getElementById('dhikrArabic').textContent = dhikr.text;
    document.getElementById('dhikrMeaning').textContent = dhikr.meaning;
    document.getElementById('dhikrCount').textContent = `تکرار: ${dhikr.count}`;
    document.getElementById('hadithText').textContent = dhikr.hadith;
}

async function loadStreaks() {
    const stats = await apiGet('/stats');
    if (!stats?.streaks) return;

    const el = document.getElementById('streaksDetail');
    if (!el) return;
    el.innerHTML = '';

    const habits = [
        { key: 'namaz', name: 'تمرکز در نماز', color: '#5856D6' },
        { key: 'sleep', name: 'خواب منظم', color: '#5AC8FA' },
        { key: 'exercise', name: 'ورزش', color: '#FF2D55' },
    ];

    habits.forEach(h => {
        const s = stats.streaks[h.key] || { current: 0, best: 0 };
        const item = document.createElement('div');
        item.className = 'streak-item';
        item.innerHTML = `
            <div class="streak-icon" style="background:${h.color}15">
                <svg viewBox="0 0 24 24" fill="${h.color}" stroke="none">
                    <path d="M12 2c.5 3.5-1.5 6-1.5 6s2.5.5 3.5 3c.7 1.7.3 3.5-.5 5 2.5-1 4-3.5 4-6.5 0-4.5-3.5-7-5.5-7.5z"/>
                </svg>
            </div>
            <div class="streak-info">
                <div class="streak-name">${h.name}</div>
                <div class="streak-best">بهترین: ${s.best} روز</div>
            </div>
            <div class="streak-badge">${s.current}</div>
        `;
        el.appendChild(item);
    });
}

async function loadShop() {
    const shop = await apiGet('/shop');
    if (!shop) return;

    const el = document.getElementById('shopItems');
    if (!el) return;
    el.innerHTML = '';

    shop.items.forEach(item => {
        const canBuy = shop.xp >= item.cost;
        const row = document.createElement('div');
        row.className = 'shop-item';
        row.innerHTML = `
            <div class="shop-info">
                <div class="shop-name">${item.name}</div>
                <div class="shop-cost">${item.cost} XP</div>
            </div>
            <button class="shop-buy" ${canBuy ? '' : 'disabled'} onclick="buyItem('${item.id}')">
                ${canBuy ? 'خرید' : 'قفل'}
            </button>
        `;
        el.appendChild(row);
    });
}
