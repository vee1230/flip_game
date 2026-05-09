/**
 * =====================================================
 * DAILY CHALLENGE MODULE
 * =====================================================
 * Manages Daily Challenge card functionality:
 * - Modal popup with challenge details
 * - Challenge initialization and tracking
 * - Reward claiming and backend integration
 * - Daily reset logic
 */

// Challenge configuration
const DAILY_CHALLENGE_CONFIG = {
  objective: 'Complete Easy Mode with at least 3 matched pairs',
  mode: 'easy',
  requiredMatches: 3,
  reward: 50, // Stars
  title: 'Daily Challenge',
};

// Challenge state in localStorage key
const DAILY_CHALLENGE_KEY = 'mmPuzzleDailyChallenge';
const DAILY_CHALLENGE_STATUS_KEY = 'mmPuzzleDailyChallengeStatus';

/**
 * Initialize Daily Challenge on page load
 * Fetches status from backend and updates UI
 */
export async function initDailyChallenge() {
  try {
    // Load challenge status from localStorage or backend
    const status = await getDailyChallengeStatus();
    updateDailyChallengeUI(status);
  } catch (error) {
    console.error('Failed to initialize daily challenge:', error);
  }
}

/**
 * Get daily challenge status from backend or localStorage cache
 */
async function getDailyChallengeStatus() {
  const currentUser = window.currentUser || JSON.parse(localStorage.getItem('mmPuzzleSession') || '{}');
  
  if (!currentUser.uid) {
    // Not logged in, use guest localStorage
    return getLocalDailyChallengeStatus();
  }

  try {
    // Fetch from backend
    const response = await fetch(`${window.CONFIG?.PYTHON_API || 'http://localhost:8000'}/daily-challenge/status/${currentUser.uid}`);
    if (!response.ok) throw new Error('Failed to fetch status');
    
    const data = await response.json();
    if (data.status === 'success') {
      // Cache in localStorage
      localStorage.setItem(DAILY_CHALLENGE_STATUS_KEY, JSON.stringify(data.data));
      return data.data;
    }
  } catch (error) {
    console.warn('Backend status fetch failed, using localStorage:', error);
  }

  // Fallback to localStorage
  return getLocalDailyChallengeStatus();
}

/**
 * Get local daily challenge status from localStorage
 */
function getLocalDailyChallengeStatus() {
  const stored = localStorage.getItem(DAILY_CHALLENGE_STATUS_KEY);
  if (!stored) {
    return {
      is_completed: false,
      is_claimed: false,
      date: getTodayDate(),
    };
  }

  const data = JSON.parse(stored);
  
  // Auto-reset if date changed
  if (data.date !== getTodayDate()) {
    return {
      is_completed: false,
      is_claimed: false,
      date: getTodayDate(),
    };
  }

  return data;
}

/**
 * Get today's date as YYYY-MM-DD string
 */
function getTodayDate() {
  const today = new Date();
  return today.toISOString().split('T')[0];
}

/**
 * Update Daily Challenge card UI based on status
 */
function updateDailyChallengeUI(status) {
  const card = document.getElementById('home-daily-challenge');
  if (!card) return;

  const titleEl = document.getElementById('dc-title');
  const descEl = document.getElementById('dc-desc');
  const rewardEl = document.getElementById('dc-reward');
  const iconEl = document.getElementById('dc-icon');

  if (status.is_claimed) {
    // Challenge completed and claimed
    card.classList.add('completed');
    if (iconEl) iconEl.textContent = '✅';
    if (titleEl) titleEl.textContent = 'Daily Challenge';
    if (descEl) descEl.textContent = 'Completed! Come back tomorrow.';
    if (rewardEl) rewardEl.textContent = 'Claimed ✓';
    card.style.pointerEvents = 'none';
    card.style.opacity = '0.6';
  } else if (status.is_completed) {
    // Challenge completed, reward ready to claim
    card.classList.add('reward-ready');
    if (iconEl) iconEl.textContent = '🎁';
    if (titleEl) titleEl.textContent = 'Reward Ready!';
    if (descEl) descEl.textContent = 'Click to claim your +50 Stars';
    if (rewardEl) rewardEl.textContent = '+50 Stars';
  } else {
    // Challenge available
    card.classList.remove('completed', 'reward-ready');
    if (iconEl) iconEl.textContent = '⭐';
    if (titleEl) titleEl.textContent = DAILY_CHALLENGE_CONFIG.objective;
    if (descEl) descEl.textContent = 'Complete Easy Mode and match 3+ pairs';
    if (rewardEl) rewardEl.textContent = '+50 Stars';
    card.style.pointerEvents = 'auto';
    card.style.opacity = '1';
  }
}

