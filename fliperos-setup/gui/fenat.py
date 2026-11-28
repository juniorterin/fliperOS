"""The way through the internet for the Matchmaker's tunnel: STUN and TURN.

STUN (RFC 5389) tells a cabinet the public address its router gives one UDP
port: the WireGuard of the match then listens on that same port, and the two
cabinets open their routers by sending to each other at the same time.

TURN (RFC 8656, Cloudflare Realtime) is the relay for when that is
impossible (both behind CGNAT or a symmetric NAT). Relay keeps one
allocation on the TURN server and, per peer, a local UDP port: the
WireGuard peer's endpoint is 127.0.0.1:that port, and what WireGuard sends
there goes to the peer through the relay (a ChannelData message), and back.
The relay only sees WireGuard's ciphertext; the cabinets never send a ROM
through it (felink's file server only serves on a direct path).

Standard library only, like fews.py.
"""
import binascii
import hashlib
import hmac
import os
import select
import socket
import struct
import threading
import time

MAGIC = 0x2112A442
STUN_SERVER = ("stun.cloudflare.com", 3478)

# Methods (class bits added below) and attributes.
BINDING, ALLOCATE, REFRESH, SEND, DATA, CREATE_PERMISSION, CHANNEL_BIND = 0x001, 0x003, 0x004, 0x006, 0x007, 0x008, 0x009
REQUEST, INDICATION, SUCCESS, ERROR = 0x0000, 0x0010, 0x0100, 0x0110
A_MAPPED, A_USERNAME, A_INTEGRITY, A_ERROR, A_CHANNEL, A_LIFETIME = 0x0001, 0x0006, 0x0008, 0x0009, 0x000C, 0x000D
A_PEER, A_DATA, A_REALM, A_NONCE, A_RELAYED, A_TRANSPORT = 0x0012, 0x0013, 0x0014, 0x0015, 0x0016, 0x0019
A_XOR_MAPPED, A_SOFTWARE, A_FINGERPRINT = 0x0020, 0x8022, 0x8028
SOFTWARE = b"FliperOS Matchmaker"
LIFETIME = 600              # seconds asked for an allocation (refreshed at half)
PERMISSION_EVERY = 240      # permissions last 300 s, channels 600 s: renewed before
FIRST_CHANNEL = 0x4000
RATE = 256 * 1024           # bytes a second one peer may push through the relay
NAT_KEEPALIVE = 15          # seconds: something to the TURN server, so the home router keeps the way open


class StunError(Exception):
    pass


def message(method_class, tid, attrs=()):
    body = b"".join(attr(t, v) for t, v in attrs)
    return struct.pack("!HHI12s", method_class, len(body), MAGIC, tid) + body


def attr(kind, value):
    pad = (4 - len(value) % 4) % 4
    return struct.pack("!HH", kind, len(value)) + value + b"\0" * pad


def parse(data):
    """(type, tid, {attribute: [values]}) of a STUN message, or None."""
    if len(data) < 20:
        return None
    kind, length, magic, tid = struct.unpack("!HHI12s", data[:20])
    if magic != MAGIC or kind & 0xC000 or 20 + length > len(data):
        return None
    attrs, pos = {}, 20
    while pos + 4 <= 20 + length:
        t, n = struct.unpack("!HH", data[pos:pos + 4])
        attrs.setdefault(t, []).append(data[pos + 4:pos + 4 + n])
        pos += 4 + n + (4 - n % 4) % 4
    return kind, tid, attrs


def xor_addr(ip, port, tid=b""):
    """XOR-*-ADDRESS of an IPv4 address (an IPv6 one also needs its message's tid)."""
    packed = socket.inet_pton(socket.AF_INET6 if ":" in ip else socket.AF_INET, ip)
    key = struct.pack("!I", MAGIC) + tid
    xored = bytes(a ^ b for a, b in zip(packed, key))
    family = 2 if len(packed) == 16 else 1
    return struct.pack("!BBH", 0, family, port ^ (MAGIC >> 16)) + xored


def read_addr(value, tid=None):
    """(ip, port) of a MAPPED-ADDRESS (tid None) or an XOR-*-ADDRESS."""
    if len(value) < 8:
        return None
    family, port = value[1], struct.unpack("!H", value[2:4])[0]
    raw = value[4:20] if family == 2 else value[4:8]
    if tid is not None:
        port ^= MAGIC >> 16
        key = struct.pack("!I", MAGIC) + tid
        raw = bytes(a ^ b for a, b in zip(raw, key))
    return socket.inet_ntop(socket.AF_INET6 if family == 2 else socket.AF_INET, raw), port


