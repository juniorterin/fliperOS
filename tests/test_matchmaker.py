#!/usr/bin/env python3
"""The Matchmaker: its data (fliperos-setup/gui/mmdata.py: the pages per
emulator or core, the game ids, the rows of a page and of a game's lobby)
and the program (gui/fliperos-matchmaker, with the fake library and online
session of tools/matchmaker/shots.py; needs pygame).

    docker run --rm -v "$PWD:/w" -w /w fliperos-guitest python3 tests/test_matchmaker.py
"""
import importlib.util
import json
import os
import re
import sys
import tempfile
import time
import types
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GUI = os.path.join(ROOT, "fliperos-setup", "gui")
sys.path.insert(0, GUI)

import mmdata  # noqa: E402

SYSTEMS = [
    {"key": "mame", "exe": "/x/fliperos-kms-run", "args": "groovymame [name]"},
    {"key": "naomi", "exe": "/x/fliperos-kms-run", "args": "flycast [rom]"},
    {"key": "atomiswave", "exe": "/x/fliperos-kms-run", "args": "flycast [rom]"},
    {"key": "retroarch/fbneo", "exe": "/x/fliperos-kms-run", "args": "retroarch -L fbneo"},
    {"key": "retroarch/mame2010", "exe": "/x/fliperos-kms-run", "args": "retroarch -L mame2010"},
    {"key": "model2", "exe": "/x/fliperos-x11-run", "args": "fliperos-model2 [name]"},
    {"key": "hbmame", "exe": "/x/fliperos-kms-run", "args": "hbgroovymame [name]"},
]


def deterministic(key):
    return key == "retroarch/fbneo"


class PagesTests(unittest.TestCase):
    def test_one_page_per_emulator_or_core_never_per_console(self):
        pages = mmdata.pages(SYSTEMS, deterministic)
        self.assertEqual([p["name"] for p in pages], ["GROOVYMAME", "HBGROOVYMAME", "FLYCAST", "FBNEO"])
        flycast = pages[2]
        self.assertEqual([s["key"] for s in flycast["systems"]], ["naomi", "atomiswave"])

    def test_dojo_names_the_flycast_page(self):
        self.assertEqual(mmdata.page_of({"key": "naomi2"}, dojo=True), ("flycast", "FLYCAST DOJO"))

    def test_cores_without_rollback_and_other_emulators_are_left_out(self):
        self.assertIsNone(mmdata.page_of({"key": "retroarch/mame2010"}, deterministic))
        self.assertIsNone(mmdata.page_of({"key": "model2"}, deterministic))

    def test_game_ids(self):
        self.assertEqual(mmdata.game_id("mame", {"Name": "sf2ce"}), "mame:sf2ce")
        self.assertIsNone(mmdata.game_id("mame", {"Name": "Bad Name!"}))


class HomeRowsTests(unittest.TestCase):
    def setUp(self):
        self.page = {"key": "mame", "name": "GROOVYMAME"}
        self.games = [{"Name": "3countb"}, {"Name": "sf2ce"}, {"Name": "kof98"}]

    def test_online_now_first_the_fullest_on_top_then_the_other_games(self):
        counts = {"mame:sf2ce": {"players": 5, "looking": 2}, "mame:kof98": {"players": 3, "looking": 1},
                  "naomi:mvsc2": {"players": 9, "looking": 0}}
        rows = mmdata.home_rows(self.page, self.games, counts)
        self.assertEqual((rows[0]["kind"], rows[0]["count"]), ("group", 2))
        self.assertEqual([r["id"] for r in rows[1:3]], ["mame:sf2ce", "mame:kof98"])
        self.assertTrue(rows[2]["last"])
        self.assertEqual([r["game"]["Name"] for r in rows[3:]], ["3countb"])

    def test_a_game_this_cabinet_lacks_still_shows(self):
        rows = mmdata.home_rows(self.page, self.games, {"mame:garou": {"players": 2, "looking": 0}})
        row = rows[1]
        self.assertFalse(row["have"])
        self.assertEqual((row["game"]["Title"], row["game"].get("_missing")), ("GAROU", True))

    def test_a_closed_group_hides_its_games(self):
        rows = mmdata.home_rows(self.page, self.games, {"mame:sf2ce": {"players": 1}}, opened=False)
        self.assertEqual([r["kind"] for r in rows], ["group", "game", "game"])
        self.assertEqual(rows[0]["count"], 1)


