"""Testes do build da midia e dos arquivos que vao para a imagem.

Rodam com python3 puro (sem Docker, sem chroot): conferem os scripts de
build, o menu de boot, o Limine do disco instalado, o fliperos-video-check
e as configuracoes que o fliperos-rootfs.sh instala.
"""
import importlib.util
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


video = load('video', 'fliperos-video-check.py')
limine_update = load('limine_update', 'fliperos-limine-update.py')
MKISO = (ROOT / 'fliperos-mkiso.sh').read_text()
ROOTFS = (ROOT / 'fliperos-rootfs.sh').read_text()


def boot_entries(text=None):
    """(titulo, corpo) de cada entrada do limine.conf da midia."""
    text = text if text is not None else (ROOT / 'config/limine.conf').read_text()
    entries = []
    for block in text.split('\n/')[1:]:
        title, _, body = block.partition('\n')
        entries.append((title, body))
    return entries


def cmdline(body):
    return re.search(r'cmdline: (.*)', body).group(1).split()


class VideoCheckTests(unittest.TestCase):
    def test_progressive(self):
        result = video.timing(6510, 416, 261)
        self.assertAlmostEqual(result['horizontal_khz'], 15.64903846)
        self.assertAlmostEqual(result['vertical_hz'], 59.957999, places=4)

    def test_interlaced_fields(self):
        result = video.timing(13500, 858, 525, 16)
        self.assertAlmostEqual(result['horizontal_khz'], 15.73426573)
        self.assertAlmostEqual(result['vertical_hz'], 59.94005994)

    def test_boot_mode_640x480i(self):
        # O modo 640x480i da tabela do patch 15 kHz: 13.038 MHz, 831 x 523.
        result = video.timing(13038, 831, 523, 16)
        self.assertAlmostEqual(result['horizontal_khz'], 15.6895, places=3)
        self.assertTrue(result['interlaced'])

    def test_doublescan_not_false_15khz(self):
        result = video.timing(25175, 800, 525, 32)
        self.assertAlmostEqual(result['horizontal_khz'], 31.46875)
        self.assertAlmostEqual(result['vertical_hz'], 29.9702381)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            video.timing(0, 416, 261)

    def test_verdicts(self):
        crt = {'connector': 'VGA-1', 'active': True, 'horizontal_khz': 15.649}
        lcd = {'connector': 'HDMI-A-1', 'active': True, 'horizontal_khz': 31.469}
        self.assertEqual(video.verdict([], [], None, 15, 16)[1], 2)
        self.assertEqual(video.verdict([crt], ['permission denied'], None, 15, 16)[1], 2)
        self.assertEqual(video.verdict([crt, lcd], [], None, 15, 16)[1], 1)
        self.assertEqual(video.verdict([crt, lcd], [], 'VGA-1', 15, 16)[1], 0)


