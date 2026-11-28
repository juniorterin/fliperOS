"""Tests of the online parties and the relay's credentials (phase 2): the
party rules on their own, then a real server with real WebSocket clients.

    docker run --rm -v "$PWD/server/matchmaker:/m" -w /m python:3.12-slim \\
        sh -c "pip install -q -r requirements.txt && python -m unittest discover -s tests -v"
"""
import asyncio
import json
import os
import secrets
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from websockets.asyncio.client import connect  # noqa: E402

from matchmaker import app, turn  # noqa: E402
from matchmaker.hub import Hub, Player  # noqa: E402
from matchmaker.parties import Parties, clean_signal  # noqa: E402
from matchmaker.store import Store  # noqa: E402


def player(n):
    return Player(n, "P%d" % n, "000%d" % n, None)


class PartyRuleTests(unittest.TestCase):
    def setUp(self):
        self.hub = Hub()
        self.parties = Parties(self.hub)
        self.a, self.b, self.c = player(1), player(2), player(3)
        for p in (self.a, self.b, self.c):
            self.hub.join(p)

    def test_the_host_is_dot_one_and_guests_follow(self):
        party, notes = self.parties.open_party(self.a, "mame:sf2ce", "groovymame", 4)
        self.assertEqual(notes[-1][1]["addr"], "10.207.0.1")
        _, notes = self.parties.join(self.b, party.id)
        joined = next(m for who, m in notes if who is self.b)
        self.assertEqual((joined["op"], joined["addr"], joined["host"]["addr"]), ("joined", "10.207.0.2", "10.207.0.1"))
        guest = next(m for who, m in notes if who is self.a)
        self.assertEqual((guest["op"], guest["peer"]["id"], guest["peer"]["addr"]), ("guest", 2, "10.207.0.2"))

    def test_every_party_gets_its_own_net(self):
        p1, _ = self.parties.open_party(self.a, "mame:sf2ce", "groovymame", 2)
        p2, _ = self.parties.open_party(self.b, "mame:kof98", "groovymame", 2)
        self.assertNotEqual(p1.net, p2.net)

    def test_the_server_sets_group_kind_and_places(self):
        party, _ = self.parties.open_party(self.a, "mame:sf2ce", "groovymame", 3)
        self.parties.join(self.b, party.id)
        for p in (self.a, self.b):
            self.assertEqual((p.info["group"], p.info["kind"], p.info["score"], p.info["game"]),
                             (party.id, "party", "2/3", "mame:sf2ce"))

    def test_full_closed_and_gone(self):
        party, _ = self.parties.open_party(self.a, "mame:sf2ce", "groovymame", 2)
        self.parties.join(self.b, party.id)
        self.assertEqual(self.parties.join(self.c, party.id)[0], "full")
        self.parties.leave(self.b)
        self.parties.lock(self.a, False)
        self.assertEqual(self.parties.join(self.c, party.id)[0], "closed")
        self.assertEqual(self.parties.join(self.c, "pzzz")[0], "gone")
        self.assertEqual(self.parties.join(self.c, "../etc")[0], "gone")

    def test_only_the_host_locks(self):
        party, _ = self.parties.open_party(self.a, "mame:sf2ce", "groovymame", 3)
        self.parties.join(self.b, party.id)
        self.assertFalse(self.parties.lock(self.b, False))
        self.assertTrue(party.open)

    def test_the_host_leaving_closes_it_for_everyone(self):
        party, _ = self.parties.open_party(self.a, "mame:sf2ce", "groovymame", 3)
        self.parties.join(self.b, party.id)
        self.parties.join(self.c, party.id)
        notes = self.parties.leave(self.a)
        self.assertEqual(sorted(who.id for who, m in notes if m["op"] == "closed"), [2, 3])
        self.assertIsNone(self.parties.party_of(self.b))
        self.assertIsNone(self.b.info["group"])
        self.assertNotIn(party.id, self.parties.by_id)

    def test_a_guest_leaving_tells_the_host_and_frees_its_address(self):
        party, _ = self.parties.open_party(self.a, "mame:sf2ce", "groovymame", 3)
        self.parties.join(self.b, party.id)
        notes = self.parties.leave(self.b)
        self.assertEqual(notes, [(self.a, {"t": "party", "op": "left", "party": party.id, "id": 2})])
        _, notes = self.parties.join(self.c, party.id)
        self.assertEqual(next(m for who, m in notes if who is self.c)["addr"], "10.207.0.2")

    def test_signals_go_between_host_and_guest_only(self):
        party, _ = self.parties.open_party(self.a, "mame:sf2ce", "groovymame", 3)
        self.parties.join(self.b, party.id)
        self.parties.join(self.c, party.id)
        self.assertIs(self.parties.may_signal(self.a, 2), self.b)
        self.assertIs(self.parties.may_signal(self.b, 1), self.a)
        self.assertIsNone(self.parties.may_signal(self.b, 3))          # guest to guest: no
        self.assertIsNone(self.parties.may_signal(self.a, 1))
        self.assertIsNone(self.parties.may_signal(player(4), 1))

    def test_signal_data_must_be_a_small_object(self):
        self.assertEqual(clean_signal({"key": "k"}), {"key": "k"})
        self.assertIsNone(clean_signal("text"))
        self.assertIsNone(clean_signal({"x": "y" * 2000}))


