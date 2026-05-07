import json
import random
import asyncio
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import get_db

router = APIRouter()

ROUNDS_TO_WIN = 3
TOTAL_PAIRS = 8


class GameSession:
    def __init__(self, room_id: str, p1_uid: str, p2_uid: str,
                 p1_ws: WebSocket, p2_ws: WebSocket,
                 p1_name: str, p2_name: str):
        self.room_id = room_id
        self.p1_uid = p1_uid
        self.p2_uid = p2_uid
        # Per-player state: independent flipping & matching
        self.players = {
            p1_uid: {"ws": p1_ws, "name": p1_name, "rounds_won": 0,
                     "flipped": [], "matched": set()},
            p2_uid: {"ws": p2_ws, "name": p2_name, "rounds_won": 0,
                     "flipped": [], "matched": set()},
        }
        self.board = self._generate_board()
        self.round_in_progress = True  # guards against double round-claim

    # ── Helpers ──────────────────────────────────────────────────
    def _generate_board(self):
        cards = list(range(1, TOTAL_PAIRS + 1)) * 2
        random.shuffle(cards)
        return cards

    def opponent_of(self, uid: str) -> str:
        return self.p2_uid if uid == self.p1_uid else self.p1_uid

    async def broadcast(self, message: dict):
        for p in self.players.values():
            try:
                await p["ws"].send_text(json.dumps(message))
            except Exception:
                pass

    async def send_to(self, uid: str, message: dict):
        if uid in self.players:
            try:
                await self.players[uid]["ws"].send_text(json.dumps(message))
            except Exception:
                pass

    def _reset_round(self):
        self.board = self._generate_board()
        for p in self.players.values():
            p["flipped"] = []
            p["matched"] = set()

    # ── Trophy DB update ─────────────────────────────────────────
    async def _update_trophies(self, winner_uid: str, loser_uid: str):
        """Award +10 to winner, deduct -10 from loser (floor 0). Returns (p1_trophies, p2_trophies)."""
        def _db_op():
            db = get_db()
            p1_t, p2_t = 0, 0
            try:
                with db.cursor() as cursor:
                    # Atomic updates are safer and faster
                    cursor.execute("UPDATE players SET trophies = trophies + 10 WHERE id=%s OR google_uid=%s", (winner_uid, winner_uid))
                    cursor.execute("UPDATE players SET trophies = GREATEST(0, trophies - 10) WHERE id=%s OR google_uid=%s", (loser_uid, loser_uid))
                    db.commit()
                    
                    # Fetch new totals
                    cursor.execute("SELECT trophies FROM players WHERE id=%s OR google_uid=%s", (self.p1_uid, self.p1_uid))
                    r1 = cursor.fetchone()
                    p1_t = r1['trophies'] if r1 else 0
                    
                    cursor.execute("SELECT trophies FROM players WHERE id=%s OR google_uid=%s", (self.p2_uid, self.p2_uid))
                    r2 = cursor.fetchone()
                    p2_t = r2['trophies'] if r2 else 0
                return p1_t, p2_t
            except Exception as e:
                print(f"[MP] Trophy update error: {e}")
                return 0, 0
            finally:
                db.close()

        # Run blocking DB operations in a thread pool to avoid freezing the event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _db_op)

    # ── Core flip handler ─────────────────────────────────────────
    async def handle_flip(self, uid: str, card_idx: int, manager: "ConnectionManager"):
        ps = self.players[uid]
        opp_uid = self.opponent_of(uid)
        opp_ps = self.players[opp_uid]

        # --- validate ---
        if not self.round_in_progress:
            return
        if card_idx < 0 or card_idx >= len(self.board):
            return
        if card_idx in ps["matched"]:
            return
        if card_idx in ps["flipped"]:
            return
        if len(ps["flipped"]) >= 2:
            return

        ps["flipped"].append(card_idx)

        # Broadcast the flip so opponent can see "what's happening"
        # Security: Do not send card_value here to prevent cheating.
        await self.broadcast({
            "type": "card_flipped",
            "card_index": card_idx,
            "by": uid,
        })

        if len(ps["flipped"]) < 2:
            return  # wait for second card

        idx1, idx2 = ps["flipped"]
        val1, val2 = self.board[idx1], self.board[idx2]
        is_match = (val1 == val2) and (idx1 != idx2)

        await asyncio.sleep(1.0)

        # After sleep, check round still live
        if not self.round_in_progress:
            ps["flipped"] = []
            return

        opp_pairs = len(opp_ps["matched"]) // 2

        if is_match:
            ps["matched"].add(idx1)
            ps["matched"].add(idx2)
            my_pairs = len(ps["matched"]) // 2

            # Personalized match_result for sender
            await self.send_to(uid, {
                "type": "match_result",
                "match": True,
                "idx1": idx1, "idx2": idx2,
                "val": val1,  # Send value only on match
                "my_pairs": my_pairs,
                "opp_pairs": opp_pairs,
            })
            # Opponent sees the flip result (cards stay shown briefly)
            await self.send_to(opp_uid, {
                "type": "match_result",
                "match": True,
                "idx1": idx1, "idx2": idx2,
                "val": val1,
                "by": uid,
                "my_pairs": opp_pairs,
                "opp_pairs": my_pairs,
            })

            # Check for round win (guard against double-claim)
            if my_pairs >= TOTAL_PAIRS and self.round_in_progress:
                self.round_in_progress = False  # claim atomically (single asyncio thread)
                ps["rounds_won"] += 1
                p1_rounds = self.players[self.p1_uid]["rounds_won"]
                p2_rounds = self.players[self.p2_uid]["rounds_won"]

                await self.broadcast({
                    "type": "round_over",
                    "round_winner": uid,
                    "round_winner_name": ps["name"],
                    "p1_rounds": p1_rounds,
                    "p2_rounds": p2_rounds,
                })

                if p1_rounds >= ROUNDS_TO_WIN or p2_rounds >= ROUNDS_TO_WIN:
                    # Match over — update trophies
                    loser_uid = opp_uid
                    p1_trophies, p2_trophies = await self._update_trophies(uid, loser_uid)
                    await self.broadcast({
                        "type": "game_over",
                        "winner": uid,
                        "p1_trophies": p1_trophies,
                        "p2_trophies": p2_trophies,
                    })
                    # Cleanup handled by manager
                    await manager.cleanup_game(self.room_id)
                else:
                    # Next round — wait 3s then reset
                    await asyncio.sleep(3.0)
                    self._reset_round()
                    await self.broadcast({
                        "type": "new_round",
                        "board": self.board,
                        "p1_rounds": self.players[self.p1_uid]["rounds_won"],
                        "p2_rounds": self.players[self.p2_uid]["rounds_won"],
                    })
                    self.round_in_progress = True
        else:
            # No match
            my_pairs = len(ps["matched"]) // 2
            await self.send_to(uid, {
                "type": "match_result",
                "match": False,
                "idx1": idx1, "idx2": idx2,
                "my_pairs": my_pairs,
                "opp_pairs": opp_pairs,
            })
            await self.send_to(opp_uid, {
                "type": "match_result",
                "match": False,
                "idx1": idx1, "idx2": idx2,
                "by": uid,
                "my_pairs": opp_pairs,
                "opp_pairs": my_pairs,
            })

        ps["flipped"] = []


