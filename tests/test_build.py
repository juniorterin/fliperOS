"""Testes do build da midia e dos arquivos que vao para a imagem.

Rodam com python3 puro (sem Docker, sem chroot): conferem os scripts de
build, o menu de boot, o Limine do disco instalado, o fliperos-video-check
e as configuracoes que o fliperos-rootfs.sh instala.
"""
from importlib.machinery import SourceFileLoader
import importlib.util
import io
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import unittest
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_script(name, filename):
    """Script Python sem extensao (os de config/). Sem .pyc: um
    config/__pycache__ iria junto em quem copia a pasta inteira."""
    sys.dont_write_bytecode = True
    loader = SourceFileLoader(name, str(ROOT / filename))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


video = load('video', 'fliperos-video-check.py')
limine_update = load('limine_update', 'fliperos-limine-update.py')
padkeys = load_script('padkeys', 'config/fliperos-padkeys')
calibrate = load_script('calibrate', 'config/fliperos-calibrate')
controllers = load_script('controllers', 'config/fliperos-controllers')
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

    def test_pcsx2_is_the_pinned_appimage(self):
        # O PCSX2 atual nao compila com as bibliotecas do noble (SDL3, Qt 6.10).
        self.assertRegex(MKISO, r'PCSX2_VERSION="[0-9.]+"')
        self.assertRegex(MKISO, r'PCSX2_SHA256="[0-9a-f]{64}"')
        body = MKISO.split('build_pcsx2_chroot() {')[1].split('\n}\n')[0]
        self.assertIn('echo "$PCSX2_SHA256  $image" | sha256sum -c', body)
        self.assertIn('--appimage-extract', body)
        self.assertIn('exec /opt/pcsx2/AppRun', body)
        self.assertNotIn('git clone', body)

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
        for pkg in ('lxde-core', 'htop', 'evtest', 'joy2key', 'qjoypad', 'hwinfo', 'read-edid'):
            self.assertRegex(MKISO, r'\b%s\b' % re.escape(pkg), pkg)
        self.assertIn('antimicrox', MKISO)
        self.assertIn('/tmp/gum.deb /tmp/antimicrox.deb', MKISO)

    def test_gum_menus_page_with_arrows(self):
        # Setas em vez dos pontos da paginacao: o gum do .deb e trocado pelo
        # do codigo da mesma versao com patches/gum, com o Go fixado.
        patch = (ROOT / 'patches/gum/0001-choose-setas.patch').read_text()
        self.assertIn('+			up = "▲"', patch)
        self.assertIn('+			down = "▼"', patch)
        self.assertIn('-		s.WriteString("  " + m.paginator.View())', patch)
        body = MKISO.split('build_gum() {')[1].split('\n}\n')[0]
        for name in ('GUM_COMMIT', 'GO_SHA256'):
            self.assertRegex(MKISO, name + r'="[0-9a-f]{40,64}"')
        self.assertIn('rev-parse HEAD) == "$GUM_COMMIT"', body)
        self.assertIn('git -C "$gsrc" apply "$here"/patches/gum/*.patch', body)
        self.assertIn('dpkg-divert --local --rename --add /usr/bin/gum', MKISO)
        self.assertRegex(MKISO, r'(?m)^fetch_debs\nbuild_gum$')
        self.assertIn('patches/', (ROOT / 'Dockerfile.fliperos').read_text())

    def test_gum_menu_sounds(self):
        # O cursor que anda e o Enter tocam os WAV de GUM_SOUND_MOVE e
        # GUM_SOUND_SELECT (aplay), no choose e no confirm. Sem CR: o git
        # apply do build recusaria.
        patch = (ROOT / 'patches/gum/0002-sons-do-menu.patch').read_bytes()
        self.assertNotIn(b'\r', patch)
        text = patch.decode()
        self.assertIn('+func Move() { play("GUM_SOUND_MOVE") }', text)
        self.assertIn('+func Select() { play("GUM_SOUND_SELECT") }', text)
        self.assertIn('+	cmd := exec.Command("aplay", "-q", file)', text)
        self.assertEqual(text.count('+			sfx.Select()'), 3)
        self.assertIn('+			sfx.Move() // FliperOS', text)
        self.assertIn('+				sfx.Move()', text)
        # A pasta dos sons e da pessoa (gravavel pelo Samba).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ('home/fliperos', 'etc/fliperos/mame', 'etc/modprobe.d', 'etc/sudoers.d', 'etc/profile.d',
                      'etc/systemd/system'):
                (root / d).mkdir(parents=True)
            (root / 'etc/passwd').write_text('fliperos:x:1000:1000::/home/fliperos:/bin/bash\n')
            subprocess.run(['bash', str(ROOT / 'fliperos-rootfs.sh'), str(root)], check=True,
                           capture_output=True, timeout=120)
            menu = root / 'opt/fliperos/sounds/menu'
            self.assertIn('select.wav', (menu / '_info.txt').read_text())
            self.assertEqual(menu.stat().st_uid, 1000)

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

    def tty1(self, installed, setup_codes, requests, *args):
        """Roda o config/fliperos-tty1 com sudo e fliperos-session falsos.
        setup_codes: status de cada "fliperos-setup --menu"; requests: o
        pedido gravado antes de cada um. Devolve as chamadas, em ordem."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'bin').mkdir()
            (tmp / 'etc').mkdir()
            if installed:
                (tmp / 'etc/installed').write_text('')
                (tmp / 'etc/firstboot').write_text('')
            log = tmp / 'calls'
            codes = ' '.join(str(c) for c in setup_codes)
            reqs = ' '.join(requests)
            (tmp / 'bin/sudo').write_text(
                '#!/bin/bash\necho "sudo $*" >> %s\n'
                'if [[ $2 == --menu ]]; then\n'
                '  n=$(grep -c -- --menu %s); codes=(%s); reqs=(%s)\n'
                '  echo "${reqs[n-1]}" > %s/request\n'
                '  exit "${codes[n-1]}"\nfi\n' % (log, log, codes, reqs, tmp))
            (tmp / 'bin/fliperos-session').write_text('#!/bin/bash\necho "session $*" >> %s\n' % log)
            for f in ('sudo', 'fliperos-session'):
                (tmp / 'bin' / f).chmod(0o755)
            env = dict(os.environ, PATH='%s:%s' % (tmp / 'bin', os.environ['PATH']),
                       FLIPEROS_ETC=str(tmp / 'etc'), FLIPEROS_BIN=str(tmp / 'bin'),
                       FLIPEROS_LAUNCH_REQUEST=str(tmp / 'request'))
            subprocess.run(['bash', str(ROOT / 'config/fliperos-tty1')] + list(args),
                           env=env, check=True, timeout=30)
            return [line.strip() for line in log.read_text().splitlines()]

    def test_tty1_flow_like_groovyarcade(self):
        """No disco: primeiro boot, launcher e depois o menu. Na midia: menu."""
        calls = self.tty1(True, [0], ['-'])
        self.assertEqual(calls, ['sudo setterm --blank 0 --powerdown 0',
                                 'sudo /usr/local/bin/fliperos-setup --first-boot',
                                 'session', 'sudo /usr/local/bin/fliperos-setup --menu'])
        calls = self.tty1(False, [0], ['-'])
        self.assertEqual(calls[1:], ['sudo /usr/local/bin/fliperos-setup --menu'])

    def test_menu_opens_the_requested_launcher_outside_the_setup(self):
        # O X aberto de dentro do setup (pty do sudo) falhava no gabinete com
        # "VT_ACTIVATE failed": o setup sai com 20 e o laco abre o launcher.
        calls = self.tty1(False, [20, 20, 0], ['lxde', 'default', '-'], '--menu')
        self.assertEqual(calls, ['sudo /usr/local/bin/fliperos-setup --menu', 'session lxde',
                                 'sudo /usr/local/bin/fliperos-setup --menu', 'session',
                                 'sudo /usr/local/bin/fliperos-setup --menu'])
        menu = (ROOT / 'config/fliperos-menu').read_text()
        self.assertIn('\n/opt/fliperos/bin/fliperos-tty1 --menu\nexec /usr/local/bin/fliperos-motd\n', menu)
        self.assertIn('/usr/local/bin/fliperos-menu', ROOTFS)
        self.assertNotIn('runuser', (ROOT / 'fliperos-setup/lib/launcher.sh').read_text())

    def test_both_shells_run_the_tty1_flow(self):
        # O shell do usuario e o zsh; o .bash_profile fica para quem voltar ao bash.
        for profile in ('.zprofile', '.bash_profile'):
            body = ROOTFS.split(profile + '" << \'EOF\'')[1].split('\nEOF')[0]
            self.assertIn('"$(tty)" == /dev/tty1', body, profile)
            self.assertIn('/opt/fliperos/bin/fliperos-tty1', body, profile)
        self.assertIn('fliperos-tty1', ROOTFS.split('for name in fliperos-session')[1].split('done')[0])

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


class PadKeysTests(unittest.TestCase):
    """Controle como teclado nos menus do setup (config/fliperos-padkeys)."""
    P = padkeys

    def test_buttons(self):
        P = self.P
        m = P.Mapper({})
        self.assertEqual(m.event(P.EV_KEY, 0x130, 1), [(P.KEY_ENTER, 1)])  # A
        self.assertEqual(m.event(P.EV_KEY, 0x131, 0), [(P.KEY_ESC, 0)])    # B solto
        self.assertEqual(m.event(P.EV_KEY, 0x120, 1), [(P.KEY_ENTER, 1)])  # botao 1 do encoder
        self.assertEqual(m.event(P.EV_KEY, 0x121, 1), [(P.KEY_ESC, 1)])    # botao 2
        self.assertEqual(m.event(P.EV_KEY, 0x13b, 1), [(P.KEY_ENTER, 1)])  # Start
        self.assertEqual(m.event(P.EV_KEY, 0x136, 1), [(P.KEY_PAGEUP, 1)])  # L
        self.assertEqual(m.event(P.EV_KEY, 0x221, 1), [(P.KEY_DOWN, 1)])   # direcional
        self.assertEqual(m.event(P.EV_KEY, 0x130, 2), [])  # repeticao do proprio controle
        # Botao 3 e X/Y: Espaco, que marca nas listas de marcar (ui_checklist).
        self.assertEqual(m.event(P.EV_KEY, 0x122, 1), [(P.KEY_SPACE, 1)])
        self.assertEqual(m.event(P.EV_KEY, 0x133, 1), [(P.KEY_SPACE, 1)])
        self.assertEqual(m.event(P.EV_KEY, 0x134, 0), [(P.KEY_SPACE, 0)])
        self.assertEqual(P.KEY_SPACE, 57)
        self.assertEqual(m.event(P.EV_KEY, 0x132, 1), [])  # C: sem tecla

    def test_digital_stick_of_an_arcade_encoder(self):
        # Encoder de fliperama (DragonRise, Xin-Mo): eixo 0..255, repouso 127/128.
        P = self.P
        m = P.Mapper({P.ABS_X: (0, 255), P.ABS_Y: (0, 255)})
        self.assertEqual(m.event(P.EV_ABS, P.ABS_Y, 0), [(P.KEY_UP, 1)])
        self.assertEqual(m.event(P.EV_ABS, P.ABS_Y, 0), [])
        self.assertEqual(m.event(P.EV_ABS, P.ABS_Y, 255), [(P.KEY_UP, 0), (P.KEY_DOWN, 1)])
        self.assertEqual(m.event(P.EV_ABS, P.ABS_Y, 128), [(P.KEY_DOWN, 0)])
        self.assertEqual(m.event(P.EV_ABS, P.ABS_X, 127), [])

    def test_analog_dead_zone_and_hat(self):
        P = self.P
        m = P.Mapper({P.ABS_X: (-32768, 32767)})
        self.assertEqual(m.event(P.EV_ABS, P.ABS_X, 12000), [])  # analogico gasto em repouso
        self.assertEqual(m.event(P.EV_ABS, P.ABS_X, 30000), [(P.KEY_RIGHT, 1)])
        self.assertEqual(m.event(P.EV_ABS, P.ABS_HAT0X, -1), [(P.KEY_LEFT, 1)])
        self.assertEqual(sorted(m.release()), sorted([(P.KEY_RIGHT, 0), (P.KEY_LEFT, 0)]))

    def test_repeat_and_two_sources_on_one_key(self):
        P = self.P
        sent = []
        keys = P.Keys(lambda k, v: sent.append((k, v)))
        keys.apply(P.KEY_DOWN, 1, 0.0)
        keys.apply(P.KEY_DOWN, 1, 0.0)  # hat e analogico juntos
        keys.tick(0.3)
        self.assertEqual(sent, [(P.KEY_DOWN, 1)])
        for t in (0.41, 0.45, 0.54):
            keys.tick(t)
        self.assertEqual(sent, [(P.KEY_DOWN, 1), (P.KEY_DOWN, 2), (P.KEY_DOWN, 2)])
        keys.apply(P.KEY_DOWN, 0, 0.6)
        self.assertEqual(sent[-1], (P.KEY_DOWN, 2))  # o outro ainda segura
        keys.apply(P.KEY_DOWN, 0, 0.6)
        self.assertEqual(sent[-1], (P.KEY_DOWN, 0))
        keys.tick(5)
        # Enter nao repete; soltar o que nao foi apertado nao emite nada.
        keys.apply(P.KEY_ENTER, 1, 6)
        keys.tick(9)
        keys.apply(P.KEY_ESC, 0, 9)
        self.assertEqual(sent[-1], (P.KEY_ENTER, 1))
        keys.release_all()
        self.assertEqual(sent[-1], (P.KEY_ENTER, 0))

    def test_only_controllers_are_read(self):
        P = self.P
        self.assertTrue(P.is_pad(b'Xbox pad', {0x130, 0x131, 0x13b}))
        self.assertTrue(P.is_pad(b'DragonRise Generic USB Joystick', {0x120, 0x121}))
        self.assertFalse(P.is_pad(b'AT keyboard', {1, 28, 30}))
        self.assertFalse(P.is_pad(b'mouse', {0x110, 0x111}))
        self.assertFalse(P.is_pad(b'GunCon2', {0x110, 0x130, 0x13b}))
        self.assertFalse(P.is_pad(P.NAME, {0x130}))

    def test_ioctl_numbers(self):
        # Os valores de linux/uinput.h e linux/input.h no x86_64.
        P = self.P
        self.assertEqual(P.UI_SET_EVBIT, 0x40045564)
        self.assertEqual(P.UI_SET_KEYBIT, 0x40045565)
        self.assertEqual(P.UI_DEV_SETUP, 0x405c5503)
        self.assertEqual(P.UI_DEV_CREATE, 0x5501)
        self.assertEqual(P.eviocgabs(0), 0x80184540)
        self.assertEqual(P.EVENT.size, 24)

    def test_on_only_while_the_setup_menu_is_up(self):
        self.assertIn('multi-user.target.wants/fliperos-padkeys.service', ROOTFS)
        setup = (ROOT / 'fliperos-setup/fliperos-setup').read_text()
        self.assertIn('padkeys_off', setup.split('restore_terminal() {')[1].split('}')[0])
        self.assertLess(setup.index('  ui_init\n'), setup.index('  padkeys_on\n'))


class RootfsRunTests(unittest.TestCase):
    """O fliperos-rootfs.sh de verdade numa raiz falsa."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        for d in ('home/fliperos', 'etc/xdg/openbox/LXDE', 'etc/modprobe.d', 'etc/sudoers.d',
                  'etc/profile.d', 'etc/systemd/system'):
            (root / d).mkdir(parents=True)
        (root / 'etc/xdg/openbox/LXDE/rc.xml').write_text(
            '<openbox_config>\n<theme>\n  <name>Clearlooks</name>\n</theme>\n'
            '<applications>\n<!-- exemplos -->\n</applications>\n</openbox_config>\n')
        (root / 'etc/passwd').write_text('fliperos:x:1000:1000::/home/fliperos:/bin/bash\n')
        subprocess.run(['bash', str(ROOT / 'fliperos-rootfs.sh'), str(root)], check=True,
                       capture_output=True, timeout=120)
        cls.root = root

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_openbox_rc_dracula_and_resolution_window(self):
        rc = (self.root / 'home/fliperos/.config/openbox/lxde-rc.xml').read_text()
        self.assertIn('<name>Dracula</name>', rc)
        self.assertIn('<application title="Screen Resolution"><maximized>yes</maximized></application>\n'
                      '</applications>', rc)

    def test_new_programs_are_installed(self):
        for path in ('usr/local/bin/fliperos-menu', 'opt/fliperos/bin/fliperos-padkeys',
                     'opt/fliperos/bin/fliperos-resolution', 'opt/fliperos/bin/fliperos-tty1'):
            self.assertTrue(os.access(self.root / path, os.X_OK), path)
        self.assertTrue((self.root / 'usr/local/share/applications/fliperos-resolution.desktop').is_file())
        self.assertTrue((self.root / 'usr/local/share/applications/org.gnome.Software.desktop').is_file())
        self.assertTrue((self.root / 'usr/share/glib-2.0/schemas/90_fliperos-software.gschema.override').is_file())
        self.assertTrue((self.root / 'home/fliperos/.config/alacritty/alacritty.toml').is_file())
        for path in ('opt/fliperos/bin/fliperos-calibrate', 'opt/fliperos/bin/fliperos-roms'):
            self.assertTrue(os.access(self.root / path, os.X_OK), path)
        self.assertEqual(os.readlink(self.root / 'opt/fliperos/roms'), '/home/fliperos/roms')
        self.assertTrue((self.root / 'etc/samba/smb.conf').is_file())
        self.assertTrue((self.root / 'home/fliperos/.config/flycast/emu.cfg').is_file())
        wants = self.root / 'etc/systemd/system/multi-user.target.wants/fliperos-padkeys.service'
        self.assertEqual(os.readlink(wants), '/etc/systemd/system/fliperos-padkeys.service')
        self.assertTrue(os.access(self.root / 'usr/local/bin/fliperos-motd', os.X_OK))
        self.assertFalse((self.root / 'etc/profile.d/fliperos.sh').exists())

    def test_networkmanager_writes_dns_and_manages_ethernet(self):
        # No gabinete o resolv.conf era o do container do build (192.168.65.7)
        # e o cabo de rede ficava sem IP.
        nm = self.root / 'etc/NetworkManager/conf.d'
        dns = (nm / '90-fliperos-dns.conf').read_text()
        self.assertIn('dns=default', dns)
        self.assertIn('rc-manager=file', dns)
        self.assertEqual((nm / '10-globally-managed-devices.conf').read_text(), '')
        squash = MKISO.split('create_squashfs() {')[1].split('mksquashfs')[0]
        self.assertIn('> "$CHROOT_DIR/etc/resolv.conf"', squash)

    def test_clock_is_synced_over_the_network(self):
        # O relogio da BIOS do gabinete estava 2 meses atrasado e o apt
        # recusava os repositorios.
        self.assertRegex(MKISO, r'\bsystemd-timesyncd\b')


class ResolutionAppTests(unittest.TestCase):
    """config/fliperos-resolution com xrandr e switchres falsos."""

    def run_app(self, saved):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'bin').mkdir()
            log = tmp / 'xrandr.log'
            (tmp / 'bin/xrandr').write_text(
                '#!/bin/bash\necho "$*" >> %s\n'
                'if [[ $1 == --query ]]; then\n'
                '  echo "Screen 0: minimum 320 x 200, current 640 x 480, maximum 16384 x 16384"\n'
                '  echo "DVI-D-1 disconnected (normal left inverted right x axis y axis)"\n'
                '  echo "VGA-1 connected primary 640x480+0+0 (normal left inverted right x axis y axis) 0mm x 0mm"\n'
                '  echo "   640x480i     59.99*+"\nfi\n' % log)
            (tmp / 'bin/switchres').write_text(
                '#!/bin/bash\necho "Switchres: Calculating best video mode for $1x$2@$3"\n'
                'echo "Switchres: Modeline \\"640x240_60 15.660000KHz 60.000000Hz\\" '
                '13.013460 640 666 727 831 240 242 245 261   -hsync -vsync"\n')
            for f in ('xrandr', 'switchres'):
                (tmp / 'bin' / f).chmod(0o755)
            (tmp / 'fliperos').mkdir()
            if saved:
                (tmp / 'fliperos/desktop-mode').write_text(saved)
            env = dict(os.environ, PATH='%s:%s' % (tmp / 'bin', os.environ['PATH']),
                       XDG_CONFIG_HOME=str(tmp), FLIPEROS_SETUP_LIB=str(ROOT / 'fliperos-setup/lib'),
                       FLIPEROS_LOG=str(tmp / 'log'))
            subprocess.run(['bash', str(ROOT / 'config/fliperos-resolution'), '--apply-saved'],
                           env=env, check=True, timeout=30)
            return log.read_text().splitlines() if log.exists() else []

    def test_saved_mode_is_calculated_by_switchres_and_set_by_xrandr(self):
        calls = self.run_app('640 240 60\n')
        self.assertEqual(calls[1:], [
            '--newmode fliperos-640x240@60 13.013460 640 666 727 831 240 242 245 261 -hsync -vsync',
            '--addmode VGA-1 fliperos-640x240@60',
            '--output VGA-1 --mode fliperos-640x240@60'])

    def test_nothing_saved_changes_nothing(self):
        self.assertEqual(self.run_app(None), [])

    def test_lxde_applies_it_and_the_menu_has_it(self):
        self.assertIn('fliperos-resolution --apply-saved', (ROOT / 'config/fliperos-lxde').read_text())
        entry = (ROOT / 'config/applications/fliperos-resolution.desktop').read_text()
        self.assertIn('Exec=alacritty --title "Screen Resolution" -e /opt/fliperos/bin/fliperos-resolution', entry)
        self.assertIn('Categories=Settings;', entry)


def apt_list():
    """Os pacotes do apt-get install principal do chroot."""
    block = MKISO.split('apt-get install -y --no-install-recommends \\\n')[1].split('\n\n')[0]
    return block.replace('\\', ' ').split()


class DesktopLogoutTests(unittest.TestCase):
    """O Desconectar do LXDE abre o menu do FliperOS no gum: a janela do
    lxsession-logout era ilegivel numa tela de baixa resolucao."""

    def test_every_logout_path_opens_the_gum_menu(self):
        logout = '/opt/fliperos/bin/fliperos-logout'
        # O quit_manager do lxsession, o item do menu (Logout do lxpanel) e o
        # botao do painel (o lxde-logout.desktop, com o mesmo ID do pacote).
        self.assertIn('quit_manager/command=%s\n' % logout,
                      (ROOT / 'config/lxde/lxsession/LXDE/desktop.conf').read_text())
        self.assertEqual((ROOT / 'config/lxde/lxpanel/LXDE/config').read_text(), '[Command]\nLogout=%s\n' % logout)
        entry = (ROOT / 'config/applications/lxde-logout.desktop').read_text()
        self.assertIn('\nExec=%s\n' % logout, entry)
        self.assertIn('id=lxde-logout.desktop', (ROOT / 'config/lxde/lxpanel/LXDE/panels/panel').read_text())
        self.assertIn(' fliperos-logout; do', ROOTFS)

    def test_logout_menu(self):
        # Fora do terminal ele se reabre no Alacritty em tela cheia; dentro,
        # o gum: voltar ao menu fecha o lxsession, os outros pelo sudo.
        script = (ROOT / 'config/fliperos-logout').read_text()
        self.assertIn('exec alacritty --class fliperos-logout -o \'window.startup_mode="Fullscreen"\'', script)
        for line in ('"Back to the FliperOS menu" "Reboot" "Power off" "Cancel"',
                     'kill -TERM "${_LXSESSION_PID:-0}"', 'Reboot) sudo -n /sbin/reboot ;;',
                     '"Power off") sudo -n /sbin/poweroff ;;', 'export GUM_SOUND_MOVE=$sounds/move.wav'):
            self.assertIn(line, script, line)


class DesktopTerminalTests(unittest.TestCase):
    """O lxterminal e o xterm nao desenhavam as bordas do Gum: o terminal do
    desktop e o Alacritty."""

    def test_only_alacritty_in_the_image(self):
        pkgs = apt_list()
        self.assertIn('alacritty', pkgs)
        for old in ('lxterminal', 'xterm', 'lxde'):
            self.assertNotIn(old, pkgs, old)
        # O metapacote lxde depende do lxterminal; os componentes vem a mao, e
        # o cabinet-update.sh protege os mesmos antes de tirar os terminais.
        update = (ROOT / 'tools/cabinet-update.sh').read_text()
        parts = update.split('lxde_parts=(')[1].split(')')[0].split()
        self.assertIn('lxde-core', parts)
        for part in parts:
            self.assertIn(part, pkgs, part)
        self.assertLess(update.index('apt-mark manual'), update.index('apt-get purge -y -q lxterminal xterm'))

    def test_steam_does_not_bring_xterm_back(self):
        # O steam-libs:i386 recomenda "xterm | x-terminal-emulator", e o
        # Alacritty (amd64) nao vale para um pacote i386: o xterm voltou na
        # ISO e virou o x-terminal-emulator.
        steam = MKISO.split('install_steam_chroot() {')[1].split('\n}\n')[0]
        self.assertIn('apt-get install -y steam-installer xterm- xterm:i386-', steam)

    def test_dracula_palette_of_the_setup(self):
        import tomllib
        conf = tomllib.loads((ROOT / 'config/lxde/alacritty/alacritty.toml').read_text())
        ui = (ROOT / 'fliperos-setup/lib/ui.sh').read_text()
        palette = ui.split('UI_PALETTE=(')[1].split(')')[0].split()
        order = ('black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white')
        colors = [conf['colors']['normal'][c] for c in order] + [conf['colors']['bright'][c] for c in order]
        # O 0 e o preto dos terminais do Dracula; o fundo e o primary.
        self.assertEqual([c.lstrip('#') for c in colors[1:]], palette[1:])
        self.assertEqual(conf['colors']['primary']['background'], '#' + palette[0])
        self.assertEqual(conf['font']['normal']['family'], 'DejaVu Sans Mono')
        self.assertEqual(conf['cursor']['style']['blinking'], 'Never')

    def test_desktop_uses_it(self):
        self.assertIn('id=Alacritty.desktop', (ROOT / 'config/lxde/lxpanel/LXDE/panels/panel').read_text())
        self.assertNotIn('lxterminal', (ROOT / 'config/lxde/lxpanel/LXDE/panels/panel').read_text())
        self.assertIn('terminal_manager/command=alacritty',
                      (ROOT / 'config/lxde/lxsession/LXDE/desktop.conf').read_text())
        session = (ROOT / 'config/fliperos-lxde').read_text()
        self.assertLess(session.index('export WINIT_X11_SCALE_FACTOR=1'), session.index('exec startlxde'))
        self.assertFalse((ROOT / 'config/lxde/lxterminal').exists())


