import { loginWithGoogle, logoutUser, initAuthListener } from '../auth/auth.js';
import { submitScore, getLeaderboard, getPersonalBest } from '../firebase/firestore.js';
import { requestNotificationPermission, onForegroundMessage, triggerLocalHighScoreNotification } from '../firebase/messaging.js';
import { CONFIG } from '../config.js';
let currentUser = null;

export const initGameFirebase = () => {
    // 1. Auth Listener
    initAuthListener((user) => {
        if (user) {
            currentUser = user;
            console.log("Logged in as:", user.displayName);
            const statusEl = document.getElementById("login-status");
            if (statusEl) statusEl.innerText = `Welcome, ${user.displayName}`;
            
            // Ask for notification permission after login
            requestNotificationPermission(user.uid);
            
            // Fetch personal best
            updatePersonalBestUI();
            
            // Poll for any unread backend notifications
            pollUnreadNotifications();
        } else {
            currentUser = null;
            const statusEl = document.getElementById("login-status");
            if (statusEl) statusEl.innerText = "Not logged in.";
        }
    });

    // 2. Initial render of leaderboard
    renderLeaderboardUI();
    
    // 3. Foreground Messages Event Listener
    onForegroundMessage((payload) => {
        console.log("Message received in foreground:", payload);
        alert(`${payload.notification.title}: ${payload.notification.body}`);
    });
};



const triggerNotificationAPI = async (targetUid, title, message, type) => {
    try {
        await fetch(`${CONFIG.PYTHON_API}/notifications/send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_uid: targetUid, title, message, type })
        });
    } catch (e) {
        console.error("Failed to trigger Python notification", e);
    }
};

const calculateAndTriggerNotifications = (currentUid, oldList, newList) => {
    oldList.forEach((oldUser, oldIndex) => {
        if (oldUser.uid === currentUid) return;

        const newIndex = newList.findIndex(u => u.uid === oldUser.uid);
        
        if (newIndex === -1) {
            triggerNotificationAPI(oldUser.uid, 'Rank Dropped! 🧗', 'Competition is fierce today! You have lost some ground and dropped out of the Top 10. Play another round to climb back up!', 'dropped_top10');
        } else if (newIndex > oldIndex) {
            if (oldIndex === 0) {
               triggerNotificationAPI(oldUser.uid, 'A Rival Appears! ⚔️', 'Someone just surpassed your #1 high score and took your spot on the leaderboard! Warm up your brain and play another round to reclaim your title.', 'lost_top1');
            } else {
               triggerNotificationAPI(oldUser.uid, 'Rank Dropped! 🛡️', 'Your high score was just beaten. We know you can do better! Jump into a new puzzle and take your spot back.', 'rank_dropped');
            }
        }
    });

    const newMyIndex = newList.findIndex(u => u.uid === currentUid);
    const oldMyIndex = oldList.findIndex(u => u.uid === currentUid);

    if (newMyIndex === 0 && oldMyIndex !== 0) {
        triggerNotificationAPI(currentUid, 'Global Champion! 👑', 'Phenomenal work! You have achieved the #1 rank on the leaderboard. Your memory skills are truly legendary.', 'reached_top1');
    } else if (newMyIndex !== -1 && oldMyIndex === -1) {
        triggerNotificationAPI(currentUid, 'Welcome to the Elite! 🎉', 'Incredible focus! Your latest score just pushed you into the Top 10 on the Global Leaderboard. Keep playing to climb even higher!', 'entered_top10');
    } else if (newMyIndex !== -1 && oldMyIndex !== -1 && newMyIndex < oldMyIndex) {
        triggerNotificationAPI(currentUid, 'Rank Up! 📈', 'Great job! Your quick thinking is paying off. You have successfully moved up the leaderboard.', 'rank_improved');
    }
};

const pollUnreadNotifications = async () => {
    if (!currentUser) return;
    try {
        const res = await fetch(`${CONFIG.PYTHON_API}/notifications/${currentUser.uid}`);
        const json = await res.json();
        
        if (json.status === 'success' && json.data.length > 0) {
            json.data.forEach(n => {
                alert(`🔔 ${n.title}\n\n${n.message}`);
            });
            
            const ids = json.data.map(n => n.id);
            await fetch(`${CONFIG.PYTHON_API}/notifications/mark-read`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notification_ids: ids })
            });
        }
    } catch(e) {
        console.error("Failed to poll notifications", e);
    }
};

const updatePersonalBestUI = async () => {
    if (!currentUser) return;
    const best = await getPersonalBest(currentUser.uid);
    const pbElement = document.getElementById("personal-best");
    if (pbElement) pbElement.innerText = best;
};

const renderLeaderboardUI = async () => {
    try {
        const res = await fetch(`${CONFIG.PYTHON_API}/scores/leaderboard?limit=10`);
        const scores = await res.json();
        
        const list = document.getElementById("leaderboard-list");
        if (!list) return;
        
        list.innerHTML = "";
        scores.forEach((s, index) => {
            const li = document.createElement("li");
            li.innerText = `#${index + 1} - ${s.display_name} : ${s.score}`;
            list.appendChild(li);
        });
    } catch(e) {
        console.error("Failed to load leaderboard", e);
    }
};

// Basic HTML Bindings:
// document.getElementById('login-btn')?.addEventListener('click', loginWithGoogle);
// document.getElementById('logout-btn')?.addEventListener('click', logoutUser);
// document.getElementById('trigger-game-over-btn')?.addEventListener('click', () => handleGameOver(100));

// Call initialization
// initGameFirebase();
