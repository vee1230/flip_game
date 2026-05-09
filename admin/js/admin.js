// Admin Dashboard Logic

const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const API_URL = isLocal ? 'http://localhost:8000/api/v1' : 'https://endearing-optimism-production-6a15.up.railway.app/api/v1';

let adminToken = localStorage.getItem('adminToken');
let adminUser = null;

// Auth check
document.addEventListener('DOMContentLoaded', () => {
    try {
        adminUser = JSON.parse(localStorage.getItem('adminUser'));
    } catch(e) {}
    
    if (!adminToken || !adminUser) {
        window.location.href = 'index.html';
        return;
    }

    document.getElementById('admin-name-display').textContent = adminUser.name || 'Admin';
    document.getElementById('auth-check').style.display = 'none';

    // Load initial tab
    loadOverview();

    // Mobile Sidebar
    document.getElementById('sidebar-toggle').addEventListener('click', () => {
        document.getElementById('sidebar').classList.toggle('open');
    });
});

function logout() {
    localStorage.removeItem('adminToken');
    localStorage.removeItem('adminUser');
    window.location.href = 'index.html';
}

// Interceptor for fetch to add Authorization header
async function apiFetch(endpoint, options = {}) {
    if (!options.headers) options.headers = {};
    options.headers['Authorization'] = `Bearer ${adminToken}`;
    options.headers['Content-Type'] = 'application/json';

    const res = await fetch(`${API_URL}${endpoint}`, options);
    if (res.status === 401) {
        logout();
        throw new Error('Unauthorized');
    }
    return res.json();
}

// Tab Switching
function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    
    document.getElementById(tabId).classList.add('active');
    document.querySelector(`.nav-item[href="#${tabId}"]`).classList.add('active');
    
    if (window.innerWidth <= 768) {
        document.getElementById('sidebar').classList.remove('open');
    }

    if (tabId === 'overview') loadOverview();
    if (tabId === 'users') loadPlayers();
    if (tabId === 'rewards') loadRewards();
    if (tabId === 'announcements') loadAnnouncements();
    if (tabId === 'leaderboard') loadLeaderboard();
    if (tabId === 'analytics') loadAnalytics();
    if (tabId === 'multiplayer') loadMultiplayer();
    if (tabId === 'activity_logs') loadActivityLogs();
}

// -----------------------------------------------------------------
// OVERVIEW TAB
// -----------------------------------------------------------------
async function loadOverview() {
    try {
        const data = await apiFetch('/admin/analytics/overview');
        document.getElementById('stat-total-players').textContent = data.total_players.toLocaleString();
        document.getElementById('stat-active-players').textContent = data.active_players.toLocaleString();
        document.getElementById('stat-total-stars').textContent = data.total_stars.toLocaleString();
        document.getElementById('stat-total-trophies').textContent = data.total_trophies.toLocaleString();
        document.getElementById('stat-total-games').textContent = data.total_games.toLocaleString();
        document.getElementById('stat-highest-score').textContent = data.highest_score.toLocaleString();
        document.getElementById('stat-daily-challenges').textContent = data.total_daily_challenges.toLocaleString();
        document.getElementById('stat-reward-claims').textContent = (data.total_reward_chests + data.total_bonus_claims).toLocaleString();
        document.getElementById('stat-mp-matches').textContent = data.total_multiplayer_matches.toLocaleString();
        document.getElementById('stat-active-mp-matches').textContent = data.active_multiplayer_matches.toLocaleString();
        document.getElementById('stat-push-active').textContent = data.tokens_active.toLocaleString();
        document.getElementById('stat-push-inactive').textContent = data.tokens_inactive.toLocaleString();

        const activities = await apiFetch('/admin/recent-activity');
        const tbody = document.querySelector('#activities-table tbody');
        // Only show top 5 for overview
        tbody.innerHTML = activities.slice(0, 5).map(a => `
            <tr>
                <td><strong>${a.player_name || 'System'}</strong></td>
                <td><span class="badge" style="background: rgba(255,255,255,0.1);">${a.action_type}</span></td>
                <td>${a.details || ''}</td>
                <td style="color:#94a3b8;font-size:12px;">${new Date(a.created_at).toLocaleString()}</td>
            </tr>
        `).join('');
    } catch(e) { console.error('Overview error:', e); }
}

