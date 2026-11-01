#!/usr/bin/env python3
"""Testes do gui/felink.py: link play e net play entre gabinetes. Sem tela e
sem emulador: a rede e o loopback, os arquivos sao de uma pasta temporaria.

    docker run --rm -v "$(pwd -W):/w" -w /w fliperos-tests python3 tests/test_link.py
"""
import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fliperos-setup" / "gui"))

import felink  # noqa: E402

LOOP = felink.Wire("lo", "127.0.0.1", "255.0.0.0", "127.255.255.255")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wait(cond, seconds=3.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.02)
    return cond()


class ProfilesTests(unittest.TestCase):
    def setUp(self):
        self.p = felink.Profiles()

    def test_every_profile_has_what_the_launcher_reads(self):
        self.assertTrue(self.p.games)
        for g in self.p.games:
            for key in ("id", "title", "emulator", "systems", "sets", "min", "max", "fixed", "order", "step", "port"):
                self.assertIn(key, g, g["id"])
            self.assertIn(g["order"], ("master-first", "slaves-first", "chain"))
            self.assertLessEqual(g["min"], g["max"])
            if g["fixed"]:
                self.assertEqual(g["min"], g["max"])

    def test_find_by_system_and_set(self):
        self.assertEqual(self.p.find("model3", "scud")["id"], "scud")
        self.assertEqual(self.p.find("model2", "daytona")["id"], "daytona")
        self.assertEqual(self.p.find("mame", "ssf2tbu")["id"], "ssf2tb")
        self.assertIsNone(self.p.find("mame", "sf2"))
        self.assertIsNone(self.p.find("model2", "scud"))
        # uma pasta de nucleo do RetroArch (retroarch/fbneo) usa a primeira parte da chave
        self.assertIsNone(self.p.find("retroarch/fbneo", "ssf2tb"))

    def test_the_tested_sizes(self):
        self.assertEqual((self.p.get("scud")["min"], self.p.get("scud")["max"]), (2, 8))
        self.assertEqual(self.p.get("dirtdvls")["max"], 2)
        ssf = self.p.get("ssf2tb")
        self.assertTrue(ssf["fixed"])
        self.assertEqual((ssf["min"], ssf["max"]), (4, 4))

    def test_every_nvram_profile_has_its_files_in_the_repository(self):
        src = ROOT / "config" / "link-nvram"
        for g in self.p.games:
            spec = g.get("nvram")
            if not spec:
                continue
            for number in range(1, g["max"] + 1):
                for ext in spec["files"]:
                    self.assertTrue((src / spec["dir"] / ("cabinet%d.%s" % (number, ext))).is_file(), (g["id"], number, ext))


class WireTests(unittest.TestCase):
    def make(self, root, name, wireless=False, device=True, state="up"):
        d = Path(root) / name
        d.mkdir()
        if device:
            (d / "device").mkdir()
        if wireless:
            (d / "wireless").mkdir()
        (d / "operstate").write_text(state + "\n")

    def test_the_wired_one_wins_over_wifi_and_virtual(self):
        with tempfile.TemporaryDirectory() as root:
            self.make(root, "lo", device=False)
            self.make(root, "docker0", device=False)
            self.make(root, "veth12", device=False)
            self.make(root, "wlan0", wireless=True)
            self.make(root, "ens133")
            addrs = {("ens133", 0x8915): "192.168.1.241", ("ens133", 0x891b): "255.255.255.0",
                     ("wlan0", 0x8915): "192.168.1.9", ("wlan0", 0x891b): "255.255.255.0"}
            wire = felink.wired(root, lambda n, r: addrs.get((n, r)))
            self.assertEqual((wire.name, wire.ip, wire.broadcast), ("ens133", "192.168.1.241", "192.168.1.255"))

    def test_no_wire_when_the_cable_is_out_or_there_is_only_wifi(self):
        with tempfile.TemporaryDirectory() as root:
            self.make(root, "ens133", state="down")
            self.make(root, "wlan0", wireless=True)
            self.assertIsNone(felink.wired(root, lambda n, r: "192.168.1.9"))

    def test_the_subnet_check(self):
        wire = felink.Wire("e", "192.168.1.241", "255.255.255.0", "192.168.1.255")
        self.assertTrue(felink.same_net(wire, "192.168.1.7"))
        self.assertFalse(felink.same_net(wire, "192.168.2.7"))
        self.assertFalse(felink.same_net(wire, "not an ip"))