/**
 * Show Daily Challenge modal with details
 */
export function showDailyChallengeModal() {
  const modal = document.getElementById('daily-challenge-modal');
  if (!modal) {
    console.error('Daily Challenge modal not found in DOM');
    return;
  }

  const status = JSON.parse(localStorage.getItem(DAILY_CHALLENGE_STATUS_KEY) || '{}');

  // Update modal content based on status
  if (status.is_claimed) {
    showCompletedModal();
  } else if (status.is_completed) {
    showClaimRewardModal();
  } else {
    showChallengeDetailsModal();
  }

  modal.classList.add('show');
}

/**
 * Show challenge details modal
 */
function showChallengeDetailsModal() {
  const titleEl = document.getElementById('challenge-modal-title');
  const objectiveEl = document.getElementById('challenge-modal-objective');
  const howtoEl = document.getElementById('challenge-modal-howto');
  const rewardEl = document.getElementById('challenge-modal-reward');
  const startBtn = document.getElementById('challenge-start-btn');
  const claimBtn = document.getElementById('challenge-claim-btn');
  const closeBtn = document.getElementById('challenge-close-btn');

  if (titleEl) titleEl.textContent = 'Daily Challenge';
  if (objectiveEl) objectiveEl.textContent = DAILY_CHALLENGE_CONFIG.objective;
  if (howtoEl) {
    howtoEl.innerHTML = `
      <strong>How to complete:</strong><br>
      Play Easy Mode and match <strong>${DAILY_CHALLENGE_CONFIG.requiredMatches} pairs</strong> before the timer runs out.
    `;
  }
  if (rewardEl) rewardEl.innerHTML = `<strong>Reward:</strong> +${DAILY_CHALLENGE_CONFIG.reward} Stars ⭐`;

  // Show start button, hide claim button
  if (startBtn) startBtn.style.display = 'inline-block';
  if (claimBtn) claimBtn.style.display = 'none';

  // Event listeners
  if (startBtn) {
    startBtn.onclick = () => {
      closeDailyChallengeModal();
      startDailyChallenge();
    };
  }
  if (closeBtn) {
    closeBtn.onclick = () => closeDailyChallengeModal();
  }
}

/**
 * Show "Claim Reward" modal when challenge is completed
 */
function showClaimRewardModal() {
  const titleEl = document.getElementById('challenge-modal-title');
  const objectiveEl = document.getElementById('challenge-modal-objective');
  const howtoEl = document.getElementById('challenge-modal-howto');
  const rewardEl = document.getElementById('challenge-modal-reward');
  const startBtn = document.getElementById('challenge-start-btn');
  const claimBtn = document.getElementById('challenge-claim-btn');
  const closeBtn = document.getElementById('challenge-close-btn');

  if (titleEl) titleEl.textContent = '🎉 Challenge Complete!';
  if (objectiveEl) objectiveEl.textContent = 'You have successfully completed today\'s challenge!';
  if (howtoEl) howtoEl.innerHTML = `
    <strong>Reward Status:</strong><br>
    Ready to claim your <strong>+${DAILY_CHALLENGE_CONFIG.reward} Stars</strong> bonus!
  `;
  if (rewardEl) rewardEl.innerHTML = `<strong>Claim Now:</strong> +${DAILY_CHALLENGE_CONFIG.reward} Stars ⭐`;

  // Show claim button, hide start button
  if (startBtn) startBtn.style.display = 'none';
  if (claimBtn) claimBtn.style.display = 'inline-block';

  if (claimBtn) {
    claimBtn.onclick = () => {
      claimDailyReward();
    };
  }
  if (closeBtn) {
    closeBtn.onclick = () => closeDailyChallengeModal();
  }
}

/**
 * Show "Completed" modal when reward already claimed
 */
