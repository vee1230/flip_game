function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    
    document.getElementById(tabId).classList.add('active');
    document.querySelector(`.nav-item[href="#${tabId}"]`).classList.add('active');
    
    if (tabId === 'overview') loadOverview();
    if (tabId === 'users') loadUsers();
    if (tabId === 'leaderboard') loadLeaderboard();
    if (tabId === 'analytics') loadAnalytics();
}

const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const PYTHON_API = isLocal ? 'http://localhost:8000/api/v1' : 'https://flipgame-production.up.railway.app/api/v1';
const PHP_API = '../includes/api.php';

async function fetchAPI(action) {
    const pyMap = {
        'get_overview':   `${PYTHON_API}/admin/overview`,
        'get_users':      `${PYTHON_API}/admin/users`,
        'get_leaderboard':`${PYTHON_API}/admin/leaderboard`,
        'get_activities': `${PYTHON_API}/admin/activities`,
        'get_analytics':  `${PYTHON_API}/admin/analytics`,
    };
    const url = pyMap[action];
    if (!url) {
        console.error('Unknown action:', action);
        return null;
    }
    try {
        const res = await fetch(url);
        return await res.json();
    } catch (e) {
        console.error('API Error (Python API failed):', e);
        return null;
    }
}

async function loadOverview() {
    const data = await fetchAPI('get_overview');
    if (data && !data.error) {
        document.getElementById('stat-total-users').textContent = data.total_users;
        document.getElementById('stat-total-games').textContent = data.total_games;
        document.getElementById('stat-max-score').textContent = data.max_score;
        document.getElementById('stat-active-users').textContent = data.active_users;
        document.getElementById('stat-total-trophies').textContent = data.total_trophies.toLocaleString();
    }

    const activities = await fetchAPI('get_activities');
    if (activities && !activities.error) {
        const tbody = document.querySelector('#activities-table tbody');
        tbody.innerHTML = activities.map(a => `
            <tr>
                <td><strong>${a.display_name}</strong></td>
                <td><span class="badge" style="background: rgba(255,255,255,0.1); border:none; color:#fff;">${a.action_type.replace('_', ' ')}</span></td>
                <td>${a.details}</td>
                <td>${new Date(a.created_at).toLocaleString()}</td>
            </tr>
        `).join('');
    }
}

async function loadUsers() {
    const data = await fetchAPI('get_users');
    if (data && !data.error) {
        const tbody = document.querySelector('#users-table tbody');
        tbody.innerHTML = data.map(u => `
            <tr>
                <td><strong>${u.display_name}</strong></td>
                <td>@${u.username}</td>
                <td><span class="badge ${u.account_type}">${u.account_type}</span></td>
                <td><span class="badge ${u.status}">${u.status}</span></td>
                <td style="font-weight:700; color:#fbbf24;">🏆 ${u.trophies || 0}</td>
                <td>${new Date(u.created_at).toLocaleDateString()}</td>
                <td style="display:flex; gap:8px;">
                    <button onclick="openEditModal(${u.id},'${u.display_name.replace(/'/g,"\\'")}','${(u.username||'').replace(/'/g,"\\'")}','${(u.email||'').replace(/'/g,"\\'")}','${u.status}')"
                        style="background:none; border:1px solid rgba(124,58,237,0.5); color:#a78bfa; border-radius:8px; padding:5px 12px; cursor:pointer; font-weight:700; font-family:'Outfit',sans-serif; font-size:13px; transition:0.2s;"
                        onmouseover="this.style.background='rgba(124,58,237,0.2)'" onmouseout="this.style.background='none'">Edit</button>
                    <button onclick="deleteUser(${u.id})"
                        style="background:none; border:1px solid rgba(239,68,68,0.5); color:#f87171; border-radius:8px; padding:5px 12px; cursor:pointer; font-weight:700; font-family:'Outfit',sans-serif; font-size:13px; transition:0.2s;"
                        onmouseover="this.style.background='rgba(239,68,68,0.2)'" onmouseout="this.style.background='none'">Delete</button>
                </td>
            </tr>
        `).join('');
    }
}