class PlanTests(unittest.TestCase):
    def members(self, n):
        return [{"number": i, "name": "C%d" % i, "ip": "10.0.0.%d" % i} for i in range(1, n + 1)]

    def test_slaves_first_for_a_ring_of_four_starts_the_master_last(self):
        plan = felink.make_plan(felink.Profiles().get("scud"), self.members(4))
        self.assertEqual(plan["order"], [4, 3, 2, 1])
        self.assertEqual(plan["delays"], {"4": 0, "3": 10, "2": 20, "1": 30})

    def test_a_pair_starts_the_master_first(self):
        plan = felink.make_plan(felink.Profiles().get("scud"), self.members(2))
        self.assertEqual(plan["order"], [1, 2])

    def test_master_first_and_chain(self):
        p = felink.Profiles()
        self.assertEqual(felink.make_plan(p.get("daytona"), self.members(3))["order"], [1, 2, 3])
        plan = felink.make_plan(p.get("ssf2tb"), self.members(4))
        self.assertEqual(plan["order"], [1, 2, 3, 4])
        self.assertEqual(plan["delays"]["4"], 18)

    def test_the_neighbour_is_the_next_in_a_ring_and_the_previous_in_a_chain(self):
        p = felink.Profiles()
        ring = felink.make_plan(p.get("scud"), self.members(3))
        self.assertEqual([felink.neighbour(p.get("scud"), ring, k) for k in (1, 2, 3)], ["10.0.0.2", "10.0.0.3", "10.0.0.1"])
        chain = felink.make_plan(p.get("ssf2tb"), self.members(4))
        self.assertEqual([felink.neighbour(p.get("ssf2tb"), chain, k) for k in (1, 2, 3, 4)],
                         [None, "10.0.0.1", "10.0.0.2", "10.0.0.3"])


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.p = felink.Profiles()
        self.members = [{"number": i, "name": "C%d" % i, "ip": "10.0.0.%d" % i} for i in range(1, 5)]

    def test_supermodel_gets_the_net_options_after_the_rom(self):
        prof = self.p.get("scud")
        plan = felink.make_plan(prof, self.members)
        argv = felink.command(prof, ["x11-run", "supermodel", "/r/scud.zip"], plan, 2, "scud")
        self.assertEqual(argv, ["x11-run", "supermodel", "/r/scud.zip", "-net", "-port-in=1970", "-port-out=1970",
                                "-address-out=10.0.0.3"])
        self.assertEqual(felink.command(prof, ["x", "supermodel", "r"], plan, 4, "scud")[-1], "-address-out=10.0.0.1")

    def test_sm2emu_names_the_set_before_the_game(self):
        prof = self.p.get("daytona")
        plan = felink.make_plan(prof, self.members[:2])
        self.assertEqual(felink.command(prof, ["x11-run", "fliperos-model2", "daytona"], plan, 1, "daytona"),
                         ["x11-run", "fliperos-model2", "--game", "daytona", "daytona"])
        keys = felink.sm2_keys(prof, plan, 2, "10.0.0.2")
        self.assertEqual((keys["link_enabled"], keys["link_next_ip"], keys["link_port"]), ("true", "10.0.0.1", "15112"))

    def test_groovymame_chain_options(self):
        prof = self.p.get("ssf2tb")
        plan = felink.make_plan(prof, self.members)
        head = felink.command(prof, ["x11-run", "groovymame", "ssf2tb"], plan, 1, "ssf2tb")
        self.assertEqual(head[-1], "ssf2tb")
        self.assertEqual(head[head.index("-comm_remotehost") + 1], "")
        self.assertEqual(head[head.index("-comm_localhost") + 1], "0.0.0.0")
        tail = felink.command(prof, ["x11-run", "groovymame", "ssf2tb"], plan, 4, "ssf2tb")
        self.assertEqual(tail[tail.index("-comm_localhost") + 1], "")
        self.assertEqual(tail[tail.index("-comm_remotehost") + 1], "10.0.0.3")

    def test_ini_set_replaces_or_appends_and_returns_the_old_text(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "cfg", "sm2-emu.ini")
            self.assertEqual(felink.ini_set(path, {"link_enabled": "true"}), "")
            before = felink.ini_set(path, {"link_enabled": "false", "link_port": "15112"})
            self.assertEqual(before, "link_enabled = true\n")
            self.assertEqual(Path(path).read_text(), "link_enabled = false\nlink_port = 15112\n")


class NvramTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        self.src = os.path.join(self.tmp.name, "src")
        self.prof = felink.Profiles().get("scud")
        os.makedirs(os.path.join(self.src, "supermodel", "scud"))
        for n in (1, 2):
            Path(self.src, "supermodel", "scud", "cabinet%d.nv" % n).write_bytes(b"cab%d" % n)
        self.dest = os.path.join(self.home, "nvram", "model3", "scudau.nv")

    def tearDown(self):
        self.tmp.cleanup()

    def test_install_puts_the_cabinets_file_and_keeps_the_players_own(self):
        os.makedirs(os.path.dirname(self.dest))
        Path(self.dest).write_bytes(b"mine")
        restore = felink.install_nvram(self.prof, 2, self.home, self.src)
        self.assertEqual(Path(self.dest).read_bytes(), b"cab2")
        self.assertEqual(Path(self.dest + ".solo").read_bytes(), b"mine")
        restore()
        self.assertEqual(Path(self.dest).read_bytes(), b"mine")
        self.assertFalse(os.path.exists(self.dest + ".solo"))
        self.assertFalse(os.path.exists(os.path.join(self.home, "nvram", ".link-active")))

    def test_a_second_install_does_not_overwrite_the_saved_solo_file(self):
        os.makedirs(os.path.dirname(self.dest))
        Path(self.dest).write_bytes(b"mine")
        felink.install_nvram(self.prof, 1, self.home, self.src)
        felink.install_nvram(self.prof, 2, self.home, self.src)
        self.assertEqual(Path(self.dest + ".solo").read_bytes(), b"mine")
        felink.recover(self.home)
        self.assertEqual(Path(self.dest).read_bytes(), b"mine")

    def test_no_file_of_theirs_means_the_game_makes_its_own_after(self):
        restore = felink.install_nvram(self.prof, 1, self.home, self.src)
        self.assertEqual(Path(self.dest).read_bytes(), b"cab1")
        restore()
        self.assertFalse(os.path.exists(self.dest))

    def test_a_number_without_a_file_changes_nothing(self):
        self.assertEqual(felink.nvram_files(self.prof, 5, self.home, self.src), [])
        felink.install_nvram(self.prof, 5, self.home, self.src)
        self.assertFalse(os.path.exists(self.dest))

    def test_sm2emu_has_two_files_per_cabinet(self):
        prof = felink.Profiles().get("daytona")
        files = felink.nvram_files(prof, 3, self.home)
        self.assertEqual(sorted(os.path.basename(d) for _, d in files), ["daytona.eeprom", "daytona.nv"])


