"""The FliperOS Matchmaker server: identity, presence, the counts per game
and the room of a game (phase 1), the online parties and the relay's
credentials (phase 2), over a WebSocket.

It runs on Coolify, behind the Cloudflare Tunnel of the server (the tunnel
passes WebSockets; the server opens no UDP port: STUN and the relay are
Cloudflare's).

    GET /health   -> 200 "ok"
    GET /pubkey   -> the public key the profiles are signed with ({"kid", "alg", "public"})
    GET /ws       -> the WebSocket (one JSON object per message)

Client to server:
    {"t": "hello", "v": 1, "secret": "<64 hex>", "nick": "MANGO", "conn": "cable"}
    {"t": "presence", "state": "looking", "game": "mame:sf2ce", "emu": "groovymame",
     "conn": "cable", "rtt": 28, "group": "m42", "kind": "match", "score": "2-1", "pct": null}
    {"t": "watch", "game": "mame:sf2ce"}           (null: stop)
    {"t": "ping", "n": 1}
    {"t": "party", "op": "open", "game": "mame:sf2ce", "emu": "groovymame", "max": 4}
    {"t": "party", "op": "join", "party": "p2a"}
    {"t": "party", "op": "leave"}
    {"t": "party", "op": "lock", "open": false}  (the host: no more cabinets)
    {"t": "signal", "to": 7, "data": {...}}        (to another cabinet of the party)
    {"t": "turn"}                                  (relay credentials, in a party)
    {"t": "turn", "op": "used", "username": "...", "bytes": 123456}
Server to client:
    {"t": "welcome", "id": 7, "nick": "MANGO", "tag": "a7k2"}
    {"t": "profile", "profile": {"kid", "payload", "sig"}}   (right after welcome, and on {"t": "profile"})
    {"t": "error", "code": "banned" | "nick" | "secret" | "signups" | "hello" | "version"}
    {"t": "counts", "games": {"mame:sf2ce": {"players": 5, "looking": 2}}}
    {"t": "room", "game": "mame:sf2ce", "players": [...]}
    {"t": "pong", "n": 1}
    {"t": "party", "op": "opened", "party": "p2a", "addr": "10.207.0.1", "net": "10.207.0.0/24", ...}
    {"t": "party", "op": "joined", "party": "p2a", "addr": "10.207.0.2", ..., "host": {player, "addr"}, "members": [...]}
    {"t": "party", "op": "member", "party": "p2a", "peer": {player, "addr"}}  (to the others: a new one)
    {"t": "party", "op": "left", "party": "p2a", "id": 9}                     (to the others)
    {"t": "party", "op": "closed", "party": "p2a"}                           (the host left)
    {"t": "party", "op": "error", "code": "gone" | "full" | "closed" | "busy" | "nets" | "bad"}
    {"t": "signal", "from": 7, "data": {...}}
    {"t": "turn", "ice": {"urls", "username", "credential", "ttl"}}  or  {"t": "turn", "error": "off" | "cap" | ...}
"""
import asyncio
import json
import logging
import os
import time
from http import HTTPStatus

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from . import identity, profile
from .hub import Hub, Player, clean_presence, EMU, GAME
from .parties import Parties, clean_signal
from .turn import Turn, TurnError
from .store import Store

LEDGER_GENESIS = "0" * 64      # the ledger's head before any match (phase 4 chains the matches)

PROTOCOL = 1
HELLO_TIMEOUT = 10.0
SIGNUPS_PER_HOUR = 5          # new identities from one address
RATE, BURST = 20.0, 40.0      # messages per second a connection may send
TICK = 0.5                    # how often counts and rooms go out

log = logging.getLogger("matchmaker")