function showCompletedModal() {
  const titleEl = document.getElementById('challenge-modal-title');
  const objectiveEl = document.getElementById('challenge-modal-objective');
  const howtoEl = document.getElementById('challenge-modal-howto');
  const rewardEl = document.getElementById('challenge-modal-reward');
  const startBtn = document.getElementById('challenge-start-btn');
  const claimBtn = document.getElementById('challenge-claim-btn');
  const closeBtn = document.getElementById('challenge-close-btn');

  if (titleEl) titleEl.textContent = '✅ Challenge Completed';
  if (objectiveEl) objectiveEl.textContent = 'You\'ve completed today\'s challenge!';
  if (howtoEl) howtoEl.innerHTML = `
    <strong>Reward Claimed:</strong> +${DAILY_CHALLENGE_CONFIG.reward} Stars ⭐<br><br>
    <em>Come back tomorrow for a new challenge!</em>
  `;
  if (rewardEl) rewardEl.innerHTML = `<strong>Status:</strong> Claimed ✓`;

  // Hide both buttons
  if (startBtn) startBtn.style.display = 'none';
  if (claimBtn) claimBtn.style.display = 'none';

  if (closeBtn) {
    closeBtn.onclick = () => closeDailyChallengeModal();
  }
}

/**
 * Close Daily Challenge modal
 */
export function closeDailyChallengeModal() {
  const modal = document.getElementById('daily-challenge-modal');
  if (modal) {
    modal.classList.remove('show');
  }
}

/**
 * Start Daily Challenge game (Easy Mode with challenge tracking)
 */
function startDailyChallenge() {
  // Mark challenge as active in window scope
  window.dailyChallengeActive = true;
  window.dailyChallengeMatches = 0;
  window.dailyChallengeCompleted = false;

  // Set game mode to Easy
  if (window.state) {
    window.state.difficulty = 'easy';
  }

  // Call main startGame function
  if (window.startGame) {
    window.startGame();
  }
}

/**
 * Track matched pairs during challenge gameplay
 * Called from checkMatch() in game.js when a pair is matched
 */
export function trackChallengeMatch() {
  if (!window.dailyChallengeActive) return;

  window.dailyChallengeMatches = (window.dailyChallengeMatches || 0) + 1;

  // Check if challenge is completed
  if (window.dailyChallengeMatches >= DAILY_CHALLENGE_CONFIG.requiredMatches) {
    window.dailyChallengeCompleted = true;
    console.log(`✅ Daily Challenge Completed! Matched ${window.dailyChallengeMatches} pairs.`);
  }

  // Update progress in UI if available
  updateChallengeProgressUI();
}

/**
 * Update challenge progress display during gameplay
 */
function updateChallengeProgressUI() {
  const progressEl = document.getElementById('challenge-progress');
  if (progressEl && window.dailyChallengeActive) {
    const matched = window.dailyChallengeMatches || 0;
    const required = DAILY_CHALLENGE_CONFIG.requiredMatches;
    progressEl.textContent = `Challenge Progress: ${matched}/${required} pairs`;
    progressEl.style.display = 'block';

    if (matched >= required) {
      progressEl.style.color = '#10b981'; // Green
      progressEl.textContent = `✅ Challenge Complete! ${matched}/${required} pairs`;
    }
  }
}

/**
 * Mark challenge as completed on game win
 * Called from showWin() in game.js
 */