// -----------------------------------------------------------------
// PLAYERS TAB
// -----------------------------------------------------------------
let allPlayers = [];

async function loadPlayers() {
    try {
        allPlayers = await apiFetch('/admin/players');
        renderPlayers(allPlayers);
    } catch(e) { console.error('Players error:', e); }
}

function renderPlayers(players) {
    const tbody = document.querySelector('#players-table tbody');
    tbody.innerHTML = players.map(p => `
        <tr>
            <td>
                <strong>${p.display_name}</strong><br>
                <span style="font-size:12px;color:#94a3b8;">@${p.username} | ${p.email || 'No email'}</span>
            </td>
            <td><span class="badge ${p.account_type.toLowerCase()}">${p.account_type}</span></td>
            <td><span class="badge ${p.status.toLowerCase()}">${p.status}</span></td>
            <td style="color:#fcd34d;font-weight:bold;">${p.stars}</td>
            <td style="color:#fbbf24;font-weight:bold;">${p.trophies}</td>
            <td>${p.best_score || 0}</td>
            <td>${p.games_played || 0}</td>
            <td style="font-size:12px;color:#94a3b8;">${p.last_login ? new Date(p.last_login).toLocaleDateString() : 'Never'}</td>
        </tr>
    `).join('');
}

function filterPlayers() {
    const term = document.getElementById('player-search').value.toLowerCase();
    const filtered = allPlayers.filter(p => 
        p.display_name.toLowerCase().includes(term) || 
        p.username.toLowerCase().includes(term) || 
        (p.email && p.email.toLowerCase().includes(term))
    );
    renderPlayers(filtered);
}

// -----------------------------------------------------------------
// REWARDS TAB
// -----------------------------------------------------------------
async function loadRewards() {
    try {
        // Load players for select dropdown
        if (allPlayers.length === 0) {
            allPlayers = await apiFetch('/admin/players');
        }
        
        const select = document.getElementById('reward-player-select');
        select.innerHTML = '<option value="">Select a player...</option>' + 
            allPlayers.map(p => `<option value="${p.id}">${p.display_name} (@${p.username}) - ⭐ ${p.stars} | 🏆 ${p.trophies}</option>`).join('');

        // Load logs
        const logs = await apiFetch('/admin/reward-logs');
        const tbody = document.querySelector('#reward-logs-table tbody');
        tbody.innerHTML = logs.map(l => {
            const isAdd = l.action === 'add';
            const color = isAdd ? 'var(--success)' : 'var(--danger)';
            const sign = isAdd ? '+' : '-';
            const icon = l.reward_type === 'stars' ? '⭐' : '🏆';
            
            return `
            <tr>
                <td><strong>${l.player_name}</strong><br><span style="font-size:11px;color:#94a3b8;">@${l.player_username}</span></td>
                <td><span class="badge" style="background:rgba(${isAdd?'16,185,129':'239,68,68'},0.2);color:${color}">${l.action.toUpperCase()}</span></td>
                <td style="color:${color};font-weight:bold;">${sign}${l.amount} ${icon}</td>
                <td style="font-size:13px;">${l.reason}</td>
                <td style="font-size:12px;color:#94a3b8;">${new Date(l.created_at).toLocaleString()}<br>by ${l.admin_name}</td>
            </tr>
            `;
        }).join('');
    } catch(e) { console.error('Rewards error:', e); }
}