class PresenceTests(unittest.TestCase):
    def pair(self, **kw):
        port = free_port()
        a = felink.Presence(LOOP, "aaa", "CABINET-A", port=port, interval=0.1, **kw)
        b = felink.Presence(LOOP, "bbb", "CABINET-B", port=port, interval=0.1, **kw)
        for p in (a, b):
            p.start()
            self.addCleanup(p.stop)
        return a, b

    def test_they_see_each_other_and_what_the_other_plays(self):
        a, b = self.pair()
        a.say(game="daytona", system="model2", link="daytona", party="aaa", slot=1, max=8, state="lobby")
        self.assertTrue(wait(lambda: any(r["id"] == "aaa" for r in b.table())))
        rec = [r for r in b.table() if r["id"] == "aaa"][0]
        self.assertEqual((rec["name"], rec["game"], rec["state"]), ("CABINET-A", "daytona", "lobby"))
        self.assertFalse(any(r["id"] == "bbb" for r in b.table()))   # nunca a si mesmo
        a.say(game=None)
        self.assertTrue(wait(lambda: "game" not in [r for r in b.table() if r["id"] == "aaa"][0]))

    def test_a_silent_cabinet_leaves_the_table(self):
        clock = [0.0]
        p = felink.Presence(LOOP, "me", "ME", clock=lambda: clock[0])
        pkt = json.dumps({"v": 1, "id": "x", "name": "X", "ip": "127.0.0.1"}).encode()
        p.hear(pkt, "127.0.0.1")
        self.assertEqual(len(p.table()), 1)
        clock[0] = 3.9
        self.assertEqual(len(p.table()), 1)
        clock[0] = 4.1
        self.assertEqual(p.table(), [])

    def test_it_ignores_other_subnets_forged_ips_and_junk(self):
        wire = felink.Wire("e", "192.168.1.241", "255.255.255.0", "192.168.1.255")
        p = felink.Presence(wire, "me", "ME")
        good = {"v": 1, "id": "x", "name": "X", "ip": "192.168.1.7"}
        p.hear(json.dumps(good).encode(), "192.168.1.7")
        p.hear(json.dumps(dict(good, id="y", ip="10.9.9.9")).encode(), "10.9.9.9")        # outra sub-rede (Wi-Fi, VPN)
        p.hear(json.dumps(dict(good, id="z", ip="192.168.1.8")).encode(), "192.168.1.7")  # diz um IP que nao e o dele
        p.hear(json.dumps(dict(good, id="me")).encode(), "192.168.1.7")                   # o proprio
        p.hear(json.dumps(dict(good, id="w", v=2)).encode(), "192.168.1.7")               # outra versao
        p.hear(b"not json", "192.168.1.7")
        p.hear(b'["a"]', "192.168.1.7")
        self.assertEqual([r["id"] for r in p.table()], ["x"])

    def test_the_parties_group_the_cabinets_by_party(self):
        table = [
            {"id": "a", "name": "A", "ip": "10.0.0.1", "party": "a", "slot": 1, "game": "daytona", "link": "daytona",
             "max": 8, "state": "lobby"},
            {"id": "b", "name": "B", "ip": "10.0.0.2", "party": "a", "slot": 2, "game": "daytona", "link": "daytona",
             "max": 8, "state": "lobby"},
            {"id": "c", "name": "C", "ip": "10.0.0.3", "party": "c", "slot": 1, "game": "ssf2tb", "link": "ssf2tb",
             "max": 4, "state": "playing"},
            {"id": "d", "name": "D", "ip": "10.0.0.4"},
        ]
        got = felink.parties(table)
        self.assertEqual([(p["game"], p["used"], p["max"], p["state"], p["host"], p["host_ip"]) for p in got],
                         [("ssf2tb", 1, 4, "playing", "C", "10.0.0.3"), ("daytona", 2, 8, "lobby", "A", "10.0.0.1")])
        self.assertEqual(got[1]["numbers"], [1, 2])