function openEditModal(id, name, username, email, status) {
    document.getElementById('edit-id').value = id;
    document.getElementById('edit-name').value = name;
    document.getElementById('edit-username').value = username;
    document.getElementById('edit-email').value = email;
    document.getElementById('edit-status').value = status;
    document.getElementById('edit-error').textContent = '';
    document.getElementById('edit-modal').style.display = 'block';
    document.getElementById('edit-modal-overlay').style.display = 'block';
}

function closeEditModal() {
    document.getElementById('edit-modal').style.display = 'none';
    document.getElementById('edit-modal-overlay').style.display = 'none';
}

async function saveUserEdit() {
    const id           = document.getElementById('edit-id').value;
    const display_name = document.getElementById('edit-name').value.trim();
    const username     = document.getElementById('edit-username').value.trim();
    const email        = document.getElementById('edit-email').value.trim();
    const status       = document.getElementById('edit-status').value;
    const errEl        = document.getElementById('edit-error');

    if (!display_name || !username) { errEl.textContent = 'Name and username are required.'; return; }

    try {
        const res = await fetch(`${PYTHON_API}/admin/users/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: parseInt(id), display_name, username, email, status })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);
    } catch (e) {
        errEl.textContent = e.message || 'Error updating user.';
        return;
    }
    closeEditModal();
    loadUsers();
}

async function deleteUser(id) {
    if (!confirm('Are you sure you want to delete this user? This cannot be undone.')) return;
    try {
        const res = await fetch(`${PYTHON_API}/admin/users/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (!data.error) { loadUsers(); loadOverview(); }
    } catch(e) {
        console.error('Error deleting user:', e);
    }
}

async function loadLeaderboard() {
    const stage = document.getElementById('lb-filter-stage').value || '';
    const theme = document.getElementById('lb-filter-theme').value || '';
    const playerSearch = document.getElementById('lb-filter-player').value.toLowerCase() || '';
    
    let url = `${PYTHON_API}/admin/leaderboard?limit=100`;
    if (stage) url += `&stage=${encodeURIComponent(stage)}`;
    if (theme) url += `&theme=${encodeURIComponent(theme)}`;
    
    try {
        const res = await fetch(url);
        const data = await res.json();
        
        if (data.error) throw new Error(data.error);
        
        const tbody = document.querySelector('#leaderboard-table tbody');
        const emptyState = document.getElementById('leaderboard-empty-state');
        const table = document.getElementById('leaderboard-table');
        
        // Update summary cards
        const summary = data.summary || {};
        document.getElementById('lb-highest-score').textContent = (summary.highest_score || 0).toLocaleString();
        document.getElementById('lb-top-player').textContent = summary.top_player || '—';
        document.getElementById('lb-fastest-time').textContent = (summary.fastest_time || 0) + 's';
        document.getElementById('lb-most-theme').textContent = summary.most_played_theme || '—';
        
        // Filter leaderboard data by player name if search is active
        let leaderboard = data.leaderboard || [];
        if (playerSearch) {
            leaderboard = leaderboard.filter(l => 
                l.display_name.toLowerCase().includes(playerSearch)
            );
        }
        
        // Show/hide empty state
        if (leaderboard.length === 0) {
            emptyState.style.display = 'block';
            table.style.display = 'none';
        } else {
            emptyState.style.display = 'none';
            table.style.display = 'table';
            
            tbody.innerHTML = leaderboard.map((l, idx) => {
                const accountBadgeStyle = l.account_type === 'Google' 
                    ? 'background: rgba(59, 130, 246, 0.2); color: #93c5fd; border: 1px solid rgba(59, 130, 246, 0.3);'
                    : 'background: rgba(148, 163, 184, 0.2); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.3);';
                
                const rank = l.rank || (idx + 1);
                const timeFormatted = formatTime(l.time_seconds);
                const dateAchieved = new Date(l.achieved_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                });
                
                return `
                    <tr>
                        <td style="font-weight:700; color:#fcd34d; text-align:center;">
                            ${rank <= 3 ? getTrophyEmoji(rank) : '#' + rank}
                        </td>
                        <td>
                            <strong>${escapeHtml(l.display_name)}</strong>
                            <span class="badge" style="${accountBadgeStyle}; font-size:9px; padding:2px 6px; border-radius:4px;">${l.account_type}</span>
                        </td>
                        <td style="color:#94a3b8; font-size:12px;">@${escapeHtml(l.display_name.toLowerCase())}</td>
                        <td style="color:#fcd34d; font-weight:900; font-size:16px; text-align:center;">${l.score}</td>
                        <td><span style="background:rgba(124,58,237,0.2); color:#d8b4fe; padding:4px 8px; border-radius:4px; font-size:12px; font-weight:700;">${escapeHtml(l.stage)}</span></td>
                        <td><span style="background:rgba(6,182,212,0.2); color:#a5f3fc; padding:4px 8px; border-radius:4px; font-size:12px; font-weight:700;">${escapeHtml(l.theme)}</span></td>
                        <td style="text-align:center; font-weight:700;">${timeFormatted}</td>
                        <td style="text-align:center; color:#94a3b8; font-size:13px;">${l.moves !== null ? l.moves : '—'}</td>
                        <td style="color:#94a3b8; font-size:12px;">${dateAchieved}</td>
                    </tr>
                `;
            }).join('');
        }
        
        // Populate filter dropdowns (from all available data)
        populateLeaderboardFilters(data.leaderboard || []);
        
    } catch (e) {
        console.error('Error loading leaderboard:', e);
        const emptyState = document.getElementById('leaderboard-empty-state');
        const table = document.getElementById('leaderboard-table');
        emptyState.style.display = 'block';
        table.style.display = 'none';
        emptyState.innerHTML = `<p style="font-size:16px; color:#f87171;">❌ Error loading leaderboard</p><p style="font-size:13px; color:#94a3b8;">${e.message}</p>`;
    }
}