async function handleRewardAdjustment(e) {
    e.preventDefault();
    const btn = document.getElementById('btn-adjust-reward');
    
    const payload = {
        player_id: parseInt(document.getElementById('reward-player-select').value),
        action: document.getElementById('reward-action').value,
        type: document.getElementById('reward-type').value,
        amount: parseInt(document.getElementById('reward-amount').value),
        reason: document.getElementById('reward-reason').value
    };

    if (!payload.player_id) { alert("Please select a player"); return; }
    
    const confirmMsg = `Are you sure you want to ${payload.action.toUpperCase()} ${payload.amount} ${payload.type.toUpperCase()} ${payload.action==='add'?'to':'from'} this player?`;
    if (!confirm(confirmMsg)) return;

    btn.disabled = true;
    btn.textContent = 'Processing...';

    try {
        const res = await apiFetch('/admin/rewards/adjust', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        
        if (res.success) {
            alert(`Success! Player now has ${res.new_balance} ${payload.type}.`);
            document.getElementById('reward-amount').value = '';
            document.getElementById('reward-reason').value = '';
            loadRewards(); // refresh lists
        } else {
            alert(res.detail || "Adjustment failed");
        }
    } catch(err) {
        alert(err.message || "An error occurred");
    } finally {
        btn.disabled = false;
        btn.textContent = 'Apply Adjustment';
    }
}

// -----------------------------------------------------------------
// LEADERBOARD TAB
// -----------------------------------------------------------------
async function loadLeaderboard() {
    try {
        const data = await apiFetch('/admin/leaderboard');
        const tbody = document.querySelector('#leaderboard-table tbody');
        
        tbody.innerHTML = data.leaderboard.map((l, i) => `
            <tr>
                <td style="font-weight:bold;color:#fcd34d;">#${i+1}</td>
                <td><strong>${l.display_name}</strong><br><span class="badge ${l.account_type.toLowerCase()}" style="font-size:9px;">${l.account_type}</span></td>
                <td style="font-weight:900;color:#fcd34d;font-size:16px;">${l.score}</td>
                <td>${l.stage}</td>
                <td>${l.theme}</td>
                <td>${l.time_seconds}s</td>
                <td style="font-size:12px;color:#94a3b8;">${new Date(l.achieved_at).toLocaleDateString()}</td>
            </tr>
        `).join('');
    } catch(e) { console.error('Leaderboard error:', e); }
}

// -----------------------------------------------------------------
// ANNOUNCEMENTS TAB
// -----------------------------------------------------------------
async function loadAnnouncements() {
    try {
        const data = await apiFetch('/admin/reward-announcements');
        const tbody = document.querySelector('#announcements-table tbody');
        
        tbody.innerHTML = data.map(a => {
            const isActive = a.status === 'active';
            const statusColor = isActive ? 'var(--success)' : 'var(--text-secondary)';
            const icon = a.reward_type === 'stars' ? '⭐' : '🏆';
            
            return `
            <tr>
                <td><strong>${a.title}</strong><br><span style="font-size:12px;color:#94a3b8;">${a.task_description}</span></td>
                <td style="font-weight:bold;color:#fcd34d;">${a.reward_amount} ${icon}</td>
                <td style="font-size:12px;color:#94a3b8;">
                    Start: ${new Date(a.start_date).toLocaleString()}<br>
                    End: ${new Date(a.end_date).toLocaleString()}
                </td>
                <td>
                    <select onchange="toggleAnnouncementStatus(${a.id}, this.value)" style="background:rgba(0,0,0,0.3); color:${statusColor}; border:1px solid ${statusColor}; padding:4px 8px; border-radius:4px; outline:none;">
                        <option value="active" ${isActive ? 'selected' : ''}>Active</option>
                        <option value="inactive" ${!isActive ? 'selected' : ''}>Inactive</option>
                    </select>
                </td>
                <td style="font-weight:bold;">${a.total_claims || 0}</td>
                <td>
                    <button class="btn-primary" style="padding:6px 12px; font-size:12px; width:auto; margin-bottom:4px;" onclick='editAnnouncement(${JSON.stringify(a).replace(/'/g, "&#39;")})'>Edit</button>
                    <button class="btn-primary" style="padding:6px 12px; font-size:12px; width:auto; background:var(--bg-panel); border:1px solid var(--accent);" onclick="sendAnnouncementPush(${a.id})">🔔 Push</button>
                </td>
            </tr>
            `;
        }).join('');
    } catch(e) { console.error('Announcements error:', e); }
}

function editAnnouncement(ann) {
    document.getElementById('ann-id').value = ann.id;
    document.getElementById('ann-title').value = ann.title;
    document.getElementById('ann-task').value = ann.task_description;
    document.getElementById('ann-reward-type').value = ann.reward_type;
    document.getElementById('ann-reward-amount').value = ann.reward_amount;
    
    // Convert dates to datetime-local format
    const toLocalISO = (dStr) => {
        const d = new Date(dStr);
        d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
        return d.toISOString().slice(0,16);
    };
    
    document.getElementById('ann-start').value = toLocalISO(ann.start_date);
    document.getElementById('ann-end').value = toLocalISO(ann.end_date);
    document.getElementById('ann-notification').value = ann.notification_message || '';
    
    document.getElementById('announcement-modal-title').textContent = 'Edit Bonus Challenge';
    document.getElementById('btn-save-announcement').textContent = 'Update Challenge';
    document.getElementById('announcement-modal').style.display = 'flex';
}

async function handleAnnouncementSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('btn-save-announcement');
    const id = document.getElementById('ann-id').value;
    
    const toMySQLDate = (isoStr) => new Date(isoStr).toISOString().slice(0, 19).replace('T', ' ');

    const payload = {
        title: document.getElementById('ann-title').value,
        task_description: document.getElementById('ann-task').value,
        reward_type: document.getElementById('ann-reward-type').value,
        reward_amount: parseInt(document.getElementById('ann-reward-amount').value),
        start_date: toMySQLDate(document.getElementById('ann-start').value),
        end_date: toMySQLDate(document.getElementById('ann-end').value),
        notification_message: document.getElementById('ann-notification').value,
        difficulty_target: 'Any',
        theme_target: 'Any'
    };

    btn.disabled = true;
    btn.textContent = 'Saving...';

    try {
        const url = id ? `/admin/reward-announcements/${id}` : '/admin/reward-announcements';
        const method = id ? 'PUT' : 'POST';
        
        const res = await apiFetch(url, {
            method,
            body: JSON.stringify(payload)
        });
        
        if (res.success) {
            alert(id ? "Updated successfully!" : `Created successfully! Push notifications: ${res.notification_success_count} success, ${res.notification_failure_count} failed.`);
            document.getElementById('announcement-modal').style.display = 'none';
            document.getElementById('announcement-form').reset();
            document.getElementById('ann-id').value = '';
            document.getElementById('announcement-modal-title').textContent = 'Create Bonus Challenge';
            document.getElementById('btn-save-announcement').textContent = 'Publish Challenge';
            loadAnnouncements();
        } else {
            alert(res.detail || "Failed to save announcement");
        }
    } catch(err) {
        alert(err.message || "An error occurred");
    } finally {
        btn.disabled = false;
        btn.textContent = id ? 'Update Challenge' : 'Publish Challenge';
    }
}

