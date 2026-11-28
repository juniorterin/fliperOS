"""The Matchmaker's online party (phase 2): felink's party inside the tunnel
(mmparty.py), the input delay from the tunnel's ping and the file server
that never sends a ROM through the relay.

The real thing (two cabinets behind NATs) is the NAT lab's party-eim and
party-symmetric (tools/matchmaker/natlab/natlab.sh). Plain Python 3:

    MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W):/w" -w /w fliperos-tests python3 tests/test_mmparty.py
"""
import os
import socket
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "fliperos-setup", "gui"))

import felink  # noqa: E402
import mmparty  # noqa: E402

LOCKSTEP = {"id": "netplay", "emulator": "groovymame", "min": 2, "max": 2, "players": 2, "fixed": True,
            "order": "master-first", "step": 0, "port": 55440, "netplay": True, "lockstep": True}
ROLLBACK = {"id": "netplay", "emulator": "retroarch", "min": 2, "max": 4, "players": 4, "fixed": False,
            "order": "master-first", "step": 0, "port": 55435, "netplay": True, "late": True, "core": "x"}


class DelayTests(unittest.TestCase):
    def test_lockstep_covers_half_the_ping_and_a_margin(self):
        self.assertEqual(felink.online_delay(1, LOCKSTEP), 1)
        self.assertEqual(felink.online_delay(22, LOCKSTEP), 2)
        self.assertEqual(felink.online_delay(150, LOCKSTEP), 6)

    def test_rollback_keeps_it_small(self):
        self.assertEqual(felink.online_delay(22, ROLLBACK), 1)
        self.assertEqual(felink.online_delay(60, ROLLBACK), 2)
        self.assertEqual(felink.online_delay(400, ROLLBACK), 3)

    def test_the_plan_carries_the_delay_only_online(self):
        members = [{"number": 1, "name": "A", "ip": "10.207.0.1"}, {"number": 2, "name": "B", "ip": "10.207.0.2"}]
        self.assertNotIn("input_delay", felink.make_plan(LOCKSTEP, members))
        self.assertEqual(felink.make_plan(dict(LOCKSTEP, input_delay=3), members)["input_delay"], 3)

    def test_retroarch_gets_its_input_latency(self):
        self.assertIn('netplay_input_latency_frames_min = "0"', felink.netplay_cfg(ROLLBACK, [1]))
        cfg = felink.netplay_cfg(ROLLBACK, [1], 2)
        self.assertIn('netplay_input_latency_frames_min = "2"', cfg)
        self.assertIn('netplay_nat_traversal = "false"', cfg)        # the tunnel, never RetroArch's own

    def test_ggpo_online_is_rollback_with_the_delay(self):
        prof = {"emulator": "flycast", "ggpo": True, "port": 19713, "party": True, "order": "master-first"}
        plan = {"n": 2, "members": [{"number": 1, "ip": "10.207.0.1"}, {"number": 2, "ip": "10.207.0.2"}],
                "input_delay": 2}
        saved = felink.flycast_lockstep
        felink.flycast_lockstep = lambda path=None: True
        try:
            opts = felink.link_args(prof, plan, 2)[1]
        finally:
            felink.flycast_lockstep = saved
        self.assertIn("network:GGPODelay=2", opts)
        self.assertNotIn("GGPOMaxPrediction", opts)

    def test_dolphin_buffer_follows_the_delay(self):
        prof = {"emulator": "dolphin", "dolphin": True, "port": 2626, "order": "master-first"}
        plan = {"n": 2, "members": [{"number": 1, "ip": "10.207.0.1"}, {"number": 2, "ip": "10.207.0.2"}]}
        self.assertIn("Dolphin.NetPlay.BufferSize=2", felink.link_args(prof, plan, 2))
        self.assertIn("Dolphin.NetPlay.BufferSize=5", felink.link_args(prof, dict(plan, input_delay=5), 2))

    def test_the_mame_lockstep_ini_gets_the_delay(self):
        home = tempfile.mkdtemp()
        plan = {"n": 2, "members": [{"number": 1, "ip": "10.207.0.1"}, {"number": 2, "ip": "10.207.0.2"}],
                "input_delay": 3, "rtc": "20261128000000"}
        felink.mame_lockstep_args(LOCKSTEP, plan, 1, home)
        with open(os.path.join(home, ".cache", "fliperos", "party-mame", "cfg", "fliperos-lockstep.ini")) as f:
            self.assertIn("delay=3\n", f.read())


