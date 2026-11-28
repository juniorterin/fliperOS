# O tunel da party online do Matchmaker (fase 2): um WireGuard (wg-fliperos)
# com cada gabinete da party, numa malha. Dentro dele roda a party da rede
# local que ja existe (felink: a sala, o plano, o servidor de arquivos, o
# lockstep do GroovyMAME, o GGPO do Flycast, o net play do RetroArch), com o
# endereco de cada um em 10.207.N.0/24, que o servidor da.
#
# Como dois gabinetes se acham (cada par, sozinho):
# 1. Cada um escolhe uma porta UDP, pergunta ao STUN da Cloudflare o endereco
#    publico dela e a da ao WireGuard (fenat.public_port: o roteador mantem o
#    mapeamento).
# 2. Pelo servidor (um "signal"), cada um manda ao outro a chave publica e os
#    enderecos: o da rede de casa, o IPv6 e o publico do STUN.
# 3. Cada lado aponta o WireGuard para o melhor endereco do outro: a mesma
#    casa (o mesmo IP publico) primeiro, o IPv6 se os dois tem, depois o
#    publico. Os dois mandam handshakes ao mesmo tempo, e os roteadores abrem.
#    O WireGuard repete o handshake a cada 5 s; TRY_DIRECT s por endereco.
# 4. Se nenhum deu, o relay (fenat.Relay, o TURN da Cloudflare com as
#    credenciais que o servidor da): cada lado manda ao outro o endereco da
#    propria alocacao, e o WireGuard passa a mandar para 127.0.0.1 (o
#    repassador local). Pelo relay passam so os controles: direct() diz ao
#    servidor de arquivos da party que nao mande ROM nenhuma por ele.
#
# A parte root (a interface, a chave, os peers) e o config/fliperos-online-tunnel,
# pelo sudo sem senha. Tudo aqui roda numa linha de fundo: o Matchmaker so
# entrega as mensagens do servidor (handle) e le o snapshot().

import ipaddress
import json
import queue
import re
import subprocess
import threading
import time

import fenat

HELPER = ["sudo", "-n", "/usr/local/sbin/fliperos-online-tunnel"]
TRY_DIRECT = 8.0        # segundos de cada endereco direto (o WireGuard tenta o handshake a cada 5 s)
CHECK = 0.5             # de quanto em quanto tempo olha os handshakes enquanto algum par se acha
CHECK_IDLE = 5.0        # e depois que todos se acharam
STALE = 180             # um handshake mais velho que isso: o par caiu
RESEND = 3.0            # sem a chave do outro ate la, o meu sinal vai de novo (e pede o dele)
KEY = re.compile(r"^[A-Za-z0-9+/]{42}[AEIMQUYcgkosw480]=$")


class TunnelError(Exception):
    pass


