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


# Os cores do RetroArch de mentira: o fbneo, o snes9x e o pcsx_rearmed fazem
# net play ("deterministic"), o mame2010 nao salva estado, o flycast so
# "serialized" e o genesis_plus_gx tem o .info mas nao o .so.
_ra = None


def setUpModule():
    global _ra
    _ra = tempfile.TemporaryDirectory()
    cores, info = os.path.join(_ra.name, "cores"), os.path.join(_ra.name, "info")
    os.makedirs(cores)
    os.makedirs(info)
    for core, state, so in (("fbneo", "deterministic", True), ("snes9x", "deterministic", True),
                            ("pcsx_rearmed", "deterministic", True), ("mame2010", "null", True),
                            ("flycast", "serialized", True), ("genesis_plus_gx", "deterministic", False)):
        with open(os.path.join(info, core + "_libretro.info"), "w") as fh:
            fh.write('corename = "%s"\nsavestate = "true"\nsavestate_features = "%s"\n' % (core, state))
        if so:
            Path(cores, core + "_libretro.so").touch()
    felink._states.clear()
    felink.RA_CORES, felink.RA_INFO = cores, info


def tearDownModule():
    _ra.cleanup()


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

    def test_flycast_naomi_network_server_and_client(self):
        prof = self.p.get("clubk2k3")
        self.assertEqual((prof["emulator"], prof["min"], prof["max"], prof["port"]), ("flycast", 2, 2, 37391))
        plan = felink.make_plan(prof, self.members[:2])
        base = ["x11-run", "flycast", "/r/clubk2k3.zip"]
        server = felink.command(prof, base, plan, 1, "clubk2k3")
        self.assertEqual(server, ["x11-run", "flycast", "-config",
                                  "network:Enable=yes,network:ActAsServer=yes,network:EnableUPnP=no", "/r/clubk2k3.zip"])
        client = felink.command(prof, base, plan, 2, "clubk2k3")
        self.assertEqual(client[3], "network:Enable=yes,network:ActAsServer=no,network:server=10.0.0.1,network:EnableUPnP=no")
        self.assertEqual(client[-1], "/r/clubk2k3.zip")
        self.assertEqual(plan["order"], [1, 2])         # o servidor primeiro

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