class FileServerTests(unittest.TestCase):
    def test_the_relay_gets_no_file(self):
        home = tempfile.mkdtemp()
        os.makedirs(os.path.join(home, "roms"))
        with open(os.path.join(home, "roms", "g.zip"), "wb") as f:
            f.write(b"game")
        wire = felink.Wire("lo", "127.0.0.1", "255.0.0.0", "127.255.255.255")
        allowed = {"value": False}
        srv = felink.FileServer(wire, home, ["roms/g.zip"], port=0, allow_ip=lambda ip: allowed["value"])
        port = srv.httpd.server_address[1]
        srv.start()
        try:
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen("http://127.0.0.1:%d/manifest" % port, timeout=3)
            self.assertEqual(e.exception.code, 403)
            allowed["value"] = True
            with urllib.request.urlopen("http://127.0.0.1:%d/file/roms/g.zip" % port, timeout=3) as r:
                self.assertEqual(r.read(), b"game")
        finally:
            srv.stop()


class FakeTunnel:
    def __init__(self, addr, rtt=None):
        self.addr, self.rtt = addr, rtt
        self.peers = []
        self.status = "up"
        self.started = self.stopped = False
        self.handled = []

    def start(self, members):
        self.started = True

    def stop(self):
        self.stopped = True

    def handle(self, msg):
        self.handled.append(msg)

    def snapshot(self):
        return {"status": self.status, "error": None, "addr": self.addr, "peers": self.peers}

    def worst_rtt(self):
        return self.rtt

    def direct(self, ip):
        return any(p["addr"] == ip and p["path"] == "direct" for p in self.peers)


class FakeOnline:
    def __init__(self):
        self.sent = []

    def send(self, msg):
        self.sent.append(msg)


class FakeLink:
    def __init__(self):
        self.calls = []
        self.message = None
        self.profile = None
        self.role = None

    def host_game(self, profile, system, name, files, rom=None):
        self.calls.append(("host", name, tuple(files)))
        self.profile, self.role = profile, "host"
        return True

    def join_party(self, party, profile, system, name, rom=None):
        self.calls.append(("join", party["host_ip"]))
        self.profile, self.role = profile, "guest"
        return True

    def tick(self, now=None):
        return None

    def lobby(self):
        return {"members": []}

    def leave(self):
        self.calls.append(("leave",))