class BootMenuTests(unittest.TestCase):
    """O menu da midia tem as opcoes do GroovyArcade e escolhe sozinho em 30 s."""

    EXPECTED = [
        ('15 kHz', '15khz', 'video=640x480iS'),
        ('25 kHz', '25khz', 'video=512x384S'),
        ('31 kHz', '31khz', 'video=640x480S'),
        ('SVGA / LCD monitor', 'svga', None),
        ('Intel 15 kHz', 'intel', 'video=1280x480iS'),
        ('NVIDIA 15 kHz', 'nvidia', 'video=1280x480iS'),
        ('NTSC', 'ntsc', 'video=720x480iS'),
        ('PAL', 'pal', 'video=768x576iS'),
        ('EDID progressive', 'edid-progressive', 'drm.edid_firmware=edid/generic_15_super_resp.bin'),
        ('EDID interlaced', 'edid-interlaced', 'drm.edid_firmware=edid/generic_15_super_resi.bin'),
    ]

    def test_ten_entries_in_groovyarcade_order(self):
        entries = boot_entries()
        self.assertEqual([t for t, _ in entries], [t for t, _, _ in self.EXPECTED])
        for (title, body), (_, profile, video_param) in zip(entries, self.EXPECTED):
            params = cmdline(body)
            self.assertIn('boot=live', params, title)
            self.assertIn('fliperos.boot=' + profile, params, title)
            self.assertIn('__COMMON__', params, title)
            if video_param:
                self.assertIn(video_param, params, title)
            else:
                self.assertFalse([p for p in params if p.startswith(('video=', 'drm.edid'))], title)

    def test_thirty_second_timer_defaults_to_15khz(self):
        text = (ROOT / 'config/limine.conf').read_text()
        self.assertRegex(text, r'(?m)^timeout: 30$')
        self.assertRegex(text, r'(?m)^default_entry: 1$')
        self.assertEqual(boot_entries(text)[0][0], '15 kHz')

    def test_edid_entries_force_the_outputs_on(self):
        for title, body in boot_entries():
            if title.startswith('EDID'):
                self.assertIn('video=e', cmdline(body))

    def test_intel_entry_enables_gen9_interlace(self):
        intel = dict(boot_entries())['Intel 15 kHz']
        self.assertIn('i915.no_ytiled_scanout=1', cmdline(intel))
        self.assertNotIn('i915.no_ytiled_scanout=1', cmdline(dict(boot_entries())['NVIDIA 15 kHz']))

    def test_entries_boot_the_iso_kernel_in_text_mode(self):
        for title, body in boot_entries():
            self.assertIn('protocol: linux', body, title)
            # copy_kernel do fliperos-mkiso.sh grava nesses dois caminhos.
            self.assertIn('path: boot():/boot/vmlinuz\n', body, title)
            self.assertIn('module_path: boot():/boot/initrd.img\n', body, title)
            self.assertIn('textmode: yes', body, title)

    def test_placeholders_are_filled_by_the_build(self):
        self.assertIn('s|__VERSION__|${FLIPEROS_VERSION}|g', MKISO)
        self.assertIn('s|__COMMON__|${BOOT_COMMON}|g', MKISO)
        common = re.search(r'BOOT_COMMON="([^"]*)"', MKISO).group(1).split()
        self.assertIn('splash', common)
        self.assertIn('consoleblank=0', common)

    def test_titles_fit_limine_limit(self):
        # O Limine guarda o titulo num buffer de 64 bytes junto com a "/" e o
        # terminador: acima de 62 caracteres ele corta o fim sem avisar.
        installed = limine_update.render(['6.18.54-15khz', '6.18.50-15khz'], 'UUID=abc', '', '3')
        for text in ((ROOT / 'config/limine.conf').read_text(), installed):
            for line in text.splitlines():
                if line.startswith('/'):
                    self.assertLessEqual(len(line[1:]), 62, line)