class FakeCloudflare:
    def __init__(self):
        self.calls = 0

    def __call__(self, key_id, token, ttl):
        self.calls += 1
        return {"iceServers": [{"urls": ["stun:stun.cloudflare.com:3478"]},
                               {"urls": ["turn:turn.cloudflare.com:3478?transport=udp",
                                         "turns:turn.cloudflare.com:443?transport=tcp"],
                                "username": "u%d" % self.calls, "credential": "c%d" % self.calls}]}


class TurnRuleTests(unittest.IsolatedAsyncioTestCase):
    async def test_off_without_a_key(self):
        t = turn.Turn(Store(":memory:"))
        with self.assertRaises(turn.TurnError) as e:
            await t.credentials(1)
        self.assertEqual(e.exception.code, "off")

    async def test_the_turn_urls_of_the_answer(self):
        t = turn.Turn(Store(":memory:"), "k", "t", fetch=FakeCloudflare())
        ice = await t.credentials(1)
        self.assertEqual(ice["urls"], ["turn:turn.cloudflare.com:3478?transport=udp",
                                       "turns:turn.cloudflare.com:443?transport=tcp"])
        self.assertEqual((ice["username"], ice["ttl"]), ("u1", turn.TTL))

    async def test_the_old_answer_shape_too(self):
        old = {"iceServers": {"urls": ["turn:turn.cloudflare.com:3478"], "username": "u", "credential": "c"}}
        self.assertEqual(turn.ice_of(old)["username"], "u")

    async def test_the_monthly_cap(self):
        st = Store(":memory:")
        t = turn.Turn(st, "k", "t", cap_gb=(turn.RESERVE * 2) / 10**9, fetch=FakeCloudflare())
        await t.credentials(1)
        await t.credentials(2)
        with self.assertRaises(turn.TurnError) as e:
            await t.credentials(3)
        self.assertEqual(e.exception.code, "cap")

    async def test_a_report_replaces_the_reserve_once(self):
        st = Store(":memory:")
        t = turn.Turn(st, "k", "t", fetch=FakeCloudflare())
        ice = await t.credentials(1)
        month = turn.month_of(t.clock())
        self.assertEqual(st.turn_bytes(month), turn.RESERVE)
        self.assertFalse(t.used(2, ice["username"], 10))          # not that cabinet's
        self.assertTrue(t.used(1, ice["username"], 1234))
        self.assertFalse(t.used(1, ice["username"], 1))            # only once
        self.assertEqual(st.turn_bytes(month), 1234)
        self.assertFalse(t.used(1, ice["username"], -5))

    async def test_a_report_never_beyond_what_a_credential_carries(self):
        st = Store(":memory:")
        t = turn.Turn(st, "k", "t", fetch=FakeCloudflare())
        ice = await t.credentials(1)
        t.used(1, ice["username"], 10**15)
        self.assertEqual(st.turn_bytes(turn.month_of(t.clock())), turn.TTL * turn.CEILING)

    async def test_credentials_per_cabinet_per_day(self):
        t = turn.Turn(Store(":memory:"), "k", "t", fetch=FakeCloudflare())
        for _ in range(turn.PER_DAY):
            await t.credentials(1)
        with self.assertRaises(turn.TurnError) as e:
            await t.credentials(1)
        self.assertEqual(e.exception.code, "daily")
        await t.credentials(2)

    async def test_cloudflare_down_is_fail(self):
        def broken(*a):
            raise OSError("down")
        t = turn.Turn(Store(":memory:"), "k", "t", fetch=broken)
        with self.assertRaises(turn.TurnError) as e:
            await t.credentials(1)
        self.assertEqual(e.exception.code, "fail")


class PartyServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        loop = asyncio.get_running_loop()
        ready = loop.create_future()
        self.task = asyncio.create_task(app.run("127.0.0.1", 0, ":memory:", ready))
        self.server, ws_server = await asyncio.wait_for(ready, 5)
        self.cloudflare = FakeCloudflare()
        self.server.turn = turn.Turn(self.server.store, "k", "t", fetch=self.cloudflare)
        self.url = "ws://127.0.0.1:%d/ws" % ws_server.sockets[0].getsockname()[1]
        self.open_ws = []

    async def asyncTearDown(self):
        for ws in self.open_ws:
            await ws.close()
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            pass

    async def cabinet(self, nick, secret=None):
        ws = await connect(self.url, additional_headers={"CF-Connecting-IP": "10.1.%d.1" % secrets.randbelow(250)})
        await ws.send(json.dumps({"t": "hello", "v": 1, "secret": secret or secrets.token_hex(32), "nick": nick}))
        welcome = await self.next_of(ws, "welcome")
        self.open_ws.append(ws)
        return ws, welcome["id"]

    async def next_of(self, ws, kind, op=None, timeout=3.0):
        async def find():
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("t") == kind and (op is None or msg.get("op") == op):
                    return msg
        return await asyncio.wait_for(find(), timeout)

    async def send(self, ws, **msg):
        await ws.send(json.dumps(msg))

    async def test_open_join_signal_and_close(self):
        host, host_id = await self.cabinet("MANGO")
        guest, guest_id = await self.cabinet("KIWI")
        await self.send(host, t="party", op="open", game="mame:sf2ce", emu="groovymame", max=2)
        opened = await self.next_of(host, "party", "opened")
        await self.send(guest, t="party", op="join", party=opened["party"])
        joined = await self.next_of(guest, "party", "joined")
        self.assertEqual((joined["host"]["id"], joined["host"]["nick"], joined["addr"]),
                         (host_id, "MANGO", "10.207.0.2"))
        told = await self.next_of(host, "party", "guest")
        self.assertEqual(told["peer"]["id"], guest_id)
        await self.send(guest, t="signal", to=host_id, data={"key": "abc", "cands": [["stun", "203.0.113.5", 40000]]})
        sig = await self.next_of(host, "signal")
        self.assertEqual((sig["from"], sig["data"]["key"]), (guest_id, "abc"))
        await host.close()
        closed = await self.next_of(guest, "party", "closed")
        self.assertEqual(closed["party"], opened["party"])

    async def test_the_room_shows_the_party(self):
        host, _ = await self.cabinet("MANGO")
        watcher, _ = await self.cabinet("LYNX")
        await self.send(watcher, t="watch", game="mame:sf2ce")
        await self.send(host, t="party", op="open", game="mame:sf2ce", emu="groovymame", max=4)
        opened = await self.next_of(host, "party", "opened")
        room = await self.next_of(watcher, "room")
        while not room["players"]:
            room = await self.next_of(watcher, "room")
        p = room["players"][0]
        self.assertEqual((p["group"], p["kind"], p["score"], p["open"]), (opened["party"], "party", "1/4", True))

    async def test_a_cabinet_cannot_fake_a_group(self):
        a, _ = await self.cabinet("MANGO")
        await self.send(a, t="presence", state="playing", game="mame:sf2ce", group="pfake", kind="match", score="5-0")
        await asyncio.sleep(0.2)
        info = next(iter(self.server.hub.players.values())).info
        self.assertEqual((info["group"], info["kind"], info["score"]), (None, None, None))

    async def test_no_signal_outside_a_party(self):
        a, _ = await self.cabinet("MANGO")
        b, b_id = await self.cabinet("KIWI")
        await self.send(a, t="signal", to=b_id, data={"key": "x"})
        with self.assertRaises(asyncio.TimeoutError):
            await self.next_of(b, "signal", timeout=0.5)

    async def test_relay_credentials_only_in_a_party(self):
        a, _ = await self.cabinet("MANGO")
        await self.send(a, t="turn")
        self.assertEqual((await self.next_of(a, "turn"))["error"], "party")
        await self.send(a, t="party", op="open", game="mame:sf2ce", emu="groovymame", max=2)
        await self.next_of(a, "party", "opened")
        await self.send(a, t="turn")
        got = await self.next_of(a, "turn")
        self.assertEqual(got["ice"]["username"], "u1")
        self.assertTrue(all(u.startswith(("turn:", "turns:")) for u in got["ice"]["urls"]))

    async def test_join_errors(self):
        a, _ = await self.cabinet("MANGO")
        await self.send(a, t="party", op="join", party="p999")
        self.assertEqual((await self.next_of(a, "party", "error"))["code"], "gone")
        await self.send(a, t="party", op="open", game="BAD GAME", emu="groovymame", max=2)
        self.assertEqual((await self.next_of(a, "party", "error"))["code"], "bad")

    async def test_the_same_cabinet_again_ends_its_old_party(self):
        secret = secrets.token_hex(32)
        host, _ = await self.cabinet("MANGO", secret)
        guest, _ = await self.cabinet("KIWI")
        await self.send(host, t="party", op="open", game="mame:sf2ce", emu="groovymame", max=2)
        opened = await self.next_of(host, "party", "opened")
        await self.send(guest, t="party", op="join", party=opened["party"])
        await self.next_of(guest, "party", "joined")
        await self.cabinet("MANGO", secret)
        await self.next_of(guest, "party", "closed")
        self.assertEqual(self.server.parties.by_id, {})


if __name__ == "__main__":
    unittest.main()
