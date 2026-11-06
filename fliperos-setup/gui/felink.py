# Link play e net play entre gabinetes (gui/fliperos-frontend): quem esta na
# rede e o que joga, a sala de espera (a festa), a NVRAM de cada gabinete, o
# comando de cada emulador e a copia dos arquivos de um jogo. SO na rede
# local e SO pelo cabo: a interface e a cabeada (nem Wi-Fi, nem virtual) e
# tudo o que o modulo abre fica nela (a presenca no broadcast da sub-rede, a
# festa e os arquivos em portas dela); com o cabo solto, nada disso existe.
#
# - Presenca: cada gabinete diz por UDP, uma vez por segundo, o que abriu
#   (jogo, festa, vagas, estado). Quem fica 4 s calado sai da tabela.
# - Festa: o anfitriao (numero 1) escuta um TCP, quem entra recebe o proximo
#   numero e todos veem a sala. No fim, a festa fixa quantos sao e o numero de
#   cada um, e manda a cada gabinete o seu atraso (a ordem de subida muda de
#   emulador para emulador: link-profiles.json).
#   Na party do RetroArch (perfil "late") quem abre ja entra no jogo, e os
#   outros entram depois, com o jogo andando.
# - Perfis: um por familia de jogo, com o que os testes mostraram
#   (docs/research/linked-cabinets.md). Jogo fora dos perfis nao tem link.
# - NVRAM: um arquivo por numero de gabinete (config/link-nvram), posto onde
#   o emulador o le; o que havia vai para NOME.solo e volta no fim do jogo.
#
# Nada aqui depende do pygame: o frontend so chama e desenha.

import hashlib
import json
import lzma
import os
import re
import socket
import struct
import threading
import time
import unicodedata
from collections import namedtuple
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote

try:
    import fcntl
except ImportError:           # fora do Linux (so os testes de bancada); wired() pede FLIPEROS_LINK_WIRE
    fcntl = None

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILES = os.environ.get("FLIPEROS_LINK_PROFILES") or os.path.join(HERE, "link-profiles.json")
NVRAM_SRC = os.environ.get("FLIPEROS_LINK_NVRAM") or next(
    (p for p in ("/usr/local/share/fliperos/link-nvram", os.path.join(HERE, "..", "..", "config", "link-nvram"))
     if os.path.isdir(p)), "/usr/local/share/fliperos/link-nvram")
PORT_PRESENCE, PORT_PARTY, PORT_FILES = 55436, 55437, 55438
# O net play e o do RetroArch, pelo fliperos-kms-run, com os jogos das pastas
# dos cores que o fazem (~/roms/retroarch/<core>, netplay_core). A pasta do
# MAME nao entra: um zip do romset do MAME nem sempre tem os dumps que o FBNeo
# pede. A lista dos sets do FBNeo vem do indice que o Setup baixa
# (config/fliperos-fbneo).
PORT_NETPLAY = 55435
# O Flycast tem o net play dele, o GGPO (rollback, UDP 19713), nos jogos de
# Naomi e Atomiswave: dois jogadores, um em cada gabinete.
PORT_GGPO = 19713
GGPO_SYSTEMS = ("naomi", "naomi2", "atomiswave")
# O Dolphin (GameCube e Wii, ~/roms/dolphin) com o patch do FliperOS
# (config/dolphin-patches: --netplay host|join): ate quatro gabinetes, um
# jogador em cada (o controle 1 de cada um), na porta TCP dele.
PORT_DOLPHIN = 2626
DOLPHIN_SYSTEMS = ("dolphin",)
DOLPHIN = os.environ.get("FLIPEROS_DOLPHIN", "/usr/local/bin/dolphin-emu")
BUTTONS_MAP = os.environ.get("FLIPEROS_BUTTONS_MAP", "/etc/fliperos/buttons.map")
KMS_RUN = os.environ.get("FLIPEROS_KMS_RUN", "/opt/fliperos/bin/fliperos-kms-run")
RA_CORES = os.environ.get("FLIPEROS_RA_CORES", "/opt/fliperos/retroarch/cores")
RA_INFO = os.environ.get("FLIPEROS_RA_INFO", "/opt/fliperos/retroarch/info")
FBNEO_INDEX = os.environ.get("FLIPEROS_FBNEO_INDEX", "/usr/local/share/fliperos/fbneo-sets.tsv.xz")
INTERVAL, EXPIRE = 1.0, 4.0
SOLO = ".solo"
# Os nomes de interface que nao sao a cabeada, mesmo com um dispositivo atras
# (as pontes e os tuneis do Docker, do libvirt e das VPNs).
VIRTUAL = ("lo", "docker", "veth", "br-", "virbr", "tun", "tap", "wg", "vmnet", "vboxnet", "zt")

Wire = namedtuple("Wire", "name ip mask broadcast")

# O apelido do gabinete (Setup > System > Cabinet name, e na instalacao): o
# nome que os outros gabinetes veem na party e no aviso "NOME IS PLAYING".
# NAME_MAX letras cabem no aviso na tela em pe (240 de largura, fonte de 8).
CONF = os.environ.get("FLIPEROS_CONF", "/etc/fliperos/fliperos.conf")
NAME_MAX = 12
# Sem apelido, uma fruta ou um bicho, sempre o mesmo para a mesma maquina
# (pelo machine-id). Nenhum e nome de emulador (nada de DOLPHIN).
NAMES = (
    "ACAI", "ACEROLA", "APPLE", "APRICOT", "AVOCADO", "BANANA", "BLACKBERRY", "BLUEBERRY", "CASHEW",
    "CHERRY", "CLEMENTINE", "COCONUT", "CRANBERRY", "CUPUACU", "DRAGONFRUIT", "DURIAN", "ELDERBERRY",
    "FIG", "GOOSEBERRY", "GRAPE", "GRAPEFRUIT", "GUAVA", "JABUTICABA", "JACKFRUIT", "KIWI", "KUMQUAT",
    "LEMON", "LIME", "LYCHEE", "MANGO", "MELON", "MULBERRY", "NECTARINE", "ORANGE", "PAPAYA",
    "PASSIONFRUIT", "PEACH", "PEAR", "PERSIMMON", "PINEAPPLE", "PITAYA", "PLUM", "POMEGRANATE", "QUINCE",
    "RAMBUTAN", "RASPBERRY", "STARFRUIT", "STRAWBERRY", "TAMARIND", "TANGERINE",
    "ALPACA", "ANTEATER", "ARMADILLO", "BADGER", "BEAVER", "BISON", "CAMEL", "CAPYBARA", "CHAMELEON",
    "CHEETAH", "EAGLE", "FALCON", "FLAMINGO", "FOX", "FROG", "GECKO", "GIRAFFE", "HAMSTER", "HEDGEHOG",
    "HIPPO", "IGUANA", "JAGUAR", "KOALA", "LEOPARD", "LION", "LLAMA", "LYNX", "MEERKAT", "MOOSE",
    "OCTOPUS", "OTTER", "OWL", "PANDA", "PANTHER", "PARROT", "PELICAN", "PENGUIN", "PUFFIN", "RABBIT",
    "RACCOON", "RHINO", "SEAL", "SHARK", "SLOTH", "SQUIRREL", "TAPIR", "TIGER", "TOUCAN", "TURTLE",
    "WALRUS",
)


