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
    if (tabId === 'leaderboard') loadLeaderboard();
    if (tabId === 'analytics') loadAnalytics();
}

// -----------------------------------------------------------------
// OVERVIEW TAB
// -----------------------------------------------------------------
async function loadOverview() {
    try {
        const data = await apiFetch('/admin/overview');
        document.getElementById('stat-total-players').textContent = data.total_players.toLocaleString();
        document.getElementById('stat-active-players').textContent = data.active_players.toLocaleString();
        document.getElementById('stat-total-stars').textContent = data.total_stars.toLocaleString();
        document.getElementById('stat-total-trophies').textContent = data.total_trophies.toLocaleString();

        const activities = await apiFetch('/admin/activities');
        const tbody = document.querySelector('#activities-table tbody');
        tbody.innerHTML = activities.map(a => `
            <tr>
                <td><strong>${a.display_name}</strong></td>
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
// ANALYTICS TAB
// -----------------------------------------------------------------
let playersChart = null;
let themesChart = null;

async function loadAnalytics() {
    try {
        const data = await apiFetch('/admin/analytics');
        
        Chart.defaults.color = '#cbd5e1';
        Chart.defaults.borderColor = 'rgba(255,255,255,0.05)';

        // New Players Chart
        if (playersChart) playersChart.destroy();
        const dates = data.new_players.map(d => d.date).reverse();
        const counts = data.new_players.map(d => d.count).reverse();
        
        playersChart = new Chart(document.getElementById('playersChart').getContext('2d'), {
            type: 'line',
            data: {
                labels: dates,
                datasets: [{
                    label: 'New Registrations',
                    data: counts,
                    borderColor: '#06b6d4',
                    backgroundColor: 'rgba(6,182,212,0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });

        // Themes Chart
        if (themesChart) themesChart.destroy();
        themesChart = new Chart(document.getElementById('themesChart').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: data.themes.map(t => t.theme),
                datasets: [{
                    data: data.themes.map(t => t.count),
                    backgroundColor: ['#7c3aed', '#06b6d4', '#f59e0b', '#ec4899', '#10b981'],
                    borderWidth: 0
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, cutout: '70%' }
        });
        
    } catch(e) { console.error('Analytics error:', e); }
}