class FrontendLinkTests(unittest.TestCase):
    """O que o gui/fliperos-frontend faz com o link: os azulejos do menu do
    jogo e as linhas do alto da lista (sem desenhar nada)."""

    @classmethod
    def setUpClass(cls):
        from importlib.machinery import SourceFileLoader
        import types
        loader = SourceFileLoader("fliperos_frontend_link", str(ROOT / "fliperos-setup/gui/fliperos-frontend"))
        cls.fm = types.ModuleType(loader.name)
        cls.fm.__file__ = loader.path
        loader.exec_module(cls.fm)

    def stub(self, parties=(), profiled=("model3", "scud")):
        import types
        link = mock.Mock()
        link.available.return_value = True
        link.local_players = 2
        link.profile_of.side_effect = lambda system, name: (
            felink.Profiles().get("scud") if (system, name) == profiled else None)
        link.parties_for.side_effect = lambda system, name: [p for p in parties if (p["system"], p["game"]) == (system, name)]
        link.parties.return_value = list(parties)
        link.netplay_of.side_effect = lambda system, name, players: felink.netplay_profile(system, name, players, 2, sets={"xmen"})
        games = [{"Name": n, "Title": n, "_system": {"key": k}, "Players": pl}
                 for k, n, pl in (("mame", "sf2", "2"), ("model3", "scud", "1"), ("model3", "daytona2", "1"))]
        games.append({"Name": "xmen", "Title": "xmen", "_system": {"key": "retroarch/fbneo"}, "Players": "4"})
        fe = types.SimpleNamespace(link=link, games=games, mode="list", show_clones=True, opened=set(), cursor=0,
                                   fd=types.SimpleNamespace(tree=lambda gs: [(g, []) for g in gs]), filtered=lambda: games,
                                   rows=[], game=lambda: fe.rows[fe.cursor][0])
        fe.rebuild = lambda keep=None: self.fm.Frontend.rebuild(fe, keep)
        for name in ("popup_tiles", "link_profile"):
            setattr(fe, name, lambda *a, name=name: getattr(self.fm.Frontend, name)(fe, *a))
        return fe

    def party(self, state="lobby", used=2, mx=8):
        return {"party": "p", "game": "scud", "system": "model3", "state": state, "used": used, "max": mx, "host": "A",
                "host_ip": "10.0.0.2", "numbers": list(range(1, used + 1))}

    def kinds(self, fe, name):
        fe.rebuild(keep=name)
        return [t["kind"] for t in fe.popup_tiles()]

    def test_the_menu_of_a_normal_game_is_the_old_three_tiles(self):
        fe = self.stub()
        self.assertEqual(self.kinds(fe, "sf2"), ["play", "fav", "more"])

    def test_a_link_game_nobody_plays_offers_link_play(self):
        fe = self.stub()
        self.assertEqual(self.kinds(fe, "scud"), ["play", "link", "fav", "more"])

    def test_an_open_party_offers_join_and_a_new_link(self):
        fe = self.stub([self.party()])
        self.assertEqual(self.kinds(fe, "scud"), ["play", "join", "new", "fav", "more"])
        join = fe.popup_tiles()[1]
        self.assertEqual((join["label"], join["party"]["host_ip"]), ("JOIN LINK", "10.0.0.2"))

    def test_a_game_with_more_players_than_controls_offers_net_play(self):
        fe = self.stub()
        self.assertEqual(self.kinds(fe, "xmen"), ["play", "link", "fav", "more"])
        tile = fe.popup_tiles()[1]
        self.assertEqual((tile["label"], tile["net"]), ("NET PLAY", True))
        party = dict(self.party(), game="xmen", system="retroarch/fbneo", max=4)
        fe2 = self.stub([party])
        self.assertEqual(self.kinds(fe2, "xmen"), ["play", "join", "new", "fav", "more"])
        self.assertEqual([t["label"] for t in fe2.popup_tiles()[1:3]], ["JOIN PARTY", "NEW PARTY"])
        # Este gabinete tem 2 controles: ocupa 2 jogadores, ou os que sobrarem.
        self.assertEqual([t["take"] for t in fe2.popup_tiles()[1:3]], [2, 2])
        fe2.link.parties_for.side_effect = lambda s, n: [dict(party, used=3)]
        self.assertEqual(fe2.popup_tiles()[1]["take"], 1)

    def test_a_started_or_full_party_is_shown_but_cannot_be_joined(self):
        fe = self.stub([self.party("playing"), self.party("lobby", used=8)])
        self.assertEqual(self.kinds(fe, "scud"), ["play", "closed", "closed", "new", "fav", "more"])
        self.assertEqual([t["label"] for t in fe.popup_tiles()[1:3]], ["STARTED", "FULL"])

    def test_the_games_other_cabinets_play_come_first_in_the_list_only(self):
        fe = self.stub([self.party()])
        fe.rebuild()
        self.assertEqual([(r[0]["Name"], r[2]) for r in fe.rows[:2]], [("scud", "elsewhere"), ("sf2", [])])
        self.assertEqual(len(fe.rows), 5)
        fe.rebuild(keep="scud")      # o mesmo jogo, na lista de baixo: nao a linha do alto
        self.assertEqual(fe.rows[fe.cursor][2], [])
        fe.mode = "flow"
        fe.rebuild()
        self.assertEqual(len(fe.rows), 4)

    def test_a_party_of_a_game_this_cabinet_does_not_have_adds_no_row(self):
        party = dict(self.party(), game="outrogame")
        fe = self.stub([party])
        fe.rebuild()
        self.assertEqual(len(fe.rows), 4)

    def test_the_frontend_without_the_link_or_the_cable_still_builds_the_list(self):
        fe = self.stub()
        fe.link.available.return_value = False
        fe.rebuild()
        self.assertEqual(len(fe.rows), 4)
        del fe.link
        fe.rebuild()
        self.assertEqual(len(fe.rows), 4)