def mapped(attrs, tid):
    if A_XOR_MAPPED in attrs:
        return read_addr(attrs[A_XOR_MAPPED][0], tid)
    if A_MAPPED in attrs:
        return read_addr(attrs[A_MAPPED][0])
    return None


def resolve(host, port, family=socket.AF_INET):
    return socket.getaddrinfo(host, port, family, socket.SOCK_DGRAM)[0][4][:2]


def stun_mapped(sock, server=STUN_SERVER, timeout=1.0, tries=3):
    """The public (ip, port) of a UDP socket, by STUN Binding; StunError if no answer."""
    dest = resolve(*server, family=sock.family)
    tid = os.urandom(12)
    req = message(BINDING | REQUEST, tid)
    for _ in range(tries):
        sock.sendto(req, dest)
        end = time.monotonic() + timeout
        while True:
            left = end - time.monotonic()
            if left <= 0 or not select.select([sock], [], [], left)[0]:
                break
            data, _ = sock.recvfrom(2048)
            msg = parse(data)
            if msg and msg[0] == BINDING | SUCCESS and msg[1] == tid:
                addr = mapped(msg[2], tid)
                if addr:
                    return addr
    raise StunError("no STUN answer from %s:%d" % server)


def public_port(port, server=STUN_SERVER, timeout=1.0):
    """Ask STUN from local UDP `port` and let it go: the router keeps the
    mapping for a while, and the WireGuard of the match listens on the same
    port and inherits it. (ip, port) or None."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", port))
        return stun_mapped(s, server, timeout)
    except (OSError, StunError):
        return None
    finally:
        s.close()


def free_udp_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def lan_addrs():
    """This cabinet's IPv4 on the LAN (the one with the default route) and its
    global IPv6, for two cabinets in the same house or with IPv6 on both ends."""
    out = {}
    for family, probe, key in ((socket.AF_INET, ("192.0.2.1", 9), "lan"),
                               (socket.AF_INET6, ("2001:db8::1", 9), "v6")):
        s = socket.socket(family, socket.SOCK_DGRAM)
        try:
            s.connect(probe)
            ip = s.getsockname()[0]
            if family == socket.AF_INET6 and (ip.startswith(("fe80", "fd", "fc")) or ip == "::1"):
                continue
            out[key] = ip
        except OSError:
            pass
        finally:
            s.close()
    return out


def turn_url(urls):
    """(host, port) of the first plain UDP TURN url (turn:HOST:PORT?transport=udp)."""
    for url in urls:
        if not url.startswith("turn:"):
            continue
        rest, _, query = url[5:].partition("?")
        if query and "transport=udp" not in query:
            continue
        host, _, port = rest.rpartition(":")
        return (host or rest), int(port or 3478)
    return None


class TurnError(Exception):
    pass


class Turn:
    """One TURN allocation over UDP, with the long-term credential (RFC 8656 9.2)."""

    def __init__(self, server, username, password, timeout=2.0):
        self.server = resolve(*server)
        self.username, self.password = username.encode(), password.encode()
        self.timeout = timeout
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.connect(self.server)
        self.realm = self.nonce = self.key = None
        self.relayed = self.mapped = None
        self.lifetime = 0
        self.lock = threading.Lock()
        self.pending = {}           # tid -> the answer, when the reader thread runs

    # -- Messages --
    def signed(self, method_class, tid, attrs):
        """A request with USERNAME, REALM, NONCE, MESSAGE-INTEGRITY and FINGERPRINT."""
        attrs = list(attrs) + [(A_USERNAME, self.username), (A_REALM, self.realm), (A_NONCE, self.nonce),
                               (A_SOFTWARE, SOFTWARE)]
        raw = message(method_class, tid, attrs)
        # The integrity covers the header with the length as if it ended at it.
        head = struct.pack("!HH", method_class, len(raw) - 20 + 24) + raw[4:]
        mac = hmac.new(self.key, head, hashlib.sha1).digest()
        raw = message(method_class, tid, attrs + [(A_INTEGRITY, mac)])
        head = struct.pack("!HH", method_class, len(raw) - 20 + 8) + raw[4:]
        crc = (binascii.crc32(head) ^ 0x5354554E) & 0xFFFFFFFF
        return message(method_class, tid, attrs + [(A_INTEGRITY, mac), (A_FINGERPRINT, struct.pack("!I", crc))])

    def exchange(self, raw, tid):
        """Send a request and wait for its answer: (type, attrs)."""
        if self.reader is not None:                  # the relay thread will hand the answer over
            self.pending[tid] = [threading.Event(), None]
        for _ in range(3):
            self.sock.send(raw)
            end = time.monotonic() + self.timeout
            while True:
                left = end - time.monotonic()
                if left <= 0:
                    break
                got = self.wait_answer(tid, left)
                if got:
                    return got
        raise TurnError("no answer from the TURN server")

    def wait_answer(self, tid, left):
        if self.reader is not None:                  # the relay thread reads the socket
            event = self.pending[tid]
            if event[0].wait(left):
                self.pending.pop(tid, None)
                return event[1]
            return None
        if not select.select([self.sock], [], [], left)[0]:
            return None
        data = self.sock.recv(4096)
        msg = parse(data)
        if msg and msg[1] == tid:
            return msg[0], msg[2]
        return None

    reader = None

    def request(self, method, attrs=()):
        """A signed request; a stale nonce is renewed once. (success attributes, tid), or TurnError."""
        for _ in range(2):
            tid = os.urandom(12)
            kind, got = self.exchange(self.signed(method | REQUEST, tid, attrs), tid)
            if kind == method | SUCCESS:
                return got, tid
            code = error_code(got)
            if code == 438 and A_NONCE in got:
                self.nonce = got[A_NONCE][0]
                continue
            raise TurnError("TURN error %s" % code)
        raise TurnError("TURN stale nonce")

    # -- The allocation --
    def allocate(self):
        """The relayed (ip, port) of a new allocation."""
        transport = [(A_TRANSPORT, struct.pack("!BBBB", 17, 0, 0, 0)), (A_LIFETIME, struct.pack("!I", LIFETIME))]
        tid = os.urandom(12)
        kind, got = self.exchange(message(ALLOCATE | REQUEST, tid, transport), tid)
        if kind != ALLOCATE | ERROR or error_code(got) != 401:
            raise TurnError("unexpected TURN answer")
        self.realm, self.nonce = got[A_REALM][0], got[A_NONCE][0]
        self.key = hashlib.md5(self.username + b":" + self.realm + b":" + self.password).digest()
        got, tid = self.request(ALLOCATE, transport)
        if A_RELAYED not in got:
            raise TurnError("no relayed address")
        self.relayed = read_addr(got[A_RELAYED][0], tid)
        self.mapped = mapped(got, tid)
        self.lifetime = struct.unpack("!I", got[A_LIFETIME][0])[0] if A_LIFETIME in got else LIFETIME
        return self.relayed

    def refresh(self, lifetime=LIFETIME):
        self.request(REFRESH, [(A_LIFETIME, struct.pack("!I", lifetime))])

    def permit(self, ip):
        self.request(CREATE_PERMISSION, [(A_PEER, xor_addr(ip, 0))])

    def bind(self, channel, peer):
        self.request(CHANNEL_BIND, [(A_CHANNEL, struct.pack("!HH", channel, 0)), (A_PEER, xor_addr(*peer))])

    def close(self):
        try:
            if self.key:
                self.sock.send(self.signed(REFRESH | REQUEST, os.urandom(12), [(A_LIFETIME, struct.pack("!I", 0))]))
        except OSError:
            pass
        self.sock.close()


def error_code(attrs):
    value = (attrs.get(A_ERROR) or [b""])[0]
    if len(value) < 4:
        return None
    return value[2] * 100 + value[3]


class Relay:
    """The relay of a match: one TURN allocation and, per peer, a local UDP
    port that the WireGuard peer uses as its endpoint (127.0.0.1:port).
    wg_port: the WireGuard listen port, where what comes from the relay goes."""

    def __init__(self, ice, wg_port, turn=None, clock=time.monotonic, rate=RATE):
        server = turn_url(ice["urls"])
        if turn is None and server is None:
            raise TurnError("no UDP TURN url")
        self.turn = turn or Turn(server, ice["username"], ice["credential"])
        self.username = ice["username"]
        self.wg = ("127.0.0.1", wg_port)
        self.clock = clock
        self.rate = rate
        self.peers = {}             # channel -> {"addr", "sock", "port", "budget", "at"}
        self.by_sock = {}
        self.carried = 0
        self.counts = {"from_wg": 0, "to_turn": 0, "channel_in": 0, "data_in": 0, "dropped": 0}
        self.running = False
        self.thread = None
        self.refreshed = self.permitted = self.poked = clock()
        self.wake_r, self.wake_w = socket.socketpair()

    @property
    def relayed(self):
        return self.turn.relayed

    def open(self):
        """The allocation: our relayed (ip, port), what the peers send to."""
        return self.turn.allocate()

    def add_peer(self, addr):
        """A peer's relayed (ip, port): the local port its WireGuard endpoint points to."""
        channel = FIRST_CHANNEL + len(self.peers)
        self.turn.permit(addr[0])
        self.turn.bind(channel, tuple(addr))
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("127.0.0.1", 0))
        peer = {"addr": tuple(addr), "sock": s, "port": s.getsockname()[1], "budget": float(self.rate),
                "at": self.clock(), "channel": channel}
        self.peers[channel] = peer
        self.by_sock[s] = peer
        try:
            self.wake_w.send(b"x")              # the relay thread listens to the new port now
        except OSError:
            pass
        return peer["port"]

    def start(self):
        self.running = True
        self.turn.reader = self
        self.thread = threading.Thread(target=self.run, name="fliperos-relay", daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(2)
        for p in self.peers.values():
            p["sock"].close()
        self.wake_r.close()
        self.wake_w.close()
        self.turn.close()

    def allow(self, peer, n):
        """A token bucket per peer: the inputs of a game fit many times over."""
        now = self.clock()
        peer["budget"] = min(float(self.rate), peer["budget"] + (now - peer["at"]) * self.rate)
        peer["at"] = now
        if peer["budget"] < n:
            return False
        peer["budget"] -= n
        return True

    def keep(self):
        """Refresh the allocation, the permissions and the channels before they lapse."""
        now = self.clock()
        try:
            if now - self.refreshed > self.turn.lifetime / 2:
                self.refreshed = now
                threading.Thread(target=self.turn.refresh, daemon=True).start()
            if now - self.poked > NAT_KEEPALIVE:
                self.poked = now
                self.turn.sock.send(message(BINDING | REQUEST, os.urandom(12)))
            if now - self.permitted > PERMISSION_EVERY:
                self.permitted = now
                for p in list(self.peers.values()):
                    threading.Thread(target=self._rebind, args=(p,), daemon=True).start()
        except OSError:
            pass

    def _rebind(self, p):
        try:
            self.turn.permit(p["addr"][0])
            self.turn.bind(p["channel"], p["addr"])
        except (OSError, TurnError):
            pass

    def run(self):
        socks = [self.turn.sock]
        while self.running:
            socks = [self.turn.sock, self.wake_r] + [p["sock"] for p in list(self.peers.values())]
            try:
                ready = select.select(socks, [], [], 0.5)[0]
            except (OSError, ValueError):
                break
            for s in ready:
                if s is self.wake_r:
                    try:
                        s.recv(64)
                    except OSError:
                        pass
                    continue
                try:
                    data = s.recv(65536) if s is self.turn.sock else s.recvfrom(65536)[0]
                except OSError:
                    continue
                if s is self.turn.sock:
                    self.from_turn(data)
                else:
                    peer = self.by_sock[s]
                    self.counts["from_wg"] += 1
                    if self.allow(peer, len(data)):
                        self.counts["to_turn"] += 1
                        self.carried += len(data)
                        try:
                            self.turn.sock.send(struct.pack("!HH", peer["channel"], len(data)) + data)
                        except OSError:
                            pass
            self.keep()

    def from_turn(self, data):
        if len(data) >= 4 and 0x40 <= data[0] <= 0x7F:          # ChannelData
            channel, n = struct.unpack("!HH", data[:4])
            peer = self.peers.get(channel)
            self.counts["channel_in"] += 1
            if peer is not None:
                self.carried += n
                try:
                    peer["sock"].sendto(data[4:4 + n], self.wg)
                except OSError:
                    pass
            return
        msg = parse(data)
        if msg is None:
            return
        kind, tid, attrs = msg
        if kind == DATA | INDICATION and A_DATA in attrs and A_PEER in attrs:
            # Before its channel is bound, the TURN server hands a peer's packet
            # over as a Data indication: it goes to WireGuard all the same.
            src = read_addr(attrs[A_PEER][0], tid)
            peer = next((p for p in self.peers.values() if p["addr"] == src), None)
            self.counts["data_in"] += 1
            if peer is not None:
                payload = attrs[A_DATA][0]
                self.carried += len(payload)
                try:
                    peer["sock"].sendto(payload, self.wg)
                except OSError:
                    pass
            return
        waiting = self.turn.pending.get(tid)
        if waiting is not None:
            waiting[1] = (kind, attrs)
            waiting[0].set()