async function toggleAnnouncementStatus(id, status) {
    try {
        const res = await apiFetch(`/admin/reward-announcements/${id}/status`, {
            method: 'PATCH',
            body: JSON.stringify({ status })
        });
        if (!res.success) alert("Failed to update status");
        loadAnnouncements();
    } catch(e) {
        alert("Error updating status");
        loadAnnouncements();
    }
}

async function sendAnnouncementPush(id) {
    if (!confirm("Send push notification to all players for this announcement?")) return;
    try {
        const res = await apiFetch(`/admin/reward-announcements/${id}/notify`, { method: 'POST' });
        if (res.success) alert(`Push notifications: ${res.notification_success_count} success, ${res.notification_failure_count} failed.`);
    } catch(e) { alert("Error sending push notification"); }
}

// -----------------------------------------------------------------
// ANALYTICS TAB
// -----------------------------------------------------------------
let playersChart = null, gamesChart = null, mpChart = null;
let claimsChart = null, currencyChart = null;
let difficultyChart = null, themesChart = null;

const CHART_COLORS = ['#7c3aed','#06b6d4','#f59e0b','#ec4899','#10b981','#3b82f6','#f97316'];

function makeLineDataset(label, data, color) {
    return { label, data, borderColor: color, backgroundColor: color.replace(')', ', 0.15)').replace('rgb','rgba'), fill: true, tension: 0.4, pointRadius: 3 };
}

function fillDates(rawData, valueKey='count') {
    // Build a map of date -> value
    const map = {};
    rawData.forEach(r => { map[r.date ? r.date.substring(0,10) : ''] = Number(r[valueKey]) || 0; });
    const labels = [], values = [];
    for (let i = 29; i >= 0; i--) {
        const d = new Date(); d.setDate(d.getDate() - i);
        const key = d.toISOString().substring(0,10);
        labels.push(key);
        values.push(map[key] || 0);
    }
    return { labels, values };
}

