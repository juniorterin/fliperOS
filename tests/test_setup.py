"""Testes da logica do fliperos-setup (fliperos-setup/lib/*.sh).

Cada teste roda um trecho de bash com as bibliotecas carregadas e os
caminhos de sistema apontados para arvores falsas (sysfs do DRM, /etc,
/proc/cmdline). Rode no container do tests/Dockerfile: o mesmo Ubuntu da
ISO, com o mesmo mawk e jq.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "fliperos-setup"
LIBS = ["common", "config", "progress", "speech", "monitor", "drm", "video", "xorg",
        "bootloader", "disk", "install", "recovery", "launcher", "audio", "network",
        "status", "scraper", "romclean", "netshare", "downloader", "freeroms", "frontends", "update", "hardware", "latency", "quirks", "padkeys", "lpt", "buttons", "debug"]
LATENCY_BASE = "mitigations=off audit=0 usbhid.jspoll=1 usbhid.kbpoll=1 usbhid.mousepoll=1"
# Boot direto no Plymouth, sem texto (pedido no teste do gabinete).
BOOT_SILENT = "loglevel=3 rd.udev.log_level=3 udev.log_level=3 vt.global_cursor_default=0"


def edid(serial=None, name=None):
    """EDID de 128 bytes com descritores de texto como os do Switchres."""
    b = bytearray(128)
    b[0:8] = b"\x00\xff\xff\xff\xff\xff\xff\x00"

    def text(off, tag, value):
        b[off:off + 5] = bytes([0, 0, 0, tag, 0])
        raw = value.encode()[:13]
        if len(raw) < 13:
            raw += b"\n" + b" " * (12 - len(raw))
        b[off + 5:off + 18] = raw

    if serial:
        text(72, 0xFF, serial)
    if name:
        text(108, 0xFC, name)
    return bytes(b)


class Env:
    """Sistema falso num diretorio temporario."""

    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix="fliperos-test-"))
        self.drm = self.dir / "drm"
        self.etc = self.dir / "etc"
        self.bin = self.dir / "bin"
        for d in (self.drm, self.etc, self.bin):
            d.mkdir(parents=True)
        self.cmdline = self.dir / "cmdline"
        self.cmdline.write_text("boot=live quiet splash\n")
        self.writes = self.dir / "writes"
        self.writes.write_text("")
        # Como o lspci -mm de verdade: o slot sem aspas e o fabricante da
        # placa no fim (no gabinete, "Advanced Micro Devices" de novo).
        self.stub("lspci", 'echo \'01:00.0 "VGA compatible controller" '
                           '"Advanced Micro Devices, Inc. [AMD/ATI]" '
                           '"Cedar [Radeon HD 5000/6000/7350/8350 Series]" -r87 '
                           '"Advanced Micro Devices, Inc. [AMD/ATI]" "Device 0b0c"\'')
        self.cards = 0

    def stub(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/bash\n" + body + "\n")
        path.chmod(0o755)

    def card(self, card, driver):
        dev = self.dir / "pci" / ("0000:0%d:00.0" % self.cards)
        self.cards += 1
        drv = self.dir / "drivers" / driver
        dev.mkdir(parents=True)
        drv.mkdir(parents=True, exist_ok=True)
        (dev / "driver").symlink_to(drv)
        (dev / "graphics" / ("fb%d" % (self.cards - 1))).mkdir(parents=True)
        (self.drm / card).mkdir()
        (self.drm / card / "device").symlink_to(dev)

    def connector(self, name, status="disconnected", data=b"", modes=""):
        d = self.drm / name
        d.mkdir()
        (d / "status").write_text(status + "\n")
        (d / "edid").write_bytes(data)
        (d / "modes").write_text(modes)

    def run(self, script, env=None):
        prelude = "set -o pipefail\nshopt -s extglob\n"
        prelude += "".join("source %s/lib/%s.sh\n" % (SETUP, n) for n in LIBS)
        # O status do sysfs falso nao muda com a escrita: as escritas ficam
        # registradas para os testes conferirem.
        prelude += 'drm_set_status() { echo "$1=$2" >> "%s"; }\n' % self.writes
        prelude += "sleep() { :; }\n"
        e = dict(os.environ)
        e.update({
            "PATH": "%s:%s" % (self.bin, e.get("PATH", "/usr/bin:/bin")),
            "DRM_SYSFS": str(self.drm),
            "FLIPEROS_ETC": str(self.etc),
            "FLIPEROS_CONF": str(self.etc / "fliperos.conf"),
            "FLIPEROS_LOG": str(self.dir / "setup.log"),
            "PROC_CMDLINE": str(self.cmdline),
            "SWITCHRES_INI": str(self.etc / "switchres.ini"),
            "MAME_INI": str(self.etc / "mame.ini"),
            "XORG_CONF": str(self.etc / "xorg.conf"),
            "BOOT_DEFAULTS": str(self.etc / "fliperos-boot"),
            "SESSIONS_TABLE": str(self.etc / "sessions.conf"),
            "SESSION_FILE": str(self.etc / "session"),
            "DRM_MODULE_PARAMS": str(self.dir / "drmparams"),
            "FBCON_SYSFS": str(self.dir / "fbcon"),
            "RETROARCH_CFG": str(self.etc / "retroarch.cfg"),
            "PROC_CPUINFO": str(self.dir / "cpuinfo"),
            "PROC_MEMINFO": str(self.dir / "meminfo"),
            "CPU_SYSFS": str(self.dir / "cpu"),
            "LATENCY_STATE": str(self.dir / "run" / "governor"),
            "FLIPEROS_NO_SPEECH": "1",
            "LC_ALL": "C.UTF-8",
        })
        e.update(env or {})
        return subprocess.run(["bash", "-c", prelude + textwrap.dedent(script)],
                              capture_output=True, text=True, env=e)

    def out(self, script, env=None):
        r = self.run(script, env)
        if r.returncode != 0:
            raise AssertionError("bash saiu com %d\nstdout:\n%s\nstderr:\n%s"
                                 % (r.returncode, r.stdout, r.stderr))
        return r.stdout

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.env = Env()

    def tearDown(self):
        self.env.close()


class ConfigTests(Base):
    def test_conf_set_replaces_and_appends(self):
        self.env.out("""
            conf_set monitor generic_15
            conf_set connector VGA-1
            conf_set monitor arcade_15
        """)
        text = (self.env.etc / "fliperos.conf").read_text()
        self.assertEqual(text, "monitor=arcade_15\nconnector=VGA-1\n")
        self.assertEqual(self.env.out("conf_get connector").strip(), "VGA-1")

    def test_conf_get_missing_key_fails(self):
        r = self.env.run("conf_get nada")
        self.assertNotEqual(r.returncode, 0)

    def test_ini_set_keeps_indentation_and_alignment(self):
        ini = self.env.etc / "switchres.ini"
        ini.write_text("# comentario\n\tmonitor                   arcade_15\n\tinterlace                 1\n")
        self.env.out('ini_set "$SWITCHRES_INI" monitor custom; ini_set "$SWITCHRES_INI" crt_range0 "15625-15750, 49.50-65.00"')
        self.assertEqual(ini.read_text(),
                         "# comentario\n\tmonitor                   custom\n\tinterlace                 1\n"
                         "crt_range0                15625-15750, 49.50-65.00\n")
        self.assertEqual(self.env.out('ini_get "$SWITCHRES_INI" monitor').strip(), "custom")

    def test_ini_set_does_not_touch_longer_keys(self):
        ini = self.env.etc / "mame.ini"
        ini.write_text("monitor_aspect 4:3\nmonitor arcade_15\n")
        self.env.out('ini_set "$MAME_INI" monitor lcd')
        self.assertEqual(ini.read_text(), "monitor_aspect 4:3\nmonitor lcd\n")


class CmdlineTests(Base):
    def test_set_and_remove(self):
        self.assertEqual(self.env.out('cmdline_set "a b=1 c b=2" b 3').strip(), "a b=3 c")
        self.assertEqual(self.env.out('cmdline_set "a" fbcon rotate:1').strip(), "a fbcon=rotate:1")
        self.assertEqual(self.env.out('cmdline_remove "a b=1 c" b').strip(), "a c")

    def test_without_video_removes_modes_and_edid(self):
        line = "quiet video=640x480iS video=VGA-1:e drm.edid_firmware=VGA-1:edid/x.bin splash"
        self.assertEqual(self.env.out('cmdline_without_video "%s"' % line).strip(), "quiet splash")
        self.assertEqual(self.env.out('cmdline_video_params "%s"' % line).strip(),
                         "video=640x480iS video=VGA-1:e drm.edid_firmware=VGA-1:edid/x.bin")

    def test_video_option_panel_orientation(self):
        out = self.env.out('cmdline_set_video_option "quiet video=VGA-1:640x480iSe" VGA-1 panel_orientation right_side_up')
        self.assertEqual(out.strip(), "quiet video=VGA-1:640x480iSe,panel_orientation=right_side_up")
        out = self.env.out('cmdline_remove_video_option "%s" VGA-1 panel_orientation' % out.strip())
        self.assertEqual(out.strip(), "quiet video=VGA-1:640x480iSe")

    def test_video_option_alone_is_removed_whole(self):
        out = self.env.out('cmdline_remove_video_option "quiet video=VGA-1:panel_orientation=left_side_up" VGA-1 panel_orientation')
        self.assertEqual(out.strip(), "quiet")


class MonitorTests(Base):
    def test_kernel_resolution_like_gatools(self):
        cases = {
            "generic_15 60 i": "640x480iS", "generic_15 60 p": "320x240S",
            "arcade_15 50 i": "768x576iS", "k7000 60 i super": "1280x480iS",
            "pal 60 i": "768x576iS", "ntsc 60 i": "720x480iS",
            "arcade_25 60 p": "512x384S", "arcade_25 60 i": "800x600iS",
            "ms929 60 i super": "800x600iS", "arcade_31 60 i": "640x480S",
            "vesa_600 60 p": "800x600", "vesa_1024 60 p": "1280x1024",
        }
        for args, want in cases.items():
            self.assertEqual(self.env.out("monitor_kernel_resolution %s" % args).strip(), want, args)

    def test_lcd_and_unknown(self):
        self.assertEqual(self.env.run("monitor_kernel_resolution lcd").returncode, 1)
        self.assertEqual(self.env.run("monitor_kernel_resolution nada").returncode, 2)

    def test_frequency(self):
        for m, f in (("generic_15", "15k"), ("pal", "15k"), ("arcade_15_25", "25k"),
                     ("d9800", "31k")):
            self.assertEqual(self.env.out("monitor_frequency %s" % m).strip(), f)
        self.assertNotEqual(self.env.run("monitor_frequency lcd").returncode, 0)

    def test_presets_match_switchres_list(self):
        ids = self.env.out('for e in "${MONITOR_PRESETS[@]}"; do echo "${e%%|*}"; done').split()
        self.assertEqual(len(ids), 29)
        self.assertEqual(ids[0], "generic_15")
        self.assertEqual(ids[-1], "lcd")
        self.assertEqual(len(set(ids)), 29)

    def test_resolutions_without_low_dotclock_are_super_only(self):
        full = self.env.out("monitor_resolutions 15k 1").splitlines()
        self.assertEqual(full[3], "640x480iS|640x480 60 Hz interlaced")
        self.assertEqual(len(full), 7)
        low = self.env.out("monitor_resolutions 15k 0").splitlines()
        self.assertEqual([l.split("|")[0] for l in low], ["1280x480iS"])

    def test_every_listed_mode_has_a_modeline(self):
        modes = self.env.out("monitor_resolutions 15k; monitor_resolutions 25k; monitor_resolutions 31k")
        for line in modes.splitlines():
            mode = line.split("|")[0]
            self.env.out("mode_modeline %s" % mode)

    def test_interlaced_modeline(self):
        line = self.env.out("mode_modeline 640x480iS").strip()
        self.assertTrue(line.startswith('"640x480i" 13.038 640 666 727 831 480 483 489 523'))
        self.assertIn("Interlace", line)

    def test_normalize_truncated_edid_name(self):
        self.assertEqual(self.env.out("monitor_normalize 'arcade_15_25_'").strip(), "arcade_15_25_31")


class DrmTests(Base):
    def test_connectors_sorted_without_writeback(self):
        self.env.card("card0", "radeon")
        for n in ("card0-VGA-1", "card0-DVI-I-1", "card0-HDMI-A-1", "card0-Writeback-1"):
            self.env.connector(n)
        self.assertEqual(self.env.out("drm_connectors").split(),
                         ["card0-DVI-I-1", "card0-HDMI-A-1", "card0-VGA-1"])

    def test_names_and_analog(self):
        self.assertEqual(self.env.out("drm_name card1-DVI-I-2").strip(), "DVI-I-2")
        self.assertEqual(self.env.out("drm_card card1-DVI-I-2").strip(), "card1")
        for name, analog in (("VGA-1", 0), ("DVI-I-1", 0), ("DVI-D-1", 1), ("HDMI-A-1", 1), ("DP-1", 1)):
            self.assertEqual(self.env.run("drm_is_analog %s" % name).returncode, analog, name)

    def test_driver_and_low_dotclock(self):
        self.env.card("card0", "amdgpu")
        self.env.card("card1", "i915")
        self.assertEqual(self.env.out("drm_card_driver card0").strip(), "amdgpu")
        self.assertEqual(self.env.run("drm_card_low_dotclock card0").returncode, 0)
        self.assertNotEqual(self.env.run("drm_card_low_dotclock card1").returncode, 0)
        self.assertEqual(self.env.out("drm_card_fb card1").strip(), "1")

    def test_gpu_short_names(self):
        self.assertEqual(self.env.out("gpu_short_name 'Advanced Micro Devices, Inc. [AMD/ATI]' "
                                      "'Oland [Radeon HD 8570 / R7 240/340]'").strip(),
                         "AMD Radeon HD 8570 / R7 240/340")
        self.assertEqual(self.env.out("gpu_short_name 'NVIDIA Corporation' 'GK104 [GeForce GTX 760]'").strip(),
                         "NVIDIA GeForce GTX 760")
        self.assertEqual(self.env.out("gpu_short_name 'Intel Corporation' 'HD Graphics 530'").strip(),
                         "Intel HD Graphics 530")

    def test_card_name_from_real_lspci_line(self):
        # No gabinete o nome saia "Oland PRO [...] Advanced Micro Devices,
        # Inc. [AMD/ATI]": os campos eram lidos deslocados em um.
        self.env.card("card0", "radeon")
        self.env.stub("lspci", 'echo \'01:00.0 "VGA compatible controller" "Advanced Micro Devices, Inc. [AMD/ATI]" '
                               '"Oland PRO [Radeon R7 240/340 / Radeon 520]" -r87 '
                               '"Advanced Micro Devices, Inc. [AMD/ATI]" "Device 0b0c"\'')
        self.assertEqual(self.env.out("drm_card_name card0").strip(), "AMD Radeon R7 240/340 / Radeon 520")

    def test_switchres_edid(self):
        path = self.env.dir / "sr.bin"
        path.write_bytes(edid("Switchres200", "generic_15"))
        self.assertEqual(self.env.run("edid_is_switchres %s" % path).returncode, 0)
        self.assertEqual(self.env.out("edid_monitor_name %s" % path).strip(), "generic_15")

    def test_factory_edid(self):
        path = self.env.dir / "lcd.bin"
        path.write_bytes(edid("A1B2C3", "DELL U2412M"))
        self.assertNotEqual(self.env.run("edid_is_switchres %s" % path).returncode, 0)
        self.assertEqual(self.env.out("edid_monitor_name %s" % path).strip(), "DELL U2412M")

    def test_empty_edid(self):
        path = self.env.dir / "none.bin"
        path.write_bytes(b"")
        self.assertNotEqual(self.env.run("edid_monitor_name %s" % path).returncode, 0)

    def test_interlace_from_modes(self):
        self.env.card("card0", "radeon")
        self.env.connector("card0-VGA-1", modes="640x480i\n640x480\n")
        self.env.connector("card0-DVI-D-1", modes="1024x768\n")
        self.assertEqual(self.env.run("drm_has_interlace card0-VGA-1").returncode, 0)
        self.assertNotEqual(self.env.run("drm_has_interlace card0-DVI-D-1").returncode, 0)


class OutputTestTests(Base):
    """Classificacao e parametros de video, como o gatools video.sh."""

    def setUp(self):
        super().setUp()
        self.env.card("card0", "radeon")
        self.env.card("card1", "i915")

    def begin(self, name, status, data=b""):
        self.env.connector(name, status, data)
        return self.env.run('video_test_begin %s; echo "rc=$? forced=$VT_FORCED"; video_classify %s' % (name, name))

    def test_disconnected_digital_is_skipped(self):
        r = self.begin("card0-HDMI-A-1", "disconnected")
        self.assertIn("rc=1", r.stdout)
        self.assertIn("card0-HDMI-A-1=off", self.env.writes.read_text())

    def test_disconnected_analog_is_forced_on(self):
        r = self.begin("card0-VGA-1", "disconnected")
        self.assertIn("rc=0 forced=1", r.stdout)
        self.assertEqual(r.stdout.splitlines()[-1], "se")
        self.assertIn("card0-VGA-1=on", self.env.writes.read_text())

    def test_connected_without_edid(self):
        r = self.begin("card0-VGA-1", "connected")
        self.assertEqual(r.stdout.splitlines()[-1], "sr")

    def test_switchres_edid_dongle(self):
        r = self.begin("card0-VGA-1", "connected", edid("Switchres200", "arcade_15"))
        self.assertEqual(r.stdout.splitlines()[-1], "so")

    def test_edid_forced_on_the_kernel_line(self):
        self.env.cmdline.write_text("boot=live drm.edid_firmware=edid/generic_15_super_resi.bin video=e\n")
        r = self.begin("card0-VGA-1", "connected", edid("Switchres200", "generic_15"))
        self.assertEqual(r.stdout.splitlines()[-1], "sdo")

    def test_lcd(self):
        r = self.begin("card0-DVI-D-1", "connected", edid("123", "LG FLATRON"))
        self.assertEqual(r.stdout.splitlines()[-1], "sl")

    def test_intel_has_no_low_dotclock(self):
        r = self.begin("card1-VGA-1", "disconnected")
        self.assertEqual(r.stdout.splitlines()[-1], "e")

    def test_apu_flag(self):
        self.env.stub("lspci", 'if [ "$1" = -vs ]; then echo "DeviceName: Onboard IGD"; fi')
        r = self.begin("card0-VGA-1", "connected")
        self.assertEqual(r.stdout.splitlines()[-1], "sra")

    def params(self, flags, monitor, conn="VGA-1"):
        return self.env.out("video_kernel_params %s %s %s" % (conn, flags, monitor)).strip()

    def test_kernel_params_like_configure_from_connector(self):
        self.assertEqual(self.params("se", "generic_15"), "video=VGA-1:640x480iSe")
        self.assertEqual(self.params("sr", "generic_15"), "video=VGA-1:640x480iS")
        self.assertEqual(self.params("sra", "arcade_15"), "video=VGA-1:640x480iS")
        self.assertEqual(self.params("r", "generic_15"), "video=VGA-1:1280x480iS")
        self.assertEqual(self.params("e", "arcade_25"), "video=VGA-1:800x600iSe")
        self.assertEqual(self.params("se", "ntsc"), "video=VGA-1:720x480iSe")
        self.assertEqual(self.params("se", "pal"), "video=VGA-1:768x576iSe")
        self.assertEqual(self.params("sr", "arcade_31"), "video=VGA-1:640x480S")

    def test_lcd_and_switchres_edid_need_no_params(self):
        self.assertEqual(self.params("sl", "lcd"), "")
        self.assertEqual(self.params("se", "lcd"), "")
        self.assertEqual(self.params("so", "arcade_15"), "")

    def test_edid_boot_keeps_the_boot_edid_on_the_connector(self):
        params = self.env.dir / "drmparams"
        params.mkdir()
        (params / "edid_firmware").write_text("edid/generic_15_super_resi.bin\n")
        self.assertEqual(self.params("sdo", "generic_15"),
                         "video=VGA-1:e drm.edid_firmware=VGA-1:edid/generic_15_super_resi.bin")

    def test_edid_boot_entry_uses_the_preset_edid(self):
        self.env.cmdline.write_text("boot=live drm.edid_firmware=edid/generic_15_super_resp.bin video=e\n")
        self.assertEqual(self.params("se", "arcade_15"),
                         "video=VGA-1:e drm.edid_firmware=VGA-1:edid/arcade_15.bin")

    def test_needs_monitor_choice(self):
        # Status 0 = a pessoa escolhe o monitor; so o EDID do Switchres
        # (dongle, sem EDID forcado no boot) dispensa a escolha.
        for flags, rc in (("so", 1), ("o", 1), ("soa", 1), ("sdo", 0), ("sl", 0), ("sr", 0), ("e", 0)):
            self.assertEqual(self.env.run("video_needs_monitor_choice %s" % flags).returncode, rc, flags)

    def test_save_result_writes_everything(self):
        self.env.connector("card0-VGA-1", "disconnected")
        (self.env.etc / "switchres.ini").write_text("\tmonitor                   arcade_15\n")
        (self.env.etc / "mame.ini").write_text("monitor arcade_15\n")
        self.env.out("video_save_result card0-VGA-1 se generic_15")
        conf = (self.env.etc / "fliperos.conf").read_text()
        for line in ("connector=VGA-1", "detection=se", "forced=1", "kernel_video=video=VGA-1:640x480iSe",
                     "boot_resolution=640x480iS", "monitor=generic_15", "frequency=15k", "driver=radeon",
                     "card=card0", "fb_map=0"):
            self.assertIn(line + "\n", conf)
        self.assertIn("monitor                   generic_15", (self.env.etc / "switchres.ini").read_text())
        self.assertIn("monitor generic_15", (self.env.etc / "mame.ini").read_text())
        # CRT: 4:3. Com "auto" o GroovyMAME tirava o formato do modo de boot
        # (640x240 = 8:3) e dobrava a largura de todo jogo.
        self.assertRegex((self.env.etc / "mame.ini").read_text(), r"(?m)^aspect +4:3$")

    def test_mame_aspect_is_auto_only_on_lcd(self):
        (self.env.etc / "mame.ini").write_text("monitor lcd\naspect 4:3\n")
        (self.env.etc / "switchres.ini").write_text("\tmonitor                   lcd\n")
        self.env.out("video_apply_monitor lcd")
        self.assertRegex((self.env.etc / "mame.ini").read_text(), r"(?m)^aspect +auto$")
        self.env.out("video_apply_monitor arcade_15")
        self.assertRegex((self.env.etc / "mame.ini").read_text(), r"(?m)^aspect +4:3$")
        self.assertIn("\naspect 4:3\n", (ROOT / "config/mame.ini").read_text())

    def test_mame_monitor_follows_the_setup(self):
        # Um mame.ini refeito volta ao arcade_15 de fabrica; a atualizacao o
        # poe de novo no monitor do Setup (no gabinete, generic_15).
        mame = self.env.etc / "mame.ini"
        mame.write_text("monitor                   arcade_15\n")
        self.env.out("video_mame_monitor")
        self.assertIn("arcade_15", mame.read_text())
        self.env.out("conf_set monitor generic_15; video_mame_monitor")
        self.assertRegex(mame.read_text(), r"(?m)^monitor +generic_15$")
        self.assertIn("  video_mame_monitor\n", (ROOT / "tools/cabinet-update.sh").read_text())

    def test_save_result_without_low_dotclock_sets_dotclock_min(self):
        self.env.connector("card1-VGA-1", "disconnected")
        self.env.out("video_save_result card1-VGA-1 e generic_15")
        self.assertIn("dotclock_min", (self.env.etc / "switchres.ini").read_text())
        conf = (self.env.etc / "fliperos.conf").read_text()
        self.assertIn("kernel_video=video=VGA-1:1280x480iSe\n", conf)
        self.assertIn("fb_map=1\n", conf)

    def test_boot_resolution_from_params(self):
        self.assertEqual(self.env.out("video_boot_resolution 'video=VGA-1:640x480iSe,panel_orientation=x'").strip(),
                         "640x480iS")
        self.assertNotEqual(self.env.run("video_boot_resolution 'video=VGA-1:e drm.edid_firmware=VGA-1:x'").returncode, 0)

    def test_suggested_monitor_from_boot_entry(self):
        for entry, monitor in (("15khz", "generic_15"), ("25khz", "arcade_25"), ("31khz", "arcade_31"),
                               ("ntsc", "ntsc"), ("pal", "pal"), ("svga", "lcd"), ("intel", "generic_15")):
            self.env.cmdline.write_text("boot=live fliperos.boot=%s\n" % entry)
            self.assertEqual(self.env.out("video_suggested_monitor").strip(), monitor, entry)

    def test_speech_spells_connectors(self):
        self.assertEqual(self.env.out("speech_connector VGA-1").strip(), "V G A 1")
        self.assertEqual(self.env.out("speech_connector DP-2").strip(), "Display Port 2")


class ResolutionTests(Base):
    def setUp(self):
        super().setUp()
        self.env.card("card0", "radeon")
        (self.env.etc / "fliperos.conf").write_text(
            "connector=VGA-1\ncard=card0\nmonitor=generic_15\nforced=1\ndetection=se\n"
            "kernel_video=video=VGA-1:640x480iSe\nboot_resolution=640x480iS\n")

    def test_set_resolution_keeps_forced_flag(self):
        self.env.out("video_set_resolution 720x480iS")
        conf = (self.env.etc / "fliperos.conf").read_text()
        self.assertIn("kernel_video=video=VGA-1:720x480iSe\n", conf)
        self.assertIn("boot_resolution=720x480iS\n", conf)

    def test_choices_follow_the_card(self):
        self.assertEqual(len(self.env.out("video_resolution_choices").splitlines()), 7)
        self.env.card("card1", "nouveau")
        self.env.out("conf_set card card1")
        self.assertEqual(self.env.out("video_resolution_choices").split("|")[0], "1280x480iS")

    def test_custom_edid(self):
        self.env.out("video_set_custom_edid custom_resolution.bin")
        conf = (self.env.etc / "fliperos.conf").read_text()
        self.assertIn("kernel_video=video=VGA-1:e drm.edid_firmware=VGA-1:edid/custom_resolution.bin\n", conf)

    def test_reconfigure_monitor_recomputes_params(self):
        self.env.out("video_reconfigure_monitor ntsc")
        conf = (self.env.etc / "fliperos.conf").read_text()
        self.assertIn("kernel_video=video=VGA-1:720x480iSe\n", conf)
        self.assertIn("monitor=ntsc\n", conf)


class OrientationTests(Base):
    def test_cmdline_rotation(self):
        out = self.env.out("orientation_cmdline 'quiet video=VGA-1:640x480iSe' VGA-1 vertical-cw").strip()
        self.assertEqual(out, "quiet video=VGA-1:640x480iSe,panel_orientation=right_side_up fbcon=rotate:1")
        out = self.env.out("orientation_cmdline '%s' VGA-1 vertical-ccw" % out).strip()
        self.assertEqual(out, "quiet video=VGA-1:640x480iSe,panel_orientation=left_side_up fbcon=rotate:3")
        out = self.env.out("orientation_cmdline '%s' VGA-1 horizontal" % out).strip()
        self.assertEqual(out, "quiet video=VGA-1:640x480iSe")

    def test_rotation_keeps_fbcon_map(self):
        out = self.env.out("orientation_cmdline 'quiet fbcon=map:1 fbcon=rotate:1' VGA-1 horizontal").strip()
        self.assertEqual(out, "quiet fbcon=map:1")

    def test_mame_rotation(self):
        mame = self.env.etc / "mame.ini"
        mame.write_text("ror 0\nrol 0\n")
        (self.env.dir / "fbcon").mkdir()
        self.env.out("orientation_apply vertical-ccw")
        self.assertIn("rol 1", mame.read_text())
        self.assertIn("ror 0", mame.read_text())
        self.assertEqual((self.env.dir / "fbcon" / "rotate_all").read_text(), "3")


class BootTests(Base):
    def test_install_cmdline_from_the_output_test(self):
        (self.env.etc / "fliperos.conf").write_text(
            "connector=VGA-1\nkernel_video=video=VGA-1:640x480iSe\norientation=vertical-cw\nfb_map=0\n")
        self.env.cmdline.write_text("boot=live fliperos.boot=15khz video=640x480iS quiet splash\n")
        out = self.env.out("boot_install_cmdline").strip()
        self.assertEqual(out, "quiet splash " + BOOT_SILENT + " consoleblank=0 radeon.si_support=1 radeon.cik_support=1 "
                              "amdgpu.si_support=0 amdgpu.cik_support=0 " + LATENCY_BASE + " "
                              "video=VGA-1:640x480iSe,panel_orientation=right_side_up fbcon=rotate:1")

    def test_install_cmdline_without_test_keeps_the_boot_entry(self):
        self.env.cmdline.write_text("boot=live fliperos.boot=intel video=1280x480iS i915.no_ytiled_scanout=1\n")
        out = self.env.out("boot_install_cmdline").strip()
        self.assertIn("i915.no_ytiled_scanout=1 video=1280x480iS", out)
        self.assertTrue(out.endswith(LATENCY_BASE), out)
        self.assertNotIn("boot=live", out)
        self.assertNotIn("fliperos.boot", out)

    def test_secondary_card_maps_the_console(self):
        (self.env.etc / "fliperos.conf").write_text("connector=VGA-1\nkernel_video=video=VGA-1:640x480iSe\nfb_map=1\n")
        out = self.env.out("boot_compose 'quiet fbcon=map:0 video=640x480iS'").strip()
        # Fora do modo debug o boot calado sempre volta (lib/debug.sh).
        self.assertEqual(out, "quiet splash " + BOOT_SILENT + " " + LATENCY_BASE
                         + " video=VGA-1:640x480iSe fbcon=map:1")

    def test_write_cmdline_keeps_the_rest(self):
        f = self.env.etc / "fliperos-boot"
        f.write_text('# x\nFLIPEROS_CMDLINE="old"\nFLIPEROS_TIMEOUT="3"\n')
        self.env.out('boot_write_cmdline "quiet video=VGA-1:e"')
        self.assertEqual(f.read_text(), '# x\nFLIPEROS_CMDLINE="quiet video=VGA-1:e"\nFLIPEROS_TIMEOUT="3"\n')
        self.assertEqual(self.env.out("boot_read_cmdline").strip(), "quiet video=VGA-1:e")

    def test_write_cmdline_creates_the_file(self):
        self.env.out('boot_write_cmdline "quiet"')
        text = (self.env.etc / "fliperos-boot").read_text()
        self.assertIn('FLIPEROS_CMDLINE="quiet"\n', text)
        self.assertIn('FLIPEROS_TIMEOUT="3"\n', text)


class XorgTests(Base):
    def test_crt_mode(self):
        (self.env.etc / "fliperos.conf").write_text(
            "connector=VGA-1\nmonitor=generic_15\nboot_resolution=640x480iS\n")
        self.env.out("xorg_generate")
        text = (self.env.etc / "xorg.conf").read_text()
        self.assertIn('Option "Monitor-VGA-1" "CRT"', text)
        self.assertIn('Modeline "640x480i" 13.038', text)
        self.assertIn('Option "PreferredMode" "640x480i"', text)
        self.assertIn("HorizSync 15.0 - 16.5", text)
        self.assertIn('Option "BlankTime" "0"', text)

    def test_lcd_only_disables_blanking(self):
        (self.env.etc / "fliperos.conf").write_text("connector=VGA-1\nmonitor=lcd\n")
        self.env.out("xorg_generate")
        text = (self.env.etc / "xorg.conf").read_text()
        self.assertNotIn("Modeline", text)
        self.assertIn('Option "BlankTime" "0"', text)


class DiskTests(Base):
    def inventory(self, devices):
        path = self.env.dir / "lsblk.json"
        path.write_text(json.dumps({"blockdevices": devices}))
        return {"DISK_INVENTORY_JSON": str(path), "LIVE_MEDIUM": str(self.env.dir / "nomedium"),
                "SYS_BLOCK": str(self.env.dir / "sysblock")}

    def dev(self, path, size, **kw):
        d = {"path": path, "type": "disk", "size": size, "model": kw.get("model"), "vendor": kw.get("vendor"),
             "serial": kw.get("serial", "S1"), "tran": kw.get("tran", "sata"), "rm": kw.get("rm", False),
             "hotplug": kw.get("hotplug", False), "ro": kw.get("ro", False), "mountpoints": kw.get("mnt", [None]),
             "label": None}
        if "children" in kw:
            d["children"] = kw["children"]
        return d

    def test_list_and_reasons(self):
        big = 500 * 10**9
        env = self.inventory([
            self.dev("/dev/sda", big, model="Samsung SSD 870 EVO"),
            self.dev("/dev/sdb", 32 * 10**9, model="SanDisk", tran="usb", rm=True,
                     children=[{"path": "/dev/sdb1", "type": "part", "size": 1, "mountpoints": ["/run/live/medium"]}]),
            self.dev("/dev/sdc", 8 * 10**9, model="Tiny"),
            self.dev("/dev/nvme0n1", 10**12, model="Kingston NV2", tran="nvme",
                     children=[{"path": "/dev/nvme0n1p1", "type": "part", "size": 1, "mountpoints": [None],
                                "children": [{"path": "/dev/mapper/x", "type": "crypt", "size": 1, "mountpoints": [None]}]}]),
            self.dev("/dev/loop0", big),
        ])
        rows = [r.split("|") for r in self.env.out("disk_list", env).splitlines()]
        by = {r[0]: r for r in rows}
        self.assertEqual(sorted(by), ["/dev/nvme0n1", "/dev/sda", "/dev/sdb", "/dev/sdc"])
        self.assertEqual(by["/dev/sda"][1:], ["Samsung SSD 870 EVO", str(big), "sata", "0", ""])
        self.assertEqual(by["/dev/sdb"][4:], ["1", "In use (mounted or swap)"])
        self.assertEqual(by["/dev/sdc"][5], "Smaller than 16 GiB")
        self.assertEqual(by["/dev/nvme0n1"][5], "Has RAID/LVM/encryption")

    def test_virtio_and_floppy(self):
        # Como o QEMU mostra: virtio sem modelo, fabricante "0x1af4", e o fd0.
        env = self.inventory([
            self.dev("/dev/fd0", 4096, tran=None),
            self.dev("/dev/vda", 21 * 10**9, vendor="0x1af4", tran=None),
        ])
        rows = [r.split("|") for r in self.env.out("disk_list", env).splitlines()]
        self.assertEqual([r[:2] for r in rows], [["/dev/vda", "Virtual disk"]])

    def test_describe(self):
        env = self.inventory([self.dev("/dev/sda", 500 * 10**9, vendor="ATA", model="Samsung SSD", tran="usb")])
        self.assertEqual(self.env.out("disk_describe /dev/sda", env).strip(),
                         "Samsung SSD (/dev/sda, 500 GB, USB)")

    def test_partition_paths_and_layout(self):
        self.assertEqual(self.env.out("disk_partition_path /dev/nvme0n1 2").strip(), "/dev/nvme0n1p2")
        self.assertEqual(self.env.out("disk_partition_path /dev/sda 3").strip(), "/dev/sda3")
        cmds = self.env.out("disk_partition_commands /dev/sda").splitlines()
        self.assertEqual(cmds[0], "wipefs --all /dev/sda")
        self.assertIn("mkpart BIOS 1MiB 2MiB set 1 bios_grub on", cmds[1])
        self.assertIn("mkpart EFI fat32 2MiB 1026MiB set 2 esp on", cmds[1])
        self.assertEqual(cmds[-2], "mkfs.vfat -F32 -n FLIPERBOOT /dev/sda2")
        self.assertEqual(cmds[-1], "mkfs.ext4 -F -L FliperOS /dev/sda3")
        # Restos do disco antigo nas particoes novas: o Limine recusava a de
        # BIOS boot ("contains a recognised filesystem").
        self.assertIn("wipefs --all /dev/sda1 /dev/sda2 /dev/sda3", cmds)
        self.assertIn("dd if=/dev/zero of=/dev/sda1 bs=1M count=1 conv=fsync status=none", cmds)
        nvme = self.env.out("disk_partition_commands /dev/nvme0n1")
        self.assertIn("wipefs --all /dev/nvme0n1p1 /dev/nvme0n1p2 /dev/nvme0n1p3", nvme)

    def test_human_size(self):
        self.assertEqual(self.env.out("human_size 500107862016").strip(), "500 GB")
        self.assertEqual(self.env.out("human_size 1000204886016").strip(), "1.0 TB")


class InstallEventsTests(Base):
    def test_copy_progress_maps_to_8_80(self):
        self.env.stub("unsquashfs", "printf '0\\n50\\n100\\n'")
        out = self.env.out("install_copy_system", {"LIVE_IMAGE": "/x", "INSTALL_TARGET": "/y"})
        self.assertEqual(out.split(), ["@pct", "8", "@pct", "44", "@pct", "80"])

    def test_copy_failure_reports_the_last_line(self):
        self.env.stub("unsquashfs", "echo 'write failed: no space'; exit 1")
        r = self.env.run("install_copy_system", {"LIVE_IMAGE": "/x", "INSTALL_TARGET": "/y"})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("@fail |Copying the system failed: write failed: no space", r.stdout)

    def test_preflight_refuses_outside_the_live_media(self):
        self.env.cmdline.write_text("quiet\n")
        r = self.env.run("EUID=0; install_preflight")
        self.assertNotEqual(r.returncode, 0)


class RecoveryTests(Base):
    def target_conf(self, target):
        path = Path(str(target) + str(self.env.etc / "fliperos.conf"))
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def test_new_video_card_keeps_the_rest_of_the_disk_settings(self):
        # Sessao da midia com a placa nova (teste de saidas feito agora).
        (self.env.etc / "fliperos.conf").write_text(
            "output_test=done\ncard=card1\ngpu=AMD Radeon R7 240\ndriver=radeon\nconnector=DVI-I-1\n"
            "kernel_video=video=DVI-I-1:640x480iSe\nboot_resolution=640x480iS\nmonitor=arcade_15\nfrequency=15\n")
        target = self.env.dir / "target"
        conf = self.target_conf(target)
        conf.write_text("latency=low\nalsa=1,0\nvolume=60\nlauncher=retroarch\norientation=vertical-cw\n"
                        "card=card0\nconnector=VGA-1\nkernel_video=video=VGA-1:640x480iSe\nmonitor=generic_15\n"
                        "geometry=15625.0-15750.0,49.5-65.0\n")
        self.env.out("install_configure_video '%s' video" % target)
        text = conf.read_text()
        for line in ("connector=DVI-I-1", "card=card1", "kernel_video=video=DVI-I-1:640x480iSe",
                     "monitor=arcade_15", "latency=low", "alsa=1,0", "volume=60", "launcher=retroarch",
                     "orientation=vertical-cw"):
            self.assertIn(line + "\n", text)
        # Geometria e da saida antiga; o que so a midia tem nao vai.
        self.assertNotIn("geometry=", text)
        self.assertNotIn("output_test", text)
        boot = Path(str(target) + str(self.env.etc / "fliperos-boot")).read_text()
        self.assertIn("preempt=full", boot)
        self.assertIn("video=DVI-I-1:640x480iSe", boot)
        self.assertIn("fbcon=rotate:1", boot)

    def test_new_install_copies_the_whole_session(self):
        (self.env.etc / "fliperos.conf").write_text("connector=VGA-1\nalsa=1,0\n")
        target = self.env.dir / "target"
        conf = self.target_conf(target)
        self.env.out("install_configure_video '%s'" % target)
        self.assertEqual(conf.read_text(), "connector=VGA-1\nalsa=1,0\n")

    def test_dpkg_keeps_packages_installed_later(self):
        old = self.env.dir / "old-status"
        new = self.env.dir / "status"
        old.write_text(
            "Package: bash\nStatus: install ok installed\nArchitecture: amd64\nVersion: 5.2-3\n\n"
            "Package: attractplus\nStatus: install ok installed\nArchitecture: amd64\nVersion: 3.0\n"
            "Description: frontend\n a longer description line\n\n"
            "Package: libc6\nStatus: install ok installed\nArchitecture: i386\nVersion: 2.39\n\n"
            "Package: libsfml\nStatus: install ok installed\nArchitecture: amd64\nVersion: 2.6\n")
        new.write_text(
            "Package: bash\nStatus: install ok installed\nArchitecture: amd64\nVersion: 5.2-2\n\n"
            "Package: libc6\nStatus: install ok installed\nArchitecture: amd64\nVersion: 2.39\n\n")
        self.env.out("recovery_dpkg_merge '%s' '%s'" % (old, new))
        text = new.read_text()
        packages = [(l.split(": ")[1]) for l in text.splitlines() if l.startswith("Package: ")]
        self.assertEqual(packages, ["bash", "libc6", "attractplus", "libc6", "libsfml"])
        # O bash fica o da midia, e a descricao de varias linhas vem inteira.
        self.assertIn("Version: 5.2-2\n", text)
        self.assertNotIn("Version: 5.2-3", text)
        self.assertIn(" a longer description line\n", text)
        # Rodar de novo nao duplica nada.
        self.env.out("recovery_dpkg_merge '%s' '%s'" % (old, new))
        self.assertEqual(new.read_text(), text)


class NetworkTests(Base):
    def test_parse_scan(self):
        scan = "Casa:80:WPA2\\nCasa:40:WPA2\\nCafe\\\\:Bar:55:WPA1 WPA2\\n:30:WPA2\\nAberta:20:\\n"
        out = self.env.out("printf '%s' | net_parse_scan" % scan).splitlines()
        self.assertEqual(out, ["Casa|80|WPA2", "Cafe:Bar|55|WPA1 WPA2", "Aberta|20|"])

    def test_ips(self):
        self.env.stub("ip", "echo '2: eth0    inet 192.168.0.20/24 brd 192.168.0.255 scope global eth0'; "
                            "echo '3: wlan0    inet 10.0.0.5/24 brd 10.0.0.255 scope global wlan0'")
        self.assertEqual(self.env.out("net_ips").strip(), "192.168.0.20 10.0.0.5")

    def test_hardware_when_no_wifi_adapter_shows_up(self):
        # No gabinete: "No Wi-Fi adapter was found" sem dizer o que existe.
        self.env.stub("lspci", "echo '00:1f.6 Ethernet controller: Intel Corporation Ethernet I219-V'; "
                               "echo '03:00.0 Network controller: Intel Corporation Wi-Fi 6 AX200 (rev 1a)'")
        self.env.stub("lsusb", "echo 'Bus 001 Device 003: ID 0bda:8179 Realtek Semiconductor Corp. "
                               "RTL8188EUS 802.11n Wireless Network Adapter'; "
                               "echo 'Bus 001 Device 002: ID 046d:c52b Logitech, Inc. Unifying Receiver'")
        self.env.stub("rfkill", "echo '0: phy0: Wireless LAN'; echo '	Soft blocked: yes'")
        self.assertEqual(self.env.out("net_hardware").splitlines(), [
            "PCI: Intel Corporation Wi-Fi 6 AX200 (rev 1a)",
            "USB: Realtek Semiconductor Corp. RTL8188EUS 802.11n Wireless Network Adapter",
            "Wi-Fi is switched off (rfkill): check the Wi-Fi key or the BIOS."])
        self.env.stub("lspci", "true")
        self.env.stub("lsusb", "true")
        self.env.stub("rfkill", "true")
        self.assertEqual(self.env.out("net_hardware").splitlines(),
                         ["No network adapter besides Ethernet was found."])


class AudioTests(Base):
    def test_devices(self):
        self.env.stub("aplay", "cat <<'EOF'\n**** List of PLAYBACK Hardware Devices ****\n"
                               "card 0: PCH [HDA Intel PCH], device 0: ALC887-VD Analog [ALC887-VD Analog]\n"
                               "  Subdevices: 1/1\n"
                               "card 1: HDMI [HDA ATI HDMI], device 3: HDMI 0 [HDMI 0]\nEOF")
        self.assertEqual(self.env.out("audio_devices").splitlines(),
                         ["0,0|HDA Intel PCH - ALC887-VD Analog", "1,3|HDA ATI HDMI - HDMI 0"])

    def test_default_card(self):
        conf = self.env.dir / "asound.conf"
        self.env.out("audio_set_default 1,3", {"ASOUND_CONF": str(conf)})
        self.assertIn("defaults.pcm.card 1\n", conf.read_text())
        self.assertIn("defaults.pcm.device 3\n", conf.read_text())

    def mixer(self, controls, level=60):
        """amixer falso: lista os controles da placa, responde o nivel e
        registra cada sset."""
        self.calls = self.env.dir / "amixer.log"
        self.calls.write_text("")
        listing = "".join("Simple mixer control '%s',0\\n" % c for c in controls)
        self.env.stub("amixer", textwrap.dedent("""\
            args="$*"
            case $args in
              *scontrols*) printf "%s" ;;
              *sget*) echo "  Front Left: Playback 52 [%d%%] [-10.00dB] [on]" ;;
              *sset*) echo "${args#*sset }" >> "%s" ;;
            esac""") % (listing, level, self.calls))
        self.env.stub("alsactl", "true")
        (self.env.etc / "fliperos.conf").write_text("alsa=1,0\n")

    def test_volume_keeps_pcm_at_max_like_ga(self):
        self.mixer(["Master", "PCM", "Front", "Capture"])
        self.env.out("audio_set_volume 60")
        self.assertEqual(self.calls.read_text().splitlines(),
                         ["PCM 100% unmute", "Master 60% unmute", "Front 60% unmute"])
        self.assertIn("volume=60\n", (self.env.etc / "fliperos.conf").read_text())

    def test_card_with_only_pcm_uses_pcm_as_volume(self):
        self.mixer(["PCM"])
        self.env.out("audio_set_volume 40")
        self.assertEqual(self.calls.read_text().splitlines(), ["PCM 40% unmute"])

    def test_volume_keys(self):
        self.mixer(["Master", "PCM", "Speaker"])
        self.env.out("audio_step up; audio_step down; audio_step mute")
        self.assertEqual(self.calls.read_text().splitlines(), [
            "Master 5%+ unmute", "Speaker 5%+ unmute",
            "Master 5%-", "Speaker 5%-",
            "Master toggle", "Speaker toggle"])
        self.assertEqual(self.env.run("audio_step sideways").returncode, 1)

    def test_volume_shown_is_the_mixer_level(self):
        # As teclas mudam o mixer sem passar pelo Setup: vale o nivel real.
        self.mixer(["Master"], level=35)
        (self.env.etc / "fliperos.conf").write_text("alsa=1,0\nvolume=80\n")
        self.assertEqual(self.env.out("audio_volume").strip(), "35")

    def test_mame_audio_latency(self):
        mame = self.env.etc / "mame.ini"
        mame.write_text("sound sdl\n")
        self.assertEqual(self.env.out("audio_mame_latency").strip(), "0.0")
        for bad in ("51", "-1", "abc", "1.2.3", ""):
            self.assertEqual(self.env.run("audio_set_mame_latency '%s'" % bad).returncode, 1, bad)
        self.env.out("audio_set_mame_latency 2.5")
        self.assertEqual(self.env.out("audio_mame_latency").strip(), "2.5")
        self.env.out("audio_set_mame_latency 50")
        self.assertIn("audio_latency", mame.read_text())


class LauncherTests(Base):
    def setUp(self):
        super().setUp()
        (self.env.etc / "sessions.conf").write_text(
            "# comentario\nsetup|none|||FliperOS Setup menu\n"
            "attractplus|kms|attractplus|fliperos-attractplus|Attract-Mode Plus\n"
            "retroarch|kms|retroarch||RetroArch\nlxde|x|startlxde|lxde|LXDE desktop\n")
        self.env.stub("retroarch", "true")
        self.env.stub("startlxde", "true")

    def test_available_lists_only_installed(self):
        self.assertEqual(self.env.out("launcher_available").splitlines(),
                         ["setup|FliperOS Setup menu", "retroarch|RetroArch", "lxde|LXDE desktop"])

    def test_set_and_current(self):
        self.assertEqual(self.env.out("launcher_current").strip(), "setup")
        self.env.out("launcher_set retroarch")
        self.assertEqual(self.env.out("launcher_current").strip(), "retroarch")
        self.assertIn("launcher=retroarch\n", (self.env.etc / "fliperos.conf").read_text())
        self.assertEqual(self.env.out("launcher_package attractplus").strip(), "fliperos-attractplus")

    def test_program_fetched_from_its_own_site(self):
        # "fetch:COMANDO" na coluna do pacote: um programa de codigo fechado,
        # que nao vem na imagem nem no repositorio. Nao e pacote do apt: o
        # Setup roda "COMANDO fetch --progress", que fala com a tela de
        # progresso, e o binario da linha so existe depois.
        target = self.env.dir / "fc" / "fightcade"
        with open(self.env.etc / "sessions.conf", "a") as table:
            table.write("fightcade|kms|%s|fetch:fliperos-fightcade|Fightcade 2\n" % target)
        fbin = self.env.dir / "fbin"
        fbin.mkdir()
        command = fbin / "fliperos-fightcade"
        command.write_text('#!/bin/sh\necho "@step 50 args=$*"\nmkdir -p "%s"\nprintf "#!/bin/sh\\n" > "%s"\n'
                           'chmod +x "%s"\n' % (target.parent, target, target))
        command.chmod(0o755)
        env = {"FLIPEROS_BIN": str(fbin)}
        self.assertEqual(self.env.out("launcher_package fightcade", env), "")
        self.assertEqual(self.env.out("launcher_fetcher fightcade", env).strip(), str(command))
        self.assertEqual(self.env.out("launcher_fetcher attractplus; launcher_fetcher retroarch", env), "")
        self.assertEqual(self.env.run("launcher_installed fightcade", env).returncode, 1)
        self.assertNotIn("fightcade", self.env.out("launcher_available", env))
        self.assertEqual(self.env.out("launcher_fetch fightcade", env).splitlines(),
                         ["@step 0 Starting", "@step 50 args=fetch --progress"])
        self.assertEqual(self.env.run("launcher_installed fightcade", env).returncode, 0)
        self.assertIn("fightcade|Fightcade 2", self.env.out("launcher_available", env))
        # Sem o comando na imagem: a tela recebe a falha, nao um erro do shell.
        command.unlink()
        run = self.env.run("launcher_fetch fightcade", env)
        self.assertEqual(run.returncode, 1)
        self.assertIn("@fail Starting|the installer of Fightcade 2 is missing", run.stdout)
        # A tela: quem tem fetch aparece como "not installed" e e baixado.
        screen = (SETUP / "screens" / "setup-menu.sh").read_text().split("screen_frontend() {")[1].split("\n}\n")[0]
        self.assertIn('launcher_package_available "$name" || [[ -n $(launcher_fetcher "$name") ]]', screen)
        self.assertIn('run_with_progress "Downloading $label" "" launcher_fetch "$choice" || return 0', screen)
        self.assertLess(screen.index("launcher_fetch "), screen.index('launcher_set "$choice"'))
        self.assertIn("roms/fightcade", self.env.out("frontends_hint fightcade"))
        self.assertEqual(self.env.out("frontends_hint pegasus"), "")

    def test_request_is_left_for_the_tty1_loop(self):
        request = self.env.dir / "run" / "launch"
        env = {"LAUNCH_REQUEST": str(request)}
        self.env.out("launcher_request lxde", env)
        self.assertEqual(request.read_text(), "lxde\n")
        self.env.out("launcher_request", env)
        self.assertEqual(request.read_text(), "default\n")


class QuirksTests(Base):
    def quirks(self):
        f = self.env.etc / "quirks.conf"
        return f.read_text().splitlines() if f.exists() else []

    def test_add_normalizes_and_keeps_the_name(self):
        self.env.out("quirk_add 'Xin-Mo | dual' ' 0x16C0:0x05E1:0x40 '")
        self.assertEqual(self.quirks(), ["0x16c0:0x05e1:0x40|Xin-Mo   dual"])
        # Sem nome, vale o vendor:produto.
        self.env.out("quirk_add '' 0x0079:0x0006:0x8")
        self.assertEqual(self.quirks()[1], "0x0079:0x0006:0x8|0x0079:0x0006")

    def test_codes_the_kernel_would_not_parse_are_refused(self):
        # O kernel le "0x%hx:0x%hx:0x%x": o 0x e os tres campos sao obrigatorios.
        for bad in ("16c0:05e1:40", "0x16c0:0x05e1", "0xzz:0x1:0x1", "0x12345:0x1:0x1",
                    "0x1:0x1:0x123456789", ""):
            self.assertEqual(self.env.run("quirk_add n '%s'" % bad).returncode, 1, bad)
        self.assertEqual(self.quirks(), [])

    def test_one_quirk_per_device_and_at_most_four(self):
        self.env.out("quirk_add a 0x16c0:0x05e1:0x40")
        self.assertEqual(self.env.run("quirk_add b 0x16c0:0x05e1:0x8").returncode, 3)
        for i in range(2, 5):
            self.env.out("quirk_add q%d 0x000%d:0x0001:0x40" % (i, i))
        self.assertEqual(self.env.out("quirks_count").strip(), "4")
        self.assertEqual(self.env.run("quirk_add q5 0x0005:0x0001:0x40").returncode, 2)

    def test_delete(self):
        self.env.out("quirk_add a 0x16c0:0x05e1:0x40; quirk_add b 0x0079:0x0006:0x8")
        self.env.out("quirk_delete 0x16c0:0x05e1:0x40")
        self.assertEqual(self.quirks(), ["0x0079:0x0006:0x8|b"])

    def test_kernel_line(self):
        line = "quiet splash usbhid.quirks=0x1:0x1:0x1 consoleblank=0"
        self.assertEqual(self.env.out("quirks_cmdline '%s'" % line).strip(), "quiet splash consoleblank=0")
        self.env.out("quirk_add a 0x16c0:0x05e1:0x40; quirk_add b 0x0079:0x0006:0x8")
        self.assertEqual(self.env.out("quirks_cmdline '%s'" % line).strip(),
                         "quiet splash consoleblank=0 usbhid.quirks=0x16c0:0x05e1:0x40,0x0079:0x0006:0x8")
        self.env.cmdline.write_text("boot=live quiet splash\n")
        self.assertIn("usbhid.quirks=0x16c0:0x05e1:0x40,0x0079:0x0006:0x8",
                      self.env.out("boot_install_cmdline").split())

    def test_usb_devices_in_the_code_format(self):
        self.env.stub("lsusb", "echo 'Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub'; "
                               "echo 'Bus 001 Device 004: ID 16C0:05e1 Van Ooijen Technische Informatica Xin-Mo'")
        self.assertEqual(self.env.out("quirks_usb_devices").splitlines(),
                         ["0x16c0:0x05e1  Van Ooijen Technische Informatica Xin-Mo"])


class DebugModeTests(Base):
    """Setup > Debug mode: boot e programas com ou sem texto na tela."""

    def test_boot_line_with_and_without_debug(self):
        line = "quiet splash %s consoleblank=0 video=VGA-1:640x240Se" % BOOT_SILENT
        self.assertEqual(self.env.out("debug_cmdline '%s'" % line).strip(), line)
        (self.env.etc / "debug").write_text("")
        self.assertEqual(self.env.out("debug_cmdline '%s'" % line).strip(), "consoleblank=0 video=VGA-1:640x240Se")
        # Desligar devolve o boot calado, na frente.
        (self.env.etc / "debug").unlink()
        self.assertEqual(self.env.out("debug_cmdline 'consoleblank=0'").strip(),
                         "quiet splash %s consoleblank=0" % BOOT_SILENT)

    def test_set_writes_the_flag_and_the_limine_quiet(self):
        boot = self.env.etc / "fliperos-boot"
        boot.write_text('FLIPEROS_CMDLINE="quiet"\nFLIPEROS_TIMEOUT="3"\n')
        self.env.out("debug_set on")
        self.assertTrue((self.env.etc / "debug").exists())
        self.assertIn('FLIPEROS_QUIET="no"\n', boot.read_text())
        self.assertIn("debug=1\n", (self.env.etc / "fliperos.conf").read_text())
        self.env.out("debug_set off")
        self.assertFalse((self.env.etc / "debug").exists())
        self.assertIn('FLIPEROS_QUIET="yes"\n', boot.read_text())
        self.assertIn('FLIPEROS_TIMEOUT="3"\n', boot.read_text())


class RetroArchSuperTests(Base):
    """crt_switch_resolution_super: nativo (0) em placa com dotclock baixo; no
    gabinete (R7 240) as notificacoes saiam espremidas em 2560."""

    def test_native_when_the_card_does_low_dotclocks(self):
        cfg = self.env.etc / "retroarch.cfg"
        shutil.copy(ROOT / "config/retroarch.cfg", cfg)
        conf = self.env.etc / "fliperos.conf"
        for detection, width in (("se", "0"), ("sr", "0"), ("sdo", "0"), ("e", "2560"), ("r", "2560")):
            conf.write_text("detection=%s\n" % detection)
            self.env.out("video_retroarch_super")
            self.assertIn('crt_switch_resolution_super = "%s"\n' % width, cfg.read_text(), detection)

    def test_saved_with_the_output_test_result(self):
        cfg = self.env.etc / "retroarch.cfg"
        shutil.copy(ROOT / "config/retroarch.cfg", cfg)
        self.env.connector("card0-VGA-1", "disconnected")
        self.env.out("video_save_result card0-VGA-1 se generic_15")
        self.assertIn('crt_switch_resolution_super = "0"\n', cfg.read_text())


class LptTests(Base):
    """Joysticks na porta paralela: db9, gamecon e turbografx do kernel."""

    def setUp(self):
        super().setUp()
        d = self.env.dir
        self.modprobe = d / "modprobe.d" / "fliperos-lpt.conf"
        self.modules = d / "modules-load.d" / "fliperos-lpt.conf"
        self.lpt_env = {"LPT_MODPROBE_CONF": str(self.modprobe), "LPT_MODULES_CONF": str(self.modules),
                        "PARPORT_SYSFS": str(d / "parport-sys"), "PARPORT_PROC": str(d / "parport-proc"),
                        "PROC_INPUT": str(d / "input-devices")}

    def out(self, script):
        return self.env.out(script, self.lpt_env)

    def test_module_options_follow_the_kernel_parameters(self):
        # Os nomes e numeros de db9.c, gamecon.c e turbografx.c.
        self.assertEqual(self.out("lpt_options gamecon 0 7 7").strip(), "options gamecon map=0,7,7")
        self.assertEqual(self.out("lpt_options gamecon 1 0 1").strip(), "options gamecon map=1,0,1")
        self.assertEqual(self.out("lpt_options db9 0 1").strip(), "options db9 dev=0,1")
        self.assertEqual(self.out("lpt_options turbografx 0 2 2 2").strip(), "options turbografx map=0,2,2,2")
        for bad in ("db9 0 4", "db9 0 0", "db9 0 1 2", "db9 0 13", "gamecon 0 0 0", "gamecon 0 10",
                    "gamecon 0 1 1 1 1 1 1", "turbografx 0 6", "turbografx 0 1 1 1 1 1 1 1 1",
                    "gamecon x 7", "gamecon 0", "foo 0 1"):
            self.assertEqual(self.env.run("lpt_options %s" % bad, self.lpt_env).returncode, 1, bad)

    def test_set_writes_the_module_options_and_the_boot_load(self):
        self.out("lpt_set gamecon 0 7 7")
        self.assertIn("lpt=gamecon 0 7 7\n", (self.env.etc / "fliperos.conf").read_text())
        conf = self.modprobe.read_text()
        self.assertIn("options gamecon map=0,7,7\n", conf)
        self.assertIn("blacklist lp\n", conf)
        self.assertEqual(self.modules.read_text(), "parport_pc\ngamecon\n")
        self.assertEqual(self.out("lpt_describe").strip(), "gamecon on parport0: PlayStation pad; PlayStation pad")
        self.assertEqual(self.env.run("lpt_set gamecon 0 0", self.lpt_env).returncode, 1)
        self.out("lpt_disable")
        self.assertFalse(self.modprobe.exists())
        self.assertFalse(self.modules.exists())
        self.assertEqual(self.out("lpt_describe").strip(), "off")

    def test_reload_swaps_the_driver(self):
        log = self.env.dir / "modprobe.log"
        self.env.stub("modprobe", 'echo "$*" >> %s' % log)
        self.out("lpt_set db9 0 2; lpt_reload")
        self.assertEqual(log.read_text().splitlines(), ["-r db9 gamecon turbografx lp", "parport_pc", "db9"])
        log.unlink()
        self.out("lpt_disable; lpt_reload")
        self.assertEqual(log.read_text().splitlines(), ["-r db9 gamecon turbografx lp"])

    def test_ports_and_joysticks_found(self):
        d = self.env.dir
        (d / "parport-sys" / "parport0").mkdir(parents=True)
        (d / "parport-proc" / "parport0").mkdir(parents=True)
        (d / "parport-proc" / "parport0" / "base-addr").write_text("888\t1912\n")
        (d / "parport-proc" / "parport0" / "modes").write_text("PCSPP,TRISTATE,EPP\n")
        self.assertEqual(self.out("lpt_ports").splitlines(), ["0|parport0 (0x378, PCSPP,TRISTATE,EPP)"])
        (d / "input-devices").write_text(
            'I: Bus=0011 Vendor=0001 Product=0001 Version=ab41\nN: Name="AT Translated Set 2 keyboard"\n'
            'P: Phys=isa0060/serio0/input0\n\n'
            'I: Bus=0000 Vendor=0001 Product=0007 Version=0100\nN: Name="PSX controller"\n'
            'P: Phys=parport0/input0\n\n'
            'I: Bus=0000 Vendor=0001 Product=0007 Version=0100\nN: Name="PSX controller"\n'
            'P: Phys=parport0/input1\n')
        self.assertEqual(self.out("lpt_devices").splitlines(),
                         ["parport0: PSX controller", "parport0: PSX controller"])


class UpdateTests(Base):
    def test_status_fd_to_events(self):
        lines = "dlstatus:1:0:Retrieving file 1 of 2\\ndlstatus:2:50:Retrieving file 2 of 2\\n" \
                "pmstatus:mesa:0:Preparing mesa\\npmstatus:mesa:100:Installed mesa\\n"
        out = self.env.out("printf '%s' | update_parse_status" % lines).splitlines()
        self.assertEqual(out, ["@step 10 Retrieving file 1 of 2", "@step 30 Retrieving file 2 of 2",
                               "@step 50 Preparing mesa", "@step 99 Installed mesa"])

    def test_waits_for_another_program_using_the_package_manager(self):
        # No gabinete, instalar um frontend durante uma atualizacao falhava na
        # hora com "Impossivel criar acesso exclusivo". A trava e de registro
        # (fcntl), como a do apt.
        lock = self.env.dir / "lock-frontend"
        lock.write_text("")
        env = {"APT_LOCKS": "%s %s" % (lock, self.env.dir / "nao-existe")}
        self.assertEqual(self.env.run("update_locked", env).returncode, 1)
        holder = subprocess.Popen(
            ["python3", "-c", "import fcntl, sys, time\nf = open(sys.argv[1], 'a')\nfcntl.lockf(f, fcntl.LOCK_EX)\n"
                              "print('ok', flush=True)\ntime.sleep(60)", str(lock)],
            stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(holder.stdout.readline().strip(), "ok")
            self.assertEqual(self.env.run("update_locked", env).returncode, 0)
            # Espera (o sleep dos testes nao dorme) e, no limite, diz o que ha.
            r = self.env.run("update_wait_lock", dict(env, APT_LOCK_WAIT="6"))
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout.count("@msg Another program is installing or updating packages"), 1)
            self.assertIn("Try again in a few minutes", r.stdout)
            self.assertEqual(self.env.run("update_install_package x", dict(env, APT_LOCK_WAIT="3")).returncode, 1)
        finally:
            holder.kill()
            holder.wait()
            holder.stdout.close()
        self.assertEqual(self.env.out("update_wait_lock; echo livre", env).strip(), "livre")

    def test_install_waits_then_lets_apt_wait_too(self):
        calls = self.env.dir / "apt.calls"
        self.env.stub("apt-get", 'echo "$*" >> "%s"' % calls)
        out = self.env.out("update_install_package fliperos-pegasus",
                           {"APT_LOCKS": str(self.env.dir / "nao-existe")}).splitlines()
        self.assertEqual(out[-1], "@step 100 fliperos-pegasus installed")
        self.assertEqual(calls.read_text().splitlines(),
                         ["update", "-y -o DPkg::Lock::Timeout=120 -o APT::Status-Fd=3 install fliperos-pegasus"])
        body = (SETUP / "lib" / "update.sh").read_text().split("update_run() {")[1]
        self.assertLess(body.index("update_wait_lock || return 1"), body.index("ev_run apt-get update"))


class GeometryTests(Base):
    def test_parse_and_apply(self):
        out = "Finished!\nFinal geometry: 1.0:2:-1\nFinal crt_range: 15625.0-15750.0,49.5-65.0,2.0,4.7,8.0,0.064,0.192,1.024,0,0,192,288,448,576\n"
        rng = self.env.out("geometry_parse '%s'" % out).strip()
        self.assertTrue(rng.startswith("15625.0-15750.0,49.5-65.0"))
        (self.env.etc / "switchres.ini").write_text("\tmonitor                   generic_15\n")
        (self.env.etc / "mame.ini").write_text("switchres_ini 0\n")
        self.env.out("geometry_apply '%s'" % rng)
        ini = (self.env.etc / "switchres.ini").read_text()
        self.assertIn("monitor                   custom", ini)
        self.assertIn("crt_range0", ini)
        self.assertIn("switchres_ini 1", (self.env.etc / "mame.ini").read_text())

    def test_reset_goes_back_to_the_monitor_preset(self):
        (self.env.etc / "switchres.ini").write_text("\tmonitor                   custom\n"
                                                    "\tcrt_range0                15625.0-15750.0,49.5-65.0\n")
        (self.env.etc / "mame.ini").write_text("monitor arcade_15\nswitchres_ini 1\n")
        self.env.out("conf_set monitor arcade_15; conf_set geometry 15625.0-15750.0,49.5-65.0; geometry_reset")
        ini = (self.env.etc / "switchres.ini").read_text()
        self.assertRegex(ini, r"(?m)^\s*monitor\s+arcade_15$")
        self.assertRegex(ini, r"(?m)^\s*crt_range0\s+auto$")
        mame = (self.env.etc / "mame.ini").read_text()
        # O GroovyMAME continua lendo o switchres.ini, como no GroovyArcade.
        self.assertRegex(mame, r"(?m)^switchres_ini\s+1$")
        self.assertRegex(mame, r"(?m)^aspect\s+4:3$")
        self.assertEqual(self.env.out("conf_get geometry || echo none").strip(), "none")

    def test_cancelled(self):
        self.assertEqual(self.env.out("geometry_parse 'Aborted!'").strip(), "")

    def test_grid_uses_the_chosen_resolution(self):
        # No gabinete o grid saia sempre em 648x480, qualquer que fosse a
        # resolucao escolhida no Video Setup.
        conf = self.env.etc / "fliperos.conf"
        # Os modos PAL da tabela do kernel sao de 50 Hz (o refresh vem do
        # modeline; no entrelacado conta o campo).
        for res, mode in (("640x240S", "640 240 60"), ("320x240", "320 240 60"),
                          ("640x480iS", "640 480 60"), ("384x224@59.64", "384 224 59.64"),
                          ("384x288S", "384 288 50"), ("768x576iS", "768 576 50"),
                          ("1280x480iS", "1280 480 60")):
            conf.write_text("boot_resolution=%s\n" % res)
            self.assertEqual(self.env.out("geometry_mode").strip(), mode, res)
        conf.write_text("boot_resolution=custom\ncustom_width=512\ncustom_height=240\ncustom_refresh=57.5\n")
        self.assertEqual(self.env.out("geometry_mode").strip(), "512 240 57.5")
        conf.write_text("")
        self.assertEqual(self.env.out("geometry_mode").strip(), "640 480 60")


# Flags reais de /proc/cpuinfo, reduzidas ao que o nivel x86-64 olha.
FLAGS_CORE2 = "fpu sse sse2 ssse3 cx16 sse4_1 lahf_lm"
FLAGS_NEHALEM = FLAGS_CORE2 + " popcnt sse4_2"
FLAGS_HASWELL = FLAGS_NEHALEM + " avx avx2 bmi1 bmi2 f16c fma abm movbe xsave"
FLAGS_ZEN4 = FLAGS_HASWELL + " avx512f avx512bw avx512cd avx512dq avx512vl"


class HardwareTests(Base):
    def machine(self, flags, threads, cores, max_khz=None, mhz=None, ram_kb=16300000,
                model="AMD Ryzen 5 3600 6-Core Processor"):
        blocks = []
        for i in range(threads):
            block = "processor\t: %d\nmodel name\t: %s\n" % (i, model)
            if cores:
                block += "physical id\t: 0\ncore id\t\t: %d\n" % (i % cores)
            if mhz:
                block += "cpu MHz\t\t: %s\n" % mhz
            blocks.append(block + "flags\t\t: %s\n" % flags)
        (self.env.dir / "cpuinfo").write_text("\n".join(blocks))
        (self.env.dir / "meminfo").write_text("MemTotal:       %d kB\nMemFree:        1 kB\n" % ram_kb)
        if max_khz:
            freq = self.env.dir / "cpu" / "cpu0" / "cpufreq"
            freq.mkdir(parents=True, exist_ok=True)
            (freq / "cpuinfo_max_freq").write_text("%d\n" % max_khz)

    def test_modern_cpu_is_ready(self):
        self.machine(FLAGS_HASWELL, 12, 6, max_khz=4208000)
        out = self.env.out("hw_cpu_model; hw_cpu_threads; hw_cpu_cores; hw_cpu_max_mhz; hw_cpu_level; "
                           "hw_ram_label $(hw_ram_mb); hw_mhz_label 4208").splitlines()
        self.assertEqual(out, ["AMD Ryzen 5 3600 6-Core Processor", "12", "6", "4208", "3", "16 GB", "4.2 GHz"])
        self.assertEqual(self.env.run("hw_low_latency_ok").returncode, 0)
        self.assertEqual(self.env.out("hw_low_latency_missing").strip(), "")

    def test_levels(self):
        for flags, level in ((FLAGS_CORE2, "1"), (FLAGS_NEHALEM, "2"), (FLAGS_HASWELL, "3"), (FLAGS_ZEN4, "4")):
            self.machine(flags, 1, 1)
            self.assertEqual(self.env.out("hw_cpu_level").strip(), level, flags)

    def test_old_cpu_lists_what_is_missing(self):
        self.machine(FLAGS_CORE2, 2, 2, max_khz=2400000, ram_kb=1950000, model="Intel(R) Core(TM)2 Duo CPU E6600")
        self.assertEqual(self.env.run("hw_low_latency_ok").returncode, 1)
        rows = self.env.out("hw_low_latency_check").splitlines()
        self.assertEqual(rows, [
            "low|CPU instructions|x86-64 (no AVX2)|x86-64-v3 (AVX2)",
            "low|CPU threads|2|4 or more",
            "low|Max clock|2.4 GHz|3.0 GHz or more",
            "low|Memory|2 GB|4 GB or more"])
        self.assertIn("CPU threads: 2, need 4 or more; Max clock", self.env.out("hw_low_latency_missing"))

    def test_one_missing_requirement(self):
        # i3-4130: Haswell (AVX2), 2 nucleos / 4 threads, 3.4 GHz, 4 GB.
        self.machine(FLAGS_HASWELL, 4, 2, max_khz=3400000, ram_kb=3900000)
        self.assertEqual(self.env.run("hw_low_latency_ok").returncode, 0)
        self.machine(FLAGS_HASWELL, 2, 2, max_khz=3400000, ram_kb=3900000)
        self.assertEqual(self.env.out("hw_low_latency_missing").strip(), "CPU threads: 2, need 4 or more")

    def test_vm_without_cpufreq(self):
        # Sem cpufreq vale o "cpu MHz"; sem nenhum dos dois, o clock nao reprova.
        self.machine(FLAGS_HASWELL, 4, None, mhz="2995.210")
        self.assertEqual(self.env.out("hw_cpu_max_mhz; hw_cpu_cores").split(), ["2995", "4"])
        self.machine(FLAGS_HASWELL, 4, None)
        self.assertEqual(self.env.out("hw_cpu_max_mhz").strip(), "0")
        self.assertIn("ok|Max clock|unknown|", self.env.out("hw_low_latency_check"))

    def test_gpu_and_analog_outputs(self):
        self.env.card("card0", "radeon")
        self.env.connector("card0-VGA-1")
        self.env.connector("card0-HDMI-A-1")
        self.env.connector("card0-DVI-I-1")
        self.assertEqual(self.env.out("hw_gpu").strip(), "AMD Radeon HD 5000/6000/7350/8350 Series (radeon)")
        self.assertEqual(self.env.out("hw_analog_outputs").strip(), "DVI-I-1,VGA-1")


class LatencyTests(Base):
    def test_cmdline_per_mode(self):
        out = self.env.out("latency_cmdline 'quiet preempt=full mitigations=auto' standard").strip()
        self.assertEqual(out, "quiet " + LATENCY_BASE)
        out = self.env.out("latency_cmdline 'quiet' low").strip()
        self.assertEqual(out, "quiet " + LATENCY_BASE + " preempt=full")

    def test_usb_poll_can_go_back_to_the_default(self):
        (self.env.etc / "fliperos.conf").write_text("usb_poll=default\n")
        out = self.env.out("latency_cmdline 'quiet usbhid.jspoll=1' low").strip()
        self.assertEqual(out, "quiet mitigations=off audit=0 preempt=full")

    def test_boot_compose_follows_the_saved_mode(self):
        conf = self.env.etc / "fliperos.conf"
        conf.write_text("latency=low\n")
        low = self.env.out("boot_compose 'quiet splash'").strip()
        self.assertTrue(low.endswith("preempt=full"), low)
        conf.write_text("latency=standard\n")
        standard = self.env.out("boot_compose '%s'" % low).strip()
        self.assertEqual(standard, "quiet splash " + BOOT_SILENT + " " + LATENCY_BASE)
        # Sem modo gravado vale o padrao.
        conf.write_text("")
        self.assertEqual(self.env.out("latency_mode").strip(), "standard")

    def test_emulators_low_and_back_to_the_shipped_files(self):
        shutil.copy(ROOT / "config/retroarch.cfg", self.env.etc / "retroarch.cfg")
        shutil.copy(ROOT / "config/mame.ini", self.env.etc / "mame.ini")
        self.env.out("latency_apply low")
        cfg = self.env.etc / "retroarch.cfg"
        for key, value in (("video_frame_delay_auto", "true"), ("preemptive_frames_enable", "true"),
                           ("run_ahead_enabled", "false"), ("run_ahead_frames", "1"),
                           ("video_max_swapchain_images", "2")):
            self.assertEqual(self.env.out("rcfg_get '%s' %s" % (cfg, key)).strip(), value, key)
        self.assertIn("latency=low\n", (self.env.etc / "fliperos.conf").read_text())
        # O modo padrao devolve exatamente os arquivos que a ISO instala: os
        # valores de latency_emulators e os de config/ nao podem divergir.
        self.env.out("latency_apply standard")
        self.assertEqual(cfg.read_text(), (ROOT / "config/retroarch.cfg").read_text())
        self.assertEqual((self.env.etc / "mame.ini").read_text(), (ROOT / "config/mame.ini").read_text())

    def governors(self, available="performance schedutil", current="schedutil"):
        files = []
        for n in (0, 1):
            policy = self.env.dir / "cpu" / "cpufreq" / ("policy%d" % n)
            policy.mkdir(parents=True, exist_ok=True)
            (policy / "scaling_available_governors").write_text(available + "\n")
            (policy / "scaling_governor").write_text(current + "\n")
            files.append(policy / "scaling_governor")
        return files

    def test_session_switches_to_performance_and_back(self):
        files = self.governors()
        self.env.out("latency_session_start")
        self.assertEqual([f.read_text() for f in files], ["performance", "performance"])
        self.assertEqual((self.env.dir / "run" / "governor").read_text(), "schedutil\n")
        # Uma sessao dentro da outra nao sobrescreve o governador guardado.
        self.env.out("latency_session_start")
        self.assertEqual((self.env.dir / "run" / "governor").read_text(), "schedutil\n")
        self.env.out("latency_session_end")
        self.assertEqual([f.read_text() for f in files], ["schedutil", "schedutil"])
        self.assertFalse((self.env.dir / "run" / "governor").exists())

    def test_low_mode_keeps_performance(self):
        files = self.governors()
        (self.env.etc / "fliperos.conf").write_text("latency=low\n")
        self.env.out("latency_boot")
        self.assertEqual(files[0].read_text(), "performance")
        self.env.out("latency_session_start; latency_session_end")
        self.assertEqual(files[0].read_text(), "performance")

    def test_back_to_standard_restores_the_default_governor(self):
        files = self.governors(available="performance powersave", current="performance")
        self.env.out("latency_apply standard")
        self.assertEqual(files[1].read_text(), "powersave")
        # Modo padrao no boot nao mexe na CPU.
        files[1].write_text("powersave")
        self.env.out("latency_boot")
        self.assertEqual(files[1].read_text(), "powersave")

    def test_no_cpufreq_is_not_an_error(self):
        self.env.out("latency_session_start; latency_session_end; latency_boot")
        self.assertFalse((self.env.dir / "run" / "governor").exists())


class StructureTests(unittest.TestCase):
    """Regras da arquitetura: a logica nao chama o gum."""

    def test_only_ui_calls_gum(self):
        for path in (SETUP / "lib").glob("*.sh"):
            if path.name == "ui.sh":
                continue
            for n, line in enumerate(path.read_text().splitlines(), 1):
                code = line.split("#", 1)[0]
                self.assertNotRegex(code, r"\bgum\b", "%s:%d chama o gum" % (path.name, n))

    def test_entry_sources_every_file(self):
        entry = (SETUP / "fliperos-setup").read_text()
        for path in list((SETUP / "lib").glob("*.sh")) + list((SETUP / "screens").glob("*.sh")):
            rel = "%s/%s" % (path.parent.name, path.name)
            self.assertIn('source "$SETUP_DIR/%s"' % rel, entry, rel)


class TopbarTests(Base):
    """O IP e o uso do disco no topo, ate em 320x240 (40 colunas)."""

    STATUS = "fliperos (192.168.1.111 10.0.0.5) - 42% used on /"

    def topbar(self, cols, title="FliperOS", status=STATUS):
        # ui_topbar escreve em /dev/tty: um terminal falso (script).
        cmd = ("UI_COLS=%d UI_TITLE='%s' UI_STATUS='%s'; ui_topbar; echo \"rows=$UI_TOPBAR_ROWS\""
               % (cols, title, status))
        script = self.env.dir / "topbar.sh"
        script.write_text(cmd)
        out = self.env.out('script -qec "bash -c \'%s\'" /dev/null' %
                           ("source %s/lib/ui.sh; source %s" % (SETUP, script)))
        lines = re.sub(r"\x1b\[[0-9;]*m|\r", "", out).splitlines()
        return [l.rstrip() for l in lines if l.strip()]

    def test_short_status(self):
        for status, short in ((self.STATUS, "192.168.1.111 - 42%"),
                              ("fliperos (no network) - 7% used on /", "no network - 7%"),
                              ("fliperos (192.168.1.111)", "192.168.1.111")):
            out = self.env.out("source %s/lib/ui.sh; UI_STATUS='%s'; ui_status_short" % (SETUP, status)).strip()
            self.assertEqual(out, short, status)

    def test_full_short_or_own_line(self):
        lines = self.topbar(80)
        self.assertTrue(lines[0].endswith(self.STATUS), lines)
        self.assertIn("rows=2", lines)
        # 40 colunas: o curto ao lado do titulo.
        lines = self.topbar(40)
        self.assertRegex(lines[0], r"^ FliperOS +192\.168\.1\.111 - 42%$")
        self.assertIn("rows=2", lines)
        # Titulo comprido: o status numa linha propria, a direita.
        lines = self.topbar(40, title="Scraping retroarch/snes9x")
        self.assertEqual(lines[0], " Scraping retroarch/snes9x")
        self.assertRegex(lines[1], r"^ +192\.168\.1\.111 - 42%$")
        self.assertIn("rows=3", lines)


class ScraperTests(Base):
    """Setup > Scraper: o que o Skyscraper raspa e onde a lista vai parar."""

    def scraper_env(self):
        roms, info, attract = self.env.dir / "roms", self.env.dir / "info", self.env.dir / "attract"
        for d in ("mame", "ps2", "dolphin", "retroarch/snes9x", "retroarch/fceumm", "retroarch/semnada"):
            (roms / d).mkdir(parents=True)
            (roms / d / "_info.txt").write_text("o que vai nesta pasta\n")
        (roms / "mame" / "sf2.zip").write_text("rom")
        (roms / "mame" / "chds").mkdir()
        (roms / "mame" / "chds" / "kinst.chd").write_text("chd")
        (roms / "retroarch" / "snes9x" / "Super Mario World (USA).sfc").write_text("rom")
        (roms / "retroarch" / "semnada" / "jogo.bin").write_text("rom")
        info.mkdir()
        (info / "snes9x_libretro.info").write_text(
            'display_name = "Nintendo - SNES / SFC (Snes9x - Current)"\n'
            'supported_extensions = "smc|sfc|swc"\ncorename = "Snes9x"\n'
            'systemname = "Super Nintendo Entertainment System"\nsystemid = "super_nes"\n')
        (info / "semnada_libretro.info").write_text('systemid = "tamagotchi"\n')
        return {"ROMS_DIR": str(roms), "RA_INFO_DIR": str(info), "ATTRACT_DIR": str(attract),
                "RA_CORES_DIR": "/opt/fliperos/retroarch/cores", "FLIPEROS_USER": "ninguem",
                "MEDIA_DIR": str(self.env.dir / "media"), "ESDE_DIR": str(self.env.dir / "es-de"),
                "SCRAPER_MEDIA_STATE": str(self.env.dir / "scraper-media")}, roms, attract

    def test_detect_ignores_info_txt_and_finds_retroarch_cores(self):
        # O _info.txt de toda pasta contava como jogo: as vazias entravam e o
        # "All systems" parava na primeira.
        env, roms, _ = self.scraper_env()
        found = self.env.out("scraper_detect", env).splitlines()
        self.assertEqual(found, ["mame|%s/mame|arcade|2" % roms,
                                 "retroarch/snes9x|%s/retroarch/snes9x|snes|1" % roms])

    def test_flycast_arcade_folders_are_systems_of_their_own(self):
        # ~/roms/naomi, naomi2 e atomiswave (MAME ROM Cleaner): cada uma e um
        # sistema nos frontends, raspada pela plataforma dela e aberta no Flycast.
        env, roms, _ = self.scraper_env()
        for d, rom in (("naomi", "mvsc2.zip"), ("naomi2", "vf4.zip"), ("atomiswave", "kofxi.zip")):
            (roms / d).mkdir()
            (roms / d / "_info.txt").write_text("o que vai nesta pasta\n")
            (roms / d / rom).write_text("rom")
        found = self.env.out("scraper_detect", env).splitlines()
        for d in ("naomi", "naomi2", "atomiswave"):
            self.assertIn("%s|%s/%s|%s|1" % (d, roms, d, d), found)
        run = '/opt/fliperos/bin/fliperos-x11-run|flycast "[romfilename]"|.zip;.7z'
        self.assertEqual(self.env.out("scraper_attract_emulator naomi; scraper_attract_emulator naomi2; "
                                      "scraper_attract_emulator atomiswave", env).splitlines(),
                         ["Naomi|" + run, "Naomi 2|" + run, "Atomiswave|" + run])
        systems = [line.split("|")[3] for line in self.env.out("frontends_systems", env).splitlines()]
        self.assertEqual(systems[:4], ["Atomiswave", "MAME", "Naomi", "Naomi 2"])

    def test_model3_folder_opens_in_supermodel(self):
        # ~/roms/model3: raspada como arcade (o ScreenScraper nao tem Model 3).
        env, roms, _ = self.scraper_env()
        (roms / "model3").mkdir()
        (roms / "model3" / "vf3.zip").write_text("rom")
        self.assertIn("model3|%s/model3|arcade|1" % roms, self.env.out("scraper_detect", env).splitlines())
        self.assertEqual(self.env.out("scraper_attract_emulator model3", env).strip(),
                         'Supermodel|/opt/fliperos/bin/fliperos-x11-run|supermodel "[romfilename]"|.zip')

    def test_attract_mode_gets_emulator_and_display_once(self):
        env, roms, attract = self.scraper_env()
        for _ in range(2):
            name = self.env.out("scraper_attract_prepare retroarch/snes9x %s/retroarch/snes9x snes" % roms,
                                env).strip()
        self.assertEqual(name, "Super Nintendo Entertainment System (Snes9x)")
        cfg = (attract / "emulators" / (name + ".cfg")).read_text()
        self.assertRegex(cfg, r'(?m)^args +retroarch -L /opt/fliperos/retroarch/cores/snes9x_libretro\.so '
                              r'"\[romfilename\]"$')
        self.assertRegex(cfg, r'(?m)^romext +\.smc;\.sfc;\.swc$')
        # A arte em ~/media/<tipo>/<sistema>, e as descricoes (overview) num
        # link para ~/media/texto.
        media = self.env.dir / "media"
        self.assertIn("artwork    snap            %s/snap/snes;%s/preview/snes\n" % (media, media), cfg)
        self.assertIn("artwork    flyer           %s/box/snes\n" % media, cfg)
        self.assertIn("artwork    wheel           %s/logo/snes\n" % media, cfg)
        self.assertIn("artwork    marquee         %s/marquee/snes\n" % media, cfg)
        overview = attract / "scraper" / name / "overview"
        self.assertTrue(overview.is_symlink())
        self.assertEqual(overview.resolve(), (media / "texto" / "snes").resolve())
        for t in ("snap", "preview", "logo", "box", "marquee", "texto"):
            self.assertTrue((media / t / "snes").is_dir(), t)
        self.assertTrue((attract / "romlists").is_dir())
        acfg = (attract / "attract.cfg").read_text()
        self.assertEqual(acfg.count("display\t"), 1)
        self.assertIn("\tromlist              %s\n" % name, acfg)
        self.assertEqual(self.env.out("scraper_attract_prepare mame %s/mame arcade" % roms, env).strip(), "MAME")
        mame_cfg = (attract / "emulators" / "MAME.cfg").read_text()
        self.assertRegex(mame_cfg, r"(?m)^args +groovymame \[name\]$")
        self.assertRegex(mame_cfg, r"(?m)^executable +/opt/fliperos/bin/fliperos-x11-run$")
        self.assertNotEqual(self.env.run("scraper_attract_prepare outra /x pc", env).returncode, 0)

    def test_attract_mode_emulator_of_the_setup_moves_to_media(self):
        # Um .cfg do Setup de antes (arte em ~/.attract/scraped) e refeito; um
        # gravado pelo Attract-Mode fica; o overview que era pasta vai para
        # ~/media/texto.
        env, roms, attract = self.scraper_env()
        (attract / "emulators").mkdir(parents=True)
        (attract / "emulators" / "MAME.cfg").write_text(
            "# Criado pelo FliperOS Setup (Scraper).\nartwork    snap            /velho/snap;/velho/video\n")
        mine = "# Generated by Attract-Mode Plus\nartwork    snap            /meu/snap\n"
        snes = "Super Nintendo Entertainment System (Snes9x)"
        (attract / "emulators" / (snes + ".cfg")).write_text(mine)
        (attract / "scraper" / "MAME" / "overview").mkdir(parents=True)
        (attract / "scraper" / "MAME" / "overview" / "sf2.txt").write_text("Street Fighter II\n")
        self.env.out("scraper_attract_prepare mame %s/mame arcade" % roms, env)
        self.env.out("scraper_attract_prepare retroarch/snes9x %s/retroarch/snes9x snes" % roms, env)
        media = self.env.dir / "media"
        self.assertIn("%s/snap/arcade;%s/preview/arcade" % (media, media),
                      (attract / "emulators" / "MAME.cfg").read_text())
        self.assertEqual((attract / "emulators" / (snes + ".cfg")).read_text(), mine)
        self.assertTrue((attract / "scraper" / "MAME" / "overview").is_symlink())
        self.assertEqual((media / "texto" / "arcade" / "sf2.txt").read_text(), "Street Fighter II\n")

    def test_list_goes_where_the_frontend_reads(self):
        env, _, _ = self.scraper_env()
        (self.env.etc / "sessions.conf").write_text("attractplus|kms|attractplus|fliperos-attractplus|AM+\n"
                                                    "pegasus|kms|pegasus-fe|fliperos-pegasus|Pegasus\n")
        for session, key, expected in (("attractplus", "mame", "attractmode"), ("pegasus", "mame", "pegasus"),
                                       # O EmulationStation do FliperOS e o ES-DE.
                                       ("emulationstation", "mame", "esde"), ("setup", "mame", "esde"),
                                       # Com o GroovyMAME de launcher, a lista dele.
                                       ("groovymame", "mame", "mameui"),
                                       ("groovymame", "retroarch/snes9x", "esde")):
            (self.env.etc / "session").write_text(session + "\n")
            self.assertEqual(self.env.out("scraper_target %s" % key, env).strip(), expected, session)
        # Sem frontend, o Attract-Mode Plus se estiver instalado.
        (self.env.bin / "attractplus").write_text("#!/bin/sh\n")
        (self.env.bin / "attractplus").chmod(0o755)
        self.assertEqual(self.env.out("scraper_target retroarch/snes9x", env).strip(), "attractmode")

    def test_generate_writes_the_art_to_media(self):
        # O "gera" do Skyscraper de cada frontend: a arte pela pasta de links
        # de ~/media/.skyscraper/<sistema>, a lista onde o frontend le.
        env, roms, _ = self.scraper_env()
        env.update({"SCRAPER_JOB_DIR": str(self.env.dir / "job"), "SCRAPER_STAGE": str(self.env.dir / "stage")})
        (self.env.etc / "sessions.conf").write_text("pegasus|kms|pegasus-fe|fliperos-pegasus|Pegasus\n"
                                                    "emulationstation|kms|es-de|fliperos-emulationstation|ES-DE\n")
        log = self.fake_tools()
        media, esde = self.env.dir / "media", self.env.dir / "es-de"
        farm = media / ".skyscraper" / "snes"
        for session, gen in (
                ("pegasus", "-f pegasus -g %s/retroarch/snes9x -o %s -e " % (roms, farm)),
                ("emulationstation", "-f esde -g %s/gamelists/retroarch-snes9x -o %s" % (esde, farm))):
            (self.env.etc / "session").write_text(session + "\n")
            log.write_text("")
            self.env.out("scraper_run retroarch/snes9x %s/retroarch/snes9x snes screenscraper 0" % roms, env)
            line = [l for l in log.read_text().splitlines() if l.startswith("gera")][0]
            # -p continua o primeiro (o read do comando do Pegasus o trocava).
            self.assertTrue(line.startswith("gera -p snes -i %s/retroarch/snes9x --flags unattend" % roms), line)
            self.assertIn(gen, line)
        self.assertIn("--flags unattend,relative", line)
        for sub, kind in (("screenshots", "snap"), ("videos", "preview"), ("wheels", "logo"), ("covers", "box"),
                          ("marquees", "marquee")):
            self.assertEqual(os.readlink(farm / sub), "../../%s/snes" % kind)
            self.assertTrue((farm / sub).is_dir(), sub)
        # O ES-DE ganhou o sistema e le a arte de ~/media.
        settings = (esde / "settings" / "es_settings.xml").read_text()
        self.assertIn('<string name="MediaDirectory" value="%s/.es-de" />' % media, settings)

    def test_descriptions_go_to_media_texto(self):
        env, _, _ = self.scraper_env()
        lists = self.env.dir / "lists"
        lists.mkdir()
        (lists / "gamelist.xml").write_text(
            '<?xml version="1.0"?>\n<gameList>\n<game><path>./sf2.zip</path><name>SF2</name>'
            '<desc>Street Fighter II &amp; friends</desc></game>\n'
            '<game><path>./semdesc.zip</path><desc/></game>\n</gameList>\n')
        (lists / "metadata.pegasus.txt").write_text(
            "collection: SNES\n\ngame: Super Mario World\nfile: /r/Super Mario World (USA).sfc\n"
            "description: Mario and Luigi\n  go to Dinosaur Land.\n  .\n  Second paragraph.\n"
            "developer: Nintendo\n")
        self.env.out("scraper_texts %s/gamelist.xml arcade" % lists, env)
        self.env.out("scraper_texts %s/metadata.pegasus.txt snes" % lists, env)
        texto = self.env.dir / "media" / "texto"
        self.assertEqual((texto / "arcade" / "sf2.txt").read_text(), "Street Fighter II & friends\n")
        self.assertFalse((texto / "arcade" / "semdesc.txt").exists())
        self.assertEqual((texto / "snes" / "Super Mario World (USA).txt").read_text(),
                         "Mario and Luigi\ngo to Dinosaur Land.\n\nSecond paragraph.\n")

    def test_old_art_moves_to_media(self):
        # A arte de antes do ~/media: a da lista do GroovyMAME, a do
        # Attract-Mode e a da pasta das ROMs (EmulationStation/Pegasus), sem
        # sobrescrever o que ja esta em ~/media.
        env, roms, attract = self.scraper_env()
        env["MAME_SCRAPED"] = str(self.env.dir / "mame-scraped" / "mame")
        old = self.env.dir / "mame-scraped" / "mame"
        for sub in ("screenshots", "covers", "wheels"):
            (old / sub).mkdir(parents=True)
            (old / sub / "sf2.png").write_text("velho " + sub)
        (old / "gamelist.xml").write_text("<gameList/>")
        (roms / "retroarch" / "snes9x" / "media" / "videos").mkdir(parents=True)
        (roms / "retroarch" / "snes9x" / "media" / "videos" / "smw.mp4").write_text("video")
        (attract / "scraped" / "mame" / "marquee").mkdir(parents=True)
        (attract / "scraped" / "mame" / "marquee" / "sf2.png").write_text("marquee")
        media = self.env.dir / "media"
        (media / "logo" / "arcade").mkdir(parents=True)
        (media / "logo" / "arcade" / "sf2.png").write_text("novo")
        self.env.out("scraper_media_migrate", env)
        self.assertEqual((media / "snap" / "arcade" / "sf2.png").read_text(), "velho screenshots")
        self.assertEqual((media / "box" / "arcade" / "sf2.png").read_text(), "velho covers")
        self.assertEqual((media / "logo" / "arcade" / "sf2.png").read_text(), "novo")
        self.assertEqual((media / "preview" / "snes" / "smw.mp4").read_text(), "video")
        self.assertEqual((media / "marquee" / "arcade" / "sf2.png").read_text(), "marquee")
        self.assertFalse((old / "screenshots").exists())
        self.assertTrue((old / "wheels" / "sf2.png").exists())
        self.assertFalse((roms / "retroarch" / "snes9x" / "media").exists())
        self.assertFalse((attract / "scraped").exists())

    def fake_tools(self, fail_on=None):
        # runuser, groovymame -listclones e um Skyscraper que anota cada lote
        # (e falha no lote que tiver FAIL_ON, como um desligamento no meio).
        log = self.env.dir / "sky.log"
        tools = {
            "runuser": '#!/bin/sh\nshift 3\nexec "$@"\n',
            "groovymame": '#!/bin/sh\nprintf "Name:            Clone of:\\n'
                          'mvscu            mvsc\\nmvscj            mvsc\\nsf2ce            sf2\\n"\n',
            "Skyscraper": '#!/bin/bash\necho "$*" >> "%s.args"\nfor ((i = 1; i <= $#; i++)); do\n' % log +
                          '  [[ ${!i} == --includefrom ]] && { j=$((i + 1)); f=${!j}; }\ndone\n'
                          'if [[ -n $f ]]; then\n  printf "lote:%%s\\n" "$(xargs -n1 basename < "$f" | tr "\\n" " ")" >> "%s"\n'
                          '  [[ -n "%s" ]] && grep -q "%s" "$f" && exit 1\nelse\n  echo gera "$@" >> "%s"\nfi\n'
                          'exit 0\n' % (log, fail_on or "", fail_on or "", log),
        }
        for name, body in tools.items():
            (self.env.bin / name).write_text(body)
            (self.env.bin / name).chmod(0o755)
        return log

    def test_screen_passes_the_whole_line_of_one_system(self):
        # O ui_menu devolve so o que vem antes do primeiro "|": escolher um
        # sistema so (e nao "All systems") chegava ao Skyscraper sem pasta nem
        # plataforma ("-p '' -i ''").
        env, roms, _ = self.scraper_env()
        env.update({"SKYSCRAPER": "true", "PICK": "retroarch/snes9x"})
        out = self.env.out("""
            source %s/screens/setup-menu.sh
            ui_menu() {
              [[ $2 == Where* ]] && { echo screenscraper; return; }
              shift 3
              printf 'opcao:%%s\\n' "$@" >&2
              echo "$PICK"
            }
            ui_input() { :; }
            ui_checklist() { echo snap; }
            ui_yesno() { return 1; }
            scraper_scrape_targets() { shift 4; printf 'alvo:%%s\\n' "$@"; }
            screen_scraper
        """ % SETUP, env)
        self.assertEqual(out.splitlines(), ["alvo:retroarch/snes9x|%s/retroarch/snes9x|snes|1" % roms])

    def test_progettosnaps_saves_screenshots_and_the_attract_list(self):
        # Sem Skyscraper: o fliperos-snaps grava as capturas em ~/media/snap e
        # o Attract-Mode ganha o emulador e a tela da pasta. So pasta de arcade.
        env, roms, attract = self.scraper_env()
        (roms / "mame" / "kof98.zip").write_text("rom")
        args = self.env.dir / "snaps.args"
        self.env.stub("fliperos-snaps", 'echo "$*" > %s\n'
                      'while (($#)); do case $1 in --dest) d=$2;; --names) n=$2;; --result) r=$2;; esac; shift; done\n'
                      'cp "$n" %s.names; mkdir -p "$d"; touch "$d/sf2.png"\n'
                      'printf "found=1\\nkept=0\\nmissing=1\\n" > "$r"; echo "@step 95 Screenshots saved"' % (args, args))
        (self.env.etc / "sessions.conf").write_text("attractplus|kms|attractplus|fliperos-attractplus|Attract-Mode Plus\n")
        (self.env.etc / "session").write_text("attractplus\n")
        env.update({"SNAPS": str(self.env.bin / "fliperos-snaps"), "SNAPS_CACHE": str(self.env.dir / "cache"),
                    "ATTRACTPLUS": "false", "SKYSCRAPER": "nao-existe"})
        out = self.env.out("scraper_run mame %s/mame arcade progettosnaps snap '' 0" % roms, env)
        self.assertIn("--cache %s/cache" % self.env.dir, args.read_text())
        self.assertEqual(Path(str(args) + ".names").read_text().split(), ["kof98", "sf2"])
        self.assertTrue((self.env.dir / "media/snap/arcade/sf2.png").exists())
        self.assertIn("@msg 1 screenshots saved, 0 already there, 1 not in progetto-SNAPS", out)
        self.assertIn("@step 100 arcade: done", out)
        self.assertTrue((attract / "emulators" / "MAME.cfg").exists())
        self.assertIn("romlist              MAME", (attract / "attract.cfg").read_text())
        r = self.env.run("scraper_run retroarch/snes9x %s/retroarch/snes9x snes progettosnaps snap" % roms, env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("@fail", r.stdout)

    def test_job_is_recorded_and_finished(self):
        env, roms, _ = self.scraper_env()
        env["SCRAPER_JOB_DIR"] = str(self.env.dir / "job")
        self.env.out("scraper_job_start screenscraper 0 1 'eu:segredo' 'mame|/r/mame|arcade|2' "
                     "'retroarch/snes9x|/r/snes|snes|1'", env)
        job = self.env.dir / "job"
        self.assertEqual(oct((job / "options").stat().st_mode & 0o777), "0o600")
        self.assertEqual((job / "options").read_text(), "screenscraper|0|1|eu:segredo\n")
        self.env.out("scraper_job_done mame", env)
        self.assertEqual(self.env.out("scraper_job_pending", env), "retroarch/snes9x|/r/snes|snes|1\n")
        self.env.out("scraper_job_done retroarch/snes9x", env)
        self.assertFalse(job.exists())

    def test_media_types_to_fetch(self):
        # Os tipos marcados na tela viram as flags do Skyscraper (so baixa o
        # que foi marcado) e o artwork.xml (so exporta o que foi marcado).
        env, roms, _ = self.scraper_env()
        env.update({"SCRAPER_STAGE": str(self.env.dir / "stage")})
        for media, flags in (("snap,logo,box,marquee,texto", "unattend"),
                             ("snap,logo,box,marquee,texto,preview", "unattend,videos"),
                             ("snap", "unattend,nocovers,nowheels,nomarquees"),
                             ("logo,preview", "unattend,videos,noscreenshots,nocovers,nomarquees"),
                             ("none", "unattend,noscreenshots,nocovers,nowheels,nomarquees")):
            self.assertEqual(self.env.out("scraper_media_flags %s" % media).strip(), flags, media)
        options = self.env.out("scraper_media_options").splitlines()
        self.assertEqual([o.split("|")[0] for o in options], ["snap", "logo", "box", "marquee", "texto", "preview"])
        # Sem escolha guardada: tudo menos os videos. Um trabalho anotado antes
        # (videos 0 ou 1) continua valendo.
        self.assertEqual(self.env.out("scraper_media_saved; scraper_media_list 0; scraper_media_list 1; "
                                      "scraper_media_list snap,box").split(),
                         ["snap,logo,box,marquee,texto", "snap,logo,box,marquee,texto",
                          "snap,logo,box,marquee,texto,preview", "snap,box"])
        self.env.out("conf_set scraper_media logo,preview")
        self.assertEqual(self.env.out("scraper_media_saved").strip(), "logo,preview")
        art = Path(self.env.out("scraper_artwork snap,logo", env).strip()).read_text()
        self.assertEqual(re.findall(r'<output type="(\w+)"/>', art), ["screenshot", "wheel"])
        art = Path(self.env.out("scraper_artwork", env).strip()).read_text()
        self.assertEqual(re.findall(r'<output type="(\w+)"/>', art), ["screenshot", "cover", "wheel", "marquee"])
        screen = (SETUP / "screens" / "setup-menu.sh").read_text().split("screen_scraper() {")[1].split("\n}\n")[0]
        self.assertIn('media=$(ui_checklist "Scraper: Media"', screen)
        self.assertIn('conf_set scraper_media "$media"', screen)
        self.assertNotIn("Download videos too", screen)

    def test_new_media_type_fetches_cached_games_again(self):
        # O Skyscraper nao volta a um jogo que ja esta no cache: um tipo de
        # arte que a pasta ainda nao tinha pede o --refresh; o que ela ja tem
        # fica anotado por pasta.
        env, roms, _ = self.scraper_env()
        env.update({"SCRAPER_JOB_DIR": str(self.env.dir / "job"), "SCRAPER_STAGE": str(self.env.dir / "stage")})
        (self.env.etc / "sessions.conf").write_text("emulationstation|kms|es-de|fliperos-emulationstation|ES-DE\n")
        (self.env.etc / "session").write_text("emulationstation\n")
        log = self.fake_tools()
        args = Path(str(log) + ".args")
        run = "scraper_job_clear; scraper_run retroarch/snes9x %s/retroarch/snes9x snes screenscraper %%s" % roms

        def gather(media):
            args.write_text("")
            self.env.out(run % media, env)
            return [line for line in args.read_text().splitlines() if "--includefrom" in line][0]
        first = gather("snap,logo,box,marquee,texto")
        self.assertIn("--flags unattend,relative ", first)
        self.assertNotIn("--refresh", first)
        second = gather("snap,preview")
        self.assertIn("--flags unattend,videos,nocovers,nowheels,nomarquees,relative ", second)
        self.assertTrue(second.endswith("--refresh"), second)
        # Os videos ja estao na pasta: de novo sem o --refresh, mesmo voltando
        # a marcar um tipo que ela ja teve.
        self.assertNotIn("--refresh", gather("snap,logo,preview"))
        state = (self.env.dir / "scraper-media").read_text()
        self.assertEqual(state, "retroarch/snes9x=snap,logo,box,marquee,texto,preview\n")
        self.assertEqual(self.env.out("scraper_media_fetched mame", env).strip(), "snap,logo,box,marquee,texto")

    def test_batches_resume_and_clones(self):
        env, roms, attract = self.scraper_env()
        for g in ("mvsc", "sf2", "kof98", "pacman"):
            (roms / "mame" / (g + ".zip")).write_text(g)
        env.update({"SCRAPER_JOB_DIR": str(self.env.dir / "job"), "SCRAPER_CHUNK": "3",
                    "SCRAPER_STAGE": str(self.env.dir / "stage"), "MAME_SCRAPED": str(self.env.dir / "scraped"),
                    "MAME_INI": str(self.env.etc / "mame.ini")})
        (self.env.etc / "session").write_text("groovymame\n")
        log = self.fake_tools(fail_on="pacman")
        # 4 jogos + 3 clones dos que existem, em lotes de 3; o segundo lote
        # (com o pacman) "cai".
        r = self.env.run("scraper_run mame %s/mame arcade arcadedb 0 '' 1" % roms, env)
        self.assertNotEqual(r.returncode, 0)
        lots = log.read_text().splitlines()
        self.assertEqual(lots[0], "lote:kof98.zip mvsc.zip mvscj.zip ")
        self.assertIn("pacman.zip", lots[1])
        self.assertFalse(any(l.startswith("gera") for l in lots))
        stage = self.env.dir / "stage" / "mame"
        self.assertTrue((stage / "mvsc.zip").is_symlink())
        self.assertIn("clone de mvsc", (stage / "mvscu.zip").read_text())
        self.assertFalse((stage / "kof98u.zip").exists())
        # Retomando: so o que faltou, e depois a lista do GroovyMAME.
        log.write_text("")
        self.fake_tools()
        self.env.out("scraper_run mame %s/mame arcade arcadedb 0 '' 1" % roms, env)
        lots = log.read_text().splitlines()
        self.assertEqual(lots[0], "lote:mvscu.zip pacman.zip sf2.zip ")
        self.assertEqual(lots[1], "lote:sf2ce.zip ")
        farm = self.env.dir / "media" / ".skyscraper" / "arcade"
        self.assertIn("-f emulationstation -g %s -o %s" % (farm, farm), lots[2])


class FrontendsTests(Base):
    """lib/frontends.sh: as pastas de ~/roms e o comando de cada uma no
    Pegasus e no ES-DE, os mesmos do Attract-Mode."""

    def frontends_env(self):
        env, roms, _ = ScraperTests.scraper_env(self)
        env.update(PEGASUS_DIR=str(self.env.dir / "pegasus"), ESDE_DIR=str(self.env.dir / "es-de"),
                   FLIPEROS_BIN="/opt/fliperos/bin")
        return env, roms

    def themes_240p(self, env):
        """Os temas do FliperOS instalados; devolve a pasta do tema do Pegasus."""
        pegasus = self.env.dir / "themes" / "fliperos-240p"
        esde = self.env.dir / "themes" / "fliperos-240p-es-de"
        pegasus.mkdir(parents=True)
        esde.mkdir(parents=True)
        (pegasus / "theme.qml").write_text("import QtQuick 2.7\n")
        (esde / "theme.xml").write_text("<theme></theme>\n")
        env.update(PEGASUS_THEME=str(pegasus), ESDE_THEME=str(esde))
        return pegasus

    def test_pegasus_collections_and_launch(self):
        env, roms = self.frontends_env()
        self.env.out("frontends_configure pegasus", env)
        mame = (roms / "mame" / "metadata.pegasus.txt").read_text()
        self.assertIn("collection: MAME\n", mame)
        self.assertIn("extensions: zip, 7z\n", mame)
        self.assertIn("launch: /opt/fliperos/bin/fliperos-x11-run groovymame {file.basename}\n", mame)
        snes = (roms / "retroarch" / "snes9x" / "metadata.pegasus.txt").read_text()
        self.assertIn('launch: /opt/fliperos/bin/fliperos-kms-run retroarch -L '
                      '/opt/fliperos/retroarch/cores/snes9x_libretro.so "{file.path}"\n', snes)
        dirs = (self.env.dir / "pegasus" / "game_dirs.txt").read_text().split()
        self.assertEqual(dirs, ["%s/mame" % roms, "%s/retroarch/snes9x" % roms])
        # Um metadata do Skyscraper (com os jogos) fica; so ganha o launch.
        (roms / "mame" / "metadata.pegasus.txt").write_text("collection: Arcade\n\ngame: Street Fighter II\n")
        self.env.out("frontends_configure pegasus", env)
        self.assertEqual((roms / "mame" / "metadata.pegasus.txt").read_text(),
                         "collection: Arcade\nlaunch: /opt/fliperos/bin/fliperos-x11-run groovymame {file.basename}\n"
                         "\ngame: Street Fighter II\n")

    def test_esde_systems_and_rom_folder(self):
        env, roms = self.frontends_env()
        self.env.out("frontends_configure emulationstation", env)
        import xml.etree.ElementTree as ET
        systems = ET.parse(self.env.dir / "es-de" / "custom_systems" / "es_systems.xml").getroot()
        by_name = {s.findtext("name"): s for s in systems.iter("system")}
        self.assertEqual(sorted(by_name), ["mame", "retroarch-snes9x"])
        mame = by_name["mame"]
        self.assertEqual(mame.findtext("command"), "/opt/fliperos/bin/fliperos-x11-run groovymame %BASENAME%")
        self.assertEqual(mame.findtext("extension"), ".zip .7z .ZIP .7Z")
        self.assertEqual(mame.findtext("theme"), "arcade")
        self.assertEqual(by_name["retroarch-snes9x"].findtext("command"),
                         "/opt/fliperos/bin/fliperos-kms-run retroarch -L "
                         "/opt/fliperos/retroarch/cores/snes9x_libretro.so %ROM%")
        settings = (self.env.dir / "es-de" / "settings" / "es_settings.xml").read_text()
        self.assertIn('<string name="ROMDirectory" value="%s" />' % roms, settings)
        # A arte: <MediaDirectory>/<sistema>/<tipo do ES-DE> -> ~/media/<tipo>/<plataforma>.
        media = self.env.dir / "media"
        self.assertIn('<string name="MediaDirectory" value="%s/.es-de" />' % media, settings)
        self.assertEqual(os.readlink(media / ".es-de" / "mame" / "marquees"), "../../logo/arcade")
        self.assertEqual(os.readlink(media / ".es-de" / "retroarch-snes9x" / "screenshots"), "../../snap/snes")
        self.assertTrue((media / ".es-de" / "retroarch-snes9x" / "videos").is_dir())
        # Rodar de novo troca o valor, sem repetir a opcao.
        self.env.out("frontends_configure emulationstation", env)
        settings = (self.env.dir / "es-de" / "settings" / "es_settings.xml").read_text()
        self.assertEqual(settings.count('name="MediaDirectory"'), 1)

    def test_attract_mode_screens_get_a_game_list(self):
        # Uma tela sem lista ganha a que o proprio Attract-Mode monta da pasta
        # (--build-romlist, como o usuario); a que ja existe (do Scraper) fica.
        env, roms = self.frontends_env()
        attract = self.env.dir / "attract"
        calls = self.env.dir / "attractplus.calls"
        self.env.stub("runuser", 'echo "runuser $1 $2" >> "%s"; shift 3; exec "$@"' % calls)
        self.env.stub("attractplus", 'echo "$*" >> "%s"' % calls)
        (attract / "romlists").mkdir(parents=True)
        (attract / "romlists" / "MAME.txt").write_text("#Name;Title\nsf2;Street Fighter II\n")
        self.env.out("frontends_configure attractplus", env)
        snes = "Super Nintendo Entertainment System (Snes9x)"
        self.assertEqual(calls.read_text().splitlines(),
                         ["runuser -u ninguem", "--build-romlist %s -o %s" % (snes, snes)])
        self.assertTrue((attract / "emulators" / "MAME.cfg").exists())

    def test_240p_settings_are_saved_once_on_a_15khz_monitor(self):
        # Num tubo de 15 kHz os frontends rodam em 320x240: o tema FliperOS
        # 240p de cada um ja fica escolhido, uma vez so; o que a pessoa mudar
        # depois no proprio frontend fica.
        env, roms = self.frontends_env()
        theme = self.themes_240p(env)
        self.env.stub("pgrep", "exit 1")
        settings = self.env.dir / "es-de" / "settings" / "es_settings.xml"
        settings.parent.mkdir(parents=True)
        # O arquivo que o ES-DE grava na primeira vez, com os padroes dele.
        settings.write_text('<?xml version="1.0"?>\n<bool name="MenuBlurBackground" value="true" />\n'
                            '<string name="Theme" value="slate-es-de" />\n<string name="ThemeFontSize" value="medium" />\n'
                            '<string name="ThemeVariant" value="withVideos" />\n')
        peg = self.env.dir / "pegasus" / "settings.txt"
        # Monitor LCD (ou ainda nao escolhido): os padroes de cada frontend ficam.
        self.env.out("frontends_configure emulationstation; frontends_configure pegasus", env)
        self.assertIn('<string name="Theme" value="slate-es-de" />', settings.read_text())
        self.assertFalse(peg.exists())
        self.env.out("conf_set frequency 15k; frontends_configure emulationstation; frontends_configure pegasus", env)
        text = settings.read_text()
        for line in ('<string name="Theme" value="fliperos-240p-es-de" />',
                     '<string name="ThemeAspectRatio" value="automatic" />',
                     '<bool name="MenuBlurBackground" value="false" />',
                     '<string name="ApplicationUpdaterFrequency" value="never" />'):
            self.assertEqual(text.count(line), 1, line)
        self.assertEqual(text.count('name="Theme"'), 1)
        self.assertEqual(peg.read_text(), "general.theme: %s/\ngeneral.fullscreen: true\n"
                                          "general.input-mouse-support: false\n" % theme)
        # A pessoa troca o tema no frontend: a vez seguinte nao mexe.
        settings.write_text(text.replace("fliperos-240p-es-de", "modern-es-de"))
        peg.write_text("general.theme: :/themes/pegasus-theme-grid/\ngeneral.fullscreen: true\n")
        self.env.out("frontends_configure emulationstation; frontends_configure pegasus", env)
        self.assertIn('<string name="Theme" value="modern-es-de" />', settings.read_text())
        self.assertEqual(peg.read_text(), "general.theme: :/themes/pegasus-theme-grid/\ngeneral.fullscreen: true\n")
        conf = (self.env.etc / "fliperos.conf").read_text()
        self.assertIn("esde_240p=1\n", conf)
        self.assertIn("pegasus_240p=1\n", conf)

    def test_240p_settings_wait_while_the_frontend_is_open(self):
        # O frontend regrava o arquivo dele ao fechar: aberto, fica para depois.
        env, roms = self.frontends_env()
        self.themes_240p(env)
        self.env.stub("pgrep", "exit 0")
        self.env.out("conf_set frequency 15k; frontends_configure emulationstation", env)
        settings = (self.env.dir / "es-de" / "settings" / "es_settings.xml").read_text()
        self.assertNotIn('name="Theme"', settings)
        self.assertIn('name="ROMDirectory"', settings)
        self.assertNotIn("esde_240p", (self.env.etc / "fliperos.conf").read_text())

    def test_240p_settings_need_the_theme_installed(self):
        # Sem o tema na pasta do frontend nada e escolhido (nem anotado): o
        # frontend abriria com um tema que nao existe.
        env, roms = self.frontends_env()
        env.update(PEGASUS_THEME=str(self.env.dir / "nenhum"), ESDE_THEME=str(self.env.dir / "nenhum"))
        self.env.stub("pgrep", "exit 1")
        self.env.out("conf_set frequency 15k; frontends_configure emulationstation; frontends_configure pegasus", env)
        self.assertNotIn('name="Theme"', (self.env.dir / "es-de" / "settings" / "es_settings.xml").read_text())
        self.assertFalse((self.env.dir / "pegasus" / "settings.txt").exists())
        conf = (self.env.etc / "fliperos.conf").read_text()
        self.assertNotIn("esde_240p", conf)
        self.assertNotIn("pegasus_240p", conf)

    def test_pending_240p_settings_are_saved_before_a_launcher_opens(self):
        # fliperos-setup --session-start (antes de abrir um launcher, com
        # nenhum frontend aberto): so os instalados, e a pasta fica do usuario.
        env, roms = self.frontends_env()
        self.themes_240p(env)
        self.env.stub("pgrep", "exit 1")
        (self.env.etc / "sessions.conf").write_text("emulationstation|kms|emulationstation|fliperos-emulationstation|ES\n"
                                                    "pegasus|kms|pegasus-fe|fliperos-pegasus|Pegasus\n")
        self.env.stub("pegasus-fe", "exit 0")
        self.env.out("conf_set frequency 15k; frontends_240p", env)
        self.assertTrue((self.env.dir / "pegasus" / "settings.txt").exists())
        self.assertFalse((self.env.dir / "es-de").exists())   # o ES-DE nao esta instalado
        self.env.stub("emulationstation", "exit 0")
        self.env.out("frontends_240p", env)
        self.assertIn('<string name="Theme" value="fliperos-240p-es-de" />',
                      (self.env.dir / "es-de" / "settings" / "es_settings.xml").read_text())
        main = (SETUP / "fliperos-setup").read_text()
        self.assertIn("latency_session_start\n      # A configuracao de 240p", main)
        self.assertIn("      frontends_240p\n      return 0", main)
        self.assertIn("  frontends_240p\n", (ROOT / "tools/cabinet-update.sh").read_text())

    def test_chosen_frontend_is_configured(self):
        menu = (SETUP / "screens" / "setup-menu.sh").read_text().split("screen_frontend() {")[1].split("\n}\n")[0]
        self.assertLess(menu.index('launcher_set "$choice"'), menu.index('frontends_configure "$choice"'))
        kms = (ROOT / "config/fliperos-kms-run").read_text()
        self.assertIn('export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-eglfs}"', kms)
        scraper = (SETUP / "lib" / "scraper.sh").read_text()
        self.assertIn('-e "$(frontends_pegasus_launch "$exe $cmd")"', scraper)


class MenuSoundsTests(Base):
    """Sons do menu (lib/audio.sh e ui_sounds): os WAV da pessoa no gum."""

    def setUp(self):
        super().setUp()
        self.dir = self.env.dir / "sounds"
        self.dir.mkdir()
        self.vars = {"MENU_SOUNDS_DIR": str(self.dir)}

    def sounds(self):
        script = 'source %s/lib/ui.sh; ui_sounds; echo "$(menu_sounds_label)|${GUM_SOUND_MOVE:-}|${GUM_SOUND_SELECT:-}"'
        return self.env.out(script % SETUP, self.vars).strip()

    def test_on_when_the_files_are_there(self):
        self.assertEqual(self.sounds(), "no sound files||")
        (self.dir / "select.wav").write_bytes(b"RIFF")
        self.assertEqual(self.sounds(), "on||%s/select.wav" % self.dir)
        (self.dir / "move.wav").write_bytes(b"RIFF")
        self.assertEqual(self.sounds(), "on|%s/move.wav|%s/select.wav" % (self.dir, self.dir))

    def test_turned_off_in_the_setup(self):
        (self.dir / "move.wav").write_bytes(b"RIFF")
        self.env.out("menu_sounds_set off", self.vars)
        self.assertEqual(self.sounds(), "off||")
        self.env.out("menu_sounds_set on", self.vars)
        self.assertEqual(self.sounds(), "on|%s/move.wav|" % self.dir)

    def test_in_the_audio_setup(self):
        menu = (SETUP / "screens" / "setup-menu.sh").read_text()
        self.assertIn('"sounds|Menu sounds ($(menu_sounds_label))"', menu)
        self.assertIn("ui_sounds", (SETUP / "lib" / "ui.sh").read_text().split("ui_init() {")[1].split("\n}\n")[0])


def load_engine():
    """O config/fliperos-romclean como modulo (nao tem extensao .py)."""
    import importlib.machinery
    import importlib.util
    loader = importlib.machinery.SourceFileLoader("romclean", str(ROOT / "config/fliperos-romclean"))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader("romclean", loader))
    loader.exec_module(module)
    return module


class RomCleanerTests(Base):
    """lib/romclean.sh: o Setup > MAME ROM Cleaner (config/fliperos-romclean)."""

    XML = ('<mame build="0.289">'
           '<machine name="neogeo" isbios="yes"><description>Neo-Geo</description></machine>'
           '<machine name="mslug" romof="neogeo"><description>Metal Slug</description><year>1996</year>'
           '<input players="2" coins="1"><control type="joy" buttons="4"/></input><driver status="good"/></machine>'
           '<machine name="mslugb" cloneof="mslug" romof="mslug"><description>Metal Slug (bootleg)</description>'
           '<year>1996</year><input players="2" coins="1"><control type="joy" buttons="4"/></input>'
           '<driver status="good"/></machine>'
           '<machine name="cent"><description>Centipede</description><year>1980</year>'
           '<input players="2" coins="1"><control type="trackball" buttons="1"/></input>'
           '<driver status="good"/></machine>'
           '<machine name="naomi" isbios="yes"><description>Naomi BIOS</description></machine>'
           '<machine name="mvsc2" romof="naomi"><description>Marvel Vs. Capcom 2</description><year>2000</year>'
           '<input players="2" coins="1"><control type="joy" buttons="6"/></input>'
           '<driver status="preliminary"/></machine>'
           '<machine name="awbios" isbios="yes"><description>Atomiswave BIOS</description></machine>'
           '<machine name="kofxi" romof="awbios"><description>The King of Fighters XI</description>'
           '<year>2005</year><input players="2" coins="1"><control type="joy" buttons="5"/></input>'
           '<driver status="imperfect"/></machine></mame>')
    SETS = ("neogeo", "mslug", "mslugb", "cent", "naomi", "mvsc2", "awbios", "kofxi")

    def setUp(self):
        super().setUp()
        self.full = self.env.dir / "romsets" / "full"
        self.full.mkdir(parents=True)
        for name in self.SETS:
            (self.full / (name + ".zip")).write_bytes(b"x" * 1536)
        self.xml = self.env.dir / "listxml.xml"
        self.xml.write_text(self.XML)
        # O -listxml fica anotado: com o cache, so roda uma vez.
        self.env.stub("groovymame", 'case "$1" in -listxml) echo x >> "%s/listxml.calls"; cat "%s" ;; '
                                    '-version) echo "0.289 (GroovyMAME 0.289.222f)" ;; esac'
                      % (self.env.dir, self.xml))
        self.env.stub("fliperos-romclean", 'exec python3 %s "$@"' % (ROOT / "config/fliperos-romclean"))
        self.roms = self.env.dir / "roms"
        self.vars = {"ROMCLEAN": str(self.env.bin / "fliperos-romclean"),
                     "MAME2010_XML": str(self.env.dir / "mame2010.xml.xz"),
                     "ROMS_ROOT": str(self.roms), "BIOS_ROOT": str(self.env.dir / "bios"),
                     "ROMCLEAN_CACHE": str(self.env.dir / "cache"), "ROMCLEAN_DATA": str(self.env.dir / "data")}

    def test_downloader_filter_is_a_romclean_command(self):
        # Setup > Downloader > Filter: o filtro salvo vira as opcoes do
        # fliperos-romclean, e o downloader as usa sobre a lista do torrent.
        state = self.env.dir / "dl"
        env = dict(self.vars, DOWNLOADER_STATE=str(state), FLIPEROS_USER="ninguem")
        (self.env.dir / "torrent.list").write_text("".join("%s.zip\t1536\n" % n for n in self.SETS))
        out = self.env.out("""
            romclean_data_load "$ROMCLEAN_DATA"
            mapfile -t kv < <(romclean_preset cabinet flycast)
            downloader_filter_save flycast %s cabinet "${kv[@]}"
            downloader_filter_label
            downloader_filter_get target
            mapfile -t args < "$DOWNLOADER_STATE/filter.scan"
            "$ROMCLEAN" scan "${args[@]}" --roms /nao/baixado --names %s --plan %s > /dev/null
        """ % (self.roms, self.env.dir / "torrent.list", self.env.dir / "dl.plan"), env).splitlines()
        self.assertEqual(out, ["Joystick cabinet (2 players, 6 buttons), Flycast (Naomi, Naomi 2, Atomiswave)",
                               "flycast"])
        chds = (state / "filter.chds").read_text().splitlines()
        self.assertEqual(chds[-4:], ["--roms", "%s/naomi" % self.roms, "--roms", "%s/naomi2" % self.roms])
        self.assertIn("--xml-command", chds)
        rows = [line.split("\t") for line in (self.env.dir / "dl.plan").read_text().splitlines()
                if line.startswith("move")]
        self.assertEqual(sorted((r[2], Path(r[5]).name) for r in rows),
                         [("awbios.zip", "dc"), ("kofxi.zip", "atomiswave"), ("mvsc2.zip", "naomi"),
                          ("naomi.zip", "dc")])

    def downloader_screen(self, script, status="pct=0\nstate=none\nline=x\n", diff=""):
        state = self.env.dir / "dl"
        state.mkdir(exist_ok=True)
        calls = self.env.dir / "dl.calls"
        self.env.stub("fliperos-downloader", 'echo "$*" >> %s\ncase $1 in status) printf "%%b" "%s" ;; '
                      'diff) printf "%%b" "%s" ;; esac'
                      % (calls, status.replace("\n", "\\n"), diff.replace("\t", "\\t").replace("\n", "\\n")))
        self.env.stub("systemctl", 'echo "systemctl $*" >> %s' % calls)
        env = dict(self.vars, DOWNLOADER_STATE=str(state), DOWNLOADER=str(self.env.bin / "fliperos-downloader"),
                   FLIPEROS_USER="ninguem")
        r = self.env.run("""
            source %s/lib/ui.sh
            source %s/screens/progress.sh
            source %s/screens/rom-cleaner.sh
            source %s/screens/downloader.sh
            ui_msg() { printf 'msg:%%s\\n' "$*"; }
            ui_info() { :; }
            ui_yesno() { return 1; }
            ui_pager() { :; }
            run_with_progress() { shift 2; "$@" > /dev/null; }
        """ % (SETUP, SETUP, SETUP, SETUP) + script, env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout + r.stderr, calls.read_text() if calls.exists() else "", state

    def test_downloader_magnet_warns_about_the_filter(self):
        out, calls, state = self.downloader_screen("""
            ui_input() { echo ' magnet:?xt=urn:btih:abc&dn=MAME '; }
            screen_downloader_magnet roms
            ui_input() { echo 'http://site/romset.torrent'; }
            screen_downloader_magnet chds
        """)
        self.assertIn("The MAME ROM Cleaner filter will be used: only the ROMs of the games the filter chooses", out)
        self.assertIn("starts with the Joystick cabinet (2 players, 6 buttons) preset", out)
        self.assertIn("add roms magnet:?xt=urn:btih:abc&dn=MAME --progress", calls)
        self.assertIn("systemctl enable --now fliperos-transmission.service", calls)
        self.assertIn("msg:Downloader That is not a magnet link.", re.sub(r"\x1b\[[0-9;]*m", "", out))
        self.assertNotIn("add chds", calls)
        kv = (state / "filter.kv").read_text()
        self.assertIn("target=groovymame\n", kv)
        self.assertIn("preset=cabinet\n", kv)

    def test_torrent_menu_filter_first_and_the_rom_link_is_required(self):
        # A ordem: filtro, link das ROMs, link dos CHDs, pasta, comecar. Sem o
        # link das ROMs (so o dos CHDs) o Start nao comeca.
        # O ui_menu roda num $(...): a contagem fica num arquivo.
        out, calls, _ = self.downloader_screen("""
            ui_menu() {
              echo x >> "$DOWNLOADER_STATE/menus"
              [[ $(wc -l < "$DOWNLOADER_STATE/menus") == 1 ]] || return 1
              printf 'item:%s\\n' "${@:4}" >&2
              echo start
            }
            screen_downloader_start() { echo "start:$*"; }
            screen_downloader
        """, status="pct=0\\nstate=none\\nline=x\\nchds_name=MAME CHDs\\n")
        plain = re.sub(r"\x1b\[[0-9;]*m", "", out)
        items = [line.split("|")[0] for line in plain.splitlines() if line.startswith("item:")]
        self.assertEqual(items, ["item:filter", "item:roms", "item:chds", "item:dest", "item:start", "item:return"])
        self.assertIn("ROM set magnet link (required): not set", plain)
        self.assertIn("CHD set magnet link (optional): MAME CHDs", plain)
        self.assertIn("msg:ROM/CHD MAME torrent The ROM set magnet link is required.", plain)
        self.assertNotIn("start:", out)
        # Com ele, comeca.
        out, _, _ = self.downloader_screen("""
            rm -f "$DOWNLOADER_STATE/menus"
            ui_menu() {
              echo x >> "$DOWNLOADER_STATE/menus"
              [[ $(wc -l < "$DOWNLOADER_STATE/menus") == 1 ]] || return 1
              echo start
            }
            screen_downloader_start() { echo "start:$*"; }
            screen_downloader
        """, status="pct=0\\nstate=none\\nline=x\\nroms_name=MAME ROMs\\n")
        self.assertIn("start:", out)

    def test_download_folder_keeps_the_filter(self):
        out, _, state = self.downloader_screen("""
            ui_browse() { echo /mnt/disco/mame; }
            screen_downloader_dest
            downloader_dest
            downloader_dest_label
        """)
        self.assertIn("/mnt/disco/mame\n/mnt/disco/mame\n", out)
        kv = (state / "filter.kv").read_text()
        self.assertIn("dest=/mnt/disco/mame\n", kv)
        self.assertIn("preset=cabinet\n", kv)
        scan = (state / "filter.scan").read_text().splitlines()
        self.assertEqual(scan[scan.index("--dest") + 1], "/mnt/disco/mame")
        self.assertEqual((state / "filter.chds").read_text().splitlines()[-2:], ["--roms", "/mnt/disco/mame"])
        # Fora de ~/roms/mame as BIOS vao com os jogos.
        self.assertNotIn("--bios-dest", scan)

    def test_downloader_warns_what_the_new_filter_adds_and_deletes(self):
        diff = "roms\tadd\t2\t2048\nroms\tremove\t1\t10\nchds\tadd\t0\t0\nchds\tremove\t1\t300\n"
        out, calls, state = self.downloader_screen("""
            touch "$DOWNLOADER_STATE/roms.plan"
            ui_menu() { printf 'menu:%s\\n' "$2" >&2; echo apply; }
            screen_downloader_start() { echo "start:$*"; }
            screen_downloader_changes
        """, diff=diff)
        plain = re.sub(r"\x1b\[[0-9;]*m", "", out)
        self.assertIn("The filter changed", plain)
        self.assertRegex(plain, r"ROMs to add:\s+2 \(2.0 KB to download\)")
        self.assertRegex(plain, r"ROMs to delete:\s+1 \(10 B freed\)")
        self.assertRegex(plain, r"CHDs to delete:\s+1 \(300 B freed\)")
        self.assertNotIn("CHDs to add", plain)
        self.assertIn("start:prune", out)
        self.assertIn("diff --list", calls)
        # Sem plano aplicado (nenhum download ainda), nada a avisar.
        (state / "roms.plan").unlink()
        out, _, _ = self.downloader_screen("""
            ui_menu() { echo "menu"; }
            screen_downloader_changes
        """, diff=diff)
        self.assertEqual(out, "")

    SCAN = """
        romclean_data_load %(full)s
        mapfile -t kv < <(romclean_preset cabinet %(target)s)
        mapfile -t args < <(romclean_args %(target)s "${kv[@]}")
        plan=%(plan)s
        s=$(romclean_scan %(full)s %(target)s "" "$(romclean_default_dest %(target)s)" "$plan" "${args[@]}")
        echo "move=$(romclean_value "$s" move) rest=$(romclean_value "$s" rest) bytes=$(romclean_value "$s" rest_bytes)"
    """

    def scan(self, target="groovymame", then=""):
        return self.env.out(self.SCAN % {"full": self.full, "target": target, "plan": self.env.dir / "plan"} + then,
                            self.vars).splitlines()

    def test_cabinet_preset_copies_and_the_romset_stays(self):
        lines = self.scan(then="""
            romclean_list "$plan" move
            echo --
            romclean_list "$plan" rest
            echo --
            romclean_transfer "$plan" copy | grep -c '^@step'
            cat "$plan.result"
        """)
        # O Metal Slug e a BIOS dele vao; o bootleg e o de trackball sobram; os
        # do Flycast nao entram na conta.
        self.assertEqual(lines[0], "move=2 rest=2 bytes=3072")
        self.assertEqual(lines[1:4], ["mslug            Metal Slug", "neogeo           Neo-Geo", "--"])
        self.assertEqual(lines[4:7], ["cent             Centipede", "mslugb           Metal Slug (bootleg)", "--"])
        self.assertGreaterEqual(int(lines[7]), 2)
        self.assertEqual(lines[8:], ["copied=2", "skipped=0", "errors=0"])
        # Os jogos em ~/roms/mame, a BIOS em ~/bios/mame, o romset inteiro.
        self.assertTrue((self.roms / "mame" / "mslug.zip").exists())
        self.assertTrue((self.env.dir / "bios" / "mame" / "neogeo.zip").exists())
        self.assertFalse((self.roms / "mame" / "neogeo.zip").exists())
        self.assertEqual(len(list(self.full.iterdir())), len(self.SETS))
        self.assertIn("ROM cleaner: copy (%s -> %s/mame)" % (self.full, self.roms),
                      (self.env.dir / "setup.log").read_text())

    def test_move_then_delete_the_rest(self):
        lines = self.scan(then="""
            r=$(romclean_apply "$plan" move); romclean_value "$r" moved
            r=$(romclean_apply "$plan" delete-rest); romclean_value "$r" deleted
        """)
        self.assertEqual(lines[1:], ["2", "2"])
        # Na origem ficam os do Flycast: nunca sao apagados.
        self.assertEqual(sorted(p.name for p in self.full.iterdir()),
                         ["awbios.zip", "kofxi.zip", "mvsc2.zip", "naomi.zip"])

    def test_flycast_gets_one_folder_per_system(self):
        lines = self.scan("flycast", then="""
            r=$(romclean_apply "$plan" copy); romclean_value "$r" copied
        """)
        self.assertEqual(lines, ["move=4 rest=4 bytes=6144", "4"])
        self.assertTrue((self.roms / "naomi" / "mvsc2.zip").exists())
        self.assertTrue((self.roms / "atomiswave" / "kofxi.zip").exists())
        self.assertEqual(sorted(p.name for p in (self.env.dir / "bios" / "dc").iterdir()),
                         ["awbios.zip", "naomi.zip"])
        self.assertFalse((self.roms / "naomi" / "mslug.zip").exists())

    def test_chd_cleaner_copies_the_chds_of_the_games_in_the_rom_folder(self):
        self.xml.write_text(self.XML.replace(
            '</mame>', '<machine name="kinst"><description>Killer Instinct</description><disk name="kinst"/>'
                       '</machine><machine name="ikaruga" romof="naomi"><description>Ikaruga</description>'
                       '<disk name="gdl-0010"/></machine></mame>'))
        chds = self.env.dir / "chds"
        for folder, name in (("kinst", "kinst.chd"), ("ikaruga", "gdl-0010.chd"), ("area51", "area51.chd")):
            (chds / folder).mkdir(parents=True)
            (chds / folder / name).write_bytes(b"c" * 2048)
        for folder, rom in (("mame", "kinst.zip"), ("mame", "mslug.zip"), ("naomi", "ikaruga.zip")):
            (self.roms / folder).mkdir(parents=True, exist_ok=True)
            (self.roms / folder / rom).write_bytes(b"x")
        script = """
            plan=%(dir)s/plan
            s=$(romclean_chd_scan %(chds)s %(target)s "" "$(romclean_default_dest %(target)s)" "$plan")
            echo "games=$(romclean_value "$s" games) move=$(romclean_value "$s" move) bytes=$(romclean_value "$s" move_bytes)"
            romclean_list "$plan" move
            romclean_transfer "$plan" copy | tail -1
        """
        mame = self.env.out(script % {"dir": self.env.dir, "chds": chds, "target": "groovymame"},
                            self.vars).splitlines()
        self.assertEqual(mame, ["games=1 move=1 bytes=2048", "kinst            Killer Instinct", "@step 100 Done"])
        self.assertTrue((self.roms / "mame" / "kinst" / "kinst.chd").exists())
        # No Flycast, para dentro das pastas de Naomi (os jogos de GD-ROM).
        flycast = self.env.out(script % {"dir": self.env.dir, "chds": chds, "target": "flycast"},
                               self.vars).splitlines()
        self.assertEqual(flycast[:2], ["games=1 move=1 bytes=2048", "ikaruga          Ikaruga"])
        self.assertTrue((self.roms / "naomi" / "ikaruga" / "gdl-0010.chd").exists())
        self.assertFalse((self.roms / "mame" / "area51").exists())
        self.assertEqual(self.env.out("romclean_chd_folders flycast /r; romclean_chd_folders groovymame /r/mame",
                                      self.vars).split(), ["/r/naomi", "/r/naomi2", "/r/mame"])
        home = {"FLIPEROS_USER": "fliperos"}
        self.assertEqual(self.env.out("romclean_chd_label flycast /home/fliperos/roms; "
                                      "romclean_chd_label groovymame /home/fliperos/roms/mame", home).split(),
                         ["~/roms/{naomi,naomi2}", "~/roms/mame"])
        menu = (SETUP / "screens" / "setup-menu.sh").read_text()
        screen = (SETUP / "screens" / "rom-cleaner.sh").read_text()
        self.assertIn('"chdcleaner|MAME CHD Cleaner"', screen)
        self.assertIn("chdcleaner) screen_chd_cleaner ;;", screen)
        self.assertIn('"downloader|Downloader (MAME ROM/CHD torrent, free games)"', menu)
        self.assertIn("downloader) screen_downloads ;;", menu)
        self.assertNotIn("freeroms|", menu)
        self.assertIn('source "$SETUP_DIR/screens/downloader.sh"', (SETUP / "fliperos-setup").read_text())

    def test_the_xml_is_read_once_per_mame_version(self):
        self.scan()
        self.scan("flycast")
        self.assertEqual((self.env.dir / "listxml.calls").read_text(), "x\n")
        self.assertTrue((self.env.dir / "cache" / "romclean-groovymame-0.289.json").is_file())

    def test_every_parameter_has_a_picker(self):
        # Cada parametro: de escolher uma (radio) ou de marcar varias (check),
        # com titulo, a pergunta e as opcoes "valor|rotulo".
        keys = self.env.out('echo "${ROMCLEAN_KEYS[@]}"').split()
        self.assertEqual(len(keys), 20)
        for key in keys + ["transfer"]:
            kind, title, text = self.env.out(
                'echo "${ROMCLEAN_TYPE[%s]}"; echo "${ROMCLEAN_TITLE[%s]}"; echo "${ROMCLEAN_HELP[%s]}"'
                % (key, key, key)).splitlines()
            self.assertIn(kind, ("radio", "check"), key)
            self.assertTrue(title and text, key)
            # Uma linha na caixa de 72 colunas: numa tela de 240 linhas sobra
            # pouco para a lista.
            self.assertLessEqual(len(text), 66, key)
            options = self.env.out("romclean_options %s; true" % key).splitlines()
            if key != "genres":
                self.assertGreaterEqual(len(options), 2, key)
            for option in options:
                self.assertRegex(option, r"^[a-z0-9]+\|\S", key)
        kinds = dict(line.split("=") for line in self.env.out(
            'for k in "${ROMCLEAN_KEYS[@]}"; do echo "$k=${ROMCLEAN_TYPE[$k]}"; done').split())
        self.assertEqual(sorted(k for k, v in kinds.items() if v == "check"),
                         ["controls", "decades", "genres", "hardware", "lines", "modes", "orientation", "systems"])

    def test_presets(self):
        keys = self.env.out('echo "${ROMCLEAN_KEYS[@]}"').split()
        for preset in ("cabinet", "working", "psx", "all"):
            kv = dict(line.split("=", 1) for line in self.env.out("romclean_preset %s" % preset).splitlines())
            self.assertEqual(list(kv), keys, preset)
            for key, value in kv.items():
                options = [o.split("|")[0] for o in self.env.out("romclean_options %s; true" % key).splitlines()]
                for v in value.split(",") if value else ():
                    self.assertIn(v, options, (preset, key))
        self.assertNotEqual(self.env.run("romclean_preset outro").returncode, 0)
        # No Flycast o status do MAME nao filtra.
        self.assertIn("status=all\n", self.env.out("romclean_preset cabinet flycast"))
        self.assertIn("status=imperfect\n", self.env.out("romclean_preset cabinet groovymame"))
        self.assertEqual(self.env.out("romclean_preset_label cabinet; romclean_preset_label custom").splitlines(),
                         ["Joystick cabinet (2 players, 6 buttons)", "Custom"])

    def args(self, target, *kv):
        return self.env.out("romclean_args %s %s" % (target, " ".join("'%s'" % x for x in kv)),
                            self.vars).splitlines()

    def test_parameters_become_engine_options(self):
        cabinet = self.env.out('mapfile -t kv < <(romclean_preset cabinet); romclean_args groovymame "${kv[@]}"',
                               self.vars).splitlines()
        # Sem o catver.ini e o nplayers.ini os filtros deles nao entram; uma
        # lista com tudo marcado nao filtra.
        self.assertEqual(cabinet, ["--arcade-only", "--status", "imperfect", "--max-players", "2", "--max-buttons",
                                   "6", "--controls", "joy8,joy4,joy2,twin", "--clones", "1g1r", "--regions",
                                   "World,USA,Europe,Brazil,Hispanic,Oceania,Asia,Japan,Unknown", "--no-bootlegs",
                                   "--no-prototypes", "--exclude", "flycast"])
        flycast = self.env.out('mapfile -t kv < <(romclean_preset cabinet flycast); romclean_args flycast "${kv[@]}"',
                               self.vars).splitlines()
        self.assertEqual(flycast[flycast.index("--status") + 1], "all")
        self.assertEqual(flycast[-2:], ["--systems", "naomi,naomi2,atomiswave"])
        self.assertNotIn("flycast", flycast)
        self.assertEqual(self.args("flycast", "systems=atomiswave", "hardware=neogeo"), ["--systems", "atomiswave"])
        self.assertEqual(self.args("flycast", "systems="), ["--systems", "naomi,naomi2,atomiswave"])
        for kv, expected in (
                ("chd=only", ["--only", "chd"]), ("chd=no", ["--exclude", "chd"]), ("chd=yes", []),
                ("vector=no", ["--exclude", "vector"]), ("lines=15", ["--scan-rates", "15"]),
                ("lines=15,25,31", []), ("lines=", []), ("orientation=vertical", ["--orientation", "vertical"]),
                ("orientation=horizontal,vertical", []), ("decades=1980,1990", ["--decades", "1980,1990"]),
                ("controls=", ["--controls", ""]), ("controls=joy8,trackball", ["--controls", "joy8,trackball"]),
                ("hardware=neogeo,cps2", ["--hardware", "neogeo,cps2"]), ("hardware=", []),
                ("region=japan", ["--regions", "Japan,World,USA,Europe,Asia,Brazil,Hispanic,Oceania,Unknown"]),
                ("flycast=yes", []), ("mature=no", []), ("genres=Fighter", []), ("modes=sim", [])):
            self.assertEqual(self.args("groovymame", kv), expected, kv)
        every = self.env.out("romclean_all controls").strip()
        self.assertEqual(self.args("groovymame", "controls=" + every), ["--controls", "any"])

    def test_labels_of_the_parameter_screen(self):
        for key, value, label in (
                ("players", "0", "Players: Any"), ("buttons", "6", "Buttons: Up to 6"),
                ("arcade", "yes", "Games: Arcade machines only"), ("clones", "1g1r", "Clones: Best version of each game"),
                ("controls", "joy8,joy4", "Controls: 8-way joystick, 4-way joystick"),
                ("controls", "", "Controls: buttons only"), ("hardware", "", "Hardware: any"),
                ("hardware", "neogeo,cps2", "Hardware: Neo-Geo, Capcom CPS-2"),
                ("lines", "15", "Resolution: Low"), ("lines", "15,25,31", "Resolution: all"),
                ("decades", "1980,1990", "Years: 1980s, 1990s"), ("systems", "naomi,naomi2", "Systems: Naomi, Naomi 2"),
                ("controls", "joy8,joy4,joy2,twin", "Controls: 8-way joystick, 4-way joystick, 2-way joystick, Twin sticks"),
                ("controls", "joy8,joy4,joy2,twin,trackball,spinner", "Controls: 6 of 13"),
                ("transfer", "copy", "Transfer: Copy"), ("chd", "only", "Games with CHD: Only those")):
            self.assertEqual(self.env.out("romclean_label %s '%s'" % (key, value)).strip(), label)

    def test_data_files_come_with_the_romset(self):
        # catver.ini na pasta de cima do romset, nplayers.ini na subpasta
        # folders (a da interface do MAME), controls.xml na pasta do sistema;
        # o nome sem diferenciar maiusculas.
        (self.full.parent / "Catver.ini").write_text(
            ";; catver.ini 0.289 / 21-Aug-26 ;;\n[Category]\nmslug=Platform / Run Jump\ncent=Shooter / Gallery\n"
            "sf2=Fighter / Versus\nkof98=Fighter / Versus\nslots=Slot Machine / Reels\n")
        (self.full / "folders").mkdir()
        (self.full / "folders" / "nplayers.ini").write_text(";; NPlayers 0.278 ;;\n[NPlayers]\nmslug=2P sim\n")
        (self.env.dir / "data").mkdir()
        (self.env.dir / "data" / "controls.xml").write_text('<dat><meta><version name="0.141.1"/></meta></dat>')
        script = """
            romclean_data_load %s
            echo "$ROMCLEAN_CATVER"; echo "$ROMCLEAN_NPLAYERS"; echo "$ROMCLEAN_CONTROLS"
            echo "$ROMCLEAN_DATA_LABEL"; echo "$ROMCLEAN_GENRES_DEFAULT"
            romclean_options genres
            echo --
            romclean_label genres "$ROMCLEAN_GENRES_DEFAULT"
            romclean_args groovymame "genres=$ROMCLEAN_GENRES_DEFAULT" mature=no modes=sim
            romclean_args groovymame "genres=$(romclean_all genres)" mature=yes "modes=$(romclean_all modes)"
        """ % self.full
        lines = self.env.out(script, self.vars).splitlines()
        self.assertEqual(lines[:3], [str(self.full.parent / "Catver.ini"), str(self.full / "folders" / "nplayers.ini"),
                                     str(self.env.dir / "data" / "controls.xml")])
        self.assertEqual(lines[3], "catver.ini 0.289, nplayers.ini 0.278, controls.xml 0.141.1")
        self.assertEqual(lines[4], "Fighter,Platform,Shooter")
        self.assertEqual(lines[5:10], ["Fighter|Fighter (2)", "Platform|Platform (1)", "Shooter|Shooter (1)",
                                       "Slot Machine|Slot Machine (1)", "--"])
        self.assertEqual(lines[10], "Categories: Fighter, Platform, Shooter")
        self.assertEqual(lines[11:], ["--categories", "Fighter,Platform,Shooter", "--no-mature", "--play-modes", "sim"])
        # Sem nenhum: os filtros deles somem da tela e a tela diz o que falta.
        lines = self.env.out('romclean_data_load /nada; echo "$ROMCLEAN_DATA_LABEL"; '
                             "for k in genres mature modes players; do romclean_visible $k groovymame && echo $k; done",
                             dict(self.vars, ROMCLEAN_DATA="/nada")).splitlines()
        self.assertEqual(lines, ["none (missing: catver.ini, nplayers.ini, controls.xml)", "players"])

    def test_emulators_and_where_the_games_go(self):
        out = self.env.out("romclean_targets", self.vars).splitlines()
        self.assertEqual([o.split("|")[0] for o in out], ["groovymame", "flycast", "file"])
        self.assertEqual(out[0], "groovymame|GroovyMAME 0.289")
        (self.env.dir / "mame2010.xml.xz").write_bytes(b"")
        self.assertIn("mame2010|MAME 2010 (0.139), the RetroArch mame2010 core",
                      self.env.out("romclean_targets", self.vars).splitlines())
        # O emulador provavel pelo nome da pasta.
        script = ("romclean_default_target /r/retroarch/mame2010; romclean_default_target /r/mame; "
                  "romclean_default_target /pc/Naomi; romclean_default_target /pc/naomi-roms/full")
        self.assertEqual(self.env.out(script, self.vars).split(), ["mame2010", "groovymame", "flycast", "groovymame"])
        roms, bios = self.roms, self.env.dir / "bios"
        self.assertEqual(self.env.out("romclean_default_dest mame2010", self.vars).strip(), "%s/mame" % roms)
        (roms / "retroarch" / "mame2010").mkdir(parents=True)
        self.assertEqual(self.env.out("romclean_default_dest mame2010; romclean_default_dest flycast; "
                                      "romclean_default_dest groovymame", self.vars).split(),
                         ["%s/retroarch/mame2010" % roms, str(roms), "%s/mame" % roms])
        # A BIOS: ~/bios/mame com os jogos em ~/roms/mame, ~/bios/dc no
        # Flycast; no core mame2010 e numa pasta escolhida a mao, com os jogos.
        self.assertEqual(self.env.out("romclean_target_args groovymame %s/mame/" % roms, self.vars).splitlines(),
                         ["--dest", "%s/mame/" % roms, "--bios-dest", "%s/mame" % bios])
        self.assertEqual(self.env.out("romclean_target_args groovymame /mnt/usb; "
                                      "romclean_target_args mame2010 %s/retroarch/mame2010" % roms,
                                      self.vars).splitlines(),
                         ["--dest", "/mnt/usb", "--dest", "%s/retroarch/mame2010" % roms])
        self.assertEqual(self.env.out("romclean_target_args flycast %s" % roms, self.vars).splitlines(),
                         ["--dest", "%s/naomi" % roms, "--no-devices", "--route", "naomi=%s/naomi" % roms,
                          "--route", "naomi2=%s/naomi2" % roms, "--route", "atomiswave=%s/atomiswave" % roms,
                          "--bios-dest", "%s/dc" % bios])
        home = {"FLIPEROS_USER": "fliperos", "ROMS_ROOT": "/home/fliperos/roms", "BIOS_ROOT": "/home/fliperos/bios"}
        self.assertEqual(self.env.out("romclean_dest_label flycast /home/fliperos/roms; "
                                      "romclean_dest_label groovymame /home/fliperos/roms/mame; "
                                      "romclean_dest_label mame2010 /mnt/usb", home).splitlines(),
                         ["~/roms/{naomi,naomi2,atomiswave} (BIOS: ~/bios/dc)", "~/roms/mame (BIOS: ~/bios/mame)",
                          "/mnt/usb"])

    def test_every_value_is_known_by_the_engine(self):
        # Os valores da tela sao os que o fliperos-romclean aceita.
        engine = load_engine()
        values = {key: self.env.out("romclean_all %s" % key).strip().split(",")
                  for key in ("controls", "status", "modes", "lines", "hardware", "systems", "clones", "decades")}
        self.assertEqual(sorted(values["controls"]), engine.FAMILIES)
        self.assertEqual(tuple(values["modes"]), engine.PLAY_MODES)
        self.assertEqual(tuple(values["lines"]), engine.SCAN_RATES)
        self.assertEqual(tuple(values["hardware"]), engine.HARDWARE)
        self.assertEqual(tuple(values["systems"]), engine.FLYCAST_SYSTEMS)
        self.assertEqual(sorted(values["status"]), ["all", "imperfect", "working"])
        self.assertEqual(sorted(values["clones"]), ["1g1r", "keep", "none"])
        for name in ("world", "usa", "europe", "japan", "brazil"):
            regions = self.env.out("romclean_regions %s" % name).strip().split(",")
            self.assertEqual(sorted(regions), sorted(engine.REGION_ORDER), name)

    def test_human_bytes(self):
        self.assertEqual(self.env.out("human_bytes 0; human_bytes 1536; human_bytes 3221225472").split("\n")[:3],
                         ["0 B", "1.5 KB", "3.0 GB"])

    def test_the_screen(self):
        menu = (SETUP / "screens" / "setup-menu.sh").read_text()
        self.assertIn('"cleaner|Cleaner (MAME/Flycast/etc ROM/CHD)"', menu)
        self.assertIn("cleaner) screen_cleaner ;;", menu)
        self.assertNotIn("romcleaner|", menu)
        screen = (SETUP / "screens" / "rom-cleaner.sh").read_text()
        # Em Setup > Cleaner.
        self.assertIn('"romcleaner|MAME ROM Cleaner"', screen)
        self.assertIn("romcleaner) screen_rom_cleaner ;;", screen)
        # Enter num parametro abre as opcoes dele (uma ou varias) e volta.
        pick = screen.split("screen_rom_cleaner_pick() {")[1].split("\n}\n")[0]
        self.assertIn('ui_checklist "$title" "${ROMCLEAN_HELP[$key]}" "$value" "${options[@]}"', pick)
        self.assertIn('ui_radio "$title" "${ROMCLEAN_HELP[$key]}" "$value" "${options[@]}"', pick)
        self.assertIn("run_with_progress", screen)
        # De uma pasta so de leitura (a da rede) nao se move.
        self.assertIn('[[ -w $folder && $mode != downloader ]] && writable=1', screen)
        self.assertIn("source \"$SETUP_DIR/lib/netshare.sh\"", (SETUP / "fliperos-setup").read_text())

    def test_attract_romlist_gets_the_real_names_and_the_clones(self):
        # Setup > AttractPlus ROM List: o nome do -listxml no lugar do nome do
        # arquivo, os clones de um romset merged (so no MAME, que abre pelo
        # nome), sem as BIOS, e a tela Arcade com todas as pastas.
        roms, info, attract = self.env.dir / "home-roms", self.env.dir / "info", self.env.dir / "attract"
        files = {"mame": ("mslug.zip", "neogeo.zip", "meujogo.zip", "_info.txt"), "naomi": ("mvsc2.zip",),
                 "retroarch/fbneo": ("mslug.zip",), "retroarch/snes9x": ("mario.sfc",)}
        for folder, names in files.items():
            (roms / folder).mkdir(parents=True)
            for name in names:
                (roms / folder / name).write_text("x")
        info.mkdir()
        (info / "fbneo_libretro.info").write_text('systemname = "Arcade (various)"\nsystemid = "fb_alpha"\n'
                                                  'corename = "FinalBurn Neo"\nsupported_extensions = "zip|7z"\n')
        (info / "snes9x_libretro.info").write_text('systemname = "Super Nintendo"\nsystemid = "super_nes"\n')
        env = dict(self.vars, ROMS_DIR=str(roms), RA_INFO_DIR=str(info), ATTRACT_DIR=str(attract),
                   MEDIA_DIR=str(self.env.dir / "media"), FLIPEROS_USER="ninguem")
        lines = self.env.out("""
            mapfile -t s < <(frontends_romlist_systems)
            printf '%s\\n' "${s[@]}"
            frontends_romlist "$ROMCLEAN_CACHE.result" "${s[@]}" | grep -c '^@step'
            cat "$ROMCLEAN_CACHE.result"
        """, env).splitlines()
        fbneo = "Arcade (various) (FinalBurn Neo)"
        self.assertEqual(lines[:3], ["mame|%s/mame|arcade|3|MAME" % roms, "naomi|%s/naomi|naomi|1|Naomi" % roms,
                                     "retroarch/fbneo|%s/retroarch/fbneo|fba|1|%s" % (roms, fbneo)])
        self.assertGreaterEqual(int(lines[3]), 3)
        self.assertEqual(lines[4:], ["MAME\t3\t1\t1", "Naomi\t1\t0\t0", "%s\t1\t0\t0" % fbneo, "total\t5"])

        def romlist(name):
            text = (attract / "romlists" / (name + ".txt")).read_text().splitlines()
            self.assertTrue(text[0].startswith("#Name;Title;Emulator;CloneOf;Year;"))
            return {line.split(";")[0]: line.split(";") for line in text[1:]}
        mame = romlist("MAME")
        self.assertEqual(sorted(mame), ["meujogo", "mslug", "mslugb"])
        self.assertEqual(mame["mslug"][:5], ["mslug", "Metal Slug", "MAME", "", "1996"])
        self.assertEqual((mame["mslug"][9], mame["mslug"][10], mame["mslug"][16]), ("joystick (8-way)", "good", "4"))
        self.assertEqual(len(mame["mslug"]), 21)
        self.assertEqual(mame["mslugb"][1:4], ["Metal Slug (bootleg)", "MAME", "mslug"])
        self.assertEqual(mame["meujogo"][1:3], ["meujogo", "MAME"])
        self.assertEqual(romlist("Naomi")["mvsc2"][1], "Marvel Vs. Capcom 2")
        self.assertEqual(sorted(romlist(fbneo)), ["mslug"])
        self.assertEqual(len(romlist("Arcade")), 4)
        self.assertEqual(sum(1 for line in (attract / "romlists" / "Arcade.txt").read_text().splitlines()), 6)
        acfg = (attract / "attract.cfg").read_text()
        self.assertIn("display\tArcade\n", acfg)
        self.assertIn("display\tNaomi\n", acfg)
        # Os arcades de outra plataforma tambem procuram a arte em arcade.
        media = self.env.dir / "media"
        naomi = (attract / "emulators" / "Naomi.cfg").read_text()
        self.assertIn("artwork    snap            %s/snap/naomi;%s/preview/naomi;%s/snap/arcade;%s/preview/arcade\n"
                      % (media, media, media, media), naomi)
        self.assertIn("artwork    wheel           %s/logo/naomi;%s/logo/arcade\n" % (media, media), naomi)
        self.assertIn("artwork    wheel           %s/logo/arcade\n" % media,
                      (attract / "emulators" / "MAME.cfg").read_text())

    def test_attract_display_goes_to_displays_cfg_after_the_migration(self):
        # O Attract-Mode Plus 3.x, depois de migrar para config/, so le as
        # telas de config/displays.cfg.
        attract = self.env.dir / "attract-split"
        (attract / "config").mkdir(parents=True)
        (attract / "config" / "attract.cfg").write_text("general\n")
        (attract / "config" / "displays.cfg").write_text(
            "display Naomi\n    layout                  Attrac-Man\n    romlist                 Naomi\n\n")
        env = dict(self.vars, ATTRACT_DIR=str(attract))
        self.env.out("scraper_attract_display Naomi; scraper_attract_display Atomiswave", env)
        displays = (attract / "config" / "displays.cfg").read_text()
        self.assertEqual(displays.count("romlist"), 2)
        self.assertIn("Attrac-Man", displays)
        self.assertIn("display\tAtomiswave\n\tlayout               AdvanceMenu\n", displays)
        self.assertFalse((attract / "attract.cfg").exists())

    def test_model2_folder_is_an_arcade_system(self):
        self.assertEqual(self.env.out("scraper_platform model2; scraper_attract_emulator model2").splitlines(),
                         ["arcade", "Model 2|/opt/fliperos/bin/fliperos-x11-run|fliperos-model2 [name]|.zip"])
        self.assertEqual(self.env.run("scraper_arcade dreamcast").returncode, 1)
        self.assertEqual(self.env.run("scraper_arcade model2").returncode, 0)


class ReloadTests(Base):
    """O Setup atualizado com a tela aberta se reabre: as telas ja carregadas
    sao as de antes e chamariam os programas novos com as opcoes antigas (no
    gabinete, o ROM cleaner antigo chamou o motor novo com --flycast)."""

    def test_stamp_changes_when_a_file_of_the_setup_changes(self):
        d = self.env.dir / "setup"
        (d / "lib").mkdir(parents=True)
        (d / "lib" / "a.sh").write_text("um\n")
        env = {"SETUP_DIR": str(d)}
        first = self.env.out("setup_stamp", env)
        self.assertEqual(self.env.out("setup_stamp", env), first)
        (d / "lib" / "a.sh").write_text("dois, maior\n")
        second = self.env.out("setup_stamp", env)
        self.assertNotEqual(second, first)
        (d / "lib" / "novo.sh").write_text("x\n")
        self.assertNotEqual(self.env.out("setup_stamp", env), second)

    def test_menus_reopen_the_setup(self):
        main = (SETUP / "fliperos-setup").read_text()
        self.assertIn("SETUP_STAMP=$(setup_stamp)\nSETUP_ARGS=(\"$@\")\n", main)
        menu = (SETUP / "screens" / "main-menu.sh").read_text()
        reload = menu.split("screen_reload_if_updated() {")[1].split("\n}\n")[0]
        self.assertIn('$(setup_stamp) != "$SETUP_STAMP"', reload)
        self.assertIn('exec "$SETUP_DIR/fliperos-setup" "${SETUP_ARGS[@]}"', reload)
        # No comeco dos dois menus do sistema instalado.
        for path, name in (("main-menu.sh", "screen_main_menu"), ("setup-menu.sh", "screen_setup_menu")):
            body = (SETUP / "screens" / path).read_text().split(name + "() {")[1].split("\n}\n")[0]
            self.assertIn("  while true; do\n    screen_reload_if_updated\n", body, name)

    def test_rom_cleaner_shows_why_the_scan_failed(self):
        screen = (SETUP / "screens" / "rom-cleaner.sh").read_text()
        self.assertIn('2> "$list")\n  rc=$?\n  cat "$list" >> "$FLIPEROS_LOG"', screen)
        self.assertIn("tail -n 1", screen.split("if ((rc != 0)); then")[1].split("fi\n")[0])


class FreeRomsTests(Base):
    """lib/freeroms.sh: Setup > Free games (config/fliperos-freeroms)."""

    def test_list_and_fetch_events(self):
        self.env.stub("fliperos-freeroms", """
            case $1 in
              list) printf 'fceumm\\t240pee.nes\\t240p Test Suite (NES)\\tGPL-2.0-or-later\\nmgba\\tlibbet.gb\\tLibbet\\tZlib\\n' ;;
              fetch) echo "$*" > "%s/fetch.args"; printf '@step 50 Libbet\\ndownloaded=2\\npresent=0\\n@step 100 Done\\n'; exit ${FAIL:-0} ;;
            esac
        """ % self.env.dir)
        env = {"FREEROMS": str(self.env.bin / "fliperos-freeroms")}
        self.assertEqual(self.env.out("freeroms_list", env).splitlines(),
                         ["240p Test Suite (NES) (fceumm, GPL-2.0-or-later)", "Libbet (mgba, Zlib)"])
        result = self.env.dir / "result"
        out = self.env.out("freeroms_fetch %s" % result, env).splitlines()
        self.assertEqual(out[0], "@step 0 Starting")
        self.assertEqual(out[-1], "@step 100 Done")
        self.assertIn("downloaded=2", result.read_text())
        self.assertEqual((self.env.dir / "fetch.args").read_text(), "fetch --progress\n")
        # O status e o do programa, nao o do tee.
        self.assertEqual(self.env.run("freeroms_fetch %s" % result, dict(env, FAIL="1")).returncode, 1)


class NetShareTests(Base):
    """lib/netshare.sh: a pasta compartilhada da rede (SMB), so para leitura."""

    def setUp(self):
        super().setUp()
        self.calls = self.env.dir / "mount.calls"
        self.mnt = self.env.dir / "mnt"
        # mount falso: anota a linha e o arquivo de credenciais; falha com a
        # mensagem do mount.cifs quando MOUNT_FAIL diz qual.
        self.env.stub("mount", """
            echo "$*" >> "%(calls)s"
            cred=$(sed -n 's/.*credentials=\\([^,]*\\).*/\\1/p' <<< "$*")
            [[ -n $cred ]] && { stat -c %%a "$cred"; cat "$cred"; } >> "%(calls)s"
            case ${MOUNT_FAIL:-} in
              13) echo "mount error(13): Permission denied" >&2; exit 32 ;;
              2) echo "mount error(2): No such file or directory" >&2; exit 32 ;;
              113) echo "mount error(113): could not connect to 10.0.0.9Unable to find suitable address." >&2; exit 32 ;;
              utf8) [[ $* == *iocharset=utf8* ]] && { echo "mount error(79): Can not access a needed shared library" >&2; exit 32; } ;;
            esac
            : > "%(dir)s/mounted"
        """ % {"calls": self.calls, "dir": self.env.dir})
        self.env.stub("mount.cifs", "exit 0")
        self.env.stub("mountpoint", '[[ -f "%s/mounted" ]]' % self.env.dir)
        self.env.stub("umount", 'echo "umount $*" >> "%s"; rm -f "%s/mounted"' % (self.calls, self.env.dir))
        self.vars = {"NETSHARE_DIR": str(self.mnt), "NETSHARE_CRED": str(self.env.etc / "netshare.cred"),
                     "FLIPEROS_USER": "root"}

    def test_mount_is_read_only_and_hides_the_password(self):
        self.env.out("netshare_mount 192.168.1.10 romsets ana 's3 nha,x'", self.vars)
        lines = self.calls.read_text().splitlines()
        self.assertRegex(lines[0], r"^-t cifs //192\.168\.1\.10/romsets %s -o ro,uid=0,gid=0,actimeo=60,"
                                   r"credentials=\S+,iocharset=utf8$" % self.mnt)
        # A senha so no arquivo de credenciais (600), que some depois.
        self.assertNotIn("s3 nha", lines[0])
        self.assertEqual(lines[1:], ["600", "username=ana", "password=s3 nha,x"])
        cred = re.search(r"credentials=([^,]+)", lines[0]).group(1)
        self.assertFalse(os.path.exists(cred))
        self.assertEqual(self.env.out("netshare_mounted && echo sim", self.vars).strip(), "sim")
        # Como convidado; e a anterior e desmontada antes.
        self.calls.write_text("")
        self.env.out("netshare_mount nas roms '' ''", self.vars)
        lines = self.calls.read_text().splitlines()
        self.assertEqual(lines[0], "umount %s" % self.mnt)
        self.assertIn("-o ro,uid=0,gid=0,actimeo=60,guest,iocharset=utf8", lines[1])

    def test_errors_in_plain_words(self):
        for code, text in (("13", "Wrong user or password"), ("2", "no shared folder with this name"),
                           ("113", "did not answer")):
            out = self.env.out('netshare_mount h s u p || echo "$NETSHARE_ERROR"', dict(self.vars, MOUNT_FAIL=code))
            self.assertIn(text, out, code)
        self.assertIn("mount.cifs //h/s: mount error(13)", (self.env.dir / "setup.log").read_text())
        # Um kernel sem o nls_utf8: monta sem o iocharset.
        self.env.out("netshare_mount h s u p", dict(self.vars, MOUNT_FAIL="utf8"))
        self.assertTrue((self.env.dir / "mounted").exists())
        (self.env.bin / "mount.cifs").unlink()
        self.assertEqual(self.env.run("netshare_available", self.vars).returncode, 1)
        self.assertIn("cifs-utils", self.env.out('netshare_mount h s u p || echo "$NETSHARE_ERROR"', self.vars))

    def test_the_share_is_remembered_and_the_password_only_if_asked(self):
        self.env.out("netshare_save 192.168.1.10 romsets ana 'se=nha'", self.vars)
        cred = self.env.etc / "netshare.cred"
        self.assertEqual(oct(cred.stat().st_mode & 0o777), "0o600")
        self.assertEqual(self.env.out("netshare_saved host; netshare_saved share; netshare_saved user; "
                                      "netshare_saved_password ana", self.vars).splitlines(),
                         ["192.168.1.10", "romsets", "ana", "se=nha"])
        self.assertEqual(self.env.run("netshare_saved_password outro", self.vars).returncode, 1)
        self.env.out("netshare_save 192.168.1.10 romsets ana", self.vars)
        self.assertFalse(cred.exists())
        self.assertEqual(self.env.run("netshare_saved_password ana", self.vars).returncode, 1)

    def test_shares_of_a_computer(self):
        self.env.stub("smbclient", """
            echo "$*" >> "%s"
            printf 'Disk|romsets|Romsets\\nDisk|C$|Default\\nIPC|IPC$|Remote IPC\\nDisk|Fotos da casa|\\nPrinter|hp|\\n'
        """ % self.calls)
        self.assertEqual(self.env.out("netshare_shares 192.168.1.10 ana senha", self.vars).splitlines(),
                         ["romsets", "Fotos da casa"])
        self.assertRegex(self.calls.read_text(), r"^-g -L //192\.168\.1\.10 -A \S+\n$")
        self.assertNotIn("senha", self.calls.read_text())

    def test_in_the_image(self):
        self.assertIn("cifs-utils smbclient", (ROOT / "fliperos-mkiso.sh").read_text())
        self.assertIn("cifs-utils smbclient", (ROOT / "tools/cabinet-update.sh").read_text())


if __name__ == "__main__":
    unittest.main()
