"""Tests of the Matchmaker server (phase 1): a real server on a free port and
real WebSocket clients.

    docker run --rm -v "$PWD/server/matchmaker:/m" -w /m python:3.12-slim \\
        sh -c "pip install -q -r requirements.txt && python -m unittest discover -s tests -v"
"""
import asyncio
import json
import os
import re
import secrets
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from websockets.asyncio.client import connect  # noqa: E402

from matchmaker import app, identity, profile  # noqa: E402
from matchmaker.hub import Hub, Player, clean_presence  # noqa: E402
from matchmaker.store import Store  # noqa: E402


def new_secret():
    return secrets.token_hex(32)


class IdentityTests(unittest.TestCase):
    def test_the_tag_is_four_base36_lowercase(self):
        tag = next(identity.tags_for(identity.key_hash(new_secret())))
        self.assertRegex(tag, r"^[0-9a-z]{4}$")

    def test_the_server_never_keeps_the_secret(self):
        s = new_secret()
        self.assertNotEqual(identity.key_hash(s), s)
        self.assertEqual(len(identity.key_hash(s)), 64)

    def test_a_secret_must_be_64_hex(self):
        for bad in ("", "abc", "z" * 64, None):
            with self.assertRaises(ValueError):
                identity.key_hash(bad)

    def test_nicknames_follow_the_cabinet_name_rules(self):
        self.assertEqual(identity.clean_nick(" mango "), "MANGO")
        self.assertEqual(identity.clean_nick("arcade  1"), "ARCADE 1")
        for bad in ("", "A" * 13, "MÁNGO", "#TAG", "-ABC", "PORRA2"):
            with self.assertRaises(ValueError):
                identity.clean_nick(bad)


class StoreTests(unittest.TestCase):
    def test_two_cabinets_with_one_nickname_get_different_tags(self):
        st = Store(":memory:")
        a = st.register(identity.key_hash(new_secret()), "MANGO")
        b = st.register(identity.key_hash(new_secret()), "MANGO")
        self.assertEqual(a[1], b[1])
        self.assertNotEqual(a[2], b[2])

    def test_a_tag_taken_by_another_key_moves_to_the_next(self):
        st = Store(":memory:")
        k1, k2 = identity.key_hash(new_secret()), identity.key_hash(new_secret())
        own = next(identity.tags_for(k2))
        st.db.execute("INSERT INTO cabinets (key_hash, nick, tag, created, last_seen) VALUES (?, 'KIWI', ?, 0, 0)",
                      (k1, own))
        _, _, tag = st.register(k2, "KIWI")
        self.assertNotEqual(tag, own)

    def test_renaming_keeps_the_tag_when_it_is_free(self):
        st = Store(":memory:")
        cab_id, _, tag = st.register(identity.key_hash(new_secret()), "MANGO")
        self.assertEqual(st.seen(cab_id, "PAPAYA"), ("PAPAYA", tag))


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.st = Store(":memory:")
        self.signer = profile.Signer()
        self.cab_id, _, _ = self.st.register(identity.key_hash(new_secret()), "MANGO")

    def signed(self):
        version, rec = self.st.record(self.cab_id)
        return self.signer.sign(profile.payload(self.st.row(self.cab_id), rec, version, "0" * 64))

    def test_a_signed_profile_verifies_with_the_public_key(self):
        pub = self.signer.public_info()["public"]
        data = profile.verify(self.signed(), pub)
        self.assertEqual((data["nick"], data["version"], data["record"]), ("MANGO", 1, {}))
        self.assertEqual(data["total"], {"w": 0, "l": 0, "matches": 0})

    def test_changing_one_number_breaks_the_signature(self):
        signed = self.signed()
        signed["payload"] = signed["payload"].replace('"w":0', '"w":99')
        self.assertIsNone(profile.verify(signed, self.signer.public_info()["public"]))

    def test_another_key_cannot_sign_for_the_server(self):
        forged = profile.Signer().sign(json.loads(self.signed()["payload"]))
        self.assertIsNone(profile.verify(forged, self.signer.public_info()["public"]))

    def test_every_result_raises_the_version(self):
        self.st.add_result(self.cab_id, "mame:sf2ce", True)
        self.st.add_result(self.cab_id, "mame:sf2ce", False)
        version, rec = self.st.add_result(self.cab_id, "mame:kof98", True)
        self.assertEqual(version, 4)
        data = profile.verify(self.signed(), self.signer.public_info()["public"])
        self.assertEqual(data["record"], {"mame:kof98": {"l": 0, "w": 1}, "mame:sf2ce": {"l": 1, "w": 1}})
        self.assertEqual(data["total"], {"w": 2, "l": 1, "matches": 3})

    def test_the_key_comes_from_the_environment_seed(self):
        seed = profile.b64(secrets.token_bytes(32))
        a, b = profile.Signer(seed), profile.Signer(seed)
        self.assertEqual(a.kid, b.kid)
        self.assertFalse(a.ephemeral)


