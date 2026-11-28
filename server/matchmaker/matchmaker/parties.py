"""Online parties (phase 2): who plays together over the internet.

A party is one game, a host and up to `max` cabinets. The server gives each
party a /24 inside 10.207.0.0/16 (the host is .1, the guests .2, .3...) and
passes the tunnel's signals between any two of its cabinets (a mesh): the WireGuard
public key and the addresses where a cabinet can be reached (its LAN address,
IPv6, the public IPv4 from STUN, the TURN relay). Everything else (who takes
which player, the countdown, the game's command) runs inside the tunnel, in
the same party code the cabinets use on a cable (felink).

The server owns the group of a player (the party id), its kind and its
places ("2/4"): a cabinet cannot claim to be in a party it is not in.
"""
import itertools
import json
import re

NET = "10.207"
NETS = 256                  # parties at once: 10.207.0.0/24 .. 10.207.255.0/24
MAX_PLAYERS = 10            # GroovyMAME's lockstep (felink.MAME_MAX_PLAYERS)
PARTY_ID = re.compile(r"^p[0-9a-z]{1,12}$")
SIGNAL_MAX = 1024           # bytes of one signal's data (JSON)


class Party:
    def __init__(self, pid, net, host, game, emu, max_players):
        self.id, self.net, self.game, self.emu, self.max = pid, net, game, emu, max_players
        self.host = host
        self.members = {host.id: (host, 1)}      # id -> (player, last byte of its address)
        self.open = True

    def addr(self, n):
        return "%s.%d.%d" % (NET, self.net, n)

    def places(self):
        return "%d/%d" % (len(self.members), self.max)

    def peer(self, player):
        """What another member sees of `player`: who it is and its tunnel address."""
        return dict(player.public(), addr=self.addr(self.members[player.id][1]))

    def free_byte(self):
        used = {n for _, n in self.members.values()}
        return next(n for n in itertools.count(2) if n not in used)


class Parties:
    def __init__(self, hub):
        self.hub = hub
        self.by_id = {}
        self.of_player = {}
        self.counter = itertools.count(1)

    def party_of(self, player):
        return self.of_player.get(player.id)

    def _mark(self, party):
        """The presence of every member: the party's id, kind and places."""
        for player, _ in party.members.values():
            self.hub.update(player, {"group": party.id, "kind": "party", "score": party.places(),
                                     "game": party.game, "emu": party.emu, "open": party.open,
                                     "host": player is party.host})

    def _clear(self, player):
        self.hub.update(player, {"group": None, "kind": None, "score": None, "open": None, "host": None})

    def _free_net(self):
        used = {p.net for p in self.by_id.values()}
        return next((n for n in range(NETS) if n not in used), None)

    def open_party(self, player, game, emu, max_players):
        """The player's own party (it leaves the one it was in). (party, [notes]) or (error, [notes])."""
        notes = self.leave(player)
        net = self._free_net()
        if net is None:
            return "nets", notes
        pid = "p%x" % next(self.counter)
        party = Party(pid, net, player, game, emu, max(2, min(MAX_PLAYERS, max_players)))
        self.by_id[pid] = party
        self.of_player[player.id] = party
        self._mark(party)
        notes.append((player, {"t": "party", "op": "opened", "party": pid, "addr": party.addr(1),
                               "net": "%s.%d.0/24" % (NET, net), "game": game, "emu": emu, "max": party.max}))
        return party, notes

    def join(self, player, pid):
        """Into another cabinet's party. (party, [notes]) or (error code, [notes])."""
        party = self.by_id.get(pid) if isinstance(pid, str) and PARTY_ID.match(pid) else None
        if party is None:
            return "gone", []
        if player.id in party.members:
            return "busy", []
        if not party.open:
            return "closed", []
        if len(party.members) >= party.max:
            return "full", []
        notes = self.leave(player)
        n = party.free_byte()
        party.members[player.id] = (player, n)
        self.of_player[player.id] = party
        self._mark(party)
        others = [p for p, _ in party.members.values() if p is not player]
        notes.append((player, {"t": "party", "op": "joined", "party": party.id, "addr": party.addr(n),
                               "net": "%s.%d.0/24" % (NET, party.net), "game": party.game, "emu": party.emu,
                               "max": party.max, "host": party.peer(party.host),
                               "members": [party.peer(p) for p in others]}))
        for other in others:
            notes.append((other, {"t": "party", "op": "member", "party": party.id, "peer": party.peer(player)}))
        return party, notes

    def leave(self, player):
        """Out of its party: the host's leaving closes it for everyone. [(player, message)]."""
        party = self.of_player.pop(player.id, None)
        if party is None:
            return []
        notes = []
        if party.host is player:
            for other, _ in list(party.members.values()):
                self.of_player.pop(other.id, None)
                self._clear(other)
                if other is not player:
                    notes.append((other, {"t": "party", "op": "closed", "party": party.id}))
            del self.by_id[party.id]
        else:
            party.members.pop(player.id, None)
            self._clear(player)
            self._mark(party)
            for other, _ in party.members.values():
                notes.append((other, {"t": "party", "op": "left", "party": party.id, "id": player.id}))
        return notes

    def lock(self, player, is_open):
        """The host says whether the party still takes new cabinets (a game that started)."""
        party = self.party_of(player)
        if party is None or party.host is not player:
            return False
        party.open = bool(is_open)
        self._mark(party)
        return True

    def may_signal(self, a, b_id):
        """Two members of the same party talk: the tunnel is a mesh (GroovyMAME's
        lockstep and Flycast's GGPO send to every cabinet of the party)."""
        party = self.party_of(a)
        if party is None or b_id not in party.members or b_id == a.id:
            return None
        return party.members[b_id][0]


def clean_signal(data):
    """A signal's data, if it is a small JSON object; None otherwise."""
    if not isinstance(data, dict):
        return None
    try:
        raw = json.dumps(data, separators=(",", ":"))
    except (TypeError, ValueError):
        return None
    return data if len(raw) <= SIGNAL_MAX else None
