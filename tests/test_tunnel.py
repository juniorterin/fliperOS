"""The party tunnel of the Matchmaker (phase 2): STUN and TURN (fenat.py),
the order of the ways between two cabinets and the relay handshake
(fetunnel.py), and the root helper's checks (config/fliperos-online-tunnel).

No network and no WireGuard: the real thing runs in the NAT lab
(tools/matchmaker/natlab/natlab.sh). Plain Python 3, no pygame:

    MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W):/w" -w /w python:3.12-slim python3 tests/test_tunnel.py
"""
import binascii
import hashlib
import hmac
import importlib.machinery
import importlib.util
import os
import socket
import struct
import sys
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "fliperos-setup", "gui"))

import fenat  # noqa: E402
import fetunnel  # noqa: E402


def load_helper():
    path = os.path.join(REPO, "config", "fliperos-online-tunnel")
    loader = importlib.machinery.SourceFileLoader("fliperos_online_tunnel", path)
    spec = importlib.util.spec_from_loader("fliperos_online_tunnel", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


KEY_A = "GWwsUIofvw22emdqS4PgArITY8kYDolsuSKaKL7YjU0="
KEY_B = "UpvOj/bJOdYUk+lNABYGhzmDFRBhAP78OomviJHbPCg="


class StunMessageTests(unittest.TestCase):
    def test_a_message_parses_back(self):
        tid = os.urandom(12)
        raw = fenat.message(fenat.BINDING | fenat.SUCCESS, tid, [(fenat.A_SOFTWARE, b"abc")])
        kind, got_tid, attrs = fenat.parse(raw)
        self.assertEqual((kind, got_tid, attrs[fenat.A_SOFTWARE]), (fenat.BINDING | fenat.SUCCESS, tid, [b"abc"]))

    def test_xor_address_round_trip(self):
        for ip, port in (("203.0.113.5", 40000), ("10.0.0.1", 1)):
            self.assertEqual(fenat.read_addr(fenat.xor_addr(ip, port), b""), (ip, port))

    def test_not_stun_is_none(self):
        self.assertIsNone(fenat.parse(b"\x40\x00\x00\x04abcd"))         # ChannelData
        self.assertIsNone(fenat.parse(b"short"))

    def test_the_udp_turn_url(self):
        urls = ["turns:turn.cloudflare.com:443?transport=tcp", "turn:turn.cloudflare.com:3478?transport=tcp",
                "turn:turn.cloudflare.com:3478?transport=udp"]
        self.assertEqual(fenat.turn_url(urls), ("turn.cloudflare.com", 3478))
        self.assertIsNone(fenat.turn_url(["turns:x:443?transport=tcp"]))

    def test_the_integrity_and_fingerprint_follow_the_rfc(self):
        t = fenat.Turn.__new__(fenat.Turn)
        t.username, t.realm, t.nonce = b"user", b"realm", b"nonce"
        t.key = hashlib.md5(b"user:realm:pass").digest()
        tid = os.urandom(12)
        raw = t.signed(fenat.ALLOCATE | fenat.REQUEST, tid, [(fenat.A_TRANSPORT, b"\x11\0\0\0")])
        kind, _, attrs = fenat.parse(raw)
        mi_at = raw.index(struct.pack("!HH", fenat.A_INTEGRITY, 20))
        head = raw[:2] + struct.pack("!H", mi_at - 20 + 24) + raw[4:mi_at]
        self.assertEqual(attrs[fenat.A_INTEGRITY][0], hmac.new(t.key, head, hashlib.sha1).digest())
        fp_at = len(raw) - 8
        crc = (binascii.crc32(raw[:2] + struct.pack("!H", len(raw) - 20) + raw[4:fp_at]) ^ 0x5354554E) & 0xFFFFFFFF
        self.assertEqual(attrs[fenat.A_FINGERPRINT][0], struct.pack("!I", crc))

    def test_stun_against_a_local_responder(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        srv.bind(("127.0.0.1", 0))

        def answer():
            data, src = srv.recvfrom(2048)
            _, tid, _ = fenat.parse(data)
            srv.sendto(fenat.message(fenat.BINDING | fenat.SUCCESS, tid, [(fenat.A_XOR_MAPPED, fenat.xor_addr(*src))]),
                       src)
        threading.Thread(target=answer, daemon=True).start()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("127.0.0.1", 0))
        self.assertEqual(fenat.stun_mapped(s, srv.getsockname()), s.getsockname())
        s.close()
        srv.close()


class FakeTurnSocket:
    def __init__(self):
        self.sent = []

    def send(self, data):
        self.sent.append(data)


class RelayTests(unittest.TestCase):
    def relay(self, rate=fenat.RATE):
        class T:
            relayed = ("104.30.146.175", 35613)
            lifetime = 600
            reader = None
            pending = {}

            def __init__(self):
                self.sock = FakeTurnSocket()
                self.calls = []

            def permit(self, ip):
                self.calls.append(("permit", ip))

            def bind(self, channel, peer):
                self.calls.append(("bind", channel, peer))
        wg = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        wg.bind(("127.0.0.1", 0))
        wg.settimeout(1)
        self.addCleanup(wg.close)
        r = fenat.Relay({"urls": ["turn:x:3478"], "username": "u", "credential": "c"}, wg.getsockname()[1],
                        turn=T(), rate=rate)
        return r, wg

    def test_a_peer_gets_a_permission_a_channel_and_a_local_port(self):
        r, _ = self.relay()
        port = r.add_peer(("104.30.147.180", 61756))
        self.assertEqual(r.turn.calls, [("permit", "104.30.147.180"), ("bind", 0x4000, ("104.30.147.180", 61756))])
        self.assertGreater(port, 0)

    def test_channel_data_goes_to_wireguard(self):
        r, wg = self.relay()
        r.add_peer(("104.30.147.180", 61756))
        r.from_turn(struct.pack("!HH", 0x4000, 5) + b"hello")
        self.assertEqual(wg.recvfrom(100)[0], b"hello")

    def test_a_data_indication_goes_to_wireguard_too(self):
        r, wg = self.relay()
        r.add_peer(("104.30.147.180", 61756))
        tid = os.urandom(12)
        r.from_turn(fenat.message(fenat.DATA | fenat.INDICATION, tid,
                                  [(fenat.A_PEER, fenat.xor_addr("104.30.147.180", 61756)), (fenat.A_DATA, b"early")]))
        self.assertEqual(wg.recvfrom(100)[0], b"early")

    def test_the_rate_limit(self):
        r, _ = self.relay(rate=100)
        r.add_peer(("104.30.147.180", 61756))
        peer = r.peers[0x4000]
        self.assertTrue(r.allow(peer, 80))
        self.assertFalse(r.allow(peer, 80))


class CandidateTests(unittest.TestCase):
    def test_same_house_tries_the_lan_first(self):
        mine = {"lan": ["192.168.1.10", 1000], "stun": ["177.1.1.1", 2000]}
        theirs = {"lan": ["192.168.1.20", 3000], "stun": ["177.1.1.1", 4000]}
        self.assertEqual([k for k, _ in fetunnel.candidates(mine, theirs)], ["lan", "stun"])

    def test_another_house_never_tries_its_lan(self):
        mine = {"lan": ["192.168.1.10", 1000], "stun": ["177.1.1.1", 2000]}
        theirs = {"lan": ["192.168.1.20", 3000], "stun": ["189.9.9.9", 4000]}
        self.assertEqual([k for k, _ in fetunnel.candidates(mine, theirs)], ["stun"])

    def test_ipv6_only_when_both_have_it(self):
        mine = {"v6": ["2804::1", 1000], "stun": ["177.1.1.1", 2000]}
        theirs = {"v6": ["2001:db8::2", 3000], "stun": ["189.9.9.9", 4000]}
        self.assertEqual([k for k, _ in fetunnel.candidates(mine, theirs)], ["v6", "stun"])
        self.assertEqual([k for k, _ in fetunnel.candidates({"stun": ["1.1.1.1", 1]}, theirs)], ["stun"])

    def test_bad_addresses_are_dropped(self):
        self.assertEqual(fetunnel.clean_cands({"lan": ["127.0.0.1", 5], "stun": ["x", 1], "v6": ["2001:db8::1", 0]}), {})
        self.assertEqual(fetunnel.clean_cands({"stun": ["203.0.113.5", 40000]}), {"stun": ["203.0.113.5", 40000]})
        self.assertEqual(fetunnel.endpoint_of("2001:db8::1", 5), "[2001:db8::1]:5")


class World:
    """Two cabinets' WireGuards: a path works if the scenario says so (direct)
    or if both point at their relay port and only one of them started."""

    def __init__(self, direct_ok):
        self.direct_ok = direct_ok
        self.helpers = {}
        self.wall = 1000.0
        self.linked = set()

    def link_up(self, a, b):
        pa, pb = self.helpers[a].peers.get(self.helpers[b].key), self.helpers[b].peers.get(self.helpers[a].key)
        if not pa or not pb or not pa["endpoint"] or not pb["endpoint"]:
            return False
        if pa["endpoint"].startswith("127.0.0.1:") and pb["endpoint"].startswith("127.0.0.1:"):
            if pa["quiet"] != pb["quiet"]:              # one starts, one answers: linked
                self.linked.add("relay")
            return "relay" in self.linked
        return self.direct_ok(pa["endpoint"]) and self.direct_ok(pb["endpoint"])


class FakeHelper:
    def __init__(self, world, name, key):
        self.world, self.name, self.key = world, name, key
        self.peers = {}
        world.helpers[name] = self
        self.calls = []

    def up(self, addr, port):
        self.calls.append(("up", addr))
        return self.key

    def peer(self, key, addr, endpoint=None, quiet=False):
        self.calls.append(("peer", endpoint, quiet))
        self.peers[key] = {"addr": addr, "endpoint": endpoint, "quiet": quiet}

    def keep(self, key):
        self.calls.append(("keep",))
        self.peers[key]["quiet"] = False

    def remove(self, key):
        self.peers.pop(key, None)

    def show(self):
        other = next(n for n in self.world.helpers if n != self.name)
        out = []
        for key, p in self.peers.items():
            up = self.world.link_up(self.name, other)
            out.append({"key": key, "endpoint": p["endpoint"], "handshake": int(self.world.wall) if up else 0,
                        "rx": 0, "tx": 0})
        return out

    def down(self):
        self.calls.append(("down",))


class FakeRelay:
    count = 0

    def __init__(self, ice, port):
        FakeRelay.count += 1
        self.relayed = ("104.30.146.%d" % FakeRelay.count, 40000)
        self.carried = 0
        self.ports = {}

    def open(self):
        return self.relayed

    def start(self):
        pass

    def stop(self):
        pass

    def add_peer(self, addr):
        self.ports[tuple(addr)] = 50000 + len(self.ports)
        return self.ports[tuple(addr)]


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class TunnelStateTests(unittest.TestCase):
    """Two Tunnels whose signals pass through a fake server, stepped by hand."""

    def make(self, direct_ok):
        self.world = World(direct_ok)
        self.clock = Clock()
        self.outbox = []
        cabs = {}
        for name, addr, key, pub, lan in (("a", "10.207.0.1", KEY_A, "177.1.1.1", "192.168.1.10"),
                                          ("b", "10.207.0.2", KEY_B, "189.9.9.9", "192.168.2.10")):
            helper = FakeHelper(self.world, name, key)
            t = fetunnel.Tunnel(addr, lambda m, name=name: self.outbox.append((name, m)), helper=helper,
                                clock=self.clock, wall=lambda: self.world.wall, port=40000,
                                stun=lambda port, pub=pub: (pub, port), lan=lambda lan=lan: {"lan": lan},
                                relay_factory=FakeRelay)
            t.open()
            cabs[name] = t
        self.a, self.b = cabs["a"], cabs["b"]
        self.ids = {"a": 1, "b": 2}
        self.a.know({"id": 2, "nick": "B", "tag": "bbbb", "addr": "10.207.0.2"})
        self.b.know({"id": 1, "nick": "A", "tag": "aaaa", "addr": "10.207.0.1"})

    def deliver(self, turn_error=None):
        """What the server would do with the messages sent so far."""
        while self.outbox:
            who, m = self.outbox.pop(0)
            other = self.b if who == "a" else self.a
            me = self.a if who == "a" else self.b
            if m["t"] == "signal":
                other.on_message({"t": "signal", "from": self.ids[who], "data": m["data"]})
            elif m["t"] == "turn" and m.get("op") != "used":
                if turn_error:
                    me.on_message({"t": "turn", "error": turn_error})
                else:
                    me.on_message({"t": "turn", "ice": {"urls": ["turn:x:3478"], "username": who, "credential": "c"}})

    def run_for(self, seconds, step=0.5, turn_error=None):
        end = self.clock.t + seconds
        while self.clock.t < end:
            self.deliver(turn_error)
            for t in (self.a, self.b):
                t.check()
            self.clock.t += step
            self.world.wall += step

    def path(self, t):
        return t.snapshot()["peers"][0]["path"]

    def test_direct_when_the_routers_open(self):
        self.make(lambda ep: not ep.startswith("127."))
        self.run_for(2)
        self.assertEqual((self.path(self.a), self.path(self.b)), ("direct", "direct"))
        self.assertTrue(self.a.direct("10.207.0.2"))
        self.assertTrue(self.a.ready() and self.b.ready())

    def test_relay_when_no_direct_way_and_only_one_starts(self):
        self.make(lambda ep: False)
        self.run_for(fetunnel.TRY_DIRECT + 3)
        self.assertEqual((self.path(self.a), self.path(self.b)), ("relay", "relay"))
        self.assertFalse(self.a.direct("10.207.0.2"))                    # no ROM through the relay
        a_relay = [c for c in self.a.helper.calls if c[0] == "peer" and c[1] and c[1].startswith("127.")]
        b_relay = [c for c in self.b.helper.calls if c[0] == "peer" and c[1] and c[1].startswith("127.")]
        self.assertEqual((a_relay[-1][2], b_relay[-1][2]), (False, True))   # .1 starts, .2 answers
        self.assertIn(("keep",), self.b.helper.calls)                    # then the quiet one keeps it alive

    def test_no_relay_credentials_is_a_failed_path(self):
        self.make(lambda ep: False)
        self.run_for(fetunnel.TRY_DIRECT + 3, turn_error="cap")
        self.assertEqual(self.path(self.a), "failed")
        self.assertEqual(self.a.snapshot()["relay_error"], "cap")

    def test_a_lost_signal_is_asked_again(self):
        self.make(lambda ep: not ep.startswith("127."))
        self.outbox = [m for m in self.outbox if m[0] != "a"]              # a's first signal is lost
        self.run_for(fetunnel.RESEND + 2)
        self.assertEqual((self.path(self.a), self.path(self.b)), ("direct", "direct"))

    def test_the_same_house_uses_the_lan(self):
        self.make(lambda ep: ep.startswith("192.168."))
        self.a.mine["stun"][0] = self.b.mine["stun"][0] = "177.1.1.1"
        # the signals already sent carried the old public address: send again
        for t in (self.a, self.b):
            for p in t.peers.values():
                p["sent"] = False
        self.outbox.clear()
        self.a.say_to(2)
        self.b.say_to(1)
        self.run_for(2)
        self.assertTrue(self.a.snapshot()["peers"][0]["endpoint"].startswith("192.168.2.10"))


class HelperChecksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = load_helper()

    def bad(self, fn, *args):
        with self.assertRaises(SystemExit):
            fn(*args)

    def test_keys(self):
        self.assertEqual(self.h.key(KEY_A), KEY_A)
        self.bad(self.h.key, "not a key")
        self.bad(self.h.key, KEY_A[:-2] + "B=")           # the last character of a 32-byte key

    def test_only_tunnel_addresses(self):
        self.assertEqual(self.h.tunnel_addr("10.207.3.2/24", prefix=True), "10.207.3.2/24")
        self.assertEqual(self.h.tunnel_addr("10.207.3.1"), "10.207.3.1/32")
        self.bad(self.h.tunnel_addr, "192.168.1.10")
        self.bad(self.h.tunnel_addr, "10.207.3.2/16", True)
        self.bad(self.h.tunnel_addr, "10.207.3.2; rm -rf /")

    def test_endpoints(self):
        self.assertEqual(self.h.endpoint("203.0.113.5:40000"), "203.0.113.5:40000")
        self.assertEqual(self.h.endpoint("[2001:db8::1]:40000"), "[2001:db8::1]:40000")
        self.assertEqual(self.h.endpoint("127.0.0.1:50000"), "127.0.0.1:50000")      # the relay
        for bad in ("203.0.113.5", "224.0.0.1:5000", "0.0.0.0:5000", "x:1", "203.0.113.5:80"):
            self.bad(self.h.endpoint, bad)

    def test_commands_run_without_a_shell(self):
        calls = []
        h = self.h
        saved = h.run, h.exists
        h.run = lambda *argv, data=None: calls.append(argv) or ""
        try:
            h.main(["peer", KEY_A, "10.207.0.1", "203.0.113.5:40000", "quiet"])
            self.assertEqual(calls[-1], (h.WG, "set", h.IFACE, "peer", KEY_A, "allowed-ips", "10.207.0.1/32",
                                         "persistent-keepalive", "0", "endpoint", "203.0.113.5:40000"))
            h.main(["peer", KEY_A, "10.207.0.1"])
            self.assertEqual(calls[-1][-2:], ("persistent-keepalive", h.KEEPALIVE))
            self.bad(h.main, ["peer", KEY_A, "10.207.0.1", "$(reboot)"])
            self.bad(h.main, ["format", "/dev/sda"])
        finally:
            h.run, h.exists = saved


if __name__ == "__main__":
    unittest.main()