class HubTests(unittest.TestCase):
    def player(self, n, **info):
        p = Player(n, "P%d" % n, "000%d" % n, None)
        p.info.update(info)
        return p

    def test_counts_per_game_and_looking(self):
        hub = Hub()
        for p in (self.player(1, game="mame:sf2ce", state="looking"), self.player(2, game="mame:sf2ce", state="playing"),
                  self.player(3, game="mame:kof98", state="idle"), self.player(4)):
            hub.join(p)
        self.assertEqual(hub.counts(), {"mame:sf2ce": {"players": 2, "looking": 1},
                                        "mame:kof98": {"players": 1, "looking": 0}})

    def test_who_plays_together_sits_together_in_the_room(self):
        hub = Hub()
        for p in (self.player(1, game="g:x", state="playing", group="b"), self.player(2, game="g:x", state="looking"),
                  self.player(3, game="g:x", state="playing", group="a"), self.player(4, game="g:x", state="playing", group="b"),
                  self.player(5, game="g:x", state="playing", group="a")):
            hub.join(p)
        room = hub.room("g:x")
        self.assertEqual(room[0]["state"], "looking")
        self.assertEqual([p["group"] for p in room[1:]], ["a", "a", "b", "b"])

    def test_bad_presence_fields_are_dropped(self):
        out = clean_presence({"state": "hacking", "game": "MAME SF2", "pct": 101, "conn": "cable", "rtt": 30,
                              "score": "2-1", "kind": "match"})
        self.assertEqual(out.get("conn"), "cable")
        self.assertEqual(out.get("rtt"), 30)
        self.assertNotIn("state", out)
        self.assertNotIn("game", out)
        self.assertNotIn("pct", out)


