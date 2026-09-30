"""Testes da midia em VM (QEMU/TCG, sem KVM), no container fliperos-vmtest.

    python3 tools/vm-test.py install ISO   instala num disco descartavel pela
                                           lib do fliperos-setup e boota o
                                           disco instalado em BIOS e em UEFI
    python3 tools/vm-test.py screens ISO   boota pelo menu do Limine e
                                           fotografa o tty1 (o Gum no console
                                           de verdade) tela a tela

Tudo acontece em /audit (um volume do Docker, nunca uma pasta do Windows):
disco qcow2, logs e as fotos em PNG.
"""
from pathlib import Path
import re
import socket
import struct
import subprocess
import sys
import time
import zlib

BASE = Path('/audit')
assert Path('/.dockerenv').exists(), 'rode dentro do container'
PASSWORD = 'fliperos'
LIB = '/usr/local/lib/fliperos-setup'


def extract_boot(iso):
    """Kernel e initrd da ISO, para o modo serial (-kernel/-initrd)."""
    out = BASE / 'isoboot'
    out.mkdir(exist_ok=True)
    subprocess.run(['xorriso', '-osirrox', 'on', '-indev', str(iso),
                    '-extract', '/boot/vmlinuz', str(out / 'vmlinuz'),
                    '-extract', '/boot/initrd.img', str(out / 'initrd.img')],
                   check=True, capture_output=True)
    return out


class Guest:
    def __init__(self, name, args, serial=True, monitor=False):
        self.name = name
        self.log = open(BASE / ('vm-' + name + '.log'), 'wb', buffering=0)
        self.serial_path = BASE / ('serial-' + name + '.sock')
        self.monitor_path = BASE / ('monitor-' + name + '.sock')
        for p in (self.serial_path, self.monitor_path):
            p.unlink(missing_ok=True)
        cmd = ['qemu-system-x86_64', '-m', '3072', '-smp', '2', '-accel', 'tcg',
               '-display', 'none', '-no-reboot', '-nic', 'user,model=virtio-net-pci',
               '-object', 'rng-random,filename=/dev/urandom,id=rng0',
               '-device', 'virtio-rng-pci,rng=rng0',
               '-serial', 'unix:%s,server=on,wait=off' % self.serial_path]
        cmd += ['-monitor', 'unix:%s,server=on,wait=off' % self.monitor_path] if monitor else ['-monitor', 'none']
        self.proc = subprocess.Popen(cmd + args, stdout=self.log, stderr=self.log)
        self.sock = self.connect(self.serial_path)
        self.mon = self.connect(self.monitor_path) if monitor else None
        self.buffer = b''

    def connect(self, path):
        for _ in range(100):
            if path.exists():
                break
            time.sleep(.1)
        s = socket.socket(socket.AF_UNIX)
        s.connect(str(path))
        s.settimeout(1)
        return s

    def pump(self):
        try:
            data = self.sock.recv(65536)
            self.log.write(data)
            self.buffer += data
        except socket.timeout:
            pass

    def wait(self, pattern, timeout=900):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            match = re.search(pattern.encode(), self.buffer)
            if match:
                self.buffer = self.buffer[match.end():]
                return match
            if self.proc.poll() is not None:
                if pattern == 'Power down':
                    return None
                raise RuntimeError('QEMU saiu: ' + self.name)
            self.pump()
        raise TimeoutError('%s esperando %r\n%s' % (self.name, pattern,
                                                    self.buffer[-3000:].decode(errors='replace')))

    def send(self, line):
        self.sock.sendall(line.encode() + b'\n')

    def root_shell(self):
        self.wait('login:')
        self.send('fliperos')
        self.wait('Password:')
        self.send(PASSWORD)
        self.wait(r'\$ ')
        self.send("sudo -p 'TEST_SUDO:' bash")
        self.wait('TEST_SUDO:')
        self.send(PASSWORD)
        self.wait(r'# ')
        self.send("export LC_ALL=C PS1='VMROOT> '; stty -echo")
        self.wait('VMROOT> ')

    def run(self, command, timeout=900):
        self.send(command + '; echo "RC=$?"')
        rc = int(self.wait(r'RC=(\d+)', timeout).group(1))
        self.wait('VMROOT> ')
        return rc

    def monitor(self, command):
        self.mon.sendall(command.encode() + b'\n')
        time.sleep(1)
        try:
            self.mon.recv(65536)
        except socket.timeout:
            pass

    def screenshot(self, name):
        ppm = BASE / (name + '.ppm')
        ppm.unlink(missing_ok=True)
        self.monitor('screendump ' + str(ppm))
        for _ in range(50):
            if ppm.exists() and ppm.stat().st_size > 0:
                break
            time.sleep(.2)
        time.sleep(1)
        png = BASE / (name + '.png')
        ppm_to_png(ppm, png)
        print('  foto:', png, flush=True)

    def key(self, key):
        self.monitor('sendkey ' + key)

    def close(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        self.sock.close()
        if self.mon:
            self.mon.close()
        self.log.close()


def ppm_to_png(ppm, png):
    data = ppm.read_bytes()
    parts = data.split(maxsplit=4)
    width, height = int(parts[1]), int(parts[2])
    pixels = parts[4][:width * height * 3]
    rows = b''.join(b'\x00' + pixels[y * width * 3:(y + 1) * width * 3] for y in range(height))

    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))

    png.write_bytes(b'\x89PNG\r\n\x1a\n'
                    + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
                    + chunk(b'IDAT', zlib.compress(rows, 6)) + chunk(b'IEND', b''))