class CalibrateTests(unittest.TestCase):
    """Setup > Joysticks: GunCon 2 e volante/pedais/analogico
    (config/fliperos-calibrate)."""
    C = calibrate

    def test_guncon_range_from_two_targets(self):
        # Tiros a 15% e 85% da tela leram 257 e 638 (faixa real 175..720).
        lo, hi = self.C.guncon_range(257, 638, 0.15, 0.85)
        self.assertAlmostEqual(lo, 175, delta=1)
        self.assertAlmostEqual(hi, 720, delta=1)
        self.assertEqual(self.C.median([300, 900, 310]), 310)

    def test_centered_axis_is_symmetric_around_rest(self):
        # Volante: repouso fora do meio do curso; os dois lados chegam ao fim.
        self.assertEqual(self.C.axis_calibration(100, 900, 520, 0, 1023), (140, 900, 8))
        # Pedal: repouso numa ponta, faixa vista e sem zona morta.
        self.assertEqual(self.C.axis_calibration(30, 990, 990, 0, 1023), (30, 990, 0))
        # Eixo que nao se mexeu fica como esta.
        self.assertIsNone(self.C.axis_calibration(500, 510, 505, 0, 1023))

    def test_conf_keeps_the_other_controllers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / 'calibration.conf')
            self.C.write_axes_conf(path, (0x046d, 0xc24f), 'G29', {0: (140, 900, 8)})
            self.C.write_axes_conf(path, (0x044f, 0xb66e), 'T300', {0: (0, 65535, 300), 2: (10, 1000, 0)})
            self.C.write_axes_conf(path, (0x046d, 0xc24f), 'G29', {0: (120, 910, 8)})
            conf = self.C.read_axes_conf(path)
            self.assertEqual(conf[(0x046d, 0xc24f)], {0: (120, 910, 8)})
            self.assertEqual(conf[(0x044f, 0xb66e)], {0: (0, 65535, 300), 2: (10, 1000, 0)})
            gun = Path(tmp) / 'guncon2.conf'
            self.C.write_guncon_conf(str(gun), (175, 720), (20, 240))
            self.assertIn('X_MIN=175\nX_MAX=720\nY_MIN=20\nY_MAX=240\n', gun.read_text())

    def test_ioctl_numbers(self):
        # linux/input.h no x86_64: EVIOCGID e EVIOCSABS(ABS_X).
        self.assertEqual(self.C.EVIOCGID, 0x80084502)
        self.assertEqual(self.C.eviocsabs(0), 0x401845c0)
        self.assertEqual(self.C.eviocgabs(1), 0x80184541)

    def test_wired_into_the_setup_and_udev(self):
        rules = (ROOT / 'config/99-fliperos-input.rules').read_text()
        self.assertIn('ENV{ID_INPUT_JOYSTICK}=="1"', rules)
        self.assertIn('/opt/fliperos/bin/fliperos-calibrate apply $env{DEVNAME}', rules)
        menu = (ROOT / 'fliperos-setup/screens/setup-menu.sh').read_text()
        self.assertIn('joysticks|Joysticks (GunCon 2, wheel, LPT)', menu)
        screens = (ROOT / 'fliperos-setup/screens/joysticks.sh').read_text()
        for item in ('guncon|Calibrate GunCon 2', 'axes|Calibrate wheel', 'lpt|LPT joysticks'):
            self.assertIn(item, screens)


