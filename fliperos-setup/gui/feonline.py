# O lado do gabinete do Matchmaker online (fase 1): fala com o servidor
# (server/matchmaker, wss://fliperos-matchmaker.juniorter.in/ws) enquanto o
# Matchmaker esta aberto. Fora dele nada online roda: sem servico, sem avisos.
#
# - check(): o Matchmaker confere, ao abrir, se ha internet e se o servidor
#   responde ("ok", "internet" ou "server": as telas de offline).
# - O segredo do gabinete (32 bytes, ~/.config/fliperos/online.key, 0600): o
#   servidor guarda so o hash dele, e dele sai a tag de NICK#tag.
# - conn_type(): cabo ou Wi-Fi, pela interface da rota padrao.
# - Online: uma linha de fundo que conecta, se apresenta, reconecta sozinha e
#   guarda o ultimo estado (quem sou, a ficha assinada, as contagens por jogo,
#   as salas, o ping); presence() e watch() mandam o que o Matchmaker faz.
#
# Nada aqui depende do pygame: o Matchmaker so chama e desenha.

import json
import os
import secrets
import socket
import threading
import time
import urllib.request
from urllib.parse import urlparse

import fews

SERVER = os.environ.get("FLIPEROS_MATCHMAKER_URL", "wss://fliperos-matchmaker.juniorter.in/ws")
KEY_FILE = os.environ.get("FLIPEROS_ONLINE_KEY") or os.path.join(os.path.expanduser("~"), ".config", "fliperos",
                                                                    "online.key")
PROTOCOL = 1
# A chave publica com que o servidor assina as fichas (o /pubkey dele).
PUBKEY = {"kid": "2cf268e1d202ad3a", "public": "5mRFlFqk05QC2bEHa21ZeVP85xyVxBbl6ODGTCv_dok"}
PING_EVERY = 10.0
BACKOFF = (1, 2, 4, 8, 15, 30)


def health_url(url=SERVER):
    u = urlparse(url)
    scheme = "https" if u.scheme == "wss" else "http"
    return "%s://%s/health" % (scheme, u.netloc)


def load_secret(path=KEY_FILE, create=True):
    """O segredo do gabinete (64 hex); criado na primeira vez (so o dono le)."""
    try:
        with open(path) as f:
            s = f.read().strip().lower()
        if len(s) == 64 and all(c in "0123456789abcdef" for c in s):
            return s
    except OSError:
        pass
    if not create:
        return None
    s = secrets.token_hex(32)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(s + "\n")
    os.replace(tmp, path)
    return s


def conn_type(route="/proc/net/route", sysfs="/sys/class/net"):
    """"cable", "wifi" ou None (sem rota padrao): a interface da rota padrao
    de menor metrica, Wi-Fi se ela tem wireless/ ou phy80211 no sysfs."""
    best = None
    try:
        with open(route) as f:
            next(f, None)
            for line in f:
                cols = line.split()
                if len(cols) >= 7 and cols[1] == "00000000" and int(cols[3], 16) & 2:
                    metric = int(cols[6])
                    if best is None or metric < best[0]:
                        best = (metric, cols[0])
    except (OSError, ValueError):
        return None
    if best is None:
        return None
    base = os.path.join(sysfs, best[1])
    if os.path.exists(os.path.join(base, "wireless")) or os.path.exists(os.path.join(base, "phy80211")):
        return "wifi"
    return "cable"


def internet_up(hosts=(("1.1.1.1", 443), ("8.8.8.8", 443)), timeout=3.0):
    for addr in hosts:
        try:
            socket.create_connection(addr, timeout).close()
            return True
        except OSError:
            continue
    return False