const CHART_OPTIONS = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: '#cbd5e1', font: { family: 'Outfit' } } } },
    scales: {
        x: { ticks: { color: '#64748b', maxTicksLimit: 7, font: { family: 'Outfit' } }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { ticks: { color: '#64748b', font: { family: 'Outfit' } }, grid: { color: 'rgba(255,255,255,0.04)' } }
    }
};
const PIE_OPTIONS = {
    responsive: true, maintainAspectRatio: false, cutout: '65%',
    plugins: { legend: { labels: { color: '#cbd5e1', font: { family: 'Outfit' }, padding: 16 } } }
};

async function loadAnalytics() {
    try {
        Chart.defaults.color = '#cbd5e1';
        Chart.defaults.borderColor = 'rgba(255,255,255,0.05)';

        const [ppd, gpd, mp, claims, stars, trophies, diff, themes] = await Promise.all([
            apiFetch('/admin/analytics/players-per-day'),
            apiFetch('/admin/analytics/games-per-day'),
            apiFetch('/admin/analytics/multiplayer'),
            apiFetch('/admin/analytics/reward-claims'),
            apiFetch('/admin/analytics/stars-earned'),
            apiFetch('/admin/analytics/trophies-earned'),
            apiFetch('/admin/analytics/difficulty-usage'),
            apiFetch('/admin/analytics/theme-usage'),
        ]);

        // --- Players Per Day ---
        if (playersChart) playersChart.destroy();
        const pData = fillDates(ppd);
        playersChart = new Chart(document.getElementById('playersChart'), {
            type: 'line',
            data: { labels: pData.labels, datasets: [makeLineDataset('New Registrations', pData.values, '#06b6d4')] },
            options: CHART_OPTIONS
        });

        // --- Games Per Day ---
        if (gamesChart) gamesChart.destroy();
        const gData = fillDates(gpd);
        gamesChart = new Chart(document.getElementById('gamesChart'), {
            type: 'bar',
            data: { labels: gData.labels, datasets: [{ label: 'Games Played', data: gData.values, backgroundColor: 'rgba(139,92,246,0.6)', borderRadius: 6 }] },
            options: CHART_OPTIONS
        });

        // --- Multiplayer Matches Per Day ---
        if (mpChart) mpChart.destroy();
        const mData = fillDates(mp);
        mpChart = new Chart(document.getElementById('mpChart'), {
            type: 'bar',
            data: { labels: mData.labels, datasets: [{ label: 'MP Matches', data: mData.values, backgroundColor: 'rgba(236,72,153,0.6)', borderRadius: 6 }] },
            options: CHART_OPTIONS
        });

        // --- Reward Claims ---
        if (claimsChart) claimsChart.destroy();
        const cChests = fillDates(claims.chests || []);
        const cDaily = fillDates(claims.daily || []);
        const cBonus = fillDates(claims.bonus || []);
        claimsChart = new Chart(document.getElementById('claimsChart'), {
            type: 'line',
            data: {
                labels: cChests.labels,
                datasets: [
                    makeLineDataset('Reward Chests', cChests.values, '#f59e0b'),
                    makeLineDataset('Daily Challenges', cDaily.values, '#10b981'),
                    makeLineDataset('Bonus Challenges', cBonus.values, '#7c3aed'),
                ]
            },
            options: CHART_OPTIONS
        });

        // --- Stars & Trophies Earned ---
        if (currencyChart) currencyChart.destroy();
        const sData = fillDates(stars, 'total');
        const tData = fillDates(trophies, 'total');
        currencyChart = new Chart(document.getElementById('currencyChart'), {
            type: 'line',
            data: {
                labels: sData.labels,
                datasets: [
                    makeLineDataset('Stars Earned ⭐', sData.values, '#f59e0b'),
                    makeLineDataset('Trophies Earned 🏆', tData.values, '#8b5cf6'),
                ]
            },
            options: CHART_OPTIONS
        });

        // --- Difficulty Doughnut ---
        if (difficultyChart) difficultyChart.destroy();
        difficultyChart = new Chart(document.getElementById('difficultyChart'), {
            type: 'doughnut',
            data: { labels: diff.map(d => d.stage), datasets: [{ data: diff.map(d => d.count), backgroundColor: CHART_COLORS, borderWidth: 0 }] },
            options: PIE_OPTIONS
        });

        // --- Themes Doughnut ---
        if (themesChart) themesChart.destroy();
        themesChart = new Chart(document.getElementById('themesChart'), {
            type: 'doughnut',
            data: { labels: themes.map(t => t.theme), datasets: [{ data: themes.map(t => t.count), backgroundColor: CHART_COLORS, borderWidth: 0 }] },
            options: PIE_OPTIONS
        });

    } catch(e) { console.error('Analytics error:', e); }
}

