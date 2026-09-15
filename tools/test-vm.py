"""Integration test on a disposable QCOW2 disk only, inside the audit container."""
from pathlib import Path
import os
import re
import socket
import subprocess
import time

BASE = Path('/audit')
assert Path('/.dockerenv').exists()
disk = BASE / 'test-install.qcow2'
if not disk.exists():
    subprocess.run(['qemu-img', 'create', '-f', 'qcow2', str(disk), '20G'], check=True)


class Guest:
    def __init__(self, mode):
        self.mode = mode
        self.log = open(BASE / ('vm-' + mode + '.log'), 'wb', buffering=0)
        serial = str(BASE / ('serial-' + mode + '.sock'))
        Path(serial).unlink(missing_ok=True)
        cmd = ['qemu-system-x86_64', '-m', '2048', '-smp', '2', '-accel', 'tcg',
               '-display', 'none', '-serial', 'unix:' + serial + ',server=on,wait=off',
               '-monitor', 'none', '-no-reboot', '-nic', 'none',
               '-object', 'rng-random,filename=/dev/urandom,id=rng0', '-device', 'virtio-rng-pci,rng=rng0',
               '-drive', 'file=' + str(disk) + ',format=qcow2,if=virtio']
        if mode == 'live':
            cmd += ['-kernel', '/audit/iso/boot/vmlinuz', '-initrd', '/audit/iso/boot/initrd.img',
                    '-append', 'boot=live components console=ttyS0,115200n8 systemd.wants=serial-getty@ttyS0.service',
                    '-cdrom', '/audit/fliperos-0.6.iso']
        elif mode == 'uefi':
            cmd += ['-bios', '/usr/share/OVMF/OVMF_CODE.fd']
        self.proc = subprocess.Popen(cmd, stdout=self.log, stderr=self.log)
        for _ in range(100):
            if Path(serial).exists():
                break
            time.sleep(.1)
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.connect(serial)
        self.sock.settimeout(1)
        self.buffer = b''

    def wait(self, pattern, timeout=600):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            match = re.search(pattern.encode(), self.buffer)
            if match:
                self.buffer = self.buffer[match.end():]
                return
            if self.proc.poll() is not None:
                if pattern == 'Power down' and self.proc.returncode == 0:
                    return
                raise RuntimeError('QEMU exited: ' + self.mode)
            try:
                data = self.sock.recv(65536)
                self.log.write(data)
                self.buffer += data
            except socket.timeout:
                continue
        raise TimeoutError(self.mode + ' waiting for ' + pattern + '\n' + self.buffer[-2500:].decode(errors='replace'))

    def send(self, line):
        self.sock.sendall(line.encode() + b'\n')

    def login(self, password):
        self.wait('login:')
        self.send('fliperos')
        self.wait('Password:')
        self.send(password)
        self.wait(r'\$ ')
        self.send("sudo -p 'TEST_SUDO:' bash")
        self.wait('TEST_SUDO:')
        self.send(password)
        self.wait(r'# ')
        self.send("export LC_ALL=C PS1='VMROOT> '; stty -echo")
        self.wait('VMROOT> ')

    def close(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        self.sock.close()
        self.log.close()


print('LIVE: booting kernel/initramfs with ISO filesystem', flush=True)
guest = Guest('live')
try:
    guest.login('fliperos')
    print('LIVE: login succeeded; installing to disposable /dev/vda', flush=True)
    guest.send('python3 -c \'import runpy; m=runpy.run_path("/usr/local/bin/fliperos-install"); m["install"](m["get_disk"]("/dev/vda"), "VGA-1")\'')
    guest.wait('Para confirmar, digite APAGAR /dev/vda:')
    guest.send('APAGAR /dev/vda')
    guest.wait('New password:', timeout=600)
    guest.send('Vm-test-only-9264')
    guest.wait('Retype new password:')
    guest.send('Vm-test-only-9264')
    guest.wait('Instalacao concluida', timeout=120)
    guest.wait('VMROOT> ')
    print('INSTALL: succeeded; enabling serial console on test disk only', flush=True)
    guest.send("mount /dev/vda3 /mnt; mount /dev/vda2 /mnt/boot/efi; mount --bind /dev /mnt/dev; mount -t proc proc /mnt/proc; mount -t sysfs sys /mnt/sys")
    guest.wait('VMROOT> ')
    guest.send("printf 'GRUB_TERMINAL=serial\\nGRUB_SERIAL_COMMAND=\"serial --speed=115200\"\\nGRUB_CMDLINE_LINUX=\"console=ttyS0,115200n8\"\\n' > /mnt/etc/default/grub.d/zz-vm-test.cfg; chroot /mnt update-grub; sync")
    guest.wait('VMROOT> ', timeout=120)
    guest.send('umount /mnt/dev /mnt/proc /mnt/sys /mnt/boot/efi /mnt; poweroff')
    guest.wait('Power down', timeout=120)
finally:
    guest.close()

for mode in ('bios', 'uefi'):
    print(mode.upper() + ': booting installed disk through GRUB', flush=True)
    guest = Guest(mode)
    try:
        guest.login('Vm-test-only-9264')
        guest.send('test -f /etc/fliperos/installed && ! grep -qw boot=live /proc/cmdline && echo INSTALLED_BOOT_OK')
        guest.wait('INSTALLED_BOOT_OK')
        guest.wait('VMROOT> ')
        guest.send('poweroff')
        guest.wait('Power down', timeout=120)
        print(mode.upper() + ': installed boot passed', flush=True)
    finally:
        guest.close()
