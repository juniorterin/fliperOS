# A party online do Matchmaker (fase 2): a party da rede local de sempre
# (felink: a sala, o plano, o servidor de arquivos, o comando do jogo) dentro
# do tunel da party (fetunnel), no endereco que o servidor deu a este gabinete.
#
# Quem abre (host): o servidor da a party (opened) -> o tunel sobe -> a sala
# do felink abre no endereco do tunel (o numero 1) e serve os arquivos do jogo
# so a quem chega direto (o relay so leva os controles).
# Quem entra (guest): joined -> o tunel liga ao anfitriao -> se falta o jogo
# e o caminho e direto, os arquivos vem dele (fetch_files) -> entra na sala.
#
# O atraso de entrada vai no plano (felink.online_delay, pelo ping do pior par
# do tunel): o anfitriao o poe no perfil antes de comecar.
#
# Nada aqui desenha: o Matchmaker chama tick() e le state().

import threading
import time

import felink
import fetunnel

RTT_WAIT = 5.0          # o anfitriao espera o ping do tunel ate isso antes de comecar
RTT_DEFAULT = 100       # sem ping nenhum medido, o atraso e o de 100 ms


class TunnelPresence:
    """A presenca da sala do felink online: os outros gabinetes nao a ouvem
    por broadcast (o tunel e de ponto a ponto); quem diz ao mundo o que este
    gabinete faz e o servidor (o Matchmaker manda a presenca)."""

    def table(self):
        return []

    def say(self, **info):
        pass

    def stop(self):
        pass


class OnlineLink(felink.Link):
    """O felink.Link no tunel: o "cabo" e a wg-fliperos com o endereco da party."""

    def __init__(self, home, tunnel, name, ident=None, profiles=None, local_players=None, clock=time.monotonic):
        net = tunnel.addr.rsplit(".", 1)[0]
        wire = felink.Wire("wg-fliperos", tunnel.addr, "255.255.255.0", net + ".255")
        super().__init__(home, profiles=profiles, wire=wire, ident=ident, name=name, clock=clock,
                         local_players=local_players)
        self.tunnel = tunnel
        self.presence = TunnelPresence()
        self.since = clock()
        self.file_allow = tunnel.direct       # a ROM so vai a quem chega direto

    def poll(self, now):
        pass                                  # nao ha cabo a conferir: o tunel e do fetunnel

    def tune(self):
        """O atraso de entrada pelo ping do pior par, no perfil (vai no plano)."""
        if self.profile is None:
            return None
        rtt = self.tunnel.worst_rtt()
        self.profile["input_delay"] = felink.online_delay(rtt if rtt is not None else RTT_DEFAULT, self.profile)
        return self.profile["input_delay"]

    def start_now(self):
        if self.role == "host":
            if self.tunnel.worst_rtt() is None and self.clock() - self.since < RTT_WAIT:
                return False                  # o ping do tunel ainda vem: o atraso sai dele
            self.tune()
        return super().start_now()

    def tick(self, now=None):
        if self.role == "host" and not self.plan:
            self.tune()
        return super().tick(now)