# ── Connection Manager ────────────────────────────────────────────


class ConnectionManager:
    def __init__(self):
        self.lobby: Dict[str, dict] = {}
        self.pending_challenges: Dict[str, str] = {}
        self.active_games: Dict[str, GameSession] = {}
        self.user_to_room: Dict[str, str] = {}
        self.room_counter = 0

    def _lobby_snapshot(self):
        return [
            {"uid": uid, "display_name": p["display_name"], "avatar": p["avatar"]}
            for uid, p in self.lobby.items()
        ]

    async def _broadcast_lobby(self):
        snapshot = self._lobby_snapshot()
        print(f"[LOBBY] Snapshot: {snapshot}", flush=True)
        print(f"[LOBBY] Broadcasting to {len(self.lobby)} players. Snapshot size: {len(snapshot)}", flush=True)
        for uid, p in list(self.lobby.items()):
            try:
                await p["ws"].send_text(json.dumps({
                    "type": "lobby_update",
                    "players": [pl for pl in snapshot if pl["uid"] != uid]
                }))
            except Exception:
                pass

    # ── Connection lifecycle ──────────────────────────────────────
    async def connect(self, websocket: WebSocket, uid: str,
                      display_name: str, avatar: str):
        await websocket.accept()

        if uid in self.user_to_room:
            room_id = self.user_to_room[uid]
            if room_id in self.active_games:
                self.active_games[room_id].players[uid]["ws"] = websocket
            return

        self.lobby[uid] = {
            "ws": websocket,
            "display_name": display_name,
            "avatar": avatar,
            "status": "lobby",
        }
        snapshot = [pl for pl in self._lobby_snapshot() if pl["uid"] != uid]
        await websocket.send_text(json.dumps({"type": "lobby_update", "players": snapshot}))
        await self._broadcast_lobby()

    async def cleanup_game(self, room_id: str):
        if room_id not in self.active_games:
            return
        session = self.active_games.pop(room_id)
        for puid in [session.p1_uid, session.p2_uid]:
            self.user_to_room.pop(puid, None)
            if puid in self.lobby:
                self.lobby[puid]["status"] = "lobby"
        await self._broadcast_lobby()

    async def disconnect(self, uid: str):
        for challenger, challenged in list(self.pending_challenges.items()):
            if challenger == uid or challenged == uid:
                other = challenged if challenger == uid else challenger
                del self.pending_challenges[challenger]
                if other in self.lobby:
                    try:
                        await self.lobby[other]["ws"].send_text(json.dumps({
                            "type": "challenge_cancelled", "from_uid": uid
                        }))
                    except Exception:
                        pass

        room_id = self.user_to_room.get(uid)
        if room_id and room_id in self.active_games:
            session = self.active_games[room_id]
            other_uid = session.opponent_of(uid)
            await session.send_to(other_uid, {"type": "opponent_disconnected"})
            await self.cleanup_game(room_id)

        self.lobby.pop(uid, None)
        await self._broadcast_lobby()

    # ── Challenge flow ────────────────────────────────────────────
    async def send_challenge(self, challenger_uid: str, target_uid: str):
        if target_uid not in self.lobby:
            if challenger_uid in self.lobby:
                await self.lobby[challenger_uid]["ws"].send_text(json.dumps({
                    "type": "challenge_error", "message": "Player is no longer available."
                }))
            return
        if self.lobby[target_uid]["status"] == "in_game":
            await self.lobby[challenger_uid]["ws"].send_text(json.dumps({
                "type": "challenge_error", "message": "That player is already in a game."
            }))
            return
        self.pending_challenges[challenger_uid] = target_uid
        challenger_info = self.lobby[challenger_uid]
        await self.lobby[target_uid]["ws"].send_text(json.dumps({
            "type": "challenge_received",
            "from_uid": challenger_uid,
            "from_name": challenger_info["display_name"],
            "from_avatar": challenger_info["avatar"],
        }))

    async def respond_challenge(self, responder_uid: str,
                                challenger_uid: str, accept: bool):
        if self.pending_challenges.get(challenger_uid) != responder_uid:
            return
        del self.pending_challenges[challenger_uid]

        if not accept:
            if challenger_uid in self.lobby:
                await self.lobby[challenger_uid]["ws"].send_text(json.dumps({
                    "type": "challenge_declined",
                    "from_uid": responder_uid,
                    "from_name": self.lobby.get(responder_uid, {}).get("display_name", "Opponent"),
                }))
            return

        if challenger_uid not in self.lobby or responder_uid not in self.lobby:
            return

        p1_uid, p2_uid = challenger_uid, responder_uid
        p1_ws = self.lobby[p1_uid]["ws"]
        p2_ws = self.lobby[p2_uid]["ws"]
        p1_name = self.lobby[p1_uid]["display_name"]
        p2_name = self.lobby[p2_uid]["display_name"]

        self.room_counter += 1
        room_id = f"room_{self.room_counter}"
        session = GameSession(room_id, p1_uid, p2_uid, p1_ws, p2_ws, p1_name, p2_name)
        self.active_games[room_id] = session
        self.user_to_room[p1_uid] = room_id
        self.user_to_room[p2_uid] = room_id
        self.lobby[p1_uid]["status"] = "in_game"
        self.lobby[p2_uid]["status"] = "in_game"

        await session.broadcast({
            "type": "match_found",
            "room_id": room_id,
            "p1": p1_uid, "p1_name": p1_name,
            "p2": p2_uid, "p2_name": p2_name,
            "board": session.board,
            # No 'turn' — race mode is simultaneous
        })

    # ── In-game message handling ──────────────────────────────────
    async def handle_message(self, uid: str, message: dict):
        action = message.get("action")

        if action == "challenge":
            await self.send_challenge(uid, message.get("target_uid", ""))
            return
        if action == "respond_challenge":
            await self.respond_challenge(
                responder_uid=uid,
                challenger_uid=message.get("challenger_uid", ""),
                accept=message.get("accept", False),
            )
            return

        room_id = self.user_to_room.get(uid)
        if not room_id or room_id not in self.active_games:
            return

        session = self.active_games[room_id]

        if action == "flip":
            card_idx = message.get("card_index")
            if card_idx is not None:
                await session.handle_flip(uid, card_idx, self)


manager = ConnectionManager()


@router.websocket("/ws/{uid:path}")
async def websocket_endpoint(websocket: WebSocket, uid: str):
    print(f"[WS] Attempting connection for UID: {uid}", flush=True)
    display_name = websocket.query_params.get("name", uid)
    avatar = websocket.query_params.get("avatar", "")
    print(f"[WS] Params: name={display_name}, avatar={avatar}", flush=True)
    await manager.connect(websocket, uid, display_name, avatar)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await manager.handle_message(uid, message)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await manager.disconnect(uid)