function getTrophyEmoji(rank) {
    const emojis = ['🥇', '🥈', '🥉'];
    return emojis[rank - 1] || '#' + rank;
}

function formatTime(seconds) {
    if (!seconds) return '0s';
    if (seconds < 60) return seconds + 's';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function populateLeaderboardFilters(leaderboardData) {
    const stages = [...new Set(leaderboardData.map(l => l.stage).filter(Boolean))];
    const themes = [...new Set(leaderboardData.map(l => l.theme).filter(Boolean))];
    
    const stageSelect = document.getElementById('lb-filter-stage');
    const themeSelect = document.getElementById('lb-filter-theme');
    
    const currentStage = stageSelect.value;
    const currentTheme = themeSelect.value;
    
    stageSelect.innerHTML = '<option value="">All Stages</option>' + 
        stages.map(s => `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`).join('');
    
    themeSelect.innerHTML = '<option value="">All Themes</option>' + 
        themes.map(t => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('');
    
    stageSelect.value = currentStage;
    themeSelect.value = currentTheme;
}

function resetLeaderboardFilters() {
    document.getElementById('lb-filter-stage').value = '';
    document.getElementById('lb-filter-theme').value = '';
    document.getElementById('lb-filter-player').value = '';
    loadLeaderboard();
}

let difficultyChartInstance = null;
let themeChartInstance = null;

async function loadAnalytics() {
    const data = await fetchAPI('get_analytics');
    if (data && !data.error) {
        const diffCtx = document.getElementById('difficultyChart').getContext('2d');
        const themeCtx = document.getElementById('themeChart').getContext('2d');

        if (difficultyChartInstance) difficultyChartInstance.destroy();
        if (themeChartInstance) themeChartInstance.destroy();

        // Standard Chart styling for dark mode
        Chart.defaults.color = '#cbd5e1';
        Chart.defaults.borderColor = 'rgba(255,255,255,0.1)';

        difficultyChartInstance = new Chart(diffCtx, {
            type: 'bar',
            data: {
                labels: data.difficulties.map(d => d.stage),
                datasets: [{
                    label: 'Games Played',
                    data: data.difficulties.map(d => d.count),
                    backgroundColor: 'rgba(124, 58, 237, 0.6)',
                    borderColor: '#7c3aed',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });

        themeChartInstance = new Chart(themeCtx, {
            type: 'doughnut',
            data: {
                labels: data.themes.map(t => t.theme),
                datasets: [{
                    data: data.themes.map(t => t.count),
                    backgroundColor: ['#06b6d4', '#a78bfa', '#f59e0b', '#ec4899'],
                    borderWidth: 0
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, cutout: '70%' }
        });
    }
}

// Machine Learning Management
async function checkMLStatus() {
    const statusEl = document.getElementById('ml-models-status');
    if (!statusEl) return;
    try {
        const res = await fetch(`${PYTHON_API}/ml/status`);
        const data = await res.json();
        if (data.models_ready) {
            statusEl.textContent = 'Operational ✅';
            statusEl.style.color = '#10b981';
        } else {
            statusEl.textContent = 'Initializing... ⏳';
            statusEl.style.color = '#f59e0b';
        }
    } catch (e) {
        statusEl.textContent = 'Disconnected ❌';
        statusEl.style.color = '#ef4444';
    }
}

async function retrainMLModels() {
    if (!confirm('This will fetch all real data from the database and re-train the models. This may take a few seconds. Continue?')) return;
    
    const btn = event.target;
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Training... ⏳';
    
    try {
        const res = await fetch(`${PYTHON_API}/ml/train`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            alert(`Success! Models re-trained using ${data.real_samples_used} real samples.`);
            checkMLStatus();
        } else {
            alert('Training failed. Check server logs.');
        }
    } catch (e) {
        alert('Error connecting to ML server.');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    loadOverview();
    checkMLStatus();

    // Leaderboard Filter Event Listeners
    const stageFilter = document.getElementById('lb-filter-stage');
    const themeFilter = document.getElementById('lb-filter-theme');
    const playerFilter = document.getElementById('lb-filter-player');
    
    if (stageFilter) {
        stageFilter.addEventListener('change', loadLeaderboard);
    }
    if (themeFilter) {
        themeFilter.addEventListener('change', loadLeaderboard);
    }
    if (playerFilter) {
        playerFilter.addEventListener('keyup', (e) => {
            if (e.key === 'Enter') {
                loadLeaderboard();
            }
        });
    }

    // Mobile Sidebar Toggle
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
        
        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768 && 
                !sidebar.contains(e.target) && 
                !sidebarToggle.contains(e.target) && 
                sidebar.classList.contains('open')) {
                sidebar.classList.remove('open');
            }
        });
        
        // Close sidebar when a nav link is clicked on mobile
        document.querySelectorAll('.sidebar .nav-item').forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    sidebar.classList.remove('open');
                }
            });
        });
    }
});