def clean_name(text):
    """O apelido como a tela o mostra: maiusculas sem acento, so letras,
    algarismos, espaco e hifen (o que as duas fontes do frontend tem), ate
    NAME_MAX. Vazio se nao sobra nada."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).upper()
    text = re.sub(r"[^A-Z0-9 -]+", "", text)
    return " ".join(text.split())[:NAME_MAX].strip()


def default_name(ident):
    """A fruta ou o bicho deste gabinete (o mesmo a cada boot)."""
    return NAMES[int(hashlib.sha1((ident or "").encode()).hexdigest(), 16) % len(NAMES)]


def cabinet_name(ident, conf=None):
    """O apelido do fliperos.conf (cabinet_name=) ou, sem ele, default_name."""
    try:
        with open(conf or CONF, encoding="utf-8", errors="replace") as f:
            for line in f:
                key, _, value = line.rstrip("\n").partition("=")
                if key == "cabinet_name" and clean_name(value):
                    return clean_name(value)
    except OSError:
        pass
    return default_name(ident)


# ── A interface cabeada ────────────────────────────────────────────

def iface_addr(name, request):
    if fcntl is None:
        return None
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        packed = fcntl.ioctl(s.fileno(), request, struct.pack("256s", name.encode()[:15]))
        return socket.inet_ntoa(packed[20:24])
    except OSError:
        return None
    finally:
        s.close()


def wired(root="/sys/class/net", addr=iface_addr):
    """A interface cabeada: fisica, sem ser Wi-Fi, com o cabo ligado e um
    IPv4. None se nao ha (e entao nao ha link nem net play). Os testes
    escolhem a interface com FLIPEROS_LINK_WIRE=NOME,IP,BROADCAST."""
    forced = os.environ.get("FLIPEROS_LINK_WIRE")
    if forced:
        name, ip, broadcast = forced.split(",")
        return Wire(name, ip, "255.0.0.0", broadcast)
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return None
    for name in names:
        if name.startswith(VIRTUAL):
            continue
        base = os.path.join(root, name)
        if not os.path.exists(os.path.join(base, "device")):
            continue
        if os.path.exists(os.path.join(base, "wireless")) or os.path.exists(os.path.join(base, "phy80211")):
            continue
        try:
            with open(os.path.join(base, "operstate")) as f:
                if f.read().strip() != "up":
                    continue
        except OSError:
            continue
        ip = addr(name, 0x8915)             # SIOCGIFADDR
        mask = addr(name, 0x891b)           # SIOCGIFNETMASK
        if ip and mask:
            return Wire(name, ip, mask, broadcast_of(ip, mask))
    return None


def broadcast_of(ip, mask):
    a, m = struct.unpack("!I", socket.inet_aton(ip))[0], struct.unpack("!I", socket.inet_aton(mask))[0]
    return socket.inet_ntoa(struct.pack("!I", a | (~m & 0xffffffff)))


def same_net(wire, ip):
    try:
        a = struct.unpack("!I", socket.inet_aton(ip))[0]
        b = struct.unpack("!I", socket.inet_aton(wire.ip))[0]
        m = struct.unpack("!I", socket.inet_aton(wire.mask))[0]
    except OSError:
        return False
    return a & m == b & m


# ── Os perfis ──────────────────────────────────────────────────────

class Profiles:
    """Os jogos de link (link-profiles.json): achar o perfil de um jogo pelo
    sistema e pelo set."""

    def __init__(self, path=PROFILES):
        try:
            with open(path) as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {}
        self.games = data.get("games") or []

    def find(self, system, name):
        """O perfil do jogo (a chave do sistema, ex. model3, e o set), ou None."""
        key = (system or "").split("/")[0]
        for p in self.games:
            if key in p["systems"] and name in p["sets"]:
                return p
        return None

    def get(self, pid):
        return next((p for p in self.games if p["id"] == pid), None)


# ── A presenca ─────────────────────────────────────────────────────

class Presence:
    """O que cada gabinete diz de si pelo broadcast da sub-rede cabeada, e a
    tabela do que os outros dizem. say() muda o que este diz (jogo, festa,
    vagas, estado); table() devolve os outros."""

    def __init__(self, wire, ident, name, port=PORT_PRESENCE, targets=None, expire=EXPIRE, interval=INTERVAL,
                 clock=time.monotonic):
        self.wire, self.ident, self.name, self.port = wire, ident, name, port
        self.targets = targets or [(wire.broadcast, port)]
        self.expire, self.interval, self.clock = expire, interval, clock
        self.info = {}
        self.seen = {}
        self.lock = threading.Lock()
        self.stopped = threading.Event()
        self.rx = self.tx = None
        self.threads = []

    def start(self):
        self.rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            self.rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        # Presa ao broadcast da sub-rede cabeada: o que vem de outra interface
        # nao chega aqui. Onde nao se prende ao endereco de broadcast (o
        # Windows, dos testes de bancada), recebe de todas e hear() confere de
        # que sub-rede veio.
        try:
            self.rx.bind((self.wire.broadcast, self.port))
        except OSError:
            self.rx.bind(("", self.port))
        self.rx.settimeout(0.3)
        self.tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tx.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.tx.bind((self.wire.ip, 0))
        for fn in (self.listen, self.announce):
            t = threading.Thread(target=fn, daemon=True)
            t.start()
            self.threads.append(t)

    def stop(self):
        self.stopped.set()
        for t in self.threads:
            t.join(1.5)
        for s in (self.rx, self.tx):
            if s:
                s.close()

    def say(self, **info):
        """Troca o que este gabinete diz; o que vale None sai. Avisa na hora."""
        with self.lock:
            for k, v in info.items():
                if v is None:
                    self.info.pop(k, None)
                else:
                    self.info[k] = v
        self.send()

    def packet(self):
        with self.lock:
            body = dict(self.info)
        body.update(v=1, id=self.ident, name=self.name, ip=self.wire.ip)
        return json.dumps(body, separators=(",", ":")).encode()

    def send(self):
        if not self.tx:
            return
        data = self.packet()
        for target in self.targets:
            try:
                self.tx.sendto(data, target)
            except OSError:
                pass

    def announce(self):
        while not self.stopped.wait(self.interval):
            self.send()

    def listen(self):
        while not self.stopped.is_set():
            try:
                data, (src, _) = self.rx.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                return
            self.hear(data, src)

    def hear(self, data, src):
        try:
            rec = json.loads(data.decode())
        except (ValueError, UnicodeDecodeError):
            return
        if not isinstance(rec, dict) or rec.get("v") != 1 or rec.get("id") in (None, self.ident):
            return
        # So a sub-rede do cabo: o IP de quem fala tem de ser dela, e o que
        # ele diz de si tem de bater com de onde veio.
        if not same_net(self.wire, src) or rec.get("ip") != src:
            return
        with self.lock:
            self.seen[rec["id"]] = (rec, self.clock())

    def table(self):
        """Os outros gabinetes (os registros que chegaram ha menos de EXPIRE s)."""
        now = self.clock()
        with self.lock:
            for k in [k for k, (_, t) in self.seen.items() if now - t > self.expire]:
                del self.seen[k]
            return sorted((r for r, _ in self.seen.values()), key=lambda r: (r.get("name", ""), r["id"]))


def parties(table):
    """As festas que a tabela mostra: uma por festa (o id do anfitriao), com
    o jogo, o perfil, quantos ja entraram, o maximo e o estado (lobby: aberta;
    playing: ja comecou, e so aceita gente com open, a party do RetroArch). Os
    que nao estao numa festa ficam de fora."""
    out = {}
    for rec in table:
        pid = rec.get("party")
        if not pid:
            continue
        p = out.setdefault(pid, {"party": pid, "game": rec.get("game"), "system": rec.get("system"),
                                 "link": rec.get("link"), "max": rec.get("max"), "state": rec.get("state"),
                                 "host_ip": None, "host": None, "open": False, "numbers": [], "slots": 0})
        if rec.get("slot") == 1:
            p["host_ip"], p["host"] = rec.get("ip"), rec.get("name")
            p["max"], p["state"], p["open"] = rec.get("max"), rec.get("state"), bool(rec.get("open"))
        if rec.get("slot"):
            p["numbers"].append(rec["slot"])
            p["slots"] += rec.get("take") or 1
    for p in out.values():
        p["numbers"].sort()
        p["used"] = p.pop("slots")
    return sorted(out.values(), key=lambda p: (p["state"] != "playing", p["game"] or ""))


def joinable(party):
    """Da para entrar: a sala esta aberta (ou a party ja anda e aceita quem
    chega) e ha vaga."""
    return (party["state"] == "lobby" or party.get("open")) and party["used"] < (party["max"] or 0)


# ── A festa ────────────────────────────────────────────────────────

def make_plan(profile, members):
    """O que a festa manda no comeco: quantos sao, o numero e o IP de cada
    um e o atraso de cada um (a ordem de subida do perfil)."""
    n = len(members)
    numbers = [m["number"] for m in members]
    if profile["order"] == "slaves-first" and n > 2:
        order = sorted(numbers[1:], reverse=True) + numbers[:1]
    else:
        order = list(numbers)
    step = profile.get("step", 6)
    return {"profile": profile["id"], "n": n, "order": order, "step": step,
            "members": [{"number": m["number"], "name": m["name"], "ip": m["ip"], "take": m.get("take", 1),
                         "first": m.get("first", m["number"])} for m in members],
            "delays": {str(num): order.index(num) * step for num in numbers}}


def send_line(conn, obj):
    try:
        conn.sendall(json.dumps(obj, separators=(",", ":")).encode() + b"\n")
        return True
    except OSError:
        return False


def read_lines(conn):
    """As mensagens que chegam (um JSON por linha), ate a conexao cair."""
    buf = b""
    while True:
        try:
            chunk = conn.recv(4096)
        except OSError:
            return
        if not chunk:
            return
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            try:
                yield json.loads(line.decode())
            except ValueError:
                continue


class PartyHost:
    """A festa de quem abre o jogo: o numero 1. Escuta quem quer entrar, mantem
    a sala e, no start(), fixa os numeros e manda o plano a todos."""

    def __init__(self, wire, profile, game, ident, name, port=PORT_PARTY, on_change=None, take=1):
        self.wire, self.profile, self.game = wire, profile, game
        self.ident, self.name, self.port = ident, name, port
        self.on_change = on_change or (lambda: None)
        self.members = [{"id": ident, "name": name, "ip": wire.ip, "conn": None, "take": max(1, take)}]
        self.state = "lobby"
        self.plan = None
        self.lock = threading.Lock()
        self.sock = None

    def open(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.wire.ip, self.port))
        self.sock.listen(8)
        self.sock.settimeout(0.3)
        threading.Thread(target=self.accept, daemon=True).start()

    def numbered(self):
        """Os gabinetes da festa em ordem, cada um com o numero, quantos
        jogadores ocupa (take) e o primeiro deles (first). Num jogo de link cada
        gabinete e um; no net play, tantos quantos os controles dele. Depois do
        comeco o first de cada um fica fixo (o jogo ja os tem nesses lugares)."""
        out, first = [], 1
        for i, m in enumerate(self.members):
            first = m.get("first") or first
            out.append({"number": i + 1, "name": m["name"], "ip": m["ip"], "take": m["take"], "first": first})
            first += m["take"]
        return out

    def late_open(self):
        """A party que ja comecou e ainda aceita quem chega (a do RetroArch)."""
        return bool(self.profile.get("late")) and self.state == "playing"

    def free_place(self, want):
        """(first, take) de quem chega com o jogo andando: os primeiros lugares
        livres em sequencia, com ate want jogadores (menos, se nao ha tantos
        juntos). None se nao ha lugar."""
        busy = set()
        for m in self.members:
            busy.update(range(m["first"], m["first"] + m["take"]))
        cap = self.capacity()
        for take in range(max(1, want), 0, -1):
            for first in range(1, cap - take + 2):
                if not busy.intersection(range(first, first + take)):
                    return first, take
        return None

    def snapshot(self):
        with self.lock:
            return {"party": self.ident, "profile": self.profile["id"], "game": self.game, "state": self.state,
                    "min": self.profile["min"], "max": self.profile["max"], "fixed": self.profile["fixed"],
                    "capacity": self.capacity(), "members": self.numbered()}

    def count(self):
        return len(self.members)

    def capacity(self):
        """As vagas: os jogadores do jogo no net play, os gabinetes no link."""
        return self.profile.get("players") or self.profile["max"]

    def used(self):
        return sum(m["take"] for m in self.members)

    def full(self):
        return self.used() >= self.capacity()

    def ready(self):
        """Pode comecar: o minimo chegou (os de tamanho fixo, so com todos). A
        party do RetroArch comeca so com quem abriu."""
        n = self.count()
        if self.profile.get("late"):
            return True
        return n >= self.profile["min"] and (not self.profile["fixed"] or n == self.profile["max"])

    def accept(self):
        while self.state != "closed":
            try:
                conn, (src, _) = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            if not same_net(self.wire, src):
                conn.close()
                continue
            threading.Thread(target=self.serve, args=(conn, src), daemon=True).start()

    def serve(self, conn, src):
        member = None
        for msg in read_lines(conn):
            if msg.get("op") == "join" and member is None:
                why = None
                late = False
                with self.lock:
                    late = self.late_open()
                    place = None
                    take = 1
                    if self.profile.get("netplay"):
                        # Um gabinete ocupa um jogador por controle que tem,
                        # ate onde ha vagas.
                        try:
                            want = int(msg.get("want") or 1)
                        except (TypeError, ValueError):
                            want = 1
                        take = max(1, min(want, self.capacity() - self.used()))
                        if late:
                            place = self.free_place(take)
                    if self.state != "lobby" and not late:
                        why = "closed"
                    elif self.full() or (late and not place):
                        why = "full"
                    elif msg.get("game") != self.game:
                        why = "game"
                    else:
                        member = {"id": msg.get("id"), "name": clean_name(str(msg.get("name") or "")) or src, "ip": src,
                                  "conn": conn, "take": take}
                        if place:
                            member["first"], member["take"] = place
                        self.members.append(member)
                if why:
                    send_line(conn, {"op": "refused", "why": why})
                    break
                with self.lock:
                    number = self.members.index(member) + 1
                snap = self.snapshot()
                send_line(conn, {"op": "joined", "party": snap, "number": number})
                if late:
                    # O jogo ja anda: quem chega comeca na hora, com o seu lugar.
                    plan = make_plan(self.profile, snap["members"])
                    plan["delays"] = {str(number): 0}
                    send_line(conn, {"op": "start", "number": number, "plan": plan})
                self.share()
            elif msg.get("op") == "leave":
                break
        if member:
            self.drop(member)
        try:
            conn.close()
        except OSError:
            pass

    def drop(self, member):
        """Quem sai da sala (ou, na party que aceita gente com o jogo
        andando, quem fecha o jogo) libera o lugar."""
        with self.lock:
            if member in self.members and (self.state == "lobby" or self.late_open()):
                self.members.remove(member)
        self.share()

    def share(self):
        """Manda a sala a todos (e avisa o frontend)."""
        snap = self.snapshot()
        for number, m in enumerate(list(self.members), 1):
            if m["conn"] and not send_line(m["conn"], {"op": "state", "party": snap, "number": number}):
                with self.lock:
                    if m in self.members:
                        self.members.remove(m)
        self.on_change()

    def start(self):
        """Fixa os numeros e manda o plano (com o atraso de cada um). Devolve
        o plano, ou None se ainda nao da."""
        with self.lock:
            if self.state != "lobby" or not self.ready():
                return None
            self.state = "playing"
            members = self.numbered()
            for m, n in zip(self.members, members):
                m["first"] = n["first"]
        self.plan = make_plan(self.profile, members)
        for i, m in enumerate(self.members[1:], 2):
            send_line(m["conn"], {"op": "start", "number": i, "plan": self.plan})
        self.on_change()
        return self.plan

    def close(self):
        """A festa acaba: quem esta nela volta para a lista."""
        for m in list(self.members[1:]):
            send_line(m["conn"], {"op": "closed"})
            try:
                m["conn"].close()
            except OSError:
                pass
        with self.lock:
            self.state = "closed"
        if self.sock:
            self.sock.close()
        self.on_change()


class PartyGuest:
    """Quem entra na festa de outro gabinete."""

    def __init__(self, wire, ident, name, port=PORT_PARTY):
        self.wire, self.ident, self.name, self.port = wire, ident, name, port
        self.conn = None
        self.party = None
        self.number = None
        self.plan = None
        self.refused = None
        self.closed = False
        self.changed = threading.Event()

    def join(self, host_ip, game, timeout=3.0, want=1):
        """Entra. True se o anfitriao aceitou; senao self.refused diz porque
        (closed, full, game, ou down se nem atendeu)."""
        try:
            self.conn = socket.create_connection((host_ip, self.port), timeout=timeout)
        except OSError:
            self.refused = "down"
            return False
        self.conn.settimeout(None)
        send_line(self.conn, {"op": "join", "id": self.ident, "name": self.name, "game": game, "want": want})
        threading.Thread(target=self.listen, daemon=True).start()
        if not self.changed.wait(timeout):
            self.refused = self.refused or "down"
        if self.party is None or self.refused:
            self.leave()
            return False
        return True

    def listen(self):
        for msg in read_lines(self.conn):
            op = msg.get("op")
            if op in ("joined", "state"):
                self.party = msg["party"]
                self.number = msg.get("number", self.number)
            elif op == "refused":
                self.refused = msg.get("why") or "down"
            elif op == "start":
                self.plan, self.number = msg["plan"], msg["number"]
            elif op == "closed":
                self.closed = True
            self.changed.set()
        # A conexao caiu: se nao comecou, a festa acabou.
        if not self.plan:
            self.closed = True
        self.changed.set()

    def leave(self):
        if self.conn:
            send_line(self.conn, {"op": "leave"})
            try:
                self.conn.close()
            except OSError:
                pass


# ── O que cada emulador pede ───────────────────────────────────────

def neighbour(profile, plan, number):
    """O IP do gabinete que este conecta: no anel, o seguinte (o ultimo, o
    primeiro); na cadeia, o anterior (a cabeca nao conecta ninguem)."""
    ips = {m["number"]: m["ip"] for m in plan["members"]}
    n = plan["n"]
    if profile["order"] == "chain":
        return ips.get(number - 1)
    return ips[number % n + 1]


def link_args(profile, plan, number):
    """Os argumentos de link do emulador, para o fim do comando do jogo
    (sm2emu e groovymame: antes do nome do jogo, que o x11-run le por ultimo)."""
    port = profile["port"]
    nxt = neighbour(profile, plan, number)
    emu = profile["emulator"]
    if emu == "supermodel":
        return ["-net", "-port-in=%d" % port, "-port-out=%d" % port, "-address-out=%s" % nxt]
    if emu == "flycast" and profile.get("ggpo"):
        # O GGPO: cada lado manda para o IP do outro (network:server, nos dois: vazio e o
        # 127.0.0.1) e o servidor e o jogador 1. Sem atraso de entrada: no cabo o
        # rollback e raro. O UPnP fica desligado.
        other = next(m["ip"] for m in plan["members"] if m["number"] != number)
        return ["-config", "network:GGPO=yes,network:ActAsServer=%s,network:server=%s,network:GGPODelay=0,"
                "network:EnableUPnP=no" % ("yes" if number == 1 else "no", other)]
    if emu == "dolphin":
        # O net play do Dolphin pela linha de comando (o patch): o numero 1 abre a
        # sessao e comeca quando os gabinetes da festa chegam; os outros se
        # conectam a ele (e tentam de novo ate ele abrir). Direto, sem o servidor
        # de travessia nem UPnP; -b: o Dolphin fecha quando o jogo acaba.
        host = next(m["ip"] for m in plan["members"] if m["number"] == 1)
        args = ["-b", "--netplay", "host" if number == 1 else "join", "--netplay_players", str(plan["n"])]
        # BufferSize: o atraso de entrada do Dolphin (sem rollback); 5 de fabrica, 2 no cabo.
        for key, value in (("TraversalChoice", "direct"), ("UseUPNP", "False"), ("BufferSize", 2), ("HostPort", port),
                           ("ConnectPort", port), ("Address", host), ("Nickname", "P%d" % number)):
            args += ["-C", "Dolphin.NetPlay.%s=%s" % (key, value)]
        return args
    if emu == "flycast":
        # A rede do Naomi do Flycast (UDP, porta 37391): o numero 1 e o servidor, os outros se
        # conectam a ele. O UPnP fica desligado: nada de pedir ao roteador (e a Internet) que
        # abra a porta.
        role = "network:Enable=yes,network:ActAsServer=yes" if number == 1 else \
            "network:Enable=yes,network:ActAsServer=no,network:server=%s" % plan["members"][0]["ip"]
        return ["-config", role + ",network:EnableUPnP=no"]
    if emu == "groovymame":
        # A cadeia: a cabeca nao conecta ninguem e o fim nao escuta.
        return ["-comm_localhost", "" if number == plan["n"] else "0.0.0.0", "-comm_localport", str(port),
                "-comm_remotehost", nxt or "", "-comm_remoteport", str(port)]
    return []


def sm2_keys(profile, plan, number, ip):
    """As chaves de [network] do ini do SM2-Emu (o parser as le em qualquer
    lugar do arquivo): o anel de UDP."""
    return {"link_enabled": "true", "link_local_ip": "", "link_port": str(profile["port"]),
            "link_next_ip": neighbour(profile, plan, number), "link_next_port": str(profile["port"])}


def command(profile, base, plan, number, game):
    """O comando do jogo em link. base: o do frontend (fedata command), que
    termina no nome do jogo (sm2emu, groovymame) ou no arquivo (supermodel)."""
    argv = list(base)
    extra = link_args(profile, plan, number)
    if profile["emulator"] == "supermodel":
        return argv + extra
    if profile["emulator"] == "sm2emu":
        # --game antes do jogo: o x11-run le o ultimo argumento como o jogo.
        return argv[:-1] + ["--game", game] + argv[-1:]
    if len(argv) > 1 and argv[-2] in ("-e", "--exec"):
        # O Dolphin: o arquivo vem depois do -e.
        return argv[:-2] + extra + argv[-2:]
    return argv[:-1] + extra + argv[-1:]


INPUT_DEVICES = os.environ.get("FLIPEROS_INPUT_DEVICES", "/proc/bus/input/devices")


def connected_joysticks(path=None):
    """Quantos joysticks estao ligados agora (os aparelhos com js do
    /proc/bus/input/devices; a mesma conta do fliperos-buttons players, sem as
    pistolas de luz: o aparelho que tambem e mouse nao e um jogador)."""
    count = 0
    try:
        with open(path or INPUT_DEVICES, encoding="utf-8", errors="replace") as f:
            for line in f:
                if (line.startswith("H: Handlers=") and re.search(r"\bjs\d+\b", line)
                        and not re.search(r"\bmouse\d+\b", line)):
                    count += 1
    except OSError:
        return None
    return count


def local_players(path=None, proc=None):
    """Quantos jogadores este gabinete tem agora: os do Button mapping
    (/etc/fliperos/buttons.map) cujo controle esta ligado. Soltar um controle
    tira o jogador dele, e ligar de volta o devolve; o de teclado (encoder que
    se diz teclado) conta sempre. FLIPEROS_LOCAL_PLAYERS manda; sem mapa, 2; e
    nunca menos de 1 (o gabinete ainda joga, ao menos pelo teclado)."""
    forced = os.environ.get("FLIPEROS_LOCAL_PLAYERS")
    if forced and forced.isdigit() and int(forced) > 0:
        return int(forced)
    index = {}
    try:
        with open(path or BUTTONS_MAP, encoding="utf-8") as f:
            for line in f:
                parts = line.split(None, 3)
                if len(parts) >= 3 and parts[0].isdigit() and parts[2].lstrip("-").isdigit():
                    index.setdefault(int(parts[0]), []).append(int(parts[2]))
    except OSError:
        pass
    if not index:
        return 2
    connected = connected_joysticks(proc)
    if connected is None:
        return len(index)
    active = [p for p, idx in index.items() if all(i < 0 for i in idx) or all(i < connected for i in idx if i >= 0)]
    return max(1, len(active))


_fbneo = {}


def fbneo_sets(path=None):
    """Os sets do FBNeo, de todos os sistemas (o indice do fliperos-fbneo:
    "pasta<TAB>set<TAB>pai<TAB>crcs"; um de console o fliperos-kms-run poe na
    pasta do sistema). Vazio se nao ha indice: sem ele nenhum jogo do FBNeo tem
    net play."""
    path = path or FBNEO_INDEX
    if path not in _fbneo:
        sets = set()
        try:
            with lzma.open(path, "rt", encoding="utf-8") as f:
                for line in f:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) >= 2:
                        sets.add(parts[1])
        except (OSError, lzma.LZMAError, EOFError):
            pass
        _fbneo[path] = frozenset(sets)
    return _fbneo[path]


_states = {}


def netplay_core(system_key):
    """O core de uma pasta do RetroArch (retroarch/<core>) que faz net play, ou
    None: instalado e com savestate_features = "deterministic" no .info, que e
    o que o proprio RetroArch pede para o net play (o MAME 2010 nao salva
    estado, o Flycast so "serialized")."""
    if not (system_key or "").startswith("retroarch/"):
        return None
    core = system_key.split("/", 1)[1]
    so = os.path.join(RA_CORES, core + "_libretro.so")
    info = os.path.join(RA_INFO, core + "_libretro.info")
    if info not in _states:
        state = ""
        try:
            with open(info, encoding="utf-8", errors="replace") as f:
                for line in f:
                    key, _, value = line.partition("=")
                    if key.strip() == "savestate_features":
                        state = value.strip().strip('"')
        except OSError:
            pass
        _states[info] = state
    return so if _states[info] == "deterministic" and os.path.isfile(so) else None


_dolphin = {}


def dolphin_netplay(path=None):
    """O Dolphin instalado tem o --netplay do patch do FliperOS? (procura a
    opcao no binario, uma vez por arquivo e data)."""
    path = path or DOLPHIN
    try:
        key = (path, os.stat(path).st_mtime)
    except OSError:
        return False
    if key not in _dolphin:
        found, tail = False, b""
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                if b"netplay_players" in tail + chunk:
                    found = True
                    break
                tail = chunk[-32:]
        _dolphin[key] = found
    return _dolphin[key]


def netplay_profile(system_key, name, players, local, sets=None):
    """O perfil de net play de um jogo, ou None. Numa pasta de core do
    RetroArch que faz net play (netplay_core; na do FBNeo, so um set que o
    FBNeo conhece), um jogo com mais jogadores do que controles aqui: cada
    gabinete entra com os jogadores dos seus controles. No Naomi e no
    Atomiswave, o GGPO do Flycast: um jogo de dois ou mais jogadores, dois
    gabinetes com um jogador cada. No Dolphin, de dois a quatro gabinetes,
    um jogador cada. Quem abre e o primeiro. No RetroArch (late) quem abre
    nao espera ninguem: o jogo abre na hora e os outros entram com ele
    andando, como o net play do RetroArch deixa; o GGPO e o Dolphin precisam
    de todos no comeco."""
    try:
        n = int(players)
    except (TypeError, ValueError):
        return None
    if (system_key or "").split("/")[0] in GGPO_SYSTEMS:
        if n < 2:
            return None
        return {"id": "netplay", "title": name, "emulator": "flycast", "systems": [system_key], "sets": [name],
                "min": 2, "max": 2, "players": 2, "take": 1, "fixed": True, "order": "master-first", "step": 6,
                "port": PORT_GGPO, "netplay": True, "ggpo": True}
    if (system_key or "").split("/")[0] in DOLPHIN_SYSTEMS:
        if n < 2 or not dolphin_netplay():
            return None
        return {"id": "netplay", "title": name, "emulator": "dolphin", "systems": [system_key], "sets": [name],
                "min": 2, "max": min(n, 4), "players": min(n, 4), "take": 1, "fixed": False,
                "order": "master-first", "step": 3, "port": PORT_DOLPHIN, "netplay": True, "dolphin": True}
    core = netplay_core(system_key)
    if not core or n <= local:
        return None
    if system_key == "retroarch/fbneo" and name not in (fbneo_sets() if sets is None else sets):
        return None
    return {"id": "netplay", "title": name, "emulator": "retroarch", "systems": [system_key], "sets": [name],
            "min": 2, "max": n, "players": n, "fixed": False, "order": "master-first", "step": 6,
            "port": PORT_NETPLAY, "netplay": True, "late": True, "core": core}


NETPLAY_CFG = """# O net play do FliperOS: so a rede local, so pelo cabo. Nada de servidor
# publico, de retransmissao nem de travessia de NAT.
netplay_public_announce = "false"
netplay_use_mitm_server = "false"
netplay_nat_traversal = "false"
netplay_input_latency_frames_min = "0"
netplay_input_latency_frames_range = "0"
netplay_check_frames = "600"
netplay_allow_slaves = "false"
netplay_max_connections = "%d"
"""


def netplay_cfg(profile, slots):
    """A config do net play deste gabinete: a de cima e os jogadores que ele
    ocupa (netplay_request_device_pN), um por controle configurado."""
    text = NETPLAY_CFG % profile["max"]
    return text + "".join('netplay_request_device_p%d = "true"\n' % k for k in slots)


def netplay_command(profile, plan, number, rom, name, cfg, core=None):
    """O RetroArch do net play: o numero 1 abre o jogo (--host) e os outros se
    conectam a ele (--connect), depois de o plano dar o atraso de cada um. A
    ROM vai por ultimo: o fliperos-kms-run le o jogo dali (os botoes dele, o
    set de console do FBNeo na pasta do sistema)."""
    argv = [KMS_RUN, "retroarch", "-L", core or profile["core"], "--appendconfig", cfg, "--nick", name,
            "--port", str(profile["port"])]
    if number == 1:
        return argv + ["--host", rom]
    host = next(m["ip"] for m in plan["members"] if m["number"] == 1)
    return argv + ["--connect", host, rom]


def ini_set(path, keys):
    """Troca (ou acrescenta) as chaves no ini; devolve o texto de antes, para voltar."""
    try:
        with open(path) as f:
            before = f.read()
    except OSError:
        before = ""
    lines = before.splitlines()
    for key, value in keys.items():
        for i, line in enumerate(lines):
            if line.split("=")[0].strip() == key:
                lines[i] = "%s = %s" % (key, value)
                break
        else:
            lines.append("%s = %s" % (key, value))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return before


# ── A NVRAM de cada gabinete ───────────────────────────────────────

def nvram_files(profile, number, home, src=None):
    """(origem, destino) de cada arquivo da NVRAM deste numero, ou [] se o
    perfil nao tem (ou a pasta nao tem o arquivo desse numero)."""
    spec = profile.get("nvram")
    if not spec:
        return []
    src = src or NVRAM_SRC
    out = []
    for ext, name in spec["files"].items():
        origin = os.path.join(src, spec["dir"], "cabinet%d.%s" % (number, ext))
        if os.path.isfile(origin):
            out.append((origin, os.path.join(home, spec["dest"], name)))
    return out


def place_files(home, items):
    """Poe cada (destino, origem) no lugar: origem e o caminho de um arquivo ou
    os bytes do que se grava. O arquivo que la havia vai para NOME.solo (so o
    primeiro: um .solo que ja existe e o da pessoa) e volta no restore(). A
    lista do que foi mexido fica em ~/nvram/.link-active, para um frontend que
    reabre depois de uma queda desfazer (recover)."""
    import shutil
    marker = os.path.join(home, "nvram", ".link-active")
    done = []
    try:
        with open(marker) as f:
            done = json.load(f)
    except (OSError, ValueError):
        pass
    for dest, origin in items:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.exists(dest) and not os.path.exists(dest + SOLO):
            os.replace(dest, dest + SOLO)
        if isinstance(origin, bytes):
            with open(dest, "wb") as f:
                f.write(origin)
        else:
            shutil.copyfile(origin, dest)
        if dest not in done:
            done.append(dest)
    if done:
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "w") as f:
            json.dump(done, f)
    return lambda: recover(home)


def install_nvram(profile, number, home, src=None):
    """Poe a NVRAM do numero onde o emulador a le (place_files)."""
    return place_files(home, [(dest, origin) for origin, dest in nvram_files(profile, number, home, src)])


def mame_cfg(tag, value, game):
    """O cfg de um jogo do MAME com um so item da Machine Configuration ligado
    (o :comm:CFG do Tournament Battle; o dois pontos do comeco e parte do tag)."""
    return ('<?xml version="1.0"?>\n<mamecfg version="10">\n    <system name="%s">\n        <input>\n'
            '            <port tag="%s" type="CONFIG" mask="1" defvalue="0" value="%s" />\n'
            '        </input>\n    </system>\n</mamecfg>\n' % (game, tag, value)).encode()


def recover(home):
    """Desfaz install_nvram: tira a NVRAM da festa e volta a da pessoa."""
    marker = os.path.join(home, "nvram", ".link-active")
    try:
        with open(marker) as f:
            done = json.load(f)
    except (OSError, ValueError):
        return
    for dest in done:
        try:
            os.remove(dest)
        except OSError:
            pass
        if os.path.exists(dest + SOLO):
            os.replace(dest + SOLO, dest)
    try:
        os.remove(marker)
    except OSError:
        pass


# ── Os arquivos de um jogo ─────────────────────────────────────────

def game_files(roots, relpaths):
    """O que o jogo pede: [(caminho relativo, tamanho, sha256)] dos arquivos
    que existem. roots: as pastas-base (home); relpaths: relativos a ela."""
    out = []
    for rel in relpaths:
        path = os.path.join(roots, rel)
        if os.path.isfile(path):
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            out.append({"path": rel, "size": os.path.getsize(path), "sha256": h.hexdigest()})
    return out


class FileServer:
    """Serve os arquivos do jogo a quem entra na festa sem eles, so na
    interface cabeada: /manifest (o que o jogo pede e o que ha) e /file/CAMINHO
    (com Range, para retomar). So serve o que esta em allow (a lista de
    caminhos relativos a home) e para IPs da sub-rede do cabo."""

    def __init__(self, wire, home, allow, port=PORT_FILES):
        self.wire, self.home, self.allow, self.port = wire, home, set(allow), port
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if not same_net(outer.wire, self.client_address[0]):
                    return self.send_error(403)
                if self.path == "/manifest":
                    body = json.dumps(game_files(outer.home, sorted(outer.allow))).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if self.path.startswith("/file/"):
                    rel = unquote(self.path[len("/file/"):])
                    if rel not in outer.allow:
                        return self.send_error(404)
                    path = os.path.join(outer.home, rel)
                    try:
                        size = os.path.getsize(path)
                        start = 0
                        rng = self.headers.get("Range", "")
                        if rng.startswith("bytes=") and rng.endswith("-"):
                            start = int(rng[6:-1])
                        f = open(path, "rb")
                    except (OSError, ValueError):
                        return self.send_error(404)
                    with f:
                        f.seek(start)
                        self.send_response(206 if start else 200)
                        self.send_header("Content-Length", str(size - start))
                        self.end_headers()
                        while True:
                            chunk = f.read(1 << 20)
                            if not chunk:
                                break
                            try:
                                self.wfile.write(chunk)
                            except OSError:
                                break
                    return
                self.send_error(404)

        self.httpd = ThreadingHTTPServer((wire.ip, port), Handler)

    def start(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def fetch_files(host_ip, home, wanted=None, port=PORT_FILES, progress=None):
    """Copia do anfitriao os arquivos que faltam ou diferem (wanted: os
    caminhos relativos que o jogo pede; sem ele, tudo o que o anfitriao
    serve). Cada um vem para NOME.part, e so vira o arquivo depois de
    conferido (o sha256 do manifesto); uma queda retoma do que ja veio.
    progress(feitos, total, caminho). Devolve (ok, faltou)."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://%s:%d/manifest" % (host_ip, port), timeout=5) as r:
            manifest = {m["path"]: m for m in json.load(r)}
    except (OSError, ValueError):
        return False, list(wanted or [])
    if wanted is None:
        wanted = list(manifest)
    todo = [manifest[p] for p in wanted if p in manifest]
    missing = [p for p in wanted if p not in manifest]
    total = sum(m["size"] for m in todo)
    done = 0
    for m in todo:
        dest = os.path.join(home, m["path"])
        if os.path.isfile(dest) and os.path.getsize(dest) == m["size"] and sha256_of(dest) == m["sha256"]:
            done += m["size"]
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        part = dest + ".part"
        have = os.path.getsize(part) if os.path.exists(part) else 0
        if have > m["size"]:
            have = 0
        req = urllib.request.Request("http://%s:%d/file/%s" % (host_ip, port, quote(m["path"])))
        if have:
            req.add_header("Range", "bytes=%d-" % have)
        try:
            with urllib.request.urlopen(req, timeout=10) as r, open(part, "ab" if have else "wb") as f:
                got = have
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
                    got += len(chunk)
                    if progress:
                        progress(done + got, total, m["path"])
        except OSError:
            return False, [x["path"] for x in todo[todo.index(m):]] + missing
        if sha256_of(part) != m["sha256"]:
            os.remove(part)
            return False, [m["path"]] + missing
        os.replace(part, dest)
        done += m["size"]
    return not missing, missing


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ── O link deste gabinete, para o frontend ─────────────────────────