class RomFoldersTests(unittest.TestCase):
    """~/roms com uma pasta por emulador e por core do RetroArch."""

    def test_one_folder_per_emulator_and_core(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            info = tmp / 'info'
            info.mkdir()
            (info / 'snes9x_libretro.info').write_text(
                'display_name = "Nintendo - SNES / SFC (Snes9x - Current)"\n'
                'supported_extensions = "smc|sfc|swc|fig|bs|st"\n')
            (info / 'mpv_libretro.info').write_text('display_name = "Video (MPV)"\n')
            env = dict(os.environ, FLIPEROS_ROMS=str(tmp / 'roms'), FLIPEROS_CORE_INFO=str(info))
            for _ in range(2):  # a segunda rodada nao muda nada
                subprocess.run(['bash', str(ROOT / 'config/fliperos-roms')], env=env, check=True)
            roms = tmp / 'roms'
            for emu in ('mame', 'ps2', 'dreamcast', 'naomi', 'naomi2', 'atomiswave', 'model3', 'dolphin',
                        'openbor/Paks', 'hypseus', 'fightcade', 'fightcade/fbneo', 'fightcade/flycast',
                        'fightcade/snes9x', 'fightcade/fc1'):
                self.assertTrue((roms / emu / '_info.txt').is_file(), emu)
            self.assertEqual((roms / 'retroarch/snes9x/_info.txt').read_text(),
                             'RetroArch, core snes9x: Nintendo - SNES / SFC (Snes9x - Current) '
                             '(.smc .sfc .swc .fig .bs .st)\n')
            self.assertEqual((roms / 'retroarch/mpv/_info.txt').read_text(), 'RetroArch, core mpv: Video (MPV)\n')

    def test_fightcade_reads_its_roms_from_the_roms_folder(self):
        # O Fightcade procura as ROMs dentro da pasta de cada emulador dele:
        # elas viram links para ~/roms/fightcade, e o que ja estava la vai junto.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fc = tmp / 'fightcade'
            for emu in ('fbneo', 'flycast', 'snes9x', 'ggpofba'):
                (fc / 'emulator' / emu / 'ROMs').mkdir(parents=True)
            (fc / 'emulator/fbneo/ROMs/sf2.zip').write_text('rom')
            env = dict(os.environ, HOME=str(tmp), FLIPEROS_CORE_INFO=str(tmp / 'nada'), FIGHTCADE_DIR=str(fc))
            for _ in range(2):
                subprocess.run(['bash', str(ROOT / 'config/fliperos-roms')], env=env, check=True)
            for emu, folder in (('fbneo', 'fbneo'), ('flycast', 'flycast'), ('snes9x', 'snes9x'), ('ggpofba', 'fc1')):
                link = fc / 'emulator' / emu / 'ROMs'
                self.assertTrue(link.is_symlink(), emu)
                self.assertEqual(os.readlink(link), str(tmp / 'roms/fightcade' / folder))
            self.assertEqual((tmp / 'roms/fightcade/fbneo/sf2.zip').read_text(), 'rom')
            # Sem o Fightcade instalado, as pastas existem e nada mais.
            env['FIGHTCADE_DIR'] = str(tmp / 'nenhum')
            subprocess.run(['bash', str(ROOT / 'config/fliperos-roms')], env=env, check=True)
            self.assertFalse((tmp / 'nenhum').exists())

    def test_bios_media_and_config_folders(self):
        # Ao lado de ~/roms: ~/bios (com as subpastas dos emuladores), ~/media
        # (um tipo por pasta) e ~/config (links para o que ja existe).
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            for d in ('.config/retroarch', '.config/flycast', 'etc/mame', 'ES-DE'):
                (home / d).mkdir(parents=True)
            # Uma pasta bios do PCSX2 com a BIOS dentro vira link para ~/bios/ps2.
            (home / '.config/PCSX2/bios').mkdir(parents=True)
            (home / '.config/PCSX2/bios/scph39001.bin').write_text('bios')
            env = dict(os.environ, HOME=str(home), FLIPEROS_CORE_INFO=str(home / 'nada'),
                       FLIPEROS_ETC=str(home / 'etc'))
            for _ in range(2):
                subprocess.run(['bash', str(ROOT / 'config/fliperos-roms')], env=env, check=True)
            for d in ('bios', 'bios/dc', 'bios/ps2', 'bios/mame', 'media', 'media/snap', 'media/preview',
                      'media/logo', 'media/box', 'media/marquee', 'media/texto', 'config'):
                self.assertTrue((home / d / '_info.txt').is_file(), d)
            self.assertTrue((home / '.config/PCSX2/bios').is_symlink())
            self.assertEqual((home / 'bios/ps2/scph39001.bin').read_text(), 'bios')
            links = {p.name: os.readlink(p) for p in (home / 'config').iterdir() if p.is_symlink()}
            # So o que existe (o OpenBOR, o Dolphin... ainda nao criaram a sua).
            self.assertEqual(links, {'retroarch': str(home / '.config/retroarch'),
                                     'flycast': str(home / '.config/flycast'),
                                     'pcsx2': str(home / '.config/PCSX2'), 'groovymame': str(home / 'etc/mame'),
                                     'es-de': str(home / 'ES-DE')})
            # O programa saiu: o link sem destino vai embora no login seguinte.
            (home / 'ES-DE').rmdir()
            subprocess.run(['bash', str(ROOT / 'config/fliperos-roms')], env=env, check=True)
            self.assertFalse((home / 'config/es-de').is_symlink())

    def test_emulators_point_there(self):
        self.assertIn('rgui_browser_directory = "/home/fliperos/roms"', (ROOT / 'config/retroarch.cfg').read_text())
        self.assertIn('system_directory = "/home/fliperos/bios"', (ROOT / 'config/retroarch.cfg').read_text())
        self.assertIn('rompath /home/fliperos/roms/mame', (ROOT / 'config/mame.ini').read_text())
        flycast = (ROOT / 'config/flycast-emu.cfg').read_text()
        # Os discos do Dreamcast e os arcades (uma pasta por sistema).
        self.assertIn('Dreamcast.ContentPath = /home/fliperos/roms/dreamcast;/home/fliperos/roms/naomi;'
                      '/home/fliperos/roms/naomi2;/home/fliperos/roms/atomiswave\n', flycast)
        self.assertIn('Dreamcast.BiosPath = /home/fliperos/bios/dc', flycast)
        self.assertIn('FLYCAST_BIOS_PATH=', (ROOT / 'config/fliperos-x11-run').read_text())
        smb = (ROOT / 'config/smb.conf').read_text()
        for share in ('roms', 'bios', 'media', 'config'):
            self.assertIn('[%s]\n' % share, smb)
            self.assertIn('path = /home/fliperos/%s\n' % share, smb)
        self.assertIn('wide links = yes', smb)

    def test_flycast_player_2_has_a_controller(self):
        cfg = (ROOT / 'config/flycast-emu.cfg').read_text()
        self.assertIn('device2 = 0\n', cfg)
        self.assertIn('maple_sdl_joystick_1 = 1\n', cfg)

    def test_flycast_linear_interpolation_is_off_by_default(self):
        # O padrao do Flycast (yes) borra a imagem ao leva-la para o modo do
        # tubo. Desligada de fabrica; num emu.cfg de antes, so se a opcao
        # ainda nao esta gravada (gravada, a escolha e da pessoa).
        cfg = (ROOT / 'config/flycast-emu.cfg').read_text()
        self.assertIn('[config]\n', cfg)
        self.assertIn('rend.LinearInterpolation = no\n', cfg.split('[input]')[0])
        for before, value in (
                (None, 'no'),
                ('[config]\nDreamcast.BiosPath = /x\n\n[input]\ndevice1 = 0\n', 'no'),
                ('[config]\nrend.LinearInterpolation = yes\nrend.Resolution = 480\n\n[input]\ndevice1 = 0\n', 'yes')):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for d in ('home/fliperos/.config/flycast', 'etc/modprobe.d', 'etc/sudoers.d', 'etc/profile.d',
                          'etc/systemd/system'):
                    (root / d).mkdir(parents=True)
                (root / 'etc/passwd').write_text('fliperos:x:1000:1000::/home/fliperos:/bin/bash\n')
                emu = root / 'home/fliperos/.config/flycast/emu.cfg'
                if before is not None:
                    emu.write_text(before)
                for _ in range(2):
                    subprocess.run(['bash', str(ROOT / 'fliperos-rootfs.sh'), str(root)], check=True,
                                   capture_output=True, timeout=120)
                text = emu.read_text()
                self.assertEqual(text.count('rend.LinearInterpolation'), 1, text)
                # Na secao [config], que e onde o Flycast a le.
                config = text.split('[config]\n')[1].split('[input]')[0]
                self.assertIn('rend.LinearInterpolation = %s\n' % value, config, text)

    def test_old_roms_move_to_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ('home/fliperos/roms/mame', 'opt/fliperos/roms/mame', 'opt/fliperos/roms/ps2',
                      'etc/modprobe.d', 'etc/sudoers.d', 'etc/profile.d', 'etc/systemd/system'):
                (root / d).mkdir(parents=True)
            (root / 'etc/passwd').write_text('fliperos:x:1000:1000::/home/fliperos:/bin/bash\n')
            (root / 'opt/fliperos/roms/mame/sf2.zip').write_text('rom')
            (root / 'opt/fliperos/roms/ps2/game.iso').write_text('iso')
            # A BIOS de /opt/fliperos/bios vai junto para ~/bios.
            (root / 'opt/fliperos/bios').mkdir(parents=True)
            (root / 'opt/fliperos/bios/scph5501.bin').write_text('bios')
            # Num mame.ini/ui.ini de antes, as pastas de ~/bios e ~/media entram
            # na lista que ja existe; as do Scraper antigo saem.
            mame = root / 'etc/fliperos/mame'
            mame.mkdir(parents=True)
            # As relativas do -createconfig puro (homepath ".", cfg_directory
            # "cfg") enchiam a home: saem, e sem absoluta vale a do config/.
            (mame / 'mame.ini').write_text(
                'homepath                  .\n'
                'rompath                   roms;/home/fliperos/roms/mame;/mnt/pendrive\n'
                'snapshot_directory        snap;$HOME/.mame/snap;/home/fliperos/.mame/scraped/mame/screenshots\n'
                'samplepath                /home/fliperos/roms/mame/samples\n'
                'cfg_directory             cfg\n'
                'nvram_directory           /mnt/nvram\n'
                'plugin                    \n')
            (mame / 'ui.ini').write_text('covers_directory          /home/fliperos/.mame/scraped/mame/covers;covers\n'
                                         'logos_directory           logo\nui_path                   ui\n')
            # O cfg/nvram que esse mame.ini gravou na home: vale o mais novo.
            home = root / 'home/fliperos'
            for d in ('cfg', '.mame/cfg'):
                (home / d).mkdir(parents=True)
            (home / '.mame/cfg/mvsc.cfg').write_text('velho')
            (home / '.mame/cfg/sf2.cfg').write_text('so no .mame')
            (home / 'cfg/mvsc.cfg').write_text('novo')
            (home / 'cfg/default.cfg').write_text('so na home')
            os.utime(home / '.mame/cfg/mvsc.cfg', (1000, 1000))
            # Um emu.cfg do Flycast de antes ganha a pasta da BIOS.
            (root / 'home/fliperos/.config/flycast').mkdir(parents=True)
            (root / 'home/fliperos/.config/flycast/emu.cfg').write_text(
                '[config]\nDreamcast.ContentPath = /home/fliperos/roms/dreamcast;/mnt/dc\nrend.Resolution = 480\n')
            for _ in range(2):
                subprocess.run(['bash', str(ROOT / 'fliperos-rootfs.sh'), str(root)], check=True,
                               capture_output=True, timeout=120)
            self.assertEqual((root / 'home/fliperos/roms/mame/sf2.zip').read_text(), 'rom')
            self.assertEqual((root / 'home/fliperos/roms/ps2/game.iso').read_text(), 'iso')
            self.assertEqual(os.readlink(root / 'opt/fliperos/roms'), '/home/fliperos/roms')
            self.assertEqual((root / 'home/fliperos/bios/scph5501.bin').read_text(), 'bios')
            self.assertEqual(os.readlink(root / 'opt/fliperos/bios'), '/home/fliperos/bios')
            ini = (mame / 'mame.ini').read_text()
            self.assertIn('homepath                  $HOME/.mame\n', ini)
            self.assertIn('rompath                   /home/fliperos/roms/mame;/mnt/pendrive;/home/fliperos/bios/mame\n',
                          ini)
            self.assertIn('snapshot_directory        $HOME/.mame/snap;/home/fliperos/media/snap/arcade\n', ini)
            self.assertIn('samplepath                /home/fliperos/roms/mame/samples\n', ini)
            self.assertIn('cfg_directory             $HOME/.mame/cfg\n', ini)
            # Uma absoluta escolhida fica; o que nao e pasta tambem.
            self.assertIn('nvram_directory           /mnt/nvram\n', ini)
            self.assertIn('plugin                    \n', ini)
            ui = (mame / 'ui.ini').read_text()
            self.assertIn('covers_directory          /home/fliperos/media/box/arcade\n', ui)
            self.assertIn('logos_directory           /home/fliperos/media/logo/arcade\n', ui)
            self.assertIn('marquees_directory        /home/fliperos/media/marquee/arcade\n', ui)
            self.assertIn('ui_path                   $HOME/.mame/ui\n', ui)
            self.assertEqual(ui.count('covers_directory'), 1)
            self.assertFalse((home / 'cfg').exists())
            self.assertEqual((home / '.mame/cfg/mvsc.cfg').read_text(), 'novo')
            self.assertEqual((home / '.mame/cfg/sf2.cfg').read_text(), 'so no .mame')
            self.assertEqual((home / '.mame/cfg/default.cfg').read_text(), 'so na home')
            flycast = (root / 'home/fliperos/.config/flycast/emu.cfg').read_text()
            self.assertIn('Dreamcast.BiosPath = /home/fliperos/bios/dc', flycast)
            # ...e as pastas dos arcades na lista de jogos, junto das que tinha.
            self.assertIn('Dreamcast.ContentPath = /home/fliperos/roms/dreamcast;/mnt/dc;/home/fliperos/roms/naomi;'
                          '/home/fliperos/roms/naomi2;/home/fliperos/roms/atomiswave\n', flycast)


class GroovyMameTests(unittest.TestCase):
    """O release oficial do GroovyMAME e o atalho config/fliperos-groovymame."""

    def run_wrapper(self, *args, display=':0'):
        # O GroovyMAME e o fliperos-x11-run falsos so imprimem os argumentos.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'ini').mkdir()
            fake = tmp / 'groovymame'
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
            fake.chmod(0o755)
            x11run = tmp / 'fliperos-x11-run'
            x11run.write_text('#!/bin/sh\necho x11-run ${FLIPEROS_SWITCHRES_OPTS:-}\nprintf "%s\\n" "$@"\n')
            x11run.chmod(0o755)
            env = dict(os.environ, FLIPEROS_GROOVYMAME_BIN=str(fake), FLIPEROS_MAME_INI_DIR=str(tmp / 'ini'),
                       FLIPEROS_X11_RUN=str(x11run))
            env.pop('DISPLAY', None)
            if display:
                env['DISPLAY'] = display
            out = subprocess.run(['bash', str(ROOT / 'config/fliperos-groovymame'), *args], env=env,
                                 capture_output=True, text=True, timeout=60, check=True).stdout
            return out.split('\n')[:-1], str(tmp / 'ini')

    def test_wrapper_opens_in_its_own_x(self):
        # No console, o GroovyMAME se abre num Xorg so para ele, onde o
        # Switchres troca o modo pelo XRandR (no KMS o SDL ficava no tamanho do
        # modo do boot). Comandos sem tela rodam direto, sem subir o X.
        wrapper = str(ROOT / 'config/fliperos-groovymame')
        self.assertEqual(self.run_wrapper('mvsc', display=None)[0], ['x11-run', wrapper, 'mvsc'])
        # A interface: o X ja no modo dela, sem entrelacar.
        self.assertEqual(self.run_wrapper(display=None)[0], ['x11-run --interlace 0', '--mode', '640x480@30', wrapper])
        for args in (('-listclones',), ('-listfull', 'mvsc'),('-verifyroms', 'mvsc'), ('-showconfig',),
                     ('-createconfig',), ('-version',), ('-validate',), ('-romident', 'x.zip'), ('-help',)):
            out, ini = self.run_wrapper(*args, display=None)
            self.assertEqual(out, ['-inipath', ini, *args], args)

    def test_groovymame_switches_modes_in_x(self):
        # modesetting 1: o Switchres troca o modo de cada jogo (no X, pelo
        # XRandR; no gabinete, SR-1_384x224@59.64 no MvC). Chamado de dentro do
        # fliperos-kms-run, o X nao herda o kmsdrm do SDL.
        self.assertIn('\nmodesetting 1\n', (ROOT / 'config/mame.ini').read_text())
        self.assertNotIn('SDL_KMSDRM_REQUIRE_DRM_MASTER', (ROOT / 'config/fliperos-kms-run').read_text())
        x11 = (ROOT / 'config/fliperos-x11-run').read_text()
        self.assertIn('\nexport SDL_VIDEODRIVER=x11\n', x11)
        self.assertLess(x11.index('SDL_VIDEODRIVER=x11'), x11.index('exec xinit'))
        launcher = (ROOT / 'config/fliperos-launch').read_text()
        self.assertIn('groovymame) label=GroovyMAME run=("$x11" groovymame) ;;', launcher)

    def test_wrapper_inipath(self):
        # O mame.ini do sistema (o padrao do release, ".;ini", depende da pasta
        # de onde se abre); um -inipath na linha de comando vale mais.
        args, ini = self.run_wrapper('mvsc')
        self.assertEqual(args, ['-inipath', ini, 'mvsc'])
        # Sem jogo (a interface): sem o autosync, que no jogo escolhido nela
        # deixava a velocidade com um vblank quebrado (acelerado no gabinete).
        args, ini = self.run_wrapper()
        self.assertEqual(args, ['-inipath', ini, '-noautosync', '-waitvsync', '-nointerlace'])
        self.assertEqual(self.run_wrapper('-inipath', '/x', 'mvsc')[0], ['-inipath', '/x', 'mvsc'])
        self.assertIn('/usr/local/libexec/groovymame', (ROOT / 'config/fliperos-groovymame').read_text())

    def test_full_mame_ini_like_groovyarcade(self):
        # O -createconfig do proprio GroovyMAME (todas as opcoes da versao) com
        # as do config/mame.ini por cima, na linha de cada uma.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fake = tmp / 'groovymame'
            fake.write_text('#!/bin/bash\n[[ " $* " == *" -createconfig "* ]] || exit 1\n'
                            'printf "#\\n# CORE SEARCH PATH OPTIONS\\n#\\nhomepath                  .\\n'
                            'rompath                   roms\\ninipath                   .;ini\\n'
                            'switchres                 1\\nmodesetting               0\\nmonitor                   generic_15\\n'
                            'lowlatency                0\\nfilter                    1\\n" > mame.ini\n')
            fake.chmod(0o755)
            (tmp / 'mame').mkdir()
            out = tmp / 'mame' / 'mame.ini'
            out.write_text((ROOT / 'config/mame.ini').read_text())
            subprocess.run(['bash', str(ROOT / 'config/fliperos-mame-ini'), str(out), str(out)],
                           env=dict(os.environ, FLIPEROS_GROOVYMAME_BIN=str(fake)),
                           capture_output=True, text=True, timeout=60, check=True)
            text = out.read_text()
            self.assertTrue(text.startswith('#\n# CORE SEARCH PATH OPTIONS\n#\n'))
            for line in ('homepath                  $HOME/.mame',
                         'rompath                   /home/fliperos/roms/mame;/home/fliperos/bios/mame',
                         'inipath                   %s' % out.parent, 'monitor                   arcade_15',
                         'modesetting               1', 'lowlatency                1', 'filter                    1',
                         'plugin                    hiscore', 'uifont                    default'):
                self.assertIn(line + '\n', text, line)
            self.assertEqual(text.count('\nrompath '), 1)
        self.assertIn('fliperos-mame-ini" "$root/opt/fliperos/bin/fliperos-mame-ini', ROOTFS)
        body = MKISO.split('install_groovymame_chroot() {')[1].split('\n}\n')[0]
        self.assertIn('fliperos-mame-ini /etc/fliperos/mame/mame.ini /etc/fliperos/mame/mame.ini', body)

    def test_old_aspect_option_is_removed(self):
        # A opcao GroovyMAME 4:3 saiu: numa instalacao anterior vao embora o
        # gerador, os .ini por jogo e a chave do fliperos.conf.
        self.assertFalse((ROOT / 'config/fliperos-mame-aspect').exists())
        for path in (ROOT / 'fliperos-setup/screens/video-setup.sh', ROOT / 'tools/cabinet-update.sh',
                     ROOT / 'config/fliperos-groovymame'):
            self.assertNotIn('mame_crt_aspect', path.read_text(), path)
            self.assertNotIn('fliperos-mame-aspect', path.read_text(), path)
        self.assertNotIn('fliperos-mame-aspect', MKISO)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ('home/fliperos', 'etc/fliperos/mame/aspect', 'opt/fliperos/bin', 'etc/modprobe.d',
                      'etc/sudoers.d', 'etc/profile.d', 'etc/systemd/system'):
                (root / d).mkdir(parents=True)
            (root / 'etc/passwd').write_text('fliperos:x:1000:1000::/home/fliperos:/bin/bash\n')
            (root / 'etc/fliperos/mame/aspect/mvsc.ini').write_text('aspect 320:224\n')
            (root / 'opt/fliperos/bin/fliperos-mame-aspect').write_text('#!/bin/sh\n')
            (root / 'etc/fliperos/fliperos.conf').write_text('monitor=arcade_15\nmame_crt_aspect=yes\n')
            subprocess.run(['bash', str(ROOT / 'fliperos-rootfs.sh'), str(root)], check=True,
                           capture_output=True, timeout=120)
            self.assertFalse((root / 'etc/fliperos/mame/aspect').exists())
            self.assertFalse((root / 'opt/fliperos/bin/fliperos-mame-aspect').exists())
            self.assertEqual((root / 'etc/fliperos/fliperos.conf').read_text(), 'monitor=arcade_15\n')

    def test_release_is_pinned_and_installed_behind_the_wrapper(self):
        body = MKISO.split('install_groovymame_chroot() {')[1].split('\n}\n')[0]
        self.assertRegex(MKISO, r'GROOVYMAME_SHA256="[0-9a-f]{64}"')
        self.assertIn('releases/download/${GROOVYMAME_TAG}/${GROOVYMAME_FILE}', body)
        self.assertIn('sha256sum -c', body)
        self.assertIn('/usr/local/libexec/groovymame', body)
        self.assertIn('libqt6widgets6t64', body)
        self.assertNotIn('make ', body)
        self.assertRegex(MKISO, r'(?m)^install_groovymame_chroot$')

    def ini(self, name):
        values = {}
        for line in (ROOT / 'config' / name).read_text().splitlines():
            if line.strip() and not line.startswith('#'):
                key, value = line.split(None, 1)
                self.assertNotIn(key, values, 'chave repetida: ' + key)
                values[key] = value
        return values

    def test_groovyarcade_options(self):
        # As do -createconfig do gasetup (core/configs/groovymame), mais a
        # latencia do Setup.
        ini = self.ini('mame.ini')
        # A fonte e a do MAME: a uismall.bdf do GroovyArcade ficava pequena
        # demais no gabinete.
        for key, value in (('plugin', 'hiscore'), ('skip_gameinfo', '1'), ('uifont', 'default'),
                           ('video', 'opengl'), ('lowlatency', '1'), ('switchres_ini', '1'), ('modesetting', '1'),
                           ('sound', 'sdl'), ('aspect', '4:3'), ('autoframedelay', '1'), ('framedelay', '0')):
            self.assertEqual(ini[key], value, key)
        self.assertEqual(ini['homepath'], '$HOME/.mame')
        self.assertEqual(ini['cfg_directory'], '$HOME/.mame/cfg')
        self.assertEqual(ini['rompath'], '/home/fliperos/roms/mame;/home/fliperos/bios/mame')
        self.assertEqual(ini['snapshot_directory'], '$HOME/.mame/snap;/home/fliperos/media/snap/arcade')
        ui = self.ini('mame-ui.ini')
        for key, kind in (('covers_directory', 'box'), ('flyers_directory', 'box'),
                          ('marquees_directory', 'marquee'), ('logos_directory', 'logo')):
            self.assertEqual(ui[key], '/home/fliperos/media/%s/arcade' % kind, key)
        # 20 e o minimo do MAME (20-40): o 19 do GroovyArcade e descartado.
        self.assertEqual((ui['font_rows'], ui['infos_text_size']), ('20', '1.00'))

    def test_support_files_come_from_the_tag(self):
        # As pastas do mame.ini existem na imagem: o codigo da mesma tag.
        body = MKISO.split('install_groovymame_chroot() {')[1].split('\n}\n')[0]
        self.assertRegex(MKISO, r'GROOVYMAME_COMMIT="[0-9a-f]{40}"')
        self.assertIn('rev-parse HEAD) == "$GROOVYMAME_COMMIT"', body)
        self.assertIn('"$gm_src/uismall.bdf" "$gm_share/fonts/uismall.bdf"', body)
        ini = self.ini('mame.ini')
        for key in ('pluginspath', 'fontpath', 'bgfx_path', 'hashpath', 'languagepath', 'artpath', 'ctrlrpath'):
            shared = [p for p in ini[key].split(';') if p.startswith('/usr/local/share/groovymame/')]
            self.assertEqual(len(shared), 1, key)
            self.assertIn(shared[0].rsplit('/', 1)[1], body, key)

    def test_rootfs_merges_new_keys_into_an_older_mame_ini(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ('home/fliperos/cfg', 'home/fliperos/snap', 'etc/fliperos/mame', 'etc/modprobe.d',
                      'etc/sudoers.d', 'etc/profile.d', 'etc/systemd/system'):
                (root / d).mkdir(parents=True)
            (root / 'etc/passwd').write_text('fliperos:x:1000:1000::/home/fliperos:/bin/bash\n')
            (root / 'home/fliperos/cfg/default.cfg').write_text('<mameconfig/>')
            mame = root / 'etc/fliperos/mame/mame.ini'
            # O modesetting 0 de antes (o GroovyMAME no KMS) passa para o 1.
            mame.write_text('monitor generic_15\nlowlatency 0\nmodesetting               0\n')
            (root / 'etc/fliperos/mame/ui.ini').write_text('font_rows 30\n')
            for _ in range(2):
                subprocess.run(['bash', str(ROOT / 'fliperos-rootfs.sh'), str(root)], check=True,
                               capture_output=True, timeout=120)
            text = mame.read_text()
            self.assertTrue(text.startswith('monitor generic_15\nlowlatency 0\n'))
            self.assertEqual(text.count('\nplugin '), 1)
            self.assertRegex(text, r'(?m)^modesetting +1$')
            self.assertEqual(text.count('modesetting '), 1)
            self.assertNotRegex(text, r'(?m)^monitor +arcade_15$')
            ui = (root / 'etc/fliperos/mame/ui.ini').read_text()
            self.assertTrue(ui.startswith('font_rows 30\n'))
            self.assertRegex(ui, r'(?m)^ui_bg_color +ef282a36$')
            # O que o binario antigo gravava na home vai para ~/.mame.
            self.assertTrue((root / 'home/fliperos/.mame/cfg/default.cfg').is_file())
            self.assertTrue((root / 'home/fliperos/snap').is_dir())

    def test_rootfs_moves_the_old_binary_and_installs_the_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ('home/fliperos', 'usr/local/bin', 'etc/modprobe.d', 'etc/sudoers.d', 'etc/profile.d',
                      'etc/systemd/system'):
                (root / d).mkdir(parents=True)
            (root / 'etc/passwd').write_text('fliperos:x:1000:1000::/home/fliperos:/bin/bash\n')
            (root / 'usr/local/bin/groovymame').write_bytes(b'\x7fELF binario compilado')
            for _ in range(2):
                subprocess.run(['bash', str(ROOT / 'fliperos-rootfs.sh'), str(root)], check=True,
                               capture_output=True, timeout=120)
            self.assertEqual((root / 'usr/local/libexec/groovymame').read_bytes(), b'\x7fELF binario compilado')
            self.assertEqual((root / 'usr/local/bin/groovymame').read_text(),
                             (ROOT / 'config/fliperos-groovymame').read_text())


class RomCleanTests(unittest.TestCase):
    """config/fliperos-romclean: os jogos que vao para a pasta do MAME."""

    @staticmethod
    def machine(name, desc, attrs='', coins=1, players=2, controls=(('joy', 6),), year='1996', status='good',
                extra=''):
        ctrl = ''.join('<control type="%s" buttons="%d"/>' % c for c in controls)
        inp = ('<input players="%d" coins="%d">%s</input>' % (players, coins, ctrl)) if coins is not None else ''
        drv = '<driver status="%s"/>' % status if status else ''
        return ('<machine name="%s" %s><description>%s</description><year>%s</year>%s%s%s</machine>\n'
                % (name, attrs, desc, year, extra, inp, drv))

    def setUp(self):
        m = self.machine
        raster = '<display type="raster" rotate="0" width="320" height="224"/>'
        self.XML = '<?xml version="1.0"?>\n<mame build="0.289">\n' + ''.join([
            m('neogeo', 'Neo-Geo', 'isbios="yes"', coins=None, status=''),
            m('pgm', 'PGM', 'isbios="yes"', coins=None, status=''),
            m('mslug', 'Metal Slug - Super Vehicle-001', 'romof="neogeo"', controls=(('joy', 4),), extra=raster),
            m('mslugb', 'Metal Slug (bootleg)', 'cloneof="mslug" romof="mslug"', extra=raster),
            m('1942', '1942 (Revision B)', controls=(('joy', 2),), year='1984',
              extra='<display type="raster" rotate="270"/>'),
            m('asteroid', 'Asteroids (rev 4)', controls=(), year='1979', extra='<display type="vector" rotate="0"/>'),
            m('coh1000c', 'ZN-1', 'isbios="yes"', coins=None, status='',
              extra='<chip type="cpu" name="Sony CXD8530CQ"/>'),
            m('sfex', 'Street Fighter EX (USA 961219)', 'romof="coh1000c"',
              extra='<chip type="cpu" name="Sony CXD8530CQ"/>' + raster),
            m('tekken3', 'Tekken 3 (Japan, TET1/VER.E1)', controls=(('joy', 4),), status='imperfect',
              extra='<chip type="cpu" name="Sony CXD8661R"/>' + raster),
            m('kpython2', 'Python 2', status='preliminary', extra='<chip type="cpu" name="Sony Playstation 2 IOP"/>'),
            m('broken', 'Broken', status='preliminary'),
            m('wbml', 'Wonder Boy in Monster Land (Japan New Ver.)', status='preliminary', year='1987'),
            m('wbmlb', 'Wonder Boy in Monster Land (English bootleg set 1)', 'cloneof="wbml" romof="wbml"',
              year='1987'),
            m('qsound_hle', 'QSound', 'isdevice="yes" runnable="no"', coins=None, status=''),
            m('sfa2', 'Street Fighter Alpha 2 (Europe 960229)', extra='<device_ref name="qsound_hle"/>' + raster),
            m('pinball', 'Pinball', 'ismechanical="yes"', controls=()),
            m('kinst', 'Killer Instinct (v1.5d)', year='1994', extra='<disk name="kinst"/>' + raster),
            m('cent', 'Centipede (revision 4)', controls=(('trackball', 1),), year='1980'),
            m('area51', 'Area 51 (R3000)', controls=(('lightgun', 1),), year='1995'),
            m('nes', 'Nintendo Entertainment System', coins=0, year='1985'),
            m('mvsc', 'Marvel Vs. Capcom (Europe 980123)', year='1998', extra=raster),
            m('mvscu', 'Marvel Vs. Capcom (USA 980123)', 'cloneof="mvsc" romof="mvsc"', year='1998', extra=raster),
            m('mvscj', 'Marvel Vs. Capcom (Japan 980123)', 'cloneof="mvsc" romof="mvsc"', year='1998',
              extra=raster),
            m('xmen6p', 'X-Men (6 Players ver EAA)', players=6, controls=(('joy', 3),), year='1992'),
            m('sf2proto', 'Street Fighter II (prototype)', year='1991'),
            # Do Flycast: Naomi e Atomiswave (nunca apagados).
            m('naomi', 'Naomi', 'isbios="yes"', coins=None, status=''),
            m('mvsc2', 'Marvel Vs. Capcom 2 (USA)', 'romof="naomi"', year='2000'),
            m('awbios', 'Atomiswave BIOS', 'isbios="yes"', coins=None, status=''),
            m('kofxi', 'The King of Fighters XI', 'romof="awbios"', year='2005', status='imperfect'),
        ]) + '</mame>\n'
        self.tmp = Path(tempfile.mkdtemp())
        self.roms = self.tmp / 'full'
        self.roms.mkdir()
        self.dest = self.tmp / 'mame'
        names = re.findall(r'<machine name="([^"]+)"', self.XML)
        self.files = ['%s.zip' % n for n in names if n != 'wbmlb'] + ['unknown.zip', 'readme.txt']
        for name in self.files:
            (self.roms / name).write_bytes(b'x' * 10)
        (self.roms / 'kinst').mkdir()
        (self.roms / 'kinst' / 'kinst.chd').write_bytes(b'c' * 100)
        (self.tmp / 'mame.xml').write_text(self.XML)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def romclean(self, *args, stdin=None):
        return subprocess.run(['python3', str(ROOT / 'config/fliperos-romclean'), *args], input=stdin,
                              capture_output=True, text=True, timeout=60, check=True).stdout

    def scan(self, *flags, xml=None, roms=None):
        plan = self.tmp / 'plan.tsv'
        out = self.romclean('scan', '--xml', str(xml or self.tmp / 'mame.xml'), '--roms', str(roms or self.roms),
                            '--dest', str(self.dest), '--plan', str(plan), *flags)
        summary = dict(line.split('=', 1) for line in out.splitlines())
        parts = {'move': [], 'rest': []}
        # self.dests: a pasta de destino de cada arquivo que vai.
        self.dests = {}
        for line in plan.read_text().splitlines():
            if not line.startswith('#'):
                fields = line.split('\t')
                parts[fields[0]].append(fields[2])
                if fields[0] == 'move':
                    self.dests[fields[2]] = fields[5]
        return summary, sorted(parts['move']), sorted(parts['rest'])

    # O preset do Setup para o GroovyMAME: os arcades do Flycast ficam para ele.
    CABINET = ('--arcade-only', '--status', 'imperfect', '--max-players', '2', '--max-buttons', '6',
               '--controls', 'joystick', '--clones', '1g1r', '--no-bootlegs', '--no-prototypes',
               '--exclude', 'flycast')

    def test_joystick_cabinet(self):
        # O preset do Setup: arcade, ate 2 jogadores e 6 botoes, so joystick,
        # uma versao por jogo (a USA antes da europeia), sem bootleg/prototipo.
        summary, move, rest = self.scan(*self.CABINET)
        self.assertEqual(move, ['1942.zip', 'asteroid.zip', 'coh1000c.zip', 'kinst', 'kinst.zip', 'mslug.zip',
                                'mvsc.zip', 'mvscu.zip', 'neogeo.zip', 'qsound_hle.zip', 'sfa2.zip', 'sfex.zip',
                                'tekken3.zip'])
        self.assertEqual(rest, ['area51.zip', 'broken.zip', 'cent.zip', 'kpython2.zip', 'mslugb.zip', 'mvscj.zip',
                                'nes.zip', 'pgm.zip', 'pinball.zip', 'sf2proto.zip', 'wbml.zip', 'xmen6p.zip'])
        # Pai, BIOS e dispositivo: mvsc (do mvscu), neogeo, coh1000c, qsound_hle.
        self.assertEqual(summary['needed'], '4')
        self.assertEqual(summary['unknown'], '1')
        self.assertEqual(int(summary['move_bytes']), 10 * 12 + 100)

    def test_controls_years_and_regions(self):
        _, move, _ = self.scan('--controls', 'joystick,trackball', '--arcade-only')
        self.assertIn('cent.zip', move)
        self.assertNotIn('area51.zip', move)
        self.assertNotIn('nes.zip', move)
        _, move, _ = self.scan('--years', '1980-1989')
        self.assertEqual([f for f in move if f in self.files], ['1942.zip', 'cent.zip', 'nes.zip', 'wbml.zip'])
        _, move, rest = self.scan('--clones', '1g1r', '--regions', 'Japan,USA')
        self.assertIn('mvscj.zip', move)
        self.assertIn('mvscu.zip', rest)
        _, move, rest = self.scan('--clones', 'none')
        self.assertIn('mvsc.zip', move)
        self.assertIn('mslugb.zip', rest)

    def test_rules(self):
        cases = {'vertical': '1942.zip', 'vector': 'asteroid.zip', 'mechanical': 'pinball.zip', 'chd': 'kinst.zip',
                 'clone': 'mslugb.zip', 'notworking': 'broken.zip', 'bios': 'pgm.zip'}
        for rule, gone in cases.items():
            _, move, rest = self.scan('--exclude', rule)
            self.assertIn(gone, rest, rule)
            self.assertIn('mslug.zip', move, rule)
        # Um BIOS usado vai junto mesmo excluindo os BIOS.
        self.assertIn('neogeo.zip', self.scan('--exclude', 'bios')[1])
        # So a placa do PlayStation: ZN (com a BIOS) e System 12; o PS2 nao.
        _, move, _ = self.scan('--only', 'psx')
        self.assertEqual(move, ['coh1000c.zip', 'sfex.zip', 'tekken3.zip'])

    def test_flycast_systems_go_to_their_folders(self):
        # Naomi e Atomiswave, do Flycast: fora do alvo dele nao vao nem sobram
        # para apagar.
        flycast = ['awbios.zip', 'kofxi.zip', 'mvsc2.zip', 'naomi.zip']
        summary, move, rest = self.scan(*self.CABINET)
        self.assertEqual(summary['flycast'], '4')
        self.assertFalse(set(flycast) & set(move + rest))
        # No alvo Flycast: so os sistemas dele, cada um na sua pasta, a BIOS na
        # dela e sem os dispositivos do MAME.
        naomi, aw, bios = (str(self.tmp / d) for d in ('naomi', 'atomiswave', 'bios-dc'))
        target = ('--dest', naomi, '--route', 'naomi=' + naomi, '--route', 'atomiswave=' + aw,
                  '--bios-dest', bios, '--no-devices')
        summary, move, rest = self.scan('--systems', 'naomi,atomiswave', *target)
        self.assertEqual(self.dests, {'mvsc2.zip': naomi, 'kofxi.zip': aw, 'naomi.zip': bios, 'awbios.zip': bios})
        self.assertEqual(summary['flycast'], '0')
        self.assertNotIn('mvsc2.zip', rest)
        self.assertIn('mslug.zip', rest)
        _, move, rest = self.scan('--systems', 'atomiswave', *target)
        self.assertEqual(move, ['awbios.zip', 'kofxi.zip'])
        self.assertFalse(set(flycast) & set(rest))
        # Os filtros valem para eles como para os outros (o kofxi e imperfeito).
        _, move, _ = self.scan('--systems', 'naomi,atomiswave', '--status', 'working', *target)
        self.assertEqual(move, ['mvsc2.zip', 'naomi.zip'])
        self.assertEqual(subprocess.run(
            ['python3', str(ROOT / 'config/fliperos-romclean'), 'scan', '--xml', str(self.tmp / 'mame.xml'),
             '--roms', str(self.roms), '--dest', naomi, '--plan', str(self.tmp / 'p'), '--systems', 'dreamcast'],
            capture_output=True).returncode, 2)

    def test_bios_and_devices_go_to_the_bios_folder(self):
        # --bios-dest: a BIOS e os dispositivos numa pasta, os jogos (e o pai
        # de um clone) na outra.
        bios = str(self.tmp / 'bios-mame')
        _, move, _ = self.scan(*self.CABINET, '--bios-dest', bios)
        for name in ('neogeo.zip', 'coh1000c.zip', 'qsound_hle.zip'):
            self.assertEqual(self.dests[name], bios, name)
        for name in ('mslug.zip', 'mvsc.zip', 'mvscu.zip', 'kinst', 'kinst.zip'):
            self.assertEqual(self.dests[name], str(self.dest), name)
        _, move, _ = self.scan(*self.CABINET, '--bios-dest', bios, '--no-devices')
        self.assertNotIn('qsound_hle.zip', move)
        self.assertIn('neogeo.zip', move)
        # O que ja esta na pasta das BIOS tambem e destino: a BIOS do jogo de
        # la nunca sobra para apagar.
        Path(bios).mkdir()
        (self.roms / 'mslug.zip').rename(Path(bios) / 'mslug.zip')
        _, move, rest = self.scan('--only', 'psx', '--bios-dest', bios)
        self.assertIn('neogeo.zip', move)
        self.assertNotIn('neogeo.zip', rest)

    def data_files(self):
        catver = self.tmp / 'catver.ini'
        catver.write_text(';; catver.ini 0.289 / 21-Aug-26 / MAME 0.289 ;;\n\n[Category]\n'
                          'mslug=Platform / Run, Jump & Shoot\nsfa2=Fighter / Versus\nmvsc=Fighter / Versus\n'
                          '1942=Shooter / Flying Vertical\nbroken=Tabletop / Mahjong * Mature *\n'
                          'pinball=Arcade / Pinball\nnes=Game Console / Home Videogame\n'
                          'neogeo=System / BIOS\n\n[VerAdded]\nmslug=0.36b5\n')
        nplayers = self.tmp / 'nplayers.ini'
        nplayers.write_text(';; NPlayers 0.278 / 06-jul-25 / MAME .278 ;;\n\n[NPlayers]\nmslug=2P sim\n'
                            '1942=2P alt\nsfa2=2P sim\ncent=1P\nxmen6p=6P alt / 2P sim\nneogeo=BIOS\nbroken=???\n')
        controls = self.tmp / 'controls.xml'
        controls.write_text('<?xml version="1.0"?>\n<dat><meta><version name="0.141.1"/></meta>\n'
                            '<game romname="mslug" numPlayers="2"><player number="1" numButtons="3"/></game>\n'
                            '<game romname="mvsc" numPlayers="2"><player number="1" numButtons="6"/>'
                            '<player number="2" numButtons="6"/></game>\n'
                            '<game romname="sfex"><player number="1"/></game>\n</dat>\n')
        return str(catver), str(nplayers), str(controls)

    def test_categories_play_modes_and_buttons_from_the_data_files(self):
        catver, nplayers, controls = self.data_files()
        # catver.ini: o genero e a parte antes da barra; o clone sem linha
        # fica com o do pai; o que o catver nao conhece passa.
        _, move, rest = self.scan('--catver', catver, '--categories', 'Fighter,Shooter')
        for name in ('sfa2.zip', 'mvsc.zip', 'mvscu.zip', '1942.zip', 'tekken3.zip'):
            self.assertIn(name, move, name)
        for name in ('mslug.zip', 'broken.zip', 'pinball.zip', 'nes.zip'):
            self.assertIn(name, rest, name)
        self.assertIn('broken.zip', self.scan('--catver', catver, '--no-mature')[2])
        self.assertIn('broken.zip', self.scan('--catver', catver, '--only', 'mature')[1])
        # nplayers.ini: dois ao mesmo tempo, um de cada vez, um so, ou nao diz.
        _, move, rest = self.scan('--nplayers', nplayers, '--play-modes', 'sim')
        self.assertEqual([f for f in move if f in ('mslug.zip', 'sfa2.zip', 'xmen6p.zip', '1942.zip', 'cent.zip',
                                                   'tekken3.zip', 'broken.zip')],
                         ['mslug.zip', 'sfa2.zip', 'xmen6p.zip'])
        _, move, _ = self.scan('--nplayers', nplayers, '--play-modes', 'alt,single')
        self.assertIn('1942.zip', move)
        self.assertIn('cent.zip', move)
        self.assertIn('xmen6p.zip', move)
        self.assertNotIn('sfa2.zip', move)
        self.assertNotIn('tekken3.zip', move)
        self.assertIn('tekken3.zip', self.scan('--nplayers', nplayers, '--play-modes', 'sim,unknown')[1])
        # controls.xml: os botoes que o jogo usa (o Metal Slug tem 4 no MAME, usa 3).
        self.assertIn('mslug.zip', self.scan('--max-buttons', '3')[2])
        self.assertIn('mslug.zip', self.scan('--max-buttons', '3', '--controls-xml', controls)[1])
        self.assertIn('sfex.zip', self.scan('--max-buttons', '6', '--controls-xml', controls)[1])

    def test_options_for_the_screen(self):
        catver, nplayers, controls = self.data_files()
        out = self.romclean('options', '--catver', catver, '--nplayers', nplayers, '--controls-xml', controls)
        lines = out.splitlines()
        self.assertEqual(lines[0], '# catver\t0.289')
        # Os generos de jogo primeiro (do mais comum ao mais raro), marcados;
        # BIOS, pinball e console depois, desmarcados.
        self.assertEqual(lines[1:8], ['genre\tFighter\t2\t1', 'genre\tPlatform\t1\t1', 'genre\tShooter\t1\t1',
                                      'genre\tTabletop\t1\t1', 'genre\tArcade\t1\t0', 'genre\tGame Console\t1\t0',
                                      'genre\tSystem\t1\t0'])
        self.assertEqual(lines[8:], ['# nplayers\t0.278', '# controls\t0.141.1'])
        self.assertEqual(self.romclean('options'), '')

    FAMILIES_XML = ('<mame>'
                    '<machine name="pacman"><description>Pac-Man</description><year>1980</year>'
                    '<display type="raster" rotate="90" width="288" height="224" refresh="60.6"/>'
                    '<input players="2" coins="1"><control type="joy" ways="4"/></input></machine>'
                    '<machine name="robotron"><description>Robotron</description><year>1982</year>'
                    '<input players="2" coins="1"><control type="doublejoy" ways="8" ways2="8"/></input></machine>'
                    '<machine name="tempest"><description>Tempest</description><year>1980</year>'
                    '<display type="vector" rotate="270"/>'
                    '<input players="2" coins="1"><control type="dial" buttons="2"/></input></machine>'
                    '<machine name="pong"><description>Pong</description><year>1972</year>'
                    '<input players="2" coins="1"><control type="paddle"/></input></machine>'
                    '<machine name="quiz"><description>Quiz</description><year>1995</year>'
                    '<display type="raster" rotate="0" width="512" height="384" refresh="60"/>'
                    '<input players="2" coins="1"><control type="only_buttons" buttons="4"/></input></machine>'
                    '<machine name="tekken" sourcefile="namco/namcos11.cpp"><description>Tekken</description>'
                    '<year>1994</year><display type="raster" rotate="0" width="640" height="480" refresh="60"/>'
                    '<input players="2" coins="1"><control type="joy" ways="8" buttons="4"/></input></machine>'
                    '<machine name="mk" sourcefile="midway/midyunit.cpp"><description>Mortal Kombat</description>'
                    '<year>1992</year><display type="raster" rotate="0" width="400" height="254" refresh="53.2" '
                    'pixclock="8000000" htotal="506" vtotal="289"/>'
                    '<input players="2" coins="1"><control type="joy" ways="8" buttons="6"/></input></machine>'
                    '<machine name="sf2" sourcefile="capcom/cps1.cpp"><description>Street Fighter II</description>'
                    '<year>1991</year><display type="raster" rotate="0" width="384" height="224" refresh="59.6"/>'
                    '<input players="2" coins="1"><control type="joy" ways="8" buttons="6"/></input></machine>'
                    '</mame>')

    def families(self, *flags):
        roms = self.tmp / 'families'
        if not roms.exists():
            roms.mkdir()
            (self.tmp / 'families.xml').write_text(self.FAMILIES_XML)
            for name in re.findall(r'<machine name="([^"]+)"', self.FAMILIES_XML):
                (roms / (name + '.zip')).write_bytes(b'x')
        return [f[:-4] for f in self.scan(*flags, xml=self.tmp / 'families.xml', roms=roms)[1]]

    def test_controls_the_panel_has(self):
        # Jogo so de botoes passa sempre; "joystick" vale os quatro tipos.
        self.assertEqual(self.families('--controls', 'joy8'), ['mk', 'quiz', 'sf2', 'tekken'])
        self.assertEqual(self.families('--controls', 'joy8,joy4'), ['mk', 'pacman', 'quiz', 'sf2', 'tekken'])
        self.assertEqual(self.families('--controls', 'twin,spinner'), ['quiz', 'robotron', 'tempest'])
        self.assertEqual(self.families('--controls', 'joystick'),
                         ['mk', 'pacman', 'quiz', 'robotron', 'sf2', 'tekken'])
        self.assertEqual(self.families('--controls', 'paddle'), ['pong', 'quiz'])
        self.assertEqual(self.families('--controls', ''), ['quiz'])
        self.assertEqual(len(self.families('--controls', 'any')), 8)

    def test_resolution_decades_and_hardware(self):
        # A resolucao: pelo pixclock/htotal quando o XML os tem (o MK, de 254
        # linhas a 15,8 kHz), senao pelas linhas; o que nao e raster passa.
        self.assertEqual(self.families('--scan-rates', '15'), ['mk', 'pacman', 'pong', 'robotron', 'sf2', 'tempest'])
        self.assertEqual(self.families('--scan-rates', '25,31'), ['pong', 'quiz', 'robotron', 'tekken', 'tempest'])
        self.assertEqual(self.families('--decades', '1970,1980'), ['pacman', 'pong', 'robotron', 'tempest'])
        self.assertEqual(self.families('--hardware', 'cps1,midway'), ['mk', 'sf2'])
        self.assertEqual(self.families('--orientation', 'vertical'), ['pacman', 'tempest'])
        _, move, _ = self.scan('--hardware', 'neogeo')
        self.assertEqual(move, ['mslug.zip', 'mslugb.zip', 'neogeo.zip'])

    def test_cache_and_xml_from_a_command(self):
        cache = self.tmp / 'cache' / 'mame.json'
        first, move, _ = self.scan(*self.CABINET, '--cache', str(cache))
        self.assertTrue(cache.is_file())
        # Com o cache, o XML nem e lido (aqui nem existe).
        args = ['--roms', str(self.roms), '--dest', str(self.dest), '--plan', str(self.tmp / 'plan.tsv'),
                *self.CABINET]
        out = self.romclean('scan', '--cache', str(cache), '--xml', str(self.tmp / 'sumiu.xml'), *args)
        self.assertIn('move=%s\n' % first['move'], out)
        out = self.romclean('scan', '--cache', str(cache), *args)
        self.assertIn('move=%s\n' % first['move'], out)
        # Um cache de outro formato e refeito.
        cache.write_text('{"format": 0, "machines": {"x": {}}}')
        out = self.romclean('scan', '--cache', str(cache), '--xml-command', 'cat %s' % (self.tmp / 'mame.xml'), *args)
        self.assertIn('move=%s\n' % first['move'], out)
        self.assertIn('"format":2', cache.read_text()[:40].replace(' ', ''))
        # Sem XML nem cache, com um XML vazio e com uma pasta que nao existe:
        # erro em uma linha (a que o Setup mostra), nao um plano vazio.
        for extra, message in (((), 'no MAME XML'), (('--xml-command', 'true'), 'could not read the MAME XML'),
                               (('--xml', str(self.tmp / 'mame.xml'), '--roms', '/nao/existe'),
                                'could not read the romset folder')):
            r = subprocess.run(['python3', str(ROOT / 'config/fliperos-romclean'), 'scan', *args, *extra],
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0, extra)
            self.assertIn(message, r.stderr.strip().splitlines()[-1], extra)
            self.assertNotIn('Traceback', r.stderr, extra)

    def test_copy_keeps_the_romset_and_shows_progress(self):
        bios = self.tmp / 'bios-mame'
        _, move, _ = self.scan(*self.CABINET, '--bios-dest', str(bios))
        plan, result = str(self.tmp / 'plan.tsv'), self.tmp / 'result.txt'
        out = self.romclean('apply', plan, 'copy', '--progress', '--result', str(result))
        self.assertRegex(out, r'(?m)^@step \d+ 1 of 13: 1942\.zip$')
        self.assertTrue(out.rstrip().endswith('@step 100 Done'))
        self.assertEqual(result.read_text(), 'copied=13\nskipped=0\nerrors=0\n')
        # O romset fica inteiro; os jogos numa pasta, a BIOS na outra, a pasta
        # do CHD com o que tinha dentro.
        self.assertEqual(len(list(self.roms.iterdir())), len(self.files) + 1)
        self.assertEqual((self.dest / 'mslug.zip').read_bytes(), b'x' * 10)
        self.assertEqual((self.dest / 'kinst' / 'kinst.chd').read_bytes(), b'c' * 100)
        self.assertEqual(sorted(p.name for p in bios.iterdir()), ['coh1000c.zip', 'neogeo.zip', 'qsound_hle.zip'])
        self.assertFalse(list(self.dest.glob('*.part')))
        # De novo: o que ja esta la com o mesmo tamanho fica; um arquivo
        # cortado (tamanho diferente) e copiado outra vez.
        (self.dest / 'mslug.zip').write_bytes(b'cortado')
        self.assertIn('copied=1\nskipped=12\nerrors=0\n', self.romclean('apply', plan, 'copy'))
        self.assertEqual((self.dest / 'mslug.zip').read_bytes(), b'x' * 10)

    CHD_XML = ('<mame>'
               '<machine name="kinst"><description>Killer Instinct</description><disk name="kinst" region="ata"/>'
               '</machine>'
               # O clone com o mesmo disco do pai (merge): o CHD esta na pasta do pai.
               '<machine name="kinst13" cloneof="kinst" romof="kinst"><description>Killer Instinct (v1.3)'
               '</description><disk name="kinst" merge="kinst" region="ata"/></machine>'
               # O clone com disco proprio: na pasta dele.
               '<machine name="kinstp" cloneof="kinst" romof="kinst"><description>Killer Instinct (proto)'
               '</description><disk name="kinstp" region="ata"/></machine>'
               '<machine name="area51"><description>Area 51</description><disk name="area51"/></machine>'
               '<machine name="gdrom" romof="naomigd"><description>GD-ROM game</description>'
               '<disk name="gdl-0010"/><disk name="pic" status="nodump"/></machine>'
               '<machine name="naomigd" isbios="yes" romof="naomi"><description>Naomi GD</description></machine>'
               '<machine name="naomi" isbios="yes"><description>Naomi</description></machine>'
               '<machine name="nodump"><description>No dump</description><disk name="x" status="nodump"/></machine>'
               '<machine name="mslug"><description>Metal Slug</description></machine>'
               '</mame>')

    def chds(self, *flags, roms=('mame',)):
        base = self.tmp / 'chd'
        if not base.exists():
            (base / 'xml').mkdir(parents=True)
            (base / 'mame.xml').write_text(self.CHD_XML)
            for folder, chd, size in (('kinst', 'kinst.chd', 300), ('kinstp', 'kinstp.chd', 200),
                                      ('gdrom', 'gdl-0010.chd', 500), ('outro', 'outro.chd', 900)):
                (base / 'chds' / folder).mkdir(parents=True)
                (base / 'chds' / folder / chd).write_bytes(b'c' * size)
            (base / 'chds' / 'solto.chd').write_bytes(b'x')
            for folder, sets in (('mame', ('kinst13', 'area51', 'nodump', 'mslug', 'unknown')), ('naomi', ('gdrom',))):
                (base / folder).mkdir()
                for name in sets:
                    (base / folder / (name + '.zip')).write_bytes(b'x')
        plan = base / 'plan.tsv'
        args = [a for r in roms for a in ('--roms', str(base / r))]
        out = self.romclean('chds', '--xml', str(base / 'mame.xml'), '--chds', str(base / 'chds'), *args,
                            '--plan', str(plan), *flags)
        rows = [line.split('\t') for line in plan.read_text().splitlines() if not line.startswith('#')]
        return (dict(line.split('=', 1) for line in out.splitlines()),
                {r[2]: Path(r[5]).name for r in rows if r[0] == 'move'},
                {r[1]: r[2] for r in rows if r[0] == 'missing'}, base)

    def test_chds_of_the_games_in_the_rom_folder(self):
        # So os CHDs dos jogos que estao na pasta de ROMs: o do clone que usa o
        # disco do pai vem da pasta do pai; disco sem dump nao conta; o que a
        # colecao nao tem fica na lista do que falta.
        summary, copies, missing, base = self.chds()
        self.assertEqual(copies, {'kinst': 'mame'})
        self.assertEqual(missing, {'area51': 'area51.chd'})
        self.assertEqual((summary['games'], summary['move'], summary['missing'], summary['move_bytes']),
                         ('2', '1', '1', '300'))
        self.assertEqual(summary['sets'], '4')
        # Os clones dentro do zip do pai (romset merged), se pedido.
        (base / 'mame' / 'kinst.zip').write_bytes(b'x')
        summary, copies, _, _ = self.chds('--clones')
        self.assertEqual(copies, {'kinst': 'mame', 'kinstp': 'mame'})
        self.assertEqual(self.chds()[1], {'kinst': 'mame'})
        # Cada pasta de ROMs recebe os CHDs dos jogos dela (as do Flycast).
        summary, copies, _, _ = self.chds(roms=('mame', 'naomi', 'naomi2'))
        self.assertEqual(copies, {'kinst': 'mame', 'gdrom': 'naomi'})
        # O plano e o do apply: copia a pasta, com progresso, e o que ja esta
        # la fica.
        out = self.romclean('apply', str(base / 'plan.tsv'), 'copy', '--progress')
        self.assertIn('copied=2\nskipped=0\nerrors=0\n', out)
        self.assertEqual((base / 'mame' / 'kinst' / 'kinst.chd').read_bytes(), b'c' * 300)
        self.assertEqual((base / 'naomi' / 'gdrom' / 'gdl-0010.chd').stat().st_size, 500)
        self.assertTrue((base / 'chds' / 'kinst' / 'kinst.chd').exists())
        self.assertFalse((base / 'mame' / 'outro').exists())
        self.assertIn('copied=0\nskipped=2\n', self.romclean('apply', str(base / 'plan.tsv'), 'copy'))
        r = subprocess.run(['python3', str(ROOT / 'config/fliperos-romclean'), 'chds', '--xml',
                            str(base / 'mame.xml'), '--chds', '/nao/existe', '--roms', str(base / 'mame'),
                            '--plan', str(base / 'p')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn('could not read the CHD folder', r.stderr)

    def test_copy_reports_what_failed(self):
        # Um arquivo que nao da para ler (aqui, uma pasta com o nome do zip no
        # destino): os outros vao, a tela recebe o erro e o status e 1.
        self.scan('--only', 'psx')
        (self.dest / 'sfex.zip').mkdir(parents=True)
        r = subprocess.run(['python3', str(ROOT / 'config/fliperos-romclean'), 'apply', str(self.tmp / 'plan.tsv'),
                            'copy', '--progress'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn('copied=2\nskipped=0\nerrors=1\n', r.stdout)
        self.assertIn('@fail Copying|1 sets could not be copied', r.stdout)
        self.assertNotIn('@step 100', r.stdout)
        self.assertIn('sfex.zip', r.stderr)

    def test_bios_of_a_game_already_in_the_mame_folder_is_kept(self):
        # O mslug ja esta na pasta do MAME (limpeza anterior): a neogeo.zip
        # que ficou na origem vai para la, nao para a lista de apagar. O mesmo
        # com o pai de um clone (mvsc do mvscu) e o dispositivo do sfa2.
        self.dest.mkdir()
        for name in ('mslug.zip', 'mvscu.zip', 'sfa2.zip'):
            (self.roms / name).rename(self.dest / name)
        summary, move, rest = self.scan(*self.CABINET)
        for name in ('neogeo.zip', 'mvsc.zip', 'qsound_hle.zip'):
            self.assertIn(name, move)
            self.assertNotIn(name, rest)
        self.assertIn('pgm.zip', rest)
        # Limpando a propria pasta do MAME, ela nao conta como destino.
        _, move, rest = self.scan(*self.CABINET, roms=self.dest)
        self.assertEqual(sorted(move), ['mslug.zip', 'mvscu.zip', 'sfa2.zip'])

    def test_parent_goes_for_a_clone_in_its_zip(self):
        # Num romset merged o wbmlb esta dentro do wbml.zip: o pai que nao
        # funciona vai porque o clone funciona.
        summary, move, _ = self.scan('--status', 'working')
        self.assertIn('wbml.zip', move)
        self.assertNotIn('broken.zip', move)

    def test_mame_2010_xml(self):
        xml = ('<?xml version="1.0"?>\n<!DOCTYPE mame [\n<!ELEMENT mame (game+)>\n]>\n<mame build="0.139">\n'
               '<game name="tekken3" sourcefile="namcos12.c"><description>Tekken 3</description>'
               '<chip type="cpu" tag="maincpu" name="CXD8661R"/><input players="2" buttons="4" coins="2">'
               '<control type="joy8way"/></input><driver status="imperfect"/></game>\n'
               '<game name="sfex" sourcefile="zn.c" romof="coh1000c"><description>Street Fighter EX</description>'
               '<chip type="cpu" name="PSX CPU"/><input players="2" buttons="6" coins="2">'
               '<control type="joy8way"/></input><driver status="good"/></game>\n'
               '<game name="coh1000c" sourcefile="zn.c" isbios="yes"><description>ZN1</description>'
               '<chip type="cpu" name="PSX CPU"/></game>\n'
               '<game name="cent" sourcefile="centiped.c"><description>Centipede</description>'
               '<input players="2" buttons="1" coins="3"><control type="trackball"/></input></game>\n'
               '<game name="harddriv" sourcefile="harddriv.c"><description>Hard Drivin</description>'
               '<chip type="cpu" name="R3000 (big)"/><input players="1" buttons="4" coins="2">'
               '<control type="paddle"/><control type="pedal"/></input></game>\n</mame>\n')
        (self.tmp / 'mame2010.xml').write_text(xml)
        import lzma
        with lzma.open(self.tmp / 'mame2010.xml.xz', 'wt') as f:
            f.write(xml)
        roms = self.tmp / 'mame2010'
        roms.mkdir()
        for name in ('tekken3.zip', 'sfex.zip', 'coh1000c.zip', 'cent.zip', 'harddriv.zip'):
            (roms / name).write_bytes(b'x')
        for path in ('mame2010.xml', 'mame2010.xml.xz'):
            _, move, rest = self.scan('--only', 'psx', xml=self.tmp / path, roms=roms)
            self.assertEqual(move, ['coh1000c.zip', 'sfex.zip', 'tekken3.zip'], path)
            self.assertEqual(rest, ['cent.zip', 'harddriv.zip'], path)
        # joy8way e o joystick; um painel com volante e pedal pega o Hard Drivin.
        _, move, _ = self.scan('--controls', 'joystick', '--arcade-only', xml=self.tmp / 'mame2010.xml', roms=roms)
        self.assertEqual(move, ['coh1000c.zip', 'sfex.zip', 'tekken3.zip'])
        _, move, _ = self.scan('--controls', 'joystick,paddle,pedal', xml=self.tmp / 'mame2010.xml', roms=roms)
        self.assertIn('harddriv.zip', move)

    def test_control_types_of_both_versions(self):
        # O 0.139 escreve joy8way, vjoy2way, doublejoy8way; o atual, joy e
        # doublejoy com o atributo ways.
        rc = load_script('romclean', 'config/fliperos-romclean')
        import xml.etree.ElementTree as ET
        for kind, ways, family in (
                ('joy', None, 'joy8'), ('joy', '8', 'joy8'), ('joy', '5 (half8)', 'joy8'), ('joy', '16', 'joy8'),
                ('joy', '4', 'joy4'), ('joy', '3 (half4)', 'joy4'), ('joy', '2', 'joy2'),
                ('joy', 'vertical2', 'joy2'), ('doublejoy', '8', 'twin'), ('joy8way', None, 'joy8'),
                ('joy4way', None, 'joy4'), ('vjoy2way', None, 'joy2'), ('doublejoy8way', None, 'twin'),
                ('vdoublejoy2way', None, 'twin'), ('stick', None, 'analog'), ('dial', None, 'spinner'),
                ('paddle', None, 'paddle'), ('positional', None, 'positional'), ('lightgun', None, 'lightgun'),
                ('hanafuda', None, 'mahjong'), ('mouse', None, 'trackball'), ('only_buttons', None, None)):
            el = ET.Element('control', type=kind)
            if ways:
                el.set('ways', ways)
            self.assertEqual(rc.control_family(el), family, (kind, ways))
        self.assertEqual(rc.regions_of('Marvel Vs. Capcom (USA 980123)'), {'USA'})
        self.assertEqual(rc.regions_of('Street Fighter Alpha 2 (Euro 960229)'), {'Europe'})
        self.assertEqual(rc.regions_of('Galaga (Namco rev. B)'), set())

    def test_xml_from_stdin(self):
        plan = self.tmp / 'plan.tsv'
        out = self.romclean('scan', '--xml', '-', '--roms', str(self.roms), '--dest', str(self.dest),
                            '--plan', str(plan), '--only', 'psx', stdin=self.XML)
        self.assertIn('move=3\n', out)

    def test_move_then_delete_what_is_left(self):
        self.dest.mkdir()
        (self.dest / 'neogeo.zip').write_bytes(b'ja estava')
        self.scan('--only', 'psx', '--exclude', 'bios')
        out = self.romclean('apply', str(self.tmp / 'plan.tsv'), 'move')
        self.assertIn('moved=3\n', out)
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()),
                         ['coh1000c.zip', 'neogeo.zip', 'sfex.zip', 'tekken3.zip'])
        self.assertEqual((self.dest / 'neogeo.zip').read_bytes(), b'ja estava')
        self.assertFalse((self.roms / 'sfex.zip').exists())
        out = self.romclean('apply', str(self.tmp / 'plan.tsv'), 'delete-rest')
        # Ficam so o que nao esta no XML e os do Flycast.
        self.assertEqual(sorted(p.name for p in self.roms.iterdir()),
                         ['awbios.zip', 'kofxi.zip', 'mvsc2.zip', 'naomi.zip', 'readme.txt', 'unknown.zip'])
        self.assertIn('deleted=%d\n' % (len(self.files) - 2 - 3 - 4 + 1), out)

    def test_the_mame_folder_itself(self):
        # A origem e a propria pasta do MAME: o que passou fica onde esta.
        self.dest = self.roms
        self.scan('--only', 'psx')
        self.assertIn('skipped=3\n', self.romclean('apply', str(self.tmp / 'plan.tsv'), 'move'))
        self.assertTrue((self.roms / 'tekken3.zip').exists())

    def test_apply_only_touches_the_folder(self):
        (self.tmp / 'fora.zip').write_bytes(b'x')
        plan = self.tmp / 'plan.tsv'
        plan.write_text('# roms\t%s\n# dest\t%s\nrest\tx\t../fora.zip\t1\tX\n' % (self.roms, self.dest))
        self.assertIn('skipped=1\n', self.romclean('apply', str(plan), 'delete-rest'))
        self.assertTrue((self.tmp / 'fora.zip').exists())

    def test_mame2010_xml_is_pinned_and_installed(self):
        text = (ROOT / 'config/fliperos-romclean').read_text()
        self.assertRegex(text, r"MAME2010_COMMIT = '[0-9a-f]{40}'")
        self.assertRegex(text, r"MAME2010_SHA256 = '[0-9a-f]{64}'")
        self.assertRegex(MKISO, r'(?m)^install_mame2010_xml$')
        self.assertIn('fetch-mame2010 \\\n    "$CHROOT_DIR/usr/local/share/fliperos/mame2010.xml.xz"', MKISO)
        self.assertIn('install -Dm755 "$src/config/fliperos-romclean" "$root/opt/fliperos/bin/fliperos-romclean"',
                      (ROOT / 'fliperos-rootfs.sh').read_text())
        self.assertIn('fliperos-romclean fetch-mame2010 /usr/local/share/fliperos/mame2010.xml.xz',
                      (ROOT / 'tools/cabinet-update.sh').read_text())


class FreeRomsTests(unittest.TestCase):
    """config/fliperos-freeroms: jogos livres para as pastas de ~/roms."""

    def test_every_game_is_pinned_and_has_a_free_license(self):
        fr = load_script('freeroms', 'config/fliperos-freeroms')
        self.assertGreaterEqual(len(fr.GAMES), 5)
        seen = set()
        for core, name, title, license_, sha256, url in fr.GAMES:
            self.assertRegex(sha256, r'^[0-9a-f]{64}$', name)
            # Da pagina de versoes do proprio projeto, numa tag fixa.
            self.assertRegex(url, r'^https://github\.com/[^/]+/[^/]+/releases/download/v[0-9.a-z]+/[^/]+$', name)
            self.assertTrue(url.endswith('/' + name), name)
            self.assertIn(license_, ('GPL-2.0-or-later', 'GPL-3.0-or-later', 'Zlib'), name)
            self.assertTrue(title)
            self.assertNotIn((core, name), seen)
            seen.add((core, name))

    def test_fetch_checks_the_hash_and_only_installed_cores(self):
        import hashlib
        fr = load_script('freeroms', 'config/fliperos-freeroms')
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'src').mkdir()
            (tmp / 'cores').mkdir()
            (tmp / 'cores' / 'fceumm_libretro.so').write_bytes(b'')
            games = []
            for core, name in (('fceumm', 'a.nes'), ('fceumm', 'b.nes'), ('mgba', 'c.gb')):
                (tmp / 'src' / name).write_bytes(name.encode() * 100)
                games.append((core, name, name, 'Zlib', hashlib.sha256(name.encode() * 100).hexdigest(),
                              (tmp / 'src' / name).as_uri()))
            roms = tmp / 'roms'
            # O do core que nao esta instalado (mgba) fica de fora.
            self.assertEqual(fr.fetch(str(roms), str(tmp / 'cores'), games=games), (2, 0, 1, 0))
            self.assertEqual((roms / 'retroarch/fceumm/a.nes').read_bytes(), b'a.nes' * 100)
            self.assertFalse((roms / 'retroarch/mgba').exists())
            self.assertEqual(fr.fetch(str(roms), str(tmp / 'cores'), games=games), (0, 2, 1, 0))
            # Um arquivo estragado e baixado de novo; um hash que nao bate nao
            # deixa arquivo nenhum.
            (roms / 'retroarch/fceumm/a.nes').write_bytes(b'estragado')
            games[1] = games[1][:4] + ('0' * 64,) + games[1][5:]
            (roms / 'retroarch/fceumm/b.nes').unlink()
            self.assertEqual(fr.fetch(str(roms), str(tmp / 'cores'), games=games), (1, 0, 1, 1))
            self.assertEqual((roms / 'retroarch/fceumm/a.nes').read_bytes(), b'a.nes' * 100)
            self.assertEqual(sorted(p.name for p in (roms / 'retroarch/fceumm').iterdir()), ['a.nes'])

    def test_list_and_install(self):
        out = subprocess.run(['python3', str(ROOT / 'config/fliperos-freeroms'), 'list'], capture_output=True,
                             text=True, check=True).stdout.splitlines()
        self.assertIn('fceumm\t240pee.nes\t240p Test Suite (NES)\tGPL-2.0-or-later', out)
        self.assertIn('install -Dm755 "$src/config/fliperos-freeroms" "$root/opt/fliperos/bin/fliperos-freeroms"',
                      ROOTFS)
        menu = (ROOT / 'fliperos-setup/screens/setup-menu.sh').read_text()
        self.assertIn('"freeroms|Free games (open-source homebrew)"', menu)
        self.assertIn('freeroms) screen_free_roms ;;', menu)
        self.assertIn('run_with_progress "Downloading the free games" "" freeroms_fetch "$result"', menu)


class QuietLaunchTests(unittest.TestCase):
    """Sem texto na tela ao abrir emuladores; o modo debug mostra tudo."""

    def test_limine_menu_shows_in_debug(self):
        self.assertIn('quiet: yes\n', limine_update.render(['6.18.54-15khz'], 'UUID=abc', '', '3'))
        self.assertIn('quiet: no\n', limine_update.render(['6.18.54-15khz'], 'UUID=abc', '', '3', 'no'))

    def run_kms(self, debug):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'logs').mkdir()
            prog = tmp / 'emu'
            prog.write_text('#!/bin/sh\necho saida-do-emulador\n')
            prog.chmod(0o755)
            flag = tmp / 'debug'
            if debug:
                flag.write_text('')
            env = dict(os.environ, FLIPEROS_LOGS=str(tmp / 'logs'), FLIPEROS_DEBUG_FLAG=str(flag))
            env.pop('DISPLAY', None)
            out = subprocess.run(['bash', str(ROOT / 'config/fliperos-kms-run'), str(prog)],
                                 capture_output=True, text=True, env=env).stdout
            log = tmp / 'logs' / 'emu.log'
            return out, log.read_text() if log.exists() else None

    def test_emulator_output_goes_to_the_log(self):
        out, log = self.run_kms(debug=False)
        self.assertEqual(out, '')
        self.assertEqual(log, 'saida-do-emulador\n')
        out, log = self.run_kms(debug=True)
        self.assertEqual(out, 'saida-do-emulador\n')
        for script in ('config/fliperos-x11-run', 'config/fliperos-session'):
            self.assertIn('/etc/fliperos/debug', (ROOT / script).read_text(), script)


class ControllerMappingTests(unittest.TestCase):
    """fliperos-controllers: completa o mapeamento automatico do SDL2 (botoes
    que ele deixa de fora, direcional digital mandado como eixos)."""
    M = controllers
    # Encoder comum: gamepad de 8 botoes (BTN_A B C X Y Z TL TR) com o
    # direcional em dois eixos de -1 a +1. O SDL so mapeia 6 botoes e poe o
    # direcional no analogico.
    AUTO = 'guid,Encoder,a:b0,b:b1,x:b3,y:b4,leftshoulder:b6,rightshoulder:b7,leftx:a0,lefty:a1,crc:1234,'

    def test_leftover_buttons_and_digital_stick(self):
        base = self.M.parse_mapping(self.AUTO)
        self.assertNotIn('crc', base)
        out = self.M.complete(base, 8, 2, 0, {0, 1}, scratch=False)
        self.assertEqual((out['lefttrigger'], out['righttrigger']), ('b2', 'b5'))
        self.assertEqual([out[k] for k in ('dpleft', 'dpright', 'dpup', 'dpdown')], ['-a0', '+a0', '-a1', '+a1'])
        self.assertNotIn('leftx', out)
        self.assertEqual(sorted(v for v in out.values() if v.startswith('b')), ['b%d' % i for i in range(8)])

    def test_real_analog_stick_and_complete_pads_stay(self):
        base = self.M.parse_mapping(self.AUTO)
        out = self.M.complete(base, 8, 2, 0, set(), scratch=False)
        self.assertEqual((out['leftx'], out['lefty']), ('a0', 'a1'))
        full = self.M.parse_mapping('g,Pad,a:b0,b:b1,x:b2,y:b3,dpup:h0.1,leftx:a0,lefty:a1,')
        self.assertEqual(self.M.complete(full, 4, 2, 1, set(), scratch=False), full)

    def test_controllers_without_any_mapping(self):
        out = self.M.complete({}, 10, 2, 0, {0, 1}, scratch=True)
        self.assertEqual((out['a'], out['b'], out['x'], out['start']), ('b0', 'b1', 'b2', 'b9'))
        self.assertEqual(out['dpup'], '-a1')
        hat = self.M.complete({}, 4, 0, 1, set(), scratch=True)
        self.assertEqual((hat['dpup'], hat['dpleft']), ('h0.1', 'h0.8'))

    def test_db_line_and_merge(self):
        self.assertEqual(self.M.mapping_line('abc', 'Pad, X', {'b': 'b1', 'a': 'b0'}),
                         'abc,Pad  X,a:b0,b:b1,platform:Linux,')
        self.assertEqual(self.M.merge_db(['# gerado', 'abc,old', 'def,keep'], {'abc': 'abc,new'}),
                         ['def,keep', 'abc,new'])

    def test_flycast_files_follow_its_convention(self):
        # O Flycast nao entende direcional em meio eixo: o arquivo dele vem
        # pronto, na convencao do DefaultInputMapping (padrao e arcade).
        binds = self.M.complete(self.M.parse_mapping(self.AUTO), 8, 2, 0, {0, 1}, scratch=False)
        std = self.M.flycast_cfg('Encoder', binds, arcade=False)
        for bind in ('0-:btn_dpad1_left', '1+:btn_dpad1_down', '0:btn_a', '3:btn_x', '6:btn_z', '7:btn_c',
                     '2:btn_trigger_left', '5:btn_trigger_right'):
            self.assertIn(bind + '\n', std, bind)
        arcade = self.M.flycast_cfg('Encoder', binds, arcade=True)
        for bind in ('3:btn_c', '4:btn_x', '7:btn_y', '6:btn_z'):
            self.assertIn(bind + '\n', arcade, bind)
        self.assertIn('version = 4\n', arcade)
        self.assertEqual(self.M.flycast_filename('vusb.wikidot.com/project:x Pad', arcade=True),
                         'SDL_vusb.wikidot.com-project-x Pad_arcade.cfg')

    def test_retroarch_profile_in_panel_order(self):
        # Painel de 8 botoes com o direcional em eixos: 1 2 3 = Y X L,
        # 4 5 6 = B A R, depois Start e Select, na numeracao do udev.
        binds = self.M.complete(self.M.parse_mapping(self.AUTO), 8, 2, 0, {0, 1}, scratch=False)
        self.assertTrue(self.M.is_arcade(binds))
        ra = self.M.retroarch_binds(binds, 8)
        self.assertEqual([ra[k + '_btn'] for k in ('y', 'x', 'l', 'b', 'a', 'r', 'start', 'select')],
                         [str(i) for i in range(8)])
        self.assertEqual([ra[k + '_axis'] for k in ('up', 'down', 'left', 'right')], ['-1', '+1', '-0', '+0'])
        # Encoder de 12 com hat: os extras de painel de 8, Select/Start nos 9 e 10.
        hat = self.M.complete({}, 12, 0, 1, set(), scratch=True)
        ra = self.M.retroarch_binds(hat, 12)
        self.assertEqual([ra[k + '_btn'] for k in ('l2', 'r2', 'select', 'start', 'l3', 'r3')],
                         ['6', '7', '8', '9', '10', '11'])
        self.assertEqual((ra['up_btn'], ra['left_btn']), ('h0up', 'h0left'))
        # Com analogico de verdade nao e painel: fica com o RetroArch.
        analog = self.M.complete(self.M.parse_mapping(self.AUTO), 8, 2, 0, set(), scratch=False)
        self.assertFalse(self.M.is_arcade(analog))
        text = self.M.retroarch_profile('Painel', (5824, 1503), binds, 8)
        for line in ('input_driver = "udev"', 'input_device = "Painel"', 'input_vendor_id = "5824"',
                     'input_product_id = "1503"', 'input_start_btn = "6"', 'input_up_axis = "-1"'):
            self.assertIn(line + '\n', text, line)

    def test_retroarch_profile_only_when_none_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(self.M.retroarch_has_profile(tmp, 'Painel', (5824, 1503)))
            Path(tmp, 'a.cfg').write_text('input_device = "Outro"\ninput_vendor_id = 5824\ninput_product_id = 1503\n')
            self.assertTrue(self.M.retroarch_has_profile(tmp, 'Painel', (5824, 1503)))
            self.assertFalse(self.M.retroarch_has_profile(tmp, 'Painel', (1, 2)))
            Path(tmp, 'b.cfg').write_text('input_driver = "udev"\ninput_device = "Painel"\n')
            self.assertTrue(self.M.retroarch_has_profile(tmp, 'Painel', (0, 0)))

    def test_runs_at_boot_and_on_hotplug(self):
        rules = (ROOT / 'config/99-fliperos-input.rules').read_text()
        self.assertIn('ENV{SYSTEMD_WANTS}+="fliperos-controllers.service"', rules)
        self.assertIn('multi-user.target.wants/fliperos-controllers.service', ROOTFS)
        self.assertIn("echo 'SDL_GAMECONTROLLERCONFIG_FILE=/var/lib/fliperos/gamecontrollerdb.txt'", ROOTFS)
        for script in ('config/fliperos-lxde', 'config/fliperos-kms-run', 'config/fliperos-x11-run'):
            self.assertIn('/var/lib/fliperos/gamecontrollerdb.txt', (ROOT / script).read_text(), script)
        self.assertFalse((ROOT / 'config/gamecontrollerdb.txt').exists())


class AppStoreTests(unittest.TestCase):
    """App Store do LXDE: GNOME Software com Flatpak (Flathub), sem snap."""

    def test_packages_and_flathub(self):
        pkgs = apt_list()
        for pkg in ('gnome-software', 'gnome-software-plugin-flatpak', 'flatpak', 'xdg-desktop-portal-gtk'):
            self.assertIn(pkg, pkgs)
            self.assertIn(pkg, (ROOT / 'tools/cabinet-update.sh').read_text())
        self.assertNotIn('gnome-software-plugin-snap', MKISO)
        self.assertIn('flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo',
                      MKISO)

    def test_no_background_updates(self):
        override = (ROOT / 'config/fliperos-software.gschema.override').read_text()
        self.assertIn('[org.gnome.software]', override)
        for key in ('download-updates=false', 'download-updates-notify=false', 'first-run=false'):
            self.assertIn(key + '\n', override)
        self.assertIn('90_fliperos-software.gschema.override', ROOTFS)

    def test_menu_entry_and_panel_button(self):
        entry = (ROOT / 'config/applications/org.gnome.Software.desktop').read_text()
        for line in ('Name=App Store', 'Exec=gnome-software %U', 'TryExec=gnome-software',
                     'Categories=System;PackageManager;'):
            self.assertIn(line + '\n', entry)
        self.assertIn('id=org.gnome.Software.desktop', (ROOT / 'config/lxde/lxpanel/LXDE/panels/panel').read_text())


class FrontendThemeTests(unittest.TestCase):
    """Os temas do FliperOS para 240p: config/pegasus-theme-fliperos e
    config/esde-theme-fliperos."""
    THEME = ROOT / 'config/pegasus-theme-fliperos'
    ESDE = ROOT / 'config/esde-theme-fliperos'

    def test_esde_theme_files(self):
        caps = ElementTree.parse(self.ESDE / 'capabilities.xml').getroot()
        self.assertEqual(caps.tag, 'themeCapabilities')
        self.assertEqual(caps.findtext('themeName'), 'FliperOS 240p')
        self.assertEqual([a.text for a in caps.findall('aspectRatio')], ['4:3'])
        theme = ElementTree.parse(self.ESDE / 'theme.xml').getroot()
        self.assertEqual(theme.tag, 'theme')
        views = {name.strip(): view for view in theme.findall('view') for name in view.get('name').split(',')}
        self.assertEqual(set(views), {'system', 'gamelist'})
        # O tamanho da letra e fracao da altura: em 240 linhas, a das listas
        # tem 12 pixels ou mais, e nenhuma tem menos de 9.
        for view, name in (('system', 'systemTextlist'), ('gamelist', 'gamelistTextlist')):
            lists = [v.find("textlist[@name='%s']" % name) for v in theme.findall('view')
                     if view in v.get('name') and v.find("textlist[@name='%s']" % name) is not None]
            self.assertEqual(len(lists), 1, name)
            self.assertGreaterEqual(round(float(lists[0].findtext('fontSize')) * 240), 12, name)
        sizes = [round(float(size.text) * 240) for size in theme.iter('fontSize')]
        self.assertGreaterEqual(min(sizes), 9)
        # A imagem do jogo, o video no lugar dela, e a descricao.
        gamelist = [v for v in theme.findall('view') if v.get('name') == 'gamelist'][0]
        self.assertIn('screenshot', gamelist.find("video[@name='gameVideo']").findtext('imageType'))
        self.assertEqual(gamelist.find("text[@name='description']").findtext('metadata'), 'description')
        # Jogo sem dados: nada, em vez de "unknown".
        for element in (gamelist.find("datetime[@name='year']"), gamelist.find("text[@name='developer']")):
            self.assertEqual(element.findtext('defaultValue'), ':space:')
        # Variaveis usadas existem, e os arquivos sao do tema (./) ou do ES-DE (:/).
        text = (self.ESDE / 'theme.xml').read_text()
        known = {v.tag for v in theme.find('variables')} | {'system.fullName'}
        self.assertLessEqual(set(re.findall(r'\$\{([^}]+)\}', text)), known)
        for path in [p.text for p in theme.iter('path')] + [theme.find('variables').findtext('mainFont')]:
            if path.startswith('./'):
                self.assertTrue((self.ESDE / path[2:]).is_file(), path)
            else:
                self.assertTrue(path.startswith(':/'), path)
        self.assertEqual(ElementTree.parse(self.ESDE / 'fill.svg').getroot().tag, '{http://www.w3.org/2000/svg}svg')

    def test_theme_files(self):
        cfg = dict(line.split(': ', 1) for line in (self.THEME / 'theme.cfg').read_text().splitlines())
        self.assertEqual(cfg['name'], 'FliperOS 240p')
        for key in ('author', 'version', 'summary', 'description'):
            self.assertTrue(cfg[key], key)
        qml = (self.THEME / 'theme.qml').read_text()
        self.assertEqual(qml.count('{'), qml.count('}'))
        self.assertEqual(qml.count('('), qml.count(')'))
        # As medidas sao de uma tela de 240 linhas; a letra da lista tem 12.
        self.assertIn('readonly property real s: Math.max(1, height / 240)', qml)
        self.assertIn('pixelSize: px(12)', qml)
        # So o QtQuick: um modulo QML que faltasse derrubaria o tema inteiro.
        self.assertEqual(re.findall(r'(?m)^import (\S+)', qml), ['QtQuick'])
        for api in ('api.collections', 'game.launch()', 'api.keys.isAccept(event)', 'api.memory.set('):
            self.assertIn(api, qml)

    def test_installed_where_each_frontend_looks_for_themes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ('home/fliperos', 'etc/modprobe.d', 'etc/sudoers.d', 'etc/profile.d', 'etc/systemd/system'):
                (root / d).mkdir(parents=True)
            (root / 'etc/passwd').write_text('fliperos:x:1000:1000::/home/fliperos:/bin/bash\n')
            subprocess.run(['bash', str(ROOT / 'fliperos-rootfs.sh'), str(root)], check=True,
                           capture_output=True, timeout=120)
            theme = root / 'usr/share/pegasus-frontend/themes/fliperos-240p'
            self.assertEqual(sorted(p.name for p in theme.iterdir()), ['theme.cfg', 'theme.qml'])
            self.assertEqual((theme / 'theme.qml').read_text(), (self.THEME / 'theme.qml').read_text())
            esde = root / 'usr/share/es-de/themes/fliperos-240p-es-de'
            self.assertEqual(sorted(p.name for p in esde.iterdir()), ['capabilities.xml', 'fill.svg', 'theme.xml'])
            self.assertEqual((esde / 'theme.xml').read_text(), (self.ESDE / 'theme.xml').read_text())
        lib = (ROOT / 'fliperos-setup/lib/frontends.sh').read_text()
        self.assertIn('PEGASUS_THEME=${PEGASUS_THEME:-/usr/share/pegasus-frontend/themes/fliperos-240p}', lib)
        self.assertIn('ESDE_THEME=${ESDE_THEME:-/usr/share/es-de/themes/fliperos-240p-es-de}', lib)


class DesktopAppsTests(unittest.TestCase):
    """Falkon e Transmission na imagem, com o nome dizendo para que servem."""

    def test_in_the_image(self):
        pkgs = apt_list()
        for pkg in ('falkon', 'transmission-gtk'):
            self.assertIn(pkg, pkgs)
            self.assertIn(pkg, (ROOT / 'tools/cabinet-update.sh').read_text())

    def test_menu_names_say_what_they_are(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ('home/fliperos', 'usr/share/applications', 'etc/modprobe.d', 'etc/sudoers.d',
                      'etc/profile.d', 'etc/systemd/system'):
                (root / d).mkdir(parents=True)
            (root / 'etc/passwd').write_text('fliperos:x:1000:1000::/home/fliperos:/bin/bash\n')
            (root / 'usr/share/applications/org.kde.falkon.desktop').write_text(
                '[Desktop Entry]\nName=Falkon\nName[pt_BR]=Falkon\nGenericName=Web Browser\nExec=falkon %u\n\n'
                '[Desktop Action NewTab]\nName=Open new tab\nName[pt_BR]=Abrir uma nova aba\n'
                'Exec=falkon --new-tab\n')
            (root / 'usr/share/applications/transmission-gtk.desktop').write_text(
                '[Desktop Entry]\nName=Transmission\nGenericName=BitTorrent Client\nExec=transmission-gtk %U\n')
            for _ in range(2):  # de novo, o sufixo nao dobra
                subprocess.run(['bash', str(ROOT / 'fliperos-rootfs.sh'), str(root)], check=True,
                               capture_output=True, timeout=120)
            apps = root / 'usr/local/share/applications'
            # /usr/local/share vem antes de /usr/share: a entrada com o mesmo
            # ID troca a do pacote. So o nome do programa muda; as acoes ficam.
            self.assertEqual((apps / 'org.kde.falkon.desktop').read_text(),
                             '[Desktop Entry]\nName=Falkon (browser)\nName[pt_BR]=Falkon (browser)\n'
                             'GenericName=Web Browser\nExec=falkon %u\n\n'
                             '[Desktop Action NewTab]\nName=Open new tab\nName[pt_BR]=Abrir uma nova aba\n'
                             'Exec=falkon --new-tab\n')
            self.assertIn('Name=Transmission (torrent)\n', (apps / 'transmission-gtk.desktop').read_text())
            self.assertEqual((root / 'usr/share/applications/transmission-gtk.desktop').read_text().count('torrent'), 0)


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

    def test_programs_fetched_from_their_site(self):
        # "fetch:COMANDO" na coluna do pacote: o que nao pode vir na imagem. O
        # comando vem na imagem, e o binario da linha so existe depois do fetch.
        fetched = {r[0]: r for r in self.rows() if r[3].startswith('fetch:')}
        self.assertEqual(sorted(fetched), ['fightcade'])
        for row in fetched.values():
            command = row[3][len('fetch:'):]
            self.assertTrue((ROOT / 'config' / command).is_file(), command)
            self.assertIn('"$root/opt/fliperos/bin/%s"' % command, ROOTFS)
            self.assertFalse(row[2].startswith('/opt/fliperos/bin/'), row)
        self.assertEqual(fetched['fightcade'],
                         ['fightcade', 'kms', '/opt/fliperos/fightcade/fightcade', 'fetch:fliperos-fightcade',
                          'Fightcade 2'])


def fightcade_package(path, files=None):
    """Um pacote como o do Fightcade para Linux: tudo dentro de Fightcade/."""
    files = files if files is not None else {
        'Fightcade2.sh': '#!/bin/sh\necho "$@" > "${0%/*}/args"\nenv > "${0%/*}/env"\n',
        'fc2-electron/fc2-electron': '#!/bin/sh\n',
        'VERSION.txt': '9.9.9',
        'emulator/fbneo/fcadefbneo.exe': 'MZ',
        'emulator/fbneo/ROMs/neogeo.zip': 'bios',
        # Os arquivos de configuracao que vem no pacote, com fim de linha do
        # Windows (os dos emuladores do Wine) e os padroes de la.
        'emulator/fbneo/config/fcadefbneo.default.ini':
            '// The display mode to use for fullscreen\r\nnVidHorWidth 1280\r\nnVidHorHeight 720\r\n\r\n'
            'nVidScrnAspectX 16\r\nnVidScrnAspectY 9 \r\nnVidVerWidth 1280\r\nbVidAutoSwitchFull 0\r\nnVidSelect 4\r\n',
        'emulator/ggpofba/config/ggpofba-ng.default.ini':
            'nVidWidth 1024\r\nnVidHeight 768\r\nnVidScrnAspectX 16\r\nnVidScrnAspectY 9\r\n',
        'emulator/flycast/emu.default.cfg':
            '[config]\nrend.Resolution = 480\nrend.ScreenStretching = 100\n\n[window]\nfullscreen = no\nheight = 480\n',
        'emulator/flycast/flycast.elf': 'ELF',
        'emulator/flycast/ROMs/.keep': '',
        'emulator/snes9x/ROMs/.keep': '',
        'emulator/ggpofba/ROMs/.keep': '',
    }
    with tarfile.open(path, 'w:gz') as tar:
        for name, content in files.items():
            data = content.encode()
            info = tarfile.TarInfo('Fightcade/' + name)
            info.size = len(data)
            info.mode = 0o755 if name.endswith(('.sh', 'fc2-electron', '.elf')) else 0o644
            tar.addfile(info, io.BytesIO(data))


class FightcadeTests(unittest.TestCase):
    """config/fliperos-fightcade: o Fightcade 2 baixado do site dele (nao vem
    na imagem) e aberto num Xorg proprio."""
    SCRIPT = ROOT / 'config/fliperos-fightcade'

    def env(self, tmp, **extra):
        (tmp / 'home').mkdir(exist_ok=True)
        env = dict(os.environ, HOME=str(tmp / 'home'), FIGHTCADE_DIR=str(tmp / 'fc'), FLIPEROS_USER='root',
                   FIGHTCADE_URL=(tmp / 'pkg.tar.gz').as_uri(), FLIPEROS_ROMS_SCRIPT=str(ROOT / 'config/fliperos-roms'),
                   FLIPEROS_CORE_INFO=str(tmp / 'nada'))
        env.pop('DISPLAY', None)
        env.update(extra)
        return env

    def fetch(self, tmp, *args, **extra):
        return subprocess.run(['bash', str(self.SCRIPT), 'fetch'] + list(args), capture_output=True, text=True,
                              env=self.env(tmp, **extra), timeout=120)

    def test_fetch_installs_the_package_and_links_the_rom_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fightcade_package(tmp / 'pkg.tar.gz')
            run = self.fetch(tmp, '--progress')
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            steps = [line for line in run.stdout.splitlines() if line.startswith('@step')]
            self.assertEqual(steps[0], '@step 0 Downloading Fightcade from fightcade.com')
            self.assertIn('@step 88 Unpacking', steps)
            self.assertEqual(steps[-1], '@step 100 Fightcade 9.9.9 installed')
            fc = tmp / 'fc'
            # Sem a pasta Fightcade/ do pacote, e sem o arquivo baixado.
            self.assertTrue(os.access(fc / 'Fightcade2.sh', os.X_OK))
            self.assertFalse((fc / 'Fightcade').exists())
            self.assertFalse((fc / '.download.part').exists())
            # O "binario" da tabela de sessoes: so existe depois do download.
            self.assertEqual(os.readlink(fc / 'fightcade'), str(self.SCRIPT))
            # As ROMs em ~/roms/fightcade; o que veio na pasta vai junto.
            roms = tmp / 'home/roms/fightcade'
            self.assertEqual(os.readlink(fc / 'emulator/fbneo/ROMs'), str(roms / 'fbneo'))
            self.assertEqual(os.readlink(fc / 'emulator/ggpofba/ROMs'), str(roms / 'fc1'))
            self.assertEqual((roms / 'fbneo/neogeo.zip').read_text(), 'bios')
            # De novo (reparo): os links e as ROMs da pessoa ficam.
            (roms / 'fbneo/sf2.zip').write_text('rom')
            (fc / 'Fightcade2.sh').unlink()
            run = self.fetch(tmp)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertNotIn('@step', run.stdout)
            self.assertIn('Fightcade 9.9.9 installed', run.stdout)
            self.assertTrue((fc / 'Fightcade2.sh').exists())
            self.assertTrue((fc / 'emulator/fbneo/ROMs').is_symlink())
            self.assertEqual((roms / 'fbneo/sf2.zip').read_text(), 'rom')

    def test_fetch_refuses_what_is_not_the_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            # Sem rede (o arquivo nao existe).
            run = self.fetch(tmp, '--progress')
            self.assertEqual(run.returncode, 1)
            self.assertIn('@fail Fightcade|the download failed (no network?)', run.stdout)
            # Outro arquivo no lugar do pacote (uma pagina de erro, um pacote sem o cliente).
            (tmp / 'pkg.tar.gz').write_text('<html>not found</html>')
            run = self.fetch(tmp, '--progress')
            self.assertEqual(run.returncode, 1)
            self.assertIn('@fail Fightcade|the downloaded file is not the Fightcade package', run.stdout)
            fightcade_package(tmp / 'pkg.tar.gz', {'README.txt': 'x'})
            self.assertEqual(self.fetch(tmp).returncode, 1)
            self.assertFalse((tmp / 'fc/fightcade').exists())
            self.assertFalse((tmp / 'fc/.download.part').exists())

    def test_opens_in_its_own_xorg(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            x11 = tmp / 'x11-run'
            x11.write_text('#!/bin/sh\necho "RUN=$*"\necho "RC=$FLIPEROS_OPENBOX_RC"\n')
            x11.chmod(0o755)
            env = self.env(tmp, FLIPEROS_X11_RUN=str(x11))
            # Sem o download: diz onde instalar, e nao abre nada.
            run = subprocess.run(['bash', str(self.SCRIPT)], capture_output=True, text=True, env=env)
            self.assertEqual(run.returncode, 1)
            self.assertIn('Setup > Frontend', run.stderr)
            fightcade_package(tmp / 'pkg.tar.gz')
            self.assertEqual(self.fetch(tmp).returncode, 0)
            # No console: o fliperos-x11-run com o nome da linha da tabela de
            # modos (fightcade) e o openbox dele.
            run = subprocess.run(['bash', str(tmp / 'fc/fightcade')], capture_output=True, text=True, env=env)
            self.assertEqual(run.stdout, 'RUN=%s/fc/fightcade\nRC=/etc/fliperos/openbox-fightcade.xml\n' % tmp)

    CLIENT = '10 ./fc2-electron/fc2-electron --no-sandbox'

    def session(self, tmp, checks, frequency='15k', modes=None, switchres=True, **extra):
        """Abre o Fightcade dentro de um X de mentira. checks: o que o pgrep
        mostra a cada conferida (processos separados por "|"); depois da
        ultima, nada. Devolve o processo; os pedidos ao xrandr ficam em
        tmp/xrandr.log."""
        bin_dir = tmp / 'bin'
        bin_dir.mkdir(exist_ok=True)
        (tmp / 'pgrep.checks').write_text(''.join(line + '\n' for line in checks))
        (tmp / 'n').write_text('0\n')
        for name in ('xrandr.log', 'xrandr.modes'):
            (tmp / name).unlink(missing_ok=True)
        fakes = {
            'pgrep': 'n=$(cat "$FAKE/n")\necho $((n + 1)) > "$FAKE/n"\n'
                     'sed -n "$((n + 1))p" "$FAKE/pgrep.checks" | tr "|" "\\n" | grep .\n',
            # Como o xrandr de verdade: a saida com imagem, o id do modo atual
            # e os modos acrescentados na lista.
            'xrandr': 'case $1 in\n'
                      '  --query)\n'
                      '    echo "VGA-1 connected primary 640x480+0+0 (normal left inverted right) 0mm x 0mm"\n'
                      '    echo "   SR-1_640x480@60i  59.94*+"\n'
                      '    sed "s/.*/   &  60.00 /" "$FAKE/xrandr.modes" 2> /dev/null ;;\n'
                      '  --verbose)\n'
                      '    echo "VGA-1 connected primary 640x480+0+0 (0x4a) normal (normal left) 0mm x 0mm"\n'
                      '    echo "  SR-1_640x480@60i (0x4a) 13.0MHz -HSync -VSync Interlace *current +preferred" ;;\n'
                      '  --addmode) echo "$*" >> "$FAKE/xrandr.log"; echo "$3" >> "$FAKE/xrandr.modes" ;;\n'
                      '  --newmode | --output) echo "$*" >> "$FAKE/xrandr.log" ;;\n'
                      'esac\n',
            'switchres': 'echo "Switchres: Modeline \\"$1x$2_$3 15.700000KHz 60.000000Hz\\" 6.700 $1 336 368 426 '
                         '$2 244 247 262 -hsync -vsync"\n' if switchres else
                         'echo "Switchres: could not find a video mode"; exit 1\n',
        }
        for name, body in fakes.items():
            (bin_dir / name).write_text('#!/bin/bash\n' + body)
            (bin_dir / name).chmod(0o755)
        (tmp / 'fliperos.conf').write_text('frequency=%s\n' % frequency)
        (tmp / 'modes.conf').write_text(modes or (ROOT / 'config/fliperos-emulator-modes.conf').read_text())
        env = self.env(tmp, DISPLAY=':9', FLIPEROS_RES_H='480', FIGHTCADE_QUIT_WAIT='1', FAKE=str(tmp),
                       FLIPEROS_CONF=str(tmp / 'fliperos.conf'), FLIPEROS_MODES=str(tmp / 'modes.conf'),
                       PATH='%s:%s' % (bin_dir, os.environ['PATH']))
        env.update(extra)
        return subprocess.run(['bash', str(tmp / 'fc/fightcade')], capture_output=True, text=True, env=env,
                              timeout=60)

    def xrandr_log(self, tmp):
        log = tmp / 'xrandr.log'
        return log.read_text().splitlines() if log.exists() else []

    def test_inside_x_starts_the_client_and_waits_for_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fightcade_package(tmp / 'pkg.tar.gz')
            self.assertEqual(self.fetch(tmp).returncode, 0)
            fc = tmp / 'fc'
            # O cliente aberto nas duas primeiras conferidas, depois fechado.
            for height, scale, extra in (('480', '0.67', {}), ('768', '1.00', {}), ('240', '0.50', {}),
                                         ('480', '0.8', {'FIGHTCADE_SCALE': '0.8'})):
                run = self.session(tmp, [self.CLIENT, self.CLIENT], FLIPEROS_RES_H=height, **extra)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual((fc / 'args').read_text(), '--force-device-scale-factor=%s\n' % scale)
                # Saiu so depois de o cliente fechar (tres conferidas).
                self.assertEqual((tmp / 'n').read_text().strip(), '3')
            # Uma atualizacao automatica (o cliente fecha e o fcade-upd o reabre) nao encerra a sessao.
            run = self.session(tmp, [self.CLIENT, '11 ./fcade-upd update.tar.gz', self.CLIENT])
            self.assertEqual((tmp / 'n').read_text().strip(), '4')
            env_file = (fc / 'env').read_text()
            self.assertIn('WINEPREFIX=%s/home/.local/share/fliperos/wine-fightcade\n' % tmp, env_file)
            self.assertIn('WINEDLLOVERRIDES=mscoree,mshtml=\n', env_file)
            self.assertIn('WINEDEBUG=-all\n', env_file)
            # O Flycast dele e um AppImage: sem o FUSE, extrai e roda.
            self.assertIn('APPIMAGE_EXTRACT_AND_RUN=1\n', env_file)

    def test_each_match_runs_in_the_mode_of_its_emulator(self):
        # A sala fica em 640x480; com um emulador aberto a tela vai para o
        # modo dele na tabela (320x240 nos do Wine, 640x240 no Flycast, num
        # monitor de 15 kHz) e volta ao da sala quando ele fecha.
        fbneo = self.CLIENT + '|20 /usr/lib/wine/wine /opt/fliperos/fightcade/emulator/fbneo/fcadefbneo.exe sf2'
        flycast = self.CLIENT + '|30 ./flycast.elf|31 /tmp/appimage_extracted_0/usr/bin/flycast-dojo'
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fightcade_package(tmp / 'pkg.tar.gz')
            self.assertEqual(self.fetch(tmp).returncode, 0)
            run = self.session(tmp, [self.CLIENT, fbneo, fbneo, self.CLIENT, flycast, self.CLIENT])
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(self.xrandr_log(tmp), [
                # Os modos ja entram na lista da saida antes de abrir a sala:
                # o Wine os enxerga quando o emulador pede a tela cheia.
                '--newmode fliperos-320x240@60 6.700 320 336 368 426 240 244 247 262 -hsync -vsync',
                '--addmode VGA-1 fliperos-320x240@60',
                '--newmode fliperos-640x240@60 6.700 640 336 368 426 240 244 247 262 -hsync -vsync',
                '--addmode VGA-1 fliperos-640x240@60',
                # Uma troca por partida, e a volta ao modo em que a sala abriu.
                '--output VGA-1 --mode fliperos-320x240@60',
                '--output VGA-1 --mode 0x4a',
                '--output VGA-1 --mode fliperos-640x240@60',
                '--output VGA-1 --mode 0x4a'])
            # A sala fechada com o emulador ainda aberto: a tela volta antes de sair.
            self.session(tmp, [self.CLIENT + '|40 wine fcadesnes9x.exe', '40 wine fcadesnes9x.exe'])
            self.assertEqual(self.xrandr_log(tmp)[-2:], ['--output VGA-1 --mode fliperos-320x240@60',
                                                         '--output VGA-1 --mode 0x4a'])
            # O modo e o da tabela, que a pessoa pode editar.
            table = (ROOT / 'config/fliperos-emulator-modes.conf').read_text().replace(
                'fightcade-fbneo     320x240@60', 'fightcade-fbneo     384x224@59.6')
            self.session(tmp, [fbneo, self.CLIENT], modes=table)
            self.assertIn('--output VGA-1 --mode fliperos-384x224@59.6', self.xrandr_log(tmp))
            # Noutros monitores a partida fica no modo da sala: nenhuma troca.
            self.session(tmp, [self.CLIENT, fbneo, flycast, self.CLIENT], frequency='31k')
            self.assertEqual(self.xrandr_log(tmp), [])
            # O Switchres sem modo para o monitor: fica na sala, avisa uma vez
            # e nao tenta de novo a cada segundo. Fechado o emulador, o modo
            # da sala e posto de novo (o emulador pode ter trocado sozinho).
            run = self.session(tmp, [fbneo, fbneo, fbneo, self.CLIENT], switchres=False)
            self.assertEqual(self.xrandr_log(tmp), ['--output VGA-1 --mode 0x4a'])
            self.assertEqual(run.stderr.count('could not switch to 320x240@60'), 1)

    def test_emulators_fill_the_mode_of_the_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fightcade_package(tmp / 'pkg.tar.gz')
            self.assertEqual(self.fetch(tmp).returncode, 0)
            emu = tmp / 'fc/emulator'
            fbneo, fba, flycast = (emu / 'fbneo/config/fcadefbneo.ini', emu / 'ggpofba/config/ggpofba-ng.ini',
                                   emu / 'flycast/emu.cfg')
            self.session(tmp, [self.CLIENT])

            def text(path):
                return path.read_bytes().decode()

            # Os arquivos saem dos "default" do pacote; a tela cheia no modo
            # da tabela, o jogo ja em tela cheia e o monitor 4:3 (um tubo). O
            # fim de linha do Windows fica.
            self.assertEqual(text(fbneo), '// The display mode to use for fullscreen\r\nnVidHorWidth 320\r\n'
                                          'nVidHorHeight 240\r\n\r\nnVidScrnAspectX 4\r\nnVidScrnAspectY 3\r\n'
                                          'nVidVerWidth 1280\r\nbVidAutoSwitchFull 1\r\nnVidSelect 4\r\n')
            self.assertEqual(text(fba), 'nVidWidth 320\r\nnVidHeight 240\r\nnVidScrnAspectX 4\r\nnVidScrnAspectY 3\r\n')
            # Flycast: tela cheia e 200% de estiramento em 640x240 (pixels 8:3).
            self.assertEqual(text(flycast), '[config]\nrend.Resolution = 480\nrend.ScreenStretching = 200\n\n'
                                            '[window]\nfullscreen = yes\nheight = 480\n')
            # O que a pessoa muda no emulador fica; o tamanho segue a tabela.
            fbneo.write_bytes(text(fbneo).replace('bVidAutoSwitchFull 1', 'bVidAutoSwitchFull 0')
                              .replace('nVidScrnAspectX 4', 'nVidScrnAspectX 16').encode())
            flycast.write_text(text(flycast).replace('fullscreen = yes', 'fullscreen = no'))
            table = (ROOT / 'config/fliperos-emulator-modes.conf').read_text().replace(
                'fightcade-fbneo     320x240@60', 'fightcade-fbneo     640x240@60').replace(
                'fightcade-flycast   640x240@60', 'fightcade-flycast   320x240@60')
            self.session(tmp, [self.CLIENT], modes=table)
            self.assertIn('nVidHorWidth 640\r\nnVidHorHeight 240\r\n', text(fbneo))
            self.assertIn('nVidScrnAspectX 16\r\n', text(fbneo))
            self.assertIn('bVidAutoSwitchFull 0\r\n', text(fbneo))
            self.assertIn('rend.ScreenStretching = 100\n', text(flycast))
            self.assertIn('fullscreen = no\n', text(flycast))
        # Noutro monitor: o modo da sala, sem esticar, e o formato do pacote (16:9).
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fightcade_package(tmp / 'pkg.tar.gz')
            self.assertEqual(self.fetch(tmp).returncode, 0)
            self.session(tmp, [self.CLIENT], frequency='31k')
            fbneo = (tmp / 'fc/emulator/fbneo/config/fcadefbneo.ini').read_bytes().decode()
            self.assertIn('nVidHorWidth 640\r\nnVidHorHeight 480\r\n\r\nnVidScrnAspectX 16\r\n', fbneo)
            self.assertIn('bVidAutoSwitchFull 1\r\n', fbneo)
            self.assertIn('rend.ScreenStretching = 100\n', (tmp / 'fc/emulator/flycast/emu.cfg').read_text())

    def test_window_shortcuts(self):
        rc = ElementTree.parse(ROOT / 'config/openbox-fightcade.xml').getroot()
        ns = {'ob': 'http://openbox.org/3.4/rc'}
        keys = {k.get('key'): k.find('ob:action', ns).get('name') for k in rc.findall('ob:keyboard/ob:keybind', ns)}
        self.assertEqual(keys, {'A-Tab': 'NextWindow', 'A-F4': 'Close'})
        # O resto como o do fliperos-x11-run: sem bordas e as janelas maximizadas.
        base = ElementTree.parse(ROOT / 'config/openbox-x11-run.xml').getroot()
        for tree in (rc, base):
            apps = tree.findall('ob:applications/ob:application', ns)
            self.assertEqual([a.findtext('ob:decor', namespaces=ns) for a in apps], ['no', None])
            self.assertEqual(apps[1].findtext('ob:maximized', namespaces=ns), 'yes')

    def test_image_has_what_it_needs(self):
        # O cliente (Electron) e os emuladores de 32 bits no Wine, com o
        # OpenGL de 32 bits por onde o Direct3D do Wine desenha.
        pkgs = apt_list()
        for pkg in ('libnss3', 'libxss1', 'libxtst6', 'libcups2t64', 'libatk-bridge2.0-0t64', 'libatspi2.0-0t64',
                    'libgtk-3-0t64', 'libasound2t64', 'libgbm1', 'xdg-utils'):
            self.assertIn(pkg, pkgs)
            if pkg != 'libgbm1':
                self.assertIn(pkg, (ROOT / 'tools/cabinet-update.sh').read_text())
        for text in (MKISO, (ROOT / 'tools/cabinet-update.sh').read_text()):
            self.assertIn('libgl1:i386 libgl1-mesa-dri:i386 libglx-mesa0:i386', text)
        self.assertIn('wine wine64 wine32:i386 libgl1:i386', MKISO)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ('home/fliperos', 'etc/fliperos', 'etc/modprobe.d', 'etc/sudoers.d', 'etc/profile.d',
                      'etc/systemd/system'):
                (root / d).mkdir(parents=True)
            (root / 'etc/passwd').write_text('fliperos:x:1000:1000::/home/fliperos:/bin/bash\n')
            # Uma tabela de modos de antes do Fightcade ganha as linhas dele: a
            # da sala e a de cada emulador das partidas. Uma que a pessoa ja
            # mudou fica como esta.
            (root / 'etc/fliperos/emulator-modes.conf').write_text('flycast             640x240@60      640x480@60\n'
                                                                   'fightcade-fc1       640x240@60      640x480@60\n')
            for _ in range(2):
                subprocess.run(['bash', str(ROOT / 'fliperos-rootfs.sh'), str(root)], check=True,
                               capture_output=True, timeout=120)
            self.assertTrue(os.access(root / 'opt/fliperos/bin/fliperos-fightcade', os.X_OK))
            self.assertTrue((root / 'etc/fliperos/openbox-fightcade.xml').is_file())
            self.assertEqual((root / 'etc/fliperos/emulator-modes.conf').read_text(),
                             'flycast             640x240@60      640x480@60\n'
                             'fightcade-fc1       640x240@60      640x480@60\n'
                             'fightcade           640x480@60      640x480@60\n'
                             'fightcade-fbneo     320x240@60      640x480@60\n'
                             'fightcade-snes9x    320x240@60      640x480@60\n'
                             'fightcade-flycast   640x240@60      640x480@60\n')
            # O programa em si nao vem na imagem.
            self.assertFalse((root / 'opt/fliperos/fightcade').exists())
            self.assertTrue((root / 'usr/local/share/applications/fliperos-fightcade.desktop').is_file())


class InputDriverTests(unittest.TestCase):
    """GunCon 2 (fora do mainline) e os drivers de volante hid-tmff2 e
    new-lg4ff entram sempre; --skip-* os deixa de fora."""

    def test_guncon2_usb_id_and_calibration_hook(self):
        rules = (ROOT / 'config/99-fliperos-input.rules').read_text()
        self.assertIn('0b9a', rules)
        self.assertIn('016a', rules)
        self.assertIn('fliperos-guncon2-calibrate', rules)

    def test_guncon2_and_wheel_drivers_build_by_default(self):
        self.assertIn('SKIP_INPUT_DRIVERS=false', MKISO)
        self.assertIn('\nWITH_WHEEL_DRIVERS=true\n', MKISO)
        self.assertIn('--skip-wheel-drivers) WITH_WHEEL_DRIVERS=false', MKISO)
        for repo in ('Kimplul/hid-tmff2', 'berarma/new-lg4ff'):
            self.assertIn(repo, MKISO)
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
    (docs/wiki/Latency.md)."""

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


class AudioBuildTests(unittest.TestCase):
    """Som sem servidor de som: tudo direto no ALSA, e as teclas de volume
    valendo em qualquer tela."""

    def test_hda_codec_never_sleeps(self):
        # O power_save do Ubuntu (1 s) desligava o codec em silencio e cada
        # liga-desliga estalava nas caixas ("puffs" no gabinete).
        self.assertIn('options snd_hda_intel power_save=0 power_save_controller=N', ROOTFS)
        update = (ROOT / 'tools/cabinet-update.sh').read_text()
        self.assertIn('echo 0 > /sys/module/snd_hda_intel/parameters/power_save', update)
        self.assertIn('echo N > /sys/module/snd_hda_intel/parameters/power_save_controller', update)

    def test_emulators_use_alsa(self):
        self.assertIn('\nsound sdl\n', (ROOT / 'config/mame.ini').read_text())
        for script in ('config/fliperos-kms-run', 'config/fliperos-x11-run'):
            self.assertIn('export SDL_AUDIODRIVER="${SDL_AUDIODRIVER:-alsa}"', (ROOT / script).read_text(), script)

    def test_volume_keys_are_mapped(self):
        rows = [line.split(None, 2) for line in (ROOT / 'config/fliperos-volume.triggers').read_text().splitlines()
                if line.strip() and not line.startswith('#')]
        mapped = {(event, value): command for event, value, command in rows}
        for event, action in (('KEY_VOLUMEUP', 'up'), ('KEY_VOLUMEDOWN', 'down')):
            for value in ('1', '2'):
                self.assertEqual(mapped[(event, value)], '/usr/local/bin/fliperos-setup --volume ' + action)
        self.assertEqual(mapped[('KEY_MUTE', '1')], '/usr/local/bin/fliperos-setup --volume mute')

    def test_triggerhappy_is_installed_and_runs_as_root(self):
        self.assertIn(' triggerhappy', MKISO.split('apt-get install -y --no-install-recommends')[1].split('\n\n')[0])
        self.assertIn('etc/triggerhappy/triggers.d/fliperos-volume.conf', ROOTFS)
        dropin = ROOTFS.split('triggerhappy.service.d/fliperos.conf')[1].split('EOF')[1]
        self.assertIn('ExecStart=\nExecStart=/usr/sbin/thd', dropin)
        self.assertNotIn('--user', dropin)
        entry = (ROOT / 'fliperos-setup/fliperos-setup').read_text()
        self.assertLess(entry.index('--volume)'), entry.index('if ! have gum'))

    def test_lxpanel_leaves_the_keys_to_triggerhappy(self):
        panel = (ROOT / 'config/lxde/lxpanel/LXDE/panels/panel').read_text()
        self.assertIn('type=volume', panel)
        self.assertNotIn('XF86Audio', panel)


class DraculaThemeTests(unittest.TestCase):
    """Tema Dracula no LXDE, no RGUI do RetroArch e na UI do GroovyMAME."""

    def test_lxde_uses_the_pinned_dracula_gtk(self):
        self.assertIn('sNet/ThemeName=Dracula', (ROOT / 'config/lxde/lxsession/LXDE/desktop.conf').read_text())
        script = (ROOT / 'fliperos-dracula.sh').read_text()
        self.assertRegex(script, r'DRACULA_GTK_COMMIT="[0-9a-f]{40}"')
        self.assertIn('config/openbox-3/themerc', script)
        self.assertIn('fliperos-dracula.sh', MKISO)
        for pkg in ('gtk2-engines-murrine', 'gtk2-engines-pixbuf', 'librsvg2-common'):
            self.assertIn(pkg, MKISO)

    def test_openbox_theme_uses_the_palette(self):
        theme = (ROOT / 'config/openbox-3/themerc').read_text()
        self.assertIn('window.active.title.bg.color: #282a36', theme)
        self.assertIn('menu.items.active.text.color: #ff79c6', theme)
        self.assertIn('lxde-rc.xml', ROOTFS)

    def test_retroarch_rgui_dracula(self):
        # RGUI_THEME_DRACULA e o 18o item de menu/menu_defines.h (indice 17).
        self.assertIn('rgui_menu_color_theme = "17"', (ROOT / 'config/retroarch.cfg').read_text())

    def test_groovymame_ui_colors(self):
        rows = [line.split() for line in (ROOT / 'config/mame-ui.ini').read_text().splitlines()
                if line.strip() and not line.startswith('#')]
        colors = [(key, value) for key, value in rows if key.startswith('ui_') and key.endswith('_color')]
        self.assertEqual(len({key for key, _ in colors}), 16)
        for key, value in colors:
            self.assertRegex(value, r'^[0-9a-f]{8}$', key)
        # Fora as cores, so o tamanho do texto do GroovyArcade e as pastas da
        # arte em ~/media.
        self.assertEqual({key for key, _ in rows} - {key for key, _ in colors},
                         {'font_rows', 'infos_text_size', 'ui_path', 'covers_directory', 'flyers_directory',
                          'marquees_directory', 'logos_directory'})
        self.assertIn('config/mame-ui.ini', ROOTFS)
        self.assertIn('etc/fliperos/mame/ui.ini', ROOTFS)


class SilentBootTests(unittest.TestCase):
    """Boot direto no Plymouth, sem texto (pedido no teste do gabinete)."""

    SILENT = ('loglevel=3', 'rd.udev.log_level=3', 'udev.log_level=3', 'vt.global_cursor_default=0')

    def test_kernel_lines_are_silent(self):
        common = re.search(r'BOOT_COMMON="([^"]*)"', MKISO).group(1).split()
        installed = re.search(r'BOOT_SILENT="([^"]*)"',
                              (ROOT / 'fliperos-setup/lib/bootloader.sh').read_text()).group(1).split()
        for param in self.SILENT:
            self.assertIn(param, common)
            self.assertIn(param, installed)

    def test_installed_limine_is_quiet_but_keeps_the_menu_on_a_key(self):
        text = limine_update.render(['6.18.54-15khz'], 'UUID=abc', 'quiet splash', '3')
        self.assertIn('\nquiet: yes\n', text)
        # A contagem invisivel continua: uma tecla nela mostra o menu.
        self.assertIn('timeout: 3\n', text)
        self.assertIn('Diagnostico', text)

    def test_autologin_prints_nothing(self):
        unit = MKISO.split('autologin.conf << UNIT')[1].split('UNIT\n')[0]
        self.assertIn('--skip-login --noissue', unit)
        self.assertNotIn('--noclear', unit)
        self.assertIn('.hushlogin', ROOTFS)

    def test_console_stays_quiet_after_boot(self):
        # O 10-console-messages.conf do Ubuntu (kernel.printk = 4 4 1 7)
        # passava por cima do loglevel=3: um erro do kernel depois do Plymouth
        # ia para a tela (no gabinete, o do hdaudio). O 99- vem depois.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ('home/fliperos', 'etc/fliperos/mame', 'etc/modprobe.d', 'etc/sudoers.d', 'etc/profile.d',
                      'etc/systemd/system'):
                (root / d).mkdir(parents=True)
            (root / 'etc/passwd').write_text('fliperos:x:1000:1000::/home/fliperos:/bin/bash\n')
            subprocess.run(['bash', str(ROOT / 'fliperos-rootfs.sh'), str(root)], check=True,
                           capture_output=True, timeout=120)
            conf = root / 'etc/sysctl.d/99-fliperos-console.conf'
            self.assertEqual(conf.read_text(), 'kernel.printk = 3 4 1 3\n')
            self.assertGreater(conf.name, '10-console-messages.conf')
        self.assertIn('sysctl -q -p /etc/sysctl.d/99-fliperos-console.conf',
                      (ROOT / 'tools/cabinet-update.sh').read_text())


class MotdTests(unittest.TestCase):
    """config/fliperos-motd: como abrir o menu, ao entrar no shell."""

    def motd(self, size, term='linux', ssh=False):
        env = {'PATH': '/usr/bin:/bin', 'TERM': term, 'FLIPEROS_MOTD_SIZE': size}
        if ssh:
            env['SSH_CONNECTION'] = '192.168.1.2 50000 192.168.1.111 22'
        return subprocess.run(['bash', str(ROOT / 'config/fliperos-motd')], env=env, capture_output=True,
                              text=True, timeout=30, check=True).stdout

    def test_console_shows_the_menu_command_in_the_setup_colors(self):
        out = self.motd('30 80')
        self.assertIn('|_| |_|_| .__/', out)
        self.assertIn('\x1b[35m', out)  # rosa: o indice 5 da paleta Dracula do console
        self.assertIn('fliperos-menu', out)
        self.assertNotIn('sudo fliperos-setup', out)

    def test_ssh_points_to_the_setup(self):
        # No SSH o fliperos-menu abriria o frontend no terminal da rede.
        out = self.motd('40 120', term='xterm-256color', ssh=True)
        self.assertIn('sudo fliperos-setup', out)
        self.assertIn('\x1b[38;5;212m', out)

    def test_small_screen_has_no_art(self):
        # 320x240: 40x15 caracteres.
        out = self.motd('15 40')
        self.assertNotIn('|_|', out)
        self.assertIn('FliperOS', out)
        self.assertLessEqual(len(out.splitlines()), 15)

    def test_shown_when_entering_the_shell(self):
        self.assertIn('if [[ -o login ]] && (( $+commands[fliperos-motd] )); then\n  fliperos-motd\nfi',
                      (ROOT / 'config/zshrc').read_text())
        self.assertIn('command -v fliperos-motd > /dev/null && fliperos-motd', ROOTFS)
        self.assertIn('install -Dm755 "$src/config/fliperos-motd" "$root/usr/local/bin/fliperos-motd"', ROOTFS)
        self.assertNotIn('printf', (ROOT / 'fliperos-setup/screens/main-menu.sh').read_text()
                         .split('screen_terminal() {')[1].split('\n}\n')[0])


class TerminalThemeTests(unittest.TestCase):
    """Terminal escuro: zsh com Oh My Zsh e o tema Dracula."""

    def test_pinned_ohmyzsh_and_dracula_zsh(self):
        script = (ROOT / 'fliperos-dracula.sh').read_text()
        for name in ('OHMYZSH_COMMIT', 'DRACULA_ZSH_COMMIT'):
            self.assertRegex(script, name + r'="[0-9a-f]{40}"')
        self.assertIn('custom/themes/dracula.zsh-theme', script)
        # O tema procura o lib/async.zsh ao lado do proprio arquivo.
        self.assertIn('custom/themes/lib/async.zsh', script)
        self.assertIn(' zsh', MKISO.split('apt-get install -y --no-install-recommends')[1].split('\n\n')[0])

    def test_zshrc(self):
        zshrc = (ROOT / 'config/zshrc').read_text()
        self.assertIn('export ZSH=/usr/local/share/oh-my-zsh', zshrc)
        self.assertIn('ZSH_THEME=dracula', zshrc)
        self.assertIn("zstyle ':omz:update' mode disabled", zshrc)
        # Cache no home: /usr/local/share/oh-my-zsh e do root.
        self.assertIn('ZSH_CACHE_DIR=$HOME/.cache/oh-my-zsh', zshrc)
        # No console do Linux, sem os simbolos que a fonte nao tem, e com o
        # cursor de volta (o boot o esconde ate o Plymouth).
        console = zshrc.split('if [[ $TERM == linux ]]; then')[1].split('fi\n')[0]
        self.assertIn('DRACULA_ARROW_ICON="> "', console)
        self.assertIn("printf '\\e[?25h'", console)
        self.assertLess(zshrc.index('DRACULA_ARROW_ICON'), zshrc.index('source "$ZSH/oh-my-zsh.sh"'))
        self.assertIn('config/zshrc', ROOTFS)

    def test_user_shell_is_zsh_when_installed(self):
        self.assertIn('usr/bin/zsh', ROOTFS)
        self.assertIn(r's|^\(fliperos:.*:\)/bin/bash$|\1/usr/bin/zsh|', ROOTFS)


class EmulatorMenuTests(unittest.TestCase):
    """Emuladores no menu do LXDE: saem do desktop pelo fliperos-launch."""

    # So os de jogos (Game;): o Screen Resolution fica em Preferencias.
    APPS = sorted(p for p in (ROOT / 'config/applications').glob('fliperos-*.desktop')
                  if 'Categories=Game;' in p.read_text())
    # O que mostra o atalho (TryExec): o binario do emulador; o Model 2 so
    # precisa do Wine (o emulador o usuario copia), e o Fightcade aparece
    # depois de baixado pelo Setup.
    TRYEXEC = {'dolphin': '/usr/local/bin/dolphin-emu', 'model2': '/usr/bin/wine',
               'fightcade': '/opt/fliperos/fightcade/fightcade'}

    def entry(self, path):
        return dict(line.split('=', 1) for line in path.read_text().splitlines() if '=' in line)

    def test_every_emulator_has_an_entry(self):
        names = {p.stem.replace('fliperos-', '') for p in self.APPS}
        self.assertEqual(names, {'retroarch', 'groovymame', 'flycast', 'pcsx2', 'supermodel',
                                 'dolphin', 'openbor', 'model2', 'fightcade'})

    def test_entries_go_through_the_launcher(self):
        launcher = (ROOT / 'config/fliperos-launch').read_text()
        for path in self.APPS:
            name = path.stem.replace('fliperos-', '')
            e = self.entry(path)
            self.assertEqual(e['Exec'], '/opt/fliperos/bin/fliperos-launch ' + name)
            self.assertEqual(e['TryExec'], self.TRYEXEC.get(name, '/usr/local/bin/' + name))
            self.assertIn('Game;', e['Categories'])
            self.assertIn('  %s) label=' % name, launcher)

    def test_every_icon_is_installed(self):
        own = {p.name for p in (ROOT / 'config/icons').glob('*.svg')}
        for path in self.APPS:
            icon = self.entry(path)['Icon']
            self.assertTrue(icon.startswith('/usr/local/share/pixmaps/'), icon)
            name = icon.rsplit('/', 1)[1]
            # Os proprios (config/icons) ou os que o build copia de cada projeto.
            self.assertTrue(name in own or ('pixmaps/' + name) in MKISO or name == 'com.libretro.RetroArch.svg',
                            name)
        self.assertIn('rm -f /usr/local/share/applications/com.libretro.RetroArch.desktop', MKISO)

    def test_session_only_runs_known_requests(self):
        session = (ROOT / 'config/fliperos-session').read_text()
        self.assertIn('fliperos-next', session)
        self.assertIn('/opt/fliperos/bin/fliperos-kms-run | /opt/fliperos/bin/fliperos-x11-run)', session)
        self.assertIn('fliperos-launch', ROOTFS)


class EmulatorModeTests(unittest.TestCase):
    """fliperos-x11-run: o modo de cada emulador (640x240 nos de 480i num
    monitor de 15 kHz), o --mode para qualquer programa e a imagem esticada
    para preencher o modo."""

    # "15k" e o que o setup grava (monitor_frequency); com "15" o teste nao
    # pegava que o script so aceitava "15" e mandava o gabinete para 480i.
    def run_x11(self, args, frequency='15k', modes=None):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bin_dir = tmp / 'bin'
            bin_dir.mkdir()
            # xinit falso: mostra o modo pedido e o comando.
            (bin_dir / 'xinit').write_text('#!/bin/bash\necho "MODE=$FLIPEROS_RES_W $FLIPEROS_RES_H $FLIPEROS_RES_HZ"\n'
                                           'echo "ARGS=$*"\n')
            for prog in ('flycast', 'dolphin-emu', 'pcsx2', 'myprog', 'supermodel', 'hypseus', 'fightcade'):
                (bin_dir / prog).write_text('#!/bin/sh\n')
            for p in bin_dir.iterdir():
                p.chmod(0o755)
            (tmp / 'fliperos.conf').write_text('frequency=%s\n' % frequency)
            (tmp / 'modes.conf').write_text(modes or (ROOT / 'config/fliperos-emulator-modes.conf').read_text())
            env = dict(os.environ, PATH='%s:%s' % (bin_dir, os.environ['PATH']), HOME=str(tmp),
                       FLIPEROS_CONF=str(tmp / 'fliperos.conf'), FLIPEROS_MODES=str(tmp / 'modes.conf'))
            env.pop('DISPLAY', None)
            return subprocess.run(['bash', str(ROOT / 'config/fliperos-x11-run')] + args,
                                  capture_output=True, text=True, env=env)

    def test_480i_emulators_run_at_640x240_on_15khz(self):
        out = self.run_x11(['flycast', 'game.gdi']).stdout
        self.assertIn('MODE=640 240 60', out)
        # 4:3 esticado para preencher o 640x240 (8:3 em pixels).
        self.assertIn('-config window:fullscreen=yes,config:rend.ScreenStretching=200 game.gdi', out)
        out = self.run_x11(['dolphin-emu']).stdout
        self.assertIn('MODE=640 240 60', out)
        self.assertIn('-C Dolphin.Display.Fullscreen=True -C GFX.Settings.AspectRatio=3', out)

    def test_nothing_interlaced_on_15khz(self):
        # No gabinete o Flycast abria em 640x480 (480i): frequency=15k nao
        # batia com "15". Versoes antigas gravavam "15".
        for freq in ('15k', '15'):
            self.assertIn('MODE=640 240 60', self.run_x11(['flycast'], frequency=freq).stdout, freq)
        for line in (ROOT / 'config/fliperos-emulator-modes.conf').read_text().splitlines():
            if line.strip() and not line.startswith('#'):
                height = int(line.split()[1].split('x')[1].split('@')[0])
                # So o Fightcade: a sala de jogos e uma pagina de desktop.
                self.assertLessEqual(height, 480 if line.split()[0] == 'fightcade' else 240, line)
        out = self.run_x11(['supermodel', 'game.zip']).stdout
        self.assertIn('MODE=640 240 57.524', out)
        self.assertIn('-fullscreen -res=640,240 -stretch game.zip', out)
        self.assertIn('-res=496,384', self.run_x11(['supermodel'], frequency='31k').stdout)

    def test_stretched_200_percent_at_640x240(self):
        # 640x240 tem pixels 8:3; para o 4:3 encher o tubo, cada emulador estica
        # a imagem para a largura toda (o "200%").
        self.assertIn('rend.ScreenStretching=200', self.run_x11(['flycast']).stdout)
        self.assertIn('GFX.Settings.AspectRatio=3', self.run_x11(['dolphin-emu']).stdout)
        self.assertIn('-stretch', self.run_x11(['supermodel']).stdout)
        # Hypseus: jogo e player primeiro, opcoes no fim.
        out = self.run_x11(['hypseus', 'lair', 'vldp', '-framefile', 'f.txt']).stdout
        self.assertIn('hypseus lair vldp -framefile f.txt -fullscreen -x 640 -y 240 -ignore_aspect_ratio', out)

    def test_old_tables_lose_the_384_line_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ('home/fliperos', 'etc/fliperos', 'etc/modprobe.d', 'etc/sudoers.d', 'etc/profile.d',
                      'etc/systemd/system'):
                (root / d).mkdir(parents=True)
            (root / 'etc/passwd').write_text('fliperos:x:1000:1000::/home/fliperos:/bin/bash\n')
            (root / 'etc/fliperos/emulator-modes.conf').write_text(
                'flycast             640x240@60      640x480@60\n'
                'supermodel          496x384@57.524  496x384@57.524\n'
                'fliperos-model2     320x240@60      496x384@57.524\n')
            subprocess.run(['bash', str(ROOT / 'fliperos-rootfs.sh'), str(root)], check=True,
                           capture_output=True, timeout=120)
            table = (root / 'etc/fliperos/emulator-modes.conf').read_text()
            self.assertIn('supermodel          640x240@57.524  496x384@57.524\n', table)
            # Linha mudada pela pessoa fica como esta.
            self.assertIn('fliperos-model2     320x240@60      496x384@57.524\n', table)

    def test_fightcade_lobby_gets_480_lines_and_a_mouse_cursor(self):
        # A sala de jogos nao cabe em 240 linhas: 640x480 (entrelacado no
        # 15 kHz), com o cursor, que os emuladores de jogo direto nao tem.
        for freq in ('15k', '31k'):
            out = self.run_x11(['fightcade'], frequency=freq).stdout
            self.assertIn('MODE=640 480 60', out, freq)
            self.assertNotIn('-nocursor', out)
        self.assertIn('-nocursor', self.run_x11(['myprog']).stdout)

    def test_other_monitors_keep_480(self):
        out = self.run_x11(['flycast'], frequency='31k').stdout
        self.assertIn('MODE=640 480 60', out)
        self.assertIn('rend.ScreenStretching=100', out)

    def test_any_program_with_mode(self):
        out = self.run_x11(['--mode', '640x240@60', 'myprog', '-x']).stdout
        self.assertIn('MODE=640 240 60', out)
        self.assertIn('myprog -x', out)
        self.assertIn('MODE=320 240 60', self.run_x11(['myprog']).stdout)
        r = self.run_x11(['--mode', '640x240', 'myprog'])
        self.assertEqual(r.returncode, 2)

    def test_mouse_cursor_only_for_emulators_with_a_mouse_interface(self):
        # No gabinete o mouse sumia ao abrir o PCSX2 (lista de jogos, BIOS).
        for prog in ('pcsx2', 'dolphin-emu', 'flycast'):
            self.assertNotIn('-nocursor', self.run_x11([prog]).stdout, prog)
        self.assertIn('-nocursor', self.run_x11(['myprog']).stdout)
        client = (ROOT / 'config/fliperos-x11-client').read_text()
        self.assertIn('xsetroot -cursor_name left_ptr', client)

    def test_window_manager_fits_the_window_to_each_mode(self):
        # Como o galauncher.xinitrc do GroovyArcade: sem gerenciador de
        # janelas, a janela do GroovyMAME ficava com o tamanho do modo em que
        # abriu (320x240 numa tela de 640x480, visto no gabinete).
        client = (ROOT / 'config/fliperos-x11-client').read_text()
        wm = client.index('openbox --config-file "${FLIPEROS_OPENBOX_RC:-/etc/fliperos/openbox-x11-run.xml}" &')
        self.assertLess(client.index('_NET_SUPPORTING_WM_CHECK'), client.index('exec /usr/local/bin/switchres'))
        self.assertLess(wm, client.index('exec /usr/local/bin/switchres'))
        import xml.etree.ElementTree as ET
        rc = ET.parse(ROOT / 'config/openbox-x11-run.xml').getroot()
        ns = {'o': 'http://openbox.org/3.4/rc'}
        self.assertEqual(rc.find('o:applications/o:application/o:decor', ns).text, 'no')
        self.assertIsNone(rc.find('o:keyboard/o:keybind', ns))
        # Preto na troca de modo: o fundo do X e a moldura do openbox (branca
        # no tema padrao, vista no gabinete entre a interface e o jogo).
        self.assertEqual(rc.find('o:theme/o:name', ns).text, 'FliperOS-Black')
        theme = (ROOT / 'config/openbox-black-themerc').read_text()
        for key in ('window.active.client.color', 'window.inactive.client.color'):
            self.assertIn('%s: #000000\n' % key, theme)
        self.assertLess(client.index('xsetroot -solid black'), client.index('openbox --config-file'))
        # Opcoes a mais do Switchres de quem chamou (a interface do GroovyMAME
        # pede --interlace 0).
        self.assertIn('args+=(${FLIPEROS_SWITCHRES_OPTS:-})', client)
        self.assertLess(client.index('FLIPEROS_SWITCHRES_OPTS'), client.index('exec /usr/local/bin/switchres'))
        self.assertIn('"$root/usr/share/themes/FliperOS-Black/openbox-3/themerc"', ROOTFS)
        self.assertIn('install -Dm644 "$src/config/openbox-x11-run.xml" "$root/etc/fliperos/openbox-x11-run.xml"',
                      ROOTFS)

    def test_pcsx2_ini_is_adjusted_after_first_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            ini = Path(tmp) / 'PCSX2.ini'
            ini.write_text('[UI]\nSettingsVersion = 1\nStartFullscreen = false\n\n[EmuCore/GS]\nAspectRatio = Auto 4:3/3:2\n')
            subprocess.run(['bash', str(ROOT / 'config/fliperos-ini-set'), str(ini), 'EmuCore/GS', 'AspectRatio', 'Stretch'], check=True)
            subprocess.run(['bash', str(ROOT / 'config/fliperos-ini-set'), str(ini), 'UI', 'StartFullscreen', 'true'], check=True)
            subprocess.run(['bash', str(ROOT / 'config/fliperos-ini-set'), str(ini), 'New', 'Key', 'v'], check=True)
            self.assertEqual(ini.read_text(), '[UI]\nSettingsVersion = 1\nStartFullscreen = true\n\n'
                                              '[EmuCore/GS]\nAspectRatio = Stretch\n\n[New]\nKey = v\n')

    def test_modes_table_is_valid(self):
        for line in (ROOT / 'config/fliperos-emulator-modes.conf').read_text().splitlines():
            if not line.strip() or line.startswith('#'):
                continue
            cols = line.split()
            self.assertEqual(len(cols), 3, line)
            for mode in cols[1:]:
                self.assertRegex(mode, r'^\d+x\d+@[\d.]+$', line)
        self.assertIn('emulator-modes.conf', ROOTFS)


class NewEmulatorBuildTests(unittest.TestCase):
    """Hypseus, OpenBOR, Dolphin, Wine (Model 2), Steam e Heroic (GOG)."""

    def test_pinned_versions(self):
        self.assertRegex(MKISO, r'HYPSEUS_TAG="v2\.[0-9.]+"')   # a serie 3 exige SDL3
        self.assertRegex(MKISO, r'OPENBOR_COMMIT="[0-9a-f]{40}"')
        self.assertRegex(MKISO, r'DOLPHIN_TAG="[0-9]{4}[a-z]?"')
        self.assertRegex(MKISO, r'HEROIC_SHA256="[0-9a-f]{64}"')

    def test_every_one_can_be_skipped_and_runs_in_order(self):
        main = MKISO.split('# ── Main')[1]
        for flag, step in (('--skip-hypseus', 'build_hypseus_chroot'), ('--skip-openbor', 'build_openbor_chroot'),
                           ('--skip-dolphin', 'build_dolphin_chroot'), ('--skip-wine', 'install_wine_chroot'),
                           ('--skip-steam', 'install_steam_chroot'), ('--skip-heroic', 'install_heroic_chroot')):
            self.assertIn(flag + ')', MKISO)
            self.assertIn('\n' + step + '\n', main)
        self.assertLess(main.index('build_supermodel_chroot'), main.index('build_hypseus_chroot'))
        self.assertLess(main.index('install_heroic_chroot'), main.index('create_squashfs'))

    def test_openbor_starts_fullscreen(self):
        # Em janela ele abria em 2x de tamanho fixo (640x480 num modo de
        # 320x240, so o meio aparecia): tela cheia no seletor de paks e no jogo.
        body = MKISO.split('build_openbor_chroot() {')[1].split('\n}\n')[0]
        self.assertIn("sed -i 's/^static int isFull = 0;/static int isFull = 1;/' engine/sdl/menu.c", body)
        self.assertIn("sed -i 's/^\\([[:space:]]*savedata\\.fullscreen = \\)0;/\\11;/' engine/openbor.c", body)
        self.assertLess(body.index("grep -q 'savedata.fullscreen = 1;'"), body.index('cmake -S . -B build'))

    def test_steam_installs_without_questions(self):
        body = MKISO.split('install_steam_chroot() {')[1].split('\n}\n')[0]
        self.assertIn('DEBIAN_FRONTEND=noninteractive apt-get install -y steam-installer', body)
        self.assertLess(body.index('enable_i386_chroot'), body.index('steam-installer'))

    def test_model2_emulator_is_not_redistributed(self):
        # Freeware de codigo fechado, sem permissao clara: o usuario copia.
        self.assertNotRegex(MKISO, r'(?i)m2emulator.*(http|zip)')
        helper = (ROOT / 'config/fliperos-model2').read_text()
        self.assertIn('/opt/fliperos/model2', helper)
        self.assertIn('WINEPREFIX=', helper)


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


class DocsTests(unittest.TestCase):
    """O README e o resumo; o detalhe fica nas paginas de docs/wiki, que o
    tools/wiki-publish.sh publica na wiki do GitHub."""
    WIKI = ROOT / 'docs/wiki'
    URL = 'https://github.com/juniorterin/fliperOS/wiki'
    PAGE = r'[A-Za-z0-9_-]+'

    def pages(self):
        return {p.stem for p in self.WIKI.glob('*.md')} - {'Home', '_Sidebar'}

    def test_links_between_pages_exist(self):
        for page in self.WIKI.glob('*.md'):
            text = page.read_text()
            for target in re.findall(r'\]\(([^)]+)\)', text):
                if target.startswith(('https://', 'http://', '#')):
                    continue
                # Fora isso, so outra pagina da wiki: la nao ha os arquivos do repositorio.
                match = re.fullmatch(r'(%s)\.md(#.*)?' % self.PAGE, target)
                self.assertTrue(match, '%s: link %s' % (page.name, target))
                self.assertIn(match.group(1), self.pages() | {'Home'}, '%s: link %s' % (page.name, target))
            # As referencias "secao N" eram do README de uma pagina so.
            self.assertNotRegex(text, r'se[cç][aã]o \d', page.name)

    def test_every_page_is_in_the_index_and_in_the_sidebar(self):
        self.assertGreaterEqual(len(self.pages()), 10)
        for index in ('Home.md', '_Sidebar.md'):
            listed = set(re.findall(r'\]\((%s)\.md\)' % self.PAGE, (self.WIKI / index).read_text())) - {'Home'}
            self.assertEqual(listed, self.pages(), index)

    def test_readme_is_the_short_version(self):
        readme = (ROOT / 'README.md').read_text()
        self.assertLess(len(readme), 4000)
        # Leva a cada pagina da wiki, e so a paginas que existem.
        linked = set(re.findall(re.escape(self.URL) + r'/(%s)' % self.PAGE, readme))
        self.assertEqual(linked, self.pages())
        for needed in ('dd if=fliperos-0.7.iso', 'fliperos-mkiso.sh', 'tests/test_setup.py', 'tools/wiki-publish.sh'):
            self.assertIn(needed, readme)

    def test_publish_writes_wiki_links(self):
        # Aqui os links levam o .md (funcionam no repositorio); na wiki, nao.
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(['bash', str(ROOT / 'tools/wiki-publish.sh'), '--to', tmp], check=True,
                           capture_output=True, timeout=60)
            out = Path(tmp)
            self.assertEqual({p.name for p in out.iterdir()}, {p.name for p in self.WIKI.glob('*.md')})
            home = (out / 'Home.md').read_text()
            self.assertIn('[Emuladores](Emuladores)', home)
            self.assertIn('[Fightcade 2](Fightcade-2)', (out / '_Sidebar.md').read_text())
            for page in out.iterdir():
                self.assertNotRegex(page.read_text(), r'\]\(%s\.md' % self.PAGE, page.name)
            # Os enderecos de fora ficam como estao.
            self.assertIn('(https://github.com/charmbracelet/gum)', home)
            self.assertIn('tree/main/docs/wiki)', home)

    def test_wikipedia_draft_is_wikitext_and_cites_existing_pages(self):
        text = (ROOT / 'docs/wikipedia/FliperOS.wiki').read_text()
        # Wikitexto, nao Markdown (o link "[x](y)"), e com tudo o que abre fechado.
        self.assertNotIn('](', text)
        for opened, closed in (('{{', '}}'), ('[[', ']]')):
            self.assertEqual(text.count(opened), text.count(closed), opened)
        self.assertEqual(len(re.findall(r'<ref[ >]', text)), text.count('</ref>') + len(re.findall(r'<ref [^>]*/>', text)))
        # Cada nome de referencia e definido uma vez so.
        named = re.findall(r'<ref name="([^"]+)">', text)
        self.assertEqual(len(named), len(set(named)))
        for used in re.findall(r'<ref name="([^"]+)" />', text):
            self.assertIn(used, named)
        # As referencias sao as paginas daqui: uma renomeada quebraria o artigo.
        cited = re.findall(r'fliperOS/blob/main/([^ |}]+)', text)
        self.assertGreaterEqual(len(cited), 10)
        for path in cited:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_html_reference_is_built_from_both(self):
        script = (ROOT / 'tools/render-docs.py').read_text()
        self.assertIn("root / 'README.md'", script)
        self.assertIn("'_Sidebar.md'", script)
        html = (ROOT / 'fliperos-doc.html').read_text()
        for title in ('Fightcade 2', 'Sistema instalado', 'Build e testes'):
            self.assertIn('>%s</h1>' % title, html)
        # Os links entre paginas viram links dentro do arquivo.
        self.assertIn('href="#Fightcade-2"', html)
        for page in self.pages():
            self.assertNotIn('href="%s.md' % page, html)
            self.assertNotIn('href="%s/%s"' % (self.URL, page), html)


class ReleaseTests(unittest.TestCase):
    """Toda ISO nova vai para os Releases do GitHub com o changelog da versao,
    no formato dos releases do GroovyArcade (tools/release-publish.sh)."""
    SCRIPT = ROOT / 'tools/release-publish.sh'
    VERSION = re.search(r'^FLIPEROS_VERSION="(.*)"$', MKISO, re.M).group(1)

    def notes(self, version):
        return subprocess.run(['bash', str(self.SCRIPT), '--notes', version], capture_output=True, text=True, timeout=60)

    def test_changelog_has_the_version_of_the_build(self):
        # Subir o FLIPEROS_VERSION sem escrever o que mudou quebra aqui.
        changelog = (ROOT / 'CHANGELOG.md').read_text()
        versions = re.findall(r'^## (\S+)$', changelog, re.M)
        self.assertEqual(versions[0], self.VERSION)
        self.assertEqual(len(versions), len(set(versions)))
        self.assertEqual(len(versions), len(re.findall(r'^## ', changelog, re.M)))

    def test_release_text_is_the_section_of_the_version(self):
        result = self.notes(self.VERSION)
        self.assertEqual(result.returncode, 0, result.stderr)
        # As secoes do GroovyArcade: OS, Packages, gasetup, gatools.
        for heading in ('**Mudanças no sistema:**', '**Mudanças nos pacotes:**',
                        '**Mudanças no fliperos-setup:**', '**Mudanças nas ferramentas:**'):
            self.assertIn(heading + '\n\n- ', result.stdout)
        self.assertNotIn('\n## ', '\n' + result.stdout)
        self.assertNotIn('# Changelog', result.stdout)
        self.assertNotEqual(result.stdout[0], '\n')

    def test_version_without_section_is_not_published(self):
        result = self.notes('99.9')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('CHANGELOG.md', result.stderr)
        self.assertEqual(result.stdout, '')

    def test_only_the_audited_iso_without_wifi_goes_public(self):
        script = self.SCRIPT.read_text()
        audit = script.index('tools/verify-iso.sh" "$iso"')
        wifi = script.index('NetworkManager/system-connections/')
        self.assertLess(audit, wifi)
        self.assertLess(wifi, script.index('gh release create'))
        # O verify-iso extrai onde o release-publish vai ler.
        self.assertIn('FLIPEROS_VERIFY_DIR=$audit', script)
        self.assertIn('work=${FLIPEROS_VERIFY_DIR:-', (ROOT / 'tools/verify-iso.sh').read_text())
        # A senha do --wifi-psk vai em texto para a imagem.
        self.assertIn('/etc/NetworkManager/system-connections', MKISO)

    def test_iso_over_the_github_limit_goes_in_parts(self):
        script = self.SCRIPT.read_text()
        self.assertIn('limit=2147483648 part=1900M', script)
        self.assertIn('split -b "$part" -a 3 --numeric-suffixes=1', script)
        self.assertIn('copy /b', script)
        # O release e do commit de que a ISO saiu, e nao troca um que ja existe sem pedir.
        self.assertIn('--target "$commit"', script)
        self.assertRegex(script, r'\(\(replace\)\) \|\| die')

    def test_release_tools_are_in_the_vmtest_image(self):
        dockerfile = (ROOT / 'tools/Dockerfile.vmtest').read_text()
        for package in ('gh', 'git', 'ca-certificates', 'xorriso', 'squashfs-tools'):
            self.assertRegex(dockerfile, r'\s%s\s' % re.escape(package))


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
        # glcore e gl usam o contexto KMS; o vulkan (khr_display) nao troca.
        self.assertEqual(self.values()['video_driver'], 'glcore')
        gl = [line for line in (ROOT / 'config/retroarch-gl.cfg').read_text().splitlines()
              if line and not line.startswith('#')]
        self.assertEqual(gl, ['video_driver = "gl"'])
        self.assertIn('install -Dm644 "$src/config/retroarch-gl.cfg" "$root/etc/fliperos/retroarch/retroarch-gl.cfg"',
                      (ROOT / 'fliperos-rootfs.sh').read_text())

    def test_initial_mode_is_the_active_one(self):
        values = self.values()
        self.assertEqual((values['video_fullscreen_x'], values['video_fullscreen_y']), ('0', '0'))

    def test_audio_is_sdl2_over_alsa(self):
        # Sem servidor de som: o SDL do RetroArch sai direto no ALSA.
        self.assertEqual(self.values()['audio_driver'], 'sdl2')
        self.assertIn('export SDL_AUDIODRIVER="${SDL_AUDIODRIVER:-alsa}"',
                      (ROOT / 'config/fliperos-kms-run').read_text())

    def test_standard_latency_values(self):
        values = self.values()
        self.assertEqual(values['video_max_swapchain_images'], '2')
        self.assertEqual(values['video_threaded'], 'false')
        self.assertEqual(values['input_poll_type_behavior'], '2')
        # Os do modo de baixa latencia ficam desligados no arquivo da ISO.
        self.assertEqual(values['video_frame_delay_auto'], 'false')
        self.assertEqual(values['preemptive_frames_enable'], 'false')
        self.assertEqual(values['run_ahead_enabled'], 'false')

    def test_online_updater_can_write(self):
        # Pastas do usuario: o Core Downloader e as atualizacoes do menu
        # gravam sem root. Nada disso em /etc.
        values = self.values()
        self.assertEqual(values['libretro_directory'], '/opt/fliperos/retroarch/cores')
        self.assertEqual(values['libretro_info_path'], '/opt/fliperos/retroarch/info')
        self.assertEqual(values['joypad_autoconfig_dir'], '/opt/fliperos/retroarch/autoconfig')
        body = MKISO.split("<< 'RASCRIPT'")[1].split('\nRASCRIPT\n')[0]
        self.assertIn('RA_DIR=/opt/fliperos/retroarch', body)
        self.assertIn('chown -R fliperos:fliperos "$RA_DIR"', body)
        self.assertIn('libretro/libretro-core-info __RA_CORE_INFO_COMMIT__', body)
        self.assertNotIn('/etc/fliperos/retroarch/cores', MKISO)
        for name in ('RA_CORE_INFO_COMMIT', 'RA_AUTOCONFIG_COMMIT'):
            self.assertRegex(MKISO, name + r'="[0-9a-f]{40}"')

    def test_sdl2_joypad_driver_can_be_chosen(self):
        # O sdl2 so aparece em Drivers > Controle se o RetroArch tiver SDL2; o
        # arquivo do sistema vem por cima do do usuario a cada abertura, entao
        # nao fixa o driver de controle (padrao compilado: udev).
        values = self.values()
        self.assertNotIn('input_joypad_driver', values)
        self.assertEqual(values['input_driver'], 'udev')
        body = MKISO.split("<< 'RASCRIPT'")[1].split('\nRASCRIPT\n')[0]
        self.assertIn('libsdl2-dev', body)
        self.assertIn('--enable-sdl2', body)
        self.assertNotIn('--disable-sdl2', body)

    def test_mame2010_is_built_without_fortify(self):
        # O gcc do Ubuntu liga o _FORTIFY_SOURCE sozinho, e com ele a glibc
        # aborta o MAME 0.139 ao iniciar uma CPU H8/3002 (Namco System 12).
        body = MKISO.split("<< 'RASCRIPT'")[1].split('\nRASCRIPT\n')[0]
        self.assertIn('make -C "$dir" -f "$mk" -j"$(nproc)" "$@"', body)
        self.assertIn('\nbuild_core libretro/mame2010-libretro ARCHOPTS=-U_FORTIFY_SOURCE\n', body)
        self.assertIn('[[ $symbols != *__strcat_chk* ]]', (ROOT / 'tools/verify-iso.sh').read_text())

    def test_retroarch_gets_the_system_config(self):
        # E, se o Setup gravou, os botoes de cada jogador por cima.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            prog = tmp / 'retroarch'
            prog.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
            prog.chmod(0o755)
            buttons = tmp / 'buttons.cfg'
            (tmp / 'debug').write_text('')  # modo debug: a saida na tela, nao no log
            env = dict(os.environ, FLIPEROS_RA_BUTTONS=str(buttons), FLIPEROS_DEBUG_FLAG=str(tmp / 'debug'),
                       PATH='%s:%s' % (tmp, os.environ['PATH']))
            env.pop('DISPLAY', None)
            run = lambda: subprocess.run(['bash', str(ROOT / 'config/fliperos-kms-run'), 'retroarch', '-L', 'x'],
                                         capture_output=True, text=True, env=env).stdout.split('\n')
            self.assertEqual(run()[:3], ['--appendconfig', '/etc/fliperos/retroarch/retroarch.cfg', '-L'])
            buttons.write_text('')
            self.assertEqual(run()[:2], ['--appendconfig', '/etc/fliperos/retroarch/retroarch.cfg|%s' % buttons])

    def test_glcore_falls_back_to_gl_without_opengl_3_2_core(self):
        # O glcore nao abre em placa que so tem OpenGL 2.x: o fliperos-kms-run
        # pergunta ao Mesa (eglinfo) e passa o "gl" por cima. Sem resposta
        # (sem eglinfo, EGL que nao abre), vale o glcore do arquivo.
        head = 'GBM platform:\nEGL API version: 1.5\nEGL client APIs: OpenGL OpenGL_ES \n'
        core = 'OpenGL core profile version: %s (Core Profile) Mesa 25.2.8\n'
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            prog = tmp / 'retroarch'
            prog.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
            prog.chmod(0o755)
            cfg = tmp / 'retroarch.cfg'
            gl = ROOT / 'config/retroarch-gl.cfg'
            (tmp / 'debug').write_text('')
            env = dict(os.environ, FLIPEROS_RA_CFG=str(cfg), FLIPEROS_RA_GL=str(gl),
                       FLIPEROS_RA_BUTTONS=str(tmp / 'buttons.cfg'), FLIPEROS_DEBUG_FLAG=str(tmp / 'debug'),
                       PATH='%s:%s' % (tmp, os.environ['PATH']))
            env.pop('DISPLAY', None)

            def appended(driver, eglinfo):
                cfg.write_text('video_driver = "%s"\n' % driver)
                fake = tmp / 'eglinfo'
                if eglinfo is None:
                    fake.unlink(missing_ok=True)
                else:
                    (tmp / 'eglinfo.txt').write_text(eglinfo)
                    fake.write_text('#!/bin/sh\necho "$*" > "%s/eglinfo.args"\ncat "%s/eglinfo.txt"\n' % (tmp, tmp))
                    fake.chmod(0o755)
                out = subprocess.run(['bash', str(ROOT / 'config/fliperos-kms-run'), 'retroarch', '-L', 'x'],
                                     capture_output=True, text=True, env=env).stdout.split('\n')
                self.assertEqual((out[0], out[2]), ('--appendconfig', '-L'))
                return out[1].split('|')[1:]

            self.assertEqual(appended('glcore', head), [str(gl)])  # so OpenGL 2.x: sem perfil core
            self.assertEqual((tmp / 'eglinfo.args').read_text().split(), ['-B', '-p', 'gbm', '-a', 'glcore'])
            self.assertEqual(appended('glcore', head + core % '3.1'), [str(gl)])
            for version in ('3.2', '3.3', '4.5', '10.0'):
                self.assertEqual(appended('glcore', head + core % version), [], version)
            self.assertEqual(appended('glcore', 'GBM platform:\neglinfo: eglInitialize failed\n'), [])
            self.assertEqual(appended('glcore', None), [])
            # Quem trocou o driver no arquivo do sistema fica com o dele.
            self.assertEqual(appended('vulkan', head), [])


class RetroArchMameRemapTests(unittest.TestCase):
    """Os cores de MAME do RetroArch leem Button 1-6 do RetroPad numa ordem
    propria: o remap leva o painel (Y X L / B A R) ao botao de mesmo numero."""

    IDS = {'b': 0, 'y': 1, 'a': 8, 'x': 9, 'l': 10, 'r': 11}
    PANEL = ['y', 'x', 'l', 'b', 'a', 'r']   # botoes 1 a 6 do painel no RetroPad
    CORES = {'MAME': ['b', 'a', 'y', 'x', 'l', 'r'],          # input_retro.cpp
             'MAME 2010': ['a', 'b', 'x', 'y', 'l', 'r']}     # retromain.c

    def test_panel_button_n_is_game_button_n(self):
        for core, order in self.CORES.items():
            text = (ROOT / 'config/retroarch-remaps' / (core + '.rmp')).read_text()
            self.assertTrue(text.startswith('# FliperOS'), core)
            for player in range(1, 5):
                for n, pad in enumerate(self.PANEL):
                    self.assertIn('input_player%d_btn_%s = "%d"\n' % (player, pad, self.IDS[order[n]]), text,
                                  (core, player, n + 1))

    def test_installed_without_overwriting_a_user_remap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ('home/fliperos', 'etc/fliperos/mame', 'etc/modprobe.d', 'etc/sudoers.d', 'etc/profile.d',
                      'etc/systemd/system'):
                (root / d).mkdir(parents=True)
            (root / 'etc/passwd').write_text('fliperos:x:1000:1000::/home/fliperos:/bin/bash\n')
            remaps = root / 'home/fliperos/.config/retroarch/config/remaps'
            (remaps / 'MAME 2010').mkdir(parents=True)
            (remaps / 'MAME 2010' / 'MAME 2010.rmp').write_text('input_player1_btn_b = "0"\n')
            subprocess.run(['bash', str(ROOT / 'fliperos-rootfs.sh'), str(root)], check=True,
                           capture_output=True, timeout=120)
            self.assertEqual((remaps / 'MAME' / 'MAME.rmp').read_text(),
                             (ROOT / 'config/retroarch-remaps/MAME.rmp').read_text())
            self.assertEqual((remaps / 'MAME 2010' / 'MAME 2010.rmp').read_text(), 'input_player1_btn_b = "0"\n')


class ButtonMappingTests(unittest.TestCase):
    """config/fliperos-buttons: os botoes de cada jogador no RetroArch e no GroovyMAME."""

    def setUp(self):
        self.rc = load_script('buttons', 'config/fliperos-buttons')

    def test_mame_codes(self):
        # Na numeracao do SDL (joystickprovider sdljoy): botao 0 = BUTTON1.
        code = self.rc.mame_code
        self.assertEqual(code(0, 'b0'), 'JOYCODE_1_BUTTON1')
        self.assertEqual(code(1, 'b7'), 'JOYCODE_2_BUTTON8')
        self.assertEqual(code(0, '-a0'), 'JOYCODE_1_XAXIS_LEFT_SWITCH')
        self.assertEqual(code(0, '+a1'), 'JOYCODE_1_YAXIS_DOWN_SWITCH')
        self.assertEqual(code(0, '+a2'), 'JOYCODE_1_ZAXIS_POS_SWITCH')
        self.assertEqual(code(2, 'h0.1'), 'JOYCODE_3_HAT1UP')
        self.assertEqual(code(0, 'h1.8'), 'JOYCODE_1_HAT2LEFT')

    def test_retroarch_binds(self):
        # Os botoes do painel no layout dos cores de arcade: 1 2 3 = Y X L,
        # 4 5 6 = B A R, ficha = Select. O outro tipo de bind fica vazio.
        lines = self.rc.retroarch_lines
        self.assertEqual(lines(1, 'b1', 'b2'), ['input_player1_y_btn = "2"', 'input_player1_y_axis = "nul"'])
        self.assertEqual(lines(2, 'b4', 'b0'), ['input_player2_b_btn = "0"', 'input_player2_b_axis = "nul"'])
        self.assertEqual(lines(1, 'coin', 'b9'), ['input_player1_select_btn = "9"',
                                                  'input_player1_select_axis = "nul"'])
        self.assertEqual(lines(1, 'up', '-a1'), ['input_player1_up_axis = "-1"', 'input_player1_up_btn = "nul"'])
        self.assertEqual(lines(1, 'left', 'h0.8'), ['input_player1_left_btn = "h0left"',
                                                    'input_player1_left_axis = "nul"'])

    def test_save_both(self):
        # Painel V-USB do gabinete: dois aparelhos iguais, um por jogador.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            name = 'vusb.wikidot.com/project:mamepanel V-USB Mame Panel 32'
            lines = ['1 up 0 -a1 %s' % name, '1 b1 0 b0 %s' % name, '1 coin 0 b7 %s' % name,
                     '2 up 1 -a1 %s' % name, '2 b1 1 b0 %s' % name, '2 start 1 b6 %s' % name]
            (tmp / 'map').write_text('\n'.join(lines) + '\n')
            env = dict(os.environ, FLIPEROS_RA_BUTTONS=str(tmp / 'ra' / 'buttons.cfg'),
                       FLIPEROS_MAME_CTRLR=str(tmp / 'ctrlr' / 'fliperos.cfg'),
                       FLIPEROS_FLYCAST_MAPPINGS=str(tmp / 'flycast'), FLIPEROS_SDL_USER_DB=str(tmp / 'sdl-user.txt'),
                       FLIPEROS_OPENBOR_SAVES=str(tmp / 'Saves'), FLIPEROS_BUTTONS_MAP=str(tmp / 'buttons.map'),
                       FLIPEROS_CONTROLLERS=str(tmp / 'nada'))
            subprocess.run(['python3', str(ROOT / 'config/fliperos-buttons'), 'save', str(tmp / 'map')], env=env,
                           check=True, capture_output=True, timeout=30)
            ra = (tmp / 'ra' / 'buttons.cfg').read_text()
            for line in ('input_player1_joypad_index = "0"', 'input_player2_joypad_index = "1"',
                         'input_player1_up_axis = "-1"', 'input_player1_y_btn = "0"', 'input_player1_select_btn = "7"',
                         'input_player2_start_btn = "6"'):
                self.assertIn(line + '\n', ra, line)
            import xml.etree.ElementTree as ET
            text = (tmp / 'ctrlr' / 'fliperos.cfg').read_text()
            ports = {p.get('type'): p.find('newseq').text
                     for p in ET.fromstring(text).iter('port')}
            self.assertEqual(ports['P1_JOYSTICK_UP'], 'JOYCODE_1_YAXIS_UP_SWITCH OR KEYCODE_UP')
            self.assertEqual(ports['P1_BUTTON1'], 'JOYCODE_1_BUTTON1 OR KEYCODE_LCONTROL')
            self.assertEqual(ports['COIN1'], 'JOYCODE_1_BUTTON8 OR KEYCODE_5')
            self.assertEqual(ports['P2_BUTTON1'], 'JOYCODE_2_BUTTON1 OR KEYCODE_A')
            self.assertEqual(ports['START2'], 'JOYCODE_2_BUTTON7 OR KEYCODE_2')
            self.assertIn('<system name="default">', text)
            # Flycast por nome de aparelho, e o mapa guardado para a atualizacao.
            self.assertIn('0:btn_a', (tmp / 'flycast' / ('SDL_' + name.replace('/', '-').replace(':', '-') + '_arcade.cfg')).read_text())
            self.assertEqual((tmp / 'buttons.map').read_text(), (tmp / 'map').read_text())

    PANEL = {'up': (0, '-a1'), 'down': (0, '+a1'), 'left': (0, '-a0'), 'right': (0, '+a0'), 'b1': (0, 'b0'),
             'b2': (0, 'b1'), 'b3': (0, 'b2'), 'b4': (0, 'b3'), 'b5': (0, 'b4'), 'b6': (0, 'b5'),
             'start': (0, 'b6'), 'coin': (0, 'b7')}

    def test_sdl_mapping_is_a_fight_stick(self):
        # X Y RB em cima, A B RT embaixo; a notacao e a do proprio SDL.
        line = self.rc.sdl_mapping_line('0300abcd', 'Painel, 2', self.PANEL)
        fields = dict(f.split(':', 1) for f in line.split(',')[2:] if ':' in f)
        self.assertTrue(line.startswith('0300abcd,Painel  2,'))
        self.assertEqual((fields['x'], fields['y'], fields['rightshoulder']), ('b0', 'b1', 'b2'))
        self.assertEqual((fields['a'], fields['b'], fields['righttrigger']), ('b3', 'b4', 'b5'))
        self.assertEqual((fields['dpup'], fields['dpleft'], fields['back']), ('-a1', '-a0', 'b7'))
        self.assertEqual(fields['platform'], 'Linux')
        # Dois paineis iguais (o mesmo GUID): uma linha so.
        devices = {0: ('g', 'P', 8, 2), 1: ('g', 'P', 8, 2)}
        p2 = {c: (1, e) for c, (_, e) in self.PANEL.items()}
        self.assertEqual(list(self.rc.sdl_user_db({1: self.PANEL, 2: p2}, devices)), ['g'])

    def test_user_mapping_wins_in_the_sdl_db(self):
        ctl = load_script('controllers', 'config/fliperos-controllers')
        merged = ctl.merge_db(['g1,auto,a:b0,', 'g2,outro,a:b0,'], {'g1': 'g1,gerado,a:b1,'}, ['g1,meu,a:b3,'])
        self.assertEqual(merged, ['g2,outro,a:b0,', 'g1,meu,a:b3,'])

    def test_openbor_codes_and_settings(self):
        # 600 + 1 + aparelho * 64 + botao; eixos depois dos botoes (2 por
        # eixo, o negativo primeiro), hats depois dos eixos.
        code = self.rc.openbor_code
        self.assertEqual(code(0, 'b0', 8, 2), 601)
        self.assertEqual(code(1, 'b5', 8, 2), 601 + 64 + 5)
        self.assertEqual(code(0, '-a1', 8, 2), 601 + 8 + 2)
        self.assertEqual(code(0, '+a1', 8, 2), 601 + 8 + 3)
        self.assertEqual(code(0, 'h0.4', 8, 2), 601 + 8 + 4 + 2)
        data = self.rc.openbor_default()
        self.assertEqual(len(data), 320)
        import struct
        self.assertEqual(struct.unpack_from('<I', data)[0], 0x33749)
        self.assertEqual(struct.unpack_from('<i', data, 288)[0], 1)   # fullscreen
        devices = {0: ('g', 'P', 8, 2)}
        keys = struct.unpack_from('<52i', self.rc.openbor_with_keys(data, {1: self.PANEL}, devices), 40)
        self.assertEqual(keys[:13], (601 + 10, 601 + 11, 601 + 8, 601 + 9, 601, 604, 605, 606, 602, 603, 607, 69,
                                     608))
        self.assertEqual(keys[13], 601 + 64 * 99)   # jogador 2 sem nada

    def test_flycast_arcade_is_panel_order(self):
        text = self.rc.flycast_cfg('P', self.PANEL, self.rc.FLYCAST_ARCADE)
        for bind in ('0:btn_a', '1:btn_b', '2:btn_c', '3:btn_x', '4:btn_y', '5:btn_z', '6:btn_start', '7:btn_d',
                     '1-:btn_dpad1_up', '0+:btn_dpad1_right'):
            self.assertIn(bind + '\n', text)
        self.assertEqual(self.rc.flycast_filename('a/b: c', True), 'SDL_a-b- c_arcade.cfg')

    def test_pcsx2_pads_on_sdl(self):
        x11 = (ROOT / 'config/fliperos-x11-run').read_text()
        self.assertIn("if ! grep -q 'SDL-[0-9]/' \"$ini\"; then", x11)
        self.assertIn('Cross=FaceSouth', x11)
        self.assertIn('[[ ${kv%%=*} == Type ]] || value="SDL-$((pad - 1))/$value"', x11)
        update = (ROOT / 'tools/cabinet-update.sh').read_text()
        self.assertIn('/opt/fliperos/bin/fliperos-buttons save /etc/fliperos/buttons.map', update)

    def test_capture_waits_for_release(self):
        # O que estava apertado no comeco nao conta; soltar um eixo nao e o
        # lado oposto; um gatilho em -32768 e repouso.
        rest = ([1, 0], [-32767, -32768, 0], [4])
        self.assertIsNone(self.rc.pressed(rest, ([1, 0], [-32767, -32768, 0], [4])))
        settled = self.rc.settle(rest, ([0, 0], [0, -32768, 0], [0]))
        self.assertEqual(settled, ([0, 0], [0, -32768, 0], [0]))
        self.assertIsNone(self.rc.pressed(settled, ([0, 0], [0, -32768, 0], [0])))
        self.assertEqual(self.rc.pressed(settled, ([0, 1], [0, -32768, 0], [0])), 'b1')
        self.assertEqual(self.rc.pressed(settled, ([0, 0], [0, 32767, 0], [0])), '+a1')
        self.assertEqual(self.rc.pressed(settled, ([0, 0], [-32767, -32768, 0], [0])), '-a0')
        self.assertEqual(self.rc.pressed(settled, ([0, 0], [0, -32768, 0], [2])), 'h0.2')

    def test_setup_saves_the_mame_options(self):
        lib = (ROOT / 'fliperos-setup/lib/buttons.sh').read_text()
        self.assertIn('ini_set "$MAME_INI" ctrlr fliperos', lib)
        self.assertIn('ini_set "$MAME_INI" joystickprovider sdljoy', lib)
        self.assertIn('install -Dm755 "$src/config/fliperos-buttons" "$root/opt/fliperos/bin/fliperos-buttons"',
                      ROOTFS)
        screen = (ROOT / 'fliperos-setup/screens/joysticks.sh').read_text()
        self.assertIn('"buttons|Button mapping (RetroArch and GroovyMAME)"', screen)
        body = screen.split('screen_buttons() {')[1].split('\n}\n')[0]
        self.assertLess(body.index('padkeys_off'), body.index('buttons_capture'))
        self.assertLess(body.rindex('buttons_capture'), body.index('padkeys_on'))


if __name__ == '__main__':
    unittest.main()