class OnlineParty:
    """Uma party online deste gabinete, do "opened"/"joined" do servidor ao fim.

    online: o feonline.Online; msg: a mensagem opened (host) ou joined (guest);
    game: {"system", "name", "profile", "files", "rom", "wanted"} do Matchmaker
    (files: o que o host serve; wanted: o que o guest precisa, relativos ao home).
    tunnel_factory e link_factory: os testes trocam."""

    def __init__(self, online, msg, game, home, name, tunnel_factory=None, link_factory=None,
                 relay_only=False, clock=time.monotonic):
        self.online, self.game, self.home, self.name = online, game, home, name
        self.role = "host" if msg.get("op") == "opened" else "guest"
        self.party_id = msg["party"]
        self.addr = msg["addr"]
        self.host = msg.get("host")                     # o anfitriao (guest)
        self.members = list(msg.get("members") or [])
        self.clock = clock
        make_tunnel = tunnel_factory or (lambda addr: fetunnel.Tunnel(addr, online.send, relay_only=relay_only))
        self.tunnel = make_tunnel(self.addr)
        self.link_factory = link_factory or (lambda: OnlineLink(home, self.tunnel, name))
        self.link = None
        self.stage = "tunnel"           # tunnel, fetch, lobby, playing, closed, failed
        self.message = None
        self.progress = None            # (feito, total) da copia dos arquivos
        self.fetching = None
        self.started_at = clock()

    def start(self):
        self.tunnel.start(self.members)

    def handle(self, msg):
        """Uma mensagem do servidor (do online.take()): o tunel e o fim da party."""
        kind, op = msg.get("t"), msg.get("op")
        if kind == "party" and op == "closed" or kind == "session":
            self.finish("closed", "THE PARTY IS OVER" if kind == "party" else "THE CONNECTION DROPPED")
            return
        if msg.get("party") not in (None, self.party_id) and kind == "party":
            return
        self.tunnel.handle(msg)

    def state(self):
        snap = self.tunnel.snapshot()
        lobby = self.link.lobby() if self.link else None
        return {"stage": self.stage, "role": self.role, "message": self.message, "tunnel": snap, "lobby": lobby,
                "progress": self.progress, "rtt": self.tunnel.worst_rtt()}

    def host_peer(self):
        if not self.host:
            return None
        return next((p for p in self.tunnel.snapshot()["peers"] if p["id"] == self.host["id"]), None)

    def tick(self, now=None):
        """Chamado do laco do Matchmaker. "launch" na hora de abrir o jogo."""
        now = self.clock() if now is None else now
        if self.stage in ("closed", "failed"):
            return None
        snap = self.tunnel.snapshot()
        if snap["status"] == "failed":
            return self.finish("failed", "NO TUNNEL: " + (snap["error"] or "")[:40])
        if self.stage == "tunnel":
            if self.role == "host" and snap["status"] == "up":
                self.open_room()
            elif self.role == "guest":
                peer = self.host_peer()
                if peer and peer["path"] == "failed":
                    return self.finish("failed", "NO WAY TO THE OTHER CABINET")
                if peer and peer["path"] in ("direct", "relay"):
                    self.after_tunnel(peer)
        elif self.stage == "fetch" and self.fetching is not None and not self.fetching.is_alive():
            self.fetching = None
            if self.stage == "fetch":
                self.join_room()
        if self.link and self.stage in ("lobby", "playing"):
            got = self.link.tick(now)
            if got == "launch":
                self.stage = "playing"
                self.online.send({"t": "party", "op": "lock", "open": bool(self.link.profile.get("late"))})
                return "launch"
            if got == "closed":
                return self.finish("closed", "THE PARTY IS OVER")
        return None

    def open_room(self):
        self.link = self.link_factory()
        g = self.game
        if not self.link.host_game(g["profile"], g["system"], g["name"], g.get("files") or [], rom=g.get("rom")):
            return self.finish("failed", self.link.message or "COULD NOT OPEN THE PARTY")
        self.stage = "lobby"

    def after_tunnel(self, peer):
        """O guest ligado ao anfitriao: copia o que falta (so direto) e entra na sala."""
        wanted = self.game.get("wanted") or []
        if not wanted:
            return self.join_room()
        if peer["path"] != "direct":
            return self.finish("failed", "NEEDS THE ROM (NOT THROUGH THE RELAY)")
        self.stage = "fetch"
        self.progress = (0, 0)

        def fetch():
            def progress(done, total, path):
                self.progress = (done, total)
            ok, missing = felink.fetch_files(peer["addr"], self.home, wanted, progress=progress)
            if not ok:
                self.finish("failed", "THE GAME DID NOT COME (%d FILES)" % len(missing))
        self.fetching = threading.Thread(target=fetch, name="fliperos-party-fetch", daemon=True)
        self.fetching.start()

    def join_room(self):
        self.link = self.link_factory()
        g = self.game
        party = {"host_ip": self.host["addr"], "game": g["name"], "system": g["system"]}
        if not self.link.join_party(party, g["profile"], g["system"], g["name"], rom=g.get("rom")):
            return self.finish("failed", self.link.message or "COULD NOT JOIN")
        self.stage = "lobby"

    def command(self, base):
        return self.link.command(base)

    def finish(self, stage, message=None):
        if self.stage in ("closed", "failed"):
            return None
        self.stage, self.message = stage, message
        return None

    def leave(self):
        """Sai da party (a do host fecha para todos), o tunel desce."""
        if self.link:
            try:
                self.link.leave()
            except OSError:
                pass
        if self.stage not in ("closed", "failed"):
            self.online.send({"t": "party", "op": "leave"})
            self.stage = "closed"
        self.tunnel.stop()
