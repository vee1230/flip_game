with open(r'c:\xampp\htdocs\match-game\index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the startMultiplayerGame function start
start_line = None
end_line = None
for i, line in enumerate(lines):
    if 'window.startMultiplayerGame = (data) =>' in line:
        start_line = i
    if start_line is not None and i > start_line and line.strip() == '};':
        end_line = i
        break

print(f"Found block: lines {start_line+1} to {end_line+1}")

# Build the replacement block (preserving \r\n endings like the file)
new_block = [
    '    window.startMultiplayerGame = (data) => {\r\n',
    '        state.isMultiplayer = true;\r\n',
    '        state.mpP1 = data.p1;\r\n',
    '        state.mpP2 = data.p2;\r\n',
    '\r\n',
    "        const themeData = GAME_DATA.themes[state.theme || 'animals'];\r\n",
    '        const pool = [...themeData.cards].slice(0, 8);\r\n',
    '        const idMap = {};\r\n',
    '        pool.forEach((c, i) => { idMap[i+1] = c; });\r\n',
    '\r\n',
    '        state.cards = data.board.map((id, index) => {\r\n',
    "            const baseCard = idMap[id] || { symbol: '\u2753', id: id, name: 'Unknown' };\r\n",
    '            return { ...baseCard, uid: baseCard.id * 1000 + index, _idx: index };\r\n',
    '        });\r\n',
    '\r\n',
    '        state.flipped = [];\r\n',
    '        state.matched = [];\r\n',
    '        state.score = 0;\r\n',
    '        state.moves = 0;\r\n',
    '        state.comboCount = 0;\r\n',
    '        state.health = 100;\r\n',
    '        state.paused = false;\r\n',
    '        state.canFlip = true;\r\n',
    '        state.gameActive = true;\r\n',
    '        state.timeLeft = 120;\r\n',
    '        state._flipTimestamps = [];\r\n',
    '        state._scaledDamage = 10;\r\n',
    '        clearInterval(state.timerInterval);\r\n',
    '        state.timerInterval = setInterval(tickTimer, 1000);\r\n',
    '\r\n',
    '        document.getElementById(\'game-title-text\').innerHTML = `Multiplayer vs ${data.p1 === currentUser.id ? data.p2 : data.p1}`;\r\n',
    "        document.getElementById('game-level-info').textContent = `Find the most pairs!`;\r\n",
    "        document.getElementById('mp-turn-indicator').style.display = 'block';\r\n",
    '\r\n',
    '        // Ensure game screen is visible and any lingering modals are cleared\r\n',
    "        showScreen('screen-game');\r\n",
    '        closeAllModals();\r\n',
    '\r\n',
    '        updateStatsUI();\r\n',
    '        buildCardGrid(4);\r\n',
    '\r\n',
    '        // Set turn AFTER buildCardGrid so canFlip state is set correctly\r\n',
    '        window.updateTurn(data.turn);\r\n',
    '    };\r\n',
]

lines[start_line:end_line+1] = new_block

with open(r'c:\xampp\htdocs\match-game\index.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Done! File patched successfully.")
