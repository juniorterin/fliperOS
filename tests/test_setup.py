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
import shlex
import shutil
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "fliperos-setup"
LIBS = ["common", "config", "progress", "speech", "monitor", "drm", "video", "multimonitor", "xorg",
        "bootloader", "disk", "install", "recovery", "launcher", "audio", "network",
        "status", "scraper", "romclean", "netshare", "downloader", "mediapacks", "freeroms", "frontends", "update", "patches", "splash", "folders", "hardware", "latency", "quirks", "padkeys", "lpt", "buttons", "debug", "emulators", "services", "system", "customgames", "whatsnew"]
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
        # O log do kernel do container nao entra na linha do kernel.
        self.stub("dmesg", ":")

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
            "NM_STATE": str(self.dir / "nm" / "NetworkManager.state"),
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


class NouveauLowDotclockTests(Base):
    """NVIDIA (nouveau): o patch 10 do kernel libera os dotclocks baixos na
    saida analogica, mas so a placa que passou no grid em 320x240 os usa."""

    def setUp(self):
        super().setUp()
        self.env.card("card0", "nouveau")
        self.env.connector("card0-VGA-1", "disconnected")

    def conf(self):
        return (self.env.etc / "fliperos.conf").read_text()

    def low(self, card="card0"):
        return self.env.run("drm_card_low_dotclock %s" % card).returncode == 0

    def test_super_until_the_grid_passes(self):
        self.assertEqual(self.env.run("drm_card_low_dotclock_testable card0").returncode, 0)
        self.assertFalse(self.low())
        self.env.out("video_low_dotclock_set card0 1")
        self.assertIn("low_dotclock_pci=0000:00:00.0\n", self.conf())
        self.assertTrue(self.low())
        self.env.out("video_low_dotclock_set card0 0")
        self.assertNotIn("low_dotclock_pci", self.conf())
        self.assertFalse(self.low())

    def test_another_card_passing_does_not_count(self):
        self.env.out("conf_set low_dotclock_pci 0000:09:00.0")
        self.assertFalse(self.low())

    def test_only_nouveau_is_tested(self):
        self.env.card("card1", "i915")
        self.env.card("card2", "amdgpu")
        # O KMS do driver da NVIDIA nao aceita os modos do Switchres.
        self.env.card("card3", "nvidia")
        for card in ("card1", "card2", "card3"):
            self.assertNotEqual(self.env.run("drm_card_low_dotclock_testable %s" % card).returncode, 0, card)

    def test_classified_native_after_the_grid(self):
        self.env.out("video_low_dotclock_set card0 1")
        r = self.env.run("video_test_begin card0-VGA-1; video_classify card0-VGA-1")
        self.assertEqual(r.stdout.splitlines()[-1], "se")

    def test_retest_switches_boot_mode_and_dotclock_min(self):
        ini = self.env.etc / "switchres.ini"
        self.env.out("video_save_result card0-VGA-1 e generic_15")
        self.assertIn("kernel_video=video=VGA-1:1280x480iSe\n", self.conf())
        self.assertRegex(ini.read_text(), r"(?m)^\s*dotclock_min\s+25\.0$")
        self.env.out("video_low_dotclock_set card0 1; video_low_dotclock_apply")
        self.assertIn("detection=se\n", self.conf())
        self.assertIn("kernel_video=video=VGA-1:640x480iSe\n", self.conf())
        self.assertRegex(ini.read_text(), r"(?m)^\s*dotclock_min\s+0$")
        self.env.out("video_low_dotclock_set card0 0; video_low_dotclock_apply")
        self.assertIn("detection=e\n", self.conf())
        self.assertIn("kernel_video=video=VGA-1:1280x480iSe\n", self.conf())
        self.assertRegex(ini.read_text(), r"(?m)^\s*dotclock_min\s+25\.0$")

    def test_own_dotclock_min_is_kept(self):
        ini = self.env.etc / "switchres.ini"
        ini.write_text("dotclock_min 8.0\n")
        self.env.out("video_low_dotclock_set card0 1; video_save_result card0-VGA-1 se generic_15")
        self.assertRegex(ini.read_text(), r"(?m)^\s*dotclock_min\s+8\.0$")

    def test_step_minimum_goes_to_switchres_and_mame(self):
        # A GTX 980 Ti no nouveau: preta em 320x240 (6,5 MHz), imagem de
        # 7,15 MHz para cima. O degrau de 384 de largura vale 7.7.
        ini, mame = self.env.etc / "switchres.ini", self.env.etc / "mame.ini"
        ini.write_text("dotclock_min 25.0\n")
        mame.write_text("dotclock_min 25.0\n")
        self.env.out("video_low_dotclock_set card0 1 7.7; video_save_result card0-VGA-1 se generic_15")
        self.assertIn("low_dotclock_min=7.7\n", self.conf())
        self.assertEqual(self.env.out("video_low_dotclock_min card0").strip(), "7.7")
        self.assertRegex(ini.read_text(), r"(?m)^\s*dotclock_min\s+7\.7$")
        self.assertRegex(mame.read_text(), r"(?m)^\s*dotclock_min\s+7\.7$")
        # O grid de novo, agora visto em 320x240: o degrau gravado antes sai.
        self.env.out("video_low_dotclock_set card0 1 0; video_save_result card0-VGA-1 se generic_15")
        self.assertRegex(ini.read_text(), r"(?m)^\s*dotclock_min\s+0$")
        self.assertRegex(mame.read_text(), r"(?m)^\s*dotclock_min\s+0$")
        self.env.out("video_low_dotclock_set card0 0")
        self.assertNotIn("low_dotclock", self.conf())

    def test_minimum_only_for_the_card_that_passed(self):
        self.env.out("conf_set low_dotclock_pci 0000:09:00.0; conf_set low_dotclock_min 7.7")
        self.assertEqual(self.env.out("video_low_dotclock_min card0").strip(), "0")
        self.env.card("card1", "amdgpu")
        self.assertEqual(self.env.out("video_low_dotclock_min card1").strip(), "0")

    def test_steps_from_320_to_640(self):
        steps = self.env.out("echo $LOWDOT_STEPS").split()
        self.assertEqual([s.split(":")[0] for s in steps], ["320", "384", "512", "640"])
        for step in steps:
            width, minimum = step.split(":")
            mhz = float(self.env.out("video_low_dotclock_mhz %s" % width))
            # O proprio modo do degrau passa do minimo dele.
            self.assertGreater(mhz, float(minimum), step)
        self.assertEqual(self.env.out("video_low_dotclock_mhz 320").strip(), "6.5")
        self.assertEqual(self.env.out("video_low_dotclock_mhz 640").strip(), "13.0")

    def test_boot_modes_below_the_minimum_are_not_offered(self):
        self.env.out("conf_set card card0; conf_set monitor generic_15; video_low_dotclock_set card0 1 0")
        self.assertIn("320x240S|", self.env.out("video_resolution_choices"))
        self.env.out("video_low_dotclock_set card0 1 7.7")
        modes = [l.split("|")[0] for l in self.env.out("video_resolution_choices").splitlines()]
        self.assertNotIn("320x240S", modes)
        for mode in ("384x288S", "640x240S", "640x480iS", "1280x480iS"):
            self.assertIn(mode, modes)

    def test_grid_climbs_the_steps(self):
        # Preto em 320, visto em 384: fica o degrau de 384 (7.7).
        script = ("source %s/screens/output-test.sh\n"
                  "have() { return 0; }; speak() { :; }; ui_clear() { :; }; ui_flush_input() { :; }\n"
                  "ui_timed_confirm() { :; }; ui_text() { \"$@\"; }\n"
                  "video_low_dotclock_grid() { echo \"GRID ${2:-320}\" >&2; }\n"
                  "ui_yesno() { echo \"ASKED: $2\" >&2; [[ $2 == *384x240* ]]; }\n"
                  "screen_low_dotclock_test card0 generic_15; echo rc=$?" % SETUP)
        log = self.env.dir / "log"
        r = self.env.run(script, {"FLIPEROS_LOG": str(log)})
        self.assertIn("rc=0", r.stdout)
        self.assertEqual(re.findall(r"GRID \d+", log.read_text()), ["GRID 320", "GRID 384"])
        self.assertIn("ASKED: Did you see the 384x240 test grid (7.8 MHz) clearly?", r.stderr)
        self.assertIn("low_dotclock_min=7.7\n", self.conf())
        # Nenhum visto: super resolucao.
        log.write_text("")
        r = self.env.run(script.replace("[[ $2 == *384x240* ]]", "false"), {"FLIPEROS_LOG": str(log)})
        self.assertIn("rc=1", r.stdout)
        self.assertEqual(re.findall(r"GRID \d+", log.read_text()), ["GRID 320", "GRID 384", "GRID 512", "GRID 640"])
        self.assertNotIn("low_dotclock", self.conf())

    def test_carried_by_recovery_mode(self):
        self.assertIn("low_dotclock_pci", self.env.out("echo $VIDEO_CONF_KEYS").split())

    def test_kernel_lines_of_the_grid_go_to_the_log(self):
        # O que o nouveau diz no grid (o PLL) fica no log do Setup.
        self.env.stub("fake-dmesg", "printf '%s\\n' 'usb 1-1: new device' "
                      "'nouveau 0000:01:00.0: disp: unable to find matching pll values' 'drm: modeset'")
        out = self.env.out("video_low_dotclock_kernel_log", {"DMESG_CMD": str(self.env.bin / "fake-dmesg")})
        self.assertEqual(out.splitlines(), ["dotclock baixo: o kernel depois do grid:",
                                            "nouveau 0000:01:00.0: disp: unable to find matching pll values",
                                            "drm: modeset"])
        test = (ROOT / "fliperos-setup/screens/output-test.sh").read_text()
        self.assertIn('video_low_dotclock_kernel_log >> "$FLIPEROS_LOG"', test)
        self.assertIn("did not show on the nouveau driver", test)

    def test_grid_is_wired_to_the_output_test_and_video_setup(self):
        test = (ROOT / "fliperos-setup/screens/output-test.sh").read_text()
        self.assertIn('drm_card_low_dotclock_testable "$card"', test)
        self.assertIn("switchres \"${2:-320}\" 240 60 -s -m \"$1\" --dotclock_min 0 -l grid",
                      (ROOT / "fliperos-setup/lib/video.sh").read_text())
        self.assertIn("lowdot) screen_low_dotclock_retest ;;",
                      (ROOT / "fliperos-setup/screens/video-setup.sh").read_text())


class DiskMenuLabelTests(Base):
    """A escolha do disco na instalacao: lista vertical em texto, com o
    /dev, o tamanho e o tipo antes do modelo na interface grafica."""

    def test_list_style_not_tiles(self):
        screen = (SETUP / "screens/disk-selection.sh").read_text()
        self.assertIn('choice=$(UI_STYLE=list ui_menu "Automatically Partition"', screen)

    def test_short_label_in_the_gui(self):
        lib = "source %s/screens/disk-selection.sh; " % SETUP
        out = self.env.out(lib + "ui_gui_alive() { return 0; }; "
                           "disk_menu_label 'Kingston SA400S37240G' 240057409536 /dev/sda sata 0").strip()
        self.assertEqual(out, "sda 240 GB SATA Kingston SA400S37240G")
        out = self.env.out(lib + "ui_gui_alive() { return 1; }; "
                           "disk_menu_label 'Kingston SA400S37240G' 240057409536 /dev/sda sata 0").rstrip()
        self.assertRegex(out, r"^Kingston SA400S37240G +240 GB  /dev/sda +SATA$")


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

    def test_vertical_console_in_480i_with_both_modes(self):
        # Em pe, o console em 640x480i (60 colunas) e o EDID do FliperOS com
        # o 640x240 do menu e do frontend e o 640x480i, dos tempos do
        # Switchres para o monitor; deitado, a linha volta a de antes.
        edid_dir = self.env.dir / "edid"
        self.env.stub("switchres", 'case $2 in\n'
                      '  240) echo \'Switchres: Modeline "640x240_60 15.66KHz 60Hz" 13.013460 640 666 727 831 '
                      '240 242 245 261   -hsync -vsync\' ;;\n'
                      '  480) echo \'Switchres: Modeline "640x480_60i 15.69KHz 60Hz" 13.038390 640 666 727 831 '
                      '480 483 489 523 interlace  -hsync -vsync\' ;;\nesac')
        env = {"EDID_DIR": str(edid_dir), "EDID_MODES": str(SETUP.parent / "config" / "fliperos-edid-modes")}
        self.env.out("conf_set monitor generic_15; vertical_edid", env)
        data = (edid_dir / "fliperos-vertical.bin").read_bytes()
        self.assertEqual(len(data), 128)
        self.assertEqual(sum(data) % 256, 0)
        self.assertEqual(data[:8], b"\x00\xff\xff\xff\xff\xff\xff\x00")
        # Os dois modos: 640x240 progressivo e 640x480i (campo de 240 linhas).
        self.assertEqual((data[56], data[59], data[71] & 0x80), (0x80, 0xF0, 0))
        self.assertEqual((data[74], data[77], data[89] & 0x80), (0x80, 0xF0, 0x80))
        line = "quiet video=VGA-1:640x240Se,panel_orientation=right_side_up fbcon=rotate:1"
        out = self.env.out("vertical_console_cmdline '%s' VGA-1 vertical-cw" % line, env).strip()
        self.assertEqual(out, "quiet video=VGA-1:640x480iSe,panel_orientation=right_side_up fbcon=rotate:1 "
                              "drm.edid_firmware=VGA-1:edid/fliperos-vertical.bin")
        self.assertEqual(self.env.out("vertical_console_cmdline '%s' VGA-1 horizontal" % line, env).strip(), line)
        # Com um EDID ja na linha (boot por EDID), fica como esta.
        own = "video=VGA-1:e drm.edid_firmware=VGA-1:edid/ntsc.bin"
        self.assertEqual(self.env.out("vertical_console_cmdline '%s' VGA-1 vertical-cw" % own, env).strip(), own)
        # Um monitor de 31 kHz (480 progressivo): sem o EDID, nada muda.
        self.env.stub("switchres", "echo 'Switchres: Modeline \"640x480\" 25.2 640 656 752 800 480 490 492 525 -hsync -vsync'")
        self.assertNotEqual(self.env.run("vertical_edid", env).returncode, 0)
        self.assertFalse((edid_dir / "fliperos-vertical.bin").exists())
        self.assertEqual(self.env.out("vertical_console_cmdline '%s' VGA-1 vertical-cw" % line, env).strip(), line)

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


class DeflickerTests(Base):
    def test_level_defaults_to_medium_and_is_saved(self):
        # Medio (a media de duas linhas do RePlayOS) sem nada gravado.
        self.assertEqual(self.env.out("deflicker_level").strip(), "medium")
        self.env.out("deflicker_set strong")
        self.assertEqual(self.env.out("deflicker_level").strip(), "strong")
        self.assertIn("deflicker=strong\n", (self.env.etc / "fliperos.conf").read_text())
        self.assertNotEqual(self.env.run("deflicker_set blur").returncode, 0)
        self.assertEqual(self.env.out("deflicker_level").strip(), "strong")
        self.env.out("deflicker_set off")
        self.assertEqual(self.env.out("deflicker_level").strip(), "off")

    def conf(self):
        return (self.env.etc / "fliperos.conf").read_text()

    def test_every_program_in_the_table_with_its_old_behaviour(self):
        rows = [r.split("|") for r in self.env.out("mode480_rows").splitlines()]
        states = {r[0]: r[2] for r in rows}
        # O que cada um ja fazia: os do fliperos-x11-run em 640x240, o
        # GroovyMAME (interlace 1) e os cores (sem switchres.ini) em 480i, o
        # MAME 2010 (interlace 0) em 240p.
        self.assertEqual(states, {
            "flycast": "240p", "pcsx2": "240p", "duckstation": "240p", "dolphin": "240p", "laserdisc": "240p",
            "model3": "240p", "model2": "240p", "groovymame": "filter", "psx": "filter", "mame2010": "240p", "snes": "filter",
            "megadrive": "filter", "fbneo": "filter", "fightcade": "240p", "desktop": "filter",
            "other": "filter"})
        allowed = {r[0]: r[4] for r in rows}
        self.assertEqual(allowed["desktop"], "filter,pure")
        self.assertEqual(allowed["fightcade"], "240p,filter,pure")
        self.assertEqual(allowed["other"], "filter,pure")
        self.assertTrue(all(r[3].endswith(("Now: 640x240. Not installed.", "Now: 480i, filter medium.",
                                           "Now: 640x240.", "Now: 480i, filter medium. Not installed."))
                            for r in rows), rows)

    def test_method_and_level_per_program(self):
        self.env.out("mode480_set flycast filter strong")
        conf = self.conf()
        for line in ("mode480_flycast=filter", "deflicker_flycast=strong", "deflicker_level_flycast=strong"):
            self.assertIn(line + "\n", conf)
        # Puro: a camada desligada para ele, o nivel guardado para a proxima.
        self.env.out("mode480_set flycast pure")
        self.assertIn("deflicker_flycast=off\n", self.conf())
        self.assertEqual(self.env.out("mode480_level flycast").strip(), "strong")
        self.assertEqual(self.env.out("mode480_state flycast").strip(), "pure")
        # Uma linha com dois programas grava os dois.
        self.env.out("mode480_set laserdisc filter light")
        self.assertIn("deflicker_hypseus=light\n", self.conf())
        self.assertIn("mode480_singe=filter\n", self.conf())
        # O que a linha nao tem, um estado ou nivel que nao existe: nada.
        for bad in ("desktop 240p", "fightcade 480i", "flycast 480i", "flycast filter blur"):
            self.assertNotEqual(self.env.run("mode480_set " + bad).returncode, 0, bad)
        self.assertNotIn("mode480_desktop", self.conf())

    def test_groovymame_and_retroarch_cores(self):
        mame = self.env.etc / "mame.ini"
        mame.write_text("interlace                 1\n")
        ra = self.env.dir / "retroarch"
        env = {"RA_HOME": str(ra)}
        self.env.out("mode480_set groovymame 240p", env)
        self.assertRegex(mame.read_text(), r"(?m)^interlace +0$")
        self.env.out("mode480_set groovymame pure", env)
        self.assertRegex(mame.read_text(), r"(?m)^interlace +1$")
        self.assertIn("deflicker_groovymame=off\n", self.conf())
        self.env.out("mode480_set psx 240p; mode480_set mame2010 filter", env)
        psx = (ra / "config/PCSX-ReARMed/PCSX-ReARMed.switchres.ini").read_text()
        self.assertTrue(psx.endswith("interlace 0\n"))
        # Sem o cabecalho "# FliperOS": as atualizacoes nao o regravam.
        self.assertFalse(psx.startswith("# FliperOS"))
        self.assertTrue((ra / "config/MAME 2010/MAME 2010.switchres.ini").read_text().endswith("interlace 1\n"))
        self.assertIn("deflicker_pcsx_rearmed=medium\n", self.conf())

    def test_save_applies_only_what_changed_with_the_chosen_level(self):
        self.env.out("mode480_save 'flycast=240p,pcsx2=filter,desktop=pure,other=filter'",
                     {"MODE480_LEVEL_pcsx2": "light", "MODE480_LEVEL_other": "strong"})
        conf = self.conf()
        self.assertNotIn("mode480_flycast", conf)
        self.assertIn("mode480_pcsx2=filter\n", conf)
        self.assertIn("deflicker_pcsx2=light\n", conf)
        self.assertIn("deflicker_desktop=off\n", conf)
        # A linha "other" e o nivel de todo o resto.
        self.assertIn("deflicker=strong\n", conf)
        self.assertEqual(self.env.out("deflicker_level").strip(), "strong")

    def colour_bin(self, ctm="no"):
        """fliperos-color falso: responde o caps e registra cada chamada."""
        log = self.env.dir / "color.log"
        self.env.stub("fliperos-color", 'echo "$*" >> %s\n[ "$1" = caps ] && printf "lut 256\\nctm %s\\nrange output_csc\\n"\n'
                      'exit 0\n' % (log, ctm))
        return {"COLOR_BIN": str(self.env.bin / "fliperos-color")}, log

    def test_colour_parameters(self):
        table = [r.split("|") for r in self.env.out("color_table").splitlines()]
        keys = [r[0] for r in table]
        self.assertEqual(keys, ["brightness", "contrast", "gamma", "temperature", "red_gain", "green_gain",
                                "blue_gain", "red_offset", "green_offset", "blue_offset", "red_gamma",
                                "green_gamma", "blue_gamma", "saturation", "hue"])
        self.assertEqual(self.env.out("color_get gamma").strip(), "100")
        # Fora da faixa: o limite; nao numero ou chave que nao existe: nada.
        self.env.out("color_set brightness 99; color_set hue -500")
        self.assertIn("color_brightness=50\n", self.conf())
        self.assertIn("color_hue=-180\n", self.conf())
        self.assertNotEqual(self.env.run("color_set gamma alto").returncode, 0)
        self.assertNotEqual(self.env.run("color_set sharpness 3").returncode, 0)
        self.assertEqual(self.env.out("color_pretty gamma 125").strip(), "1.25")
        self.assertEqual(self.env.out("color_pretty temperature 9300").strip(), "9300 K")
        self.assertEqual(self.env.out("color_pretty brightness 5").strip(), "+5")
        self.env.out("color_range_set limited")
        self.assertEqual(self.env.out("color_range").strip(), "limited")
        self.assertEqual(self.env.run("color_changed").returncode, 0)
        self.env.out("color_reset")
        self.assertNotIn("color_", self.conf())
        self.assertNotEqual(self.env.run("color_changed").returncode, 0)

    def test_colour_apply_picks_hardware_or_software_matrix(self):
        env, log = self.colour_bin("no")
        self.env.out("color_apply", env)
        # Sem CTM na placa: a saturacao e o matiz pela camada.
        self.assertIn("color_ctm=sw\n", self.conf())
        self.assertEqual(log.read_text().splitlines(), ["caps", "apply"])
        env, log = self.colour_bin("yes")
        self.env.out("color_apply", env)
        self.assertIn("color_ctm=hw\n", self.conf())

    def test_in_video_setup(self):
        screen = (ROOT / "fliperos-setup/screens/video-setup.sh").read_text()
        self.assertIn('"colour|Colour calibration|', screen)
        self.assertIn("colour) screen_colour ;;", screen)
        calibrate = screen.split("screen_colour_calibrate()")[1]
        self.assertIn('python3 "$SETUP_DIR/gui/color-calibrate.py"', calibrate)
        self.assertIn("FLIPEROS_COLOR_FILE=", calibrate)
        self.assertTrue((ROOT / "fliperos-setup/gui/color-calibrate.py").is_file())
        self.assertIn('"mode480|480i hacks|', screen)
        self.assertIn("mode480) screen_mode480 ;;", screen)
        body = screen.split("screen_mode480()")[1]
        self.assertIn("UI_GRID_LIVE=1", body)
        self.assertIn('"240p|640x240;filter|480i filter;pure|480i pure"', body)
        dialog = screen.split("screen_deflicker_level()")[1]
        for level in ("preview", "light", "medium", "strong"):
            self.assertIn('"%s|' % level, dialog)
        preview = screen.split("screen_deflicker_preview()")[1]
        self.assertIn('--mode 640x480@60 python3 "$SETUP_DIR/gui/flicker-preview.py"', preview)
        self.assertIn("FLIPEROS_DEFLICKER_FILE=", preview)
        self.assertTrue((ROOT / "fliperos-setup/gui/flicker-preview.py").is_file())


class SettingsCliTests(Base):
    """fliperos-setup --settings / --setting (lib/system.sh): os ajustes que
    o painel web muda."""

    def test_list_and_set(self):
        env = {"COLOR_BIN": str(self.env.dir / "none")}
        rows = [line.split("|") for line in self.env.out("settings_list", env).splitlines()]
        self.assertTrue(all(len(r) == 7 for r in rows), rows)
        keys = [r[0] for r in rows]
        for key in ("launcher", "latency", "debug", "menu_sounds", "mode480.flycast", "deflicker.flycast",
                    "color.gamma", "color.hue"):
            self.assertIn(key, keys)
        # Nada que possa deixar o gabinete sem imagem.
        self.assertFalse([k for k in keys if k in ("monitor", "resolution", "amd_driver")])
        gamma = rows[keys.index("color.gamma")]
        # O passo vai junto (o slider do painel anda de 5 em 5 no gama).
        self.assertEqual((gamma[1], gamma[3], gamma[5]), ("Colour", "number", "50..200:5"))
        self.assertIn("240p=640x240;filter=480i filter;pure=480i pure", rows[keys.index("mode480.flycast")][5])
        self.assertIn("filter=480i filter;pure=480i pure", rows[keys.index("mode480.desktop")][5])
        # Mudar: pelas funcoes do Setup; chave ou valor que nao existe, 2.
        self.env.out("settings_set color.gamma 130; settings_set mode480.flycast pure; settings_set deflicker.pcsx2 strong",
                     env)
        conf = (self.env.etc / "fliperos.conf").read_text()
        for line in ("color_gamma=130", "mode480_flycast=pure", "deflicker_level_pcsx2=strong", "color_ctm=sw"):
            self.assertIn(line + "\n", conf)
        # O voltar ao padrao das cores: um botao, que apaga tudo (a faixa
        # RGB tambem) e aplica.
        reset = rows[keys.index("color.reset")]
        self.assertEqual((reset[1], reset[3], reset[4], reset[5]), ("Colour", "action", "", ""))
        self.env.out("color_range_set limited; settings_set color.reset 1", env)
        self.assertNotIn("color_gamma", (self.env.etc / "fliperos.conf").read_text())
        self.assertNotIn("color_range", (self.env.etc / "fliperos.conf").read_text())
        for bad in ("monitor arcade_15", "latency fast", "mode480.desktop 240p", "deflicker.flycast blur",
                    "service.nope boot", "color.gamma abc", "launcher nothere"):
            self.assertEqual(self.env.run("settings_set " + bad, env).returncode, 2, bad)
        self.assertIn('settings_set "${2:-}" "${3:-}"', (SETUP / "fliperos-setup").read_text())

    def test_video_audio_and_power_rows(self):
        # O que faltava do Video Setup e do Audio Setup no painel, e desligar.
        env = {"COLOR_BIN": str(self.env.dir / "none"), "ASOUND_CONF": str(self.env.dir / "asound.conf"),
               "SPLASH_DIR": str(self.env.dir / "none"), "SPLASH_BUNDLED": str(self.env.dir / "none"),
               "PLYMOUTH_THEMES": str(self.env.dir / "none")}
        self.env.stub("aplay", "echo 'card 1: Generic [HD-Audio Generic], device 0: ALC887 Analog [ALC887 Analog]'")
        rows = {r.split("|")[0]: r.split("|") for r in self.env.out("settings_list", env).splitlines()}
        self.assertEqual(rows["orientation"][1:5], ["Video", "Monitor orientation", "choice", "horizontal"])
        self.assertEqual(rows["audio_card"][5], "1_0=HD-Audio Generic - ALC887 Analog")
        self.assertEqual(rows["mame_latency"][3:6], ["number", "0.0", "0..50:0.5"])
        for key in ("audio.test", "power.reboot", "power.poweroff"):
            self.assertEqual(rows[key][3], "action", key)
        # Um monitor so: os jogos de varias telas nao aparecem nem mudam.
        self.assertNotIn("mm_games", rows)
        self.assertEqual(self.env.run("settings_set mm_games off", env).returncode, 2)
        self.env.out("settings_set audio_card 1_0; settings_set mame_latency 12.5", env)
        self.assertIn("alsa=1,0\n", (self.env.etc / "fliperos.conf").read_text())
        self.assertIn("12.5", self.env.out('ini_get "$MAME_INI" audio_latency', env))
        # A orientacao pelas funcoes do Monitor Orientation (o boot aqui de mentira).
        out = self.env.out("orientation_boot() { echo \"boot $1\"; }; downloader_filter_orientation() { echo filters; }; "
                           "settings_set orientation vertical-cw; settings_set orientation vertical-cw", env)
        self.assertEqual(out.split(), ["boot", "vertical-cw", "filters"])
        self.assertIn("orientation=vertical-cw\n", (self.env.etc / "fliperos.conf").read_text())
        for bad in ("orientation sideways", "audio_card 7_0", "audio_card 1,0", "mame_latency 51", "splash nothere"):
            self.assertEqual(self.env.run("settings_set " + bad, env).returncode, 2, bad)
        # Desligar e reiniciar: depois da resposta ao painel.
        self.env.stub("systemd-run", 'echo "systemd-run $*" >> %s' % self.env.writes)
        self.env.out("settings_set power.reboot 1", env)
        self.assertIn("systemd-run --on-active=2 --unit=fliperos-web-power systemctl reboot",
                      self.env.writes.read_text())

    def test_wifi_and_password_without_a_screen(self):
        # Setup > Network e Setup > System > Password pelo painel web.
        env = {"COLOR_BIN": str(self.env.dir / "none")}
        self.env.stub("nmcli", textwrap.dedent("""\
            case "$*" in
              "-t -f DEVICE,TYPE,STATE,CONNECTION device status") printf 'lo:loopback:unmanaged:\\nwlan0:wifi:connected:Casa\\n' ;;
              "-t -f DEVICE,TYPE device status") printf 'wlan0:wifi\\n' ;;
              *"device wifi list"*) printf 'Casa:80:WPA2\\nVizinho:30:\\n' ;;
              *) echo "nmcli $*" >> %s ;;
            esac""" % self.env.writes))
        self.assertEqual(self.env.out("net_cli status", env).splitlines(), ["wlan0|wifi|connected|Casa|"])
        self.assertEqual(self.env.out("net_cli scan", env).splitlines(), ["wlan0|Casa|80|WPA2", "wlan0|Vizinho|30|"])
        self.env.out("net_cli connect wlan0 Casa <<< 'segredo1'", env)
        self.assertIn("nmcli --wait 45 device wifi connect Casa ifname wlan0 password segredo1",
                      self.env.writes.read_text())
        for bad in ("net_cli connect eth9 Casa", "net_cli connect wlan0 ''", "net_cli nope"):
            self.assertEqual(self.env.run(bad + " < /dev/null", env).returncode, 2, bad)
        setup = (SETUP / "fliperos-setup").read_text()
        self.assertIn('net_cli "${@:2}"', setup)
        # A senha so pela entrada; curta demais, 2.
        self.assertIn('IFS= read -r pass || true\n      password_valid "$pass" || return 2', setup)

    def test_boot_game_in_the_launcher_list(self):
        # O jogo direto no boot: so aparece (e so vale) depois de escolhido, no
        # Setup ou na pagina do jogo no painel web (--bootgame).
        env = {"COLOR_BIN": str(self.env.dir / "none")}

        def launcher():
            return next(line.split("|") for line in self.env.out("settings_list", env).splitlines()
                        if line.startswith("launcher|"))
        self.assertNotIn("game=", launcher()[5])
        self.assertEqual(self.env.run("settings_set launcher game", env).returncode, 2)
        (self.env.etc / "bootgame").write_text("Street Fighter II\n/r/sf2.zip\ngroovymame\nsf2\n")
        self.assertIn("game=A game: Street Fighter II", launcher()[5])
        self.env.out("settings_set launcher game", env)
        self.assertEqual(self.env.out("launcher_current", env).strip(), "game")
        setup = (SETUP / "fliperos-setup").read_text()
        self.assertIn('bootgame_set "${2:-}" "${3:-}" || return 2', setup)
        self.assertIn('geometry_cli "${@:2}"', setup)

    def test_geometry_without_a_screen(self):
        # Video Setup > Geometry pelo painel web: o status, um crt_range
        # digitado (so da faixa do monitor) e a volta ao padrao.
        env = {"COLOR_BIN": str(self.env.dir / "none")}
        self.env.out("conf_set monitor generic_15", env)
        status = dict(line.split("=", 1) for line in self.env.out("geometry_cli status", env).splitlines())
        self.assertEqual((status["monitor"], status["range"]), ("generic_15", ""))
        good = "15625-16200,49.5-65,2.0,4.7,8.0,0.064,0.192,1.024,0,0,192,288,448,576"
        self.assertEqual(self.env.run("geometry_cli set 'not a range'", env).returncode, 2)
        self.assertEqual(self.env.run("geometry_cli set 31000-32000,50-70,1,1,1,1,1,1,0,0,192,288,448,576", env)
                         .returncode, 3)
        self.assertEqual(self.env.run("geometry_cli set " + good, env).returncode, 0)
        self.assertIn("geometry=" + good + "\n", (self.env.etc / "fliperos.conf").read_text())
        self.env.out("geometry_cli reset", env)
        self.assertNotIn("geometry=", (self.env.etc / "fliperos.conf").read_text())

    def test_live_screen_quality(self):
        # A qualidade da tela ao vivo so aparece (e muda) com o go2rtc instalado.
        go2rtc = self.env.dir / "go2rtc"
        env = {"COLOR_BIN": str(self.env.dir / "none"), "STREAM_GO2RTC": str(go2rtc)}
        keys = [line.split("|")[0] for line in self.env.out("settings_list", env).splitlines()]
        self.assertNotIn("stream_quality", keys)
        self.assertEqual(self.env.run("settings_set stream_quality high", env).returncode, 2)
        go2rtc.write_text("#!/bin/sh\n")
        go2rtc.chmod(0o755)
        rows = {r[0]: r for r in (line.split("|") for line in self.env.out("settings_list", env).splitlines())}
        self.assertEqual(rows["stream_quality"][4], "normal")
        self.assertIn("max=Maximum (network cable)", rows["stream_quality"][5])
        self.env.out("settings_set stream_quality high", env)
        self.assertIn("stream_quality=high\n", (self.env.etc / "fliperos.conf").read_text())
        rows = {r[0]: r for r in (line.split("|") for line in self.env.out("settings_list", env).splitlines())}
        self.assertEqual(rows["stream_quality"][4], "high")
        self.assertEqual(self.env.run("settings_set stream_quality ultra", env).returncode, 2)


class DownloaderCliTests(Base):
    """fliperos-setup --downloader (lib/downloader.sh, downloader_cli): o
    Downloader sem tela, para o painel web."""

    def test_checks_before_anything(self):
        state = self.env.dir / "dl"
        env = {"DOWNLOADER_STATE": str(state), "DOWNLOADER": str(self.env.bin / "fliperos-downloader")}
        self.env.stub("fliperos-downloader", 'echo "$*" >> %s/dl.log' % self.env.dir)
        self.env.stub("systemctl", "true")
        for bad in ("bogus", "add roms http://x", "add games magnet:?xt=1", "remove all"):
            self.assertEqual(self.env.run("downloader_cli " + bad, env).returncode, 2, bad)
        # Sem filtro escolhido no Setup, nada comeca.
        self.assertEqual(self.env.run("downloader_cli start", env).returncode, 3)
        self.env.out("downloader_cli add chds 'magnet:?xt=urn:btih:abc'", env)
        self.assertIn("add chds magnet:?xt=urn:btih:abc --progress\n", (self.env.dir / "dl.log").read_text())
        out = self.env.out("downloader_cli status", env)
        self.assertIn("filter=not chosen yet\n", out)


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
        self.assertNotIn('"Monitor-', text)
        self.assertIn('Option "BlankTime" "0"', text)

    def test_single_monitor_has_no_layout(self):
        (self.env.etc / "fliperos.conf").write_text(
            "connector=VGA-1\nmonitor=generic_15\nboot_resolution=640x480iS\n")
        self.env.out("xorg_generate")
        text = (self.env.etc / "xorg.conf").read_text()
        self.assertNotIn("Primary", text)
        self.assertNotIn("RightOf", text)
        self.assertEqual(text.count('Section "Monitor"'), 1)

    def test_extra_monitors_side_by_side_in_game_order(self):
        # A tela 1 dos jogos a esquerda; o principal e a tela primaria, onde
        # os programas de uma tela so abrem.
        (self.env.etc / "fliperos.conf").write_text(
            "connector=VGA-1\nmonitor=generic_15\nboot_resolution=640x480iS\nscreens=DVI-I-1,VGA-1,DVI-I-2\n")
        self.env.out("xorg_generate")
        text = (self.env.etc / "xorg.conf").read_text()
        for line in ('Option "Monitor-VGA-1" "CRT"', 'Option "Monitor-DVI-I-1" "CRT2"',
                     'Option "Monitor-DVI-I-2" "CRT3"'):
            self.assertIn(line, text)
        sections = {}
        for block in text.split('Section "Monitor"')[1:]:
            block = block.split("EndSection")[0]
            sections[re.search(r'Identifier "(\w+)"', block).group(1)] = block
        self.assertNotIn("RightOf", sections["CRT2"])
        self.assertIn('Option "RightOf" "CRT2"', sections["CRT"])
        self.assertIn('Option "RightOf" "CRT"', sections["CRT3"])
        self.assertIn('Option "Primary" "true"', sections["CRT"])
        for block in sections.values():
            self.assertIn('Modeline "640x480i" 13.038', block)
        self.assertEqual(text.count('Section "Screen"'), 1)