class Server:
    def __init__(self, db_path=":memory:", clock=time.monotonic, signer=None, turn=None):
        self.store = Store(db_path)
        self.hub = Hub()
        self.parties = Parties(self.hub)
        self.turn = turn or Turn.from_env(self.store, os.environ)
        self.clock = clock
        self.signer = signer or profile.Signer.from_env()
        if self.signer.ephemeral:
            log.warning("MATCHMAKER_SIGNING_KEY not set: profiles signed with a throwaway key")

    def signed_profile(self, cab_id):
        version, record = self.store.record(cab_id)
        return self.signer.sign(profile.payload(self.store.row(cab_id), record, version, LEDGER_GENESIS))

    def client_ip(self, ws):
        headers = ws.request.headers if ws.request else {}
        return headers.get("CF-Connecting-IP") or (ws.remote_address or ("",))[0]

    async def send(self, ws, msg):
        try:
            await ws.send(json.dumps(msg, separators=(",", ":")))
        except ConnectionClosed:
            pass

    async def hello(self, ws):
        """The first message: who this cabinet is. The Player, or None (and an error sent)."""
        try:
            raw = await asyncio.wait_for(ws.recv(), HELLO_TIMEOUT)
            msg = json.loads(raw)
        except (asyncio.TimeoutError, ValueError, ConnectionClosed):
            await self.send(ws, {"t": "error", "code": "hello"})
            return None
        if not isinstance(msg, dict) or msg.get("t") != "hello":
            await self.send(ws, {"t": "error", "code": "hello"})
            return None
        if msg.get("v") != PROTOCOL:
            await self.send(ws, {"t": "error", "code": "version"})
            return None
        try:
            khash = identity.key_hash(msg.get("secret"))
        except ValueError:
            await self.send(ws, {"t": "error", "code": "secret"})
            return None
        try:
            nick = identity.clean_nick(msg.get("nick"))
        except ValueError:
            await self.send(ws, {"t": "error", "code": "nick"})
            return None
        if self.store.banned(khash):
            await self.send(ws, {"t": "error", "code": "banned"})
            return None
        row = self.store.find(khash)
        if row is None:
            ip = self.client_ip(ws)
            if self.store.signups_since(ip, 3600) >= SIGNUPS_PER_HOUR:
                await self.send(ws, {"t": "error", "code": "signups"})
                return None
            cab_id, nick, tag = self.store.register(khash, nick, ip)
        else:
            cab_id = row["id"]
            nick, tag = self.store.seen(cab_id, nick)

        async def send(m, ws=ws):
            await self.send(ws, m)
        player = Player(cab_id, nick, tag, send)
        if msg.get("conn") in ("cable", "wifi"):
            player.info["conn"] = msg["conn"]
        await self.send(ws, {"t": "welcome", "id": cab_id, "nick": nick, "tag": tag})
        await self.send(ws, {"t": "profile", "profile": self.signed_profile(cab_id)})
        return player

    async def handler(self, ws):
        player = await self.hello(ws)
        if player is None:
            return
        old = self.hub.players.get(player.id)
        if old is not None:
            await self.notify(self.parties.leave(old))   # the same cabinet again: its old party is over
        self.hub.join(player)
        tokens, last = BURST, self.clock()
        try:
            async for raw in ws:
                now = self.clock()
                tokens = min(BURST, tokens + (now - last) * RATE)
                last = now
                if tokens < 1:
                    continue                      # too fast: dropped
                tokens -= 1
                try:
                    msg = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(msg, dict):
                    continue
                kind = msg.get("t")
                if kind == "presence":
                    fields = clean_presence(msg)
                    if self.parties.party_of(player):
                        fields.pop("game", None)          # in a party, the party's game
                        fields.pop("emu", None)
                    self.hub.update(player, fields)
                elif kind == "party":
                    await self.party(player, msg)
                elif kind == "signal":
                    to = self.parties.may_signal(player, msg.get("to"))
                    data = clean_signal(msg.get("data"))
                    if to is not None and data is not None:
                        await to.send({"t": "signal", "from": player.id, "data": data})
                elif kind == "turn":
                    await self.relay(player, msg)
                elif kind == "watch":
                    game = msg.get("game")
                    if game is None or (isinstance(game, str) and GAME.match(game)):
                        player.watching = game
                        if game:
                            await player.send({"t": "room", "game": game, "players": self.hub.room(game)})
                elif kind == "profile":
                    await player.send({"t": "profile", "profile": self.signed_profile(player.id)})
                elif kind == "ping" and isinstance(msg.get("n"), int):
                    await player.send({"t": "pong", "n": msg["n"]})
        except ConnectionClosed:
            pass
        finally:
            if self.hub.players.get(player.id) is player:
                await self.notify(self.parties.leave(player))
            self.hub.leave(player)

    async def notify(self, notes):
        for who, msg in notes:
            await who.send(msg)

    async def party(self, player, msg):
        op = msg.get("op")
        if op == "open":
            game, emu, most = msg.get("game"), msg.get("emu"), msg.get("max")
            if not (isinstance(game, str) and GAME.match(game) and isinstance(emu, str) and EMU.match(emu)
                    and isinstance(most, int) and not isinstance(most, bool)):
                await player.send({"t": "party", "op": "error", "code": "bad"})
                return
            party, notes = self.parties.open_party(player, game, emu, most)
        elif op == "join":
            party, notes = self.parties.join(player, msg.get("party"))
        elif op == "leave":
            party, notes = None, self.parties.leave(player)
        elif op == "lock":
            self.parties.lock(player, msg.get("open") is True)
            return
        else:
            return
        await self.notify(notes)
        if isinstance(party, str):
            await player.send({"t": "party", "op": "error", "code": party})

    async def relay(self, player, msg):
        """The relay's credentials, only to a cabinet in a party; or what it used."""
        if msg.get("op") == "used":
            self.turn.used(player.id, msg.get("username"), msg.get("bytes"))
            return
        if not self.parties.party_of(player):
            await player.send({"t": "turn", "error": "party"})
            return
        try:
            ice = await self.turn.credentials(player.id)
        except TurnError as e:
            await player.send({"t": "turn", "error": e.code})
            return
        await player.send({"t": "turn", "ice": ice})

    async def ticker(self):
        while True:
            await asyncio.sleep(TICK)
            await self.flush()

    async def flush(self):
        for player, msg in self.hub.flush():
            await player.send(msg)


def http_for(server):
    """/health and /pubkey answer in plain HTTP; only /ws becomes a WebSocket."""
    def http(connection, request):
        if request.path == "/health":
            return connection.respond(HTTPStatus.OK, "ok\n")
        if request.path == "/pubkey":
            return connection.respond(HTTPStatus.OK, json.dumps(server.signer.public_info()) + "\n")
        if request.path != "/ws":
            return connection.respond(HTTPStatus.NOT_FOUND, "not found\n")
        return None
    return http


async def run(host="0.0.0.0", port=8080, db_path=":memory:", ready=None):
    server = Server(db_path)
    async with serve(server.handler, host, port, process_request=http_for(server), max_size=4096,
                     ping_interval=20, ping_timeout=20) as ws_server:
        if ready is not None:
            ready.set_result((server, ws_server))
        ticker = asyncio.create_task(server.ticker())
        try:
            await ws_server.serve_forever()
        finally:
            ticker.cancel()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    data = os.environ.get("DATA_DIR", "/data")
    os.makedirs(data, exist_ok=True)
    asyncio.run(run(port=int(os.environ.get("PORT", "8080")), db_path=os.path.join(data, "matchmaker.db")))


if __name__ == "__main__":
    main()