def disk(fresh):
    path = BASE / 'install-test.qcow2'
    if fresh:
        path.unlink(missing_ok=True)
        subprocess.run(['qemu-img', 'create', '-f', 'qcow2', str(path), '20G'], check=True, capture_output=True)
    return ['-drive', 'file=%s,format=qcow2,if=virtio' % path]


def install(iso):
    boot = extract_boot(iso)
    print('LIVE: boot serial da midia (entrada SVGA/LCD)', flush=True)
    guest = Guest('live', disk(True) + [
        '-kernel', str(boot / 'vmlinuz'), '-initrd', str(boot / 'initrd.img'),
        '-append', 'boot=live fliperos.boot=svga consoleblank=0 console=ttyS0,115200n8 '
                   'systemd.wants=serial-getty@ttyS0.service',
        '-cdrom', str(iso)])
    try:
        guest.root_shell()
        assert guest.run('fliperos-setup --version') == 0
        print('LIVE: instalando em /dev/vda pela lib do fliperos-setup', flush=True)
        load = 'for f in %s/lib/*.sh; do . "$f"; done' % LIB
        rc = guest.run("bash -c '%s; install_run /dev/vda \"$(disk_identity /dev/vda)\"' "
                       "| tee /tmp/install-events | grep -E '^@(step|fail)'" % load, timeout=3600)
        guest.run('cat /tmp/install-events | tail -3; tail -20 /var/log/fliperos-setup.log')
        assert rc == 0, 'install_run falhou'
        assert guest.run("grep -q '^@step 100' /tmp/install-events") == 0, 'instalacao nao chegou a 100%'
        print('INSTALL: ok; console serial so no disco de teste', flush=True)
        guest.run('mount /dev/vda3 /mnt && mount /dev/vda2 /mnt/boot/efi && mount --bind /dev /mnt/dev '
                  '&& mount -t proc proc /mnt/proc && mount -t sysfs sys /mnt/sys')
        guest.run("sed -i 's|^FLIPEROS_CMDLINE=\"\\(.*\\)\"$|FLIPEROS_CMDLINE=\"\\1 console=ttyS0,115200n8\"|' "
                  "/mnt/etc/default/fliperos-boot && chroot /mnt /usr/local/sbin/fliperos-limine-update", 300)
        guest.run('cat /mnt/boot/efi/limine/limine.conf; test -f /mnt/etc/fliperos/firstboot')
        guest.send('umount /mnt/dev /mnt/proc /mnt/sys /mnt/boot/efi /mnt; poweroff')
        guest.wait('Power down', timeout=300)
    finally:
        guest.close()

    for mode, extra in (('bios', []), ('uefi', ['-bios', '/usr/share/ovmf/OVMF.fd'])):
        print(mode.upper() + ': boot do disco instalado pelo Limine', flush=True)
        guest = Guest(mode, disk(False) + extra)
        try:
            guest.root_shell()
            checks = [
                'test -f /etc/fliperos/installed',
                '! grep -qw boot=live /proc/cmdline',
                'grep -qw consoleblank=0 /proc/cmdline',
                'uname -r | grep -q -- -15khz',
                'fliperos-setup --version',
                'test -f /etc/fliperos/firstboot',
                'test -x /opt/fliperos/bin/fliperos-session',
            ]
            for check in checks:
                assert guest.run(check) == 0, mode + ': falhou ' + check
            guest.send('poweroff')
            guest.wait('Power down', timeout=300)
            print(mode.upper() + ': ok', flush=True)
        finally:
            guest.close()


def screens(iso):
    """Boot de verdade: menu do Limine (30 s ate a entrada padrao), tty1 com
    autologin e o fliperos-setup no console do Linux, com a paleta Dracula."""
    print('SCREENS: boot pelo Limine, fotos do tty1', flush=True)
    guest = Guest('screens', disk(True) + ['-cdrom', str(iso), '-vga', 'std'], monitor=True)
    try:
        time.sleep(20)
        guest.screenshot('00-limine')
        # Da tempo do timer de 30 s, do boot e do teste de saidas comecar.
        steps = [(240, '01-output-test-intro', None), (20, '02-testing-output', 'ret'),
                 (15, '03-testing-results', 'ret'), (10, '04-monitor-type', 'ret'),
                 (10, '05-fliperos-setup', 'ret'), (10, '06-configure-video', 'n'),
                 (15, '07-disk-selection', None)]
        for wait, name, key in steps:
            time.sleep(wait)
            guest.screenshot(name)
            if key:
                guest.key(key)
        time.sleep(10)
        guest.screenshot('08-after')
    finally:
        guest.close()


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] not in ('install', 'screens'):
        print(__doc__)
        sys.exit(2)
    {'install': install, 'screens': screens}[sys.argv[1]](Path(sys.argv[2]))