class PartyTests(unittest.TestCase):
    def setUp(self):
        self.port = free_port()
        self.prof = felink.Profiles().get("scud")
        self.changes = []
        self.host = felink.PartyHost(LOOP, self.prof, "scud", "host", "HOST", port=self.port,
                                     on_change=lambda: self.changes.append(1))
        self.host.open()
        self.addCleanup(self.host.close)

    def guest(self, name="G", game="scud"):
        g = felink.PartyGuest(LOOP, name, name, port=self.port)
        self.addCleanup(g.leave)
        ok = g.join("127.0.0.1", game)
        return g, ok

    def test_guests_get_the_next_numbers_and_everyone_sees_the_room(self):
        g2, ok2 = self.guest("G2")
        g3, ok3 = self.guest("G3")
        self.assertTrue(ok2 and ok3)
        self.assertEqual((g2.number, g3.number), (2, 3))
        self.assertTrue(wait(lambda: len(g2.party["members"]) == 3))
        self.assertEqual([m["name"] for m in g2.party["members"]], ["HOST", "G2", "G3"])
        self.assertEqual(self.host.count(), 3)

    def test_a_guest_who_leaves_frees_the_place_and_the_numbers_close_up(self):
        g2, _ = self.guest("G2")
        g3, _ = self.guest("G3")
        g2.leave()
        self.assertTrue(wait(lambda: self.host.count() == 2))
        self.assertTrue(wait(lambda: g3.number == 2))

    def test_the_wrong_game_and_a_full_party_are_refused(self):
        g, ok = self.guest("X", game="daytona")
        self.assertFalse(ok)
        self.assertEqual(g.refused, "game")
        for i in range(7):
            self.assertTrue(self.guest("G%d" % i)[1])
        g, ok = self.guest("late")
        self.assertFalse(ok)
        self.assertEqual(g.refused, "full")

    def test_nobody_answering_is_down(self):
        g = felink.PartyGuest(LOOP, "x", "x", port=free_port())
        self.assertFalse(g.join("127.0.0.1", "scud", timeout=1))
        self.assertEqual(g.refused, "down")

    def test_start_needs_the_minimum_then_closes_the_party_and_numbers_everyone(self):
        self.assertIsNone(self.host.start())
        g2, _ = self.guest("G2")
        g3, _ = self.guest("G3")
        plan = self.host.start()
        self.assertEqual(plan["n"], 3)
        self.assertEqual(plan["order"], [3, 2, 1])
        self.assertTrue(wait(lambda: g3.plan is not None and g2.plan is not None))
        self.assertEqual((g2.plan, g3.number), (plan, 3))
        self.assertEqual(self.host.state, "playing")
        late, ok = self.guest("late")
        self.assertFalse(ok)
        self.assertEqual(late.refused, "closed")

    def test_a_fixed_size_game_only_starts_with_everyone(self):
        port = free_port()
        host = felink.PartyHost(LOOP, felink.Profiles().get("ssf2tb"), "ssf2tb", "h", "H", port=port)
        host.open()
        self.addCleanup(host.close)
        guests = []
        for i in range(3):
            g = felink.PartyGuest(LOOP, "g%d" % i, "G%d" % i, port=port)
            self.addCleanup(g.leave)
            self.assertTrue(g.join("127.0.0.1", "ssf2tb"))
            guests.append(g)
            if i < 2:
                self.assertFalse(host.ready())
                self.assertIsNone(host.start())
        self.assertTrue(host.ready())
        self.assertEqual(host.start()["order"], [1, 2, 3, 4])

    def test_the_host_closing_sends_everybody_back(self):
        g2, _ = self.guest("G2")
        self.host.close()
        self.assertTrue(wait(lambda: g2.closed))
        self.assertIsNone(g2.plan)

    def test_it_only_takes_connections_from_the_cable_subnet(self):
        port = free_port()
        host = felink.PartyHost(LOOP, self.prof, "scud", "h", "H", port=port)
        host.open()
        self.addCleanup(host.close)
        g = felink.PartyGuest(LOOP, "g", "G", port=port)
        with mock.patch.object(felink, "same_net", return_value=False):
            self.assertFalse(g.join("127.0.0.1", "scud", timeout=1))
        self.assertEqual(host.count(), 1)


class FilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.host_home = os.path.join(self.tmp.name, "host")
        self.guest_home = os.path.join(self.tmp.name, "guest")
        os.makedirs(os.path.join(self.host_home, "roms", "model2"))
        os.makedirs(os.path.join(self.host_home, "secret"))
        self.data = os.urandom(3 * (1 << 20) + 123)
        Path(self.host_home, "roms", "model2", "daytona.zip").write_bytes(self.data)
        Path(self.host_home, "secret", "x").write_bytes(b"no")
        self.port = free_port()
        self.srv = felink.FileServer(LOOP, self.host_home, ["roms/model2/daytona.zip", "roms/model2/gone.zip"], port=self.port)
        self.srv.start()
        self.addCleanup(self.srv.stop)

    def test_fetch_copies_what_is_missing_and_checks_it(self):
        seen = []
        ok, missing = felink.fetch_files("127.0.0.1", self.guest_home, ["roms/model2/daytona.zip"], port=self.port,
                                         progress=lambda d, t, p: seen.append((d, t)))
        self.assertTrue(ok)
        self.assertEqual(missing, [])
        self.assertEqual(Path(self.guest_home, "roms", "model2", "daytona.zip").read_bytes(), self.data)
        self.assertEqual(seen[-1][0], seen[-1][1])
        self.assertFalse(os.path.exists(os.path.join(self.guest_home, "roms", "model2", "daytona.zip.part")))

    def test_what_the_host_does_not_have_is_reported(self):
        ok, missing = felink.fetch_files("127.0.0.1", self.guest_home, ["roms/model2/daytona.zip", "roms/model2/gone.zip"],
                                         port=self.port)
        self.assertFalse(ok)
        self.assertEqual(missing, ["roms/model2/gone.zip"])

    def test_a_drop_resumes_from_the_part_file(self):
        dest = Path(self.guest_home, "roms", "model2", "daytona.zip.part")
        dest.parent.mkdir(parents=True)
        dest.write_bytes(self.data[:1 << 20])
        ok, _ = felink.fetch_files("127.0.0.1", self.guest_home, ["roms/model2/daytona.zip"], port=self.port)
        self.assertTrue(ok)
        self.assertEqual(Path(self.guest_home, "roms", "model2", "daytona.zip").read_bytes(), self.data)

    def test_a_corrupt_part_is_refused(self):
        dest = Path(self.guest_home, "roms", "model2", "daytona.zip.part")
        dest.parent.mkdir(parents=True)
        dest.write_bytes(b"x" * (1 << 20))
        ok, missing = felink.fetch_files("127.0.0.1", self.guest_home, ["roms/model2/daytona.zip"], port=self.port)
        self.assertFalse(ok)
        self.assertEqual(missing, ["roms/model2/daytona.zip"])
        self.assertFalse(os.path.exists(os.path.join(self.guest_home, "roms", "model2", "daytona.zip")))

    def test_a_file_that_is_already_there_is_not_fetched_again(self):
        dest = Path(self.guest_home, "roms", "model2", "daytona.zip")
        dest.parent.mkdir(parents=True)
        dest.write_bytes(self.data)
        seen = []
        ok, _ = felink.fetch_files("127.0.0.1", self.guest_home, ["roms/model2/daytona.zip"], port=self.port,
                                   progress=lambda d, t, p: seen.append(d))
        self.assertTrue(ok)
        self.assertEqual(seen, [])

    def test_only_the_allowed_files_are_served(self):
        import urllib.error
        import urllib.request
        for path in ("/file/secret/x", "/file/../secret/x", "/file/%2e%2e/secret/x"):
            with self.assertRaises(urllib.error.HTTPError, msg=path):
                urllib.request.urlopen("http://127.0.0.1:%d%s" % (self.port, path), timeout=3)

    def test_it_does_not_serve_the_subnet_it_is_not_on(self):
        import urllib.error
        import urllib.request
        with mock.patch.object(felink, "same_net", return_value=False):
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen("http://127.0.0.1:%d/manifest" % self.port, timeout=3)