class LobbyRowsTests(unittest.TestCase):
    PLAYERS = [
        {"id": 1, "nick": "MANGO", "tag": "a7k2", "state": "looking"},
        {"id": 2, "nick": "KIWI", "tag": "0f3d", "state": "playing", "group": "m1", "kind": "match", "score": "2-1"},
        {"id": 3, "nick": "LYNX", "tag": "9q2m", "state": "playing", "group": "m1", "kind": "match", "score": "2-1"},
        {"id": 4, "nick": "OTTER", "tag": "b52c", "state": "party", "group": "p1", "kind": "party", "score": "2/2"},
        {"id": 5, "nick": "GUAVA", "tag": "3mxp", "state": "download", "group": "p1", "kind": "party", "pct": 45},
        {"id": 6, "nick": "ACAI", "tag": "77rt", "state": "idle"},
    ]

    def test_who_plays_together_is_one_row_with_them_inside(self):
        rows = mmdata.lobby_rows(self.PLAYERS)
        kinds = [(r["kind"], r.get("name") or r.get("text") or r["player"]["nick"]) for r in rows]
        self.assertEqual(kinds, [
            ("group", "LOOKING"), ("player", "MANGO"),
            ("group", "PLAYING"), ("sub", "KIWI VS LYNX"), ("player", "KIWI"), ("player", "LYNX"),
            ("group", "IN PARTY"), ("sub", "PARTY OTTER"), ("player", "OTTER"), ("player", "GUAVA"),
            ("group", "IDLE")])
        match = rows[3]
        self.assertEqual(match["right"], "2-1")
        self.assertEqual([r["level"] for r in rows[4:6]], [2, 2])
        self.assertEqual(rows[7]["right"], "2/2")

    def test_idle_opens_and_a_match_closes(self):
        rows = mmdata.lobby_rows(self.PLAYERS, opened={"IDLE": True}, open_subs={"m1": False})
        names = [r.get("name") or r.get("text") or r["player"]["nick"] for r in rows]
        self.assertNotIn("KIWI", names)
        self.assertEqual(names[-1], "ACAI")

    def test_counts_are_players(self):
        rows = mmdata.lobby_rows(self.PLAYERS)
        self.assertEqual({r["name"]: r["count"] for r in rows if r["kind"] == "group"},
                         {"LOOKING": 1, "PLAYING": 2, "IN PARTY": 2, "IDLE": 1})


class SeparateProgramTests(unittest.TestCase):
    """The Matchmaker is its own program: a frontend of the sessions table,
    with its own icon, that never imports the standard frontend."""

    def test_it_is_a_session_of_its_own(self):
        with open(os.path.join(ROOT, "config", "fliperos-sessions.conf"), encoding="utf-8") as f:
            rows = [line.split("|") for line in f.read().splitlines() if line and not line.startswith("#")]
        row = next(r for r in rows if r[0] == "matchmaker")
        self.assertEqual(row[1:4], ["kms", "/usr/local/lib/fliperos-setup/gui/fliperos-matchmaker", ""])
        with open(os.path.join(ROOT, "fliperos-rootfs.sh"), encoding="utf-8") as f:
            self.assertIn('"$root/usr/local/lib/fliperos-setup/gui/fliperos-matchmaker"', f.read())

    def test_the_standard_frontend_stays_out(self):
        for name in ("fliperos-matchmaker", "mmview.py", "mmdata.py"):
            with open(os.path.join(GUI, name), encoding="utf-8") as f:
                text = f.read()
            # (the comments may name it; loading it, never)
            self.assertNotRegex(text, r"[\"']fliperos-frontend[\"']|import fliperos_frontend", name)
        with open(os.path.join(GUI, "feview.py"), encoding="utf-8") as f:
            self.assertNotRegex(f.read(), r"(?i)matchmaker|feonline")

    def test_the_setup_icon_is_16_by_16_in_the_theme_letters(self):
        with open(os.path.join(GUI, "theme.py"), encoding="utf-8") as f:
            text = f.read()
        art = re.search(r'ICONS\["matchmaker"\] = """(.*?)"""', text, re.S).group(1).split()
        self.assertEqual((len(art), {len(r) for r in art}), (16, {16}))
        self.assertLessEqual(set("".join(art)) - {"."}, set("PKCFMGORYDLB"))

    def test_every_icon_the_screens_load_exists(self):
        with open(os.path.join(GUI, "mmview.py"), encoding="utf-8") as f:
            text = f.read()
        names = set(re.findall(r'icon\("([a-z0-9_]+)"', text))
        names |= {"ping_%d" % n for n in range(1, 5)} | {"retry_32", "back_32"}
        missing = [n for n in sorted(names) if not os.path.isfile(os.path.join(GUI, "icons", "matchmaker", n + ".png"))]
        self.assertEqual(missing, [])


