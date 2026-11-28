"""The cabinet's side (fliperos-setup/gui/fews.py and feonline.py: standard
library only) against the real Matchmaker server on a free port.

    docker run --rm -v "$PWD:/w" -w /w/server/matchmaker python:3.12-slim \\
        sh -c "pip install -q -r requirements.txt && python -m unittest discover -s tests -v"
"""
import asyncio
import json
import os
import socket
import stat
import sys
import tempfile
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
GUI = os.path.abspath(os.path.join(HERE, "..", "..", "..", "fliperos-setup", "gui"))
sys.path.insert(0, GUI)

import feonline  # noqa: E402
import fews  # noqa: E402
from matchmaker import app, profile  # noqa: E402


class ServerThread:
    """The real server, in its own event loop on a thread."""

    def __init__(self):
        self.ready = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()
        if not self.ready.wait(10):
            raise RuntimeError("server did not start")

    def _run(self):
        async def main():
            self.loop = asyncio.get_running_loop()
            fut = self.loop.create_future()
            self.task = asyncio.ensure_future(app.run("127.0.0.1", 0, ":memory:", fut))
            self.server, ws_server = await fut
            self.port = ws_server.sockets[0].getsockname()[1]
            self.ready.set()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        asyncio.run(main())

    @property
    def url(self):
        return "ws://127.0.0.1:%d/ws" % self.port

    def stop(self):
        self.loop.call_soon_threadsafe(self.task.cancel)


def wait_for(cond, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.05)
    return False


class WebSocketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ServerThread()

    @classmethod
    def tearDownClass(cls):
        cls.srv.stop()

    def hello(self, ws, nick="MANGO"):
        ws.send(json.dumps({"t": "hello", "v": 1, "secret": os.urandom(32).hex(), "nick": nick}))
        return json.loads(ws.recv(timeout=5))

    def test_handshake_hello_welcome_profile(self):
        ws = fews.WebSocket(self.srv.url)
        welcome = self.hello(ws)
        self.assertEqual(welcome["t"], "welcome")
        self.assertRegex(welcome["tag"], r"^[0-9a-z]{4}$")
        prof = json.loads(ws.recv(timeout=5))
        self.assertEqual(prof["t"], "profile")
        ws.close()

    def test_a_timeout_loses_nothing(self):
        ws = fews.WebSocket(self.srv.url)
        self.hello(ws)
        ws.recv(timeout=5)                        # the profile
        for _ in range(20):                       # many timeouts, some in the middle of the counts coming in
            ws.recv(timeout=0.01)
        ws.send(json.dumps({"t": "ping", "n": 5}))
        got = None
        while got is None or got.get("t") != "pong":
            got = json.loads(ws.recv(timeout=3))
        self.assertEqual(got["n"], 5)
        ws.close()

    def test_a_bad_url_and_a_closed_port(self):
        with self.assertRaises(ValueError):
            fews.WebSocket("http://x/ws")
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        with self.assertRaises(OSError):
            fews.WebSocket("ws://127.0.0.1:%d/ws" % port, timeout=2)


class OnlineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ServerThread()

    @classmethod
    def tearDownClass(cls):
        cls.srv.stop()

    def test_online_presence_room_counts_and_ping(self):
        old = feonline.PING_EVERY
        feonline.PING_EVERY = 0.2
        try:
            a = feonline.Online("MANGO", self.srv.url, secret=os.urandom(32).hex())
            b = feonline.Online("KIWI", self.srv.url, secret=os.urandom(32).hex())
            a.start()
            b.start()
            self.assertTrue(wait_for(lambda: a.snapshot()["status"] == "online" and b.snapshot()["status"] == "online"))
            me = a.snapshot()["me"]
            self.assertEqual(me["nick"], "MANGO")
            b.watch("mame:sf2ce")
            a.presence(state="looking", game="mame:sf2ce", emu="groovymame")
            self.assertTrue(wait_for(lambda: [p["nick"] for p in b.snapshot()["rooms"].get("mame:sf2ce", [])] == ["MANGO"]))
            self.assertTrue(wait_for(lambda: b.snapshot()["counts"].get("mame:sf2ce", {}).get("looking") == 1))
            self.assertTrue(wait_for(lambda: a.snapshot()["rtt"] is not None))
            self.assertIsNotNone(a.snapshot()["profile"])
            a.stop()
            self.assertTrue(wait_for(lambda: b.snapshot()["rooms"].get("mame:sf2ce") == []))
            b.stop()
        finally:
            feonline.PING_EVERY = old

    def test_a_refused_nickname_stops_trying(self):
        o = feonline.Online("X" * 20, self.srv.url, secret=os.urandom(32).hex())
        o.start()
        self.assertTrue(wait_for(lambda: o.snapshot()["status"] == "refused"))
        self.assertEqual(o.snapshot()["error"], "nick")
        o.thread.join(3)
        self.assertFalse(o.thread.is_alive())

    def test_no_server_is_offline(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        o = feonline.Online("MANGO", "ws://127.0.0.1:%d/ws" % port, secret=os.urandom(32).hex())
        o.start()
        self.assertTrue(wait_for(lambda: o.snapshot()["status"] == "offline"))
        o.stop()

    def test_check(self):
        self.assertEqual(feonline.check(self.srv.url, internet=lambda: False), "internet")
        self.assertEqual(feonline.check(self.srv.url, internet=lambda: True), "ok")
        self.assertEqual(feonline.check("ws://127.0.0.1:1/ws", internet=lambda: True), "server")
        self.assertEqual(feonline.health_url("wss://a.b/ws"), "https://a.b/health")


class CabinetTests(unittest.TestCase):
    def test_the_secret_is_made_once_and_only_its_owner_reads_it(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "fliperos", "online.key")
            s1 = feonline.load_secret(path)
            s2 = feonline.load_secret(path)
            self.assertEqual(s1, s2)
            self.assertRegex(s1, r"^[0-9a-f]{64}$")
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
            self.assertIsNone(feonline.load_secret(os.path.join(d, "none"), create=False))

    def fake_net(self, d, ifaces, routes):
        route = os.path.join(d, "route")
        with open(route, "w") as f:
            f.write("Iface\tDestination\tGateway\tFlags\tRefCnt\tUse\tMetric\tMask\n")
            for iface, metric in routes:
                f.write("%s\t00000000\t0101A8C0\t0003\t0\t0\t%d\t00000000\n" % (iface, metric))
        sysfs = os.path.join(d, "net")
        for name, wifi in ifaces:
            os.makedirs(os.path.join(sysfs, name))
            if wifi:
                os.makedirs(os.path.join(sysfs, name, "wireless"))
        return route, sysfs

    def test_cable_or_wifi_by_the_default_route(self):
        with tempfile.TemporaryDirectory() as d:
            route, sysfs = self.fake_net(d, [("enp2s0", False), ("wlan0", True)], [("wlan0", 600), ("enp2s0", 100)])
            self.assertEqual(feonline.conn_type(route, sysfs), "cable")
        with tempfile.TemporaryDirectory() as d:
            route, sysfs = self.fake_net(d, [("wlan0", True)], [("wlan0", 600)])
            self.assertEqual(feonline.conn_type(route, sysfs), "wifi")
        with tempfile.TemporaryDirectory() as d:
            route, sysfs = self.fake_net(d, [("enp2s0", False)], [])
            self.assertIsNone(feonline.conn_type(route, sysfs))

    def test_the_profile_signature_is_checked(self):
        signer = profile.Signer()
        signed = signer.sign({"v": 1, "nick": "MANGO", "total": {"w": 3, "l": 1}})
        pub = signer.public_info()
        self.assertEqual(feonline.verify_profile(signed, pub)["nick"], "MANGO")
        signed["payload"] = signed["payload"].replace('"w":3', '"w":30')
        self.assertIs(feonline.verify_profile(signed, pub), False)

    def test_the_pinned_key_is_the_live_servers(self):
        self.assertEqual(feonline.PUBKEY["kid"], "2cf268e1d202ad3a")


if __name__ == "__main__":
    unittest.main()
