import sys

file_path = r'c:\xampp\htdocs\match-game\index.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """    <!-- ── START GAME (hero button) ── -->
    <button id="start-btn" class="btn-start-hero" onclick="startGame()" aria-label="Start Game">
      Start Game
    </button>"""
replacement1 = """    <!-- ── START GAME (hero button) ── -->
    <div style="display:flex; gap:10px; justify-content:center; max-width:520px; width:100%; margin: 0 auto;">
        <button id="start-btn" class="btn-start-hero" onclick="startGame()" aria-label="Start Game" style="flex:1;">
          Start Game
        </button>
        <button id="multiplayer-btn" class="btn-start-hero" onclick="window.startMultiplayer()" aria-label="Multiplayer" style="flex:1; background: linear-gradient(135deg, #10b981, #06b6d4);">
          ⚔️ Multiplayer
        </button>
    </div>"""

target2 = """  <!-- ===================== GAME SCREEN ===================== -->
  <div id="screen-game" class="screen hidden" role="main" aria-label="Game">

    <!-- Preview Overlay -->"""
replacement2 = """  <!-- ===================== GAME SCREEN ===================== -->
  <div id="screen-game" class="screen hidden" role="main" aria-label="Game">

    <!-- Matchmaking Overlay -->
    <div id="matchmaking-overlay" style="display:none; position:fixed; inset:0; background:rgba(15,12,41,0.95); z-index:9999; flex-direction:column; align-items:center; justify-content:center; color:#fff;">
      <h2 style="margin-bottom:20px; font-size: 28px; color:#a78bfa;">⚔️ Matchmaking</h2>
      <div id="matchmaking-status" style="margin-bottom:30px; font-size: 18px;">Connecting to server...</div>
      <button class="btn-secondary" onclick="window.Multiplayer.quitMultiplayer(); document.getElementById('matchmaking-overlay').style.display='none'; goHome();">Cancel</button>
    </div>

    <!-- Preview Overlay -->"""

target3 = """      <div class="game-title-area">
        <div class="game-title" id="game-title-text">Memory Match</div>
        <div class="game-level-info" id="game-level-info"></div>
      </div>"""
replacement3 = """      <div class="game-title-area">
        <div class="game-title" id="game-title-text">Memory Match</div>
        <div class="game-level-info" id="game-level-info"></div>
        <div id="mp-turn-indicator" style="display:none; font-size: 12px; font-weight: bold; color: #10b981;">Your Turn</div>
      </div>"""

target4 = """  <script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js"></script>"""
replacement4 = """  <script type="module">
    import * as Multiplayer from './src/game/multiplayer.js';
    window.Multiplayer = Multiplayer;

    window.startMultiplayer = () => {
        if (!currentUser || currentUser.type === 'guest') {
            alert("Guest accounts cannot play multiplayer. Please log in.");
            return;
        }
        showScreen('screen-game');
        document.getElementById('matchmaking-overlay').style.display = 'flex';
        Multiplayer.startMultiplayerMatchmaking(currentUser.id);
    };

    window.startMultiplayerGame = (data) => {
        state.isMultiplayer = true;
        state.mpP1 = data.p1;
        state.mpP2 = data.p2;
        window.updateTurn(data.turn);

        const themeData = GAME_DATA.themes[state.theme || 'animals'];
        const pool = [...themeData.cards].slice(0, 8); 
        const idMap = {};
        pool.forEach((c, i) => { idMap[i+1] = c; });

        state.cards = data.board.map((id, index) => {
            const baseCard = idMap[id] || { symbol: '❓', id: id, name: 'Unknown' };
            return { ...baseCard, uid: baseCard.id * 1000 + index, _idx: index };
        });

        state.flipped = [];
        state.matched = [];
        state.score = 0;
        state.moves = 0;
        state.health = 100;
        state.canFlip = true;
        state.gameActive = true;
        state.timeLeft = 120;
        clearInterval(state.timerInterval);
        state.timerInterval = setInterval(tickTimer, 1000);

        document.getElementById('game-title-text').innerHTML = `Multiplayer vs ${data.p1 === currentUser.id ? data.p2 : data.p1}`;
        document.getElementById('game-level-info').textContent = `Find the most pairs!`;
        document.getElementById('mp-turn-indicator').style.display = 'block';
        
        updateStatsUI();
        buildCardGrid(4);
        
        setTimeout(() => {
            document.querySelectorAll('.card').forEach(c => c.classList.remove('no-flip-transition', 'preview'));
        }, 100);
    };

    window.updateTurn = (turnUid) => {
        Multiplayer.myTurn = (turnUid === currentUser.id);
        const ind = document.getElementById('mp-turn-indicator');
        if (Multiplayer.myTurn) {
            ind.textContent = "Your Turn";
            ind.style.color = "#10b981";
            state.canFlip = true;
        } else {
            ind.textContent = "Opponent's Turn";
            ind.style.color = "#ef4444";
            state.canFlip = false;
        }
    };

    window.handleOpponentFlip = (data) => {
        if (data.by !== currentUser.id) {
            state.flipped.push(data.card_index);
            const el = document.querySelector(`.card[data-index="${data.card_index}"]`);
            if(el) {
                el.classList.add('flipped');
                AudioEngine.sfxFlip();
            }
        }
    };

    window.handleMatchResult = (data) => {
        const {match, idx1, idx2, p1_score, p2_score} = data;
        const el1 = document.querySelector(`.card[data-index="${idx1}"]`);
        const el2 = document.querySelector(`.card[data-index="${idx2}"]`);
        
        if (match) {
            AudioEngine.sfxMatch();
            state.matched.push(idx1, idx2);
            if(el1) el1.classList.add('matched');
            if(el2) el2.classList.add('matched');
            if (currentUser.id === state.mpP1) state.score = p1_score;
            else state.score = p2_score;
            
            document.getElementById('score-display').textContent = `Me: ${state.score}`;
            document.getElementById('timer-display').textContent = `Op: ${currentUser.id === state.mpP1 ? p2_score : p1_score}`;
            document.getElementById('timer-box').querySelector('.stat-label').textContent = 'OPP. SCORE';
        } else {
            AudioEngine.sfxWrong();
            if(el1) el1.classList.add('wrong');
            if(el2) el2.classList.add('wrong');
            setTimeout(() => {
                if(el1) el1.classList.remove('flipped', 'wrong');
                if(el2) el2.classList.remove('flipped', 'wrong');
            }, 800);
        }
        state.flipped = [];
    };

    window.endMultiplayerGame = (winnerUid) => {
        state.gameActive = false;
        Multiplayer.quitMultiplayer();
        clearInterval(state.timerInterval);
        
        let title = "Draw!";
        if (winnerUid === currentUser.id) title = "You Won!";
        else if (winnerUid !== "draw") title = "You Lost!";
        
        document.getElementById('win-title').textContent = title;
        document.getElementById('win-caption').textContent = "Multiplayer Match Over";
        document.getElementById('win-modal').classList.add('show');
    };

    window.exitGame = () => {
        Multiplayer.quitMultiplayer();
        goHome();
    };

  </script>
  <script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js"></script>"""

