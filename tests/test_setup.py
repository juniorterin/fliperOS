"""Testes da logica do fliperos-setup (fliperos-setup/lib/*.sh).

Cada teste roda um trecho de bash com as bibliotecas carregadas e os
caminhos de sistema apontados para arvores falsas (sysfs do DRM, /etc,
/proc/cmdline). Rode no container do tests/Dockerfile: o mesmo Ubuntu da
ISO, com o mesmo mawk e jq.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "fliperos-setup"
LIBS = ["common", "config", "progress", "speech", "monitor", "drm", "video", "xorg",
        "bootloader", "disk", "install", "recovery", "launcher", "audio", "network",
        "status", "scraper", "update", "hardware", "latency", "quirks", "padkeys"]
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
        self.assertEqual(out, "quiet " + LATENCY_BASE + " video=VGA-1:640x480iSe fbcon=map:1")

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


class UpdateTests(Base):
    def test_status_fd_to_events(self):
        lines = "dlstatus:1:0:Retrieving file 1 of 2\\ndlstatus:2:50:Retrieving file 2 of 2\\n" \
                "pmstatus:mesa:0:Preparing mesa\\npmstatus:mesa:100:Installed mesa\\n"
        out = self.env.out("printf '%s' | update_parse_status" % lines).splitlines()
        self.assertEqual(out, ["@step 10 Retrieving file 1 of 2", "@step 30 Retrieving file 2 of 2",
                               "@step 50 Preparing mesa", "@step 99 Installed mesa"])


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
        self.assertEqual(standard, "quiet splash " + LATENCY_BASE)
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


if __name__ == "__main__":
    unittest.main()
