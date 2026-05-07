import { CONFIG } from '../config.js';
export let ws = null;
export let isMultiplayer = false;

let _uid = null;
let _reconnectTimer = null;
let _displayName = null;
let _avatar = null;

export const startLobby = (uid, displayName, avatar) => {
    _uid = uid;
    _displayName = displayName;
    _avatar = avatar;
    if (ws) ws.close();
    clearTimeout(_reconnectTimer);

    const encodedName = encodeURIComponent(displayName || uid);
    const encodedAvatar = encodeURIComponent(avatar || '');
    const encodedUid = encodeURIComponent(uid);

    // Detect environment: use local WS for localhost, production WSS for deployed
    const wsBase = CONFIG.WS_URL;
    ws = new WebSocket(`${wsBase}/api/v1/multiplayer/ws/${encodedUid}?name=${encodedName}&avatar=${encodedAvatar}`);

    ws.onopen = () => {
        console.log('[MP] Connected to lobby');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        switch (data.type) {
            case 'lobby_update':
                if (window.onLobbyUpdate) window.onLobbyUpdate(data.players);
                break;
            case 'challenge_received':
                if (window.onChallengeReceived) window.onChallengeReceived(data);
                break;
            case 'challenge_cancelled':
                if (window.onChallengeCancelled) window.onChallengeCancelled(data);
                break;
            case 'challenge_declined':
                if (window.onChallengeDeclined) window.onChallengeDeclined(data);
                break;
            case 'challenge_error':
                if (window.onChallengeError) window.onChallengeError(data.message);
                break;
            case 'match_found':
                isMultiplayer = true;
                if (window.startMultiplayerGame) window.startMultiplayerGame(data);
                break;
            case 'card_flipped':
                if (window.handleOpponentFlip) window.handleOpponentFlip(data);
                break;
            case 'match_result':
                if (window.handleMatchResult) window.handleMatchResult(data);
                break;
            case 'round_over':
                if (window.onRoundOver) window.onRoundOver(data);
                break;
            case 'new_round':
                if (window.onNewRound) window.onNewRound(data);
                break;
            case 'game_over':
                if (window.endMultiplayerGame) window.endMultiplayerGame(data);
                break;
            case 'opponent_disconnected':
                if (window.onOpponentDisconnected) window.onOpponentDisconnected();
                else { alert('Opponent disconnected!'); if (window.exitGame) window.exitGame(); }
                break;
        }
    };

    ws.onclose = () => {
        console.log('[MP] WebSocket closed');
        if (_uid && !isMultiplayer) {
            _reconnectTimer = setTimeout(() => {
                if (_uid) startLobby(_uid, _displayName, _avatar);
            }, 3000);
        }
    };

    ws.onerror = (err) => {
        console.error('[MP] WebSocket error:', err);
    };
};

export const sendChallenge = (targetUid) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'challenge', target_uid: targetUid }));
    }
};

export const respondChallenge = (challengerUid, accept) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'respond_challenge', challenger_uid: challengerUid, accept }));
    }
};

export const sendFlip = (cardIndex) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'flip', card_index: cardIndex }));
    }
};

export const quitMultiplayer = () => {
    _uid = null;
    clearTimeout(_reconnectTimer);
    isMultiplayer = false;
    if (ws) {
        ws.close();
        ws = null;
    }
};

// Legacy alias kept for backward compatibility
export const startMultiplayerMatchmaking = startLobby;
