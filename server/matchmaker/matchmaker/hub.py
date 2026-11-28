"""Who is online and what they do: the counts per game (the ONLINE NOW of
the Matchmaker's pages) and the room of a game (its lobby). In memory only:
a cabinet that drops leaves the room.
"""
import re

STATES = ("idle", "looking", "playing", "party", "download")
CONNS = ("cable", "wifi")
GAME = re.compile(r"^[a-z0-9_.-]{1,24}:[a-z0-9_.-]{1,40}$")
EMU = re.compile(r"^[a-z0-9_.-]{1,32}$")


def clean_presence(msg):
    """The fields of a presence message that are valid (the rest is dropped).
    game: "system:set" (mame:sf2ce). Who plays together (the group, its kind
    and its score "2-1" or places "2/4") is not the cabinet's to say: the
    server sets it from its parties (parties.py) and, in phase 3, its duels."""
    out = {}
    if msg.get("state") in STATES:
        out["state"] = msg["state"]
    if msg.get("conn") in CONNS:
        out["conn"] = msg["conn"]
    game = msg.get("game")
    if game is None or (isinstance(game, str) and GAME.match(game)):
        out["game"] = game
    emu = msg.get("emu")
    if emu is None or (isinstance(emu, str) and EMU.match(emu)):
        out["emu"] = emu
    for key, hi in (("pct", 100), ("rtt", 5000)):
        v = msg.get(key)
        if v is None or (isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= hi):
            out[key] = v
    return out


class Player:
    def __init__(self, cab_id, nick, tag, send):
        self.id, self.nick, self.tag, self.send = cab_id, nick, tag, send
        self.info = {"state": "idle", "conn": None, "game": None, "emu": None, "group": None, "kind": None,
                     "score": None, "pct": None, "rtt": None, "open": None, "host": None}
        self.watching = None

    def public(self):
        return dict(self.info, id=self.id, nick=self.nick, tag=self.tag)


class Hub:
    def __init__(self):
        self.players = {}
        self.dirty_counts = False
        self.dirty_rooms = set()

    def join(self, player):
        old = self.players.get(player.id)
        if old is not None:
            self.leave(old)               # the same cabinet connected again: the new link wins
        self.players[player.id] = player
        self.dirty_counts = True

    def leave(self, player):
        if self.players.get(player.id) is player:
            del self.players[player.id]
            if player.info["game"]:
                self.dirty_rooms.add(player.info["game"])
            self.dirty_counts = True

    def update(self, player, fields):
        before = player.info["game"]
        player.info.update(fields)
        for game in (before, player.info["game"]):
            if game:
                self.dirty_rooms.add(game)
        self.dirty_counts = True

    def counts(self):
        """Per game: how many are on it and how many look for a duel."""
        out = {}
        for p in self.players.values():
            g = p.info["game"]
            if not g:
                continue
            c = out.setdefault(g, {"players": 0, "looking": 0})
            c["players"] += 1
            if p.info["state"] == "looking":
                c["looking"] += 1
        return out

    def room(self, game):
        """The lobby of a game: its players, the ones that play together next to each other."""
        people = [p.public() for p in self.players.values() if p.info["game"] == game]
        people.sort(key=lambda p: (STATES.index(p["state"]), p["group"] or "", p["nick"], p["tag"]))
        return people

    def watchers(self, game):
        return [p for p in self.players.values() if p.watching == game]

    def flush(self):
        """What to send now: [(player, message)], and the dirty flags cleared."""
        out = []
        if self.dirty_counts:
            msg = {"t": "counts", "games": self.counts()}
            out += [(p, msg) for p in self.players.values()]
            self.dirty_counts = False
        for game in sorted(self.dirty_rooms):
            msg = {"t": "room", "game": game, "players": self.room(game)}
            out += [(p, msg) for p in self.watchers(game)]
        self.dirty_rooms.clear()
        return out