// Logout Modal Functions
function confirmLogout() {
    document.getElementById('logout-modal').style.display = 'block';
    document.getElementById('logout-modal-overlay').style.display = 'block';
}

function closeLogoutModal() {
    document.getElementById('logout-modal').style.display = 'none';
    document.getElementById('logout-modal-overlay').style.display = 'none';
}

function confirmDoLogout() {
    // Navigate back to the main game screen
    window.location.href = '../index.html';
}

async function updateAnnouncement() {
    const inputEl = document.querySelector('.settings-card .auth-input');
    const message = inputEl.value.trim();
    if (!message) {
        alert('Please enter an announcement text.');
        return;
    }

    const btn = event.target || document.activeElement;
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Updating...';

    try {
        const res = await fetch(`${PYTHON_API}/admin/announcement`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        const data = await res.json();
        if (data.success) {
            alert(`Announcement sent to ${data.notified} users!`);
            inputEl.value = '';
        } else {
            alert(data.detail || 'Failed to send announcement.');
        }
    } catch (e) {
        console.error('Announcement Error:', e);
        alert('Error connecting to server.');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

async function resetLeaderboard() {
    if (!confirm('DANGER: This will permanently delete all scores from the leaderboard. Are you absolutely sure?')) return;
    
    const btn = event.target || document.activeElement;
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Resetting...';

    try {
        const res = await fetch(`${PYTHON_API}/admin/leaderboard`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (data.success) {
            alert('Leaderboard has been successfully reset.');
            loadLeaderboard(); 
        } else {
            alert('Failed to reset leaderboard.');
        }
    } catch (e) {
        console.error('Reset Error:', e);
        alert('Error connecting to server.');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}
