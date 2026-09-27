import importlib.util
import os
from pathlib import Path
import re
import unittest
from unittest import mock
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


video = load('video', 'fliperos-video-check.py')
installer = load('installer', 'fliperos-install.py')
autodetect = load('autodetect', 'fliperos-video-autodetect.py')
config = load('config', 'fliperos-config.py')
tui = load('tui', 'fliperos_tui.py')


class VideoTests(unittest.TestCase):
    def test_progressive(self):
        result = video.timing(6510, 416, 261)
        self.assertAlmostEqual(result['horizontal_khz'], 15.64903846)
        self.assertAlmostEqual(result['vertical_hz'], 59.957999, places=4)

    def test_interlaced_fields(self):
        result = video.timing(13500, 858, 525, 16)
        self.assertAlmostEqual(result['horizontal_khz'], 15.73426573)
        self.assertAlmostEqual(result['vertical_hz'], 59.94005994)

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
        self.assertEqual(video.verdict([lcd], [], 'VGA-1', 15, 16)[1], 2)
        self.assertEqual(video.verdict([dict(crt, active=False)], [], None, 15, 16)[1], 2)

    def test_edid(self):
        edid = (ROOT / 'crt15-edid.bin').read_bytes()
        self.assertEqual(len(edid), 128)
        self.assertEqual(edid[:8], b'\x00\xff\xff\xff\xff\xff\xff\x00')
        self.assertEqual(sum(edid) % 256, 0)
        self.assertEqual(edid[35:38], bytes(3))
        self.assertEqual(edid[38:54], b'\x01\x01' * 8)
        self.assertEqual(edid[126], 0)
        dtd = edid[54:72]
        clock = int.from_bytes(dtd[:2], 'little') * 10
        h = dtd[2] + ((dtd[4] >> 4) << 8)
        hb = dtd[3] + ((dtd[4] & 15) << 8)
        v = dtd[5] + ((dtd[7] >> 4) << 8)
        vb = dtd[6] + ((dtd[7] & 15) << 8)
        self.assertEqual((h, v), (640, 240))
        self.assertAlmostEqual(video.timing(clock, h + hb, v + vb)['horizontal_khz'], 15.64903846)
        for offset in (72, 90, 108):
            self.assertEqual(edid[offset:offset + 2], bytes(2))


class InstallerTests(unittest.TestCase):
    def disk(self, **kwargs):
        return dict(path='/dev/testdisk', type='disk', size=20 * 1024**3, ro=False,
                    mountpoints=[], **kwargs)

    def test_exclude_live_and_swap_disks(self):
        for mount in ('/run/live/medium', '/', '[SWAP]'):
            self.assertIsNotNone(installer.rejection(self.disk(children=[{
                'path': '/dev/testdisk1', 'type': 'part', 'mountpoints': [mount]}])))

    def test_exclude_active_lvm(self):
        self.assertIsNotNone(installer.rejection(self.disk(children=[{
            'path': '/dev/dm-123', 'type': 'lvm', 'mountpoints': []}])))

    def test_valid_unused_disk(self):
        self.assertIsNone(installer.rejection(self.disk()))

    def test_partition_names(self):
        self.assertEqual(installer.partition_path('/dev/sda', 3), '/dev/sda3')
        self.assertEqual(installer.partition_path('/dev/nvme0n1', 3), '/dev/nvme0n1p3')
        self.assertEqual(installer.partition_path('/dev/mmcblk0', 2), '/dev/mmcblk0p2')

    def test_plan_and_boot_arguments(self):
        plan = installer.plan(self.disk(), 'VGA-1')
        self.assertTrue(plan['erases_entire_disk'])
        self.assertIn('drm.edid_firmware=VGA-1:', plan['kernel_parameters'])
        self.assertNotIn('boot=live', plan['kernel_parameters'])
        with self.assertRaises(ValueError):
            installer.boot_parameters('VGA-1; reboot')

    def test_connector_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / 'etc/fliperos'
            config.mkdir(parents=True)
            (config / 'xorg.conf').write_text((ROOT / 'config/xorg.conf').read_text())
            service = root / 'etc/systemd/system/fliperos-video-check.service'
            service.parent.mkdir(parents=True)
            service.write_text((ROOT / 'config/fliperos-video-check.service').read_text())
            installer.configure_video(root, 'DVI-I-1')
            self.assertEqual((config / 'connector').read_text(), 'DVI-I-1\n')
            self.assertIn('Monitor-DVI-I-1', (config / 'xorg.conf').read_text())
            self.assertIn('--connector DVI-I-1 --wait 15', service.read_text())

    def test_install_denied_without_root(self):
        with mock.patch.object(installer.os, 'geteuid', return_value=1000), mock.patch.object(installer, 'run') as command:
            with self.assertRaises(ValueError):
                installer.install(self.disk(), 'VGA-1')
            command.assert_not_called()