class MultiMonitorTests(Base):
    def setUp(self):
        super().setUp()
        self.env.card("card0", "radeon")
        for name in ("card0-VGA-1", "card0-DVI-I-1", "card0-DVI-I-2", "card0-HDMI-A-1"):
            self.env.connector(name, "connected" if name == "card0-VGA-1" else "disconnected")
        self.env.card("card1", "radeon")
        self.env.connector("card1-VGA-1")
        (self.env.etc / "fliperos.conf").write_text(
            "connector=VGA-1\ncard=card0\nmonitor=generic_15\nforced=1\ndetection=se\n"
            "kernel_video=video=VGA-1:640x480iSe\nboot_resolution=640x480iS\n")

    def conf(self):
        return (self.env.etc / "fliperos.conf").read_text()

    def test_candidates_are_free_outputs_of_the_same_card(self):
        # As analogicas primeiro; a digital (conversor ativo) e as de outra
        # placa sao experimentais.
        self.assertEqual(self.env.out("mm_candidates").split(), ["DVI-I-1", "DVI-I-2", "HDMI-A-1", "card1:VGA-1"])
        self.env.out("mm_set_extra 2 DVI-I-1")
        self.assertEqual(self.env.out("mm_candidates").split(), ["DVI-I-2", "HDMI-A-1", "card1:VGA-1"])
        # O monitor que ja tem a saida pode ficar com ela.
        self.assertEqual(self.env.out("mm_candidates DVI-I-1").split(),
                         ["DVI-I-1", "DVI-I-2", "HDMI-A-1", "card1:VGA-1"])

    def test_extra_on_a_second_card(self):
        self.env.out("mm_save VGA-1 card1:VGA-1 DVI-I-1")
        self.assertEqual(self.env.out("mm_extras").split(), ["card1:VGA-1", "DVI-I-1"])
        # O video= vale pelo nome em todas as placas: o VGA-1 da segunda fica
        # com o do principal, sem trocar o dele.
        self.env.out("conf_set orientation vertical-cw")
        out = self.env.out("boot_compose 'quiet'").split()
        self.assertEqual([w for w in out if w.startswith("video=VGA-1:")],
                         ["video=VGA-1:640x480iSe,panel_orientation=right_side_up"])
        self.assertIn("video=DVI-I-1:640x480iSe,panel_orientation=right_side_up", out)
        # Ligar e desligar mexe na saida da placa certa.
        self.env.cmdline.write_text("quiet video=VGA-1:640x480iSe video=DVI-I-1:640x480iSe\n")
        for name in ("card1-VGA-1", "card0-DVI-I-1"):
            (self.env.drm / name / "status").write_text("connected\n")
        self.env.out("mm_outputs main")
        self.assertEqual(self.env.writes.read_text().split(), ["card1-VGA-1=off", "card0-DVI-I-1=off"])
        # Xorg: a placa principal presa pelo BusID, a outra como GPU screen.
        self.env.out("xorg_generate")
        xorg = (self.env.etc / "xorg.conf").read_text()
        self.assertIn('BusID "PCI:0:0:0"', xorg)
        self.assertIn('Option "AutoBindGPU" "true"', xorg)
        self.assertNotIn("Monitor-card1", xorg)
        self.assertIn('Option "Monitor-DVI-I-1" "CRT2"', xorg)
        self.assertEqual(xorg.count('Section "Monitor"'), 2)
        # Uma so placa: nada de BusID.
        self.env.out("mm_save VGA-1 DVI-I-1; xorg_generate")
        self.assertNotIn("BusID", (self.env.etc / "xorg.conf").read_text())

    def test_digital_extra_gets_the_super_resolution(self):
        # O TMDS nao desce abaixo de 25 MHz: o conversor ativo recebe a super
        # resolucao, e o Xorg nao lhe da o modeline de dotclock baixo.
        self.env.out("mm_save VGA-1 HDMI-A-1 DVI-I-1")
        out = self.env.out("boot_compose 'quiet'").split()
        self.assertIn("video=HDMI-A-1:1280x480iSe", out)
        self.assertIn("video=DVI-I-1:640x480iSe", out)
        self.env.out("xorg_generate")
        xorg = (self.env.etc / "xorg.conf").read_text()
        sections = {s.split('"')[1]: s for s in xorg.split('Section "Monitor"')[1:]}
        self.assertIn("Modeline", sections["CRT"])
        self.assertIn("Modeline", sections["CRT3"])
        self.assertNotIn("Modeline", sections["CRT2"])
        self.assertIn('Option "RightOf" "CRT"', sections["CRT2"])

    def test_single_monitor_by_default(self):
        self.assertEqual(self.env.out("mm_screens").split(), ["VGA-1"])
        self.assertEqual(self.env.out("mm_count").strip(), "1")
        self.assertEqual(self.env.out("mm_extras"), "")

    def test_set_extras_keeps_the_order(self):
        self.env.out("mm_set_extra 2 DVI-I-1; mm_set_extra 3 DVI-I-2")
        self.assertIn("screens=VGA-1,DVI-I-1,DVI-I-2\n", self.conf())
        self.env.out("mm_save DVI-I-1 VGA-1 DVI-I-2")
        self.assertEqual(self.env.out("mm_extras").split(), ["DVI-I-1", "DVI-I-2"])
        # Trocar a saida de um monitor: a nova entra no fim.
        self.env.out("mm_set_extra 3 off")
        self.assertIn("screens=DVI-I-1,VGA-1\n", self.conf())
        self.env.out("mm_set_extra 2 DVI-I-2")
        self.assertIn("screens=VGA-1,DVI-I-2\n", self.conf())
        # So o principal: a chave sai.
        self.env.out("mm_set_extra 2 off")
        self.assertNotIn("screens=", self.conf())
        self.assertEqual(self.env.out("mm_count").strip(), "1")

    def test_stale_list_without_the_main_output_is_ignored(self):
        self.env.out("conf_set screens HDMI-A-1,DVI-I-1")
        self.assertEqual(self.env.out("mm_screens").split(), ["VGA-1"])

    def test_orders(self):
        self.env.out("mm_save VGA-1 DVI-I-1")
        self.assertEqual(self.env.out("mm_orders").splitlines(),
                         ["VGA-1,DVI-I-1|VGA-1, DVI-I-1", "DVI-I-1,VGA-1|DVI-I-1, VGA-1"])
        self.env.out("mm_save VGA-1 DVI-I-1 DVI-I-2")
        orders = self.env.out("mm_orders").splitlines()
        self.assertEqual(len(orders), 6)
        self.assertEqual(len(set(orders)), 6)

    def test_boot_line_forces_the_extras_in_the_main_mode(self):
        self.env.out("mm_save DVI-I-1 VGA-1 DVI-I-2")
        out = self.env.out("boot_compose 'quiet'").split()
        self.assertIn("video=VGA-1:640x480iSe", out)
        self.assertIn("video=DVI-I-1:640x480iSe", out)
        self.assertIn("video=DVI-I-2:640x480iSe", out)
        self.env.out("mm_set_extra 2 off; mm_set_extra 2 off")
        out = self.env.out("boot_compose '%s'" % " ".join(out))
        self.assertNotIn("DVI-I", out)

    def test_boot_line_rotates_every_monitor(self):
        self.env.out("mm_save VGA-1 DVI-I-1; conf_set orientation vertical-cw")
        out = self.env.out("boot_compose 'quiet'").split()
        self.assertIn("video=VGA-1:640x480iSe,panel_orientation=right_side_up", out)
        self.assertIn("video=DVI-I-1:640x480iSe,panel_orientation=right_side_up", out)
        self.assertEqual(out.count("fbcon=rotate:1"), 1)

    def test_extras_of_an_edid_boot_use_the_preset_mode(self):
        self.env.out("conf_set kernel_video 'video=VGA-1:e drm.edid_firmware=VGA-1:edid/custom_resolution.bin'")
        self.assertEqual(self.env.out("mm_kernel_spec").strip(), "640x480iSe")
        self.env.card("card2", "nouveau")
        self.env.out("conf_set card card2")
        self.assertEqual(self.env.out("mm_kernel_spec").strip(), "1280x480iSe")

    def test_outputs_only_touch_extras_of_this_boot(self):
        # Ligar uma saida sem o modo dela no boot daria 31 kHz ao CRT.
        self.env.out("mm_save VGA-1 DVI-I-1 DVI-I-2")
        self.env.cmdline.write_text("quiet video=VGA-1:640x480iSe video=DVI-I-1:640x480iSe\n")
        self.assertEqual(self.env.run("mm_pending").returncode, 0)
        (self.env.drm / "card0-DVI-I-1" / "status").write_text("connected\n")
        self.env.out("mm_outputs main")
        self.assertEqual(self.env.writes.read_text(), "card0-DVI-I-1=off\n")
        self.env.writes.write_text("")
        (self.env.drm / "card0-DVI-I-1" / "status").write_text("disconnected\n")
        self.env.out("mm_outputs all")
        self.assertEqual(self.env.writes.read_text(), "card0-DVI-I-1=on\n")
        self.env.cmdline.write_text("quiet video=VGA-1:640x480iSe video=DVI-I-1:640x480iSe video=DVI-I-2:640x480iSe\n")
        self.assertNotEqual(self.env.run("mm_pending").returncode, 0)

    def test_blink_restores_each_output(self):
        self.env.out("mm_save VGA-1 DVI-I-1")
        self.env.out("mm_blink DVI-I-1; mm_blink VGA-1; conf_set forced 0; mm_blink VGA-1")
        self.assertEqual(self.env.writes.read_text().split(),
                         ["card0-DVI-I-1=off", "card0-DVI-I-1=on", "card0-VGA-1=off", "card0-VGA-1=on",
                          "card0-VGA-1=off", "card0-VGA-1=detect"])

    def test_new_main_output_forgets_the_extras(self):
        self.env.out("mm_save VGA-1 DVI-I-1")
        self.env.out("video_save_result card0-VGA-1 se generic_15")
        self.assertIn("screens=VGA-1,DVI-I-1\n", self.conf())
        self.env.out("video_save_result card0-DVI-I-1 se generic_15")
        self.assertNotIn("screens=", self.conf())
        self.assertIn("screens", self.env.out("echo $VIDEO_CONF_KEYS").split())

    def test_multiscreen_games_toggle(self):
        self.env.out("mm_save VGA-1 DVI-I-1")
        self.assertEqual(self.env.run("mm_games_on").returncode, 0)
        self.env.out("mm_set_games off")
        self.assertIn("multiscreen=off\n", self.conf())
        self.assertNotEqual(self.env.run("mm_games_on").returncode, 0)
        # Desligado, nada de preparar os jogos de varias telas do GroovyMAME.
        gen = self.env.dir / "gen"
        gen.write_text("#!/bin/sh\necho gen >> %s\n" % (self.env.dir / "gen.log"))
        gen.chmod(0o755)
        self.env.out("MAME_SCREENS=%s; mm_mame_prepare" % gen)
        self.assertFalse((self.env.dir / "gen.log").exists())
        self.env.out("mm_set_games on")
        self.assertNotIn("multiscreen", self.conf())
        self.env.out("MAME_SCREENS=%s; mm_mame_prepare" % gen)
        self.assertTrue((self.env.dir / "gen.log").exists())

    def test_cli_and_screen(self):
        entry = (SETUP / "fliperos-setup").read_text()
        self.assertIn('    --outputs)\n      mm_outputs "${2:-all}"', entry)
        self.assertLess(entry.index("--outputs)"), entry.index("if ! have gum"))
        video = (SETUP / "screens/video-setup.sh").read_text()
        self.assertIn('"monitors|Multiple Monitors|', video)
        self.assertIn("monitors) screen_multi_monitor ;;", video)
        self.assertIn('entries+=("games|Multi-Screen Games: $games")', video)
        self.assertIn("games) screen_mm_games ;;", video)


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
        Path(str(target) + str(self.env.etc / "patch-level")).write_text("12\n")
        self.env.out("install_configure_video '%s'" % target, {"FLIPEROS_SETUP_VERSION": "0.10"})
        # Com o What's new desta versao e do update da ISO ja vistos: um disco
        # novo nao tem nada de novo.
        self.assertEqual(conf.read_text(), "connector=VGA-1\nalsa=1,0\nwhatsnew_version=0.10\nwhatsnew_level=12\n")

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

    def test_browse_shows_a_disk_once_not_its_uuid_shortcut(self):
        media = self.env.dir / "media"
        (media / "TOSHIBA_HDWD110").mkdir(parents=True)
        (media / "5E2C-4AEF").symlink_to("TOSHIBA_HDWD110")
        (media / "roms").symlink_to(self.env.dir)
        r = self.env.run("""
            source %s/lib/ui.sh
            ui_menu() { shift 3; printf '%%s\\n' "$@" >&2; return 1; }
            ui_browse T X %s dir
        """ % (SETUP, media))
        self.assertIn("0|TOSHIBA_HDWD110/", r.stderr)
        self.assertIn("roms/", r.stderr)
        self.assertNotIn("5E2C-4AEF", r.stderr)

    def test_online_from_the_networkmanager_state(self):
        state = self.env.dir / "nmstate"
        self.env.stub("nmcli", 'case "$*" in "-t -f STATE general") cat %s ;; esac' % state)
        for value, online in (("connected", 0), ("connected (site only)", 0),
                              ("connected (local only)", 1), ("disconnected", 1), ("connecting", 1)):
            state.write_text(value + "\n")
            self.assertEqual(self.env.run("net_online").returncode, online, value)
        # Sem o NetworkManager: a rota padrao.
        state.write_text("")
        self.env.stub("ip", "echo 'default via 192.168.1.1 dev eth0'")
        self.assertEqual(self.env.run("net_online").returncode, 0)
        self.env.stub("ip", ":")
        self.assertEqual(self.env.run("net_online").returncode, 1)

    def need_internet(self, wifi, answer):
        state = self.env.dir / "nmstate"
        state.write_text("disconnected\n")
        self.env.stub("nmcli", 'case "$*" in "-t -f STATE general") cat %s ;; '
                               '"-t -f DEVICE,TYPE device status") echo eth0:ethernet; %s ;; esac'
                      % (state, "echo wlan0:wifi" if wifi else ":"))
        return self.env.run("""
            source %s/lib/ui.sh
            source %s/screens/progress.sh
            source %s/screens/setup-menu.sh
            ui_msg() { echo "msg:$*"; }
            ui_yesno() { echo "yesno:$2"; return %d; }
            screen_wifi() { echo "wifi:$*"; echo connected > %s; }
            run_with_progress() { echo "run:$*"; }
            run_online "Installing X" "" emulators_install x
        """ % (SETUP, SETUP, SETUP, 0 if answer else 1, state))

    def test_offline_with_wifi_offers_it_and_goes_on_once_connected(self):
        r = self.need_internet(wifi=True, answer=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("yesno:This needs the internet", r.stdout)
        self.assertIn("wifi:0 quiet", r.stdout)
        self.assertIn("run:Installing X  emulators_install x", r.stdout)

    def test_offline_wifi_refused_or_no_adapter_does_not_run(self):
        r = self.need_internet(wifi=True, answer=False)
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("run:", r.stdout)
        self.assertNotIn("wifi:", r.stdout)
        r = self.need_internet(wifi=False, answer=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("msg:Installing X", r.stdout)
        self.assertIn("Plug in a network cable", r.stdout)
        self.assertNotIn("yesno:", r.stdout)

    def test_menus_that_download_check_the_internet_first(self):
        menu = (SETUP / "screens" / "setup-menu.sh").read_text()
        for line in ('downloader) screen_need_internet "The Downloader" && screen_downloads ;;',
                     'scraper) screen_need_internet "The Scraper" && screen_scraper ;;',
                     'update) screen_need_internet "System Update" && screen_update ;;'):
            self.assertIn(line, menu)
        self.assertNotRegex(menu, r'run_with_progress "(Installing|Downloading|Updating)')


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

    def test_volume_leveler_is_optional_and_off_by_default(self):
        conf = self.env.dir / "asound.conf"
        plugin = self.env.dir / "ladspa" / "sc4_1882.so"
        env = {"ASOUND_CONF": str(conf), "AUDIO_LEVELER_PLUGIN": str(plugin)}
        self.env.out("audio_set_default 1,3", env)
        self.assertNotIn("pcm.!default", conf.read_text())
        self.assertEqual(self.env.run("audio_leveler_enabled", env).returncode, 1)
        # Sem o swh-plugins: nao liga e o som fica como esta.
        self.assertEqual(self.env.run("audio_leveler_set on", env).returncode, 1)
        self.assertNotIn("pcm.!default", conf.read_text())
        plugin.parent.mkdir()
        plugin.write_text("")
        self.env.out("audio_leveler_set on", env)
        text = conf.read_text()
        self.assertIn("defaults.pcm.card 1\n", text)
        self.assertIn('pcm.!default {\n    type plug\n    slave.pcm "fliperos_leveler"\n}', text)
        # O plug em bloco: "plug:dmix:1,3" numa string nao abre (o ALSA le o
        # ",3" como argumento do plug) e deixava tudo mudo.
        self.assertIn('slave.pcm {\n        type plug\n        slave.pcm "dmix:1,3"\n    }', text)
        self.assertNotIn("plug:dmix", text)
        self.assertIn('path "%s"' % plugin.parent, text)
        self.assertIn("label sc4\n        input { controls [ 0 20 400 -20 4 6 6 ] }", text)
        # Trocar a placa mantem o nivelador, na placa nova.
        self.env.out("audio_set_default 0,0", env)
        self.assertIn('slave.pcm "dmix:0,0"', conf.read_text())
        # Sem o plugin (apagado depois), o asound.conf volta ao simples.
        plugin.unlink()
        self.env.out("audio_write_conf", env)
        self.assertNotIn("ladspa", conf.read_text())
        plugin.write_text("")
        self.env.out("audio_leveler_set off", env)
        self.assertNotIn("ladspa", conf.read_text())
        self.assertIn("audio_leveler=off\n", (self.env.etc / "fliperos.conf").read_text())

    def test_live_screen_sound_copies_the_output_only_with_the_loopback(self):
        # Live screen sound: o mesmo som no dmix da placa e no do loopback
        # (o fliperos_tee), so com o loopback aberto; sem ele o default nao
        # abriria e tudo ficaria mudo.
        conf = self.env.dir / "asound.conf"
        cards = self.env.dir / "cards"
        cards.write_text(" 0 [PCH            ]: HDA-Intel - HDA Intel PCH\n")
        plugin = self.env.dir / "sc4.so"
        env = {"ASOUND_CONF": str(conf), "AUDIO_PROC_CARDS": str(cards), "AUDIO_LEVELER_PLUGIN": str(plugin)}
        self.env.out("conf_set alsa 0,0; conf_set stream_audio on; audio_write_conf", env)
        self.assertNotIn("fliperos_tee", conf.read_text())
        self.assertEqual(self.env.out("audio_card_id 0", env).strip(), "PCH")
        cards.write_text(cards.read_text() + "10 [FliperOSLoop   ]: Loopback - Loopback\n")
        self.env.out("audio_write_conf", env)
        text = conf.read_text()
        # A placa pelo mesmo dmix dos jogos (o sysdefault: outro dmix da "busy"
        # com algo tocando); o loopback pelo dmix dele, escrito, atras de um
        # plug (o padrao dele nao abre). Visto no gabinete.
        self.assertIn('slaves.a { pcm "sysdefault:0" channels 2 }', text)
        self.assertIn('slaves.b { pcm { type plug slave.pcm "fliperos_loop" } channels 2 }', text)
        self.assertIn('pcm "hw:FliperOSLoop,0,0"\n        format S16_LE\n        rate 48000\n        channels 2\n'
                      '        period_size 1024\n        buffer_size 16384\n', text)
        self.assertNotIn("fliperos_card", text)
        self.assertIn('pcm.fliperos_loopcap {\n    type dsnoop', text)
        # Num dispositivo que nao e o 0 (uma HDMI), o dmix dele.
        self.env.out("conf_set alsa 1,3; audio_write_conf", env)
        self.assertIn('slaves.a { pcm { type plug slave.pcm "dmix:1,3" } channels 2 }', conf.read_text())
        self.env.out("conf_set alsa 0,0; audio_write_conf", env)
        text = conf.read_text()
        self.assertIn('pcm.!default {\n    type plug\n    slave.pcm "fliperos_tee"\n}', text)
        # Com o nivelador, o compressor sai no tee (um default so).
        plugin.write_text("")
        self.env.out("conf_set audio_leveler on; audio_write_conf", env)
        text = conf.read_text()
        self.assertEqual(text.count("pcm.!default"), 1)
        self.assertIn('slave.pcm {\n        type plug\n        slave.pcm "fliperos_tee"\n    }', text)
        # O modulo no timer padrao (o timer_source na placa o deixava ocupado).
        modprobe = self.env.dir / "aloop.conf"
        load = self.env.dir / "aloop.load"
        self.env.stub("modprobe", "exit 0")
        self.env.stub("aplay", "cat > /dev/null; exit 0")
        senv = dict(env, AUDIO_LOOP_MODPROBE=str(modprobe), AUDIO_LOOP_LOAD=str(load))
        self.env.out("audio_stream_set on", senv)
        self.assertEqual(modprobe.read_text(), "options snd-aloop index=10 id=FliperOSLoop pcm_substreams=1\n")
        self.assertEqual(load.read_text(), "snd-aloop\n")
        self.assertIn("fliperos_tee", conf.read_text())
        # O default com a copia nao tocou (uma placa sem S16_LE): volta como estava.
        self.env.stub("aplay", "cat > /dev/null; exit 1")
        self.assertEqual(self.env.run("audio_stream_set on", senv).returncode, 1)
        self.assertNotIn("fliperos_tee", conf.read_text())
        self.assertIn("stream_audio=off\n", (self.env.etc / "fliperos.conf").read_text())
        self.assertFalse(load.exists())
        # Num boot sem o loopback, a sessao tira a copia do asound.conf.
        self.env.stub("aplay", "cat > /dev/null; exit 0")
        self.env.out("audio_stream_set on", senv)
        cards.write_text(" 0 [PCH            ]: HDA-Intel - HDA Intel PCH\n")
        self.env.out("audio_stream_check", senv)
        self.assertNotIn("fliperos_tee", conf.read_text())
        setup = (SETUP / "fliperos-setup").read_text()
        self.assertIn("    --session-start)\n", setup)
        self.assertIn("      audio_stream_check\n", setup.split("    --session-start)\n")[1].split(";;")[0])

    def mixer(self, controls, level=60, switch="on"):
        """amixer falso: lista os controles da placa, responde o nivel e
        registra cada sset."""
        self.calls = self.env.dir / "amixer.log"
        self.calls.write_text("")
        listing = "".join("Simple mixer control '%s',0\\n" % c for c in controls)
        self.env.stub("amixer", textwrap.dedent("""\
            args="$*"
            case $args in
              *scontrols*) printf "%s" ;;
              *sget*) echo "  Front Left: Playback 52 [%d%%] [-10.00dB] [%s]" ;;
              *sset*) echo "${args#*sset }" >> "%s" ;;
            esac""") % (listing, level, switch, self.calls))
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

    def test_volume_get_and_set_for_the_web_panel(self):
        # fliperos-setup --volume get / set N (config/fliperos-web).
        self.mixer(["Master", "PCM"], level=35)
        self.assertEqual(self.env.out("audio_step get").strip(), "35")
        self.env.out("audio_step set 070")
        self.assertEqual(self.calls.read_text().splitlines(), ["PCM 100% unmute", "Master 70% unmute"])
        for bad in ("set 101", "set -5", "set", "set 5x"):
            self.assertEqual(self.env.run("audio_step " + bad).returncode, 1, bad)
        self.assertIn('audio_step "${@:2}"', (SETUP / "fliperos-setup").read_text())
        # state: o volume e o mudo, para o botao Mudo do painel ficar marcado.
        self.assertEqual(self.env.out("audio_step state").strip(), "35 on")
        self.mixer(["Master", "PCM"], level=35, switch="off")
        self.assertEqual(self.env.out("audio_step state").strip(), "35 off")

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
        self.assertIn('run_online "Downloading $label" "" launcher_fetch "$choice" || return 0', screen)
        self.assertLess(screen.index("launcher_fetch "), screen.index('launcher_set "$choice"'))
        self.assertIn("roms/fightcade", self.env.out("frontends_hint fightcade"))
        self.assertEqual(self.env.out("frontends_hint pegasus"), "")

    def test_custom_frontends_are_added_edited_and_deleted(self):
        custom = self.env.etc / "sessions.custom.conf"
        self.env.stub("myfe", "true")
        name = self.env.out('launcher_custom_save "" "My FE" "FOO=1 myfe --full"').strip()
        self.assertEqual(name, "custom-1")
        self.assertEqual(custom.read_text(), "custom-1|kms|FOO=1 myfe --full|custom|My FE\n")
        # Entra na lista como os outros, instalado pelo programa do comando.
        self.assertIn("custom-1|My FE", self.env.out("launcher_available").splitlines())
        self.assertEqual(self.env.out("launcher_label custom-1").strip(), "My FE")
        self.assertEqual(self.env.out("launcher_package custom-1").strip(), "custom")
        self.assertEqual(self.env.out("launcher_fetcher custom-1"), "")
        self.assertEqual(self.env.out('launcher_custom_program "A=1 B_2=x ~/fe -x"').strip(),
                         "/home/fliperos/fe")
        # Um segundo, e a edicao troca a linha sem mexer na ordem dos nomes.
        self.assertEqual(self.env.out('launcher_custom_save "" "Other" "nothere"').strip(), "custom-2")
        self.assertEqual(self.env.run("launcher_installed custom-2").returncode, 1)
        self.assertNotIn("custom-2", self.env.out("launcher_available"))
        self.env.out('launcher_custom_save custom-1 "My FE 2" "myfe"')
        self.assertEqual(self.env.out("launcher_custom_list").splitlines(), ["custom-2|Other", "custom-1|My FE 2"])
        # "|" e quebra de linha nao cabem na tabela.
        for label, cmd in (("A|B", "myfe"), ("Ok", "a | b"), ("", "myfe"), ("Ok", "  ")):
            run = self.env.run('launcher_custom_save "" %s %s' % (shlex.quote(label), shlex.quote(cmd)))
            self.assertEqual(run.returncode, 1, (label, cmd))
        self.assertEqual(len(custom.read_text().splitlines()), 2)
        # Apagar o que abre ao ligar volta o menu do Setup.
        self.env.out("launcher_set custom-1")
        self.env.out("launcher_custom_delete custom-1")
        self.assertEqual(self.env.out("launcher_current").strip(), "setup")
        self.assertEqual(custom.read_text(), "custom-2|kms|nothere|custom|Other\n")
        # Os da tabela do FliperOS nao se apagam por aqui.
        self.assertEqual(self.env.run("launcher_custom_delete retroarch").returncode, 1)
        self.assertEqual(self.env.out('launcher_custom_save "" "Third" "myfe"').strip(), "custom-1")

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


class QuirkTypesTests(Base):
    """Quirks de qualquer USB: o usbhid (controles, pistolas, teclados) e o
    usb-storage (discos), cada um com o seu parametro do kernel."""

    def test_disk_quirk_has_its_own_parameter_and_no_limit_of_four(self):
        self.env.out("quirk_add 'JMicron SATA' ' 152D:0578:U '")
        for i in range(1, 5):
            self.env.out("quirk_add q%d 0x000%d:0x0001:0x40" % (i, i))
        # O limite de 4 e so do usbhid: o disco nao conta nem e barrado.
        self.assertEqual(self.env.run("quirk_add q5 0x0005:0x0001:0x40").returncode, 2)
        self.env.out("quirk_add other 0bda:9210:u")
        self.assertEqual(self.env.out("quirks_count usb-storage").strip(), "2")
        self.assertEqual(self.env.out("quirks_count").strip(), "6")
        # O mesmo aparelho pode ter um de cada tipo, mas nao dois do mesmo.
        self.assertEqual(self.env.run("quirk_add again 152d:0578:ut").returncode, 3)
        line = self.env.out("quirks_cmdline 'quiet usb-storage.quirks=1:1:u splash'").split()
        self.assertEqual(line[:2], ["quiet", "splash"])
        self.assertIn("usbhid.quirks=0x0001:0x0001:0x40,0x0002:0x0001:0x40,0x0003:0x0001:0x40,0x0004:0x0001:0x40",
                      line)
        self.assertIn("usb-storage.quirks=152d:0578:u,0bda:9210:u", line)

    def test_disk_codes_the_kernel_would_not_parse_are_refused(self):
        for bad in ("152d:578:u", "0x152d:0x0578:u", "152d:0578:", "152d:0578:1"):
            self.assertEqual(self.env.run("quirk_add n '%s'" % bad).returncode, 1, bad)

    def test_quirks_are_in_system_not_joysticks(self):
        joy = (SETUP / "screens" / "joysticks.sh").read_text()
        system = (SETUP / "screens" / "setup-menu.sh").read_text().split("screen_setup_system() {")[1].split("\n}\n")[0]
        self.assertNotIn("quirks) screen_quirks", joy)
        self.assertNotIn('"quirks|', joy)
        self.assertIn("quirks) screen_quirks ;;", system)


class ServicesTests(Base):
    """Setup > System > Services: cada servico no boot, depois do boot ou desligado."""

    def setUp(self):
        super().setUp()
        self.log = self.env.dir / "calls"
        self.enabled = self.env.dir / "enabled"
        self.wifi = self.env.dir / "wifi"
        self.log.write_text("")
        self.enabled.write_text("ssh.service\n")
        self.wifi.write_text("enabled\n")
        self.env.stub("systemctl", textwrap.dedent("""\
            case $1 in
              list-unit-files)
                for u in ssh.service ssh.socket smbd.service nmbd.service; do
                  [ "$u" = "$3" ] && echo "$u enabled enabled"
                done ;;
              is-enabled) grep -qx "$2" %s && echo enabled || echo disabled ;;
              *) echo "systemctl $*" >> %s ;;
            esac""" % (self.enabled, self.log)))
        self.env.stub("nmcli", textwrap.dedent("""\
            if [ "$1 $2" = "radio wifi" ] && [ -z "$3" ]; then cat %s; else echo "nmcli $*" >> %s; fi"""
                                               % (self.wifi, self.log)))

    def calls(self):
        return self.log.read_text().splitlines()

    def test_rows_only_for_what_exists_with_the_state_of_now(self):
        rows = [r.split("|")[:3] for r in self.env.out("services_rows").splitlines()]
        # Sem avahi nem o Downloader neste sistema.
        self.assertEqual(rows, [["ssh", "SSH", "boot"], ["samba", "Network share", "off"],
                                ["wifi", "Wi-Fi", "boot"]])

    def test_save_applies_only_what_changed(self):
        failed = self.env.out("services_save 'ssh=after,samba=boot,wifi=off'")
        self.assertEqual(failed, "")
        self.assertEqual(self.calls(), ["systemctl disable ssh.service ssh.socket",
                                        "systemctl enable --now smbd.service nmbd.service",
                                        "nmcli radio wifi off"])
        conf = (self.env.etc / "services.conf").read_text().splitlines()
        self.assertEqual(sorted(conf), ["samba=boot", "ssh=after", "wifi=off"])
        # Salvo, o estado e o do arquivo; nada muda de novo.
        self.log.write_text("")
        self.env.out("services_save 'ssh=after,samba=boot,wifi=off'")
        self.assertEqual(self.calls(), [])
        self.env.out("services_save 'ssh=off'")
        self.assertEqual(self.calls(), ["systemctl disable --now ssh.service ssh.socket"])

    def test_after_boot_wifi_starts_off_and_comes_up_later(self):
        state = self.env.dir / "nm" / "NetworkManager.state"
        state.parent.mkdir()
        state.write_text("[main]\nNetworkingEnabled=true\nWirelessEnabled=true\n")
        (self.env.etc / "services.conf").write_text("wifi=after\nssh=after\nsamba=boot\n")
        self.env.out("services_boot")
        self.assertIn("WirelessEnabled=false\n", state.read_text())
        self.assertIn("NetworkingEnabled=true\n", state.read_text())
        self.env.out("services_late")
        self.assertEqual(self.calls(), ["systemctl start --no-block ssh.service", "nmcli radio wifi on"])
        # Sem o arquivo do NetworkManager ainda: criado.
        state.unlink()
        self.env.out("services_boot")
        self.assertEqual(state.read_text(), "[main]\nWirelessEnabled=false\n")

    def test_minimal_moves_boot_services_to_after(self):
        moved = self.env.out("services_minimal").splitlines()
        self.assertEqual(moved, ["SSH", "Wi-Fi"])
        self.assertEqual(self.env.out("services_state ssh; services_state samba; services_state wifi").split(),
                         ["after", "off", "after"])

    def test_game_mode_turns_the_network_wait_off(self):
        # Com o NetworkManager-wait-online no sistema: no modo jogo ele vai
        # para Off (esperar a rede depois do boot nao serve), o resto para After.
        self.env.stub("systemctl", textwrap.dedent("""\
            case $1 in
              list-unit-files)
                for u in ssh.service NetworkManager-wait-online.service; do
                  [ "$u" = "$3" ] && echo "$u enabled enabled"
                done ;;
              is-enabled) echo enabled ;;
              *) echo "systemctl $*" >> %s ;;
            esac""" % self.log))
        self.assertIn("netwait|Wait for network|boot|", self.env.out("services_rows"))
        self.assertEqual(self.env.out("services_minimal").splitlines(), ["SSH", "Wi-Fi", "Wait for network"])
        self.assertIn("systemctl disable --now NetworkManager-wait-online.service", self.calls())
        self.assertIn("netwait=off\n", (self.env.etc / "services.conf").read_text())

    def test_states_and_keys_are_checked(self):
        self.assertEqual(self.env.run("services_set ssh sometimes").returncode, 1)
        self.assertEqual(self.env.run("services_set telnet boot").returncode, 1)
        self.assertFalse((self.env.etc / "services.conf").exists())

    def test_units_and_menu(self):
        rootfs = (ROOT / "fliperos-rootfs.sh").read_text()
        for unit in ("fliperos-services.service", "fliperos-services-late.service", "fliperos-services-late.timer",
                     "fliperos-services-screen.timer"):
            self.assertIn(unit, rootfs)
            self.assertTrue((ROOT / "config" / unit).is_file(), unit)
        self.assertIn("ExecStart=/usr/local/bin/fliperos-setup --services-boot",
                      (ROOT / "config" / "fliperos-services.service").read_text())
        self.assertIn("Before=NetworkManager.service", (ROOT / "config" / "fliperos-services.service").read_text())
        # Os "After boot" sobem 15 s depois da primeira tela (o tty1 liga o
        # timer); sem tela, a reserva de 3 min. Uma vez por boot.
        self.assertIn("OnBootSec=3min", (ROOT / "config" / "fliperos-services-late.timer").read_text())
        screen = (ROOT / "config" / "fliperos-services-screen.timer").read_text()
        self.assertIn("OnActiveSec=15s", screen)
        self.assertIn("Unit=fliperos-services-late.service", screen)
        self.assertNotIn("[Install]", screen)
        self.assertIn("RemainAfterExit=yes", (ROOT / "config" / "fliperos-services-late.service").read_text())
        self.assertIn("sudo -n /usr/local/bin/fliperos-setup --services-screen", (ROOT / "config" / "fliperos-tty1").read_text())
        entry = (SETUP / "fliperos-setup").read_text()
        self.assertIn("--services-late)\n      services_late", entry)
        self.assertIn("--services-screen)\n      services_screen", entry)
        # O Transmission do Downloader nao e um servico da tabela: so sobe
        # quando um download e pedido.
        self.assertNotIn("fliperos-transmission", self.env.out("services_table"))


class PasswordTests(Base):
    def test_system_and_samba_change_together_and_the_log_never_sees_it(self):
        got = self.env.dir / "got"
        self.env.stub("chpasswd", 'cat >> %s' % got)
        self.env.stub("smbpasswd", 'echo "smb $*" >> %s; cat >> %s' % (got, got))
        self.assertEqual(self.env.run("password_set abc").returncode, 1)
        self.assertFalse(got.exists())
        self.env.out("password_set 's3cret pass'")
        self.assertEqual(got.read_text(), "fliperos:s3cret pass\nsmb -s -a fliperos\ns3cret pass\ns3cret pass\n")
        self.assertNotIn("s3cret", (self.env.dir / "setup.log").read_text())

    def test_samba_failure_is_reported_apart(self):
        self.env.stub("chpasswd", "cat > /dev/null")
        self.env.stub("smbpasswd", "cat > /dev/null; exit 1")
        self.assertEqual(self.env.run("password_set longenough").returncode, 2)
        self.env.stub("chpasswd", "exit 1")
        self.assertEqual(self.env.run("password_set longenough").returncode, 1)


class BootGameTests(Base):
    """Setup > Games > Frontend: um jogo direto no boot."""

    def test_command_is_the_frontends_one_word_by_word(self):
        roms = self.env.dir / "roms"
        (roms / "dreamcast").mkdir(parents=True)
        game = roms / "dreamcast" / "Crazy Taxi $ (USA) | v1.gdi"
        game.write_text("")
        env = {"FLIPEROS_BIN": "/opt/fliperos/bin"}
        out = self.env.out("bootgame_command mame '%s'" % (roms / "mame" / "sf2.zip"), env).splitlines()
        self.assertEqual(out, ["/opt/fliperos/bin/fliperos-x11-run", "groovymame", "sf2"])
        self.env.out("bootgame_set dreamcast \"$GAME\"", dict(env, GAME=str(game)))
        lines = (self.env.etc / "bootgame").read_text().splitlines()
        self.assertEqual(lines, ["Crazy Taxi $ (USA)   v1", str(game), "/opt/fliperos/bin/fliperos-x11-run",
                                 "flycast", str(game)])
        self.assertEqual(self.env.out("launcher_current").strip(), "game")
        self.assertEqual(self.env.out("bootgame_label").strip(), "Crazy Taxi $ (USA)   v1")
        # Um arquivo que nao existe nao vira o jogo do boot.
        self.assertEqual(self.env.run("bootgame_set mame /nada/sf2.zip").returncode, 1)
        # Um caminho relativo vira o inteiro: o jogo abre de outra pasta.
        self.env.out('cd "$ROMS" && bootgame_set dreamcast "dreamcast/$NAME"',
                     dict(env, ROMS=str(roms), NAME=game.name))
        self.assertEqual((self.env.etc / "bootgame").read_text().splitlines()[1], str(game))

    def test_runner_runs_the_saved_words_without_a_shell(self):
        save = self.env.dir / "bootgame"
        rom = self.env.dir / "a b$c.zip"
        rom.write_text("")
        save.write_text("A game\n%s\nprintf\n[%%s]\n%s\n" % (rom, rom))
        run = subprocess.run(["bash", str(ROOT / "config" / "fliperos-bootgame")], capture_output=True, text=True,
                             env=dict(os.environ, FLIPEROS_BOOTGAME=str(save)))
        self.assertEqual(run.stdout, "[%s]" % rom)
        # A ROM sumiu (disco desligado): sai sem abrir nada, com o motivo.
        rom.unlink()
        run = subprocess.run(["bash", str(ROOT / "config" / "fliperos-bootgame")], capture_output=True, text=True,
                             env=dict(os.environ, FLIPEROS_BOOTGAME=str(save)), timeout=30)
        self.assertEqual((run.returncode, run.stdout), (0, ""))
        self.assertIn("not there", run.stderr)

    def test_session_row_and_first_boot(self):
        table = (ROOT / "config" / "fliperos-sessions.conf").read_text()
        self.assertIn("\ngame|kms|/opt/fliperos/bin/fliperos-bootgame||", table)
        (self.env.etc / "sessions.conf").write_text("setup|none|||Menu\ngame|kms|/bin/true||A game\n")
        # No primeiro boot ainda nao ha jogos: fica de fora.
        self.assertEqual(self.env.out("launcher_available").splitlines(), ["setup|Menu"])
        session = (ROOT / "config" / "fliperos-session").read_text()
        self.assertIn('game)\n        FLIPEROS_POWERKEY=game "${program[@]}"', session)
        self.assertIn("fliperos-bootgame", (ROOT / "fliperos-rootfs.sh").read_text())


class HarvestPackLineTests(unittest.TestCase):
    """O quadro do Auto scrape diz de que sistema e cada pacote: os videos e
    os logos de arcade sao so do MAME (e dos cores de arcade)."""

    def test_system_in_every_pack_label(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("feharvest", SETUP / "gui/feharvest.py")
        fh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fh)
        names = {}
        for line in (ROOT / "config/fliperos-media-torrents").read_text().splitlines():
            parts = line.split("\t")
            if not line.startswith("#") and len(parts) >= 5:
                kind = fh.KIND_LABELS[parts[1]]
                names[parts[0]] = ("%s %s" % (fh.pack_system(parts[4]), kind)).strip()
        self.assertEqual(names["mame-videos-snaps"], "MAME VIDEOS")
        self.assertEqual(names["arcade-wheels"], "MAME LOGOS")
        self.assertEqual(names["sega-naomi-wheels"], "NAOMI LOGOS")
        self.assertEqual(names["atomiswave_202210"], "ATOMISWAVE VIDEOS")
        self.assertEqual(names["SegaModel2VideoSnaps"], "MODEL 2 VIDEOS")
        h = fh.Harvester.__new__(fh.Harvester)
        h.packs = {"mame-videos-snaps": ("downloading", 80), "arcade-wheels": ("done", 100)}
        h.state = {}
        fh.pack_kinds = lambda: names
        self.assertEqual(h.pack_line(), "MAME LOGOS DONE  MAME VIDEOS 80%")


class EmulatorsVulkanTests(Base):
    """O driver da placa AMD manda no renderizador: amdgpu liga o Vulkan nos
    emuladores; radeon (sem Vulkan) volta cada um ao de fabrica."""

    def setUp(self):
        super().setUp()
        self.home = self.env.dir / "home"
        for path, text in (("flycast/emu.cfg", "[config]\npvr.rend = 3\n"),
                           ("dolphin-emu/Dolphin.ini", "[Core]\nCPUThread = True\n"),
                           ("PCSX2/inis/PCSX2.ini", "[EmuCore/GS]\nRenderer = 12\n")):
            f = self.home / ".config" / path
            f.parent.mkdir(parents=True)
            f.write_text(text)
        ds = self.home / ".local/share/duckstation/settings.ini"
        ds.parent.mkdir(parents=True)
        ds.write_text("[GPU]\nRenderer = OpenGL\n")
        self.envs = {"EMULATORS_HOME": str(self.home), "EMULATORS_INI_SET": str(ROOT / "config/fliperos-ini-set")}

    def values(self):
        read = lambda p: (self.home / p).read_text()
        return (re.search(r"pvr\.rend = (\d)", read(".config/flycast/emu.cfg")).group(1),
                re.search(r"GFXBackend = ([\w-]+)", read(".config/dolphin-emu/Dolphin.ini") + "GFXBackend = -").group(1),
                re.search(r"Renderer = (-?\d+)", read(".config/PCSX2/inis/PCSX2.ini")).group(1),
                re.search(r"Renderer = (\w+)", read(".local/share/duckstation/settings.ini")).group(1))

    def test_amdgpu_then_radeon(self):
        self.env.card("card0", "amdgpu")
        self.env.out("emulators_vulkan_sync", self.envs)
        self.assertEqual(self.values(), ("5", "Vulkan", "-1", "Automatic"))
        self.assertIn("emulators_driver=amdgpu", (self.env.etc / "fliperos.conf").read_text())
        self.assertIn("CPUThread = True", (self.home / ".config/dolphin-emu/Dolphin.ini").read_text())
        # A mesma placa no mesmo driver: nada muda (a escolha da pessoa fica).
        (self.home / ".config/flycast/emu.cfg").write_text("[config]\npvr.rend = 0\n")
        self.env.out("emulators_vulkan_sync", self.envs)
        self.assertEqual(self.values()[0], "0")
        # De volta ao radeon: o OpenGL equivalente e o automatico.
        (self.home / ".config/flycast/emu.cfg").write_text("[config]\npvr.rend = 5\n")
        (self.home / ".config/PCSX2/inis/PCSX2.ini").write_text("[EmuCore/GS]\nRenderer = 14\n")
        (self.env.drm / "card0").rename(self.env.drm / "card9-old")
        self.env.card("card0", "radeon")
        self.env.out("emulators_vulkan_sync", self.envs)
        self.assertEqual(self.values(), ("3", "OGL", "-1", "Automatic"))

    def test_other_drivers_and_missing_emulators_are_left_alone(self):
        self.env.card("card0", "i915")
        self.env.out("emulators_vulkan_sync", self.envs)
        self.assertEqual(self.values(), ("3", "-", "12", "OpenGL"))
        shutil.rmtree(self.home / ".config/dolphin-emu")
        self.env.out("emulators_vulkan amdgpu", self.envs)
        self.assertFalse((self.home / ".config/dolphin-emu").exists())

    def test_called_at_every_session_start(self):
        setup = (SETUP / "fliperos-setup").read_text()
        body = setup.split("    --session-start)\n")[1].split(";;")[0]
        self.assertLess(body.index("emulators_vulkan_sync"), body.index("[[ ${2:-} == game ]]"))


class BootGameFastTests(Base):
    """O jogo direto no boot quer o boot mais curto: o Limine espera 1 s (3
    com os outros launchers) e o login do tty1 nao espera a rede."""

    def test_menu_timeout_follows_the_launcher(self):
        defaults = self.env.etc / "fliperos-boot"
        defaults.write_text('FLIPEROS_CMDLINE="quiet"\nFLIPEROS_TIMEOUT="3"\n')
        calls = self.env.dir / "limine"
        self.env.stub("limine-update", "echo run >> %s" % calls)
        script = """
            is_installed() { return 0; }; is_live() { return 1; }
            LIMINE_UPDATE=limine-update
            launcher_set %s
        """
        self.env.out(script % "game")
        self.assertIn('FLIPEROS_TIMEOUT="1"', defaults.read_text())
        self.assertIn('FLIPEROS_CMDLINE="quiet"', defaults.read_text())
        self.assertEqual((self.env.etc / "session").read_text(), "game\n")
        # O mesmo valor: o menu nao e reescrito.
        self.env.out(script % "game")
        self.assertEqual(calls.read_text().split(), ["run"])
        self.env.out(script % "fliperos")
        self.assertIn('FLIPEROS_TIMEOUT="3"', defaults.read_text())
        self.assertEqual(calls.read_text().split(), ["run", "run"])

    def test_login_does_not_wait_for_the_network(self):
        unit = (ROOT / "config" / "fliperos-user-sessions.service").read_text()
        after = [l for l in unit.splitlines() if l.startswith("After=")]
        self.assertEqual(len(after), 1)
        self.assertNotIn("network", after[0])
        self.assertIn("ExecStart=/usr/lib/systemd/systemd-user-sessions start", unit)
        rootfs = (ROOT / "fliperos-rootfs.sh").read_text()
        self.assertIn('fliperos-user-sessions.service" "$root/etc/systemd/system/systemd-user-sessions.service"', rootfs)
        self.assertIn("sed -i '/^[^#]*pam_lastlog\\.so/d' \"$root/etc/pam.d/login\"", rootfs)


class FirstBootLiveTests(Base):
    """O primeiro boot ja instala e liga a tela ao vivo do painel web."""

    def run_live(self, installed, online):
        script = ("source %s/screens/first-boot.sh; "
                  "extras_installed() { return %d; }; "
                  "run_online() { echo \"online $*\"; return %d; }; "
                  "ui_msg() { echo \"msg $*\"; }; "
                  "screen_first_boot_live; echo rc=$?") % (SETUP, 0 if installed else 1, 0 if online else 1)
        return self.env.out(script)

    def test_installs_the_live_screen(self):
        out = self.run_live(installed=False, online=True)
        self.assertIn("online Installing Live screen  extras_install stream", out)
        self.assertIn("rc=0", out)
        self.assertNotIn("msg", out)

    def test_already_installed_is_kept(self):
        self.assertNotIn("online", self.run_live(installed=True, online=True))

    def test_offline_points_to_extras(self):
        out = self.run_live(installed=False, online=False)
        self.assertIn("Setup > Games > Extras > Live screen", out)
        self.assertIn("rc=1", out)

    def test_called_by_the_first_boot(self):
        screen = (SETUP / "screens/first-boot.sh").read_text().split("screen_first_boot() {")[1]
        body = screen.split("\n}\n")[0]
        self.assertLess(body.index("screen_first_boot_live"), body.index('rm -f "$FLIPEROS_ETC/firstboot"'))


class FirstBootWizardTests(Base):
    """O primeiro boot nao pergunta o launcher (e o frontend do FliperOS) e
    leva ao Wi-Fi, quando o cabo nao traz a internet, e aos controles."""

    def first_boot(self, online=True, wifi="wlan0", mapped=True):
        (self.env.etc / "firstboot").write_text("")
        if mapped:
            (self.env.etc / "buttons.map").write_text("1 b1 0 b0 x\n")
        flag = self.env.dir / "online"
        if online:
            flag.write_text("")
        script = """
            source %s/screens/first-boot.sh
            launcher_installed() { [[ $1 == fliperos ]]; }
            net_online() { [[ -e %s ]]; }
            net_connecting() { return 1; }
            net_wifi_devices() { [[ -n "%s" ]] && echo "%s"; }
            ui_menu() { echo "MENU $1"; }
            ui_msg() { echo "msg $2"; }
            ui_info() { :; }
            ui_yesno() { echo "ask $2"; return 0; }
            screen_wifi() { echo "wifi $*"; touch %s; }
            screen_buttons() { echo "buttons"; }
            extras_installed() { return 0; }
            BUTTONS_MAP=%s
            screen_first_boot
        """ % (SETUP, flag, wifi, wifi, flag, self.env.etc / "buttons.map")
        out = self.env.out(script)
        self.assertFalse((self.env.etc / "firstboot").exists())
        self.assertNotIn("MENU", out)
        self.assertEqual((self.env.etc / "session").read_text(), "fliperos\n")
        return out

    def test_cable_with_internet_and_controls_mapped_asks_nothing(self):
        (self.env.etc / "session").write_text("setup\n")
        self.assertEqual(self.first_boot().strip(), "")

    def test_no_internet_on_the_cable_offers_the_wifi_then_the_controls(self):
        out = self.first_boot(online=False, mapped=False).splitlines()
        self.assertTrue(out[0].startswith("ask There is no internet on the network cable."), out)
        self.assertEqual(out[1], "wifi 0 quiet")
        self.assertTrue(out[2].startswith("msg Now the controls"), out)
        self.assertEqual(out[3], "buttons")

    def test_no_wifi_adapter_goes_straight_to_the_controls(self):
        out = self.first_boot(online=False, wifi="", mapped=False).splitlines()
        self.assertTrue(out[0].startswith("msg Now the controls"), out)
        self.assertEqual(out[1:], ["buttons"])


class CustomGamesTests(Base):
    """Setup > Games > Custom games: programas que nao sao ROM, em grupos que
    os frontends mostram como sistemas."""

    def setUp(self):
        super().setUp()
        self.roms = self.env.dir / "roms"
        self.roms.mkdir()
        self.e = {"ROMS_DIR": str(self.roms), "CUSTOM_GAMES_DIR": str(self.roms / "custom"),
                  "FLIPEROS_BIN": "/opt/fliperos/bin"}

    def test_entry_is_a_script_that_runs_in_its_own_mode(self):
        cmd = "wine ~/games/Pang \\$ Deluxe/pang.exe --full 'x y'"
        self.env.out('customgames_save "PC games" "Pang" 240p "%s"' % cmd, self.e)
        script = self.roms / "custom" / "PC games" / "Pang.sh"
        self.assertTrue(os.access(script, os.X_OK))
        text = script.read_text()
        self.assertIn("# mode: 640x240@60\n", text)
        self.assertIn("# command: wine ~/games/Pang $ Deluxe/pang.exe --full 'x y'\n", text)
        # O script roda o comando como ele foi digitado, pelo fliperos-x11-run.
        fake = self.env.dir / "x11"
        fake.write_text('#!/bin/bash\nprintf "%s\\n" "$@"\n')
        fake.chmod(0o755)
        text = text.replace("/opt/fliperos/bin/fliperos-x11-run", str(fake))
        script.write_text(text)
        out = subprocess.run(["sh", str(script)], capture_output=True, text=True).stdout.splitlines()
        self.assertEqual(out[:4], ["--mode", "640x240@60", "bash", "-c"])
        self.assertEqual(out[4], "wine ~/games/Pang $ Deluxe/pang.exe --full 'x y'")

    def test_modes_names_and_listing(self):
        self.assertEqual(self.env.out("customgames_mode 480i", self.e).strip(), "640x480@60")
        self.assertEqual(self.env.out("customgames_mode 384x224@59.6", self.e).strip(), "384x224@59.6")
        for bad in ("640x480", "x240@60", "640x240@", "big"):
            self.assertEqual(self.env.run("customgames_mode '%s'" % bad, self.e).returncode, 1, bad)
        for bad in ("", "a/b", "a|b", ".hidden", ".."):
            self.assertEqual(self.env.run("customgames_valid_name '%s'" % bad, self.e).returncode, 1, bad)
        self.assertEqual(self.env.run("customgames_save G '' 240p ls", self.e).returncode, 1)
        self.env.out("customgames_save G A 384x224@59.6 'echo a'; customgames_save G B 480i 'echo b'", self.e)
        self.assertEqual(self.env.out("customgames_list", self.e).splitlines(),
                         ["G|A|384x224@59.6|echo a", "G|B|640x480@60|echo b"])
        self.assertEqual(self.env.out("customgames_mode_label 640x480@60; customgames_mode_label 384x224@59.6",
                                      self.e).split(), ["480i", "384x224@59.6"])

    def test_edit_moves_and_delete_removes_the_empty_group(self):
        self.env.out("customgames_save Old A 240p 'echo a'", self.e)
        self.env.out("customgames_save New B 480i 'echo b' Old A", self.e)
        self.assertEqual(self.env.out("customgames_list", self.e).splitlines(), ["New|B|640x480@60|echo b"])
        self.assertFalse((self.roms / "custom" / "Old").exists())
        self.env.out("customgames_delete New B", self.e)
        self.assertEqual(self.env.out("customgames_groups", self.e), "")

    def test_groups_are_systems_in_the_frontends_but_not_scraped(self):
        self.env.out("customgames_save 'PC games' Pang 240p 'echo pang'", self.e)
        rows = self.env.out("scraper_detect", self.e).splitlines()
        self.assertIn("custom/PC games|%s|ports|1" % (self.roms / "custom" / "PC games"), rows)
        self.assertEqual(self.env.out("scraper_attract_emulator 'custom/PC games'", self.e).strip(),
                         'PC games|/bin/sh|"[romfilename]"|.sh')
        menu = (SETUP / "screens" / "setup-menu.sh").read_text()
        self.assertIn("mapfile -t found < <(scraper_detect | grep -v '^custom/')", menu)
        # E pode ser o jogo do boot: o comando e o sh com o script.
        script = self.roms / "custom" / "PC games" / "Pang.sh"
        self.assertEqual(self.env.out("bootgame_command 'custom/PC games' \"$F\"", dict(self.e, F=str(script)))
                         .splitlines(), ["/bin/sh", str(script)])


class ArcadeResyncTests(Base):
    """As romlists de arcade do Attract-Mode com as informacoes do MAME (os
    filtros das telas) tambem para os jogos postos depois da AttractPlus ROM
    List."""

    def setUp(self):
        super().setUp()
        self.attract = self.env.dir / "attract"
        (self.attract / "romlists").mkdir(parents=True)
        (self.attract / "emulators").mkdir()
        (self.attract / "emulators" / "MAME.cfg").write_text("executable x\nromext               .zip;.7z\n")
        self.roms = self.env.dir / "mame"
        self.roms.mkdir()
        for game in ("sf2.zip", "pacman.7z"):
            (self.roms / game).write_text("")
        # As listas sao do FliperOS (a pasta propria), nao do Attract-Mode.
        lists = self.env.dir / "lists"
        lists.mkdir()
        self.list = lists / "MAME.txt"
        self.e = {"ATTRACT_DIR": str(self.attract), "FLIPEROS_LISTS": str(lists),
                  "FRONTENDS_ROMLIST_STATE": str(self.env.dir / "state")}

    def stale(self):
        return self.env.run('frontends_arcade_stale "%s" MAME' % self.roms, self.e).returncode == 0

    def test_stale_without_list_info_or_when_the_folder_changed(self):
        head = "#Name;Title;Emulator;CloneOf;Year;Manufacturer;Category\n"
        self.assertTrue(self.stale())                       # sem romlist
        self.list.write_text(head + "sf2;sf2;MAME;;;;\npacman;pacman;MAME;;;;\n")
        self.assertTrue(self.stale())                       # so o nome do arquivo
        self.list.write_text(head + "sf2;Street Fighter II;MAME;;1991;Capcom;Fighter\n"
                             "pacman;Pac-Man;MAME;;1980;Namco;Maze\n")
        self.assertTrue(self.stale())                       # feita antes de guardar a pasta
        # Uma BIOS que a AttractPlus ROM List deixa de fora nao a atrasa.
        (self.roms / "neogeo.zip").write_text("")
        self.env.out('frontends_romlist_state_save MAME "%s"' % self.roms, self.e)
        self.assertFalse(self.stale())
        (self.roms / "dkong.zip").write_text("")
        self.assertTrue(self.stale())                       # jogo novo na pasta
        (self.roms / "dkong.zip").unlink()
        self.assertFalse(self.stale())
        (self.roms / "pacman.7z").unlink()
        self.assertTrue(self.stale())                       # jogo que saiu
        frontends = (SETUP / "lib" / "frontends.sh").read_text()
        self.assertIn('    frontends_romlist_state_save "$name" "$dir"\n', frontends)

    def test_resync_only_with_the_cache_and_without_recursion(self):
        calls = self.env.dir / "calls"
        script = """
            frontends_romlist_systems() { echo "mame|%s|arcade|2|MAME"; }
            groovymame_version() { echo 0.289; }
            frontends_romlist() { echo "romlist $* resync=$FRONTENDS_RESYNCING" >> %s; frontends_arcade_resync; }
            frontends_arcade_resync
        """ % (self.roms, calls)
        cache = self.env.dir / "cache"
        cache.mkdir()
        self.env.out(script, dict(self.e, ROMCLEAN_CACHE=str(cache)))
        self.assertFalse(calls.exists())                    # sem o cache: nada
        (cache / "romclean-groovymame-0.289.json").write_text("{}")
        self.env.out(script, dict(self.e, ROMCLEAN_CACHE=str(cache)))
        self.assertEqual(calls.read_text().splitlines(),
                         ["romlist /dev/null mame|%s|arcade|2|MAME resync=1" % self.roms])
        frontends = (SETUP / "lib" / "frontends.sh").read_text()
        self.assertIn("frontends_attract() {\n  local key dir platform n=0\n", frontends)
        self.assertLess(frontends.index("  frontends_arcade_resync\n  frontends_attract_lists\n  frontends_attract_prune"),
                        frontends.index("frontends_attract_empty\n"))


class FolderListsTests(unittest.TestCase):
    """Toda listagem de pastas e a lista vertical em texto na interface
    grafica (UI_STYLE=list), nunca o carrossel de icones."""

    def test_every_folder_listing_is_a_vertical_list(self):
        ui = (SETUP / "lib" / "ui.sh").read_text().split("ui_browse() {")[1].split("\n}\n")[0]
        self.assertIn("choice=$(UI_STYLE=list ui_menu", ui)
        screens = {
            "folders.sh": ['choice=$(UI_STYLE=list ui_menu "$title" \\\n      "Folders in $FOLDERS_HOME',
                           'choice=$(UI_STYLE=list ui_menu "$title" "${text:+$text'],
            "rom-cleaner.sh": ['share=$(UI_STYLE=list ui_menu "$title" "Which shared folder'],
            "mediapacks.sh": ['folders=$(UI_STYLE=list ui_menu "$title" "Which games is it for?"'],
            "setup-menu.sh": ['choice=$(UI_STYLE=list ui_menu "$title" "The game opens straight',
                              'choice=$(UI_STYLE=list ui_menu "$title" "Which group?'],
        }
        for name, calls in screens.items():
            text = (SETUP / "screens" / name).read_text()
            for call in calls:
                self.assertIn(call, text, name)
        serve = (SETUP / "gui" / "serve.py").read_text()
        self.assertIn('vertical=style == "list"', serve)
        self.assertIn("return (not self.vertical and", (SETUP / "gui" / "widgets.py").read_text())


class RemoteMenuTests(Base):
    """fliperos-menu digitado no SSH: o menu em texto ali, nunca a interface
    grafica no monitor do gabinete."""

    def test_tty1_passes_remote_outside_a_vt_and_setup_forces_text(self):
        tty1 = (ROOT / "config" / "fliperos-tty1").read_text()
        self.assertIn("[[ $(tty 2> /dev/null) == /dev/tty[0-9]* ]] || remote=(--remote)", tty1)
        self.assertIn('fliperos-setup --menu "${remote[@]}"', tty1)
        entry = (SETUP / "fliperos-setup").read_text()
        self.assertIn('if [[ ${1:-} == --remote ]]; then\n    SETUP_REMOTE=1\n    export FLIPEROS_UI=text', entry)
        self.assertIn("((SETUP_REMOTE == 1))", (SETUP / "screens" / "main-menu.sh").read_text())

    def test_text_wins_over_the_menu_loop(self):
        dri = self.env.dir / "card0"
        dri.write_text("")
        self.env.cmdline.write_text("quiet splash\n")   # o disco instalado, nao a midia
        env = {"UI_DRI": str(dri), "SETUP_MENU_LOOP": "1"}
        self.assertEqual(self.env.run("source %s/lib/ui.sh; ui_gui_wanted" % SETUP, env).returncode, 0)
        env["FLIPEROS_UI"] = "text"
        self.assertEqual(self.env.run("source %s/lib/ui.sh; ui_gui_wanted" % SETUP, env).returncode, 1)

    def test_install_media_opens_the_gui_after_the_output_test(self):
        dri = self.env.dir / "card0"
        dri.write_text("")
        self.env.cmdline.write_text("boot=live quiet\n")
        env = {"UI_DRI": str(dri), "SETUP_MENU_LOOP": "1"}
        self.assertEqual(self.env.run("source %s/lib/ui.sh; ui_gui_wanted" % SETUP, env).returncode, 0)
        ui = (SETUP / "lib" / "ui.sh").read_text()
        self.assertIn("if ! is_live || conf_get output_test > /dev/null 2>&1; then\n    ui_gui_start", ui)
        entry = (SETUP / "fliperos-setup").read_text()
        self.assertIn("conf_set output_test skipped\n      fi\n      # A saida ja escolhida: o resto do instalador na interface grafica.\n      ui_gui_start", entry)


class HarvestServiceTests(unittest.TestCase):
    """O scrape automatico como servico (fliperos-scrape --daemon): segue com
    um jogo aberto e fora do frontend, que so mostra o andamento dele."""

    def harvester(self, home):
        import importlib
        import sys
        sys.path.insert(0, str(SETUP / "gui"))
        feharvest = importlib.import_module("feharvest")
        fd = type("Fd", (), {})()
        fd.web = type("Web", (), {"player_home": staticmethod(lambda: str(home))})()
        fd.short_title = staticmethod(lambda g: g.get("Title") or g["Name"])
        fe = type("Fe", (), {})()
        fe.fd, fe.lib, fe.scraping, fe.dirty = fd, None, None, set()
        return feharvest.Harvester(fe)

    def test_frontend_follows_the_service_and_rereads_what_it_fetched(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, frontend = self.harvester(tmp), self.harvester(tmp)
            # Sem o servico: o frontend roda o laco.
            self.assertFalse(frontend.follow())
            frontend.publish()          # o frontend nunca grava o andamento
            self.assertFalse(frontend.follow())
            service.publishing = True
            service.total, service.left, service.scanned = 10, 4, True
            service.current = {"Name": "sf2", "Title": "Street Fighter II"}
            service.state["tried"] = {"mame/sf2": int(__import__("time").time())}
            service.save()
            service.publish()
            self.assertTrue(frontend.follow())
            self.assertEqual((frontend.total, frontend.left), (10, 4))
            self.assertEqual(frontend.current["Title"], "Street Fighter II")
            self.assertIn(("mame", "sf2"), frontend.fe.dirty)

    def test_save_keeps_what_the_other_process_wrote(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = self.harvester(tmp), self.harvester(tmp)
            a.state["tried"] = {"mame/sf2": 100}
            a.save()
            b.state.setdefault("rested", {})["mame/kof98"] = 50
            b.save()
            data = json.loads(Path(a.path).read_text())
            self.assertEqual(data["tried"], {"mame/sf2": 100})
            self.assertEqual(data["rested"], {"mame/kof98": 50})

    def test_service_installed_after_boot_and_in_the_services_menu(self):
        unit = (ROOT / "config" / "fliperos-scrape.service").read_text()
        self.assertIn("fliperos-scrape --daemon", unit)
        self.assertIn("User=fliperos", unit)
        self.assertIn("IOSchedulingClass=idle", unit)
        rootfs = (ROOT / "fliperos-rootfs.sh").read_text()
        self.assertIn("echo 'scrape=after' >> \"$root/etc/fliperos/services.conf\"", rootfs)
        self.assertIn("scrape|Auto scrape|fliperos-scrape.service|", (SETUP / "lib" / "services.sh").read_text())


class PowerNowTests(Base):
    """Reiniciar e desligar pelo Setup: tudo solto antes do pedido, e o bash
    vira um sleep (a sessao do tty1 segurava o reboot 90 s ate o SIGKILL)."""

    def test_releases_the_screen_before_asking_and_ends_as_a_sleep(self):
        calls = self.env.dir / "calls"
        self.env.stub("systemctl", 'echo "systemctl $*" >> %s' % calls)
        self.env.stub("sleep", 'echo "sleep $*" >> %s' % calls)
        r = self.env.run("""
            source %s/screens/install-progress.sh
            install_unmount() { :; }; recovery_umount() { :; }; sync() { :; }
            restore_terminal() { echo restore >> %s; }
            trap 'echo exit-trap >> %s' EXIT
            unset -f sleep
            screen_power_now reboot
        """ % (SETUP, calls, calls))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(calls.read_text().splitlines(), ["restore", "systemctl reboot", "sleep 60"])
        for name in ("main-menu.sh", "amd-driver.sh", "latency.sh", "patches.sh"):
            self.assertNotRegex((SETUP / "screens" / name).read_text(), r"\bsystemctl (reboot|poweroff)\b", name)

    def test_session_gets_10_seconds_to_stop(self):
        self.assertIn("TimeoutStopSec=10s", (ROOT / "config" / "fliperos-session-stop.conf").read_text())
        rootfs = (ROOT / "fliperos-rootfs.sh").read_text()
        self.assertIn('"$root/etc/systemd/system/session-.scope.d/fliperos-stop.conf"', rootfs)

    def test_every_service_gets_10_seconds_but_the_update(self):
        # O reboot nao espera 90 s por servico nenhum preso no SIGTERM; o
        # update ao desligar diz o tempo dele.
        conf = (ROOT / "config" / "fliperos-stop-timeout.conf").read_text()
        self.assertIn("[Manager]\nDefaultTimeoutStopSec=10s", conf)
        rootfs = (ROOT / "fliperos-rootfs.sh").read_text()
        for where in ("system.conf.d", "user.conf.d"):
            self.assertIn('fliperos-stop-timeout.conf" "$root/etc/systemd/%s/fliperos-stop.conf"' % where, rootfs)
        self.assertIn("TimeoutStopSec=20min", (ROOT / "config" / "fliperos-update-shutdown.service").read_text())


class BackgroundJobTests(Base):
    """Scrape the games em segundo plano: a tela mostra o andamento e
    qualquer tecla volta ao menu, com o trabalho seguindo."""

    def watch(self, running, key):
        jobs = self.env.dir / "jobs"
        jobs.mkdir()
        (jobs / "scrape.events").write_text("@step 10 Reading\n@msg a\n@step 42 Street Fighter II (3 left)\n")
        return self.env.run("""
            source %s/lib/ui.sh
            source %s/screens/progress.sh
            ui_size() { :; }; ui_clear() { :; }; ui_topbar() { :; }; ui_flush_input() { :; }
            ui_progress() { echo "draw:$3:$4:$5:${*:6}"; }
            job_running() { %s; }
            ui_wait_key() { %s; }
            screen_job_watch scrape Scraper "Scraping the games"
            echo "rc=$?"
        """ % (SETUP, SETUP, "true" if running else "false", "true" if key else "false"),
            {"JOBS_DIR": str(jobs)})

    def test_a_key_leaves_while_it_goes_on(self):
        r = self.watch(running=True, key=True)
        self.assertIn("draw:42:Street Fighter II (3 left):Any key returns to the menu; it goes on in the background.:a",
                      r.stdout)
        self.assertIn("rc=1", r.stdout)

    def test_finished_with_the_screen_open(self):
        self.assertIn("rc=0", self.watch(running=False, key=False).stdout)

    def test_scrape_the_games_runs_as_a_job_and_comes_back_to_it(self):
        menu = (SETUP / "screens" / "setup-menu.sh").read_text()
        self.assertIn('job_start scrape "$SETUP_DIR/fliperos-setup" --scrape-now "$result" "${keys[@]}"', menu)
        self.assertIn("if job_running scrape; then\n    screen_scraper_fliperos_watch", menu)
        self.assertIn("--scrape-now)\n      # Setup > Games > Scraper > Scrape the games",
                      (SETUP / "fliperos-setup").read_text())


class UiParityTests(unittest.TestCase):
    """O menu grafico e o de texto tem as mesmas telas: cada primitiva que as
    telas chamam tem o ramo da interface grafica (ou passa por uma que tem),
    e cada pedido do lib/ui.sh tem a sua tela no gui/serve.py."""

    # O que desenha no terminal de proposito (alsamixer, o grid do Switchres:
    # ui_text solta o video) e os ajudantes que nao sao tela.
    NOT_SCREENS = {"ui_c", "ui_dim", "ui_bad", "ui_yes", "ui_no", "ui_clear", "ui_fields", "ui_flush_input",
                   "ui_text", "ui_done", "ui_init", "ui_status_short", "ui_size", "ui_box_width", "ui_palette",
                   "ui_screen", "ui_topbar", "ui_list_height", "ui_hint_small", "ui_hint_lines", "ui_hint_env",
                   "ui_sounds", "ui_orientation", "ui_gui_alive", "ui_gui_wanted", "ui_gui_start", "ui_gui_call",
                   "ui_gui_menu"}

    def functions(self):
        text = (SETUP / "lib" / "ui.sh").read_text()
        return dict(re.findall(r"(?ms)^(ui_\w+)\(\) \{\n(.*?)^\}\n", text))

    def test_every_screen_primitive_reaches_the_gui(self):
        bodies = self.functions()
        direct = {name for name, body in bodies.items() if re.search(r"\bui_gui_(alive|call|menu)\b", body)}
        used = set()
        for path in list((SETUP / "screens").glob("*.sh")) + list((SETUP / "lib").glob("*.sh")):
            if path.name != "ui.sh":
                used |= set(re.findall(r"\b(ui_\w+)\b", path.read_text()))
        used &= set(bodies)
        missing = []
        for name in sorted(used - self.NOT_SCREENS):
            calls = set(re.findall(r"\b(ui_\w+)\b", bodies[name])) - {name}
            if name not in direct and not (calls & direct):
                missing.append(name)
        self.assertEqual(missing, [], "sem a tela da interface grafica")

    def test_every_request_has_a_screen_and_back(self):
        ui = (SETUP / "lib" / "ui.sh").read_text()
        sent = set(re.findall(r"ui_gui_call ([a-z]\w*)", ui)) | set(re.findall(r"ui_gui_menu ([a-z]\w*)", ui))
        serve = (SETUP / "gui" / "serve.py").read_text()
        handled = set(re.findall(r'cmd == "(\w+)"', serve))
        for group in re.findall(r"cmd in \(([^)]*)\)", serve):
            handled |= set(re.findall(r'"(\w+)"', group))
        self.assertEqual(sent - handled, set())
        # O ping e o teste do servidor (tools/gui-*.sh).
        self.assertEqual(handled - sent - {"ping"}, set())
        self.assertIn("grid", sent)
        self.assertIn("class Grid:", (SETUP / "gui" / "widgets.py").read_text())


class DebugModeTests(Base):
    """Setup > System > Debug mode: boot e programas com ou sem texto na tela."""

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


class EmulatorsTests(Base):
    """Setup > Games > Emulators & Games (lib/emulators.sh sobre o config/fliperos-emulators)."""

    def test_list_field_and_install(self):
        d = self.env.dir
        (d / "emus").write_text('#!/bin/sh\nif [ "$1" = list ]; then\n'
                                '  echo "flycast|1|image|Flycast (Dreamcast)"\n  echo "kof|0|source|KOF Final Attack"\n'
                                'else echo "$*" >> "%s/calls"; echo "@step 100 Done"; fi\n' % d)
        (d / "emus").chmod(0o755)
        env = {"EMULATORS_CMD": str(d / "emus")}
        self.assertEqual(self.env.out("emulators_field kof 3; emulators_field flycast 4; emulators_field flycast 2",
                                      env).splitlines(), ["source", "Flycast (Dreamcast)", "1"])
        out = self.env.out('emulators_install model2; emulators_install kof "/media/usb/KOF Final"', env)
        self.assertIn("@step 0 Starting", out)
        self.assertIn("@step 100 Done", out)
        self.assertEqual((d / "calls").read_text().splitlines(),
                         ["install model2 --progress", "install kof --progress --source /media/usb/KOF Final"])
        r = self.env.run("emulators_install model2", {"EMULATORS_CMD": str(d / "nada")})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("@fail", r.stdout)


class ButtonMappingNoRepeatTests(Base):
    """Button mapping: um botao ja dado a um comando nao vale para outro."""

    def test_repeated_press_is_refused_and_asked_again(self):
        presses = self.env.dir / "presses"
        # O botao 0 duas vezes (a segunda e recusada) e depois um por comando.
        presses.write_text("\n".join(["0 b0 Pad", "0 b0 Pad"] + ["0 b%d Pad" % i for i in range(1, 12)]) + "\n")
        saved = self.env.dir / "saved"
        out = self.env.out("""
            source %s/screens/joysticks.sh
            ui_menu_hints() { echo panel; }
            ui_menu() { echo 1; }
            ui_capture() { return 1; }
            ui_info() { echo "info $*"; }
            ui_msg() { echo "msg $*"; }
            ui_yesno() { return 0; }
            ui_flush_input() { :; }
            padkeys_on() { :; }; padkeys_off() { :; }
            buttons_capture() { local line; line=$(head -n 1 %s); sed -i 1d %s; [[ -n $line ]] && echo "$line"; }
            buttons_save() { cp "$1" %s; }
            screen_buttons
        """ % (SETUP, presses, presses, saved))
        self.assertIn("info Button mapping That one is already UP of player 1. Press another control for DOWN.", out)
        rows = [line.split() for line in saved.read_text().splitlines()]
        self.assertEqual(len(rows), 12)
        self.assertEqual(len({(r[2], r[3]) for r in rows}), 12)
        self.assertEqual(rows[1][:4], ["1", "down", "0", "b1"])


class ButtonsLayoutTests(Base):
    """Setup > Joysticks > Buttons layout: onde ficam no painel os botoes dos jogos de 1 a 5 botoes."""

    def test_grid_and_saved_layout(self):
        out = self.env.out
        layout = self.env.etc / "buttons.layout"
        # Sem nada gravado, o botao N na posicao N (1 2 3 em cima, 4 5 6 embaixo).
        self.assertEqual(out("buttons_layout_get 3").strip(), "1 2 3")
        self.assertEqual(out("buttons_layout_grid 1 2 3"), "[1]  [2]  [3]\n[ ]  [ ]  [ ]\n")
        self.assertEqual(out("buttons_layout_grid 1 4 2 5"), "[1]  [3]  [ ]\n[2]  [4]  [ ]\n")
        self.assertEqual(out("buttons_layout_grid"), "[ ]  [ ]  [ ]\n[ ]  [ ]  [ ]\n")
        self.assertEqual(out("buttons_layout_row 1 2 4 5").strip(), "[1][2][ ] / [3][4][ ]")
        out("buttons_layout_set 4 1 4 2 5; buttons_layout_set 2 4 5")
        self.assertEqual(layout.read_text(), "2 4 5\n4 1 4 2 5\n")
        self.assertEqual(out("buttons_layout_get 4").strip(), "1 4 2 5")
        self.assertEqual(out("buttons_layout_get 5").strip(), "1 2 3 4 5")
        # O padrao tira a linha; posicao repetida ou fora do painel nao grava.
        out("buttons_layout_set 4 1 2 3 4")
        self.assertEqual(layout.read_text(), "2 4 5\n")
        for bad in ("3 1 1 2", "3 1 2", "2 1 7", "2 0 1"):
            self.assertNotEqual(self.env.run("buttons_layout_set " + bad).returncode, 0, bad)
        self.assertEqual(layout.read_text(), "2 4 5\n")

    def test_apply_makes_the_game_table_and_saves_the_buttons_again(self):
        d = self.env.dir
        (d / "romclean").write_text('#!/bin/sh\necho "romclean $*" >> "%s/calls"\n' % d)
        (d / "buttons").write_text('#!/bin/sh\necho "buttons $* $FLIPEROS_BUTTONS_LAYOUT $FLIPEROS_GAME_BUTTONS" '
                                   '>> "%s/calls"\n' % d)
        for name in ("romclean", "buttons"):
            (d / name).chmod(0o755)
        (d / "data").mkdir()
        (d / "data" / "controls.xml").write_text("<dat/>")
        self.env.out("buttons_layout_apply", {
            "ROMCLEAN": str(d / "romclean"), "BUTTONS": str(d / "buttons"), "ROMCLEAN_DATA": str(d / "data"),
            "GAME_BUTTONS": str(d / "games.txt"), "GROOVYMAME": "false", "ROMCLEAN_CACHE": str(d / "cache")})
        calls = (d / "calls").read_text().splitlines()
        self.assertEqual(calls[0], "romclean buttons --xml-command false -listxml --controls-xml %s --out %s"
                         % (d / "data" / "controls.xml", d / "games.txt"))
        self.assertEqual(calls[1], "buttons save %s %s %s" % (self.env.etc / "buttons.map",
                                                              self.env.etc / "buttons.layout", d / "games.txt"))
        # Com o XML do MAME 2010, a tabela do core mame2010, com o XML do
        # GroovyMAME como o MAME mais novo.
        (d / "calls").unlink()
        (d / "mame2010.xml.xz").write_text("")
        self.env.out("buttons_layout_apply", {
            "ROMCLEAN": str(d / "romclean"), "BUTTONS": str(d / "buttons"), "ROMCLEAN_DATA": str(d / "data"),
            "GAME_BUTTONS": str(d / "games.txt"), "GROOVYMAME": "false", "ROMCLEAN_CACHE": str(d / "cache"),
            "MAME2010_XML": str(d / "mame2010.xml.xz")})
        calls = (d / "calls").read_text().splitlines()
        self.assertEqual(calls[1], "romclean buttons --xml %s --cache %s --newer-xml-command false -listxml "
                         "--controls-xml %s --out %s" % (d / "mame2010.xml.xz", d / "cache" / "romclean-mame2010.json",
                                                         d / "data" / "controls.xml", d / "games-mame2010.txt"))
        self.assertTrue(calls[2].startswith("buttons save "))


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
        self.assertEqual(self.env.run("geometry_aborted 'Aborted!'").returncode, 0)
        # Sem "Aborted!" o geometry.py caiu (traceback): nao e um cancelamento.
        crash = "Traceback (most recent call last):\nAttributeError: 'NoneType' object has no attribute 'split'"
        self.assertNotEqual(self.env.run("geometry_aborted \"%s\"" % crash).returncode, 0)

    def test_grid_is_wider_than_the_boot_mode(self):
        # Como o 648x480 do gasetup: no modo exato do boot o Switchres teria
        # de trocar o modo em uso quando o grid reabre depois de uma seta.
        conf = self.env.etc / "fliperos.conf"
        for res, mode in (("640x240S", "648 240 60"), ("320x240S", "328 240 60"),
                          ("640x480iS", "648 480 60"), ("384x288S", "392 288 50")):
            conf.write_text("boot_resolution=%s\n" % res)
            self.assertEqual(self.env.out("geometry_grid_mode").strip(), mode, res)


class ToggleBadgeTests(Base):
    def test_setup_toggles_match_the_badge(self):
        # O selo ON/OFF da interface grafica vem do "(on)"/"(off)" no fim do
        # rotulo: os itens de liga/desliga do Setup tem de seguir esse formato.
        widgets = (SETUP / "gui" / "widgets.py").read_text()
        pattern = re.search(r'TOGGLE = re\.compile\(r"(.+)"\)', widgets).group(1)
        toggle = re.compile(pattern)
        for label in ("Volume leveler (on)", "Debug mode (off)", "Menu sounds (on)"):
            self.assertTrue(toggle.match(label), label)
        for label in ("Menu sounds (no sound files)", "Monitor 3: off", "Turn on (Wi-Fi)"):
            self.assertIsNone(toggle.match(label), label)
        menu = (SETUP / "screens" / "setup-menu.sh").read_text()
        for item in ('"debug|Debug mode ($(debug_enabled && echo on || echo off))|',
                     '"leveler|Volume leveler ($(audio_leveler_enabled && echo on || echo off))|',
                     '"sounds|Menu sounds ($(menu_sounds_label))|'):
            self.assertIn(item, menu)
        self.assertIn("badge(surf, left, top, size, state)", widgets)


class CustomMonitorTests(Base):
    RANGE = "15625.0-15750.0,49.5-65.0,2.075,4.687,7.915,0.128,0.192,1.022,0,0,192,288,448,576"

    def setUp(self):
        super().setUp()
        (self.env.etc / "switchres.ini").write_text("\tmonitor                   generic_15\n"
                                                    "\tcrt_range0                auto\n")
        (self.env.etc / "mame.ini").write_text("monitor generic_15\nswitchres_ini 0\n")
        self.env.out("conf_set monitor generic_15")

    def ini(self):
        return (self.env.etc / "switchres.ini").read_text()

    def test_label(self):
        self.assertEqual(self.env.out("video_monitor_label").strip(), "Generic 15.7 kHz")
        self.env.out("geometry_apply '%s'" % self.RANGE)
        self.assertEqual(self.env.out("video_monitor_label").strip(), "Custom (on Generic 15.7 kHz)")

    def test_same_preset_keeps_custom(self):
        # O Recovery/teste de saidas reaplica o mesmo monitor: o custom fica.
        self.env.out("geometry_apply '%s'; video_apply_monitor generic_15" % self.RANGE)
        self.assertRegex(self.ini(), r"(?m)^\s*monitor\s+custom$")
        self.assertIn(self.RANGE, self.ini())
        self.assertEqual(self.env.out("conf_get geometry").strip(), self.RANGE)
        # O mame.ini fica no preset: com switchres_ini 1 o switchres.ini manda.
        self.assertRegex((self.env.etc / "mame.ini").read_text(), r"(?m)^monitor\s+generic_15$")

    def test_other_preset_drops_custom(self):
        self.env.out("geometry_apply '%s'; video_apply_monitor arcade_15" % self.RANGE)
        self.assertRegex(self.ini(), r"(?m)^\s*monitor\s+arcade_15$")
        self.assertRegex(self.ini(), r"(?m)^\s*crt_range0\s+auto$")
        self.assertEqual(self.env.out("conf_get geometry || echo none").strip(), "none")
        self.assertEqual(self.env.out("video_monitor_label").strip(), "Arcade 15.7 kHz - standard resolution")

    def test_typed_range(self):
        good = ("15625-16200,49.5-65,2.0,4.7,8.0,0.064,0.192,1.024,0,0,192,288,448,576", self.RANGE,
                "31400-31600,49.5-65,0.94,3.77,1.89,0.349,0.064,1.017,0,0,192,288,448,576")
        for r in good:
            self.assertEqual(self.env.run("crt_range_valid '%s'" % r).returncode, 0, r)
        bad = ("auto", "15625-16200,49.5-65,2.0,4.7,8.0,0.064,0.192,1.024,0,0,192,288,448",
               "15625-16200,49.5-65,2.0,4.7,8.0,0.064,0.192,1.024,2,0,192,288,448,576",
               "15625-16200;49.5-65,2.0,4.7,8.0,0.064,0.192,1.024,0,0,192,288,448,576")
        for r in bad:
            self.assertNotEqual(self.env.run("crt_range_valid '%s'" % r).returncode, 0, r)
        self.assertEqual(self.env.out("crt_range_frequency '%s'" % good[0]).strip(), "15k")
        self.assertEqual(self.env.out("crt_range_frequency '%s'" % good[2]).strip(), "31k")
        self.assertEqual(self.env.out("crt_range_frequency 24960-24960,49.5-65").strip(), "25k")

    def test_video_setup_summary_fits_the_carousel(self):
        # A interface grafica so faz o carrossel de icones com ate 5 linhas
        # de texto em cima: orientacao junto da resolucao, nome curto.
        self.assertEqual(self.env.out("orientation_short vertical-ccw").strip(), "vertical CCW")
        body = (SETUP / "screens" / "video-setup.sh").read_text().split("screen_video_setup() {")[1]
        summary = body.split("choice=$(ui_menu_hints")[0]
        self.assertNotIn('"Orientation|', summary)
        self.assertIn('(($(mm_count) > 1)) && monitors=', summary)

    def test_preset_range_from_switchres(self):
        self.env.stub("switchres", 'echo "Switchres: display[0] options: monitor[$7]"\n'
                                   'echo "Switchres: Monitor range %s"\n'
                                   'echo "Switchres: Monitor range 1-2"' % self.RANGE)
        self.assertEqual(self.env.out("video_preset_range arcade_15").strip(), self.RANGE)

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

    def test_i8042_noaux_when_the_kernel_asks_for_it(self):
        # Sem a porta do mouse PS/2 o kernel espera uns 2 s por ela a cada
        # boot; o aviso dele no log poe o i8042.noaux na linha.
        self.assertNotIn("i8042.noaux", self.env.out("boot_compose 'quiet'"))
        # O log segue longo depois do aviso, como no gabinete (com pipefail,
        # um grep que sai cedo matava o dmesg com SIGPIPE e dava falha).
        self.env.stub("dmesg", "echo \"[    2.320970] i8042: If AUX port is really absent "
                               "please use the 'i8042.noaux' option\"; seq 200000")
        line = self.env.out("boot_compose 'quiet'").split()
        self.assertEqual(line.count("i8042.noaux"), 1)
        again = self.env.out("boot_compose '%s'" % " ".join(line)).split()
        self.assertEqual(again.count("i8042.noaux"), 1)
        # Com ele o aviso some, e ele fica.
        self.env.stub("dmesg", ":")
        again = self.env.out("boot_compose '%s'" % " ".join(line)).split()
        self.assertEqual(again.count("i8042.noaux"), 1)

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

    def topbar(self, cols, title="FliperOS", status=STATUS, version=""):
        # ui_topbar escreve em /dev/tty: um terminal falso (script).
        cmd = ("UI_COLS=%d UI_TITLE='%s' UI_STATUS='%s' UI_VERSION='%s'; ui_topbar; echo \"rows=$UI_TOPBAR_ROWS\""
               % (cols, title, status, version))
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

    def test_version_beside_the_title(self):
        lines = self.topbar(80, version="0.8.3")
        self.assertTrue(lines[0].startswith(" FliperOS 0.8.3 "), lines)
        self.assertTrue(lines[0].endswith(self.STATUS), lines)
        self.assertRegex(self.topbar(40, version="0.8.3")[0], r"^ FliperOS 0\.8\.3 +192\.168\.1\.111 - 42%$")
        # Titulo de outra tela (o scraper): sem a versao.
        self.assertEqual(self.topbar(40, title="Scraping retroarch/snes9x", version="0.8.3")[0],
                         " Scraping retroarch/snes9x")
        # O fliperos-setup passa a versao dele para o topo.
        entry = (SETUP / "fliperos-setup").read_text()
        self.assertLess(entry.index("FLIPEROS_SETUP_VERSION="), entry.index('source "$SETUP_DIR/lib/ui.sh"'))


class ScraperTests(Base):
    """Setup > Games > Scraper: o que o Skyscraper raspa e onde a lista vai parar."""

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
        self.assertIn("artwork    snap            %s/snap/retroarch/snes9x;%s/preview/retroarch/snes9x\n" % (media, media), cfg)
        self.assertIn("artwork    flyer           %s/box/retroarch/snes9x\n" % media, cfg)
        self.assertIn("artwork    wheel           %s/logo/retroarch/snes9x\n" % media, cfg)
        self.assertIn("artwork    marquee         %s/marquee/retroarch/snes9x\n" % media, cfg)
        overview = attract / "scraper" / name / "overview"
        self.assertTrue(overview.is_symlink())
        self.assertEqual(overview.resolve(), (media / "texto" / "retroarch" / "snes9x").resolve())
        for t in ("snap", "preview", "logo", "box", "marquee", "texto"):
            self.assertTrue((media / t / "retroarch" / "snes9x").is_dir(), t)
        self.assertTrue((attract / "romlists").is_dir())
        acfg = (attract / "attract.cfg").read_text()
        self.assertEqual(acfg.count("display "), 1)
        self.assertIn("    romlist                 %s\n" % name, acfg)
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
        self.assertIn("%s/snap/mame;%s/preview/mame" % (media, media),
                      (attract / "emulators" / "MAME.cfg").read_text())
        self.assertEqual((attract / "emulators" / (snes + ".cfg")).read_text(), mine)
        self.assertTrue((attract / "scraper" / "MAME" / "overview").is_symlink())
        self.assertEqual((media / "texto" / "mame" / "sf2.txt").read_text(), "Street Fighter II\n")

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
        farm = media / ".skyscraper" / "retroarch-snes9x"
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
            self.assertEqual(os.readlink(farm / sub), "../../%s/retroarch/snes9x" % kind)
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
        self.env.out("scraper_texts %s/gamelist.xml mame" % lists, env)
        self.env.out("scraper_texts %s/metadata.pegasus.txt retroarch/snes9x" % lists, env)
        texto = self.env.dir / "media" / "texto"
        self.assertEqual((texto / "mame" / "sf2.txt").read_text(), "Street Fighter II & friends\n")
        self.assertFalse((texto / "mame" / "semdesc.txt").exists())
        self.assertEqual((texto / "retroarch" / "snes9x" / "Super Mario World (USA).txt").read_text(),
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
        (media / "logo" / "mame").mkdir(parents=True)
        (media / "logo" / "mame" / "sf2.png").write_text("novo")
        self.env.out("scraper_media_migrate", env)
        self.assertEqual((media / "snap" / "mame" / "sf2.png").read_text(), "velho screenshots")
        self.assertEqual((media / "box" / "mame" / "sf2.png").read_text(), "velho covers")
        self.assertEqual((media / "logo" / "mame" / "sf2.png").read_text(), "novo")
        self.assertEqual((media / "preview" / "retroarch" / "snes9x" / "smw.mp4").read_text(), "video")
        self.assertEqual((media / "marquee" / "mame" / "sf2.png").read_text(), "marquee")
        self.assertFalse((old / "screenshots").exists())
        self.assertTrue((old / "wheels" / "sf2.png").exists())
        self.assertFalse((roms / "retroarch" / "snes9x" / "media").exists())
        self.assertFalse((attract / "scraped").exists())

    def test_media_moves_from_the_platform_to_the_folders_of_roms(self):
        # ~/media/<tipo> tinha uma pasta por plataforma (arcade, snes); agora
        # tem as de ~/roms. A do MAME fica com tudo o que era de arcade, as
        # outras pastas de arcade com a arte dos jogos delas; a custom folder
        # (um link) vira o mesmo link em cada uma.
        env, roms, _ = self.scraper_env()
        (roms / "model2").mkdir()
        (roms / "model2" / "daytona.zip").write_text("rom")
        media, disk = self.env.dir / "media", self.env.dir / "disk"
        for d in ("snap/arcade", "snap/snes", "snap/model2", "preview/old-arcade", "preview/mame", "logo/naomi",
                  ".es-de/model2", ".es-de/retroarch-snes9x", ".skyscraper/arcade"):
            (media / d).mkdir(parents=True)
        disk.mkdir()
        for name in ("sf2", "daytona", "mvscj"):
            (media / "snap" / "arcade" / (name + ".png")).write_text(name)
        (media / "snap" / "snes" / "Super Mario World (USA).png").write_text("smw")
        (media / "preview" / "arcade").symlink_to(disk)
        (media / "preview" / "old-arcade" / "sf2.mp4").write_text("de antes")
        (media / "preview" / "mame" / "_info.txt").write_text("vazia")
        (media / "logo" / "naomi" / "mvsc2.png").write_text("sem pasta de jogos agora")
        os.symlink("../../snap/arcade", media / ".es-de" / "model2" / "screenshots")
        os.symlink("../../snap/arcade", media / ".skyscraper" / "arcade" / "screenshots")
        os.symlink("../../snap/snes", media / ".es-de" / "retroarch-snes9x" / "screenshots")
        for _ in range(2):
            self.env.out("media_refolder", env)
            snap = media / "snap"
            self.assertEqual(sorted(p.name for p in snap.iterdir()), ["mame", "model2", "retroarch"])
            self.assertEqual(sorted(p.name for p in (snap / "mame").iterdir()), ["daytona.png", "mvscj.png", "sf2.png"])
            self.assertEqual([p.name for p in (snap / "model2").iterdir()], ["daytona.png"])
            self.assertTrue(os.path.samefile(snap / "model2" / "daytona.png", snap / "mame" / "daytona.png"))
            self.assertEqual((snap / "retroarch" / "snes9x" / "Super Mario World (USA).png").read_text(), "smw")
            preview = media / "preview"
            self.assertEqual(sorted(p.name for p in preview.iterdir()), ["mame", "model2", "old-mame"])
            for key in ("mame", "model2"):
                self.assertEqual(os.readlink(preview / key), str(disk))
            self.assertEqual((preview / "old-mame" / "sf2.mp4").read_text(), "de antes")
            self.assertEqual(list(disk.iterdir()), [])
            self.assertEqual((media / "logo" / "naomi" / "mvsc2.png").read_text(), "sem pasta de jogos agora")
            self.assertEqual(os.readlink(media / ".es-de" / "model2" / "screenshots"), "../../snap/model2")
            self.assertEqual(os.readlink(media / ".skyscraper" / "arcade" / "screenshots"), "../../snap/mame")
            self.assertEqual(os.readlink(media / ".es-de" / "retroarch-snes9x" / "screenshots"),
                             "../../snap/retroarch/snes9x")
        # A do MAME ja e uma custom folder: nada e gravado nela, e a de
        # plataforma fica guardada ao lado.
        (media / "box" / "arcade").mkdir(parents=True)
        (media / "box" / "arcade" / "sf2.png").write_text("capa")
        (media / "box" / "mame").symlink_to(disk)
        self.env.out("media_refolder", env)
        self.assertEqual((media / "box" / "old-mame" / "sf2.png").read_text(), "capa")
        self.assertEqual(list(disk.iterdir()), [])

    def test_attract_overview_follows_the_folder(self):
        # O overview de um emulador que apontava para a pasta de plataforma
        # (~/media/texto/arcade) passa a apontar para a da pasta de jogos.
        env, roms, attract = self.scraper_env()
        (attract / "scraper" / "MAME").mkdir(parents=True)
        (attract / "scraper" / "MAME" / "overview").symlink_to(self.env.dir / "media" / "texto" / "arcade")
        self.env.out("scraper_attract_prepare mame %s/mame arcade" % roms, env)
        self.assertEqual(os.readlink(attract / "scraper" / "MAME" / "overview"),
                         str(self.env.dir / "media" / "texto" / "mame"))

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
              shift 3
              printf 'opcao:%%s\\n' "$@" >&2
              echo "$PICK"
            }
            ui_input() { :; }
            ui_checklist() { echo snap; }
            ui_yesno() { return 1; }
            scraper_scrape_targets() { shift 4; printf 'alvo:%%s\\n' "$@"; }
            screen_scraper_scrape
        """ % SETUP, env)
        self.assertEqual(out.splitlines(), ["alvo:retroarch/snes9x|%s/retroarch/snes9x|snes|1" % roms])

    def test_scraper_site_and_its_account(self):
        # Scraper provider: a escolha fica no fliperos.conf e a conta (o -u do
        # Skyscraper) num arquivo so do root, sem ir para o log. Um site que
        # so funciona com conta nao raspa sem ela.
        env, roms, _ = self.scraper_env()
        accounts = self.env.dir / "accounts"
        env.update({"SCRAPER_ACCOUNTS": str(accounts), "SKYSCRAPER": "true"})
        self.assertEqual(self.env.out("scraper_source_saved", env).strip(), "screenscraper")
        self.assertEqual(self.env.out("scraper_account_label screenscraper; scraper_account_label arcadedb; "
                                      "scraper_account_label mobygames", env).splitlines(),
                         ["no account", "no account needed", "key missing"])
        self.assertEqual(self.env.run("scraper_account_missing mobygames", env).returncode, 0)
        self.assertNotEqual(self.env.run("scraper_account_missing screenscraper", env).returncode, 0)
        screens = """
            source %s/lib/ui.sh
            source %s/screens/setup-menu.sh
            ui_radio() { echo "$PICK"; }
            ui_menu() { echo all; }
            ui_checklist() { echo snap; }
            ui_yesno() { return 1; }
            ui_msg() { printf 'msg:%%s\\n' "$*"; }
            scraper_scrape_targets() { echo "raspa:$1 $3"; }
        """ % (SETUP, SETUP)
        out = self.env.out(screens + """
            ui_input() { [[ $4 == password ]] && echo segredo || echo eu; }
            PICK=screenscraper screen_scraper_source > /dev/null
            scraper_account_label screenscraper
            screen_scraper_scrape
            ui_input() { echo chave123; }
            PICK=mobygames screen_scraper_source > /dev/null
            scraper_source_saved
            screen_scraper_scrape
        """, env)
        self.assertEqual(out.splitlines(), ["account eu", "raspa:screenscraper eu:segredo", "mobygames",
                                            "raspa:mobygames chave123"])
        self.assertEqual(accounts.read_text(), "screenscraper=eu:segredo\nmobygames=chave123\n")
        self.assertEqual(accounts.stat().st_mode & 0o777, 0o600)
        log = (self.env.dir / "setup.log").read_text()
        self.assertNotIn("segredo", log)
        self.assertNotIn("chave123", log)
        out = self.env.out(screens + "scraper_account_set mobygames; screen_scraper_scrape", env)
        self.assertIn("MobyGames only works with an account, and none is saved.", re.sub(r"\x1b\[[0-9;]*m", "", out))
        self.assertNotIn("raspa:", out)
        # Cada site do menu e um modulo do Skyscraper (ou o progetto-SNAPS).
        sites = [line.split("|") for line in self.env.out("scraper_sources", env).splitlines()]
        self.assertEqual([s[0] for s in sites], ["screenscraper", "thegamesdb", "arcadedb", "progettosnaps",
                                                 "mobygames", "igdb", "openretro"])
        self.assertEqual({s[2] for s in sites}, {"login", "none", "key", "idsecret"})
        menu = (SETUP / "screens" / "setup-menu.sh").read_text().split("screen_scraper() {")[1].split("\n}\n")[0]
        # Scrape the games e o scraper do FliperOS (o mesmo do frontend); o
        # Skyscraper fica no item do site.
        for value in ("scrape) screen_scraper_fliperos ;;", "site) screen_scraper_scrape ;;",
                      "source) screen_scraper_source ;;", "torrent) screen_mediapacks ;;"):
            self.assertIn(value, menu)

    def test_scraper_cli_for_the_web_panel(self):
        # fliperos-setup --scraper (a pagina Scraper do painel web): o mesmo
        # da tela, com a conta pela entrada padrao (nunca na linha de comando
        # nem no log) e a raspagem com o site sem tela, retomavel.
        env, roms, _ = self.scraper_env()
        accounts = self.env.dir / "accounts-cli"
        env.update({"SCRAPER_ACCOUNTS": str(accounts), "SKYSCRAPER": "true",
                    "SCRAPER_JOB_DIR": str(self.env.dir / "job-cli")})
        self.env.stub("systemctl", "exit 3")
        status = self.env.out("scraper_cli status", env).splitlines()
        for line in ("source=screenscraper", "kind=login", "account=no account", "media=snap,logo,box,marquee,texto",
                     "skyscraper=1", "pending=", "running=0"):
            self.assertIn(line, status)
        # Com a marca de arcade, para o painel separar as pastas.
        self.assertEqual(self.env.out("scraper_cli systems", env).splitlines(),
                         ["mame|%s/mame|arcade|2|1" % roms, "retroarch/snes9x|%s/retroarch/snes9x|snes|1|0" % roms])
        self.env.out("printf 'eu:segredo\\n' | scraper_cli account screenscraper", env)
        status = self.env.out("scraper_cli status", env)
        self.assertIn("user=eu\n", status)
        self.assertIn("account=account eu\n", status)
        self.assertNotIn("segredo", status)
        self.assertNotIn("segredo", (self.env.dir / "setup.log").read_text())
        self.assertEqual(accounts.read_text(), "screenscraper=eu:segredo\n")
        for bad in ("scraper_cli source nope", "scraper_cli account arcadedb < /dev/null",
                    "printf 'semsecret\\n' | scraper_cli account igdb", "scraper_cli media snap,rm",
                    "scraper_cli site naoexiste", "scraper_cli scrape ../x", "scraper_cli nope"):
            self.assertEqual(self.env.run(bad, env).returncode, 2, bad)
        self.env.out("scraper_cli source mobygames; scraper_cli media snap,preview", env)
        status = self.env.out("scraper_cli status", env)
        self.assertIn("source=mobygames\n", status)
        self.assertIn("media=snap,preview\n", status)
        # Sem a chave, o MobyGames nao raspa.
        r = self.env.run("scraper_cli site", env)
        self.assertEqual(r.returncode, 1)
        self.assertIn("@fail ", r.stdout)
        self.env.out("printf 'chave123\\n' | scraper_cli account mobygames", env)
        # Uma pasta que falha fica para o resume, com as mesmas escolhas.
        fake = 'scraper_run() { echo "run:$1 $4 $5 $6 $7"; [[ $1 != retroarch/snes9x || -n $OK ]]; }\n'
        r = self.env.run(fake + "scraper_cli site --clones", env)
        self.assertEqual(r.returncode, 1)
        self.assertEqual([l for l in r.stdout.splitlines() if l.startswith(("run:", "failed="))],
                         ["run:mame mobygames snap,preview chave123 1",
                          "run:retroarch/snes9x mobygames snap,preview chave123 1", "failed=retroarch/snes9x"])
        self.assertIn("pending=retroarch/snes9x\n", self.env.out("scraper_cli status", env))
        out = self.env.out(fake + "OK=1 scraper_cli resume", env)
        self.assertIn("run:retroarch/snes9x mobygames snap,preview chave123 1", out)
        self.assertIn("pending=\n", self.env.out("scraper_cli status", env))
        self.assertEqual(self.env.run("scraper_cli resume", env).returncode, 1)
        # Uma pasta so; o progetto-SNAPS so nas de arcade.
        out = self.env.out(fake + "scraper_cli source progettosnaps; scraper_cli site", env)
        self.assertEqual([l for l in out.splitlines() if l.startswith("run:")], ["run:mame progettosnaps snap  0"])
        # Scrape the games: o scraper do FliperOS e o resultado.
        out = self.env.out('scraper_fliperos() { echo "fs:$*"; echo total=3 > "$1"; }; scraper_cli scrape mame', env)
        self.assertRegex(out, r"fs:\S+ mame\n")
        self.assertIn("total=3", out)

    def test_bios_cli_for_the_web_panel(self):
        # fliperos-setup --bios (Download BIOS no painel web).
        state = self.env.dir / "bios-state"
        env = {"BIOS_STATE": str(state), "BIOS_TOOL": str(self.env.bin / "fliperos-bios")}
        self.assertEqual(self.env.out("bios_cli status", env), "auto=on\n")
        state.mkdir()
        (state / "last.kv").write_text("downloaded=1\nwhen=hoje\n")
        (state / "last.tsv").write_text("missing\tmame\t/x/neogeo.zip\tneogeo\n")
        (state / "stamp").write_text("x")
        self.env.out("bios_cli auto off", env)
        self.assertEqual(self.env.out("bios_cli status", env), "auto=off\ndownloaded=1\nwhen=hoje\n")
        self.assertEqual(self.env.out("bios_cli list", env), "missing\tmame\t/x/neogeo.zip\tneogeo\n")
        self.env.out("bios_cli auto on", env)
        self.assertFalse((state / "stamp").exists())
        for bad in ("bios_cli auto talvez", "bios_cli check --tudo", "bios_cli nope"):
            self.assertEqual(self.env.run(bad, env).returncode, 2, bad)
        # Sem o fliperos-bios, a falha na tarefa; com ele, a checagem e o resumo.
        r = self.env.run("bios_cli check", env)
        self.assertEqual(r.returncode, 1)
        self.assertIn("@fail ", r.stdout)
        self.env.stub("fliperos-bios", "exit 0")
        out = self.env.out('bios_check() { echo "@step 10 x $2"; echo downloaded=4 > "$1"; }; bios_cli check --refresh', env)
        self.assertEqual(out, "@step 10 x --refresh\ndownloaded=4\n")

    def test_fliperos_scraper_from_the_setup(self):
        # scraper_fliperos: os torrents (como root) e o fliperos-scrape como o
        # usuario, nas pastas pedidas, com a barra (os @step dele).
        env, roms, _ = self.scraper_env()
        calls = self.env.dir / "fs.calls"
        self.env.stub("runuser", 'echo "runuser $*" >> %s; echo "@step 50 sf2 (1 left)"' % calls)
        env = dict(env, FLIPEROS_SCRAPE="/x/fliperos-scrape", FLIPEROS_USER="ninguem")
        out = self.env.out("mediapacks_auto() { echo torrents >> %s; }\n"
                           "scraper_fliperos %s/r mame naomi" % (calls, self.env.dir), env)
        self.assertIn("@step 50 sf2 (1 left)", out)
        lines = calls.read_text().splitlines()
        self.assertEqual(lines[0], "torrents")
        self.assertEqual(lines[1], "runuser -u ninguem -- python3 /x/fliperos-scrape --progress --retry --result "
                                   "%s/r --folder mame --folder naomi" % self.env.dir)

    def packs_env(self):
        env, roms, _ = self.scraper_env()
        for d, rom in (("naomi", "mvsc2.zip"), ("retroarch/fbneo", "kof98.zip")):
            (roms / d).mkdir(parents=True)
            (roms / d / rom).write_text("rom")
        (self.env.dir / "info" / "fbneo_libretro.info").write_text(
            'supported_extensions = "zip|7z"\ncorename = "FinalBurn Neo"\nsystemid = "fb_alpha"\n')
        calls = self.env.dir / "packs.calls"
        self.env.stub("fliperos-mediapacks", 'echo "$*" >> %s\n'
                      'while (($#)); do case $1 in\n'
                      '  --target) cp "$3" "%s.${2//\\//-}"; shift 3; continue ;;\n'
                      '  --result) printf "games=2\\nkept=1\\nfiles=2\\nbytes=2048\\n" > "$2" ;;\n'
                      '  status) printf "pct=0\\nstate=none\\nline=x\\n" ;;\n'
                      'esac; shift; done' % (calls, calls))
        self.env.stub("systemctl", 'echo "systemctl $*" >> %s' % calls)
        env.update({"MEDIAPACKS": str(self.env.bin / "fliperos-mediapacks"),
                    "MEDIAPACKS_LIST": str(ROOT / "config" / "fliperos-media-torrents"),
                    "MEDIAPACKS_USER": str(self.env.dir / "packs.user"),
                    "MEDIAPACKS_STATE": str(self.env.dir / "packs"),
                    "DOWNLOADER_STATE": str(self.env.dir / "dl")})
        return env, roms, calls

    def test_art_packs_come_filled_and_know_their_folders(self):
        # Os pacotes da imagem, cada um com as pastas de jogos dele; o link
        # trocado e o pacote da pessoa ficam na lista dela.
        env, roms, calls = self.packs_env()
        rows = [line.split("\t") for line in self.env.out("mediapacks_list", env).splitlines()]
        self.assertEqual(len(rows), 10)
        self.assertEqual(len({r[0] for r in rows}), 10)
        self.assertEqual({r[1] for r in rows}, {"logo", "preview"})
        for row in rows:
            self.assertRegex(row[3], r"^https://archive\.org/download/%s/%s_archive\.torrent$" % (row[0], row[0]))
            self.assertEqual(row[5], "image")

        def keys(spec):
            return [line.split("|")[0] for line in self.env.out("mediapacks_keys '%s'" % spec, env).splitlines()]

        self.assertEqual(keys("mame,@arcade-cores"), ["mame", "retroarch/fbneo"])
        self.assertEqual(keys("naomi,naomi2"), ["naomi"])
        self.assertEqual(keys("@arcade"), ["mame", "naomi", "retroarch/fbneo"])
        self.assertEqual(self.env.out("mediapacks_games model2; mediapacks_games mame,@arcade-cores", env).split(),
                         ["0", "3"])
        out = self.env.out("mediapacks_save arcade-wheels logo mame 'magnet:?xt=urn:btih:abc' 'Arcade logos'\n"
                           "mediapacks_add preview @arcade http://site/meu.torrent 'Meus videos' > /dev/null\n"
                           "mediapacks_list", env).splitlines()
        self.assertEqual(out[0], "arcade-wheels\tlogo\tmame\tmagnet:?xt=urn:btih:abc\tArcade logos\tchanged")
        self.assertRegex(out[-1], r"^user-[0-9a-f]{10}\tpreview\t@arcade\thttp://site/meu\.torrent\tMeus videos\tuser$")
        self.assertEqual(len(out), 11)
        self.assertIn("\timage", self.env.out("mediapacks_forget arcade-wheels; mediapacks_get arcade-wheels", env))
        self.assertIn("cancel arcade-wheels", calls.read_text())
        self.assertEqual(self.env.run("mediapacks_link_ok 'magnet:?xt=urn:btih:abc' && mediapacks_link_ok "
                                      "https://a/b.torrent && ! mediapacks_link_ok 'so um texto'", env).returncode, 0)

    def test_scraper_files_follow_a_linked_folder(self):
        # ~/roms/mame como link para a pasta de um disco: os jogos sao os de
        # la (sem o -H, o find via so o link e os pacotes de arte achavam 0).
        disk = self.env.dir / "disk-romset"
        disk.mkdir()
        for name in ("sf2.zip", "kof98.7z", "notes.txt"):
            (disk / name).write_text("x")
        link = self.env.dir / "linked-mame"
        link.symlink_to(disk)
        out = self.env.out("scraper_files mame %s" % link).splitlines()
        self.assertEqual([os.path.basename(p) for p in out], ["kof98.7z", "sf2.zip"])

    def test_art_packs_started_by_the_frontend_auto_scrape(self):
        # fliperos-setup --mediapacks auto (o scrape automatico do frontend do
        # FliperOS): todo pacote com ROMs nas pastas vai para o torrent, sem
        # tela; os sem ROMs ficam de fora.
        env, roms, calls = self.packs_env()
        out = self.env.out("mediapacks_auto", env).splitlines()
        self.assertEqual(sorted(line.split("\t")[0] for line in out),
                         ["arcade-wheels", "mame-videos-snaps", "sega-naomi-wheels", "seganaominaomi2videosnaps"])
        self.assertTrue(all(line.split("\t")[1:] == ["2", "2"] for line in out))
        started = [line.split()[1] for line in calls.read_text().splitlines() if line.startswith("start ")]
        self.assertEqual(len(started), 4)
        self.assertIn("finish", calls.read_text().split())
        # Um pacote de .zip por letra fica no torrent (o fliperos-mediapacks
        # baixa uma letra de cada vez): nada e cancelado.
        stub = (self.env.bin / "fliperos-mediapacks").read_text()
        (self.env.bin / "fliperos-mediapacks").write_text(
            stub.replace("bytes=2048\\n", "bytes=2048\\narchives=1\\n"))
        calls.unlink()
        out = self.env.out("mediapacks_auto", env).splitlines()
        self.assertFalse([line for line in out if line.endswith("\tzip")])
        self.assertNotIn("cancel ", calls.read_text())

    def test_art_pack_only_downloads_with_roms_in_its_folders(self):
        # So baixa com ROMs nas pastas do pacote, e so os nomes dos jogos que
        # estao nelas vao para o fliperos-mediapacks.
        env, roms, calls = self.packs_env()
        result = self.env.dir / "result"
        r = self.env.run("mediapacks_start sega-model-2-wheels %s" % result, env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("|No ROMs in the folders of this pack (model2)", r.stdout)
        self.assertFalse(calls.exists())
        self.env.out("mediapacks_start mame-videos-snaps %s" % result, env)
        line = calls.read_text().splitlines()[0]
        media = self.env.dir / "media"
        self.assertRegex(line, r"^start mame-videos-snaps --link https://archive\.org/download/mame-videos-snaps/"
                               r"mame-videos-snaps_archive\.torrent --type preview "
                               r"--target mame \S+/mame %s/preview/mame "
                               r"--target retroarch/fbneo \S+/retroarch-fbneo %s/preview/retroarch/fbneo "
                               r"--progress --result %s$" % (media, media, result))
        # Os jogos da pasta (o CHD da subpasta nao e um deles), sem a extensao.
        self.assertEqual(Path(str(calls) + ".mame").read_text().split(), ["sf2"])
        self.assertEqual(Path(str(calls) + ".retroarch-fbneo").read_text().split(), ["kof98"])
        self.assertTrue((media / "preview" / "retroarch" / "fbneo").is_dir())
        screens = """
            source %s/lib/ui.sh
            source %s/screens/progress.sh
            source %s/screens/mediapacks.sh
            ui_msg() { printf 'msg:%%s\\n' "$*"; }
            ui_info() { :; }
            run_with_progress() { shift 2; "$@" > /dev/null; }
            screen_mediapacks_watch() { echo barra; }
        """ % (SETUP, SETUP, SETUP)
        out = self.env.out(screens + """
            ui_menu() { shift 3; printf 'opcao:%s\\n' "$@" >&2; echo return; }
            screen_mediapacks 2>&1
            MEDIAPACKS_FOUND=$(scraper_detect)
            screen_mediapacks_pack sega-model-2-wheels 2>&1
            echo ---
            screen_mediapacks_pack arcade-wheels 2>&1
            screen_mediapacks_start arcade-wheels
        """, env)
        out = re.sub(r"\x1b\[[0-9;]*m", "", out)
        self.assertIn("opcao:arcade-wheels|Arcade logos (MAME): 3 ROMs", out)
        self.assertIn("opcao:sega-naomi-wheels|Sega Naomi logos: 1 ROMs", out)
        self.assertIn("opcao:sega-model-2-wheels|Sega Model 2 logos: no ROMs in model2", out)
        self.assertIn("opcao:all|Download every pack that has ROMs", out)
        model2, arcade = out.split("---")
        self.assertNotIn("opcao:start|", model2.split("opcao:add|Add a torrent")[1])
        self.assertIn("opcao:start|Download the logos of the ROMs found", arcade)
        self.assertIn("msg:Art pack Arcade logos (MAME): 2 files to download (2.0 KB).", arcade)
        self.assertIn("barra", arcade)
        # O servico sobe so agora, com o download pedido (nunca no boot).
        self.assertIn("systemctl start fliperos-transmission.service", calls.read_text())
        self.assertNotIn("enable", calls.read_text())
        # Sem ROM nenhuma a tela nem abre a lista.
        shutil.rmtree(roms)
        out = self.env.out(screens + "ui_menu() { echo return; }; screen_mediapacks", env)
        self.assertIn("msg:Art packs by torrent No ROMs were found", out)

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
        self.assertTrue((self.env.dir / "media/snap/mame/sf2.png").exists())
        self.assertIn("@msg 1 screenshots saved, 0 already there, 1 not in progetto-SNAPS", out)
        self.assertIn("@step 100 arcade: done", out)
        self.assertTrue((attract / "emulators" / "MAME.cfg").exists())
        self.assertIn("romlist                 MAME", (attract / "attract.cfg").read_text())
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
        screen = (SETUP / "screens" / "setup-menu.sh").read_text().split("screen_scraper_scrape() {")[1].split("\n}\n")[0]
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
        farm = self.env.dir / "media" / ".skyscraper" / "mame"
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
        self.assertEqual(by_name["retroarch-snes9x"].findtext("theme"), "snes")
        # O logo de cada sistema: a plataforma do Skyscraper e "arcade" para
        # o Model 2, o Model 3 e os cores de MAME, mas os temas tem o deles.
        info = Path(env["RA_INFO_DIR"])
        (info / "mame2010_libretro.info").write_text('systemname = "Arcade (various)"\nsystemid = "mame"\n')
        (info / "fbneo_libretro.info").write_text('systemname = "Arcade (various)"\nsystemid = "fb_alpha"\n')
        (info / "fbalpha2012_libretro.info").write_text('systemname = "Arcade (various)"\nsystemid = "fb_alpha"\n')
        self.assertEqual(self.env.out("""
            for k in mame model2 model3 naomi retroarch/mame2010 retroarch/fbneo retroarch/fbalpha2012 \\
              retroarch/snes9x; do
              frontends_esde_theme "$k" "$(scraper_platform "$k" ||
                scraper_libretro_platform "$(scraper_core_info "${k#retroarch/}" systemid)")"
            done""", env).split(), ["arcade", "model2", "model3", "naomi", "mame", "fbneo", "fba", "snes"])
        self.assertEqual(by_name["retroarch-snes9x"].findtext("command"),
                         "/opt/fliperos/bin/fliperos-kms-run retroarch -L "
                         "/opt/fliperos/retroarch/cores/snes9x_libretro.so %ROM%")
        settings = (self.env.dir / "es-de" / "settings" / "es_settings.xml").read_text()
        self.assertIn('<string name="ROMDirectory" value="%s" />' % roms, settings)
        # A arte: <MediaDirectory>/<sistema>/<tipo do ES-DE> -> ~/media/<tipo>/<plataforma>.
        media = self.env.dir / "media"
        self.assertIn('<string name="MediaDirectory" value="%s/.es-de" />' % media, settings)
        self.assertEqual(os.readlink(media / ".es-de" / "mame" / "marquees"), "../../logo/mame")
        self.assertEqual(os.readlink(media / ".es-de" / "retroarch-snes9x" / "screenshots"), "../../snap/retroarch/snes9x")
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

    def test_attract_game_list_follows_the_folder(self):
        # A lista feita com a copia dos jogos pela metade ficava com os
        # primeiros para sempre: agora o jogo novo entra (com o nome do
        # arquivo), o que saiu da pasta sai e as outras linhas ficam.
        env, roms = self.frontends_env()
        attract = self.env.dir / "attract"
        self.env.stub("runuser", "exit 0")
        snes = "Super Nintendo Entertainment System (Snes9x)"
        folder = roms / "retroarch" / "snes9x"
        for name in ("Zelda (USA).SMC", "Copiando (USA).sfc.part", "capa.png"):
            (folder / name).write_text("rom")
        (attract / "romlists").mkdir(parents=True)
        head = "#Name;Title;Emulator;CloneOf;Year\n"
        mario = "Super Mario World (USA);Super Mario World;%s;;1990\n" % snes
        snes_list = attract / "romlists" / (snes + ".txt")
        snes_list.write_text(head + mario + "Apagado (USA);Apagado;%s;;1991\n" % snes)
        # A de arcade com os nomes de verdade e do ROM List (sem os BIOS, com
        # os clones sem arquivo): fica como esta.
        mame = "#Name;Title;Emulator\nsf2;Street Fighter II;MAME\nsf2ce;Street Fighter II' CE;MAME\n"
        (roms / "mame" / "neogeo.zip").write_text("bios")
        (attract / "romlists" / "MAME.txt").write_text(mame)
        self.env.out("frontends_configure attractplus", env)
        self.assertEqual(snes_list.read_text(), head + mario + "Zelda (USA);Zelda (USA);%s;;\n" % snes)
        self.assertEqual((attract / "romlists" / "MAME.txt").read_text(), mame)
        # A de arcade so com nomes de arquivo (--build-romlist) segue a pasta.
        (attract / "romlists" / "MAME.txt").write_text("#Name;Title;Emulator\nsf2;sf2;MAME\n")
        # Nada mudou na pasta: a lista nao e regravada.
        before = snes_list.stat().st_mtime_ns
        self.env.out("frontends_configure attractplus", env)
        self.assertEqual(snes_list.stat().st_mtime_ns, before)
        self.assertEqual((attract / "romlists" / "MAME.txt").read_text(),
                         "#Name;Title;Emulator\nsf2;sf2;MAME\nneogeo;neogeo;MAME\n")
        # Um disco fora (a pasta nao existe): a lista fica.
        snes_list.write_text(head + mario)
        self.env.out('frontends_attract_refresh retroarch/snes9x "%s/fora" "%s"' % (roms, snes), env)
        self.assertEqual(snes_list.read_text(), head + mario)

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
        self.assertIn("      frontends_240p\n", main)
        # Com o Attract-Mode Plus configurado, as listas seguem as pastas
        # (frontends_attract, que tambem faz o que o else faz).
        start = main.split("--session-start)")[1].split(";;")[0]
        self.assertIn("        frontends_attract\n      else\n", start)
        self.assertIn("        frontends_arcadeflow_sync\n      fi\n", start)
        # Mas so quando quem abre e o Attract-Mode: o frontend do FliperOS faz
        # as listas no --romlists, e o boot as fazia duas vezes.
        self.assertLess(start.index("[[ ${2:-} == attractplus ]] || return 0"),
                        start.index("frontends_attract"))
        self.assertIn("frontends_attract > /dev/null",
                      (SETUP / "lib" / "frontends.sh").read_text().split("frontends_lists() {")[1].split("\n}\n")[0])
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
        self.assertIn('"sounds|Menu sounds ($(menu_sounds_label))|', menu)
        self.assertIn("ui_sounds", (SETUP / "lib" / "ui.sh").read_text().split("ui_init() {")[1].split("\n}\n")[0])


class SplashTests(Base):
    """Setup > System > Splash screen (lib/splash.sh): os temas de ~/splashscreen."""

    def setUp(self):
        super().setUp()
        self.home = self.env.dir / "splashscreen"
        self.bundled = self.env.dir / "bundled"
        self.themes = self.env.dir / "themes"
        self.calls = self.env.dir / "splash.calls"
        for d in (self.home, self.bundled, self.themes):
            d.mkdir()
        for name in ("plymouth", "plymouthd", "update-alternatives", "update-initramfs"):
            self.env.stub(name, 'echo "%s $*" >> %s' % (name, self.calls))
        self.env.stub("plymouth", 'echo "plymouth $*" >> %s; [[ $1 != --ping ]]' % self.calls)
        self.vars = {"SPLASH_DIR": str(self.home), "SPLASH_BUNDLED": str(self.bundled),
                     "PLYMOUTH_THEMES": str(self.themes), "SPLASH_PREVIEW_SECONDS": "0"}

    def theme(self, base, folder, file=None, name="Theme", script="theme.script"):
        d = base / folder
        d.mkdir()
        (d / (file or folder + ".plymouth")).write_text(
            "[Plymouth Theme]\r\nName=%s\r\nDescription=Nice\r\nModuleName=script\r\n\r\n[script]\r\n"
            "ImageDir=/usr/share/plymouth/themes/Other\r\nScriptFile=/usr/share/plymouth/themes/Other/%s\r\n"
            % (name, script))
        (d / script).write_text("// script\n")
        (d / "logo.png").write_bytes(b"\x89PNG")
        return d

    def test_boot_screen_follows_a_vertical_monitor(self):
        # O Plymouth nao gira a tela num CRT: o tema do FliperOS escolhe as
        # imagens ja giradas pela linha orientation, que o Setup troca no
        # tema do boot e na copia de ~/splashscreen; o initramfs e refeito so
        # quando o tema do boot e um que tem a linha.
        for base in (self.themes, self.home):
            d = self.theme(base, "fliperos", script="fliperos.script")
            (d / "fliperos.script").write_text('// x\norientation = "horizontal";\nside = "";\n')
        self.theme(self.themes, "other", script="other.script")
        (self.themes / "default.plymouth").symlink_to(self.themes / "other" / "other.plymouth")
        # Status 1: o tema do boot nao e um que gira (nada a refazer).
        self.assertEqual(self.env.run("splash_orientation vertical-cw", self.vars).returncode, 1)
        for base in (self.themes, self.home):
            self.assertIn('orientation = "vertical-cw";', (base / "fliperos" / "fliperos.script").read_text())
        self.assertEqual((self.themes / "other" / "other.script").read_text(), "// script\n")
        (self.themes / "default.plymouth").unlink()
        (self.themes / "default.plymouth").symlink_to(self.themes / "fliperos" / "fliperos.plymouth")
        self.assertEqual(self.env.run("splash_orientation vertical-ccw", self.vars).returncode, 0)
        self.assertIn('orientation = "vertical-ccw";', (self.themes / "fliperos" / "fliperos.script").read_text())
        # O orientation_boot refaz o initramfs uma vez (o splash e o EDID).
        self.env.out("orientation_boot horizontal", self.vars)
        self.assertEqual(self.calls.read_text().count("update-initramfs -u"), 1)
        # O tema do repositorio tem a linha e as imagens giradas.
        theme = SETUP.parent / "config" / "splashscreen" / "fliperos"
        self.assertIn('orientation = "horizontal";\n', (theme / "fliperos.script").read_text())
        for side in ("cw", "ccw"):
            self.assertTrue((theme / ("logo-%s.png" % side)).is_file())
            self.assertTrue((theme / ("throbber-%s-032.png" % side)).is_file())

    def test_list_puts_the_home_folder_first(self):
        self.theme(self.bundled, "fliperos", name="FliperOS")
        self.theme(self.home, "fliperos", name="FliperOS changed")
        self.theme(self.home, "WindozeXP", file="Other.plymouth")
        self.theme(self.home, "bad name")
        (self.home / "empty").mkdir()
        out = self.env.out("splash_list", self.vars).splitlines()
        self.assertEqual(sorted(out), ["WindozeXP|Theme - Nice", "fliperos|FliperOS changed - Nice"])

    def test_set_copies_the_theme_with_its_own_paths(self):
        self.theme(self.home, "WindozeXP", file="Other.plymouth", script="WindozeXP.script")
        self.env.out("splash_set WindozeXP", self.vars)
        dest = self.themes / "WindozeXP"
        plymouth = (dest / "WindozeXP.plymouth").read_text()
        self.assertIn("ImageDir=%s\n" % dest, plymouth)
        self.assertIn("ScriptFile=%s/WindozeXP.script\n" % dest, plymouth)
        self.assertFalse((dest / "Other.plymouth").exists())
        self.assertTrue((dest / "logo.png").is_file())
        calls = self.calls.read_text()
        self.assertIn("update-alternatives --install %s/default.plymouth default.plymouth %s/WindozeXP.plymouth 100"
                      % (self.themes, dest), calls)
        self.assertIn("update-alternatives --set default.plymouth %s/WindozeXP.plymouth" % dest, calls)
        self.assertIn("update-initramfs -u", calls)
        self.assertEqual(self.env.out("conf_get splash", self.vars).strip(), "WindozeXP")

    def test_current_and_unknown_theme(self):
        self.theme(self.bundled, "fliperos")
        self.env.out("splash_stage fliperos", self.vars)
        (self.themes / "default.plymouth").symlink_to(self.themes / "fliperos" / "fliperos.plymouth")
        self.assertEqual(self.env.out("splash_current", self.vars).strip(), "fliperos")
        r = self.env.run("splash_set nothere || echo refused; splash_set ../etc || echo refused", self.vars)
        self.assertEqual(r.stdout.split(), ["refused", "refused"])
        self.assertFalse(self.calls.exists())

    def test_preview_shows_the_theme_over_the_default(self):
        self.theme(self.home, "WindozeXP")
        self.env.out("splash_preview WindozeXP", self.vars)
        calls = self.calls.read_text()
        self.assertIn("plymouthd --mode=boot --tty=/dev/tty1", calls)
        self.assertIn('--kernel-command-line=quiet splash plymouth.splash=WindozeXP', calls)
        self.assertLess(calls.index("plymouth show-splash"), calls.index("plymouth quit"))
        self.assertNotIn("update-alternatives", calls)

    def test_preview_gives_the_tty_its_mode_back(self):
        # O plymouthd sai deixando o tty1 canonico, e o menu (no pty do sudo)
        # parava de receber as setas.
        self.theme(self.home, "WindozeXP")
        self.env.stub("stty", 'echo "stty $*" >> %s; [[ $1 == -g ]] && echo "raw:mode"; true' % self.calls)
        self.env.out("splash_preview WindozeXP", dict(self.vars, SPLASH_TTY="/dev/null"))
        calls = self.calls.read_text().splitlines()
        self.assertEqual([c for c in calls if c.startswith("stty")], ["stty -g", "stty raw:mode"])
        self.assertLess(calls.index("stty -g"), next(i for i, c in enumerate(calls) if c.startswith("plymouthd")))
        self.assertGreater(calls.index("stty raw:mode"), calls.index("plymouth quit"))
        # Mesmo se o plymouthd nao subir.
        self.calls.unlink()
        self.env.stub("plymouthd", 'echo "plymouthd $*" >> %s; false' % self.calls)
        r = self.env.run("splash_preview WindozeXP || echo failed", dict(self.vars, SPLASH_TTY="/dev/null"))
        self.assertIn("failed", r.stdout)
        self.assertIn("stty raw:mode", self.calls.read_text())

    def test_preview_refuses_with_the_boot_plymouthd_running(self):
        self.theme(self.home, "WindozeXP")
        # Com o plymouthd do boot ainda no ar, nada de previa.
        self.env.stub("plymouth", 'echo "plymouth $*" >> %s' % self.calls)
        r = self.env.run("splash_preview WindozeXP || echo busy", self.vars)
        self.assertIn("busy", r.stdout)

    def test_login_copies_the_bundled_themes_once(self):
        self.theme(self.bundled, "fliperos")
        mine = self.env.dir / "home-splash"
        env = dict(os.environ, HOME=str(self.env.dir), FLIPEROS_ROMS=str(self.env.dir / "roms"),
                   FLIPEROS_SPLASH=str(mine), FLIPEROS_SPLASH_BUNDLED=str(self.bundled),
                   FLIPEROS_CORE_INFO=str(self.env.dir / "noinfo"))
        subprocess.run(["bash", str(ROOT / "config/fliperos-roms")], env=env, check=True, timeout=60)
        self.assertTrue((mine / "fliperos" / "fliperos.plymouth").is_file())
        self.assertTrue((mine / "_info.txt").is_file())
        # Sem mexer, a copia acompanha a versao nova da imagem.
        (self.bundled / "fliperos" / "theme.script").write_text("// new\n")
        subprocess.run(["bash", str(ROOT / "config/fliperos-roms")], env=env, check=True, timeout=60)
        self.assertEqual((mine / "fliperos" / "theme.script").read_text(), "// new\n")
        # Mexida, fica como a pessoa deixou.
        (mine / "fliperos" / "logo.png").write_bytes(b"mine")
        (self.bundled / "fliperos" / "theme.script").write_text("// newer\n")
        subprocess.run(["bash", str(ROOT / "config/fliperos-roms")], env=env, check=True, timeout=60)
        self.assertEqual((mine / "fliperos" / "logo.png").read_bytes(), b"mine")
        self.assertEqual((mine / "fliperos" / "theme.script").read_text(), "// new\n")

    def test_in_the_setup_menu(self):
        menu = (SETUP / "screens" / "setup-menu.sh").read_text()
        self.assertIn('"splash|Splash screen|', menu)
        self.assertIn("splash) screen_splash ;;", menu)
        # Onde baixar mais temas, na tela e no _info.txt da pasta.
        url = "https://www.gnome-look.org/browse?cat=108&ord=latest"
        self.assertEqual(self.env.out('echo "$SPLASH_MORE_URL"', self.vars).strip(), url)
        self.assertIn("More themes: $SPLASH_MORE_URL", (SETUP / "screens" / "splash.sh").read_text())
        self.assertIn("More themes: %s" % url, (ROOT / "config/fliperos-roms").read_text())


def load_engine():
    """O config/fliperos-romclean como modulo (nao tem extensao .py)."""
    import importlib.machinery
    import importlib.util
    loader = importlib.machinery.SourceFileLoader("romclean", str(ROOT / "config/fliperos-romclean"))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader("romclean", loader))
    loader.exec_module(module)
    return module


class RomCleanerTests(Base):
    """lib/romclean.sh: o Setup > Games > Cleaner > MAME ROM Cleaner (config/fliperos-romclean)."""

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
        # Setup > Games > Downloader > Filter: o filtro salvo vira as opcoes do
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

    def test_romfilter_cli_for_the_web_panel(self):
        # fliperos-setup --romfilter (a pagina ROM filter do painel web): os
        # parametros e os presets, os valores conferidos, o filtro do
        # Downloader gravado e a previa e a copia de uma pasta com um romset.
        state = self.env.dir / "dl"
        env = dict(self.vars, DOWNLOADER_STATE=str(state), FLIPEROS_USER="ninguem")
        lines = self.env.out('romfilter_cli describe groovymame "%s"' % self.full, env).splitlines()
        self.assertIn("target|groovymame|GroovyMAME 0.289", lines)
        self.assertNotIn("file", [line.split("|")[1] for line in lines if line.startswith("target|")])
        self.assertIn("preset|cabinet|Joystick cabinet (2 players, 6 buttons)", lines)
        self.assertIn("value|cabinet|players=2", lines)
        self.assertIn("param|players|radio|Players|The most players a game may have.|1", lines)
        self.assertIn("param|systems|check|Systems|Mark the Flycast systems to take.|0", lines)
        self.assertIn("option|controls|trackball|Trackball", lines)
        self.assertIn("dest|%s/mame|%s/mame (BIOS: %s/mame)" % (self.roms, self.roms, self.vars["BIOS_ROOT"]), lines)
        self.assertIn("default_target|groovymame", lines)
        self.assertIn("writable|1", lines)
        # So valores das opcoes; um alvo, preset ou pasta que nao existe: 2.
        for bad in ('describe file', 'describe nope', 'count groovymame "" players=99',
                    'count groovymame "" status=working,all', 'count groovymame "" "players=2;reboot"',
                    'count groovymame "" nokey=1', 'save groovymame nope players=2',
                    'scan /nao/existe groovymame players=2', 'run "%s" groovymame delete' % self.full):
            self.assertEqual(self.env.run("romfilter_cli " + bad, env).returncode, 2, bad)
        # Gravar: o filtro do Downloader, com a pasta que ele ja tinha.
        out = self.env.out("romfilter_cli save flycast custom systems=naomi players=2", env)
        self.assertEqual(out.strip(), "saved=Custom, Flycast (Naomi, Naomi 2, Atomiswave)")
        kv = (state / "filter.kv").read_text().splitlines()
        self.assertEqual(kv[:3], ["target=flycast", "dest=%s" % self.roms, "preset=custom"])
        self.assertIn("--systems\nnaomi\n", (state / "filter.scan").read_text())
        # A previa e a copia (cent: trackball; o filtro so com joystick o tira).
        scan = self.env.out('romfilter_cli scan "%s" groovymame controls=joy8,joy4,joy2 clones=none hardware=' % self.full, env)
        items = sorted(line.split("\t")[1] for line in scan.splitlines() if line.startswith("item\t"))
        self.assertEqual(items, ["mslug", "neogeo"])
        self.assertIn("dest_label=%s/mame (BIOS: %s/mame)" % (self.roms, self.vars["BIOS_ROOT"]), scan.splitlines())
        run = self.env.out('romfilter_cli run "%s" groovymame copy controls=joy8,joy4,joy2 clones=none hardware=' % self.full, env)
        self.assertIn("@step 2 Reading the MAME XML and %s" % self.full, run)
        self.assertIn("copied=2", run)
        self.assertTrue((self.roms / "mame" / "mslug.zip").exists())
        self.assertTrue((self.full / "mslug.zip").exists())
        cli = (SETUP / "fliperos-setup").read_text()
        self.assertIn('    --romfilter)\n      # O filtro', cli)
        self.assertIn('      romfilter_cli "${@:2}"\n', cli)

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
            ui_menu() { echo link; }
            ui_input() { echo ' magnet:?xt=urn:btih:abc&dn=MAME '; }
            screen_downloader_magnet roms
            ui_input() { echo 'romset.torrent'; }
            screen_downloader_magnet chds
        """)
        self.assertIn("The MAME ROM Cleaner filter will be used: only the ROMs of the games the filter chooses", out)
        self.assertIn("starts with the Joystick cabinet (2 players, 6 buttons) preset", out)
        self.assertIn("add roms magnet:?xt=urn:btih:abc&dn=MAME --progress", calls)
        self.assertIn("systemctl start fliperos-transmission.service", calls)
        self.assertNotIn("systemctl enable", calls)
        self.assertIn("msg:Downloader That is not a magnet link.", re.sub(r"\x1b\[[0-9;]*m", "", out))
        self.assertNotIn("add chds", calls)
        kv = (state / "filter.kv").read_text()
        self.assertIn("target=groovymame\n", kv)
        self.assertIn("preset=cabinet\n", kv)

    def test_downloader_takes_a_torrent_file_or_address(self):
        # Um .torrent escolhido no seletor de arquivos, ou o endereco de um.
        torrent = self.env.dir / "usb" / "MAME 0.288 CHDs.torrent"
        torrent.parent.mkdir()
        torrent.write_text("d4:infod4:name4:mameee")
        # O seletor e um botao do proprio campo do link: o segundo, depois do
        # navegador (status 4), ou o unico sem navegador (status 3).
        out, calls, _ = self.downloader_screen("""
            downloader_browser_ok() { return 0; }
            ui_input() { printf 'buttons:%%s\\n' "${@:5}" >&2; return 4; }
            ui_browse() { echo "browse:$3|${*:4}" >&2; echo '%s'; }
            screen_downloader_magnet chds
            downloader_browser_ok() { return 1; }
            ui_input() { printf 'alone:%%s\\n' "${@:5}" >&2; return 3; }
            ui_browse() { echo "browse2" >&2; return 1; }
            screen_downloader_magnet roms
            ui_input() { echo 'https://site/romset.torrent'; }
            screen_downloader_magnet roms
        """ % torrent)
        self.assertIn("buttons:Web browser", out)
        self.assertIn("buttons:.torrent file", out)
        self.assertIn("|file .torrent", out)
        self.assertIn("add chds %s --progress" % torrent, calls)
        self.assertIn("alone:.torrent file", out)
        self.assertNotIn("alone:Web browser", out)
        self.assertIn("browse2", out)
        self.assertIn("add roms https://site/romset.torrent --progress", calls)

    def update_screen(self, check, plan, apply_rc=0, script="", notes=""):
        calls = self.env.dir / "upd.calls"
        self.env.stub("fliperos-update", """
            echo "$*" >> %s
            out=""
            for a in "$@"; do [[ $prev == --result ]] && out=$a; prev=$a; done
            case $1 in
              check) printf "%%b" "%s" ;;
              notes) printf "%%b" "%s" ;;
              plan) printf "%%b" "%s" > "$out" ;;
              apply) printf 'applied\\t1\\tno\\t/b/0001\\tFix\\nlevel=1\\n' > "$out"; exit %d ;;
            esac
        """ % (calls, check.replace("\t", "\\t").replace("\n", "\\n"), notes.replace("\n", "\\n"),
               plan.replace("\t", "\\t").replace("\n", "\\n"), apply_rc))
        r = self.env.run("""
            source %s/lib/ui.sh
            source %s/screens/progress.sh
            source %s/screens/patches.sh
            ui_msg() { printf 'msg:%%s\\n' "$*"; }
            ui_yesno() { return 1; }
            ui_pager() { echo "pager:$1:$(cat "$2")"; }
            run_with_progress() { shift 2; "$@" > /dev/null; }
        """ % (SETUP, SETUP, SETUP) + script, dict(self.vars, PATCH_BIN=str(self.env.bin / "fliperos-update")))
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout + r.stderr, calls.read_text() if calls.exists() else ""

    def test_boot_update_screen(self):
        # Sem update pendente: nenhuma tela.
        out, calls = self.update_screen("", "", script="ui_menu() { echo menu >&2; }; screen_update_check")
        self.assertNotIn("menu", out)
        self.assertEqual(calls, "check\n")
        # Com um: os titulos, os arquivos mudados aqui e "Agora nao".
        plan = "pending=2\nchanged=9\nexact=yes\n" + "".join("local\t/etc/f%d\n" % i for i in range(8))
        out, calls = self.update_screen("1\tno\tFix menu\n2\tyes\tNew core\n", plan, script="""
            ui_menu() {
              printf 'text:%%s\\n' "$2" >&2
              printf 'item:%%s\\n' "${@:4}" >&2
              echo x >> "$PATCH_BACKUPS.menus"
              [[ $(wc -l < "$PATCH_BACKUPS.menus") == 1 ]] && echo files || echo later
            }
            PATCH_BACKUPS=%s/backups
            screen_update_check
        """ % self.env.dir)
        self.assertIn("2 part(s), applied in order", out)
        self.assertIn("  1. Fix menu", out)
        self.assertIn("  /etc/f5", out)
        self.assertNotIn("  /etc/f6\n", out.split("pager:")[0])
        self.assertIn("...and 2 more (View the files)", out)
        self.assertIn("pager:Files the update replaces:/etc/f0", out)
        self.assertNotIn("What's new", out)
        self.assertNotIn("item:notes", out)
        self.assertIn("item:later|Not now (installs when the cabinet powers off)", out)
        self.assertNotIn("apply", calls)
        # Aplicar: o update roda e diz como ficou.
        out, calls = self.update_screen("1\tno\tFix menu\n", "pending=1\nchanged=0\nexact=yes\n",
                                        script='ui_menu() { echo "$2" >&2; echo apply; }; screen_update_check')
        self.assertIn("No file changed on this machine is replaced.", out)
        self.assertIn("apply --progress --result", calls)
        self.assertIn("msg:FliperOS update FliperOS is up to date (update 1).", out)
        out, _ = self.update_screen("1\tno\tFix\n", "pending=1\n", apply_rc=1,
                                    script="ui_menu() { echo apply; }; screen_update_check")
        self.assertIn("The update did not finish.", out)

    def test_update_screen_shows_the_changelog_first(self):
        # O que muda vem antes da pergunta, com rolagem, e pode ser lido de
        # novo pelo menu.
        out, calls = self.update_screen("1\tno\tFix menu\n", "pending=1\nchanged=0\nexact=yes\n",
                                        notes="Update 1: Fix menu\n\n- The grid keeps its place.\n", script="""
            ui_menu() {
              printf 'item:%%s\\n' "${@:4}" >&2
              echo x >> "$PATCH_BACKUPS.menus"
              [[ $(wc -l < "$PATCH_BACKUPS.menus") == 1 ]] && echo notes || echo later
            }
            PATCH_BACKUPS=%s/backups
            screen_update_check
        """ % self.env.dir)
        self.assertEqual(out.count("pager:What's new in this FliperOS update:Update 1: Fix menu"), 2)
        self.assertIn("- The grid keeps its place.", out)
        self.assertLess(out.index("pager:What's new"), out.index("item:apply|Apply now"))
        self.assertIn("item:notes|Read what changes", out)
        self.assertEqual(calls.splitlines()[:2], ["check", "notes"])

    def test_wifi_connected_checks_for_the_update_right_away(self):
        # O boot so procura o update com a rede no ar: quem liga o Wi-Fi pelo
        # Setup e perguntado na hora, sem esperar o proximo boot.
        script = """
            source %s/screens/setup-menu.sh
            net_wifi_devices() { echo wlan0; }
            net_scan() { echo 'Casa|80|WPA2'; }
            net_connect() { return ${CONNECT_RC:-0}; }
            net_ips() { echo 192.168.1.2; }
            status_line() { :; }
            speak() { :; }
            sleep() { :; }
            ui_info() { printf 'info:%%s\\n' "$*"; }
            ui_input() { echo senha; }
            ui_menu() { [[ $1 == Wi-Fi ]] && echo Casa || { echo "menu:$1" >&2; echo later; }; }
            is_live() { return ${LIVE:-1}; }
            screen_wifi 0
        """ % SETUP
        plan = "pending=1\nchanged=0\nexact=yes\n"
        out, calls = self.update_screen("1\tno\tFix menu\n", plan, script=script)
        self.assertIn("msg:Wi-Fi Connected to Casa.", out)
        self.assertLess(out.index("Connected to Casa"), out.index("info:FliperOS update Checking for FliperOS updates..."))
        self.assertIn("menu:FliperOS update", out)
        self.assertEqual(calls.split("\n")[0], "check")
        # Sem conectar, ou na midia de instalacao: nao procura.
        for change in ("CONNECT_RC=1", "LIVE=0"):
            (self.env.dir / "upd.calls").unlink(missing_ok=True)
            out, calls = self.update_screen("1\tno\tFix menu\n", plan, script=change + "\n" + script)
            self.assertEqual(calls, "")
            self.assertNotIn("menu:FliperOS update", out)

    def test_downloader_magnet_comes_filled_with_the_image_link(self):
        # Os links da imagem vem preenchidos: Enter usa o de cada tipo.
        out, calls, _ = self.downloader_screen("""
            DOWNLOADER_MAGNETS=%s
            ui_menu() { echo link; }
            ui_input() { echo "input:$2" >&2; echo "$3"; }
            screen_downloader_magnet chds
            DOWNLOADER_MAGNETS=/nada
            ui_input() { echo "input:$2|$3" >&2; }
            screen_downloader_magnet roms
        """ % (ROOT / "config" / "fliperos-downloader-magnets"))
        self.assertIn("input:The FliperOS link of the CHD set is filled in", out)
        self.assertRegex(calls, r"add chds magnet:\?xt=urn:btih:c532c2cb[0-9a-f]+&dn=MAME%200\.288%20CHDs")
        self.assertIn("input:Paste the magnet link of the ROM set (magnet:?xt=urn:btih:...).|\n", out)

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
        self.assertIn("ROM set torrent (required): not set", plain)
        self.assertIn("CHD set torrent (optional): MAME CHDs", plain)
        self.assertIn("msg:ROM/CHD MAME torrent The ROM set torrent is required.", plain)
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

    def test_flycast_games_take_their_controls_from_the_flycast_table(self):
        # O XML do MAME da ao jogo de volante da Naomi o painel generico da
        # placa (joystick e 6 botoes): quem diz o que ele usa e a tabela do
        # Flycast, e o clone fica com o do pai.
        wheel = ('<machine name="%s" romof="%s"%s><description>F355 Challenge%s</description><year>1999</year>'
                 '<input players="2" coins="1"><control type="joy" buttons="6"/></input>'
                 '<driver status="good"/></machine>')
        self.xml.write_text(self.XML.replace("</mame>", wheel % ("f355", "naomi", "", "")
                                             + wheel % ("f355j", "f355", ' cloneof="f355"', " (Japan)") + "</mame>"))
        for name in ("f355", "f355j"):
            (self.full / (name + ".zip")).write_bytes(b"x" * 1536)
        scan = """
            romclean_data_load %(full)s
            mapfile -t kv < <(romclean_preset cabinet flycast)
            mapfile -t args < <(romclean_args flycast "${kv[@]}" clones=keep %(extra)s)
            romclean_scan %(full)s flycast "" "$(romclean_default_dest flycast)" %(plan)s "${args[@]}" > /dev/null
            romclean_list %(plan)s move | cut -d' ' -f1 | paste -sd' ' -
        """
        values = {"full": self.full, "plan": self.env.dir / "plan", "extra": ""}
        # Sem a tabela, passa por jogo de joystick.
        self.assertEqual(self.env.out(scan % values, self.vars).strip(), "awbios f355 f355j kofxi mvsc2 naomi")
        data = self.env.dir / "data"
        data.mkdir()
        (data / "flycast-controls.tsv").write_text("# flycast\tabc\nf355\tpaddle,pedal\t8\nmvsc2\t-\t6\nkofxi\t-\t5\n")
        self.assertEqual(self.env.out(scan % values, self.vars).strip(), "awbios kofxi mvsc2 naomi")
        # Com o volante e os pedais no painel, e sem o limite de 6 botoes.
        values["extra"] = "controls=joy8,paddle,pedal buttons=0"
        self.assertEqual(self.env.out(scan % values, self.vars).strip(), "awbios f355 f355j kofxi mvsc2 naomi")
        values["extra"] = "controls=joy8,paddle,pedal"
        self.assertEqual(self.env.out(scan % values, self.vars).strip(), "awbios kofxi mvsc2 naomi")

    def test_flycast_table_comes_from_the_flycast_source(self):
        # tools/flycast-controls.py: os eixos do descritor de cada jogo viram
        # familias de controle; a tabela guardada cobre os tres sistemas.
        import importlib.machinery
        import importlib.util
        loader = importlib.machinery.SourceFileLoader("flycast_controls", str(ROOT / "tools/flycast-controls.py"))
        tool = importlib.util.module_from_spec(importlib.util.spec_from_loader("flycast_controls", loader))
        loader.exec_module(tool)
        descriptors = tool.read_descriptors("""
            static InputDescriptors vf4_inputs = INPUT_3_BUTTONS("PUNCH", "KICK", "GUARD");
            static InputDescriptors f355_inputs = {
                { { NAOMI_BTN0_KEY, "ASSIST SC" }, { NAOMI_BTN1_KEY, "ASSIST TC" }, NAO_START_DESC },
                { { "ACCEL", Half, 4 }, { "BRAKE", Half, 5 }, { "HANDLE", Full, 0 }, // comment { "X", Full, 1 }
                  { "", Full, 2 } },
            };
            static InputDescriptors lightgun_inputs = {
                { { NAOMI_BTN0_KEY, "TRIGGER" }, { NAOMI_RELOAD_KEY, "" }, },
            };
            static InputDescriptors monkeyba_inputs = {
                { NAO_START_DESC },
                { { "STICK V", Full, 1 }, { "STICK H", Full, 0 }, },
            };
        """)
        self.assertEqual(descriptors, {"vf4_inputs": (set(), 3), "f355_inputs": ({"paddle", "pedal"}, 2),
                                       "lightgun_inputs": ({"lightgun"}, 1), "monkeyba_inputs": ({"analog"}, 0)})
        games = tool.read_games("""
            const BIOS_t BIOS[] = { { "naomi", { { 0, "epr.ic27", 0, 1, 2 } } } };
            const Game Games[] =
            {
                { "f355", nullptr, "Ferrari F355 {deluxe}", 0, 0, "f355bios", M2, ROT0,
                  { { "mpr.ic1", 0, 1 }, }, nullptr, &f355_inputs, f355_eeprom },
                // { "old", nullptr, "", 0, 0, NULL, M2, ROT0, {}, nullptr, &vf4_inputs },
                { "nopanel", "f355", "No descriptor", 0, 0, NULL, M2, ROT0, { { "a", 0, 1 } } },
                { "vf4", NULL, "Virtua Fighter 4", 0, 0, NULL, GD, ROT0, { { "b", 0, 1 } }, "gds-0012", &vf4_inputs },
            };
        """)
        self.assertEqual(games, [("f355", "f355_inputs"), ("vf4", "vf4_inputs")])
        engine = load_engine()
        table = engine.read_flycast(str(ROOT / "config/romclean/flycast-controls.tsv"))
        self.assertGreater(len(table), 200)
        self.assertEqual(table["f355"][0], {"paddle", "pedal"})
        self.assertEqual(table["hotd2"][0], {"lightgun"})
        self.assertEqual(table["mvsc2"], (set(), 6))
        self.assertEqual(table["maxspeed"][0], {"paddle", "pedal"})

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
        self.assertIn('"downloader|Downloader|', menu)
        self.assertIn('downloader) screen_need_internet "The Downloader" && screen_downloads ;;', menu)
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
        self.assertEqual(len(keys), 19)
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
        # Model 2 e Model 3: so a placa do emulador, com qualquer status do MAME.
        for target in ("model2", "model3"):
            out = self.env.out('mapfile -t kv < <(romclean_preset cabinet %s); romclean_args %s "${kv[@]}"'
                               % (target, target), self.vars).splitlines()
            self.assertEqual(out[out.index("--status") + 1], "all")
            self.assertEqual(out[-2:], ["--hardware", target])
            self.assertNotIn("flycast", out)
            self.assertEqual(self.args(target, "hardware=neogeo"), ["--hardware", target])
        for kv, expected in (
                ("chd=only", ["--only", "chd"]), ("chd=no", ["--exclude", "chd"]), ("chd=yes", []),
                ("vector=no", ["--exclude", "vector"]), ("lines=15", ["--scan-rates", "15"]),
                ("lines=15,25,31", []), ("lines=", []), ("orientation=vertical", ["--orientation", "vertical"]),
                ("orientation=horizontal,vertical", []), ("decades=1980,1990", ["--decades", "1980,1990"]),
                ("controls=", ["--controls", ""]), ("controls=joy8,trackball", ["--controls", "joy8,trackball"]),
                ("hardware=neogeo,cps2", ["--hardware", "neogeo,cps2"]),
                # Naomi, Naomi 2 e Atomiswave sao placas da lista: sem nenhuma
                # marcada ficam para o Flycast, marcadas vem como as outras.
                ("hardware=", ["--exclude", "flycast"]),
                ("hardware=naomi,naomi2,atomiswave", ["--hardware", "naomi,naomi2,atomiswave"]),
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
                ("hardware", "naomi,naomi2,atomiswave", "Hardware: Sega Naomi, Sega Naomi 2, Sammy Atomiswave"),
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
        self.assertEqual([o.split("|")[0] for o in out], ["groovymame", "flycast", "model2", "model3", "file"])
        self.assertEqual(out[0], "groovymame|GroovyMAME 0.289")
        self.assertEqual(out[2:4], ["model2|SM2-Emu (Sega Model 2)", "model3|Supermodel (Sega Model 3)"])
        (self.env.dir / "mame2010.xml.xz").write_bytes(b"")
        # O MAME 2010 e o "MAME 3D", dos jogos de arcade baseados no PlayStation.
        self.assertIn("mame2010|MAME 2010 / MAME 3D (0.139, RetroArch core): PlayStation-based (PSX) arcade games",
                      self.env.out("romclean_targets", self.vars).splitlines())
        # O emulador provavel pelo nome da pasta.
        script = ("romclean_default_target /r/retroarch/mame2010; romclean_default_target /r/mame; "
                  "romclean_default_target /pc/Naomi; romclean_default_target /pc/naomi-roms/full; "
                  "romclean_default_target '/pc/MAME 3D'; romclean_default_target '/pc/Model 2'; "
                  "romclean_default_target /pc/supermodel; romclean_default_target /pc/model3")
        self.assertEqual(self.env.out(script, self.vars).split(),
                         ["mame2010", "groovymame", "flycast", "groovymame", "mame2010", "model2", "model3", "model3"])
        self.assertIn('[[ $target == mame2010 ]] && preset=psx',
                      (SETUP / "screens" / "rom-cleaner.sh").read_text())
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
                         ["--dest", "/mnt/usb", "--dest", "%s/retroarch/mame2010" % roms, "--flycast-rest"])
        self.assertEqual(self.env.out("romclean_target_args flycast %s" % roms, self.vars).splitlines(),
                         ["--dest", "%s/naomi" % roms, "--no-devices", "--route", "naomi=%s/naomi" % roms,
                          "--route", "naomi2=%s/naomi2" % roms, "--route", "atomiswave=%s/atomiswave" % roms,
                          "--bios-dest", "%s/dc" % bios])
        # Model 2 e Model 3: ~/roms/model2 e ~/roms/model3, sem BIOS. Dos
        # dispositivos do MAME, so as placas de I/O que o SM2-Emu le.
        self.assertEqual(self.env.out("romclean_default_dest model2; romclean_default_dest model3", self.vars).split(),
                         ["%s/model2" % roms, "%s/model3" % roms])
        self.assertEqual(self.env.out("romclean_target_args model2 %s/model2" % roms, self.vars).splitlines(),
                         ["--dest", "%s/model2" % roms, "--only-devices", "model1io,model1io2"])
        self.assertEqual(self.env.out("romclean_target_args model3 %s/model3" % roms, self.vars).splitlines(),
                         ["--dest", "%s/model3" % roms, "--no-devices"])
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
        self.assertIn('"cleaner|Cleaner|', menu)
        self.assertIn("cleaner) screen_cleaner ;;", menu)
        self.assertNotIn("romcleaner|", menu)
        screen = (SETUP / "screens" / "rom-cleaner.sh").read_text()
        # Em Setup > Games > Cleaner.
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
        # Setup > Games > AttractPlus ROM List: o nome do -listxml no lugar do nome do
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
        # O Attract-Mode Plus ja configurado: as listas do FliperOS vao para
        # ele tambem.
        (attract / "romlists").mkdir(parents=True)
        lists = self.env.dir / "lists-names"
        env = dict(self.vars, ROMS_DIR=str(roms), RA_INFO_DIR=str(info), ATTRACT_DIR=str(attract),
                   MEDIA_DIR=str(self.env.dir / "media"), FLIPEROS_USER="ninguem", FLIPEROS_LISTS=str(lists))
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
        # A lista e do FliperOS; a do Attract-Mode e uma copia.
        self.assertEqual((lists / "MAME.txt").read_text(), (attract / "romlists" / "MAME.txt").read_text())
        acfg = (attract / "attract.cfg").read_text()
        self.assertIn("display Arcade\n", acfg)
        self.assertIn("display Naomi\n", acfg)
        # A pasta que nao e de arcade tambem fica com a tela dela.
        self.assertIn("display Super Nintendo (snes9x)\n", acfg)
        # Os arcades de outra plataforma tambem procuram a arte em arcade.
        media = self.env.dir / "media"
        naomi = (attract / "emulators" / "Naomi.cfg").read_text()
        self.assertIn("artwork    snap            %s/snap/naomi;%s/preview/naomi;%s/snap/mame;%s/preview/mame\n"
                      % (media, media, media, media), naomi)
        self.assertIn("artwork    wheel           %s/logo/naomi;%s/logo/mame\n" % (media, media), naomi)
        self.assertIn("artwork    wheel           %s/logo/mame\n" % media,
                      (attract / "emulators" / "MAME.cfg").read_text())

    def test_attract_romlist_splits_one_flycast_folder_by_bios(self):
        # Naomi, Naomi 2 e Atomiswave apontando para a mesma pasta (o romset
        # inteiro do Flycast): cada lista fica so com os jogos do sistema
        # dela, pela BIOS; o que o XML nao conhece fica nas duas.
        roms, attract = self.env.dir / "flycast-roms", self.env.dir / "flycast-attract"
        (roms / "flycast").mkdir(parents=True)
        for name in ("mvsc2.zip", "kofxi.zip", "awbios.zip", "naomi.zip", "meujogo.zip"):
            (roms / "flycast" / name).write_text("x")
        for key in ("naomi", "atomiswave"):
            (roms / key).symlink_to(roms / "flycast")
        # Sem o Attract-Mode Plus: as listas sao so as do FliperOS, e nada do
        # Attract-Mode e criado.
        lists = self.env.dir / "flycast-lists"
        env = dict(self.vars, ROMS_DIR=str(roms), RA_INFO_DIR=str(self.env.dir / "no-info"), ATTRACT_DIR=str(attract),
                   MEDIA_DIR=str(self.env.dir / "media"), FLIPEROS_USER="ninguem", FLIPEROS_LISTS=str(lists))
        self.env.out("""
            mapfile -t s < <(frontends_romlist_systems)
            frontends_romlist "$ROMCLEAN_CACHE.result" "${s[@]}" > /dev/null
        """, env)

        def names(name):
            return sorted(line.split(";")[0] for line in
                          (lists / (name + ".txt")).read_text().splitlines()[1:])
        self.assertEqual(names("Naomi"), ["meujogo", "mvsc2"])
        self.assertEqual(names("Atomiswave"), ["kofxi", "meujogo"])
        # Os botoes da tabela do Flycast, nao os 6 do painel generico do XML.
        kofxi = next(line.split(";") for line in (lists / "Atomiswave.txt").read_text().splitlines()
                     if line.startswith("kofxi;"))
        self.assertEqual(kofxi[16], "5")
        self.assertFalse(attract.exists())
        # As romlists de antes (sem a separacao, sem esses botoes) sao
        # refeitas ao abrir o frontend.
        frontends = (SETUP / "lib" / "frontends.sh").read_text()
        self.assertIn("FRONTENDS_ROMLIST_VERSION=3\n", frontends)

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
        self.assertIn("display Atomiswave\n    layout                  Basic\n    romlist                 Atomiswave\n"
                      "    in_cycle                yes\n    in_menu                 yes\n", displays)
        self.assertFalse((attract / "attract.cfg").exists())

    def test_attract_displays_written_with_tabs_get_the_attract_mode_format(self):
        # O Arcadeflow le o displays.cfg contando as colunas: as telas que o
        # Setup gravava com tab passam para o formato do Attract-Mode Plus
        # (os filtros e o resto do arquivo ficam).
        attract = self.env.dir / "attract-tabs"
        (attract / "config").mkdir(parents=True)
        (attract / "config" / "attract.cfg").write_text("general\n")
        path = attract / "config" / "displays.cfg"
        path.write_text("# Generated by Attract-Mode Plus v3.2.3\n#\n"
                        "display\tNaomi 2\n\tlayout               Arcadeflow\n\tromlist              Naomi 2\n"
                        "\tin_cycle             yes\n\tin_menu              no\n"
                        "\tfilter               \"Mine\"\n\t\tsort_by              Title\n\n")
        env = dict(self.vars, ATTRACT_DIR=str(attract))
        self.env.out("scraper_attract_display 'Naomi 2'", env)
        self.assertEqual(path.read_text(),
                         "# Generated by Attract-Mode Plus v3.2.3\n#\n"
                         "display Naomi 2\n    layout                  Arcadeflow\n    romlist                 Naomi 2\n"
                         "    in_cycle                yes\n    in_menu                 no\n"
                         "\tfilter               \"Mine\"\n\t\tsort_by              Title\n\n")

    def test_attract_folder_without_games_leaves_the_displays(self):
        # Uma pasta que ficou sem jogos sai do Attract-Mode Plus: o emulador
        # do Setup, a tela, a romlist e os jogos dela na lista Arcade. O
        # emulador da pessoa e a pasta que nao existe agora ficam.
        attract, roms = self.env.dir / "attract-prune", self.env.dir / "roms-prune"
        (attract / "config").mkdir(parents=True)
        (attract / "emulators").mkdir()
        (attract / "romlists").mkdir()
        (attract / "config" / "attract.cfg").write_text("general\n")
        head = "# Criado pelo FliperOS Setup (Scraper).\n"
        for name, folder, text in (("Vazio", "vazio", head), ("Cheio", "cheio", head), ("Meu", "meu", ""),
                                   ("Fora", "fora", head)):
            if name != "Fora":
                (roms / folder).mkdir(parents=True)
                (roms / folder / "_info.txt").write_text("x")
            (attract / "emulators" / (name + ".cfg")).write_text(
                "%sexecutable           /bin/true\nrompath              %s/\n" % (text, roms / folder))
            (attract / "romlists" / (name + ".txt")).write_text("#Name;Title;Emulator\njogo;Jogo;%s\n" % name)
        (roms / "cheio" / "jogo.zip").write_text("rom")
        (attract / "romlists" / "Vazio.db1").write_text("return({\n})\n")
        (attract / "romlists" / "Arcade.txt").write_text(
            "#Name;Title;Emulator\na;A;Vazio\nb;B;Cheio\nc;C;Vazio\n")
        display = "display %s\n    layout                  Basic\n    romlist                 %s\n\tfilter \"All\"\n\n"
        displays = attract / "config" / "displays.cfg"
        displays.write_text("# Generated by Attract-Mode Plus v3.2.3\n#\n" +
                            "".join(display % (n, n) for n in ("Cheio", "Vazio", "Meu", "Fora")))
        env = dict(self.vars, ATTRACT_DIR=str(attract))
        self.env.stub("pgrep", "exit 0")
        self.env.out("frontends_attract_prune", env)
        self.assertTrue((attract / "emulators" / "Vazio.cfg").exists())
        self.env.stub("pgrep", "exit 1")
        self.env.out("frontends_attract_prune", env)
        self.assertEqual(sorted(p.name for p in (attract / "emulators").iterdir()), ["Cheio.cfg", "Fora.cfg", "Meu.cfg"])
        self.assertEqual(sorted(p.name for p in (attract / "romlists").iterdir()),
                         ["Arcade.txt", "Cheio.txt", "Fora.txt", "Meu.txt"])
        self.assertEqual(displays.read_text(), "# Generated by Attract-Mode Plus v3.2.3\n#\n" +
                         "".join(display % (n, n) for n in ("Cheio", "Meu", "Fora")))
        self.assertEqual((attract / "romlists" / "Arcade.txt").read_text(), "#Name;Title;Emulator\nb;B;Cheio\n")

    def test_arcadeflow_scraped_game_gets_the_romlist_fields_back(self):
        # O scraper do Arcadeflow grava vazio o que o ArcadeDB nao respondeu
        # (titulo, jogadores, controle, botoes): o campo vazio volta a ter o
        # valor da romlist, e o que o scraper preencheu fica.
        attract = self.env.dir / "attract-fill"
        (attract / "romlists").mkdir(parents=True)
        head = ("#Name;Title;Emulator;CloneOf;Year;Manufacturer;Category;Players;Rotation;Control;Status;"
                "DisplayCount;DisplayType;AltRomname;AltTitle;Extra;Buttons;Series;Language;Region;Rating\n")
        romlist = attract / "romlists" / "MAME.txt"
        romlist.write_text(head +
                           "samsho;Samurai \"Shodown\";MAME;;1993;SNK;Fighter / Versus;2;0;joystick (8-way);good;1;raster;;;;4;;;;\n"
                           "sf2;Street Fighter II;MAME;;1991;Capcom;Fighter / Versus;2;0;joystick (8-way);good;1;raster;;;;6;;;;\r\n")
        entry = ('   "%s" : {\n      z_manufacturer = "%s"\n      z_title = "%s"\n      z_filename = ""\n'
                 '      z_control = "%s"\n      z_players = "%s"\n      z_buttons = "%s"\n      z_rating = "7.5"\n'
                 '      z_series = ""\n      z_category = "%s"\n   }\n')
        db = attract / "romlists" / "MAME.db1"
        db.write_text("return({\n" + entry % ("samsho", "SNK", "", "", "", "", "") +
                      entry % ("sf2", "Capcom", "Street Fighter 2", "", "2", "6", "Fighting") +
                      entry % ("fora", "", "", "", "", "", "") + "})\n")
        os.utime(romlist, (1000, 1000))
        env = dict(self.vars, ATTRACT_DIR=str(attract))
        self.env.stub("pgrep", "exit 1")
        self.env.out("frontends_arcadeflow_sync", env)
        filled = ("return({\n" +
                  entry % ("samsho", "SNK", "Samurai 'Shodown'", "joystick (8-way)", "2", "4", "Fighter / Versus") +
                  entry % ("sf2", "Capcom", "Street Fighter 2", "joystick (8-way)", "2", "6", "Fighting") +
                  entry % ("fora", "", "", "", "", "", "") + "})\n")
        self.assertEqual(db.read_text(), filled)
        stamp = db.stat().st_mtime_ns
        self.env.out("frontends_arcadeflow_sync", env)
        self.assertEqual((db.read_text(), db.stat().st_mtime_ns), (filled, stamp))

    def test_arcadeflow_gets_the_system_of_each_display(self):
        # O logotipo de cada tela no menu de telas do Arcadeflow: o tema
        # recebe "TELA|SISTEMA..." com os nomes de sistema dele. Model 3 e o
        # da pasta do Supermodel; o do FBNeo e FBNeo; os outros, a plataforma
        # da pasta e o nome do sistema do core. Um core de MAME e um sistema a
        # parte, com o nome dele sem a versao (depois do tab): "MAME 2010".
        roms, info, attract = self.env.dir / "af-roms", self.env.dir / "af-info", self.env.dir / "af-attract"
        for folder in ("mame", "model2", "model3", "naomi2", "dolphin", "retroarch/mame2010", "retroarch/fbneo",
                       "retroarch/snes9x"):
            (roms / folder).mkdir(parents=True)
            (roms / folder / "jogo.zip").write_text("x")
        info.mkdir()
        (info / "mame2010_libretro.info").write_text('systemname = "Arcade (various)"\nsystemid = "mame"\n'
                                                     'corename = "MAME 2010 (0.139)"\n')
        (info / "fbneo_libretro.info").write_text('systemname = "Arcade (various)"\nsystemid = "fb_alpha"\n'
                                                  'corename = "FinalBurn Neo"\n')
        (info / "snes9x_libretro.info").write_text('systemname = "Super Nintendo"\nsystemid = "super_nes"\n'
                                                   'corename = "Snes9x"\n')
        got = self.env.dir / "af-systems"
        self.env.stub("fliperos-arcadeflow", '[ "$1" = systems ] && cat > "%s"' % got)
        env = dict(self.vars, ROMS_DIR=str(roms), RA_INFO_DIR=str(info), ATTRACT_DIR=str(attract),
                   ARCADEFLOW=str(self.env.bin / "fliperos-arcadeflow"))
        # Sem o tema instalado, nada.
        self.env.out("frontends_arcadeflow_systems", env)
        self.assertFalse(got.exists())
        (attract / "layouts" / "Arcadeflow").mkdir(parents=True)
        (attract / "layouts" / "Arcadeflow" / "data_systems.txt").write_text("mame,0\n")
        self.env.out("frontends_arcadeflow_systems", env)
        self.assertEqual(sorted(got.read_text().splitlines()), sorted([
            "MAME|mame", "Model 2|sega model 2", "Supermodel|sega model 3", "Naomi 2|naomi 2", "Dolphin|gamecube",
            "Arcade (various) (MAME 2010 (0.139))\tMAME 2010|mame|arcade", "Arcade (various) (FinalBurn Neo)|fbneo|arcade",
            "Super Nintendo (Snes9x)|snes|Super Nintendo"]))
        body = (SETUP / "lib" / "frontends.sh").read_text().split("frontends_attract() {")[1].split("\n}\n")[0]
        self.assertIn("  frontends_arcadeflow_sync\n  frontends_arcadeflow_systems\n", body)

    def test_attract_defaults_put_displays_on_arcadeflow(self):
        # Toda tela no Basic/BasicPlus (as que o Attract-Mode Plus cria) passa
        # para o Arcadeflow, sempre; a de outro layout fica. O tema recebe o
        # que ainda nao tem do FliperOS. "Group Clones" fica como esta.
        attract = self.env.dir / "attract-defaults"
        (attract / "config").mkdir(parents=True)
        display = "display %s\n    layout                  %s\n    romlist                 %s\n\n"
        displays = attract / "config" / "displays.cfg"
        cfg = attract / "config" / "attract.cfg"
        before = "".join(display % (n, l, n) for n, l in (("mame", "BasicPlus"), ("MAME", "Basic"), ("Meu", "Grid")))
        displays.write_text(before)
        general = "general\n    language                en\n    group_clones            yes\n"
        cfg.write_text(general)
        calls = self.env.dir / "arcadeflow-defaults.calls"
        self.env.stub("fliperos-arcadeflow", 'echo "$*" >> "%s"' % calls)
        env = dict(self.vars, ATTRACT_DIR=str(attract), ARCADEFLOW=str(self.env.bin / "fliperos-arcadeflow"))
        self.env.stub("pgrep", "exit 1")
        # Sem o tema, as telas ficam.
        self.env.out("frontends_attract_defaults", env)
        self.assertEqual(displays.read_text(), before)
        (attract / "layouts" / "Arcadeflow").mkdir(parents=True)
        (attract / "layouts" / "Arcadeflow" / "layout.nut").write_text("// Arcadeflow\n")
        self.env.stub("pgrep", "exit 0")
        self.env.out("frontends_attract_defaults", env)
        self.assertEqual(displays.read_text(), before)
        self.assertFalse(calls.exists())
        self.env.stub("pgrep", "exit 1")
        self.env.out("frontends_attract_defaults", env)
        self.assertEqual(calls.read_text(), "prefs\n")
        self.assertEqual(displays.read_text(), "".join(
            display % (n, l, n) for n, l in (("mame", "Arcadeflow"), ("MAME", "Arcadeflow"), ("Meu", "Grid"))))
        self.assertEqual(cfg.read_text(), general)

    def test_attract_empty_romlists_and_unused_emulators_are_removed(self):
        # A romlist sem jogos sai, com o banco do Arcadeflow e as telas dela
        # (as que o Attract-Mode Plus cria sozinho na primeira execucao), e
        # depois o emulador que nenhuma romlist usa. A colecao do Arcadeflow e
        # o emulador que so aparece na lista de outro nome ficam.
        attract = self.env.dir / "attract-empty"
        for sub in ("config", "emulators", "romlists"):
            (attract / sub).mkdir(parents=True)
        (attract / "config" / "attract.cfg").write_text("general\n")
        head = "#Name;Title;Emulator;CloneOf\n"
        lists = {"mame": head, "flycast": head + "\r\n", "MAME": head + "sf2;Street Fighter II;MAME;\n",
                 "Arcade": head + "sf2;Street Fighter II;MAME;\nvf;Virtua Fighter;Model 2;\r\n",
                 "AF Favourites": head}
        for name, text in lists.items():
            (attract / "romlists" / (name + ".txt")).write_bytes(text.encode())
        for name in ("mame.db1", "mame.db2", "MAME.db1"):
            (attract / "romlists" / name).write_text("return({\n})\n")
        for name in ("mame", "flycast", "MAME", "Model 2", "pcsx2"):
            (attract / "emulators" / (name + ".cfg")).write_text("executable /bin/true\n")
        display = "display %s\n    layout                  BasicPlus\n    romlist                 %s\n    filter                  All\n\n"
        displays = attract / "config" / "displays.cfg"
        top = "# Generated by Attract-Mode Plus v3.2.3\n#\n"
        displays.write_text(top + "".join(display % pair for pair in (
            ("mame", "mame"), ("MAME", "MAME"), ("Dreamcast", "flycast"), ("Arcade", "Arcade"), ("pcsx2", "pcsx2"))))
        env = dict(self.vars, ATTRACT_DIR=str(attract), ATTRACTPLUS=str(self.env.bin / "attractplus"))
        self.env.stub("attractplus", "exit 0")
        self.env.stub("pgrep", "exit 0")
        self.env.out("frontends_attract_empty", env)
        self.assertTrue((attract / "romlists" / "mame.txt").exists())
        self.env.stub("pgrep", "exit 1")
        self.env.out("frontends_attract_empty", dict(env, ATTRACTPLUS="attractplus-que-nao-existe"))
        self.assertTrue((attract / "romlists" / "mame.txt").exists())
        self.env.out("frontends_attract_empty", env)
        self.assertEqual(sorted(p.name for p in (attract / "romlists").iterdir()),
                         ["AF Favourites.txt", "Arcade.txt", "MAME.db1", "MAME.txt"])
        self.assertEqual(sorted(p.name for p in (attract / "emulators").iterdir()), ["MAME.cfg", "Model 2.cfg"])
        self.assertEqual(displays.read_text(), top + "".join(display % pair for pair in (
            ("MAME", "MAME"), ("Arcade", "Arcade"), ("pcsx2", "pcsx2"))))

    def test_arcadeflow_reads_a_rebuilt_romlist_again(self):
        # O Arcadeflow guarda o que leu da romlist em <emulador>.db1: o de uma
        # romlist refeita depois e esvaziado (o .db2, com os favoritos, fica),
        # ou sai se nao ha .db2. Com o Attract-Mode aberto nada muda.
        attract = self.env.dir / "attract-db"
        lists = attract / "romlists"
        lists.mkdir(parents=True)
        for name in ("MAME", "Naomi", "Novo", "Em dia"):
            (lists / (name + ".txt")).write_text("#Name;Title\n")
            (lists / (name + ".db1")).write_text("return({\n   \"sf2\" : {\n   }\n})\n")
        (lists / "MAME.db2").write_text("favoritos")
        (lists / "Em dia.db2").write_text("favoritos")
        (lists / "Novo.db1").unlink()
        env = dict(self.vars, ATTRACT_DIR=str(attract))
        self.env.out("""
            cd "$ATTRACT_DIR/romlists"
            touch -d '2026-01-01' MAME.db1 Naomi.db1 'Em dia.txt'
            touch -d '2026-01-02' MAME.txt Naomi.txt 'Em dia.db1'
        """, env)
        self.env.stub("pgrep", "exit 0")
        self.env.out("frontends_arcadeflow_sync", env)
        self.assertIn("sf2", (lists / "MAME.db1").read_text())
        self.env.stub("pgrep", "exit 1")
        self.env.out("frontends_arcadeflow_sync", env)
        self.assertEqual((lists / "MAME.db1").read_text(), "return({\n})\n")
        self.assertEqual((lists / "MAME.db2").read_text(), "favoritos")
        self.assertFalse((lists / "Naomi.db1").exists())
        self.assertFalse((lists / "Novo.db1").exists())
        self.assertIn("sf2", (lists / "Em dia.db1").read_text())
        # Ja em dia: outra passada nao mexe em nada.
        self.env.out("frontends_arcadeflow_sync", env)
        self.assertEqual((lists / "MAME.db1").read_text(), "return({\n})\n")

    def test_arcadeflow_screen_follows_the_console_mode(self):
        # Num tubo de 15 kHz o Arcadeflow recebe o modo do console (o do
        # boot) a cada abertura do launcher, para desenhar em 4:3 num 640x240;
        # sem o modo, o do Video Setup; em outro monitor, desfaz.
        attract = self.env.dir / "attract-screen"
        (attract / "layouts" / "Arcadeflow").mkdir(parents=True)
        calls = self.env.dir / "arcadeflow-screen.calls"
        self.env.stub("fliperos-arcadeflow", 'echo "$*" >> "%s"' % calls)
        fb = self.env.dir / "virtual_size"
        fb.write_text("640,240\n")
        env = dict(self.vars, ATTRACT_DIR=str(attract), ARCADEFLOW=str(self.env.bin / "fliperos-arcadeflow"),
                   FLIPEROS_FB_SIZE=str(fb))
        # Sem o tema instalado, nada.
        self.env.out("conf_set frequency 15k; frontends_arcadeflow_screen", env)
        self.assertFalse(calls.exists())
        (attract / "layouts" / "Arcadeflow" / "layout.nut").write_text("// Arcadeflow\n")
        self.env.out("conf_set frequency 15k; frontends_arcadeflow_screen", env)
        fb.unlink()
        self.env.out("conf_set frequency 15k; conf_set boot_resolution 320x240; frontends_arcadeflow_screen", env)
        self.env.out("conf_set frequency 31k; frontends_arcadeflow_screen", env)
        self.assertEqual(calls.read_text(), "screen 640 240\nscreen 320 240\nscreen\n")
        main = (SETUP / "fliperos-setup").read_text()
        self.assertIn("      frontends_arcadeflow_screen\n", main.split("--session-start)")[1].split(";;")[0])

    def test_new_attract_displays_use_arcadeflow_when_it_is_installed(self):
        # O tema padrao e o Arcadeflow, que o Setup > Games > Frontend baixa; sem ele
        # (sem rede) as telas novas ficam no Basic do FliperOS.
        attract = self.env.dir / "attract-theme"
        (attract / "layouts" / "Arcadeflow").mkdir(parents=True)
        env = dict(self.vars, ATTRACT_DIR=str(attract))
        self.env.out("scraper_attract_display Naomi", env)
        (attract / "layouts" / "Arcadeflow" / "layout.nut").write_text("// Arcadeflow\n")
        self.env.out("scraper_attract_display Atomiswave", env)
        acfg = (attract / "attract.cfg").read_text()
        self.assertIn("display Naomi\n    layout                  Basic\n", acfg)
        self.assertIn("display Atomiswave\n    layout                  Arcadeflow\n", acfg)
        # Ja instalado, o Setup nao baixa de novo.
        calls = self.env.dir / "arcadeflow.calls"
        self.env.stub("fliperos-arcadeflow", 'echo "$*" >> "%s"' % calls)
        env["ARCADEFLOW"] = str(self.env.bin / "fliperos-arcadeflow")
        self.env.out("frontends_attract_theme", env)
        self.assertFalse(calls.exists())
        (attract / "layouts" / "Arcadeflow" / "layout.nut").unlink()
        self.assertIn("@step 0 Starting", self.env.out("frontends_attract_theme", env))
        self.assertEqual(calls.read_text(), "fetch --progress\n")

    def test_attract_displays_get_the_default_filters(self):
        # Toda tela ganha os filtros padrao (genero, fabricante, ano); as que
        # o usuario ja filtrou ficam como estao.
        attract = self.env.dir / "attract-filters"
        (attract / "config").mkdir(parents=True)
        (attract / "config" / "attract.cfg").write_text("general\n")
        (attract / "config" / "displays.cfg").write_text(
            "# Generated by Attract-Mode Plus v3.2.3\n#\n"
            "display Naomi\n    layout                  BasicPlus\n    romlist                 Naomi\n\n"
            "display Mine\n    romlist                 Mine\n    filter                  \"Only mine\"\n"
            "        rule                    Title contains X\n\n")
        env = dict(self.vars, ATTRACT_DIR=str(attract))
        self.env.out("scraper_attract_display Atomiswave", env)
        path = attract / "config" / "displays.cfg"
        displays = path.read_text(encoding="utf-8")
        self.assertEqual(displays.count('\tfilter               "All Games"\n'), 2)
        naomi = displays.split("display Naomi\n")[1].split("display Mine\n")[0]
        self.assertTrue(naomi.startswith("    layout                  BasicPlus\n    romlist                 Naomi\n"
                                         '\tfilter               "All Games"\n'))
        self.assertTrue(naomi.endswith('\t\trule                 Year equals 20..\n\n'))
        mine = displays.split("display Mine\n")[1].split("display Atomiswave\n")[0]
        self.assertNotIn("All Games", mine)
        self.assertIn('\tfilter               "Most Played"\n\t\tsort_by              PlayedTime\n'
                      '\t\treverse_order        true\n\t\tlist_limit           25\n', displays)
        self.assertIn('\tfilter               "\u00a9 Raizing / Eighting"\n\t\tsort_by              Title\n'
                      '\t\trule                 Manufacturer equals (Raizin.*)|(Eightin.*)|(.*/.Raizin.*)|(.*/.Eightin.*)\n',
                      displays)
        self.assertEqual(displays.count("\tfilter "), 2 * 44)
        self.env.out("scraper_attract_display Atomiswave; scraper_attract_display Naomi", env)
        self.assertEqual(path.read_text(encoding="utf-8"), displays)

    def test_duckstation_folder_opens_in_duckstation(self):
        self.assertEqual(self.env.out("scraper_platform duckstation; scraper_attract_emulator duckstation").splitlines(),
                         ["psx", "DuckStation|/opt/fliperos/bin/fliperos-x11-run|duckstation \"[romfilename]\"|"
                                 ".cue;.chd;.pbp;.m3u;.iso;.img;.ecm;.mds;.exe;.psexe"])

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
        for path, name in (("main-menu.sh", "screen_main_menu"), ("setup-menu.sh", "screen_setup_menu"),
                           ("setup-menu.sh", "screen_setup_games"), ("setup-menu.sh", "screen_setup_system")):
            body = (SETUP / "screens" / path).read_text().split(name + "() {")[1].split("\n}\n")[0]
            self.assertIn("  while true; do\n    screen_reload_if_updated\n", body, name)

    def test_rom_cleaner_shows_why_the_scan_failed(self):
        screen = (SETUP / "screens" / "rom-cleaner.sh").read_text()
        self.assertIn('2> "$list")\n  rc=$?\n  cat "$list" >> "$FLIPEROS_LOG"', screen)
        self.assertIn("tail -n 1", screen.split("if ((rc != 0)); then")[1].split("fi\n")[0])


class SetupGroupsTests(Base):
    """O Setup em grupos e os baloes de informacao de cada item (ui_menu_hints)."""

    SCREENS = ("main-menu.sh", "setup-menu.sh", "joysticks.sh", "video-setup.sh", "downloader.sh")

    def entries(self):
        """(arquivo, titulo, valor, rotulo, balao) de cada item dos menus com balao."""
        found = []
        for name in self.SCREENS:
            text = (SETUP / "screens" / name).read_text()
            for call in text.split("ui_menu_hints ")[1:]:
                title = call.split('"')[1]
                body = call.split(") ||")[0]
                for value, label, hint in re.findall(r'"([a-z_]+)\|([^|"]+)\|([^"|]+)"', body):
                    found.append((name, title, value, label, hint))
        return found

    def test_every_menu_opens_on_the_first_item(self):
        # O cursor de um menu comeca no primeiro item (o "last" vazio); depois
        # de um submenu ele volta ao item escolhido.
        for path in sorted((SETUP / "screens").glob("*.sh")):
            text = path.read_text()
            for value in re.findall(r'^\s+local [^\n]*\blast=(\S+)', text, re.M):
                self.assertEqual(value, '""', path.name)
            joined = text.replace("\\\n", " ")
            for default in re.findall(r'\bui_menu(?:_hints)? +"[^"]*" +(?:"[^"]*"|\$\(.*?\)") +(\S+)', joined):
                self.assertFalse(re.fullmatch(r'[0-9]+', default), (path.name, default))
            self.assertNotIn("${last:-", text, path.name)
        emulators = (SETUP / "screens" / "setup-menu.sh").read_text()
        self.assertNotIn("|| last=$name", emulators)

    def test_setup_is_grouped_in_order(self):
        menu = (SETUP / "screens" / "setup-menu.sh").read_text()
        order = {}
        for name in ("screen_setup_menu", "screen_setup_games", "screen_setup_system"):
            body = menu.split(name + "() {")[1].split("\n}\n")[0]
            order[name] = re.findall(r'^      "([a-z]+)\|', body, re.M)
            # Cada item do menu tem o seu caso.
            for value in order[name]:
                self.assertIn("      %s) " % value, body, name)
        # Imagem, som, rede, jogos, controles e o resto do sistema.
        self.assertEqual(order["screen_setup_menu"],
                         ["video", "audio", "network", "games", "joysticks", "system", "return"])
        # Na ordem de por jogos no gabinete.
        self.assertEqual(order["screen_setup_games"], ["emulators", "frontend", "extras", "custom", "folders", "downloader", "cleaner",
                                                       "scraper", "romlist", "return"])
        self.assertEqual(order["screen_setup_system"], ["latency", "services", "quirks", "password", "update",
                                                        "whatsnew", "debug", "lab", "splash", "return"])
        self.assertIn("games) screen_setup_games ;;", menu)
        self.assertIn("system) screen_setup_system ;;", menu)

    def test_every_item_has_a_balloon_that_fits(self):
        entries = self.entries()
        self.assertGreater(len(entries), 50)
        titles = {title for _, title, _, _, _ in entries}
        for title in ("FliperOS Setup", "FliperOS", "Setup", "Games", "System", "Joysticks", "Video Setup",
                      "Audio Setup", "Network Setup", "Downloader"):
            self.assertIn(title, titles)
        hints = [hint for _, _, _, _, hint in entries]
        # Em 320x240 (40 colunas) o balao tem duas linhas de 34 colunas; em
        # 640x480 (80 colunas), uma linha dentro da moldura.
        script = "source %s/lib/ui.sh\nUI_HINTS=(%s)\n" % (SETUP, " ".join("'%s'" % h for h in hints))
        for hint in hints:
            self.assertNotIn("'", hint)
            self.assertTrue(hint.endswith(".") or hint.endswith(")."), hint)
        self.assertEqual(self.env.out(script + 'ui_hint_lines 34; ui_hint_lines 66; echo "$UI_HINT_SMALL_LINES"').split(),
                         ["2", "1", "2"])

    def test_menu_hints_split_the_balloons(self):
        # O ui_menu recebe os rotulos sem o balao, e os baloes na ordem dos
        # itens em UI_HINTS (vazio no item sem balao); depois nada sobra.
        out = self.env.dir / "menu.out"
        r = self.env.out("""
            source %s/lib/ui.sh
            ui_menu() { printf '%%s\\n' "$@" "--" "${UI_HINTS[@]}" > "$MENU_OUT"; echo two; }
            ui_menu_hints "Title" "" one "one|One|First balloon." "two|Two|Second (longer) balloon." "three|Three"
            echo "hints=${#UI_HINTS[@]}"
        """ % SETUP, dict(MENU_OUT=str(out)))
        self.assertEqual(r.split(), ["two", "hints=0"])
        self.assertEqual(out.read_text().split("\n"),
                         ["Title", "", "one", "one|One", "two|Two", "three|Three", "--",
                          "First balloon.", "Second (longer) balloon.", "", ""])

    def test_balloon_for_each_screen_size(self):
        # 80x30: moldura da largura da caixa do titulo, tantas linhas quantas
        # o maior texto pede. 40x15: so o texto, duas linhas, no lugar da
        # ajuda do gum.
        r = self.env.out("""
            source %s/lib/ui.sh
            show() {
              echo "$GUM_CHOOSE_HINT_BORDER $GUM_CHOOSE_HINT_WIDTH $GUM_CHOOSE_HINT_LINES ${UI_HINT_ARGS[*]}|"
            }
            UI_HINTS=("First balloon." "Second balloon.")
            UI_ROWS=30 UI_COLS=80
            ui_hint_env; show
            echo "$GUM_CHOOSE_HINTS"
            UI_ROWS=15 UI_COLS=40
            ui_hint_env; show
        """ % SETUP)
        self.assertEqual(r.split("\n"), ["1 70 1 |", "First balloon.", "Second balloon.",
                                         "0 34 2 --show-help=false|", ""])
        # O ui_menu passa o balao ao gum so no menu que o tem.
        menu = (SETUP / "lib" / "ui.sh").read_text().split("\nui_menu() {")[1].split("\n}\n")[0]
        self.assertIn('local -x GUM_CHOOSE_HINTS=""', menu)
        self.assertIn('  ((${#UI_HINTS[@]})) && ui_hint_env\n  height=$(ui_list_height "${#labels[@]}")\n', menu)
        self.assertIn('args+=("${UI_HINT_ARGS[@]}")', menu)

    def test_the_balloon_takes_rows_from_the_list(self):
        # Em 80x30 o balao (moldura + texto) sai das linhas da lista.
        script = """
            source %s/lib/ui.sh
            UI_ROWS=30 UI_COLS=80 UI_USED_ROWS=6
            ui_list_height 40
            UI_HINTS=("One line." "$(printf 'word %%.0s' {1..20})")
            ui_hint_env
            ui_list_height 40
            echo "$GUM_CHOOSE_HINT_LINES"
        """ % SETUP
        self.assertEqual(self.env.out(script).split(), ["19", "15", "2"])


class ExtrasScreenTests(Base):
    def test_installed_pixelcade_offers_the_paid_art_pack(self):
        calls = self.env.dir / "extras.calls"
        self.env.stub("fliperos-extras", 'case $1 in list) echo "pixelcade|1|Pixelcade (LED/LCD marquee)" ;; '
                      'installed) exit 0 ;; *) echo "extras $*" >> %s ;; esac' % calls)
        self.env.stub("fliperos-pixelcade", 'echo "pixelcade $*" >> %s' % calls)
        env = dict(EXTRAS_CMD=str(self.env.bin / "fliperos-extras"),
                   PIXELCADE_CMD=str(self.env.bin / "fliperos-pixelcade"), MENU_COUNT=str(self.env.dir / "menu.count"))
        r = self.env.run("""
            source %s/lib/ui.sh
            source %s/lib/extras.sh
            source %s/screens/progress.sh
            source %s/screens/setup-menu.sh
            # Extras > Pixelcade > art pack > Return > Return.
            ui_menu() {
              echo x >> "$MENU_COUNT"
              case $(wc -l < "$MENU_COUNT") in 1) echo pixelcade ;; 2) echo artpack ;; *) echo return ;; esac
            }
            ui_input() { echo ' ABC-123 '; }
            ui_msg() { echo "msg:$*"; }
            ui_yesno() { echo "yesno:$*"; return 1; }
            run_with_progress() { shift 2; "$@" > /dev/null; }
            net_online() { :; }
            screen_extras
        """ % (SETUP, SETUP, SETUP, SETUP), env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(calls.read_text().splitlines() if calls.exists() else r.stdout + r.stderr,
                         ["pixelcade artpack ABC-123 --progress"])
        self.assertIn("msg:Pixelcade art pack The art pack is installed.", r.stdout)
        # O Pixelcade instalado tem o menu dele, nao a pergunta de atualizar.
        self.assertNotIn("yesno:", r.stdout)

    def test_zedmd_says_which_firmware_it_needs(self):
        calls = self.env.dir / "extras.calls"
        self.env.stub("fliperos-extras", 'case $1 in list) echo "zedmd|0|ZeDMD (open-source LED DMD, firmware 5.1+)" ;; '
                      'installed) exit 1 ;; *) echo "extras $*" >> %s ;; esac' % calls)
        env = dict(EXTRAS_CMD=str(self.env.bin / "fliperos-extras"), MENU_COUNT=str(self.env.dir / "menu.count"))
        r = self.env.run("""
            source %s/lib/ui.sh
            source %s/lib/extras.sh
            source %s/screens/progress.sh
            source %s/screens/setup-menu.sh
            # Extras > ZeDMD > Yes > Return.
            ui_menu() {
              echo x >> "$MENU_COUNT"
              case $(wc -l < "$MENU_COUNT") in 1) echo zedmd ;; *) echo return ;; esac
            }
            ui_msg() { echo "msg:$*"; }
            ui_yesno() { echo "yesno:$*"; }
            run_with_progress() { shift 2; "$@" > /dev/null; }
            net_online() { :; }
            screen_extras
        """ % (SETUP, SETUP, SETUP, SETUP), env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(calls.read_text().splitlines(), ["extras install zedmd --progress"])
        # Antes de instalar: a versao que conecta, as que nao (as do Batocera
        # 41) e onde ver a versao; o texto cabe no dialogo.
        ask = next(line for line in r.stdout.splitlines() if line.startswith("yesno:"))
        for part in ("firmware 5.1.0 or newer", "3.x, 4.x, 5.0", "Batocera 41", "on its logo", "Frontends page",
                     "Download and install ZeDMD (open-source LED DMD, firmware 5.1+) now?"):
            self.assertIn(part, ask)
        self.assertLessEqual(len(ask.split(" ", 1)[1]), 300)
        # Depois: o que o painel parado no logo quer dizer.
        self.assertIn("installed. If the display stays on its logo, its firmware is older than 5.1", r.stdout)


class LabModeTests(Base):
    """Setup > System > Lab mode (lib/services.sh, config/fliperos-lab): liga,
    mostra o endereco e desliga."""

    def setUp(self):
        super().setUp()
        state = self.env.dir / "lab.on"
        self.state = state
        self.env.stub("fliperos-lab", """
            case $1 in
              status) if [ -e %(s)s ]; then on=1; url=https://a-b.trycloudflare.com/lab?key=K; else on=0; url=; fi
                      printf 'installed=1\\nactive=%%s\\nurl=%%s\\nexpires=0\\nhours=4\\n' $on "$url" ;;
              start) [ "$2" = --progress ] && touch %(s)s && echo '@step 100 Lab mode is on' ;;
              stop) rm -f %(s)s ;;
            esac
        """ % {"s": state})
        self.lab_env = {"LAB_CMD": str(self.env.bin / "fliperos-lab")}

    def screen(self, answer):
        return self.env.run("""
            source %s/lib/ui.sh
            source %s/screens/progress.sh
            source %s/screens/setup-menu.sh
            ui_msg() { echo "msg:$*"; }
            ui_yesno() { echo "yesno:$2"; return %d; }
            run_with_progress() { shift 2; "$@"; }
            net_online() { :; }
            screen_lab
        """ % (SETUP, SETUP, SETUP, 0 if answer else 1), self.lab_env)

    def test_turn_on_shows_the_address_and_turn_off(self):
        self.assertEqual(self.env.out("lab_enabled && echo on || echo off", self.lab_env).strip(), "off")
        r = self.screen(False)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.state.exists())
        self.assertIn("root terminal", r.stdout)
        r = self.screen(True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.state.exists())
        self.assertIn("msg:Lab mode Send this address to who is helping you:  "
                      "https://a-b.trycloudflare.com/lab?key=K", r.stdout)
        self.assertEqual(self.env.out("lab_enabled && echo on || echo off", self.lab_env).strip(), "on")
        # Ligado: a mesma entrada mostra o endereco e desliga.
        r = self.screen(True)
        self.assertIn("https://a-b.trycloudflare.com/lab?key=K", r.stdout)
        self.assertIn("msg:Lab mode Lab mode is off", r.stdout)
        self.assertFalse(self.state.exists())

    def test_system_menu_has_the_toggle(self):
        menu = (SETUP / "screens" / "setup-menu.sh").read_text()
        self.assertIn('"lab|Lab mode ($(lab_enabled && echo on || echo off))|', menu)
        self.assertIn("lab) screen_lab ;;", menu)


class FreeRomsTests(Base):
    """lib/freeroms.sh: Setup > Games > Downloader > Free games (config/fliperos-freeroms)."""

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


class FoldersTests(Base):
    """Setup > Games > Folders (lib/folders.sh): a custom folder de cada pasta de ~."""

    def setUp(self):
        super().setUp()
        self.home = self.env.dir / "home"
        self.disk = self.env.dir / "disk"
        for d in (self.home / "roms" / "mame", self.home / "bios", self.disk / "roms"):
            d.mkdir(parents=True)
        (self.home / "roms" / "mame" / "sf2.zip").write_text("mine")
        (self.disk / "roms" / "pacman.zip").write_text("theirs")
        self.vars = {"FOLDERS_HOME": str(self.home), "FOLDERS_SCRIPT": str(self.env.dir / "nothing")}

    def state(self, name="roms"):
        return self.env.out("folders_state %s" % name, self.vars).strip()

    def skeleton(self, path):
        (path / "mame").mkdir(parents=True)
        (path / "_info.txt").write_text("info\n")
        (path / "mame" / "_info.txt").write_text("info\n")

    def test_link_keeps_the_previous_folder(self):
        self.assertEqual(self.state(), "default")
        out = self.env.out('folders_link roms "%s"; echo "$FOLDERS_KEPT"' % (self.disk / "roms"), self.vars)
        self.assertEqual(out.strip(), str(self.home / "old-roms"))
        self.assertTrue((self.home / "roms").is_symlink())
        self.assertEqual(os.readlink(self.home / "roms"), str(self.disk / "roms"))
        self.assertEqual((self.home / "old-roms" / "mame" / "sf2.zip").read_text(), "mine")
        self.assertEqual(self.state(), "custom")
        self.assertEqual(self.env.out("folders_target roms", self.vars).strip(), str(self.disk / "roms"))

    def test_unlink_brings_the_previous_folder_back(self):
        self.env.out('folders_link roms "%s"' % (self.disk / "roms"), self.vars)
        self.env.out("folders_unlink roms", self.vars)
        self.assertFalse((self.home / "roms").is_symlink())
        self.assertEqual((self.home / "roms" / "mame" / "sf2.zip").read_text(), "mine")
        self.assertFalse((self.home / "old-roms").exists())
        # Nada sai da custom folder.
        self.assertEqual((self.disk / "roms" / "pacman.zip").read_text(), "theirs")

    def test_unlink_creates_the_folder_when_the_previous_one_is_gone(self):
        self.env.out('folders_link roms "%s"' % (self.disk / "roms"), self.vars)
        shutil.rmtree(self.home / "old-roms")
        r = self.env.run("folders_unlink roms", self.vars)
        self.assertEqual(r.returncode, 2)
        self.assertTrue((self.home / "roms").is_dir())
        self.assertFalse((self.home / "roms").is_symlink())
        self.assertEqual(list((self.home / "roms").iterdir()), [])

    def test_changing_the_custom_folder_only_swaps_the_link(self):
        other = self.env.dir / "other"
        other.mkdir()
        self.env.out('folders_link roms "%s"' % (self.disk / "roms"), self.vars)
        out = self.env.out('folders_link roms "%s"; echo "kept=$FOLDERS_KEPT"' % other, self.vars)
        self.assertEqual(out.strip(), "kept=")
        self.assertEqual(os.readlink(self.home / "roms"), str(other))
        self.assertEqual((self.home / "old-roms" / "mame" / "sf2.zip").read_text(), "mine")
        self.assertFalse((self.home / "old2-roms").exists())

    def test_a_link_made_by_hand_is_a_custom_folder(self):
        shutil.move(str(self.home / "roms"), str(self.home / "old-roms"))
        (self.home / "roms").symlink_to(self.disk / "roms")
        self.assertEqual(self.state(), "custom")
        # O disco desligado: o link fica, sem a pasta.
        shutil.rmtree(self.disk)
        self.assertEqual(self.state(), "offline")
        self.env.out("folders_unlink roms", self.vars)
        self.assertEqual((self.home / "roms" / "mame" / "sf2.zip").read_text(), "mine")

    def test_check_restores_after_a_link_deleted_by_hand(self):
        self.env.out('folders_link roms "%s"' % (self.disk / "roms"), self.vars)
        # Apagado a mao, sem nada no lugar.
        (self.home / "roms").unlink()
        self.assertEqual(self.state(), "missing")
        self.assertEqual(self.env.out("folders_check", self.vars).split(), ["roms"])
        self.assertEqual((self.home / "roms" / "mame" / "sf2.zip").read_text(), "mine")
        # Apagado a mao, e o login criou a pasta nova e vazia no lugar.
        self.env.out('folders_link roms "%s"' % (self.disk / "roms"), self.vars)
        (self.home / "roms").unlink()
        self.skeleton(self.home / "roms")
        self.assertEqual(self.env.out("folders_check", self.vars).split(), ["roms"])
        self.assertEqual((self.home / "roms" / "mame" / "sf2.zip").read_text(), "mine")
        self.assertFalse((self.home / "old-roms").exists())
        self.assertEqual(self.env.out("folders_check", self.vars).split(), [])

    def test_check_never_drops_a_folder_with_files(self):
        (self.home / "old-roms" / "mame").mkdir(parents=True)
        (self.home / "old-roms" / "mame" / "old.zip").write_text("old")
        self.assertEqual(self.env.out("folders_check", self.vars).split(), [])
        self.assertEqual((self.home / "roms" / "mame" / "sf2.zip").read_text(), "mine")
        # Ao ganhar uma custom folder, a de agora fica com outro nome.
        out = self.env.out('folders_link roms "%s"; echo "$FOLDERS_KEPT"' % (self.disk / "roms"), self.vars)
        self.assertEqual(out.strip(), str(self.home / "old2-roms"))
        self.assertEqual((self.home / "old-roms" / "mame" / "old.zip").read_text(), "old")
        self.assertEqual((self.home / "old2-roms" / "mame" / "sf2.zip").read_text(), "mine")
        # A guardada com outro nome nunca volta sozinha como uma pasta nova.
        (self.home / "roms").unlink()
        shutil.rmtree(self.home / "old-roms")
        self.assertEqual(self.env.out("folders_check", self.vars).split(), [])
        self.assertFalse((self.home / "roms-2").exists())

    def test_link_drops_an_empty_folder_when_the_previous_one_is_kept(self):
        shutil.move(str(self.home / "roms"), str(self.home / "old-roms"))
        self.skeleton(self.home / "roms")
        # Um tema do splash copiado da imagem tambem e do FliperOS.
        theme = self.home / "roms" / "fliperos"
        theme.mkdir()
        (theme / ".bundled").write_text("1 2\n")
        (theme / "logo.png").write_text("png")
        out = self.env.out('folders_link roms "%s"; echo "kept=$FOLDERS_KEPT"' % (self.disk / "roms"), self.vars)
        self.assertEqual(out.strip(), "kept=")
        self.assertEqual((self.home / "old-roms" / "mame" / "sf2.zip").read_text(), "mine")
        self.assertFalse((self.home / "old2-roms").exists())

    def test_refused_folders(self):
        (self.home / "roms" / "inside").mkdir()
        for target, text in ((self.home / "roms", "itself"), (self.home / "roms" / "inside", "itself"),
                             (self.home, "inside that folder"), (self.env.dir / "nothere", "not a folder"),
                             (self.home / "roms" / "mame" / "sf2.zip", "not a folder")):
            r = self.env.run('folders_link roms "%s" || echo "$FOLDERS_ERROR"' % target, self.vars)
            self.assertIn(text, r.stdout, target)
        self.assertEqual(self.state(), "default")
        self.assertFalse((self.home / "old-roms").exists())
        self.assertEqual(self.env.run('folders_link config "%s"' % self.disk, self.vars).returncode, 1)
        self.assertIn("no custom folder", self.env.run('folders_unlink bios || echo "$FOLDERS_ERROR"', self.vars).stdout)

    def test_the_folders_are_created_in_the_custom_folder(self):
        script = self.env.dir / "populate"
        script.write_text('#!/bin/bash\necho "$HOME" >> "%s"\n' % (self.env.dir / "populate.calls"))
        script.chmod(0o755)
        env = dict(self.vars, FOLDERS_SCRIPT=str(script), FLIPEROS_USER="nobody-here")
        self.env.out('folders_link roms "%s"; folders_unlink roms' % (self.disk / "roms"), env)
        self.assertEqual((self.env.dir / "populate.calls").read_text().split(), [str(self.home)] * 2)

    # -- As pastas de dentro: um emulador, um core, um tipo de arte.

    def inner(self):
        """~/roms/retroarch/mame2010 e ~/media/snap com arquivos, e um disco com uma pasta para cada uma."""
        for d in (self.home / "roms" / "retroarch" / "mame2010", self.home / "media" / "snap" / "mame",
                  self.disk / "mame2010", self.disk / "snaps", self.disk / "model2"):
            d.mkdir(parents=True)
        (self.home / "roms" / "retroarch" / "mame2010" / "tekken3.zip").write_text("mine")
        (self.home / "media" / "snap" / "mame" / "sf2.png").write_text("mine")

    def test_inner_folder_gets_its_own_custom_folder(self):
        self.inner()
        out = self.env.out('folders_link roms/retroarch/mame2010 "%s"; echo "$FOLDERS_KEPT"' % (self.disk / "mame2010"),
                           self.vars)
        core = self.home / "roms" / "retroarch" / "mame2010"
        self.assertEqual(out.strip(), str(self.home / "roms" / "retroarch" / "old-mame2010"))
        self.assertEqual(os.readlink(core), str(self.disk / "mame2010"))
        self.assertEqual(self.state("roms/retroarch/mame2010"), "custom")
        # As outras pastas e a raiz ficam como estavam.
        self.assertEqual(self.state("roms"), "default")
        self.assertEqual((self.home / "roms" / "mame" / "sf2.zip").read_text(), "mine")
        self.env.out('folders_link media/snap "%s"' % (self.disk / "snaps"), self.vars)
        self.assertEqual((self.home / "media" / "old-snap" / "mame" / "sf2.png").read_text(), "mine")
        self.assertEqual(self.env.out("folders_customs", self.vars).split(),
                         ["roms/retroarch/mame2010", "media/snap"])
        self.assertEqual(self.env.out("folders_customs roms", self.vars).split(), ["roms/retroarch/mame2010"])
        self.env.out("folders_unlink roms/retroarch/mame2010", self.vars)
        self.assertEqual((core / "tekken3.zip").read_text(), "mine")
        self.assertFalse(core.is_symlink())
        self.assertFalse((self.home / "roms" / "retroarch" / "old-mame2010").exists())

    def test_children_are_the_folders_of_the_structure(self):
        self.inner()
        (self.home / "roms" / "old-mame").mkdir()
        (self.home / "roms" / "old2-mame").mkdir()
        (self.home / "roms" / ".hidden").mkdir()
        (self.home / "roms" / "mame" / "kinst").mkdir()
        (self.home / "roms" / "gone").symlink_to(self.env.dir / "unplugged")
        self.assertEqual(self.env.out("folders_children roms", self.vars).split(),
                         ["roms/gone", "roms/mame", "roms/retroarch"])
        self.assertEqual(self.state("roms/gone"), "offline")
        self.assertEqual(self.env.out("folders_children roms/retroarch", self.vars).split(), ["roms/retroarch/mame2010"])
        self.assertEqual(self.env.out("folders_children media", self.vars).split(), ["media/snap"])
        # A arte tem as pastas de ~/roms, com a dos cores do RetroArch.
        (self.home / "media" / "snap" / "retroarch" / "mame2010").mkdir(parents=True)
        (self.home / "media" / "snap" / "retroarch" / "old-mame2010").mkdir()
        self.assertEqual(self.env.out("folders_children media/snap", self.vars).split(),
                         ["media/snap/mame", "media/snap/retroarch"])
        self.assertEqual(self.env.out("folders_children media/snap/retroarch", self.vars).split(),
                         ["media/snap/retroarch/mame2010"])
        # A pasta de um emulador e a dos temas nao tem pastas de dentro para a lista.
        for rel in ("roms/mame", "media/snap/mame", "media/snap/retroarch/mame2010", "splashscreen"):
            self.assertEqual(self.env.out("folders_children %s" % rel, self.vars).split(), [], rel)
        for rel in ("roms/old-mame", "roms/old2-mame", "roms/.hidden", "roms/../bios", "roms/a/b/c", "/roms", "roms/",
                    "games/mame", "", "media/snap/mame/a/b", "media/snap/retroarch/old-mame2010",
                    "media/snap/retroarch/mame2010/a"):
            self.assertEqual(self.env.run('folders_known "%s"' % rel, self.vars).returncode, 1, rel)
        for rel in ("roms", "roms/mame", "roms/retroarch/mame2010", "media/snap/mame", "media/snap/retroarch",
                    "media/snap/retroarch/mame2010"):
            self.assertEqual(self.env.run('folders_known "%s"' % rel, self.vars).returncode, 0, rel)

    def test_check_restores_an_inner_folder(self):
        self.inner()
        self.env.out('folders_link roms/retroarch/mame2010 "%s"; folders_link media/snap "%s"'
                     % (self.disk / "mame2010", self.disk / "snaps"), self.vars)
        (self.home / "roms" / "retroarch" / "mame2010").unlink()
        (self.home / "media" / "snap").unlink()
        self.skeleton(self.home / "media" / "snap")
        self.assertEqual(sorted(self.env.out("folders_check", self.vars).split()),
                         ["media/snap", "roms/retroarch/mame2010"])
        self.assertEqual((self.home / "roms" / "retroarch" / "mame2010" / "tekken3.zip").read_text(), "mine")
        self.assertEqual((self.home / "media" / "snap" / "mame" / "sf2.png").read_text(), "mine")

    def test_inner_folder_of_an_unplugged_root_is_refused(self):
        self.inner()
        shutil.move(str(self.home / "roms"), str(self.home / "old-roms"))
        (self.home / "roms").symlink_to(self.env.dir / "unplugged")
        r = self.env.run('folders_link roms/mame "%s" || echo "$FOLDERS_ERROR"' % (self.disk / "roms"), self.vars)
        self.assertIn("~/roms is not there", r.stdout)

    def test_kept_folders_are_not_systems(self):
        self.inner()
        (self.disk / "mame").mkdir()
        self.env.out('folders_link roms/mame "%s"; folders_link roms/retroarch/mame2010 "%s"'
                     % (self.disk / "mame", self.disk / "mame2010"), self.vars)
        (self.disk / "mame" / "pacman.zip").write_text("theirs")
        info = self.env.dir / "info"
        info.mkdir()
        (info / "mame2010_libretro.info").write_text('systemid = "mame"\n')
        (self.disk / "mame2010" / "sfex.zip").write_text("theirs")
        out = self.env.out("scraper_detect", dict(self.vars, ROMS_DIR=str(self.home / "roms"), RA_INFO_DIR=str(info)))
        self.assertEqual([line.split("|")[0] for line in out.splitlines()], ["mame", "retroarch/mame2010"])
        self.assertEqual(out.splitlines()[0].split("|")[3], "1")

    def test_browser_opens_where_the_disks_are_mounted(self):
        mounts = self.env.dir / "media" / "fliperos"
        env = dict(self.vars, FOLDERS_MOUNTS=str(mounts))
        # Nenhum disco montado ainda: a pasta acima.
        (self.env.dir / "media").mkdir()
        self.assertEqual(self.env.out("folders_browse_start", env).strip(), str(self.env.dir / "media"))
        mounts.mkdir()
        self.assertEqual(self.env.out("folders_browse_start", env).strip(), str(mounts))
        self.assertIn('"$(folders_browse_start)" dir', (SETUP / "screens" / "folders.sh").read_text())

    def test_shares_follow_the_links(self):
        smb = (ROOT / "config/smb.conf").read_text()
        for name in ("roms", "bios", "media", "splashscreen"):
            share = smb.split("[%s]\n" % name)[1].split("\n[")[0]
            self.assertIn("wide links = yes", share, name)

    def login(self):
        env = dict(os.environ, HOME=str(self.home), FLIPEROS_SPLASH_BUNDLED=str(self.env.dir / "nobundle"),
                   FLIPEROS_CORE_INFO=str(self.env.dir / "noinfo"))
        subprocess.run(["bash", str(ROOT / "config/fliperos-roms")], env=env, check=True, timeout=60)

    def test_login_fills_the_custom_folder(self):
        self.env.out('folders_link roms "%s"' % (self.disk / "roms"), self.vars)
        self.login()
        self.assertTrue((self.disk / "roms" / "mame" / "_info.txt").is_file())
        self.assertTrue((self.home / "roms").is_symlink())

    def test_login_with_the_disk_off_keeps_the_link_and_makes_the_rest(self):
        self.env.out('folders_link roms "%s"' % (self.disk / "roms"), self.vars)
        shutil.rmtree(self.disk)
        self.login()
        self.assertTrue((self.home / "roms").is_symlink())
        self.assertTrue((self.home / "media" / "snap" / "_info.txt").is_file())
        self.assertTrue((self.home / "bios" / "dc").is_dir())

    def test_login_restores_after_a_link_deleted_by_hand(self):
        self.env.out('folders_link roms "%s"' % (self.disk / "roms"), self.vars)
        (self.home / "roms").unlink()
        self.login()
        self.assertEqual((self.home / "roms" / "mame" / "sf2.zip").read_text(), "mine")
        self.assertFalse((self.home / "old-roms").exists())

    def test_login_with_inner_custom_folders(self):
        self.inner()
        self.env.out('folders_link roms/retroarch "%s"; folders_link roms/mame "%s"; folders_link media/snap "%s"'
                     % (self.disk / "mame2010", self.disk / "roms", self.disk / "snaps"), self.vars)
        # O disco de um deles desligado, o link de outro apagado a mao.
        shutil.rmtree(self.disk / "mame2010")
        (self.home / "roms" / "mame").unlink()
        self.login()
        self.assertTrue((self.home / "roms" / "retroarch").is_symlink())
        self.assertEqual((self.home / "roms" / "mame" / "sf2.zip").read_text(), "mine")
        self.assertFalse((self.home / "roms" / "old-mame").exists())
        self.assertTrue((self.disk / "snaps" / "_info.txt").is_file())
        self.assertTrue((self.home / "roms" / "ps2" / "_info.txt").is_file())
        self.assertTrue((self.home / "bios" / "dc").is_dir())
        self.assertTrue((self.home / "roms" / "model2" / "_info.txt").is_file())

    def test_in_the_setup_menu(self):
        menu = (SETUP / "screens" / "setup-menu.sh").read_text()
        self.assertIn('"folders|Folders|', menu)
        self.assertIn("folders) screen_folders ;;", menu)
        main = (SETUP / "fliperos-setup").read_text()
        for part in ("lib", "screens"):
            self.assertIn('source "$SETUP_DIR/%s/folders.sh"' % part, main)
        # As pastas da lista sao as que o fliperos-roms cria e a rede mostra.
        names = self.env.out("folders_list", self.vars).split()
        self.assertEqual(names, ["roms", "bios", "media", "splashscreen"])
        smb = (ROOT / "config/smb.conf").read_text()
        for name in names:
            self.assertIn("path = /home/fliperos/%s\n" % name, smb)


class ProgressScreenTests(Base):
    """screens/progress.sh: a tela da barra cabe no console, sem rolar."""

    def layout(self, rows, target, topbar=2):
        out = self.env.out("""
            source %s/lib/ui.sh
            source %s/screens/progress.sh
            UI_TOPBAR_ROWS=%d
            _progress_layout %d %d
            echo "$PL_TOP $PL_FOOT $PL_GAP_MSGS $PL_GAP_TITLE $PL_GAP_TARGET $PL_GAP_BAR $PL_MSGS"
        """ % (SETUP, SETUP, topbar, rows, target))
        top, foot, gmsgs, gtitle, gtarget, gbar, msgs = (int(n) for n in out.split())
        used = topbar + top + 6 + gtitle + target + gtarget + gbar + gmsgs + msgs + foot
        return used, (top, foot, gmsgs, gtitle, gtarget, gbar, msgs)

    def test_full_layout_on_a_tall_console(self):
        # 640x480i e 512x384: tudo.
        for rows in (30, 24):
            self.assertEqual(self.layout(rows, 1)[1], (1, 1, 1, 1, 1, 1, 3), rows)
        self.assertEqual(self.layout(30, 0)[1], (1, 1, 1, 1, 0, 1, 3))

    def test_never_taller_than_the_console(self):
        # 640x240 com a fonte 8x16: 15 linhas. O Downloader (sem alvo) so perde
        # a linha em branco de cima; a instalacao (com alvo), tres delas.
        self.assertEqual(self.layout(15, 0), (15, (0, 1, 1, 1, 0, 1, 3)))
        self.assertEqual(self.layout(15, 1), (15, (0, 0, 0, 1, 1, 1, 3)))
        for rows in range(9, 31):
            for target in (0, 1):
                for topbar in (2, 3):
                    used, parts = self.layout(rows, target, topbar)
                    if rows >= topbar + 6 + target:
                        self.assertLessEqual(used, rows, (rows, target, topbar, parts))
        # As mensagens so saem depois de todas as linhas em branco.
        self.assertEqual(self.layout(10, 0)[1], (0, 0, 0, 0, 0, 0, 2))

    def test_the_last_line_has_no_line_break(self):
        screen = (SETUP / "screens" / "progress.sh").read_text()
        self.assertIn("""printf '  %s\\e[K' "$(ui_c "$C_COMMENT" "${footer:0:UI_COLS-3}")\"""", screen)


class WhatsNewTests(Base):
    """lib/whatsnew.sh e screens/whatsnew.sh: o changelog da versao e os
    updates aplicados, uma vez no menu e de novo em Setup > System."""
    CHANGELOG = ("# Changelog\n\nIntro text.\n\n"
                 "## 0.11\n\n**Big thing** in `code`, see [the wiki](https://x/y).\n\n- item eleven\n\n"
                 "## 0.10\n\n- item ten\n\n"
                 "## 0.9\n\n- item nine\n")
    LOG = ("2026-10-01 10:00:00 update 16 (FliperOS 0.9.1: data files): 3 files replaced, 0 with local changes, backup /b\n"
           "2026-10-01 10:00:09 update 16 applied\n"
           "2026-10-02 10:00:00 update 17 (Menu fix (the big one)): 1 files replaced, 0 with local changes, backup /b\n"
           "2026-10-02 10:00:05 update 17 applied\n"
           "2026-10-03 10:00:00 update 18 (Broken one): 2 files replaced, 0 with local changes, backup /b\n"
           "2026-10-03 10:00:01 error: update 18 stopped (exit 1, see log); its backup is in /b\n")

    def setUp(self):
        super().setUp()
        (self.env.dir / "CHANGELOG.md").write_text(self.CHANGELOG)
        (self.env.dir / "update.log").write_text(self.LOG)
        (self.env.etc / "patch-level").write_text("17\n")
        (self.env.etc / "installed").write_text("")
        self.env.cmdline.write_text("quiet splash\n")
        self.vars = {"WHATSNEW_CHANGELOG": str(self.env.dir / "CHANGELOG.md"),
                     "WHATSNEW_UPDATE_LOG": str(self.env.dir / "update.log"),
                     "WHATSNEW_NOTES": str(self.env.dir / "notes"),
                     "FLIPEROS_SETUP_VERSION": "0.11"}

    CHECK = """
        source %s/screens/whatsnew.sh
        ui_pager() { echo "PAGER:$1"; cat "$2"; }
        screen_whatsnew_check
    """ % SETUP

    def conf(self, text):
        (self.env.etc / "fliperos.conf").write_text(text)

    def test_updates_from_the_log_newest_first_only_the_applied(self):
        self.assertEqual(self.env.out("whatsnew_updates", self.vars),
                         "17\tMenu fix (the big one)\n16\tFliperOS 0.9.1: data files\n")
        self.assertEqual(self.env.out("whatsnew_updates 16", self.vars), "17\tMenu fix (the big one)\n")

    def test_first_time_shows_only_this_version_then_nothing(self):
        out = self.env.out(self.CHECK, self.vars)
        self.assertIn("PAGER:What's new in FliperOS", out)
        self.assertIn("This is FliperOS 0.11, update 17.", out)
        # Markdown em texto: sem **, ` e o endereco do link.
        self.assertIn("FliperOS 0.11\n\nBig thing in code, see the wiki.\n\n- item eleven", out)
        self.assertNotIn("item ten", out)
        self.assertNotIn("Updates installed", out)
        conf = (self.env.etc / "fliperos.conf").read_text()
        self.assertIn("whatsnew_version=0.11\n", conf)
        self.assertIn("whatsnew_level=17\n", conf)
        self.assertNotIn("PAGER", self.env.out(self.CHECK, self.vars))

    def test_new_update_shows_its_title_without_the_changelog_again(self):
        self.conf("whatsnew_version=0.11\nwhatsnew_level=16\n")
        out = self.env.out(self.CHECK, self.vars)
        self.assertIn("Updates installed:\n- 17. Menu fix (the big one)\n", out)
        self.assertNotIn("16.", out)
        self.assertNotIn("item eleven", out)

    def test_update_notes_under_its_title(self):
        # O que o update mudou (updates/notes/0017.md), debaixo do titulo.
        (self.env.dir / "notes").mkdir()
        (self.env.dir / "notes" / "0017.md").write_text("- **Menu:** opens `faster`.\n\n- [Wiki](x) fixed.\n")
        self.conf("whatsnew_version=0.11\nwhatsnew_level=16\n")
        out = self.env.out(self.CHECK, self.vars)
        self.assertIn("- 17. Menu fix (the big one)\n  - Menu: opens faster.\n\n  - Wiki fixed.\n", out)

    def test_new_version_shows_every_version_since_the_last_seen(self):
        self.conf("whatsnew_version=0.9\nwhatsnew_level=17\n")
        out = self.env.out(self.CHECK, self.vars)
        self.assertLess(out.index("item eleven"), out.index("item ten"))
        self.assertNotIn("item nine", out)
        self.assertNotIn("Intro text", out)

    def test_not_on_the_live_media(self):
        self.env.cmdline.write_text("boot=live quiet splash\n")
        self.assertNotIn("PAGER", self.env.out(self.CHECK, self.vars))
        self.assertFalse((self.env.etc / "fliperos.conf").exists())

    def test_menu_entry_shows_everything(self):
        self.conf("whatsnew_version=0.11\nwhatsnew_level=17\n")
        out = self.env.out("""
            source %s/screens/whatsnew.sh
            ui_pager() { cat "$2"; }
            screen_whatsnew
        """ % SETUP, self.vars)
        self.assertIn("- 17. Menu fix (the big one)\n- 16. FliperOS 0.9.1: data files\n", out)
        for item in ("item eleven", "item ten", "item nine"):
            self.assertIn(item, out)
        out = self.env.out("""
            source %s/screens/whatsnew.sh
            ui_msg() { echo "MSG:$*"; }
            screen_whatsnew
        """ % SETUP, dict(self.vars, WHATSNEW_CHANGELOG="/nonexistent", WHATSNEW_UPDATE_LOG="/nonexistent"))
        self.assertIn("The changelog is not on this system.", out)

    def test_wired_into_the_menus(self):
        main = (SETUP / "screens/main-menu.sh").read_text()
        self.assertIn("screen_whatsnew_check", main.split("screen_main_menu() {")[1].split("while true")[0])
        menu = (SETUP / "screens/setup-menu.sh").read_text()
        self.assertIn('"whatsnew|What\'s new|', menu)
        self.assertIn("whatsnew) screen_whatsnew ;;", menu)
        setup = (SETUP / "fliperos-setup").read_text()
        self.assertIn('source "$SETUP_DIR/lib/whatsnew.sh"', setup)
        self.assertIn('source "$SETUP_DIR/screens/whatsnew.sh"', setup)


class AmdDriverTests(Base):
    """radeon ou amdgpu nas placas que aceitam os dois (Video Setup > Video driver)."""
    RADEON = "radeon.si_support=1 radeon.cik_support=1 amdgpu.si_support=0 amdgpu.cik_support=0"
    AMDGPU = "radeon.si_support=0 radeon.cik_support=0 amdgpu.si_support=1 amdgpu.cik_support=1 amdgpu.dc=0"

    def setUp(self):
        super().setUp()
        # O modprobe -R de verdade: a tabela de PCI IDs dos modulos. 6798 (HD
        # 7970, SI) esta nos dois; 68f9 (HD 5450) so no radeon; 67df (RX 480)
        # so no amdgpu.
        self.env.stub("modprobe", '[ "$1" = -R ] || exit 1\n'
                                  'case $2 in\n'
                                  '  *d00006798*) printf "radeon\\namdgpu\\n" ;;\n'
                                  '  *d000068F9*) echo radeon ;;\n'
                                  '  *d000067DF*) echo amdgpu ;;\n'
                                  '  *) exit 1 ;;\n'
                                  'esac')

    def gpu(self, card, driver, device):
        self.env.card(card, driver)
        (self.env.drm / card / "device" / "modalias").write_text(
            "pci:v00001002d0000%ssv00001002sd00003001bc03sc00i00\n" % device)

    def test_only_cards_both_drivers_take(self):
        self.gpu("card0", "radeon", "68F9")
        self.gpu("card1", "radeon", "6798")
        self.gpu("card2", "amdgpu", "67DF")
        self.env.connector("card1-VGA-1")
        self.assertEqual(self.env.out("drm_cards").split(), ["card0", "card1", "card2"])
        self.assertEqual(self.env.out("drm_dual_amd_cards").split(), ["card1"])

    def test_no_amd_card_no_choice(self):
        self.env.card("card0", "i915")
        (self.env.drm / "card0" / "device" / "modalias").write_text("pci:v00008086d00005912\n")
        self.assertEqual(self.env.out("drm_dual_amd_cards").strip(), "")

    def test_line_unchanged_without_a_choice(self):
        line = "quiet splash consoleblank=0 " + self.RADEON
        self.assertEqual(self.env.out("amd_driver_cmdline '%s'" % line).strip(), line)
        self.assertEqual(self.env.out("amd_driver").strip(), "radeon")

    def test_amdgpu_and_back(self):
        line = "quiet splash consoleblank=0 " + self.RADEON
        out = self.env.out("conf_set amd_driver amdgpu; amd_driver_cmdline '%s'" % line).strip()
        self.assertEqual(out, "quiet splash consoleblank=0 " + self.AMDGPU)
        out = self.env.out("conf_set amd_driver radeon; amd_driver_cmdline '%s'" % out).strip()
        self.assertEqual(out, "quiet splash consoleblank=0 " + self.RADEON)

    def test_install_line_takes_the_choice(self):
        (self.env.etc / "fliperos.conf").write_text("amd_driver=amdgpu\n")
        out = self.env.out("boot_install_cmdline").strip().split()
        for word in self.AMDGPU.split():
            self.assertIn(word, out)
        self.assertNotIn("radeon.si_support=1", out)
        self.assertEqual(len([w for w in out if w.startswith("amdgpu.si_support")]), 1)

    def test_modprobe_keeps_only_the_other_options(self):
        conf = self.env.dir / "modprobe" / "fliperos.conf"
        conf.parent.mkdir()
        conf.write_text("options radeon si_support=1 cik_support=1 dpm=1\n"
                        "options amdgpu si_support=0 cik_support=0\n"
                        "options snd_hda_intel power_save=0 power_save_controller=N\n")
        self.env.out("amd_driver_apply amdgpu", {"AMD_MODPROBE_CONF": str(conf)})
        self.assertEqual(conf.read_text(), "options radeon dpm=1\n"
                                           "options snd_hda_intel power_save=0 power_save_controller=N\n")
        self.assertIn("amd_driver=amdgpu", (self.env.etc / "fliperos.conf").read_text())

    def test_new_images_leave_the_choice_to_the_line(self):
        rootfs = (ROOT / "fliperos-rootfs.sh").read_text()
        block = rootfs.split('cat > "$root/etc/modprobe.d/fliperos.conf"')[1].split("EOF")[1]
        self.assertNotIn("si_support", block)
        self.assertIn("options radeon dpm=1", block)

    def test_boot_menu_offers_radeon_back(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("limine_update", ROOT / "fliperos-limine-update.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        text = mod.render(["6.18.54-15khz"], "UUID=abc", "quiet splash " + self.AMDGPU, "3")
        entry = text.split("/FliperOS - radeon driver\n")[1]
        cmdline = re.search(r"cmdline: (.*)", entry).group(1).split()
        for word in self.RADEON.split():
            self.assertIn(word, cmdline)
        self.assertNotIn("amdgpu.dc=0", cmdline)
        self.assertNotIn("amdgpu.si_support=1", cmdline)
        plain = mod.render(["6.18.54-15khz"], "UUID=abc", "quiet splash " + self.RADEON, "3")
        self.assertNotIn("radeon driver", plain)

    def test_mismatch_only_on_a_card_with_the_choice(self):
        self.gpu("card0", "amdgpu", "67DF")
        self.assertEqual(self.env.run("amd_driver_mismatch").returncode, 1)
        self.gpu("card1", "radeon", "6798")
        self.assertEqual(self.env.run("amd_driver_mismatch").returncode, 1)
        self.gpu("card2", "amdgpu", "6798")
        self.assertEqual(self.env.out("amd_driver_mismatch").strip(), "card2|amdgpu|radeon")

    CHECK = """
        source %s/screens/amd-driver.sh
        ui_yesno() { echo "ASKED: $2"; return 1; }
        screen_amd_driver_check
        screen_amd_driver_check
    """ % SETUP

    def check(self):
        (self.env.etc / "installed").write_text("")
        self.env.cmdline.write_text("quiet splash\n")
        return self.env.out(self.CHECK)

    def test_popup_once_when_the_driver_is_not_the_recommended(self):
        self.gpu("card0", "amdgpu", "6798")
        out = self.check()
        self.assertEqual(out.count("ASKED:"), 1)
        self.assertIn("running on the amdgpu driver. radeon is recommended", out)
        self.assertIn("amd_driver_checked=1", (self.env.etc / "fliperos.conf").read_text())
        self.assertEqual(self.env.out(self.CHECK).count("ASKED:"), 0)

    def test_no_popup_on_the_recommended_driver(self):
        self.gpu("card0", "radeon", "6798")
        self.assertNotIn("ASKED:", self.check())
        self.assertIn("amd_driver_checked=1", (self.env.etc / "fliperos.conf").read_text())

    def test_no_popup_when_amdgpu_was_chosen(self):
        # A pessoa escolheu o amdgpu no Setup ou na instalacao.
        (self.env.etc / "fliperos.conf").write_text("amd_driver=amdgpu\n")
        self.gpu("card0", "amdgpu", "6798")
        self.assertNotIn("ASKED:", self.check())

    def test_no_popup_on_the_install_media(self):
        self.gpu("card0", "amdgpu", "6798")
        self.env.cmdline.write_text("boot=live quiet\n")
        self.assertNotIn("ASKED:", self.env.out(self.CHECK))

    # ── Teste da troca (confirmar a imagem no boot seguinte) ──────────
    TRIAL = """
        source %s/screens/amd-driver.sh
        boot_apply() { echo "BOOT_APPLY initramfs=${BOOT_INITRAMFS:-0}"; }
        ui_info() { :; }
        ui_msg() { echo "MSG: $2"; }
        screen_reboot_now() { echo REBOOT_NOW; }
        screen_power_now() { systemctl "$1"; }
    """ % SETUP

    def installed(self):
        (self.env.etc / "installed").write_text("")
        self.env.cmdline.write_text("quiet splash\n")
        self.calls = self.env.dir / "calls"
        self.calls.write_text("")
        self.env.stub("systemctl", 'echo "systemctl $*" >> "%s"' % self.calls)

    def rebooted(self):
        return "systemctl reboot" in self.calls.read_text()

    def conf(self):
        return dict(l.split("=", 1) for l in (self.env.etc / "fliperos.conf").read_text().split("\n") if "=" in l)

    def test_switch_puts_the_new_driver_on_trial(self):
        self.installed()
        self.gpu("card0", "radeon", "6798")
        out = self.env.out(self.TRIAL + 'ui_yesno() { echo "ASKED: $2"; return 1; }\nscreen_amd_driver_apply amdgpu')
        conf = self.conf()
        self.assertEqual((conf["amd_driver"], conf["amd_driver_trial"], conf["amd_driver_previous"]),
                         ("amdgpu", "amdgpu", "radeon"))
        self.assertIn("with no answer in 15 s, FliperOS goes back to radeon", out)
        # O modprobe.d ja limpo: so o menu do Limine, sem refazer o initramfs.
        self.assertIn("BOOT_APPLY initramfs=0", out)

    def test_choosing_the_running_driver_ends_the_trial(self):
        self.installed()
        self.gpu("card0", "radeon", "6798")
        (self.env.etc / "fliperos.conf").write_text("amd_driver=amdgpu\namd_driver_trial=amdgpu\namd_driver_previous=radeon\n")
        self.env.out(self.TRIAL + "ui_yesno() { return 1; }\nscreen_amd_driver_apply radeon")
        conf = self.conf()
        self.assertEqual(conf["amd_driver"], "radeon")
        self.assertNotIn("amd_driver_trial", conf)

    def trial_on_amdgpu(self, boots=0, card=True):
        self.installed()
        if card:
            self.gpu("card0", "amdgpu", "6798")
        (self.env.etc / "fliperos.conf").write_text(
            "amd_driver=amdgpu\namd_driver_trial=amdgpu\namd_driver_previous=radeon\namd_driver_trial_boots=%d\n" % boots)

    def test_enter_keeps_the_driver(self):
        self.trial_on_amdgpu()
        out = self.env.out(self.TRIAL + "ui_timed_confirm() { echo \"TIMED $2 s\"; return 0; }\nscreen_amd_driver_confirm")
        self.assertIn("TIMED 15 s", out)
        self.assertIn("MSG: The amdgpu driver stays.", out)
        self.assertFalse(self.rebooted())
        conf = self.conf()
        self.assertEqual(conf["amd_driver"], "amdgpu")
        self.assertNotIn("amd_driver_trial", conf)

    def test_no_answer_goes_back_and_reboots(self):
        self.trial_on_amdgpu()
        for rc in (124, 1):
            with self.subTest(rc=rc):
                self.trial_on_amdgpu(card=False)
                out = self.env.out(self.TRIAL + "ui_timed_confirm() { return %d; }\nscreen_amd_driver_confirm" % rc)
                self.assertIn("BOOT_APPLY", out)
                self.assertTrue(self.rebooted())
                conf = self.conf()
                self.assertEqual(conf["amd_driver"], "radeon")
                self.assertNotIn("amd_driver_trial", conf)
                self.assertNotIn("amd_driver_previous", conf)

    def test_watchdog_reverts_when_the_screen_never_answered(self):
        self.trial_on_amdgpu()
        out = self.env.out(self.TRIAL + "amd_driver_trial_boot")
        self.assertTrue(self.rebooted())
        self.assertEqual(self.conf()["amd_driver"], "radeon")

    def test_watchdog_leaves_a_confirmed_driver(self):
        self.trial_on_amdgpu()
        # A tela confirma enquanto a vigia espera.
        out = self.env.out(self.TRIAL + "sleep() { amd_driver_trial_confirm; }\namd_driver_trial_boot")
        self.assertFalse(self.rebooted())
        self.assertEqual(self.conf()["amd_driver"], "amdgpu")

    def test_a_trial_boot_that_hung_goes_back_at_once(self):
        self.trial_on_amdgpu(boots=1)
        out = self.env.out(self.TRIAL + "sleep() { echo SLEPT; }\namd_driver_trial_boot")
        self.assertTrue(self.rebooted())
        self.assertNotIn("SLEPT", out)
        self.assertEqual(self.conf()["amd_driver"], "radeon")

    def test_boot_menu_fallback_ends_the_trial_without_reboot(self):
        # A entrada "FliperOS - radeon driver" do Limine: a placa abriu no radeon.
        self.installed()
        self.gpu("card0", "radeon", "6798")
        (self.env.etc / "fliperos.conf").write_text("amd_driver=amdgpu\namd_driver_trial=amdgpu\namd_driver_previous=radeon\n")
        out = self.env.out(self.TRIAL + "amd_driver_trial_boot")
        self.assertFalse(self.rebooted())
        self.assertEqual(self.conf()["amd_driver"], "radeon")
        self.assertNotIn("amd_driver_trial", self.conf())

    def test_install_with_another_driver_starts_a_trial(self):
        self.gpu("card0", "radeon", "6798")
        target = self.env.dir / "target"
        conf = target / str(self.env.etc).lstrip("/") / "fliperos.conf"
        conf.parent.mkdir(parents=True)
        conf.write_text("amd_driver=amdgpu\n")
        self.env.out('amd_driver_modprobe_clean() { :; }\n'
                     'chosen=$(conf_get amd_driver "%s"); card=$(drm_dual_amd_cards | head -1); '
                     'amd_driver_trial_start "$chosen" "$(drm_card_driver "$card")" "%s"' % (conf, conf))
        text = conf.read_text()
        self.assertIn("amd_driver_trial=amdgpu", text)
        self.assertIn("amd_driver_previous=radeon", text)
        install = (SETUP / "lib/install.sh").read_text()
        self.assertIn('amd_driver_trial_start "$chosen" "$running" "$target$FLIPEROS_CONF"', install)

    def test_trial_is_wired_into_boot(self):
        tty1 = (ROOT / "config/fliperos-tty1").read_text()
        self.assertLess(tty1.index("fliperos-setup --driver-confirm"), tty1.index("fliperos-setup --first-boot"))
        main = (SETUP / "fliperos-setup").read_text()
        self.assertIn("--driver-trial-boot)\n      # A vigia da troca de driver (fliperos-driver-trial.service).\n      amd_driver_trial_boot", main)
        self.assertIn("--driver-confirm)\n      screen_amd_driver_confirm", main)
        unit = (ROOT / "config/fliperos-driver-trial.service").read_text()
        self.assertIn("ExecStart=/usr/local/bin/fliperos-setup --driver-trial-boot", unit)
        self.assertIn("Type=simple", unit)
        rootfs = (ROOT / "fliperos-rootfs.sh").read_text()
        self.assertIn("multi-user.target.wants/fliperos-driver-trial.service", rootfs)

    def test_screens_are_wired(self):
        menu = (SETUP / "screens/main-menu.sh").read_text()
        self.assertIn("screen_amd_driver_check", menu.split("screen_main_menu() {")[1].split("while true")[0])
        install = (SETUP / "screens/install-progress.sh").read_text()
        self.assertIn("screen_amd_driver install", install)
        # Em Video Setup, nao mais em System.
        video = (SETUP / "screens/video-setup.sh").read_text().split("screen_video_setup() {")[1]
        self.assertIn("driver) screen_video_driver ;;", video)
        self.assertIn('"${driver[@]}" \\\n      "${lowdot[@]}" \\\n      "return|', video)
        self.assertNotIn("screen_amd_driver", (SETUP / "screens/setup-menu.sh").read_text())
        # Na midia so grava a escolha, e a instalacao nao pergunta de novo.
        self.assertIn("is_live && mode=install", (SETUP / "screens/amd-driver.sh").read_text())
        self.assertIn("conf_get amd_driver > /dev/null 2>&1 || screen_amd_driver install",
                      (SETUP / "screens/install-progress.sh").read_text())
        self.assertIn('source "$SETUP_DIR/screens/amd-driver.sh"', (SETUP / "fliperos-setup").read_text())
        screen = (SETUP / "screens/amd-driver.sh").read_text()
        self.assertIn('"radeon|radeon (recommended)', screen)


class NvidiaDriverTests(Base):
    """nouveau ou o driver da NVIDIA (Video Setup > Video driver numa NVIDIA)."""
    NVIDIA = "modprobe.blacklist=nouveau nvidia-drm.modeset=1 nvidia-drm.fbdev=1"
    NOUVEAU = "modprobe.blacklist=nvidia,nvidia_drm,nvidia_modeset,nvidia_uvm"
    TRIAL = AmdDriverTests.TRIAL

    def gpu(self, card="card0", driver="nouveau", device="0x17c8"):
        self.env.card(card, driver)
        (self.env.drm / card / "device" / "vendor").write_text("0x10de\n")
        (self.env.drm / card / "device" / "device").write_text(device + "\n")

    def conf(self):
        return dict(l.split("=", 1) for l in (self.env.etc / "fliperos.conf").read_text().split("\n") if "=" in l)

    def installed(self, module=True):
        (self.env.etc / "installed").write_text("")
        self.env.cmdline.write_text("quiet splash\n")
        self.calls = self.env.dir / "calls"
        self.calls.write_text("")
        self.env.stub("systemctl", 'echo "systemctl $*" >> "%s"' % self.calls)
        self.env.stub("dkms", 'echo "dkms $*" >> "%s"' % self.calls)
        self.env.stub("modprobe", 'echo "modprobe $*" >> "%s"' % self.calls)
        self.env.stub("fliperos-nvidia", '[ "$1" = installed ] && exit %d; exit 0' % (0 if module else 1))
        return {"NVIDIA_CMD": str(self.env.bin / "fliperos-nvidia")}

    def test_the_card_and_its_pci_id(self):
        self.env.card("card0", "i915")
        (self.env.drm / "card0" / "device" / "vendor").write_text("0x8086\n")
        self.assertEqual(self.env.run("nvidia_card").returncode, 1)
        self.gpu("card1")
        self.assertEqual(self.env.out("nvidia_card").strip(), "card1")
        self.assertEqual(self.env.out("nvidia_device card1").strip(), "17c8")

    def test_line_unchanged_until_a_choice(self):
        line = "quiet splash consoleblank=0"
        self.assertEqual(self.env.out("nvidia_driver_cmdline '%s'" % line).strip(), line)
        self.assertEqual(self.env.out("nvidia_driver").strip(), "nouveau")

    def test_nvidia_and_back(self):
        line = "quiet splash consoleblank=0"
        out = self.env.out("conf_set nvidia_driver nvidia; nvidia_driver_cmdline '%s'" % line).strip()
        self.assertEqual(out, line + " " + self.NVIDIA)
        out = self.env.out("conf_set nvidia_driver nouveau; nvidia_driver_cmdline '%s'" % out).strip()
        self.assertEqual(out, line + " " + self.NOUVEAU)
        # Pelo boot_compose, uma vez so.
        (self.env.etc / "fliperos.conf").write_text("nvidia_driver=nvidia\n")
        words = self.env.out("boot_compose 'quiet splash %s'" % self.NOUVEAU).split()
        self.assertEqual([w for w in words if w.startswith("modprobe.blacklist")], ["modprobe.blacklist=nouveau"])
        self.assertIn("nvidia-drm.modeset=1", words)

    def test_switch_forgets_the_grid_and_goes_super(self):
        self.gpu()
        (self.env.etc / "fliperos.conf").write_text("low_dotclock_pci=0000:00:00.0\nlow_dotclock_min=7.7\n")
        out = self.env.out("video_low_dotclock_apply() { echo REDONE; }\nnvidia_driver_apply nvidia; echo $BOOT_INITRAMFS")
        self.assertEqual(out.split(), ["REDONE", "1"])
        self.assertEqual(self.conf(), {"nvidia_driver": "nvidia"})

    def test_no_grid_on_the_nvidia_driver(self):
        # O KMS do driver da NVIDIA so aceita os modos progressivos do EDID:
        # o Switchres nao cria os seus, e o grid nao testaria nada.
        self.gpu(driver="nvidia")
        self.assertNotEqual(self.env.run("drm_card_low_dotclock_testable card0").returncode, 0)
        self.assertNotEqual(self.env.run("drm_card_low_dotclock card0").returncode, 0)

    def test_xorg_uses_the_nvidia_driver(self):
        self.gpu(driver="nvidia")
        xorg = self.env.etc / "xorg.conf"
        self.env.out("conf_set monitor generic_15; conf_set boot_resolution 640x480iS; conf_set card card0; "
                     "conf_set connector DVI-I-1; conf_set nvidia_driver nvidia; xorg_generate")
        text = xorg.read_text()
        self.assertIn('Driver "nvidia"', text)
        self.assertIn("AllowNonEdidModes", text)
        self.assertIn("NoMaxPClkCheck", text)
        self.env.out("conf_set nvidia_driver nouveau; xorg_generate")
        self.assertIn('Driver "modesetting"', xorg.read_text())
        self.assertNotIn("ModeValidation", xorg.read_text())

    def test_switch_puts_nvidia_on_trial(self):
        env = self.installed()
        self.gpu()
        out = self.env.out(self.TRIAL + 'xorg_generate() { echo XORG; }\n'
                           'ui_yesno() { echo "ASKED: $2"; return 1; }\nscreen_amd_driver_apply nvidia', env)
        conf = self.conf()
        self.assertEqual((conf["nvidia_driver"], conf["amd_driver_trial"], conf["amd_driver_previous"]),
                         ("nvidia", "nvidia", "nouveau"))
        self.assertIn("XORG", out)
        self.assertIn("BOOT_APPLY initramfs=1", out)
        self.assertIn("FliperOS goes back to nouveau", out)

    def test_no_answer_goes_back_to_nouveau(self):
        env = self.installed()
        self.gpu(driver="nvidia")
        (self.env.etc / "fliperos.conf").write_text(
            "nvidia_driver=nvidia\namd_driver_trial=nvidia\namd_driver_previous=nouveau\n")
        out = self.env.out(self.TRIAL + "xorg_generate() { :; }\n"
                           "ui_timed_confirm() { return 124; }\nscreen_amd_driver_confirm", env)
        self.assertIn("BOOT_APPLY", out)
        self.assertIn("systemctl reboot", self.calls.read_text())
        self.assertEqual(self.conf()["nvidia_driver"], "nouveau")
        self.assertNotIn("amd_driver_trial", self.conf())

    CONFIRM = ('ui_timed_confirm() { return 0; }\nui_yesno() { echo "ASKED: $2"; return 0; }\n'
               "screen_low_dotclock_retest() { echo GRID; VIDEO_CHANGED=1; }\n"
               "screen_amd_driver_confirm")

    def test_confirm_on_nouveau_offers_the_grid(self):
        env = self.installed()
        self.gpu(driver="nouveau")
        (self.env.etc / "fliperos.conf").write_text(
            "nvidia_driver=nouveau\namd_driver_trial=nouveau\namd_driver_previous=nvidia\n")
        out = self.env.out(self.TRIAL + self.CONFIRM, env)
        self.assertIn("ASKED: Test now which native 15 kHz resolutions the nouveau driver shows", out)
        self.assertIn("GRID", out)
        self.assertIn("BOOT_APPLY", out)

    def test_confirm_on_the_nvidia_driver_has_no_grid(self):
        env = self.installed()
        self.gpu(driver="nvidia")
        (self.env.etc / "fliperos.conf").write_text(
            "nvidia_driver=nvidia\namd_driver_trial=nvidia\namd_driver_previous=nouveau\n")
        out = self.env.out(self.TRIAL + self.CONFIRM, env)
        self.assertNotIn("GRID", out)
        self.assertNotIn("amd_driver_trial", self.conf())

    MENU = ('ui_fields() { :; }; ui_yes() { echo "$*"; }; ui_no() { echo "$*"; }\n'
            'ui_msg() { echo "MSG $1: ${*:2}"; }\n'
            'ui_yesno() { echo "ASKED: $2"; return 1; }\n'
            'screen_amd_driver_apply() { echo "APPLY $1"; }\n')

    def test_driver_menu_compares_the_two(self):
        env = self.installed()
        self.gpu()
        answers = self.env.dir / "answers"
        answers.write_text("compare\nreturn\n")
        out = self.env.out(self.TRIAL + self.MENU +
                           'ui_menu_hints() { local a; read -r a < "%s"; sed -i 1d "%s"; echo "$a"; }\n'
                           "screen_nvidia_driver" % (answers, answers), env)
        self.assertIn("MSG nouveau (open source): + Every FliperOS program changes resolution", out)
        self.assertIn("MSG NVIDIA driver (closed): + Full 3D speed", out)
        self.assertIn("- Outside Xorg only the boot modes", out)
        self.assertNotIn("APPLY", out)

    def test_choosing_a_driver_shows_it_and_asks(self):
        env = self.installed()
        self.gpu()
        out = self.env.out(self.TRIAL + self.MENU + 'ui_menu_hints() { echo nvidia; }\nscreen_nvidia_driver', env)
        self.assertIn("MSG NVIDIA driver (closed)", out)
        self.assertNotIn("MSG nouveau", out)
        self.assertIn("ASKED: Use the NVIDIA driver?", out)
        # Nao confirmou: nada muda.
        self.assertNotIn("APPLY", out)

    def test_boot_without_the_module_goes_back_to_nouveau(self):
        # Um kernel novo que o DKMS nao compilou: com o nouveau na lista
        # negra nao haveria imagem.
        env = self.installed(module=False)
        self.gpu(driver="nouveau")
        (self.env.etc / "fliperos.conf").write_text("nvidia_driver=nvidia\n")
        self.env.out(self.TRIAL + "xorg_generate() { :; }\namd_driver_trial_boot", env)
        calls = self.calls.read_text()
        self.assertIn("dkms autoinstall", calls)
        self.assertIn("systemctl reboot", calls)
        self.assertEqual(self.conf()["nvidia_driver"], "nouveau")

    def test_boot_with_the_module_does_nothing(self):
        env = self.installed(module=True)
        self.gpu(driver="nvidia")
        (self.env.etc / "fliperos.conf").write_text("nvidia_driver=nvidia\n")
        self.env.out(self.TRIAL + "amd_driver_trial_boot", env)
        self.assertEqual(self.calls.read_text(), "")
        self.assertEqual(self.conf()["nvidia_driver"], "nvidia")

    def test_package_by_modalias(self):
        apt = self.env.dir / "apt"
        apt.mkdir()
        (apt / "nvidia-driver-580").write_text(
            "Package: nvidia-driver-580\nModaliases: nvidia(pci:v000010DEd000017C8sv*sd*bc03sc*i*, "
            "pci:v000010DEd00001B80sv*sd*bc03sc*i*)\n")
        (apt / "nvidia-driver-595").write_text(
            "Package: nvidia-driver-595\nModaliases: nvidia(pci:v000010DEd00002204sv*sd*bc03sc*i*)\n")
        (apt / "nvidia-driver-470").write_text(
            "Package: nvidia-driver-470\nModaliases: nvidia(pci:v000010DEd00001180sv*sd*bc03sc*i*, "
            "pci:v000010DEd000017C8sv*sd*bc03sc*i*)\n")
        self.env.stub("apt-cache", '[ "$1" = show ] && cat "%s/$2" 2> /dev/null' % apt)
        tool = str(ROOT / "config/fliperos-nvidia")
        r = lambda dev, versions=None: self.env.run(
            '"%s" package %s' % (tool, dev), {"FLIPEROS_NVIDIA_VERSIONS": versions} if versions else None)
        # So o 580 compila no kernel 15 kHz: a Kepler (1180) fica no nouveau.
        self.assertEqual(r("17c8").stdout.strip(), "nvidia-driver-580")
        self.assertNotEqual(r("1180").returncode, 0)
        self.assertNotEqual(r("2204").returncode, 0)
        # Com mais versoes, a mais nova que lista a placa.
        self.assertEqual(r("2204", "595 580 470").stdout.strip(), "nvidia-driver-595")
        self.assertEqual(r("1180", "595 580 470").stdout.strip(), "nvidia-driver-470")
        self.assertEqual(r("17c8", "595 580 470").stdout.strip(), "nvidia-driver-580")
        self.assertNotEqual(r("0fff").returncode, 0)
        self.assertNotEqual(r("x;y").returncode, 0)

    def test_boot_menu_offers_nouveau_back(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("limine_update", ROOT / "fliperos-limine-update.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        text = mod.render(["6.18.54-15khz"], "UUID=abc", "quiet splash " + self.NVIDIA, "3")
        entry = text.split("/FliperOS - nouveau driver\n")[1]
        cmdline = re.search(r"cmdline: (.*)", entry).group(1).split()
        self.assertIn(self.NOUVEAU, cmdline)
        self.assertNotIn("modprobe.blacklist=nouveau", cmdline)
        self.assertNotIn("nvidia-drm.modeset=1", cmdline)
        plain = mod.render(["6.18.54-15khz"], "UUID=abc", "quiet splash " + self.NOUVEAU, "3")
        self.assertNotIn("nouveau driver", plain)

    def test_menu_and_installer_are_wired(self):
        video = (SETUP / "screens/video-setup.sh").read_text()
        self.assertIn("elif nvidia_card > /dev/null; then", video)
        screen = (SETUP / "screens/amd-driver.sh").read_text()
        self.assertIn('run_online "Installing the NVIDIA driver" "" nvidia_driver_install', screen)
        rootfs = (ROOT / "fliperos-rootfs.sh").read_text()
        self.assertIn('"$src/config/fliperos-nvidia" "$root/opt/fliperos/bin/fliperos-nvidia"', rootfs)
        tool = (ROOT / "config/fliperos-nvidia").read_text()
        # A lista negra do nouveau do pacote e anulada: quem escolhe e a linha.
        self.assertIn('"$MODPROBE_DIR/nvidia-graphics-drivers.conf"', tool)
        self.assertIn("--no-install-recommends", tool)


if __name__ == "__main__":
    unittest.main()