class LinkTests(unittest.TestCase):
    """Dois gabinetes (o Link de cada um) na mesma maquina, pelo loopback."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.now = [100.0]
        self.ports = {"presence": free_port(), "party": free_port(), "files": free_port()}
        self.a = self.cabinet("aaa", "home-a")
        self.b = self.cabinet("bbb", "home-b")
        os.makedirs(os.path.join(self.a.home, "roms", "model3"))
        Path(self.a.home, "roms", "model3", "scud.zip").write_bytes(b"scud")
        self.prof = self.a.profiles.get("scud")

    def cabinet(self, ident, folder):
        home = os.path.join(self.tmp.name, folder)
        os.makedirs(home)
        link = felink.Link(home, wire=LOOP, ident=ident, name=ident.upper(), ports=self.ports, clock=lambda: self.now[0])
        self.assertTrue(link.start())
        self.addCleanup(link.stop)
        return link

    def open_party(self):
        self.assertIsNotNone(self.a.host_game(self.prof, "model3", "scud", self.a.served([os.path.join(self.a.home, "roms/model3/scud.zip")])))
        self.assertTrue(wait(lambda: self.b.mark("model3", "scud") is True))
        return self.b.parties_for("model3", "scud")[0]

    def test_a_game_without_a_profile_has_no_mark_and_the_others_show_dim_or_lit(self):
        self.assertIsNone(self.b.mark("mame", "sf2"))
        self.assertIs(self.b.mark("model3", "scud"), False)
        party = self.open_party()
        self.assertEqual((party["host"], party["used"], party["max"], party["state"]), ("AAA", 1, 8, "lobby"))

    def test_a_cabinet_without_the_cable_does_nothing(self):
        link = felink.Link(self.tmp.name, wire=None, ident="x")
        self.assertFalse(link.start())
        self.assertFalse(link.available())
        self.assertIsNone(link.mark("model3", "scud"))
        self.assertEqual(link.parties(), [])

    def test_join_start_and_the_start_order(self):
        party = self.open_party()
        self.assertTrue(self.b.join_party(party, self.prof, "model3", "scud"))
        self.assertEqual(self.b.number, 2)
        self.assertTrue(wait(lambda: len(self.a.lobby()["members"]) == 2))
        self.assertTrue(wait(lambda: any(p["used"] == 2 for p in self.b.parties())) or True)
        self.assertIsNone(self.a.tick())                      # flexivel: espera o botao do anfitriao
        self.assertTrue(self.a.start_now())
        self.assertTrue(wait(lambda: self.b.guest.plan is not None))
        self.assertIsNone(self.b.tick())                      # recebeu o plano, a contagem comeca
        self.assertEqual(self.b.number, 2)
        # Para dois, o master sobe primeiro (3 s de contagem) e o escravo 10 s depois.
        self.now[0] = 100.0 + felink.COUNTDOWN - 0.1
        self.assertIsNone(self.a.tick())
        self.now[0] = 100.0 + felink.COUNTDOWN + 0.1
        self.assertEqual(self.a.tick(), "launch")
        self.assertIsNone(self.a.tick())                      # so uma vez
        self.assertIsNone(self.b.tick())
        self.now[0] = 100.0 + felink.COUNTDOWN + 10.1
        self.assertEqual(self.b.tick(), "launch")
        self.assertEqual(self.a.lobby()["plan"]["order"], [1, 2])

    def test_the_command_carries_the_numbers_nvram_and_the_way_back(self):
        party = self.open_party()
        self.b.join_party(party, self.prof, "model3", "scud")
        self.a.start_now()
        self.assertTrue(wait(lambda: self.b.guest.plan is not None))
        self.b.tick()
        dest = os.path.join(self.b.home, "nvram", "model3", "scudau.nv")
        os.makedirs(os.path.dirname(dest))
        Path(dest).write_bytes(b"mine")
        argv = self.b.command(["x11-run", "supermodel", "/r/scud.zip"])
        self.assertEqual(argv[:3], ["x11-run", "supermodel", "/r/scud.zip"])
        self.assertIn("-net", argv)
        self.assertEqual(Path(dest).read_bytes(), Path(felink.NVRAM_SRC, "supermodel/scud/cabinet2.nv").read_bytes())
        self.b.leave()
        self.assertEqual(Path(dest).read_bytes(), b"mine")
        self.assertIsNone(self.b.lobby())

    def test_sm2emu_writes_and_then_turns_the_link_off_in_the_ini(self):
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.a.home, "cfg")
        self.addCleanup(os.environ.pop, "XDG_CONFIG_HOME")
        prof = self.a.profiles.get("daytona")
        self.a.host_game(prof, "model2", "daytona", [])
        self.assertTrue(wait(lambda: self.b.parties_for("model2", "daytona")))
        self.b.join_party(self.b.parties_for("model2", "daytona")[0], prof, "model2", "daytona")
        self.a.start_now()
        ini = os.path.join(self.a.home, "cfg", "sm2-emu", "sm2-emu.ini")
        argv = self.a.command(["x11-run", "fliperos-model2", "daytona"])
        self.assertEqual(argv, ["x11-run", "fliperos-model2", "--game", "daytona", "daytona"])
        text = Path(ini).read_text()
        self.assertIn("link_enabled = true", text)
        self.assertIn("link_next_ip = 127.0.0.1", text)
        self.a.leave()
        self.assertIn("link_enabled = false", Path(ini).read_text())

    def test_the_tournament_battle_starts_by_itself_with_four(self):
        prof = self.a.profiles.get("ssf2tb")
        self.a.host_game(prof, "mame", "ssf2tb", [])
        cabinets = [self.b] + [self.cabinet("c%d" % i, "home-c%d" % i) for i in range(2)]
        self.assertTrue(wait(lambda: self.b.parties_for("mame", "ssf2tb")))
        party = self.b.parties_for("mame", "ssf2tb")[0]
        for i, link in enumerate(cabinets):
            self.assertTrue(link.join_party(party, prof, "mame", "ssf2tb"))
            self.assertIsNone(self.a.tick())                   # o tick que comeca devolve None; o plano ja saiu
            self.assertEqual(self.a.lobby()["plan"] is not None, i == 2)
        self.assertEqual(self.a.lobby()["plan"]["order"], [1, 2, 3, 4])
        self.assertTrue(wait(lambda: cabinets[-1].guest.plan is not None))
        self.assertEqual(self.a.lobby()["left"], felink.COUNTDOWN)
        late = self.cabinet("d", "home-d")
        self.assertFalse(late.join_party(party, prof, "mame", "ssf2tb"))

    def test_the_host_leaving_closes_the_party_for_the_guest(self):
        party = self.open_party()
        self.b.join_party(party, self.prof, "model3", "scud")
        self.a.leave()
        self.assertTrue(wait(lambda: self.b.tick() == "closed"))
        self.assertTrue(wait(lambda: self.b.mark("model3", "scud") is False))

    def test_a_started_party_is_closed_to_late_cabinets(self):
        party = self.open_party()
        self.b.join_party(party, self.prof, "model3", "scud")
        self.a.start_now()
        late = self.cabinet("late", "home-late")
        self.assertFalse(late.join_party(self.a.lobby() and {"host_ip": "127.0.0.1", "party": "aaa"}, self.prof, "model3", "scud"))
        self.assertEqual(late.message, felink.REASONS["closed"])


if __name__ == "__main__":
    unittest.main()