target5 = """      AudioEngine.sfxFlip();

      if (state.flipped.length === 2) {"""
replacement5 = """      AudioEngine.sfxFlip();

      if (window.Multiplayer && window.Multiplayer.isMultiplayer) {
          window.Multiplayer.sendFlip(index);
          return;
      }

      if (state.flipped.length === 2) {"""

target6 = """    function goHome() {
      clearInterval(state.timerInterval);"""
replacement6 = """    function goHome() {
      if (window.Multiplayer && window.Multiplayer.isMultiplayer) {
          window.Multiplayer.quitMultiplayer();
          state.isMultiplayer = false;
          document.getElementById('mp-turn-indicator').style.display = 'none';
      }
      clearInterval(state.timerInterval);"""


if target1 in content:
    content = content.replace(target1, replacement1)
    print("Replaced target 1")
else:
    print("Target 1 not found")

if target2 in content:
    content = content.replace(target2, replacement2)
    print("Replaced target 2")
else:
    print("Target 2 not found")

if target3 in content:
    content = content.replace(target3, replacement3)
    print("Replaced target 3")
else:
    print("Target 3 not found")

if target4 in content:
    content = content.replace(target4, replacement4)
    print("Replaced target 4")
else:
    print("Target 4 not found")

if target5 in content:
    content = content.replace(target5, replacement5)
    print("Replaced target 5")
else:
    print("Target 5 not found")

if target6 in content:
    content = content.replace(target6, replacement6)
    print("Replaced target 6")
else:
    print("Target 6 not found")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done modifying index.html")