def server_up(url=SERVER, timeout=5.0):
    req = urllib.request.Request(health_url(url), headers={"User-Agent": fews.USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except OSError:
        return False


def check(url=SERVER, internet=internet_up, server=server_up):
    """O que o Matchmaker confere ao abrir: "ok", "internet" (sem internet) ou
    "server" (com internet, o servidor nao responde)."""
    if not internet():
        return "internet"
    if not server(url):
        return "server"
    return "ok"


def verify_profile(profile, pub=PUBKEY):
    """A ficha (dict) se a assinatura do servidor confere; False se nao confere;
    None se nao da para conferir aqui (sem a biblioteca cryptography)."""
    try:
        import base64
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError:
        return None

    def unb64(t):
        return base64.urlsafe_b64decode(t + "=" * (-len(t) % 4))
    try:
        Ed25519PublicKey.from_public_bytes(unb64(pub["public"])).verify(
            unb64(profile["sig"]), b"fliperos-profile-v1\n" + profile["payload"].encode())
        return json.loads(profile["payload"])
    except Exception:
        return False


class Online:
    """O gabinete conectado ao servidor enquanto o Matchmaker esta aberto."""

    def __init__(self, nick, url=SERVER, secret=None, connect=None, clock=time.monotonic):
        self.nick, self.url = nick, url
        self.secret = secret or load_secret()
        self.connect = connect or (lambda u: fews.WebSocket(u, timeout=10))
        self.clock = clock
        self.lock = threading.Lock()
        self.stopped = threading.Event()
        self.ws = None
        self.thread = None
        self.state = {"status": "connecting", "error": None, "me": None, "profile": None, "verified": None,
                      "counts": {}, "rooms": {}, "rtt": None}
        self.presence_fields = {"state": "idle"}
        self.watching = None
        self.changed = threading.Event()

    # -- o que o Matchmaker usa
    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stopped.set()
        ws = self.ws
        if ws is not None:
            ws.close()
        if self.thread:
            self.thread.join(3)

    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps(self.state))

    def presence(self, **fields):
        with self.lock:
            self.presence_fields.update(fields)
        self._send(dict(self.presence_fields, t="presence", conn=conn_type(), rtt=self.state["rtt"]))

    def watch(self, game):
        self.watching = game
        self._send({"t": "watch", "game": game})

    # -- por dentro
    def _set(self, **kv):
        with self.lock:
            self.state.update(kv)
        self.changed.set()

    def _send(self, msg):
        ws = self.ws
        if ws is None:
            return
        try:
            ws.send(json.dumps(msg, separators=(",", ":")))
        except fews.Closed:
            pass

    def _session(self):
        ws = self.connect(self.url)
        self.ws = ws
        ws.send(json.dumps({"t": "hello", "v": PROTOCOL, "secret": self.secret, "nick": self.nick,
                            "conn": conn_type()}))
        first = json.loads(ws.recv(timeout=10) or "{}")
        if first.get("t") == "error":
            self._set(status="refused", error=first.get("code"))
            return False                       # nao adianta tentar de novo (banido, apelido...)
        if first.get("t") != "welcome":
            raise fews.Closed("no welcome")
        self._set(status="online", error=None, me={k: first[k] for k in ("id", "nick", "tag")})
        self.presence()                         # o que ja estava valendo, de novo apos reconectar
        if self.watching:
            self.watch(self.watching)
        next_ping, n, sent_at = self.clock(), 0, {}
        while not self.stopped.is_set():
            now = self.clock()
            if now >= next_ping:
                n += 1
                sent_at[n] = now
                self._send({"t": "ping", "n": n})
                next_ping = now + PING_EVERY
            raw = ws.recv(timeout=0.5)
            if raw is None:
                continue
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            kind = msg.get("t")
            if kind == "pong" and msg.get("n") in sent_at:
                self._set(rtt=round((self.clock() - sent_at.pop(msg["n"])) * 1000))
            elif kind == "counts":
                self._set(counts=msg.get("games") or {})
            elif kind == "room":
                with self.lock:
                    self.state["rooms"][msg.get("game")] = msg.get("players") or []
                self.changed.set()
            elif kind == "profile":
                self._set(profile=msg.get("profile"), verified=verify_profile(msg.get("profile") or {}))
        return True

    def run(self):
        tries = 0
        while not self.stopped.is_set():
            try:
                if self._session() is False:
                    return
                tries = 0
            except (OSError, fews.Closed, ValueError):
                self._set(status="offline")
            finally:
                if self.ws is not None:
                    self.ws.close()
                    self.ws = None
            if self.stopped.is_set():
                return
            wait = BACKOFF[min(tries, len(BACKOFF) - 1)]
            tries += 1
            self.stopped.wait(wait)