class OnlinePartyTests(unittest.TestCase):
    def party(self, msg, game, rtt=None):
        self.online = FakeOnline()
        self.tunnel = FakeTunnel(msg["addr"], rtt)
        self.link = FakeLink()
        p = mmparty.OnlineParty(self.online, msg, game, tempfile.mkdtemp(), "MANGO",
                                tunnel_factory=lambda addr: self.tunnel, link_factory=lambda: self.link)
        p.start()
        return p

    def test_the_host_opens_the_room_once_the_tunnel_is_up(self):
        p = self.party({"op": "opened", "party": "p1", "addr": "10.207.0.1"},
                       {"system": "mame", "name": "sf2ce", "profile": dict(LOCKSTEP), "files": ["roms/mame/sf2ce.zip"]})
        self.tunnel.status = "starting"
        p.tick(0)
        self.assertEqual(self.link.calls, [])
        self.tunnel.status = "up"
        p.tick(1)
        self.assertEqual(self.link.calls, [("host", "sf2ce", ("roms/mame/sf2ce.zip",))])
        self.assertEqual(p.state()["stage"], "lobby")

    def test_a_guest_with_the_game_joins_over_the_relay(self):
        p = self.party({"op": "joined", "party": "p1", "addr": "10.207.0.2", "members": [],
                        "host": {"id": 7, "addr": "10.207.0.1"}},
                       {"system": "mame", "name": "sf2ce", "profile": dict(LOCKSTEP), "wanted": []})
        self.tunnel.peers = [{"id": 7, "addr": "10.207.0.1", "path": "relay"}]
        p.tick(0)
        self.assertEqual(self.link.calls, [("join", "10.207.0.1")])

    def test_a_guest_without_the_game_never_gets_it_through_the_relay(self):
        p = self.party({"op": "joined", "party": "p1", "addr": "10.207.0.2", "members": [],
                        "host": {"id": 7, "addr": "10.207.0.1"}},
                       {"system": "mame", "name": "sf2ce", "profile": dict(LOCKSTEP), "wanted": ["roms/mame/sf2ce.zip"]})
        self.tunnel.peers = [{"id": 7, "addr": "10.207.0.1", "path": "relay"}]
        p.tick(0)
        self.assertEqual(p.state()["stage"], "failed")
        self.assertIn("NEEDS THE ROM", p.state()["message"])
        self.assertEqual(self.link.calls, [])

    def test_no_way_to_the_host(self):
        p = self.party({"op": "joined", "party": "p1", "addr": "10.207.0.2", "members": [],
                        "host": {"id": 7, "addr": "10.207.0.1"}},
                       {"system": "mame", "name": "sf2ce", "profile": dict(LOCKSTEP), "wanted": []})
        self.tunnel.peers = [{"id": 7, "addr": "10.207.0.1", "path": "failed"}]
        p.tick(0)
        self.assertEqual(p.state()["message"], "NO WAY TO THE OTHER CABINET")

    def test_the_host_closing_ends_the_party(self):
        p = self.party({"op": "joined", "party": "p1", "addr": "10.207.0.2", "members": [],
                        "host": {"id": 7, "addr": "10.207.0.1"}},
                       {"system": "mame", "name": "sf2ce", "profile": dict(LOCKSTEP), "wanted": []})
        p.handle({"t": "party", "op": "closed", "party": "p1"})
        self.assertEqual(p.state()["stage"], "closed")
        p.handle({"t": "signal", "from": 7, "data": {}})
        self.assertEqual(self.tunnel.handled, [{"t": "signal", "from": 7, "data": {}}])

    def test_leaving_tells_the_server_and_drops_the_tunnel(self):
        p = self.party({"op": "opened", "party": "p1", "addr": "10.207.0.1"},
                       {"system": "mame", "name": "sf2ce", "profile": dict(LOCKSTEP), "files": []})
        p.tick(0)
        p.leave()
        self.assertIn({"t": "party", "op": "leave"}, self.online.sent)
        self.assertTrue(self.tunnel.stopped)
        self.assertIn(("leave",), self.link.calls)


class OnlineLinkTests(unittest.TestCase):
    def test_the_host_waits_for_the_ping_and_puts_the_delay_in_the_profile(self):
        tunnel = FakeTunnel("10.207.0.1", rtt=None)
        clock = [0.0]
        link = mmparty.OnlineLink(tempfile.mkdtemp(), tunnel, "MANGO", ident="abc", local_players=1,
                                  clock=lambda: clock[0])
        self.assertEqual((link.wire.name, link.wire.ip, link.wire.broadcast), ("wg-fliperos", "10.207.0.1",
                                                                               "10.207.0.255"))
        link.role, link.profile = "host", dict(LOCKSTEP)
        self.assertFalse(link.start_now())                  # no ping yet
        tunnel.rtt = 22
        self.assertEqual(link.tune(), 2)
        self.assertEqual(link.profile["input_delay"], 2)
        self.assertEqual(link.file_allow, tunnel.direct)


if __name__ == "__main__":
    unittest.main()