export async function markChallengeCompleted() {
  if (!window.dailyChallengeActive || !window.dailyChallengeCompleted) return;

  try {
    const currentUser = window.currentUser || JSON.parse(localStorage.getItem('mmPuzzleSession') || '{}');
    
    if (!currentUser.uid) {
      // Guest user - just update localStorage
      const status = JSON.parse(localStorage.getItem(DAILY_CHALLENGE_STATUS_KEY) || '{}');
      status.is_completed = true;
      status.matched_pairs = window.dailyChallengeMatches;
      status.completed_at = new Date().toISOString();
      localStorage.setItem(DAILY_CHALLENGE_STATUS_KEY, JSON.stringify(status));
      return;
    }

    // Authenticated user - send to backend
    const response = await fetch(`${window.CONFIG?.PYTHON_API || 'http://localhost:8000'}/daily-challenge/complete/${currentUser.uid}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        difficulty: 'easy',
        matched_pairs: window.dailyChallengeMatches,
        is_completed: true,
      }),
    });

    if (response.ok) {
      const data = await response.json();
      if (data.status === 'success') {
        // Update localStorage cache
        localStorage.setItem(DAILY_CHALLENGE_STATUS_KEY, JSON.stringify(data.data));
      }
    }
  } catch (error) {
    console.error('Failed to mark challenge completed:', error);
  }
}

/**
 * Claim daily challenge reward
 * Awards +50 Stars and marks reward as claimed
 */
async function claimDailyReward() {
  try {
    const currentUser = window.currentUser || JSON.parse(localStorage.getItem('mmPuzzleSession') || '{}');
    
    if (!currentUser.uid) {
      // Guest user - just update localStorage
      const status = JSON.parse(localStorage.getItem(DAILY_CHALLENGE_STATUS_KEY) || '{}');
      status.is_claimed = true;
      localStorage.setItem(DAILY_CHALLENGE_STATUS_KEY, JSON.stringify(status));
      showRewardClaimedAnimation();
      closeDailyChallengeModal();
      updateDailyChallengeUI(status);
      return;
    }

    // Authenticated user - send to backend
    const response = await fetch(`${window.CONFIG?.PYTHON_API || 'http://localhost:8000'}/daily-challenge/claim/${currentUser.uid}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });

    if (response.ok) {
      const data = await response.json();
      if (data.status === 'success') {
        // Update localStorage cache
        localStorage.setItem(DAILY_CHALLENGE_STATUS_KEY, JSON.stringify(data.data));
        
        // Show reward animation
        showRewardClaimedAnimation();
        
        // Update UI
        updateDailyChallengeUI(data.data);
        
        // Update trophy display if available
        if (data.data.new_trophy_balance) {
          updateTrophyDisplay(data.data.new_trophy_balance);
        }
        
        closeDailyChallengeModal();
      }
    } else {
      const error = await response.json();
      alert(`Failed to claim reward: ${error.detail || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Failed to claim reward:', error);
    alert('Failed to claim reward. Please try again.');
  }
}

/**
 * Show reward claimed animation (confetti-like effect)
 */
function showRewardClaimedAnimation() {
  // Create a simple celebration element
  const celebration = document.createElement('div');
  celebration.style.cssText = `
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 80px;
    z-index: 9999;
    animation: pop-burst 1s ease-out forwards;
    pointer-events: none;
  `;
  celebration.textContent = '⭐';
  document.body.appendChild(celebration);

  setTimeout(() => celebration.remove(), 1000);

  // Add CSS animation if not already present
  if (!document.getElementById('reward-animation-style')) {
    const style = document.createElement('style');
    style.id = 'reward-animation-style';
    style.textContent = `
      @keyframes pop-burst {
        0% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
        100% { opacity: 0; transform: translate(-50%, -150%) scale(2); }
      }
    `;
    document.head.appendChild(style);
  }
}

/**
 * Update trophy/star display in header
 */
function updateTrophyDisplay(newBalance) {
  const trophyEl = document.getElementById('trophy-display');
  if (trophyEl) {
    trophyEl.textContent = newBalance;
  }
}

/**
 * Reset challenge state after game ends
 * Called from goHome() or when closing game
 */
export function resetDailyChallenge() {
  window.dailyChallengeActive = false;
  window.dailyChallengeMatches = 0;
  window.dailyChallengeCompleted = false;

  // Hide progress UI
  const progressEl = document.getElementById('challenge-progress');
  if (progressEl) {
    progressEl.style.display = 'none';
  }
}

/**
 * Update win/lose modal to show challenge status
 */
export function updateGameOverModalWithChallengeStatus(modalId) {
  if (!window.dailyChallengeActive) return;

  const modal = document.getElementById(modalId);
  if (!modal) return;

  // Insert challenge status message in modal
  let message = '';
  if (window.dailyChallengeCompleted) {
    message = `<div style="color:#10b981; margin-top:12px; padding:8px; background:rgba(16,185,129,0.1); border-radius:8px; font-weight:700;">✅ Daily Challenge Completed! Ready to claim +50 Stars</div>`;
  } else {
    const matched = window.dailyChallengeMatches || 0;
    const required = DAILY_CHALLENGE_CONFIG.requiredMatches;
    if (matched > 0) {
      message = `<div style="color:#f59e0b; margin-top:12px; padding:8px; background:rgba(245,158,11,0.1); border-radius:8px; font-weight:600;">Daily Challenge Progress: ${matched}/${required} pairs</div>`;
    }
  }

  if (message) {
    const modalBox = modal.querySelector('.modal-box');
    if (modalBox) {
      let statusDiv = modalBox.querySelector('#challenge-status-message');
      if (!statusDiv) {
        statusDiv = document.createElement('div');
        statusDiv.id = 'challenge-status-message';
        // Insert after modal-caption
        const caption = modalBox.querySelector('.modal-caption');
        if (caption) {
          caption.parentNode.insertBefore(statusDiv, caption.nextSibling);
        } else {
          modalBox.insertBefore(statusDiv, modalBox.querySelector('.modal-actions'));
        }
      }
      statusDiv.innerHTML = message;
    }
  }
}

/**
 * Global function for onclick handler in HTML
 * (since arrow functions don't work in HTML onclick attributes)
 */
window.startDailyChallenge = () => {
  showDailyChallengeModal();
};