@unittest.skipUnless(importlib.util.find_spec("pygame"), "needs pygame (fliperos-guitest)")
class ProgramTests(unittest.TestCase):
    """The program with the fake library and online session of the shots."""

    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
        cls.home = tempfile.TemporaryDirectory()
        os.environ["HOME"] = cls.home.name
        sys.path.insert(0, os.path.join(ROOT, "tools", "matchmaker"))
        import shots
        cls.shots = shots
        cls.prog = shots.load_program()
        cls.prog.CONFIG = os.path.join(cls.home.name, "matchmaker.json")

    @classmethod
    def tearDownClass(cls):
        cls.home.cleanup()

    def make(self, check="ok"):
        self.online = self.shots.FakeOnline()
        checks = []

        def fake_check():
            checks.append(1)
            return check if len(checks) == 1 else "ok"
        self.checks = checks
        mm = self.prog.Matchmaker(types.SimpleNamespace(shot="x"), library=self.shots.FakeLibrary(None),
                                  online=self.online, check=fake_check,
                                  netplay_core=lambda k: k == "retroarch/fbneo", nick="FLIPEROS")
        return mm

    def ids(self, mm):
        return [r.get("id") or r.get("name") for r in mm.rows]

    def test_pages_are_the_emulators_and_the_home_lists_online_now_first(self):
        mm = self.make()
        self.assertEqual([p["name"] for p in mm.cats], ["GROOVYMAME", "FLYCAST", "FBNEO"])
        self.assertEqual(mm.screen, "home")
        self.assertEqual(self.ids(mm)[:5], ["ONLINE NOW", "mame:sf2ce", "mame:kof98", "mame:xmen", "mame:rbff2"])
        self.assertFalse(mm.rows[4]["have"])
        self.assertNotIn("mame:sf2ce", self.ids(mm)[5:])
        mm.draw(time.monotonic())

    def test_without_internet_the_warning_then_try_again(self):
        mm = self.make("internet")
        self.assertEqual((mm.screen, mm.offline), ("offline", "internet"))
        mm.draw(time.monotonic())
        self.assertEqual(mm.act("b1"), None)          # TRY AGAIN
        self.assertEqual((len(self.checks), mm.screen), (2, "home"))

    def test_back_on_the_warning_closes(self):
        mm = self.make("server")
        mm.act("right")
        self.assertEqual(mm.act("b1"), "quit")

    def test_the_lobby_tells_the_server_and_back_leaves_it(self):
        mm = self.make()
        mm.cursor = 1
        mm.act("b1")
        self.assertEqual(mm.screen, "lobby")
        self.assertIn(("presence", {"state": "idle", "game": "mame:sf2ce", "emu": "mame"}), self.online.sent)
        self.assertIn(("watch", "mame:sf2ce"), self.online.sent)
        self.assertEqual([r["name"] for r in mm.rows if r["kind"] == "group"],
                         ["LOOKING", "PLAYING", "IN PARTY", "IDLE"])
        mm.draw(time.monotonic())
        mm.act("b2")
        self.assertEqual(mm.screen, "home")
        self.assertEqual(mm.rows[mm.cursor].get("id"), "mame:sf2ce")
        self.assertEqual(self.online.sent[-2:], [("presence", {"state": "idle", "game": None}), ("watch", None)])

    def test_a_group_opens_and_closes(self):
        mm = self.make()
        mm.cursor = 0
        mm.act("b1")
        self.assertEqual(self.ids(mm)[:2], ["ONLINE NOW", "mame:1944"])
        mm.act("b1")
        self.assertEqual(self.ids(mm)[1], "mame:sf2ce")

    def test_the_page_switch_is_the_frontends_and_is_remembered(self):
        mm = self.make()
        mm.act("right")
        self.assertTrue(mm.picking)
        self.assertEqual(mm.page()["name"], "GROOVYMAME")       # the strip moves first
        mm.act("b1")
        self.assertEqual(mm.page()["name"], "FLYCAST")
        self.assertEqual(self.ids(mm)[:2], ["ONLINE NOW", "flycast:mvsc2"])
        mm.act("left")
        mm.pick_at -= self.prog.PICK_WAIT
        mm.tick(time.monotonic())
        self.assertEqual(mm.page()["name"], "GROOVYMAME")
        with open(self.prog.CONFIG, encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"page": "mame"})

    def test_a_refused_cabinet_gets_the_warning(self):
        mm = self.make()
        self.online.state["status"] = "refused"
        self.online.changed.set()
        mm.tick(time.monotonic())
        self.assertEqual((mm.screen, mm.offline), ("offline", "refused"))


if __name__ == "__main__":
    unittest.main()