class RecoveryTests(unittest.TestCase):
    """Existing-install detection and the 3 repair paths (GPU swap,
    launcher/emulator config, lost/corrupted packages)."""

    def test_existing_installs_matches_labeled_unmounted_partition(self):
        device = {'path': '/dev/testdisk', 'type': 'disk', 'model': 'X', 'serial': 'S1',
                  'size': 20 * 1024**3, 'children': [
                      {'path': '/dev/testdisk1', 'type': 'part', 'label': 'BIOS', 'mountpoints': []},
                      {'path': '/dev/testdisk3', 'type': 'part', 'label': 'FliperOS', 'mountpoints': []}]}
        with mock.patch.object(installer, 'inventory', return_value=[device]), \
             mock.patch.object(installer, 'probe_marker',
                                return_value={'installed': 'x', 'connector': 'VGA-1'}) as probe:
            found = installer.existing_installs()
        probe.assert_called_once_with('/dev/testdisk3')
        self.assertEqual(found, [{'disk': '/dev/testdisk', 'partition': '/dev/testdisk3',
                                  'model': 'X', 'serial': 'S1', 'bytes': 20 * 1024**3,
                                  'installed': 'x', 'connector': 'VGA-1'}])

    def test_existing_installs_skips_mounted_partition(self):
        device = {'path': '/dev/testdisk', 'type': 'disk', 'size': 20 * 1024**3, 'children': [
            {'path': '/dev/testdisk3', 'type': 'part', 'label': 'FliperOS', 'mountpoints': ['/mnt/x']}]}
        with mock.patch.object(installer, 'inventory', return_value=[device]), \
             mock.patch.object(installer, 'probe_marker') as probe:
            self.assertEqual(installer.existing_installs(), [])
            probe.assert_not_called()

    def test_existing_installs_skips_unrelated_label(self):
        device = {'path': '/dev/testdisk', 'type': 'disk', 'size': 20 * 1024**3, 'children': [
            {'path': '/dev/testdisk1', 'type': 'part', 'label': 'FLIPERBOOT', 'mountpoints': []}]}
        with mock.patch.object(installer, 'inventory', return_value=[device]), \
             mock.patch.object(installer, 'probe_marker') as probe:
            self.assertEqual(installer.existing_installs(), [])
            probe.assert_not_called()

    def test_mounted_target_rejects_unknown_disk(self):
        with mock.patch.object(installer, 'existing_installs', return_value=[]):
            with self.assertRaises(ValueError):
                with installer.mounted_target('/dev/sdz'):
                    pass

    def test_service_khz_reads_min_khz(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = root / 'etc/systemd/system/fliperos-video-check.service'
            service.parent.mkdir(parents=True)
            service.write_text(
                (ROOT / 'config/fliperos-video-check.service').read_text().replace(
                    '--wait 15', '--wait 15 --min-khz 24.5 --max-khz 25.5'))
            self.assertEqual(installer.service_khz(root), '24.5')

    def test_service_khz_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(installer.service_khz(Path(directory)))

    def test_repair_configs_rejects_monitor_profile_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)

            def fake_khz(root):
                return '31.0' if root == Path('/') else '15.0'

            lock = mock.MagicMock()
            mounted = mock.MagicMock()
            mounted.__enter__.return_value = target
            mounted.__exit__.return_value = False
            with mock.patch.object(installer, 'preflight', return_value=lock), \
                 mock.patch.object(installer, 'service_khz', side_effect=fake_khz), \
                 mock.patch.object(installer, 'mounted_target', return_value=mounted):
                with self.assertRaises(ValueError):
                    installer.repair_configs('/dev/testdisk')
            lock.close.assert_called_once()

    def test_config_paths_are_preserved_during_package_repair(self):
        # Package repair (case 3) must never clobber the video/launcher
        # config that config repair (case 2) owns, or the two would fight.
        for path in installer.CONFIG_PATHS:
            self.assertTrue(installer.preserved(path), path)

    def test_preserved_matches_prefix_not_substring(self):
        self.assertTrue(installer.preserved('opt/fliperos/roms/mame/pacman.zip'))
        self.assertTrue(installer.preserved('home/fliperos/.config/retroarch/retroarch.cfg'))
        self.assertFalse(installer.preserved('usr/local/bin/groovymame'))
        # 'boot' must not accidentally match an unrelated 'bootstrap' path.
        self.assertFalse(installer.preserved('usr/lib/bootstrap/file'))

    def test_overlay_squashfs_overwrites_binaries_but_keeps_user_data(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
            src, dst = Path(src_dir), Path(dst_dir)
            (src / 'usr/bin').mkdir(parents=True)
            (src / 'usr/bin/mame').write_text('fresh-binary')
            (src / 'opt/fliperos/roms').mkdir(parents=True)
            (src / 'opt/fliperos/roms/pacman.zip').write_text('pristine-placeholder')
            (dst / 'usr/bin').mkdir(parents=True)
            (dst / 'usr/bin/mame').write_text('corrupted')
            (dst / 'opt/fliperos/roms').mkdir(parents=True)
            (dst / 'opt/fliperos/roms/pacman.zip').write_text('the-users-rom')
            installer.overlay_squashfs(src, dst)
            self.assertEqual((dst / 'usr/bin/mame').read_text(), 'fresh-binary')
            self.assertEqual((dst / 'opt/fliperos/roms/pacman.zip').read_text(), 'the-users-rom')


class AutodetectTests(unittest.TestCase):
    def test_connector_name_keeps_hyphenated_type(self):
        self.assertEqual(autodetect.connector_name(Path('/sys/class/drm/card0-DVI-I-1')), 'DVI-I-1')
        self.assertEqual(autodetect.connector_name(Path('/sys/class/drm/card0-VGA-1')), 'VGA-1')

    def test_classify_digital_monitor_is_skipped(self):
        self.assertEqual(autodetect.classify('HDMI-A-1', 256, 'connected'), 'edid_present')

    def test_classify_forceable_without_edid(self):
        self.assertEqual(autodetect.classify('VGA-1', 0, 'disconnected'), 'forceable')
        self.assertEqual(autodetect.classify('DVI-I-1', 0, 'disconnected'), 'forceable')

    def test_classify_non_forceable_digital_without_signal(self):
        self.assertEqual(autodetect.classify('DP-1', 0, 'disconnected'), 'skip')
        self.assertEqual(autodetect.classify('HDMI-A-1', 0, 'disconnected'), 'skip')


class ConfigCmdlineTests(unittest.TestCase):
    """Edicao da cmdline do GRUB feita pelo fliperos-config (orientacao,
    troca de conector). Um erro aqui deixa a maquina sem video no boot."""

    BASE = ('video=VGA-1:e drm.edid_firmware=VGA-1:edid/crt15.bin '
            'radeon.si_support=1 amdgpu.si_support=0')

    def test_set_param_replaces_without_duplicating(self):
        once = config.set_param(self.BASE, 'video', 'DVI-I-1:e')
        self.assertEqual(once.count('video='), 1)
        self.assertIn('video=DVI-I-1:e', once)
        self.assertIn('radeon.si_support=1', once)

    def test_set_param_none_removes_key(self):
        self.assertIsNone(config.get_param(
            config.set_param(self.BASE + ' fbcon=rotate:1', 'fbcon', None), 'fbcon'))

    def test_get_param_does_not_match_prefix_of_other_key(self):
        # drm.edid_firmware nao deve ser lido como se fosse a chave "drm".
        self.assertIsNone(config.get_param(self.BASE, 'drm'))
        self.assertEqual(config.get_param(self.BASE, 'video'), 'VGA-1:e')

    def test_video_subparam_appends_and_replaces(self):
        rotated = config.set_video_subparam(self.BASE, 'panel_orientation', 'left_side_up')
        self.assertEqual(config.get_param(rotated, 'video'),
                         'VGA-1:e,panel_orientation=left_side_up')
        flipped = config.set_video_subparam(rotated, 'panel_orientation', 'upside_down')
        self.assertEqual(config.get_param(flipped, 'video'),
                         'VGA-1:e,panel_orientation=upside_down')

    def test_video_subparam_removal_keeps_connector(self):
        rotated = config.set_video_subparam(self.BASE, 'panel_orientation', 'left_side_up')
        self.assertEqual(config.get_param(
            config.set_video_subparam(rotated, 'panel_orientation', None), 'video'), 'VGA-1:e')

    def test_video_subparam_without_video_param_is_noop(self):
        self.assertEqual(config.set_video_subparam('quiet splash', 'panel_orientation', 'x'),
                         'quiet splash')


class ConfigIniTests(unittest.TestCase):
    """Os .ini que a imagem instala sao minimos (switchres.ini tem so
    'monitor arcade_15'), entao o upsert TEM que inserir a chave que falta —
    um sub puro nao gravaria rotacao, geometria nem verbosidade."""

    def ini(self, text):
        path = Path(tempfile.mkdtemp()) / 'switchres.ini'
        path.write_text(text)
        return path

    def test_inserts_missing_key(self):
        path = self.ini('monitor arcade_15\n')
        self.assertTrue(config.set_ini_value(path, 'h_size', '0.950'))
        self.assertIn('monitor arcade_15', path.read_text())
        self.assertIn('h_size 0.950', path.read_text())

    def test_replaces_existing_key_keeping_indent(self):
        path = self.ini('monitor arcade_15\n\th_size                    1.0\n')
        config.set_ini_value(path, 'h_size', '0.900')
        self.assertIn('\th_size 0.900', path.read_text())
        self.assertNotIn('1.0', path.read_text())

    def test_does_not_confuse_key_with_longer_key(self):
        # v_shift_correct nao pode ser tratado como v_shift.
        path = self.ini('\tv_shift_correct           0\n')
        config.set_ini_value(path, 'v_shift', '3')
        text = path.read_text()
        self.assertIn('v_shift_correct           0', text)
        self.assertIn('v_shift 3', text)

    def test_missing_file_reports_false(self):
        self.assertFalse(config.set_ini_value(Path('/nao/existe.ini'), 'h_size', '1'))
        self.assertFalse(config.set_cfg_value(Path('/nao/existe.cfg'), 'k', 'v'))

    def test_retroarch_style_insert_and_replace(self):
        path = Path(tempfile.mkdtemp()) / 'retroarch.cfg'
        path.write_text('video_driver = "gl"\n')
        config.set_cfg_value(path, 'log_verbosity', 'true')
        self.assertIn('log_verbosity = "true"', path.read_text())
        config.set_cfg_value(path, 'log_verbosity', 'false')
        self.assertIn('log_verbosity = "false"', path.read_text())
        self.assertNotIn('"true"', path.read_text())
        self.assertIn('video_driver = "gl"', path.read_text())


class SessionTests(unittest.TestCase):
    """A tabela de sessoes e o contrato entre fliperos-config, o dispatcher
    fliperos-session e o futuro wizard de instalacao."""

    VALID_BACKENDS = {'kms', 'x', 'text', 'none'}

    def rows(self):
        directory = Path(tempfile.mkdtemp())
        (directory / 'sessions.conf').write_text(
            (ROOT / 'config/fliperos-sessions.conf').read_text())
        with mock.patch.object(config, 'ETC', directory):
            return config.sessions()

    def test_every_row_parses_with_a_known_backend(self):
        rows = self.rows()
        self.assertTrue(rows)
        for row in rows:
            self.assertIn(row['backend'], self.VALID_BACKENDS, row['name'])
            self.assertTrue(row['description'], row['name'])

    def test_text_launcher_always_present_as_fallback(self):
        names = {row['name']: row for row in self.rows()}
        self.assertIn('launcher', names)
        self.assertEqual(names['launcher']['backend'], 'text')
        # Nao precisa de pacote: e o fallback que sempre existe na imagem.
        self.assertEqual(names['launcher']['package'], '')

    def test_attract_mode_plus_not_plain_attract(self):
        # O Attract-Mode original nao roda em KMS; so o fork Plus roda
        # (tabela de capacidades do GroovyArcade, galauncher/videodata.conf).
        names = {row['name'] for row in self.rows()}
        self.assertIn('attractplus', names)
        self.assertNotIn('attract', names)

    def test_sessions_needing_install_declare_a_package(self):
        for row in self.rows():
            if row['backend'] in ('kms', 'x') and row['name'] not in ('retroarch', 'groovymame'):
                self.assertTrue(row['package'],
                                '%s precisa declarar pacote' % row['name'])

    def test_dispatcher_and_table_are_installed(self):
        script = (ROOT / 'fliperos-install-video.sh').read_text()
        self.assertIn('fliperos-sessions.conf', script)
        self.assertIn('fliperos-session', script)
        # O login tem que chamar o dispatcher, nao um launcher fixo.
        self.assertIn('/opt/fliperos/bin/fliperos-session', script)

    def test_no_live_use_mode_in_installer_menu(self):
        installer_text = (ROOT / 'fliperos-install.py').read_text()
        self.assertNotIn('testar live', installer_text)

    def test_setup_media_opens_config_not_installer(self):
        """A midia tem de abrir no menu de setup: sem cabo de rede, o Wi-Fi
        precisa ser configurado antes de instalar, e o instalador sozinho nao
        oferece isso."""
        script = (ROOT / 'fliperos-install-video.sh').read_text()
        live_branch = script.split('if [[ ! -f /etc/fliperos/installed ]]; then')[1]
        live_branch = live_branch.split('else')[0]
        self.assertIn('fliperos-config', live_branch)
        self.assertNotIn('fliperos-install', live_branch)

    def test_setup_media_menu_offers_wifi_and_install(self):
        text = (ROOT / 'fliperos-config.py').read_text()
        menu = text.split('def menu_setup_media')[1].split('def menu_installed')[0]
        self.assertIn('menu_network', menu)
        self.assertIn('fliperos-install', menu)
        # Itens que exigem GRUB instalado nao entram no menu da midia.
        self.assertNotIn('menu_orientation', menu)
        self.assertNotIn('menu_connector', menu)


class InputDriverTests(unittest.TestCase):
    """GunCon 2 nao existe no kernel mainline; Logitech e Thrustmaster antigo
    existem (hid-logitech com lg4ff, hid-tmff). Por isso o GunCon entra por
    padrao e os out-of-tree de volante ficam opcionais."""

    RULES = ROOT / 'config/99-fliperos-input.rules'
    CALIBRATE = ROOT / 'config/fliperos-guncon2-calibrate'

    def test_guncon2_usb_id_and_calibration_hook(self):
        rules = self.RULES.read_text()
        # 0b9a:016a e o ID do GunCon 2 documentado pelo driver.
        self.assertIn('0b9a', rules)
        self.assertIn('016a', rules)
        self.assertIn('fliperos-guncon2-calibrate', rules)

    def test_calibration_reads_config_instead_of_hardcoding(self):
        """Os valores do upstream sao do monitor DELE; cada tubo pede outros."""
        script = self.CALIBRATE.read_text()
        self.assertIn('/etc/fliperos/guncon2.conf', script)
        for key in ('X_MIN', 'X_MAX', 'Y_MIN', 'Y_MAX'):
            self.assertIn(key, script)

    def test_guncon2_builds_by_default_wheels_behind_flag(self):
        script = (ROOT / 'fliperos-mkiso.sh').read_text()
        self.assertIn('SKIP_INPUT_DRIVERS=false', script)
        self.assertIn('WITH_WHEEL_DRIVERS=false', script)
        self.assertIn('--with-wheel-drivers', script)
        self.assertIn('beardypig/guncon2', script)
        self.assertIn('dkms linux-headers-generic', script)

    def test_guncon2_module_loads_at_boot(self):
        """Compilar nao basta: sem modules-load o modulo fica so em disco."""
        self.assertIn('modules-load.d', (ROOT / 'fliperos-mkiso.sh').read_text())

    def test_tmff2_version_comes_from_dkms_conf(self):
        """O dkms-install.sh do upstream usa 0.83 e o dkms.conf diz 0.82; o
        dkms recusa quando diretorio e PACKAGE_VERSION divergem, entao a versao
        e lida do dkms.conf em vez de rodar o script deles."""
        script = (ROOT / 'fliperos-mkiso.sh').read_text()
        self.assertIn("s/^PACKAGE_VERSION=", script)
        # O script do upstream pode ser citado em comentario, mas nao executado.
        for line in script.splitlines():
            code = line.split('#')[0]
            self.assertNotIn('dkms-install.sh', code)

    def test_rules_and_config_are_installed(self):
        script = (ROOT / 'fliperos-install-video.sh').read_text()
        self.assertIn('99-fliperos-input.rules', script)
        self.assertIn('fliperos-guncon2-calibrate', script)
        self.assertIn('guncon2.conf', script)


class HiddenWifiTests(unittest.TestCase):
    """Rede oculta nao aparece na varredura (nao anuncia o SSID), entao precisa
    de entrada manual — e o nmcli exige 'hidden yes' pra achar o ponto."""

    def args_of(self, ssid, secret, hidden):
        with mock.patch.object(config.subprocess, 'run') as runner:
            runner.return_value = mock.Mock(returncode=0, stdout='', stderr='')
            config.wifi_connect(ssid, secret, hidden=hidden)
        return runner.call_args[0][0]

    def test_hidden_network_passes_hidden_yes(self):
        args = self.args_of('MinhaOculta', 'senha123', True)
        self.assertEqual(args[:5], ['nmcli', 'device', 'wifi', 'connect', 'MinhaOculta'])
        self.assertIn('hidden', args)
        self.assertEqual(args[args.index('hidden') + 1], 'yes')
        self.assertEqual(args[args.index('password') + 1], 'senha123')

    def test_visible_network_does_not_pass_hidden(self):
        self.assertNotIn('hidden', self.args_of('Rede', 'senha', False))

    def test_open_hidden_network_omits_password(self):
        args = self.args_of('Aberta', '', True)
        self.assertNotIn('password', args)
        self.assertIn('hidden', args)

    def test_failure_returns_the_nmcli_message(self):
        with mock.patch.object(config.subprocess, 'run') as runner:
            runner.return_value = mock.Mock(returncode=1, stdout='',
                                            stderr='Error: no network with SSID')
            ok, detail = config.wifi_connect('X', 'y', hidden=True)
        self.assertFalse(ok)
        self.assertIn('no network with SSID', detail)

    def test_hidden_option_is_offered_even_with_no_visible_networks(self):
        """A lista pode vir vazia e o item de rede oculta tem de sobrar."""
        source = (ROOT / 'fliperos-config.py').read_text()
        menu = source.split('def menu_wifi')[1].split('def menu_regdom')[0]
        self.assertIn('HIDDEN_TAG', menu)
        # Nao deve haver retorno antecipado por lista vazia antes do menu.
        self.assertNotIn('Nenhuma rede encontrada', menu)


class BuildImageTests(unittest.TestCase):
    """Regressao: o Dockerfile copiava "fliperos-*.py" e o modulo compartilhado
    e fliperos_tui.py, com underscore — o glob nao o pegava e a imagem de build
    saia sem ele."""

    def test_dockerfile_copies_every_source_that_install_video_needs(self):
        dockerfile = (ROOT / 'Dockerfile.fliperos').read_text()
        installer = (ROOT / 'fliperos-install-video.sh').read_text()
        needed = set(re.findall(r'"\$src/([A-Za-z0-9_.-]+\.py)"', installer))
        self.assertIn('fliperos_tui.py', needed)
        for name in needed:
            matched = ('fliperos*.py' in dockerfile
                       or name in dockerfile
                       or ('fliperos-*.py' in dockerfile and name.startswith('fliperos-')))
            self.assertTrue(matched, '%s nao e copiado pelo Dockerfile' % name)

    def test_config_directory_is_copied_wholesale(self):
        """As regras de udev e o tema do plymouth vivem em config/."""
        self.assertIn('COPY config/', (ROOT / 'Dockerfile.fliperos').read_text())


class TuiTests(unittest.TestCase):
    """O console do CRT em 640x240 tem 80x15 caracteres; um dialogo maior que
    isso fica cortado na tela, que foi o sintoma do GRUB ilegivel."""

    def test_box_fits_a_small_console(self):
        with mock.patch.object(tui.shutil, 'get_terminal_size',
                               return_value=os.terminal_size((80, 15))):
            height, width, list_height = tui._box(20)
        self.assertLessEqual(height, 15)
        self.assertLessEqual(width, 78)
        self.assertGreaterEqual(list_height, 3)
        self.assertLess(list_height, height)

    def test_box_is_capped_on_a_large_console(self):
        with mock.patch.object(tui.shutil, 'get_terminal_size',
                               return_value=os.terminal_size((200, 60))):
            height, width, _ = tui._box(5)
        self.assertLessEqual(width, tui.MAX_WIDTH)
        self.assertLessEqual(height, tui.MAX_HEIGHT)

    VALID_NEWT_COLORS = {
        'black', 'red', 'green', 'brown', 'blue', 'magenta', 'cyan', 'lightgray',
        'gray', 'brightred', 'brightgreen', 'yellow', 'brightblue',
        'brightmagenta', 'brightcyan', 'white', '',
    }

    def test_palette_uses_only_valid_newt_colors(self):
        """O newt so conhece as 16 cores do console; nome invalido e ignorado
        em silencio, entao o erro apareceria como cor que nao mudou."""
        for line in tui.DEFAULT_PALETTE.strip().splitlines():
            element, _, spec = line.partition('=')
            self.assertTrue(element.strip(), line)
            for color in spec.split(','):
                self.assertIn(color.strip(), self.VALID_NEWT_COLORS,
                              'cor invalida em: ' + line)

    def test_palette_is_passed_to_whiptail(self):
        source = (ROOT / 'fliperos_tui.py').read_text()
        self.assertIn('NEWT_COLORS', source)

    def test_palette_can_be_overridden_on_the_machine(self):
        with tempfile.TemporaryDirectory() as directory:
            custom = Path(directory) / 'newt-palette'
            custom.write_text('root=white,brightcyan\n')
            with mock.patch.object(tui, 'PALETTE_FILE', custom):
                self.assertIn('brightcyan', tui.palette())
        self.assertEqual(tui.palette(), tui.DEFAULT_PALETTE)

    def test_password_uses_passwordbox(self):
        """A senha do Wi-Fi nao deve aparecer na tela. O inputbox e legitimo
        para o SSID de rede oculta, entao a checagem e sobre o que cada chamada
        pede, nao sobre a presenca do inputbox."""
        self.assertIn('--passwordbox', (ROOT / 'fliperos_tui.py').read_text())
        config_source = (ROOT / 'fliperos-config.py').read_text()
        wifi = config_source.split('def menu_wifi')[1].split('def menu_regdom')[0]
        self.assertIn('tui.password', wifi)
        for call in re.findall(r'tui\.inputbox\((.*?)title=', wifi, flags=re.S):
            self.assertNotIn('Senha', call, 'senha pedida por inputbox: ' + call)


class RepoTests(unittest.TestCase):
    """O repositorio e instalado com trusted=yes, entao a exigencia de HTTPS
    e o que impede alguem no caminho de entregar um pacote que roda como root."""

    def test_https_required(self):
        for bad in ('http://exemplo.test/repo/', 'ftp://exemplo.test/',
                    'exemplo.test/repo/'):
            with self.assertRaises(ValueError, msg=bad):
                config.repo_source_line(bad)

    def test_flat_repo_line_ends_with_dot_slash(self):
        line = config.repo_source_line('https://exemplo.test/fliperos')
        self.assertEqual(line, 'deb [trusted=yes] https://exemplo.test/fliperos/ ./\n')

    def test_trailing_slash_not_duplicated(self):
        self.assertEqual(config.repo_source_line('https://exemplo.test/r/'),
                         config.repo_source_line('https://exemplo.test/r'))


class NmcliParsingTests(unittest.TestCase):
    """O nmcli -t escapa ':' dentro dos valores. Um split cru truncaria o SSID
    na lista e a conexao sairia com o nome errado."""

    def test_plain_line(self):
        self.assertEqual(config.nmcli_fields('MinhaRede:80:WPA2'),
                         ['MinhaRede', '80', 'WPA2'])

    def test_ssid_with_escaped_colon(self):
        self.assertEqual(config.nmcli_fields(r'Casa\:2G:72:WPA2'),
                         ['Casa:2G', '72', 'WPA2'])

    def test_ssid_with_escaped_backslash(self):
        self.assertEqual(config.nmcli_fields(r'Rede\\Teste:60:'),
                         ['Rede\\Teste', '60', ''])

    def test_empty_ssid_of_hidden_network_is_preserved_as_empty(self):
        self.assertEqual(config.nmcli_fields(':45:WPA2'), ['', '45', 'WPA2'])

    def test_device_line(self):
        self.assertEqual(config.nmcli_fields('wlan0:wifi'), ['wlan0', 'wifi'])


class PackagingTests(unittest.TestCase):
    RECIPES = ROOT / 'packaging/packages'

    def recipe_files(self):
        return sorted(self.RECIPES.glob('*.sh'))

    def test_at_least_one_recipe(self):
        self.assertTrue(self.recipe_files())

    def test_recipes_declare_the_full_contract(self):
        for recipe in self.recipe_files():
            text = recipe.read_text()
            for field in ('PKG_NAME=', 'PKG_VERSION=', 'PKG_SUMMARY=',
                          'PKG_BUILD_DEPS=', 'PKG_SHLIB_TARGETS=', 'pkg_build()'):
                self.assertIn(field, text, '%s sem %s' % (recipe.name, field))

    def test_recipe_filename_matches_package_name(self):
        for recipe in self.recipe_files():
            declared = re.search(r'^PKG_NAME="([^"]+)"', recipe.read_text(),
                                 flags=re.M).group(1)
            self.assertEqual(declared, recipe.stem)

    def test_pkg_build_chains_steps(self):
        """Regressao: o errexit do driver fica suspenso dentro de pkg_build
        (chamada em "|| err"), e um subshell com set -e nao reverte isso no
        bash. Sem o encadeamento, um build falho seguia pro make install."""
        for recipe in self.recipe_files():
            body = recipe.read_text().split('pkg_build()')[1]
            commands = [line.strip() for line in body.splitlines()
                        if line.strip() and not line.strip().startswith('#')
                        and line.strip() not in ('{', '}')]
            if len(commands) > 1:
                joined = ' '.join(commands)
                self.assertIn('&&', joined,
                              '%s: passos de pkg_build sem &&' % recipe.name)

    def test_no_orphan_recipe_outside_sessions_table(self):
        table = (ROOT / 'config/fliperos-sessions.conf').read_text()
        for recipe in self.recipe_files():
            self.assertIn(recipe.stem, table,
                          '%s nao aparece na tabela de sessoes' % recipe.stem)

    def test_packager_base_matches_iso_base(self):
        """O Depends sai do dpkg-shlibdeps contra as libs desta base; outra
        versao de Ubuntu geraria dependencia que nao resolve na ISO."""
        packager = (ROOT / 'Dockerfile.packages').read_text()
        iso = (ROOT / 'Dockerfile.fliperos').read_text()
        self.assertIn('ubuntu:24.04', packager)
        self.assertIn('ubuntu:24.04', iso)

    LAYOUT = ROOT / 'packaging/assets/attractplus-layouts/AdvanceMenu/layout.nut'

    def test_advancemenu_theme_ships_with_attractplus(self):
        """O AdvanceMENU nao e empacotado como launcher; a aparencia dele vem
        como tema do attractplus, entao a receita tem que copiar o layout."""
        self.assertTrue(self.LAYOUT.is_file())
        recipe = (self.RECIPES / 'fliperos-attractplus.sh').read_text()
        self.assertIn('attractplus-layouts/AdvanceMenu', recipe)
        self.assertIn('layouts/AdvanceMenu', recipe)

    def test_advancemenu_not_a_session(self):
        table = (ROOT / 'config/fliperos-sessions.conf').read_text()
        entries = [line.split('|')[0] for line in table.splitlines()
                   if line.strip() and not line.strip().startswith('#')]
        self.assertNotIn('advancemenu', entries)

    def test_theme_avoids_deprecated_listbox_call(self):
        """set_selbg_rgb esta deprecado desde a 3.2.3, a versao empacotada;
        os layouts embutidos ainda usam, este nao deve copiar o erro."""
        text = self.LAYOUT.read_text()
        self.assertIn('set_sel_bg_rgb', text)
        self.assertNotIn('set_selbg_rgb(', text.replace('set_sel_bg_rgb', ''))

    def test_theme_is_resolution_adaptive(self):
        """Coordenada fixa quebraria nos outros perfis de monitor: o tema tem
        de sair de fe.layout.width/height, que trazem a resolucao real."""
        text = self.LAYOUT.read_text()
        self.assertIn('fe.layout.width', text)
        self.assertIn('fe.layout.height', text)
        # A correcao de pixel nao-quadrado do CRT e o ponto do tema.
        self.assertIn('box_height', text)

    def test_repo_generator_uses_flat_layout(self):
        script = (ROOT / 'packaging/make-repo.sh').read_text()
        self.assertIn('dpkg-scanpackages', script)
        self.assertIn('apt-ftparchive', script)


class SplashTests(unittest.TestCase):
    def test_boot_parameters_enable_plymouth(self):
        params = installer.boot_parameters('VGA-1')
        self.assertIn('splash', params.split())
        self.assertIn('quiet', params.split())

    def test_diagnostic_grub_entry_has_no_splash(self):
        # A entrada de diagnostico e a saida de emergencia quando o tema
        # falha: ela nao pode ganhar splash junto com a entrada normal.
        entries = (ROOT / 'config/grub.cfg').read_text().split('menuentry')
        normal = [e for e in entries if 'nomodeset' not in e and 'linux ' in e]
        diagnostic = [e for e in entries if 'nomodeset' in e]
        self.assertTrue(normal and diagnostic)
        for entry in normal:
            self.assertIn('splash', entry)
        for entry in diagnostic:
            self.assertNotIn('splash', entry)

    def test_theme_files_are_installed(self):
        script = (ROOT / 'fliperos-install-video.sh').read_text()
        self.assertIn('fliperos.plymouth', script)
        self.assertIn('fliperos.script', script)

    def test_theme_script_uses_only_verified_api(self):
        """Erro no tema = boot sem imagem num CRT, difícil de diagnosticar.
        Estas chamadas foram conferidas no script.so do Ubuntu 24.04."""
        text = (ROOT / 'config/plymouth/fliperos.script').read_text()
        for call in ('Window.SetBackgroundTopColor', 'Window.GetWidth',
                     'Image.Text', 'Math.Int',
                     'Plymouth.SetBootProgressFunction'):
            self.assertIn(call, text)
        # Nenhum asset binario: o tema tem que se sustentar em texto.
        self.assertNotIn('Image(', text)

    def test_every_monitor_profile_has_a_splash_geometry(self):
        script = (ROOT / 'fliperos-mkiso.sh').read_text()
        geometry = script.split('splash_mode_geometry()')[1].split('}')[0]
        for profile in config.PROFILE_KHZ:
            self.assertIn(profile + ')', geometry)


class ConfigProfileTests(unittest.TestCase):
    ASSETS = {
        '15khz': ('crt15-edid.bin', 'config/switchres.ini',
                  'config/xorg.conf', 'config/mame.ini'),
        '25khz': ('crt25-edid.bin', 'config/switchres-25khz.ini',
                  'config/xorg-25khz.conf', 'config/mame-25khz.ini'),
        '31khz': ('crt31-edid.bin', 'config/switchres-31khz.ini',
                  'config/xorg-31khz.conf', 'config/mame-31khz.ini'),
    }

    def test_every_profile_has_assets_and_khz_range(self):
        self.assertEqual(set(config.PROFILE_KHZ), set(self.ASSETS))
        for profile, (low, high) in config.PROFILE_KHZ.items():
            self.assertLess(low, high)
            for source in self.ASSETS[profile]:
                self.assertTrue((ROOT / source).is_file(),
                                'perfil %s exige %s no repo' % (profile, source))

    def test_installer_ships_config_tool_for_every_profile(self):
        script = (ROOT / 'fliperos-install-video.sh').read_text()
        self.assertIn('fliperos-config.py', script)
        for profile in config.PROFILE_KHZ:
            self.assertIn('profiles/' + profile + '/edid.bin', script)

    def test_khz_ranges_match_install_video_script(self):
        script = (ROOT / 'fliperos-install-video.sh').read_text()
        for profile, (low, high) in config.PROFILE_KHZ.items():
            self.assertRegex(script, r'%s\)[^)]*?MIN_KHZ=%s; MAX_KHZ=%s'
                             % (profile, low, high))


if __name__ == '__main__':
    unittest.main()
