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
# - Perfis: um por familia de jogo, com o que os testes mostraram
#   (docs/research/linked-cabinets.md). Jogo fora dos perfis nao tem link.
# - NVRAM: um arquivo por numero de gabinete (config/link-nvram), posto onde
#   o emulador o le; o que havia vai para NOME.solo e volta no fim do jogo.
#
# Nada aqui depende do pygame: o frontend so chama e desenha.

import fcntl
import hashlib
import json
import os
import socket
import struct
import threading
import time
from collections import namedtuple
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILES = os.environ.get("FLIPEROS_LINK_PROFILES") or os.path.join(HERE, "link-profiles.json")
NVRAM_SRC = os.environ.get("FLIPEROS_LINK_NVRAM") or next(
    (p for p in ("/usr/local/share/fliperos/link-nvram", os.path.join(HERE, "..", "..", "config", "link-nvram"))
     if os.path.isdir(p)), "/usr/local/share/fliperos/link-nvram")
PORT_PRESENCE, PORT_PARTY, PORT_FILES = 55436, 55437, 55438
INTERVAL, EXPIRE = 1.0, 4.0
SOLO = ".solo"
# Os nomes de interface que nao sao a cabeada, mesmo com um dispositivo atras
# (as pontes e os tuneis do Docker, do libvirt e das VPNs).
VIRTUAL = ("lo", "docker", "veth", "br-", "virbr", "tun", "tap", "wg", "vmnet", "vboxnet", "zt")

Wire = namedtuple("Wire", "name ip mask broadcast")


# ── A interface cabeada ────────────────────────────────────────────

def iface_addr(name, request):
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
        # nao chega aqui.
        self.rx.bind((self.wire.broadcast, self.port))
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
    playing: fechada, ja comecou). Os que nao estao numa festa ficam de fora."""
    out = {}
    for rec in table:
        pid = rec.get("party")
        if not pid:
            continue
        p = out.setdefault(pid, {"party": pid, "game": rec.get("game"), "system": rec.get("system"),
                                 "link": rec.get("link"), "max": rec.get("max"), "state": rec.get("state"),
                                 "host_ip": None, "host": None, "numbers": []})
        if rec.get("slot") == 1:
            p["host_ip"], p["host"] = rec.get("ip"), rec.get("name")
            p["max"], p["state"] = rec.get("max"), rec.get("state")
        if rec.get("slot"):
            p["numbers"].append(rec["slot"])
    for p in out.values():
        p["numbers"].sort()
        p["used"] = len(p["numbers"])
    return sorted(out.values(), key=lambda p: (p["state"] != "playing", p["game"] or ""))


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
            "members": [{"number": m["number"], "name": m["name"], "ip": m["ip"]} for m in members],
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

    def __init__(self, wire, profile, game, ident, name, port=PORT_PARTY, on_change=None):
        self.wire, self.profile, self.game = wire, profile, game
        self.ident, self.name, self.port = ident, name, port
        self.on_change = on_change or (lambda: None)
        self.members = [{"id": ident, "name": name, "ip": wire.ip, "conn": None}]
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

    def snapshot(self):
        with self.lock:
            return {"party": self.ident, "profile": self.profile["id"], "game": self.game, "state": self.state,
                    "min": self.profile["min"], "max": self.profile["max"], "fixed": self.profile["fixed"],
                    "members": [{"number": i + 1, "name": m["name"], "ip": m["ip"]} for i, m in enumerate(self.members)]}

    def count(self):
        return len(self.members)

    def ready(self):
        """Pode comecar: o minimo chegou (os de tamanho fixo, so com todos)."""
        n = self.count()
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
                with self.lock:
                    if self.state != "lobby":
                        why = "closed"
                    elif len(self.members) >= self.profile["max"]:
                        why = "full"
                    elif msg.get("game") != self.game:
                        why = "game"
                    else:
                        member = {"id": msg.get("id"), "name": str(msg.get("name") or src)[:24], "ip": src, "conn": conn}
                        self.members.append(member)
                if why:
                    send_line(conn, {"op": "refused", "why": why})
                    break
                with self.lock:
                    number = self.members.index(member) + 1
                send_line(conn, {"op": "joined", "party": self.snapshot(), "number": number})
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
        with self.lock:
            if member in self.members and self.state == "lobby":
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
            members = [{"number": i + 1, "name": m["name"], "ip": m["ip"]} for i, m in enumerate(self.members)]
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

    def join(self, host_ip, game, timeout=3.0):
        """Entra. True se o anfitriao aceitou; senao self.refused diz porque
        (closed, full, game, ou down se nem atendeu)."""
        try:
            self.conn = socket.create_connection((host_ip, self.port), timeout=timeout)
        except OSError:
            self.refused = "down"
            return False
        self.conn.settimeout(None)
        send_line(self.conn, {"op": "join", "id": self.ident, "name": self.name, "game": game})
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
    return argv[:-1] + extra + argv[-1:]


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


def install_nvram(profile, number, home, src=None):
    """Poe a NVRAM do numero onde o emulador a le. O arquivo que la havia vai
    para NOME.solo (so o primeiro: um .solo que ja existe e o da pessoa) e
    volta no restore(). A lista do que foi mexido fica em ~/nvram/.link-active,
    para um frontend que reabre depois de uma queda desfazer (recover)."""
    import shutil
    files = nvram_files(profile, number, home, src)
    done = []
    for origin, dest in files:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.exists(dest) and not os.path.exists(dest + SOLO):
            os.replace(dest, dest + SOLO)
        shutil.copyfile(origin, dest)
        done.append(dest)
    marker = os.path.join(home, "nvram", ".link-active")
    if done:
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "w") as f:
            json.dump(done, f)
    return lambda: recover(home)


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


def fetch_files(host_ip, home, wanted, port=PORT_FILES, progress=None):
    """Copia do anfitriao os arquivos que faltam ou diferem (wanted: os
    caminhos relativos que o jogo pede). Cada um vem para NOME.part, e so vira
    o arquivo depois de conferido (o sha256 do manifesto); uma queda retoma
    do que ja veio. progress(feitos, total, caminho). Devolve (ok, faltou)."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://%s:%d/manifest" % (host_ip, port), timeout=5) as r:
            manifest = {m["path"]: m for m in json.load(r)}
    except (OSError, ValueError):
        return False, list(wanted)
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