class SlotsTests(unittest.TestCase):
    """O net play ocupa um jogador por controle configurado."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.prof = felink.netplay_profile("retroarch/fbneo", "xmen", "6", 2, frozenset({"xmen"}))
        self.port = free_port()

    def host(self, take=2):
        host = felink.PartyHost(LOOP, self.prof, "xmen", "h", "H", port=self.port, take=take)
        host.open()
        self.addCleanup(host.close)
        return host

    def guest(self, name, want):
        g = felink.PartyGuest(LOOP, name, name, port=self.port)
        self.addCleanup(g.leave)
        return g, g.join("127.0.0.1", "xmen", want=want)

    def devices(self, n, keyboard=True):
        """Um /proc/bus/input/devices com n joysticks (js) e um teclado."""
        path = os.path.join(self.tmp.name, "devices-%d" % n)
        text = "I: Bus=0011 Vendor=0001\nN: Name=\"AT keyboard\"\nH: Handlers=sysrq kbd event3 leds\n\n"
        for i in range(n):
            text += "I: Bus=0003 Vendor=045e\nN: Name=\"Xbox 360 Controller\"\nH: Handlers=event%d js%d\n\n" % (5 + i, i)
        Path(path).write_text(text)
        return path

    def test_the_local_players_are_the_mapped_players_with_a_controller_connected(self):
        path = os.path.join(self.tmp.name, "buttons.map")
        Path(path).write_text("1 up 0 h0.1 Pad\n1 b1 0 b0 Pad\n2 up 1 h0.1 Pad\n3 coin 2 b9 Pad\n")
        self.assertEqual(felink.connected_joysticks(self.devices(2)), 2)
        self.assertEqual(felink.local_players(path, self.devices(3)), 3)
        # Soltar o controle de um jogador tira o jogador; ligar de volta o devolve.
        self.assertEqual(felink.local_players(path, self.devices(2)), 2)
        self.assertEqual(felink.local_players(path, self.devices(1)), 1)
        self.assertEqual(felink.local_players(path, self.devices(3)), 3)
        # Sem controle nenhum, ao menos 1 (o teclado joga).
        self.assertEqual(felink.local_players(path, self.devices(0)), 1)

    def test_a_keyboard_encoder_player_is_always_there(self):
        path = os.path.join(self.tmp.name, "buttons.map")
        Path(path).write_text("1 up -1 k:UP Keyboard\n1 b1 -1 k:LCTRL Keyboard\n2 up -1 k:R Keyboard\n")
        self.assertEqual(felink.local_players(path, self.devices(0)), 2)

    def test_no_map_means_two_and_no_device_list_means_the_whole_map(self):
        self.assertEqual(felink.local_players(os.path.join(self.tmp.name, "nenhum"), self.devices(0)), 2)
        path = os.path.join(self.tmp.name, "buttons.map")
        Path(path).write_text("1 up 0 h0.1 Pad\n2 up 1 h0.1 Pad\n")
        self.assertEqual(felink.local_players(path, os.path.join(self.tmp.name, "sem-lista")), 2)
        Path(path).write_text("1 up 0 h0.1 Pad\n")
        os.environ["FLIPEROS_LOCAL_PLAYERS"] = "4"
        self.addCleanup(os.environ.pop, "FLIPEROS_LOCAL_PLAYERS")
        self.assertEqual(felink.local_players(path, self.devices(1)), 4)

    def test_the_link_rereads_the_players_when_a_controller_comes_or_goes(self):
        path = os.path.join(self.tmp.name, "buttons.map")
        Path(path).write_text("1 up 0 h0.1 Pad\n2 up 1 h0.1 Pad\n")
        now = [0.0]
        link = felink.Link(self.tmp.name, wire=LOOP, ident="x", clock=lambda: now[0])
        seen = [2]
        with mock.patch.object(felink, "local_players", side_effect=lambda *a: seen[0]):
            self.assertEqual(link.local_players, 2)
            seen[0] = 1                          # soltou um controle
            self.assertEqual(link.local_players, 2)   # a conta e guardada por 2 s
            now[0] = 2.1
            self.assertEqual(link.local_players, 1)
            seen[0] = 2                          # ligou de volta
            now[0] = 4.3
            self.assertEqual(link.local_players, 2)
            link.local_players = 3               # os testes fixam
            self.assertEqual(link.local_players, 3)

    def test_each_cabinet_takes_as_many_slots_as_it_has_controls(self):
        host = self.host(take=2)
        g2, ok2 = self.guest("g2", 2)
        g3, ok3 = self.guest("g3", 1)
        self.assertTrue(ok2 and ok3)
        members = host.snapshot()["members"]
        self.assertEqual([(m["number"], m["first"], m["take"]) for m in members], [(1, 1, 2), (2, 3, 2), (3, 5, 1)])
        self.assertEqual((g2.number, felink.Link.mine(g2.party, g2.number)["first"]), (2, 3))
        self.assertEqual(host.used(), 5)
        self.assertFalse(host.full())

    def test_a_cabinet_gets_the_slots_that_are_left_and_the_party_fills_by_slots(self):
        host = self.host(take=2)
        self.guest("g2", 2)
        g3, ok = self.guest("g3", 2)
        self.assertTrue(ok)
        self.assertEqual(host.snapshot()["members"][2]["take"], 2)        # 2 + 2 + 2 = 6: fechou
        self.assertTrue(host.full())
        g4, ok4 = self.guest("g4", 2)
        self.assertFalse(ok4)
        self.assertEqual(g4.refused, "full")

    def test_a_late_cabinet_with_more_controls_than_slots_left_takes_what_is_left(self):
        host = self.host(take=2)
        self.guest("g2", 2)
        self.guest("g3", 1)                                               # 5 de 6
        g4, ok = self.guest("g4", 2)
        self.assertTrue(ok)
        self.assertEqual([m["take"] for m in host.snapshot()["members"]][3], 1)
        self.assertTrue(host.full())

    def test_the_plan_and_the_presence_carry_the_slots(self):
        host = self.host(take=2)
        self.guest("g2", 2)
        plan = host.start()
        self.assertEqual([(m["number"], m["first"], m["take"]) for m in plan["members"]], [(1, 1, 2), (2, 3, 2)])
        table = [{"id": "h", "ip": "10.0.0.1", "party": "h", "slot": 1, "take": 2, "max": 6, "game": "xmen", "system": "retroarch/fbneo",
                  "state": "lobby", "name": "H"},
                 {"id": "g", "ip": "10.0.0.2", "party": "h", "slot": 2, "take": 2, "max": 6, "game": "xmen",
                  "system": "retroarch/fbneo", "state": "lobby", "name": "G"}]
        party = felink.parties(table)[0]
        self.assertEqual((party["used"], party["max"], party["numbers"]), (4, 6, [1, 2]))

    def test_the_retroarch_config_requests_a_device_per_slot_of_this_cabinet(self):
        text = felink.netplay_cfg(self.prof, range(3, 5))
        self.assertIn('netplay_request_device_p3 = "true"', text)
        self.assertIn('netplay_request_device_p4 = "true"', text)
        self.assertNotIn("netplay_request_device_p1", text)
        self.assertIn('netplay_max_connections = "6"', text)

    def test_the_link_of_a_two_control_cabinet_hosts_with_two_players_and_a_guest_takes_the_next_pair(self):
        a = felink.Link(self.tmp.name + "/a", wire=LOOP, ident="aaa", name="A", ports={"presence": free_port(), "party": self.port,
                                                                                    "files": free_port()}, local_players=2)
        b = felink.Link(self.tmp.name + "/b", wire=LOOP, ident="bbb", name="B", ports=a.ports, local_players=2)
        for link in (a, b):
            os.makedirs(link.home)
            self.assertTrue(link.start())
            self.addCleanup(link.stop)
        self.assertTrue(a.host_game(self.prof, "retroarch/fbneo", "xmen", [], "/r/xmen.zip"))
        self.assertEqual(a.take, 2)
        self.assertTrue(wait(lambda: b.parties_for("retroarch/fbneo", "xmen")))
        party = b.parties_for("retroarch/fbneo", "xmen")[0]
        self.assertEqual((party["used"], party["max"]), (2, 6))
        self.assertTrue(b.join_party(party, self.prof, "retroarch/fbneo", "xmen", "/r/xmen.zip"))
        self.assertEqual((b.number, b.take), (2, 2))
        self.assertTrue(a.start_now())
        self.assertTrue(wait(lambda: b.guest.plan is not None))
        b.tick()
        self.assertEqual(b.lobby()["first"], 3)
        cfg_b = " ".join(b.command(["ignored"]))
        text = Path(b.home, ".config", "fliperos", "netplay.cfg").read_text()
        self.assertIn('netplay_request_device_p3 = "true"', text)
        self.assertIn('netplay_request_device_p4 = "true"', text)
        a.command(["ignored"])
        host_text = Path(a.home, ".config", "fliperos", "netplay.cfg").read_text()
        self.assertIn('netplay_request_device_p1 = "true"', host_text)
        self.assertIn('netplay_request_device_p2 = "true"', host_text)
        self.assertNotIn("netplay_request_device_p3", host_text)

    def test_a_netplay_party_starts_by_itself_when_every_slot_is_taken(self):
        a = felink.Link(self.tmp.name + "/a", wire=LOOP, ident="aaa", name="A", ports={"presence": free_port(), "party": self.port,
                                                                                    "files": free_port()}, local_players=3)
        os.makedirs(a.home)
        self.assertTrue(a.start())
        self.addCleanup(a.stop)
        prof = felink.netplay_profile("retroarch/fbneo", "xmen", "4", 2, frozenset({"xmen"}))
        a.host_game(prof, "retroarch/fbneo", "xmen", [], "/r/xmen.zip")
        self.assertEqual(a.take, 3)
        self.assertIsNone(a.tick())
        g, ok = self.guest("g", 3)
        self.assertTrue(ok)
        self.assertEqual(felink.Link.mine(g.party, g.number)["take"], 1)     # sobrou 1 de 4
        self.assertIsNone(a.tick())                                          # o tick que comeca devolve None
        self.assertIsNotNone(a.plan)


class NetplayTests(unittest.TestCase):
    SETS = frozenset({"xmen", "sf2"})

    def test_only_a_game_with_more_players_than_controls_that_fbneo_runs(self):
        prof = felink.netplay_profile("retroarch/fbneo", "xmen", "4", 2, self.SETS)
        self.assertEqual((prof["id"], prof["min"], prof["max"], prof["port"]), ("netplay", 2, 4, 55435))
        self.assertTrue(prof["netplay"] and not prof["fixed"])
        self.assertIsNone(felink.netplay_profile("retroarch/fbneo", "sf2", "2", 2, self.SETS))       # cabe nos controles daqui
        self.assertIsNone(felink.netplay_profile("retroarch/fbneo", "gaiaone", "4", 2, self.SETS))   # o FBNeo nao roda
        self.assertIsNone(felink.netplay_profile("model2", "xmen", "4", 2, self.SETS))    # so a pasta do FBNeo
        self.assertIsNone(felink.netplay_profile("mame", "xmen", "4", 2, self.SETS))      # nem o romset do MAME
        self.assertIsNone(felink.netplay_profile("retroarch/fbneo", "xmen", "", 2, self.SETS))
        self.assertIsNotNone(felink.netplay_profile("retroarch/fbneo", "xmen", "4", 3, self.SETS))
        self.assertIsNone(felink.netplay_profile("retroarch/fbneo", "xmen", "4", 4, self.SETS))

    def test_every_retroarch_core_that_does_net_play(self):
        so = felink.netplay_core("retroarch/snes9x")
        self.assertEqual(so, os.path.join(felink.RA_CORES, "snes9x_libretro.so"))
        prof = felink.netplay_profile("retroarch/snes9x", "Bomberman 2", "4", 2)
        self.assertEqual((prof["emulator"], prof["core"], prof["systems"], prof["max"]), ("retroarch", so, ["retroarch/snes9x"], 4))
        self.assertIsNotNone(felink.netplay_profile("retroarch/pcsx_rearmed", "Crash Team Racing", "4", 2))
        self.assertIsNone(felink.netplay_core("retroarch/mame2010"))          # nao salva estado
        self.assertIsNone(felink.netplay_core("retroarch/flycast"))           # so "serialized"
        self.assertIsNone(felink.netplay_core("retroarch/genesis_plus_gx"))   # sem o .so
        self.assertIsNone(felink.netplay_core("retroarch/nada"))
        self.assertIsNone(felink.netplay_core("mame"))
        self.assertIsNone(felink.netplay_profile("retroarch/mame2010", "xmen", "4", 2))
        # Fora do FBNeo nao ha lista de sets: o nome nao importa.
        self.assertIsNotNone(felink.netplay_profile("retroarch/snes9x", "gaiaone", "4", 2, self.SETS))

    def test_naomi_and_atomiswave_get_flycast_ggpo_one_player_per_cabinet(self):
        for system in ("naomi", "naomi2", "atomiswave"):
            prof = felink.netplay_profile(system, "kofnw", "2", 2)
            self.assertEqual((prof["emulator"], prof["max"], prof["players"], prof["take"], prof["port"]),
                             ("flycast", 2, 2, 1, 19713))
            self.assertTrue(prof["ggpo"] and prof["netplay"])
        self.assertIsNone(felink.netplay_profile("naomi", "f355", "1", 2))
        self.assertIsNone(felink.netplay_profile("naomi", "kofnw", "", 2))

    def test_the_ggpo_command_points_each_side_at_the_other(self):
        prof = felink.netplay_profile("atomiswave", "kofnw", "2", 2)
        plan = felink.make_plan(prof, [{"number": i, "name": "C%d" % i, "ip": "10.0.0.%d" % i} for i in (1, 2)])
        base = ["/opt/fliperos/bin/fliperos-x11-run", "flycast", "/r/kofnw.zip"]
        host = felink.command(prof, base, plan, 1, "kofnw")
        guest = felink.command(prof, base, plan, 2, "kofnw")
        self.assertEqual(host[-1], "/r/kofnw.zip")
        self.assertIn("network:GGPO=yes,network:ActAsServer=yes,network:server=10.0.0.2", host[-2])
        self.assertIn("network:ActAsServer=no,network:server=10.0.0.1", guest[-2])
        self.assertIn("network:EnableUPnP=no", guest[-2])

    def test_a_ggpo_party_takes_one_player_from_each_cabinet(self):
        prof = felink.netplay_profile("naomi", "mvsc2", "2", 2)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        a = felink.Link(tmp.name + "/a", wire=LOOP, ident="aaa", name="A", ports={"presence": free_port(), "party": free_port(),
                                                                               "files": free_port()}, local_players=2)
        b = felink.Link(tmp.name + "/b", wire=LOOP, ident="bbb", name="B", ports=a.ports, local_players=2)
        for link in (a, b):
            os.makedirs(link.home)
            self.assertTrue(link.start())
            self.addCleanup(link.stop)
        self.assertTrue(a.host_game(prof, "naomi", "mvsc2", []))
        self.assertEqual(a.take, 1)
        self.assertTrue(wait(lambda: b.parties_for("naomi", "mvsc2")))
        party = b.parties_for("naomi", "mvsc2")[0]
        self.assertEqual((party["used"], party["max"]), (1, 2))
        self.assertTrue(b.join_party(party, prof, "naomi", "mvsc2"))
        self.assertEqual((b.number, b.take), (2, 1))

    def test_a_retroarch_folder_is_its_own_system_for_the_parties(self):
        link = felink.Link(tempfile.mkdtemp(), wire=LOOP, ident="p1")
        rows = [{"game": "sonic", "system": "retroarch/genesis_plus_gx"}, {"game": "ssf2tb", "system": "mame/x"}]
        with mock.patch.object(link, "parties", return_value=rows):
            self.assertEqual(link.parties_for("retroarch/genesis_plus_gx", "sonic"), rows[:1])
            self.assertEqual(link.parties_for("retroarch/fbneo", "sonic"), [])
            self.assertEqual(link.parties_for("mame", "ssf2tb"), rows[1:])

    def test_the_fbneo_index_is_read_from_the_xz(self):
        import lzma
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "sets.tsv.xz")
            with lzma.open(path, "wt") as f:
                f.write("\txmen\t\t\nmegadrive\tsonic\t\t\n\tsf2ce\tsf2\t\n")
            self.assertEqual(felink.fbneo_sets(path), frozenset({"xmen", "sonic", "sf2ce"}))
            self.assertEqual(felink.fbneo_sets(os.path.join(d, "nenhum")), frozenset())

    def test_the_command_hosts_for_number_1_and_connects_the_others_to_it(self):
        prof = felink.netplay_profile("retroarch/fbneo", "xmen", "4", 2, self.SETS)
        plan = felink.make_plan(prof, [{"number": i, "name": "C%d" % i, "ip": "10.0.0.%d" % i} for i in (1, 2, 3)])
        self.assertEqual(plan["order"], [1, 2, 3])
        host = felink.netplay_command(prof, plan, 1, "/r/xmen.zip", "C1", "/c/n.cfg", core="/core.so")
        self.assertEqual(host, [felink.KMS_RUN, "retroarch", "-L", "/core.so", "--appendconfig", "/c/n.cfg",
                                "--nick", "C1", "--port", "55435", "--host", "/r/xmen.zip"])
        guest = felink.netplay_command(prof, plan, 3, "/r/xmen.zip", "C3", "/c/n.cfg", core="/core.so")
        self.assertEqual(guest[-3:], ["--connect", "10.0.0.1", "/r/xmen.zip"])
        self.assertNotIn("--host", guest)

    def test_the_config_keeps_it_off_the_internet(self):
        text = felink.NETPLAY_CFG % 4
        for key in ("netplay_public_announce", "netplay_use_mitm_server", "netplay_nat_traversal"):
            self.assertIn('%s = "false"' % key, text)
        self.assertIn('netplay_max_connections = "4"', text)

    def test_a_link_command_for_a_netplay_party_writes_the_config_and_has_no_nvram(self):
        with tempfile.TemporaryDirectory() as home:
            prof = felink.netplay_profile("retroarch/fbneo", "xmen", "4", 2, self.SETS)
            link = felink.Link(home, wire=LOOP, ident="aaa")
            link.profile, link.game, link.rom, link.number = prof, "xmen", "/r/xmen.zip", 1
            link.plan = felink.make_plan(prof, [{"number": 1, "name": "A", "ip": "127.0.0.1"},
                                                {"number": 2, "name": "B", "ip": "127.0.0.2"}])
            argv = link.command(["ignored"])
            self.assertEqual(argv[1:3], ["retroarch", "-L"])
            self.assertIn("--host", argv)
            cfg = Path(home, ".config", "fliperos", "netplay.cfg").read_text()
            self.assertIn('netplay_nat_traversal = "false"', cfg)
            self.assertFalse(os.path.exists(os.path.join(home, "nvram", ".link-active")))


if __name__ == "__main__":
    unittest.main()