COUNTDOWN = 3.0          # segundos de "STARTING" depois que a festa manda o plano
WIRE_CHECK = 5.0         # de quantos em quantos segundos olha se o cabo mudou
REASONS = {"closed": "THE PARTY ALREADY STARTED", "full": "THE PARTY IS FULL", "game": "NOT THE SAME GAME",
           "down": "NO ANSWER FROM THE OTHER CABINET"}


def machine_id():
    try:
        with open("/etc/machine-id") as f:
            return f.read().strip()[:12]
    except OSError:
        return socket.gethostname()


class Link:
    """O que o frontend usa: presenca na rede cabeada, a festa deste gabinete
    (anfitriao ou convidado), a contagem do comeco e o comando do jogo em
    link. Sem cabo, available() e falso e nada mais faz nada."""

    def __init__(self, home, profiles=None, wire=False, ident=None, name=None, ports=None, clock=time.monotonic,
                 local_players=None):
        self.home = home
        self.fixed_players = local_players       # os testes fixam; sem isso, segue os controles ligados
        self.seen_players = (None, 0.0)
        self.profiles = profiles or Profiles()
        self.wire = wired() if wire is False else wire
        self.ident = ident or machine_id()
        self.name = name or cabinet_name(self.ident)
        self.ports = ports or {}
        self.clock = clock
        self.presence = None
        self.checked = clock()
        self.reset()

    @property
    def local_players(self):
        """Os jogadores deste gabinete agora (local_players): a conta e relida de
        2 em 2 segundos, para soltar ou ligar um controle valer sem reabrir nada."""
        if self.fixed_players:
            return self.fixed_players
        n, at = self.seen_players
        now = self.clock()
        if n is None or now - at >= 2.0:
            n = globals()["local_players"]()
            self.seen_players = (n, now)
        return n

    @local_players.setter
    def local_players(self, value):
        self.fixed_players = value

    def reset(self):
        self.role = None              # "host", "guest" ou None
        self.party = None             # a PartyHost
        self.guest = None             # o PartyGuest
        self.files = None             # o FileServer (so o anfitriao)
        self.profile = self.game = self.system = self.rom = None
        self.take = 1              # quantos jogadores este gabinete ocupa (net play: os controles dele)
        self.plan = self.number = None
        self.launch_at = None
        self.undo = []
        self.message = None

    # ── Ligar e desligar ──
    def start(self):
        """Abre a presenca na interface cabeada. False sem cabo."""
        if not self.wire or self.presence:
            return bool(self.presence)
        try:
            self.presence = Presence(self.wire, self.ident, self.name, port=self.ports.get("presence", PORT_PRESENCE))
            self.presence.start()
        except OSError:
            self.presence = None
            return False
        self.presence.say(state="idle")
        return True

    def stop(self):
        self.leave()
        if self.presence:
            self.presence.stop()
            self.presence = None

    def available(self):
        return self.presence is not None

    def poll(self, now):
        """O cabo solto ou posto: a presenca e a festa saem, ou voltam."""
        if now - self.checked < WIRE_CHECK:
            return
        self.checked = now
        wire = wired()
        if wire != self.wire:
            self.stop()
            self.wire = wire
            self.start()

    # ── O que se ve ──
    def profile_of(self, system_key, name):
        return self.profiles.find(system_key, name) if self.available() else None

    def netplay_of(self, system_key, name, players):
        """O perfil de net play do jogo (so com cabo), ou None."""
        if not self.available() or self.profiles.find(system_key, name):
            return None
        return netplay_profile(system_key, name, players, self.local_players)

    def table(self):
        return self.presence.table() if self.presence else []

    def parties(self):
        return parties(self.table())

    def parties_for(self, system_key, name):
        """As festas do jogo. Uma pasta de core do RetroArch e um sistema
        inteiro (o "sonic" do Mega Drive nao e o do FBNeo); as outras valem
        pela primeira parte da chave."""
        def key(k):
            k = k or ""
            return k if k.startswith("retroarch/") else k.split("/")[0]
        return [p for p in self.parties() if p["game"] == name and key(p["system"]) == key(system_key)]

    def mark(self, system_key, name):
        """None: o jogo nao tem link. False: tem, e ninguem joga. True: alguem joga."""
        if not self.profile_of(system_key, name):
            return None
        return bool(self.parties_for(system_key, name))

    # ── A festa ──
    def say(self):
        """Diz na rede o que este gabinete faz (ou que nao faz nada)."""
        if not self.presence:
            return
        if not self.role:
            self.presence.say(game=None, system=None, link=None, party=None, slot=None, max=None, state="idle")
            return
        state = "playing" if self.plan else "lobby"
        host = self.party
        # open: a party ja comecou e ainda aceita quem chega (so o anfitriao diz).
        late = bool(host and host.late_open() and not host.full())
        self.presence.say(game=self.game, system=self.system, link=self.profile["id"],
                          party=host.ident if host else self.guest.party["party"], slot=self.number or 1,
                          take=self.take, max=self.profile["players"] if self.profile.get("netplay") else self.profile["max"],
                          state=state, open=1 if late else None)

    def max_take(self, profile):
        """Quantos jogadores este gabinete pode ocupar: no net play, um por
        controle daqui (no GGPO, um so); num jogo de link, um."""
        if not (profile or {}).get("netplay"):
            return 1
        return max(1, min(self.local_players, profile.get("take") or profile["players"]))

    def host_game(self, profile, system_key, name, files, rom=None, take=None):
        """Abre a festa deste gabinete (o numero 1) e serve os arquivos do jogo.
        files: os caminhos (relativos ao home) que quem entra sem o jogo copia.
        take: os jogadores que este gabinete fornece (de 1 a max_take; None, todos)."""
        self.leave()
        try:
            take = max(1, min(self.max_take(profile), take or 99))
            party = PartyHost(self.wire, profile, name, self.ident, self.name, port=self.ports.get("party", PORT_PARTY),
                              on_change=self.say, take=take)
            party.open()
        except OSError:
            self.message = "COULD NOT OPEN THE PARTY"
            return None
        try:
            server = FileServer(self.wire, self.home, files, port=self.ports.get("files", PORT_FILES))
            server.start()
        except OSError:
            server = None
        self.role, self.party, self.files = "host", party, server
        self.profile, self.game, self.system, self.number, self.rom = profile, name, system_key, 1, rom
        self.take = take
        self.say()
        return party

    def join_party(self, party, profile, system_key, name, rom=None, take=None):
        """Entra na festa de outro gabinete. False (e self.message) se nao deu.
        take: os jogadores que este gabinete pede (None, um por controle)."""
        self.leave()
        guest = PartyGuest(self.wire, self.ident, self.name, port=self.ports.get("party", PORT_PARTY))
        want = max(1, min(self.max_take(profile), take or 99))
        if not guest.join(party["host_ip"], name, want=want):
            self.message = REASONS.get(guest.refused, REASONS["down"])
            return False
        self.role, self.guest = "guest", guest
        self.profile, self.game, self.system, self.number, self.rom = profile, name, system_key, guest.number, rom
        self.take = self.mine(guest.party, guest.number)["take"]
        self.say()
        return True

    @staticmethod
    def mine(snap, number):
        """O gabinete de numero `number` na sala (take, first), ou take 1."""
        return next((m for m in (snap or {}).get("members", []) if m["number"] == number), {"take": 1, "first": number})

    def leave(self):
        """Sai da festa (a do anfitriao fecha para todos) e volta ao normal."""
        for undo in self.undo:
            try:
                undo()
            except OSError:
                pass
        if self.party:
            self.party.close()
        if self.files:
            self.files.stop()
        if self.guest:
            self.guest.leave()
        self.reset()
        self.say()

    def lobby(self, now=None):
        """O que a sala mostra, ou None fora de uma festa."""
        if not self.role:
            return None
        now = self.clock() if now is None else now
        if self.role == "host":
            snap = self.party.snapshot()
            ready = self.party.ready()
            plan = self.party.plan
            closed = False
        else:
            snap = self.guest.party or {"members": []}
            ready = len(snap["members"]) >= self.profile["min"]
            plan = self.guest.plan
            closed = self.guest.closed and not plan
        me = self.mine(snap, self.number)
        return {"role": self.role, "profile": self.profile, "game": self.game, "members": snap["members"],
                "number": self.number, "min": self.profile["min"], "max": self.profile["max"],
                "fixed": self.profile["fixed"], "ready": ready, "plan": plan, "closed": closed,
                "slots": sum(m.get("take", 1) for m in snap["members"]),
                "capacity": self.profile.get("players") or self.profile["max"],
                "take": me["take"], "first": me["first"],
                "left": None if self.launch_at is None else max(0.0, self.launch_at - now)}

    def start_now(self):
        """O anfitriao comeca a festa (so se o minimo chegou)."""
        if self.role != "host" or not self.party:
            return False
        plan = self.party.start()
        if not plan:
            return False
        self.take_plan(plan, 1)
        return True

    def take_plan(self, plan, number):
        self.plan, self.number = plan, number
        self.launch_at = self.clock() + COUNTDOWN + plan["delays"].get(str(number), 0)
        self.say()

    def tick(self, now=None):
        """Chamado do laco do frontend. Devolve "launch" na hora de abrir o
        jogo, "closed" se a festa acabou (o anfitriao saiu) e None no resto."""
        if not self.role:
            return None
        now = self.clock() if now is None else now
        if self.role == "host":
            # Com todas as vagas cheias, ou de tamanho fixo com todos, a festa
            # comeca sozinha; a de tamanho flexivel o anfitriao comeca antes,
            # com o botao. A party do RetroArch comeca logo (late).
            if not self.plan and self.party.state == "lobby" and (
                    self.party.full() or self.profile.get("late") or (self.profile["fixed"] and self.party.ready())):
                self.start_now()
        else:
            if self.guest.plan and not self.plan:
                self.take_plan(self.guest.plan, self.guest.number)
            elif self.guest.closed and not self.plan:
                return "closed"
            elif self.guest.number != self.number and not self.plan:
                self.number = self.guest.number
                self.take = self.mine(self.guest.party, self.number)["take"]
                self.say()
        if self.plan and self.launch_at is not None and now >= self.launch_at:
            self.launch_at = None
            return "launch"
        return None

    # ── O jogo ──
    def command(self, base):
        """O comando do jogo em link (o base e o do frontend), com a NVRAM, o
        cfg e o ini deste numero no lugar; leave() desfaz tudo."""
        prof, plan, number = self.profile, self.plan, self.number
        if prof.get("ggpo") or prof.get("dolphin"):
            # O GGPO do Flycast e o net play do Dolphin: o comando do jogo com as opcoes
            # deles, sem NVRAM por numero.
            return command(prof, base, plan, number, self.game)
        if prof.get("netplay"):
            # O net play nao tem NVRAM por numero: o RetroArch com o que a festa pede.
            cfg = os.path.join(self.home, ".config", "fliperos", "netplay.cfg")
            os.makedirs(os.path.dirname(cfg), exist_ok=True)
            me = self.mine(plan, number)
            with open(cfg, "w") as f:
                f.write(netplay_cfg(prof, range(me["first"], me["first"] + me["take"])))
            return netplay_command(prof, plan, number, self.rom, self.name, cfg)
        argv = command(prof, base, plan, number, self.game)
        items = [(dest, origin) for origin, dest in nvram_files(prof, number, self.home)]
        if prof["emulator"] == "groovymame" and prof.get("cfg"):
            cfgdir = os.environ.get("FLIPEROS_MAME_CFG_DIR") or os.path.join(self.home, ".mame", "cfg")
            items.append((os.path.join(cfgdir, self.game + ".cfg"),
                          mame_cfg(prof["cfg"]["tag"], prof["cfg"]["value"], self.game)))
        self.undo.append(place_files(self.home, items))
        if prof["emulator"] == "sm2emu":
            cfg = os.environ.get("XDG_CONFIG_HOME") or os.path.join(self.home, ".config")
            ini = os.path.join(cfg, "sm2-emu", "sm2-emu.ini")
            ini_set(ini, sm2_keys(prof, plan, number, self.wire.ip))
            self.undo.append(lambda: ini_set(ini, {"link_enabled": "false"}))
        return argv

    def served(self, rom_files):
        """Os arquivos que o jogo pede, relativos ao home: os da pasta do
        jogo (e o pai, num clone) e os extras do perfil que existem."""
        out = []
        for path in rom_files:
            rel = os.path.relpath(path, self.home)
            if not rel.startswith("..") and os.path.isfile(path):
                out.append(rel)
        for rel in (self.profile or {}).get("extra", []):
            if os.path.isfile(os.path.join(self.home, rel)):
                out.append(rel)
        return out


