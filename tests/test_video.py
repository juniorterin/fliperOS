import importlib.util
from pathlib import Path
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


if __name__ == '__main__':
    unittest.main()
