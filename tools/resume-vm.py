"""Resume a long-running TCG installation without discarding the virtual disk."""
from pathlib import Path
import os
import re
import socket
import time

assert Path('/.dockerenv').exists()
log = open('/audit/vm-live.log', 'ab', buffering=0)
sock = socket.socket(socket.AF_UNIX)
sock.connect('/audit/serial-live.sock')
sock.settimeout(1)
buffer = b''


def wait(pattern, timeout=2400):
    global buffer
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        match = re.search(pattern.encode(), buffer)
        if match:
            buffer = buffer[match.end():]
            return
        try:
            chunk = sock.recv(65536)
            if not chunk:
                if pattern == 'Power down':
                    return
                raise RuntimeError('Serial disconnected')
            log.write(chunk)
            buffer += chunk
        except socket.timeout:
            pass
    raise TimeoutError(pattern + '\n' + buffer[-3000:].decode(errors='replace'))


def send(line):
    sock.sendall(line.encode() + b'\n')


print('Resuming installation already running on disposable /dev/vda', flush=True)
wait('New password:')
send('Vm-test-only-9264')
wait('Retype new password:')
send('Vm-test-only-9264')
wait('Instalacao concluida')
wait('VMROOT> ')
print('INSTALL: succeeded; configuring serial boot on test disk only', flush=True)
send('mount /dev/vda3 /mnt; mount /dev/vda2 /mnt/boot/efi; mount --bind /dev /mnt/dev; mount -t proc proc /mnt/proc; mount -t sysfs sys /mnt/sys')
wait('VMROOT> ')
send("printf 'GRUB_TERMINAL=serial\\nGRUB_SERIAL_COMMAND=\"serial --speed=115200\"\\nGRUB_CMDLINE_LINUX=\"console=ttyS0,115200n8\"\\n' > /mnt/etc/default/grub.d/zz-vm-test.cfg; chroot /mnt update-grub; sync")
wait('VMROOT> ')
send('umount /mnt/dev /mnt/proc /mnt/sys /mnt/boot/efi /mnt; poweroff')
wait('Power down')
sock.close()
log.close()

# Reuse the guest harness definitions without running its live-install entry point.
namespace = {'__name__': 'vm_harness'}
code = Path('/workspace/tools/test-vm.py').read_text().split("print('LIVE: booting")[0]
exec(compile(code, 'vm-harness', 'exec'), namespace)
Guest = namespace['Guest']
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