class InstalledLimineTests(unittest.TestCase):
    """O Limine so le FAT: no disco instalado kernel e initrd vivem na ESP,
    copiados pelo fliperos-limine-update. Erro aqui e gabinete sem boot."""

    def boot_dir(self, root, versions):
        boot = root / 'boot'
        boot.mkdir()
        for version in versions:
            (boot / ('vmlinuz-' + version)).write_bytes(b'kernel ' + version.encode())
            (boot / ('initrd.img-' + version)).write_bytes(b'initrd ' + version.encode())
        return boot

    def test_newest_kernel_first_in_natural_order(self):
        with tempfile.TemporaryDirectory() as directory:
            boot = self.boot_dir(Path(directory), ['6.18.9-15khz', '6.18.54-15khz', '6.8.0-45-generic'])
            self.assertEqual(limine_update.kernels(boot),
                             ['6.18.54-15khz', '6.18.9-15khz', '6.8.0-45-generic'])

    def test_kernel_without_initrd_is_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            boot = self.boot_dir(Path(directory), ['6.18.54-15khz'])
            (boot / 'vmlinuz-6.18.60-15khz').write_bytes(b'x')
            self.assertEqual(limine_update.kernels(boot), ['6.18.54-15khz'])

    def test_installed_entries(self):
        line = 'quiet splash consoleblank=0 video=VGA-1:640x480iSe'
        text = limine_update.render(['6.18.54-15khz', '6.18.50-15khz'], 'UUID=abc', line, '3')
        self.assertIn('graphics: no', text)
        entries = text.split('\n/')[1:]
        self.assertEqual(len(entries), 3)
        normal, previous, diagnostic = entries
        self.assertIn('vmlinuz-6.18.54-15khz', normal)
        self.assertIn('vmlinuz-6.18.50-15khz', previous)
        for entry in entries:
            self.assertIn('cmdline: root=UUID=abc ro ', entry)
            self.assertIn('video=VGA-1:640x480iSe', entry)
            self.assertIn('textmode: yes', entry)
        self.assertNotIn('splash', cmdline(diagnostic))
        self.assertNotIn('quiet', cmdline(diagnostic))

    def test_update_keeps_two_kernels_and_drops_stale(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            boot = self.boot_dir(root, ['6.18.1-15khz', '6.18.50-15khz', '6.18.54-15khz'])
            esp = root / 'esp'
            (esp / 'fliperos').mkdir(parents=True)
            (esp / 'fliperos/vmlinuz-6.12.104-15khz').write_bytes(b'old')
            versions = limine_update.update(boot, esp, 'UUID=abc', 'quiet splash', '3')
            self.assertEqual(versions, ['6.18.54-15khz', '6.18.50-15khz'])
            self.assertEqual(sorted(p.name for p in (esp / 'fliperos').iterdir()),
                             ['initrd.img-6.18.50-15khz', 'initrd.img-6.18.54-15khz',
                              'vmlinuz-6.18.50-15khz', 'vmlinuz-6.18.54-15khz'])

    def test_update_refreshes_regenerated_initrd(self):
        # update-initramfs (EDID novo da resolucao personalizada) regrava o
        # initrd com o mesmo nome: a ESP precisa receber o conteudo novo.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            boot = self.boot_dir(root, ['6.18.54-15khz'])
            esp = root / 'esp'
            limine_update.update(boot, esp, 'UUID=abc', '', '3')
            (boot / 'initrd.img-6.18.54-15khz').write_bytes(b'initrd com EDID novo')
            limine_update.update(boot, esp, 'UUID=abc', '', '3')
            self.assertEqual((esp / 'fliperos/initrd.img-6.18.54-15khz').read_bytes(),
                             b'initrd com EDID novo')

    def test_defaults_written_by_the_setup_are_read_back(self):
        """O fliperos-setup grava /etc/default/fliperos-boot e o
        fliperos-limine-update le: os dois precisam concordar no formato."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fliperos-boot'
            script = ('source %s/fliperos-setup/lib/common.sh; source %s/fliperos-setup/lib/bootloader.sh; '
                      'boot_write_cmdline "quiet video=VGA-1:640x480iSe" %s'
                      % (ROOT, ROOT, path))
            subprocess.run(['bash', '-c', script], check=True)
            defaults = limine_update.read_defaults(path.read_text())
            self.assertEqual(defaults['FLIPEROS_CMDLINE'], 'quiet video=VGA-1:640x480iSe')
            self.assertEqual(defaults['FLIPEROS_TIMEOUT'], '3')

    def test_root_from_installer_fstab(self):
        fstab = ('# / comentario\nUUID=aaa / ext4 defaults 0 1\n'
                 'UUID=bbb /boot/efi vfat umask=0077 0 2\n')
        self.assertEqual(limine_update.root_device(fstab), 'UUID=aaa')


class KernelTests(unittest.TestCase):
    """O kernel 15 kHz e o do GroovyArcade: kernel.org LTS + patches D0023R."""

    SCRIPT = (ROOT / 'fliperos-kernel.sh').read_text()

    def test_patch_set_matches_the_series(self):
        version = re.search(r'KERNEL_VERSION="([0-9.]+)"', self.SCRIPT).group(1)
        series = '.'.join(version.split('.')[:2])
        patches = sorted(p.name for p in (ROOT / 'patches/kernel-15khz' / series).glob('*.patch'))
        self.assertEqual([p[:2] for p in patches], ['%02d' % n for n in range(1, 10)])
        self.assertIn('09_linux_15khz_i915_gen9_interlace.patch', patches)

    def test_patches_have_unix_line_endings(self):
        for patch in (ROOT / 'patches/kernel-15khz').rglob('*.patch'):
            self.assertNotIn(b'\r\n', patch.read_bytes(), patch.name)

    def test_low_dotclock_table_has_the_boot_modes(self):
        # Os modos das entradas do boot e do Video Setup precisam existir na
        # tabela fixa do patch principal.
        text = (ROOT / 'patches/kernel-15khz/6.18/01_linux_15khz.patch').read_text()
        for mode in ('640x480i', '720x480i', '768x576i', '1280x480i', '512x384', '800x600i', '640x480',
                     '320x240', '384x288', '640x240', '1024x768i'):
            self.assertIn('DRM_MODE("%s"' % mode, text)

    def test_config_keeps_what_fliperos_needs(self):
        for option in ('DRM_LOAD_EDID_FIRMWARE', 'FRAMEBUFFER_CONSOLE_ROTATION', 'DEBUG_INFO_NONE'):
            self.assertIn(option, self.SCRIPT)
        self.assertIn('--disable MODULE_SIG', self.SCRIPT)

    def test_build_always_installs_the_15khz_kernel(self):
        self.assertIn('install_15khz_kernel', MKISO)
        self.assertNotIn('linux-image-generic linux-headers-generic', MKISO)
        self.assertNotIn('--with-15khz-kernel', MKISO)
        self.assertIn('fliperos-kernel.sh" key', MKISO)


class PinnedDownloadTests(unittest.TestCase):
    """O que nao existe no Ubuntu 24.04 vem fixado por versao e hash."""

    def test_debs_are_checked(self):
        for name in ('GUM', 'ANTIMICROX'):
            self.assertRegex(MKISO, r'%s_SHA256="[0-9a-f]{64}"' % name)
        self.assertIn('sha256sum -c', MKISO)

    def test_sources_are_pinned(self):
        self.assertRegex(MKISO, r'SWITCHRES_TAG="v[0-9.]+"')
        self.assertRegex(MKISO, r'SKYSCRAPER_COMMIT="[0-9a-f]{40}"')
        pinned = (ROOT / 'fliperos-limine.sh').read_text()
        self.assertRegex(pinned, r'LIMINE_COMMIT="[0-9a-f]{40}"')

    def test_build_uses_limine_not_grub(self):
        self.assertNotIn('grub-mkrescue', MKISO)
        self.assertIn('fliperos-limine.sh" iso', MKISO)
        self.assertIn('fliperos-limine.sh" rootfs', MKISO)


class ImageTests(unittest.TestCase):
    """O que o fliperos-rootfs.sh e o fliperos-mkiso.sh poem na imagem."""

    def test_groovyarcade_desktop_tools(self):
        for pkg in ('lxde', 'xterm', 'htop', 'evtest', 'joy2key', 'qjoypad', 'hwinfo', 'read-edid'):
            self.assertRegex(MKISO, r'\b%s\b' % re.escape(pkg), pkg)
        self.assertIn('antimicrox', MKISO)
        self.assertIn('/tmp/gum.deb /tmp/antimicrox.deb', MKISO)

    def test_old_menus_are_gone(self):
        for old in ('fliperos-config', 'fliperos-install.py', 'fliperos_tui', 'whiptail',
                    'MONITOR_PROFILE', 'fliperos-install-video'):
            self.assertNotIn(old, MKISO, old)
            self.assertNotIn(old, ROOTFS, old)

    def test_setup_is_installed_and_in_system_tools(self):
        self.assertIn('/usr/local/lib/fliperos-setup', ROOTFS)
        self.assertIn('fliperos-setup.desktop', ROOTFS)
        desktop = (ROOT / 'config/fliperos-setup.desktop').read_text()
        self.assertIn('Categories=System;', desktop)
        self.assertIn('Exec=sudo /usr/local/bin/fliperos-setup', desktop)
        self.assertIn('Terminal=true', desktop)

    def test_tty1_flow_like_groovyarcade(self):
        """No disco: primeiro boot, launcher e depois o setup. Na midia: setup."""
        profile = ROOTFS.split('.bash_profile" << \'EOF\'')[1].split('\nEOF')[0]
        installed = profile.split('if [[ -f /etc/fliperos/installed ]]; then')[1]
        self.assertLess(installed.index('--first-boot'), installed.index('fliperos-session'))
        # O setup "normal" e a ultima chamada, depois do launcher fechar.
        self.assertLess(installed.index('fliperos-session'), installed.rindex('sudo /usr/local/bin/fliperos-setup\n'))

    def test_sudo_only_for_the_setup(self):
        self.assertIn('NOPASSWD: /usr/local/bin/fliperos-setup', ROOTFS)

    def test_dracula_console_palette(self):
        rows = (ROOT / 'config/vtrgb-dracula').read_text().split()
        self.assertEqual(len(rows), 3)
        palette = [[int(v) for v in row.split(',')] for row in rows]
        self.assertTrue(all(len(r) == 16 for r in palette))
        # Indice 0 e o fundo do Dracula (#282a36), o 4 o roxo (#bd93f9).
        self.assertEqual([c[0] for c in palette], [40, 42, 54])
        self.assertEqual([c[4] for c in palette], [189, 147, 249])
        self.assertIn('update-alternatives --install /etc/vtrgb vtrgb', ROOTFS)

    def test_edids_for_every_preset(self):
        script = (ROOT / 'config/fliperos-rebuild-edids').read_text()
        presets = subprocess.run(
            ['bash', '-c', 'source %s/fliperos-setup/lib/monitor.sh; '
                           'for e in "${MONITOR_PRESETS[@]}"; do echo "${e%%%%|*}"; done' % ROOT],
            capture_output=True, text=True, check=True).stdout.split()
        for preset in presets:
            if preset == 'lcd':
                continue
            self.assertRegex(script, r'\b%s\b' % preset, preset)
        self.assertIn('generic_15_super_resi.bin', script)
        self.assertIn('generic_15_super_resp.bin', script)
        hook = (ROOT / 'config/fliperos-edid-hook').read_text()
        self.assertIn('/lib/firmware/edid/*.bin', hook)

    def test_geometry_is_the_switchres_tool(self):
        self.assertIn('/tmp/srs/geometry.py', MKISO)
        self.assertIn('/usr/local/bin/geometry', MKISO)

    def test_lxde_session_has_no_blanking_and_follows_orientation(self):
        client = (ROOT / 'config/fliperos-lxde').read_text()
        for cmd in ('xset -dpms', 'xset s off', 'xrandr -o right', 'xrandr -o left', 'exec startlxde'):
            self.assertIn(cmd, client)
        panel = (ROOT / 'config/lxde/lxpanel/LXDE/panels/panel').read_text()
        self.assertIn('fliperos-setup.desktop', panel)
        self.assertIn('edge=bottom', panel)


class SessionTableTests(unittest.TestCase):
    TABLE = ROOT / 'config/fliperos-sessions.conf'

    def rows(self):
        return [line.split('|') for line in self.TABLE.read_text().splitlines()
                if line.strip() and not line.lstrip().startswith('#')]

    def test_format(self):
        for row in self.rows():
            self.assertEqual(len(row), 5, row)
            self.assertIn(row[1], ('kms', 'x', 'none'), row)

    def test_setup_is_the_safe_default_and_openbox_alone_is_not_offered(self):
        names = [r[0] for r in self.rows()]
        self.assertEqual(names[0], 'setup')
        self.assertNotIn('openbox', names)
        lxde = [r for r in self.rows() if r[0] == 'lxde'][0]
        self.assertEqual(lxde[2], '/opt/fliperos/bin/fliperos-lxde')
        self.assertIn('printf \'setup\\n\'', ROOTFS)

    def test_session_script_falls_back_to_the_setup(self):
        script = (ROOT / 'config/fliperos-session').read_text()
        self.assertIn('[[ $backend == none ]] && exit 0', script)
        self.assertNotIn('fliperos-launcher', script)


class InputDriverTests(unittest.TestCase):
    """GunCon 2 nao existe no kernel mainline; Logitech e Thrustmaster antigo
    existem. Por isso o GunCon entra por padrao e os de volante sao opcionais."""

    def test_guncon2_usb_id_and_calibration_hook(self):
        rules = (ROOT / 'config/99-fliperos-input.rules').read_text()
        self.assertIn('0b9a', rules)
        self.assertIn('016a', rules)
        self.assertIn('fliperos-guncon2-calibrate', rules)

    def test_guncon2_builds_by_default_wheels_behind_flag(self):
        self.assertIn('SKIP_INPUT_DRIVERS=false', MKISO)
        self.assertIn('WITH_WHEEL_DRIVERS=false', MKISO)
        self.assertIn('beardypig/guncon2', MKISO)
        self.assertIn('modules-load.d', MKISO)

    def test_rules_and_config_are_installed(self):
        for name in ('99-fliperos-input.rules', 'fliperos-guncon2-calibrate', 'guncon2.conf'):
            self.assertIn(name, ROOTFS)

    def test_dkms_modules_build_after_the_kernel(self):
        main = MKISO.split('# ── Main')[1]
        self.assertLess(main.index('install_15khz_kernel'), main.index('build_input_drivers_chroot'))


class ShellErrexitTests(unittest.TestCase):
    """Sob "set -e", uma funcao cujo ULTIMO comando e uma lista "&&" devolve 1
    quando a condicao e falsa, e a chamada nua dela no fluxo principal aborta.
    Ja derrubou um build de ISO depois do driver compilado."""

    SCRIPTS = ('fliperos-mkiso.sh', 'fliperos-rootfs.sh', 'fliperos-kernel.sh',
               'packaging/build-deb.sh', 'packaging/make-repo.sh')
    RISKY = re.compile(r'^\s*(\$[A-Za-z_]+|\[\[.*\]\]|\[.*\])\s*&&')

    def functions(self, text):
        found, name, body = [], None, []
        for line in text.splitlines():
            start = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\(\)\s*\{', line)
            if start:
                name, body = start.group(1), []
                continue
            if name is None:
                continue
            if line == '}':
                meaningful = [b for b in body if b.strip() and not b.strip().startswith('#')]
                if meaningful:
                    found.append((name, meaningful[-1]))
                name = None
                continue
            body.append(line)
        return found

    def test_no_function_ends_with_a_boolean_and_list(self):
        for script in self.SCRIPTS:
            path = ROOT / script
            for name, last in self.functions(path.read_text()):
                self.assertIsNone(self.RISKY.match(last),
                                  '%s: %s() termina em lista &&: %s' % (script, name, last.strip()))

    def test_the_parser_actually_finds_functions(self):
        names = {name for name, _ in self.functions(MKISO)}
        self.assertIn('install_15khz_kernel', names)
        self.assertIn('summary', names)


class LatencyBuildTests(unittest.TestCase):
    """O modo de latencia padrao ja vem na midia e no sistema instalado
    (README, secao "Latencia")."""

    LIB = (ROOT / 'fliperos-setup/lib/latency.sh').read_text()

    def base_params(self):
        return re.search(r'^LATENCY_BASE_PARAMS="([^"]*)"', self.LIB, flags=re.M).group(1).split()

    def test_live_media_boots_with_the_standard_mode(self):
        common = re.search(r'BOOT_COMMON="([^"]*)"', MKISO).group(1).split()
        for param in self.base_params():
            self.assertIn(param, common)
        self.assertIn('mitigations=off', self.base_params())
        self.assertIn('usbhid.jspoll=1', self.base_params())
        self.assertNotIn('preempt=full', common)

    def test_service_applies_the_mode_at_boot(self):
        unit = (ROOT / 'config/fliperos-latency.service').read_text()
        self.assertIn('ExecStart=/usr/local/bin/fliperos-setup --latency-boot', unit)
        self.assertIn('WantedBy=multi-user.target', unit)
        self.assertIn('config/fliperos-latency.service', ROOTFS)
        self.assertIn('multi-user.target.wants/fliperos-latency.service', ROOTFS)
        entry = (ROOT / 'fliperos-setup/fliperos-setup').read_text()
        for option in ('--latency-boot)', '--session-start)', '--session-end)'):
            self.assertIn(option, entry)
        # As opcoes sem tela rodam antes de exigir o gum e um terminal.
        self.assertLess(entry.index('--latency-boot)'), entry.index('if ! have gum'))

    def test_background_apt_is_masked(self):
        for timer in ('apt-daily.timer', 'apt-daily-upgrade.timer', 'man-db.timer'):
            self.assertIn(timer, ROOTFS)

    def test_session_sets_the_governor_around_the_launcher(self):
        script = (ROOT / 'config/fliperos-session').read_text()
        start = script.index('--session-start')
        end = script.index('--session-end')
        self.assertLess(start, script.index('fliperos-kms-run "$binary"'))
        self.assertLess(script.index('xinit "$binary"'), end)
        self.assertNotIn('exec /opt/fliperos/bin/fliperos-kms-run', script)
        self.assertNotIn('exec xinit', script)

    def test_groovymame_uses_the_current_option_names(self):
        # GroovyMAME chama de "framedelay" (sem _) e ja tem o automatico.
        ini = (ROOT / 'config/mame.ini').read_text()
        for line in ('lowlatency 1', 'autoframedelay 1', 'framedelay 0'):
            self.assertIn('\n' + line + '\n', ini)
        self.assertNotIn('frame_delay', ini)


class DockerfileTests(unittest.TestCase):
    DOCKERFILE = (ROOT / 'Dockerfile.fliperos').read_text()

    def test_copies_everything_the_build_reads(self):
        for needed in ('fliperos-*.sh', 'fliperos*.py', 'config/', 'patches/', 'fliperos-setup/'):
            self.assertIn(needed, self.DOCKERFILE)
        self.assertIn('ubuntu:24.04', self.DOCKERFILE)

    def test_packager_base_matches_iso_base(self):
        self.assertIn('ubuntu:24.04', (ROOT / 'Dockerfile.packages').read_text())


class PackagingTests(unittest.TestCase):
    RECIPES = ROOT / 'packaging/packages'

    def recipe_files(self):
        return sorted(self.RECIPES.glob('*.sh'))

    def test_recipes_declare_the_full_contract(self):
        self.assertTrue(self.recipe_files())
        for recipe in self.recipe_files():
            text = recipe.read_text()
            for field in ('PKG_NAME=', 'PKG_VERSION=', 'PKG_SUMMARY=',
                          'PKG_BUILD_DEPS=', 'PKG_SHLIB_TARGETS=', 'pkg_build()'):
                self.assertIn(field, text, '%s sem %s' % (recipe.name, field))

    def test_recipe_filename_matches_package_name(self):
        for recipe in self.recipe_files():
            declared = re.search(r'^PKG_NAME="([^"]+)"', recipe.read_text(), flags=re.M).group(1)
            self.assertEqual(declared, recipe.stem)

    def test_every_recipe_is_a_launcher_package(self):
        table = (ROOT / 'config/fliperos-sessions.conf').read_text()
        for recipe in self.recipe_files():
            self.assertIn(recipe.stem, table)


class SplashTests(unittest.TestCase):
    def test_theme_files_are_installed(self):
        self.assertIn('fliperos.plymouth', ROOTFS)
        self.assertIn('fliperos.script', ROOTFS)

    def test_theme_script_uses_only_verified_api(self):
        text = (ROOT / 'config/plymouth/fliperos.script').read_text()
        for call in ('Window.SetBackgroundTopColor', 'Window.GetWidth', 'Image.Text',
                     'Math.Int', 'Plymouth.SetBootProgressFunction'):
            self.assertIn(call, text)
        self.assertNotIn('Image(', text)

    def test_splash_is_generated_for_the_boot_mode(self):
        geometry = MKISO.split('splash_mode_geometry()')[1].split('}')[0]
        self.assertIn('640x480', geometry)


class RetroArchConfigTests(unittest.TestCase):
    """config/retroarch.cfg e config de sistema: o fliperos-kms-run a passa
    com --appendconfig, por cima da do usuario."""

    CFG = ROOT / 'config/retroarch.cfg'

    def values(self):
        found = {}
        for line in self.CFG.read_text().splitlines():
            if not line.strip() or line.startswith('#'):
                continue
            match = re.match(r'^([a-z0-9_]+) = "([^"]*)"$', line)
            self.assertIsNotNone(match, 'linha fora do formato do RetroArch: ' + line)
            self.assertNotIn(match.group(1), found, 'chave repetida: ' + match.group(1))
            found[match.group(1)] = match.group(2)
        return found

    def test_crt_switchres_uses_the_system_switchres_ini(self):
        self.assertEqual(self.values()['crt_switch_resolution'], '4')

    def test_video_driver_can_modeswitch_in_kms(self):
        self.assertEqual(self.values()['video_driver'], 'gl')

    def test_initial_mode_is_the_active_one(self):
        values = self.values()
        self.assertEqual((values['video_fullscreen_x'], values['video_fullscreen_y']), ('0', '0'))

    def test_audio_is_alsa(self):
        self.assertEqual(self.values()['audio_driver'], 'alsa')

    def test_standard_latency_values(self):
        values = self.values()
        self.assertEqual(values['video_max_swapchain_images'], '2')
        self.assertEqual(values['video_threaded'], 'false')
        self.assertEqual(values['input_poll_type_behavior'], '2')
        # Os do modo de baixa latencia ficam desligados no arquivo da ISO.
        self.assertEqual(values['video_frame_delay_auto'], 'false')
        self.assertEqual(values['preemptive_frames_enable'], 'false')
        self.assertEqual(values['run_ahead_enabled'], 'false')

    def test_retroarch_gets_the_system_config(self):
        self.assertIn('--appendconfig /etc/fliperos/retroarch/retroarch.cfg',
                      (ROOT / 'config/fliperos-kms-run').read_text())


if __name__ == '__main__':
    unittest.main()