// -----------------------------------------------------------------
// MULTIPLAYER TAB
// -----------------------------------------------------------------
function statusBadge(status) {
    const colors = {
        active: 'background:rgba(16,185,129,0.2);color:#34d399;',
        completed: 'background:rgba(59,130,246,0.2);color:#93c5fd;',
        disconnected: 'background:rgba(239,68,68,0.2);color:#fca5a5;',
        waiting: 'background:rgba(245,158,11,0.2);color:#fde68a;'
    };
    const s = colors[status] || 'background:rgba(148,163,184,0.2);color:#cbd5e1;';
    return `<span class="badge" style="${s}">${status}</span>`;
}

async function loadMultiplayer() {
    try {
        const matches = await apiFetch('/admin/multiplayer-matches');
        const tbody = document.querySelector('#multiplayer-table tbody');
        if (!matches || matches.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:#64748b;padding:32px;">No multiplayer matches found.</td></tr>';
            return;
        }
        tbody.innerHTML = matches.map(m => `
            <tr>
                <td style="color:#64748b;font-size:12px;">#${m.id}</td>
                <td style="font-family:monospace;font-size:12px;">${m.room_id}</td>
                <td><strong>${m.p1_name || '—'}</strong></td>
                <td><strong>${m.p2_name || '—'}</strong></td>
                <td style="text-align:center;"><strong>${m.player_1_score} — ${m.player_2_score}</strong></td>
                <td>${m.winner_name ? `<span style="color:#f59e0b;">🏆 ${m.winner_name}</span>` : '—'}</td>
                <td>${statusBadge(m.status)}</td>
                <td style="color:#64748b;font-size:12px;">${m.started_at ? new Date(m.started_at).toLocaleString() : '—'}</td>
                <td style="color:#64748b;font-size:12px;">${m.duration_seconds ? m.duration_seconds + 's' : '—'}</td>
            </tr>
        `).join('');
    } catch(e) { console.error('Multiplayer error:', e); }
}

// -----------------------------------------------------------------
// ACTIVITY LOGS TAB
// -----------------------------------------------------------------
function actionBadge(type) {
    const colors = {
        login: 'background:rgba(59,130,246,0.2);color:#93c5fd;',
        register: 'background:rgba(16,185,129,0.2);color:#34d399;',
        multiplayer_start: 'background:rgba(139,92,246,0.2);color:#d8b4fe;',
        multiplayer_win: 'background:rgba(245,158,11,0.2);color:#fde68a;',
        multiplayer_disconnect: 'background:rgba(239,68,68,0.2);color:#fca5a5;',
    };
    const s = colors[type] || 'background:rgba(148,163,184,0.1);color:#94a3b8;';
    return `<span class="badge" style="${s}">${type.replace(/_/g,' ')}</span>`;
}

async function loadActivityLogs() {
    try {
        const activities = await apiFetch('/admin/recent-activity');
        const tbody = document.querySelector('#full-activities-table tbody');
        if (!activities || activities.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#64748b;padding:32px;">No activity found.</td></tr>';
            return;
        }
        tbody.innerHTML = activities.map(a => `
            <tr>
                <td><strong>${a.player_name || 'System'}</strong></td>
                <td>${actionBadge(a.action_type)}</td>
                <td style="color:#cbd5e1;">${a.details || ''}</td>
                <td style="color:#64748b;font-size:12px;">${new Date(a.created_at).toLocaleString()}</td>
            </tr>
        `).join('');
    } catch(e) { console.error('Activity logs error:', e); }
}