class Helper:
    """O config/fliperos-online-tunnel pelo sudo (os testes trocam o argv)."""

    def __init__(self, argv=None, run=subprocess.run):
        self.argv = list(argv or HELPER)
        self.run = run

    def call(self, *args):
        r = self.run(self.argv + [str(a) for a in args], capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            raise TunnelError((r.stderr or "").strip() or "the tunnel helper failed")
        return r.stdout

    def up(self, addr, port):
        return self.call("up", addr, port).strip()

    def peer(self, key, addr, endpoint=None, quiet=False):
        self.call("peer", key, addr, *([endpoint] if endpoint else []), *(["quiet"] if quiet else []))

    def keep(self, key):
        self.call("keep", key)

    def endpoint(self, key, endpoint):
        self.call("endpoint", key, endpoint)

    def remove(self, key):
        self.call("remove", key)

    def show(self):
        return json.loads(self.call("show") or "[]")

    def down(self):
        self.call("down")


def endpoint_of(ip, port):
    return "[%s]:%d" % (ip, port) if ":" in ip else "%s:%d" % (ip, port)


def clean_addr(value):
    """[ip, port] de um sinal, ou None."""
    if not (isinstance(value, (list, tuple)) and len(value) == 2):
        return None
    ip, port = value
    if not isinstance(ip, str) or not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
        return None
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return None
    if a.is_multicast or a.is_unspecified or a.is_loopback:
        return None
    return [str(a), port]


def clean_cands(value):
    out = {}
    if isinstance(value, dict):
        for kind in ("lan", "v6", "stun"):
            addr = clean_addr(value.get(kind))
            if addr:
                out[kind] = addr
    return out


def candidates(mine, theirs):
    """Os enderecos diretos do outro, na ordem de tentar: a mesma casa (o
    mesmo IP publico), o IPv6 (se os dois tem) e o publico."""
    out = []
    same_house = mine.get("stun") and theirs.get("stun") and mine["stun"][0] == theirs["stun"][0]
    if same_house and theirs.get("lan"):
        out.append(("lan", theirs["lan"]))
    if mine.get("v6") and theirs.get("v6"):
        out.append(("v6", theirs["v6"]))
    if theirs.get("stun"):
        out.append(("stun", theirs["stun"]))
    return out


class Tunnel:
    """O tunel deste gabinete numa party online.

    addr: o endereco deste gabinete na party ("10.207.3.2"); send: manda uma
    mensagem ao servidor (feonline.Online.send). start(members) com os que ja
    estao na party; depois, handle() com cada mensagem "party", "signal" e
    "turn" que chegar do servidor."""

    def __init__(self, addr, send, helper=None, clock=time.monotonic, wall=time.time,
                 stun=fenat.public_port, lan=fenat.lan_addrs, relay_factory=None, port=None, log=None):
        self.log = log or (lambda *a: None)
        self.addr, self.send = addr, send
        self.helper = helper or Helper()
        self.clock, self.wall = clock, wall
        self.stun, self.lan = stun, lan
        self.relay_factory = relay_factory or (lambda ice, wg_port: fenat.Relay(ice, wg_port))
        self.port = port
        self.lock = threading.Lock()
        self.inbox = queue.Queue()
        self.peers = {}             # id -> o par: quem e, a chave, os enderecos, o caminho
        self.mine = {}              # os meus enderecos (lan, v6, stun)
        self.key = None             # a minha chave publica
        self.status = "starting"    # starting, up, failed, down
        self.error = None
        self.relay = None
        self.ice = None
        self.turn_asked = False
        self.relay_error = None
        self.thread = None
        self.running = False
        self.next_check = 0.0
        self.changed = threading.Event()

    # -- o que o Matchmaker usa
    def start(self, members=()):
        self.running = True
        self.thread = threading.Thread(target=self.run, args=(list(members),), name="fliperos-tunnel", daemon=True)
        self.thread.start()

    def handle(self, msg):
        self.log("in", msg)
        self.inbox.put(msg)

    def stop(self):
        self.running = False
        self.inbox.put(None)
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(5)

    def snapshot(self):
        with self.lock:
            return {"status": self.status, "error": self.error, "addr": self.addr, "relay_error": self.relay_error,
                    "peers": [{k: p.get(k) for k in ("id", "nick", "tag", "addr", "path", "endpoint")}
                              for p in self.peers.values()]}

    def direct(self, ip):
        """O par desse endereco do tunel chega direto (nao pelo relay): so assim
        o servidor de arquivos da party manda a ROM a ele."""
        with self.lock:
            return any(p["addr"] == ip and p.get("path") == "direct" for p in self.peers.values())

    def ready(self):
        """Todos os pares da party ja se acharam (direto ou pelo relay)."""
        with self.lock:
            return self.status == "up" and all(p.get("path") in ("direct", "relay") for p in self.peers.values())

    # -- a linha de fundo
    def run(self, members):
        try:
            self.open()
        except (TunnelError, OSError) as e:
            self._set(status="failed", error=str(e)[:120])
            self.running = False
            return
        for m in members:
            self.know(m)
        while self.running:
            wait = max(0.05, self.next_check - self.clock())
            try:
                msg = self.inbox.get(timeout=wait)
            except queue.Empty:
                msg = False
            if msg is None:
                break
            if msg is not False:
                try:
                    self.on_message(msg)
                except (TunnelError, OSError, ValueError, KeyError) as e:
                    self.log("message failed", msg, repr(e))
            if self.clock() >= self.next_check:
                try:
                    self.check()
                except (TunnelError, OSError, ValueError) as e:
                    self.log("check failed", repr(e))
        self.close()

    def open(self):
        port = self.port or fenat.free_udp_port()
        public = self.stun(port)
        self.mine = {k: [ip, port] for k, ip in self.lan().items()}
        if public:
            self.mine["stun"] = list(public)
        self.key = self.helper.up(self.addr + "/24", port)
        if not KEY.match(self.key or ""):
            raise TunnelError("no tunnel key")
        self.port = port
        self._set(status="up")

    def close(self):
        if self.relay is not None:
            try:
                self.relay.stop()
            except OSError:
                pass
            self.send({"t": "turn", "op": "used", "username": self.ice["username"], "bytes": self.relay.carried})
            self.relay = None
        try:
            self.helper.down()
        except (TunnelError, OSError):
            pass
        self._set(status="down")

    def _set(self, **kv):
        with self.lock:
            for k, v in kv.items():
                setattr(self, k, v)
        self.changed.set()

    def signal(self, peer_id, **data):
        self.log("signal to", peer_id, data)
        self.send({"t": "signal", "to": peer_id, "data": data})

    def know(self, info):
        """Um gabinete da party (do "joined" ou de um "member"): o meu sinal vai a ele."""
        pid = info.get("id")
        if not isinstance(pid, int) or pid in self.peers:
            return
        try:
            ipaddress.ip_address(info.get("addr"))
        except ValueError:
            return
        with self.lock:
            self.peers[pid] = {"id": pid, "nick": info.get("nick"), "tag": info.get("tag"), "addr": info["addr"],
                               "key": None, "cands": {}, "todo": [], "since": None, "path": None, "endpoint": None,
                               "relay": None, "sent": False}
        self.say_to(pid)
        self.changed.set()

    def say_to(self, pid, again=False):
        """O meu sinal ao par (uma vez; again: de novo, pedindo o dele)."""
        peer = self.peers[pid]
        if not peer["sent"] or again:
            peer["sent"] = self.clock()
            extra = {"again": 1} if again else {}
            self.signal(pid, key=self.key, cands=self.mine, **extra)

    def on_message(self, msg):
        kind, op = msg.get("t"), msg.get("op")
        if kind == "party" and op == "member":
            self.know(msg.get("peer") or {})
        elif kind == "party" and op == "left":
            self.forget(msg.get("id"))
        elif kind == "signal":
            self.on_signal(msg.get("from"), msg.get("data") or {})
        elif kind == "turn":
            self.on_turn(msg)

    def forget(self, pid):
        with self.lock:
            peer = self.peers.pop(pid, None)
        if peer and peer["key"]:
            self.helper.remove(peer["key"])
        self.changed.set()

    def on_signal(self, pid, data):
        peer = self.peers.get(pid)
        if peer is None:
            return
        if data.get("again"):
            peer["sent"] = self.clock()             # o outro perdeu o meu: vai de novo
            self.signal(pid, key=self.key, cands=self.mine)
        relay = clean_addr(data.get("relay"))
        if relay:
            peer["relay"] = relay                  # guardado: vale quando a chave chegar
        if data.get("relay_ready"):
            peer["relay_ready"] = True
        if KEY.match(data.get("key") or "") and peer["key"] is None:
            peer["key"] = data["key"]
            peer["cands"] = clean_cands(data.get("cands"))
            peer["todo"] = candidates(self.mine, peer["cands"])
            self.say_to(pid)
            self.next_candidate(peer)
        if peer["relay"] and peer["key"]:
            self.want_relay(peer)
        self.next_check = 0.0

    def next_candidate(self, peer):
        """O proximo endereco direto do par; sem mais nenhum, o relay."""
        if peer["todo"]:
            kind, (ip, port) = peer["todo"].pop(0)
            peer["endpoint"] = endpoint_of(ip, port)
            peer["since"] = self.clock()
            self.log("try", kind, peer["endpoint"])
            self.helper.peer(peer["key"], peer["addr"], peer["endpoint"])
            return
        if peer["since"] is None:                       # sem endereco nenhum: so o relay
            self.helper.peer(peer["key"], peer["addr"])
        peer["since"] = self.clock()
        peer["path"] = "wait-relay"
        self.log("relay for", peer["id"])
        self.want_relay(peer)

    def want_relay(self, peer):
        if self.relay is None:
            if not self.turn_asked:
                self.turn_asked = True
                self.send({"t": "turn"})
            return
        if not peer.get("relay_sent"):
            peer["relay_sent"] = True
            self.signal(peer["id"], relay=list(self.relay.relayed))
        if peer["relay"] and not peer.get("relay_port"):
            peer["relay_port"] = self.relay.add_peer(tuple(peer["relay"]))
        if not peer.get("relay_port") or peer.get("relay_set"):
            return
        # Um peer novo (o handshake sai na hora), mas so de um lado: dois
        # handshakes que se cruzam no relay se anulam. O de endereco maior se
        # prepara quieto (so responde) e avisa (relay_ready); so entao o de
        # endereco menor comeca. Ligado, o quieto ganha o keepalive (check).
        peer["endpoint"] = "127.0.0.1:%d" % peer["relay_port"]
        quiet = ipaddress.ip_address(self.addr) > ipaddress.ip_address(peer["addr"])
        if not quiet and not peer.get("relay_ready"):
            return
        peer["relay_set"], peer["quiet"] = True, quiet
        self.log("endpoint relay", peer["endpoint"], peer["relay"], "quiet" if quiet else "starts")
        self.helper.peer(peer["key"], peer["addr"], peer["endpoint"], quiet=quiet)
        if quiet:
            self.signal(peer["id"], relay_ready=1)

    def on_turn(self, msg):
        if msg.get("error") or not isinstance(msg.get("ice"), dict):
            self._set(relay_error=msg.get("error") or "fail")
            with self.lock:
                for p in self.peers.values():
                    if p["path"] == "wait-relay":
                        p["path"] = "failed"
            return
        try:
            relay = self.relay_factory(msg["ice"], self.port)
            relay.open()
            relay.start()
        except (OSError, fenat.TurnError) as e:
            self._set(relay_error=str(e)[:80])
            return
        self.ice, self.relay = msg["ice"], relay
        for p in list(self.peers.values()):
            if p["path"] == "wait-relay" or p["relay"]:
                self.want_relay(p)

    def check(self):
        """Os handshakes: quem se achou, e quem passa ao proximo endereco."""
        now, wall = self.clock(), self.wall()
        shown = {row["key"]: row for row in self.helper.show()}
        pending = False
        with self.lock:
            peers = list(self.peers.values())
        for p in peers:
            if not p["key"]:
                pending = True
                if p["sent"] and now - p["sent"] >= RESEND:
                    self.say_to(p["id"], again=True)
                continue
            row = shown.get(p["key"]) or {}
            alive = row.get("handshake", 0) and wall - row["handshake"] < STALE
            if alive:
                ep = row.get("endpoint") or ""
                p["path"] = "relay" if ep.startswith("127.0.0.1:") else "direct"
                p["endpoint"] = ep
                if p.get("quiet"):
                    p["quiet"] = False
                    self.helper.keep(p["key"])
                continue
            pending = True
            if p["path"] in ("direct", "relay"):
                p["path"] = None                         # caiu: volta a procurar
                p["relay_set"] = p["relay_ready"] = False
                p["todo"] = candidates(self.mine, p["cands"])
                p["since"] = None
                self.next_candidate(p)
            elif p["path"] is None and p["since"] is not None and now - p["since"] >= TRY_DIRECT:
                self.next_candidate(p)
        self.changed.set()
        self.next_check = now + (CHECK if pending else CHECK_IDLE)