class FakePresence:
    """A tabela de mentira dos testes de tela (fliperos-frontend --shot) e do
    emulador do frontend (tools/fe-emulator, que a reescreve com o que os
    gabinetes da rede dizem): com path, e lida de novo quando o arquivo muda."""

    def __init__(self, table, path=None):
        self.rows, self.path, self.mtime = table, path, None

    def table(self):
        if self.path:
            try:
                mtime = os.stat(self.path).st_mtime_ns
                if mtime != self.mtime:
                    with open(self.path) as f:
                        self.rows = json.load(f).get("table", [])
                    self.mtime = mtime
            except (OSError, ValueError):
                pass
        return self.rows

    def say(self, **info):
        pass

    def stop(self):
        pass


def fake_link(link, path):
    """Liga o link de um Frontend em --shot (ou do emulador do frontend) a uma
    rede de mentira: o JSON do caminho tem {"table": [os registros da
    presenca dos outros gabinetes]}, lido de novo quando muda. Sem caminho, o
    cabo esta solto."""
    if not path:
        link.wire = None
        return
    try:
        with open(path) as f:
            table = json.load(f).get("table", [])
    except (OSError, ValueError):
        table = []
    link.wire = Wire("fake", "10.9.9.9", "255.255.255.0", "10.9.9.255")
    link.presence = FakePresence(table, path)