class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        loop = asyncio.get_running_loop()
        ready = loop.create_future()
        self.task = asyncio.create_task(app.run("127.0.0.1", 0, ":memory:", ready))
        self.server, ws_server = await asyncio.wait_for(ready, 5)
        self.port = ws_server.sockets[0].getsockname()[1]
        self.url = "ws://127.0.0.1:%d/ws" % self.port

    async def asyncTearDown(self):
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            pass

    async def open(self, secret=None, nick="MANGO", ip="10.0.0.1", **extra):
        ws = await connect(self.url, additional_headers={"CF-Connecting-IP": ip})
        await ws.send(json.dumps(dict({"t": "hello", "v": 1, "secret": secret or new_secret(), "nick": nick,
                                       "conn": "cable"}, **extra)))
        return ws, json.loads(await asyncio.wait_for(ws.recv(), 3))

    async def next_of(self, ws, kind, timeout=3.0):
        async def find():
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("t") == kind:
                    return msg
        return await asyncio.wait_for(find(), timeout)

    async def test_health(self):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        writer.write(b"GET /health HTTP/1.1\r\nHost: x\r\n\r\n")
        await writer.drain()
        head = await asyncio.wait_for(reader.read(200), 3)
        writer.close()
        self.assertIn(b" 200 ", head)

    async def test_hello_gives_nick_and_tag_and_the_same_tag_next_time(self):
        s = new_secret()
        ws, msg = await self.open(s)
        self.assertEqual(msg["t"], "welcome")
        self.assertEqual(msg["nick"], "MANGO")
        self.assertRegex(msg["tag"], r"^[0-9a-z]{4}$")
        await ws.close()
        ws2, again = await self.open(s)
        self.assertEqual((again["id"], again["tag"]), (msg["id"], msg["tag"]))
        await ws2.close()

    async def test_refusals(self):
        for extra, code in (({"nick": "x" * 20}, "nick"), ({"secret": "123"}, "secret"), ({"v": 99}, "version")):
            ws = await connect(self.url)
            hello = dict({"t": "hello", "v": 1, "secret": new_secret(), "nick": "MANGO"}, **extra)
            await ws.send(json.dumps(hello))
            msg = json.loads(await asyncio.wait_for(ws.recv(), 3))
            self.assertEqual((msg["t"], msg["code"]), ("error", code))
            await ws.close()

    async def test_a_banned_key_is_refused(self):
        s = new_secret()
        self.server.store.ban(identity.key_hash(s), "test")
        ws, msg = await self.open(s)
        self.assertEqual((msg["t"], msg["code"]), ("error", "banned"))
        await ws.close()

    async def test_new_identities_per_address_are_limited(self):
        codes = []
        for _ in range(app.SIGNUPS_PER_HOUR + 1):
            ws, msg = await self.open(ip="203.0.113.9")
            codes.append(msg.get("code") or msg["t"])
            await ws.close()
        self.assertEqual(codes[-1], "signups")
        self.assertEqual(codes[:-1], ["welcome"] * app.SIGNUPS_PER_HOUR)

    async def test_presence_reaches_the_counts_and_the_room(self):
        a, _ = await self.open(nick="MANGO")
        b, _ = await self.open(nick="KIWI")
        await b.send(json.dumps({"t": "watch", "game": "mame:sf2ce"}))
        empty = await self.next_of(b, "room")
        self.assertEqual(empty["players"], [])
        await a.send(json.dumps({"t": "presence", "state": "looking", "game": "mame:sf2ce", "emu": "groovymame",
                                 "rtt": 28}))
        counts = await self.next_of(b, "counts")
        while counts["games"].get("mame:sf2ce") is None:
            counts = await self.next_of(b, "counts")
        self.assertEqual(counts["games"]["mame:sf2ce"], {"players": 1, "looking": 1})
        room = await self.next_of(b, "room")
        self.assertEqual([(p["nick"], p["state"], p["rtt"]) for p in room["players"]], [("MANGO", "looking", 28)])
        await a.close()
        gone = await self.next_of(b, "room")
        self.assertEqual(gone["players"], [])
        await b.close()

    async def test_the_profile_comes_after_welcome_and_matches_pubkey(self):
        ws, welcome = await self.open(nick="KIWI")
        msg = await self.next_of(ws, "profile")
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        writer.write(b"GET /pubkey HTTP/1.1\r\nHost: x\r\n\r\n")
        await writer.drain()
        raw = await asyncio.wait_for(reader.read(2000), 3)
        writer.close()
        pub = json.loads(raw.split(b"\r\n\r\n", 1)[1])
        self.assertEqual(pub["alg"], "Ed25519")
        data = profile.verify(msg["profile"], pub["public"])
        self.assertEqual((data["id"], data["nick"], data["tag"]), (welcome["id"], "KIWI", welcome["tag"]))
        await ws.close()

    async def test_ping(self):
        ws, _ = await self.open()
        await ws.send(json.dumps({"t": "ping", "n": 7}))
        self.assertEqual(await self.next_of(ws, "pong"), {"t": "pong", "n": 7})
        await ws.close()

    async def test_the_same_cabinet_twice_keeps_one_presence(self):
        s = new_secret()
        a, _ = await self.open(s)
        b, _ = await self.open(s)
        self.assertEqual(len(self.server.hub.players), 1)
        await a.close()
        await b.close()

    async def test_tags_never_carry_upper_case(self):
        for _ in range(3):
            ws, msg = await self.open(nick="ZEBRA", ip="198.51.100.%d" % secrets.randbelow(200))
            self.assertTrue(re.fullmatch(r"[0-9a-z]{4}", msg["tag"]))
            await ws.close()


if __name__ == "__main__":
    unittest.main()
