"""Testes da midia em VM (QEMU/TCG, sem KVM), no container fliperos-vmtest.

    python3 tools/vm-test.py install ISO   instala num disco descartavel pela
                                           lib do fliperos-setup e boota o
                                           disco instalado em BIOS e em UEFI
    python3 tools/vm-test.py screens ISO   boota pelo menu do Limine e
                                           fotografa o tty1 (o Gum no console
                                           de verdade) tela a tela
    python3 tools/vm-test.py desktop ISO   no disco do modo install: abre o
                                           LXDE pelo fluxo do tty1, fotografa
                                           e traz os logs do X e do LXDE
    python3 tools/vm-test.py dev ISO       no disco do modo install, com os
                                           arquivos do repositorio de agora
                                           (sem ISO nova): menu por gamepad
                                           falso, Start desktop, resolucao do
                                           desktop e quirks
    python3 tools/vm-test.py site ISO      fotos para o site: menu, Setup,
                                           frontends e desktop no disco do
                                           modo install (console 640x480) e
                                           o instalador da midia live

Tudo acontece em /audit (um volume do Docker, nunca uma pasta do Windows):
disco qcow2, logs e as fotos em PNG.
"""
import base64
import io
from pathlib import Path
import re
import socket
import struct
import subprocess
import sys
import tarfile
import time
import zlib

BASE = Path('/audit')
assert Path('/.dockerenv').exists(), 'rode dentro do container'
PASSWORD = 'fliperos'
# O shell do usuario e o zsh com o tema Dracula (seta), o bash ("$ ") ou o
# tema no console do Linux ("> ").
PROMPT = r'(\$ |➜ |> )'
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
        self.wait(PROMPT)
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


def desktop(iso):
    """Disco ja instalado (o do modo install): o launcher vira o LXDE, o tty1
    faz o login de novo pelo fluxo normal (.zprofile -> fliperos-tty1 ->
    fliperos-session) e a tela e fotografada, com os logs do X e do LXDE."""
    print('DESKTOP: boot do disco instalado, launcher = LXDE', flush=True)
    guest = Guest('desktop', disk(False) + ['-vga', 'std'], monitor=True)
    try:
        guest.root_shell()
        guest.run('echo lxde > /etc/fliperos/session; rm -f /etc/fliperos/firstboot')
        guest.run('systemctl restart getty@tty1')
        time.sleep(150)
        guest.screenshot('desktop-01')
        guest.run("ps -eo user,args | grep -E 'Xorg|xinit|lxsession|openbox|lxpanel|pcmanfm' | grep -v grep")
        guest.run('tail -n 40 /home/fliperos/.local/share/xorg/Xorg.0.log 2>/dev/null || tail -n 40 /var/log/Xorg.0.log')
        guest.run('tail -n 30 /home/fliperos/.cache/lxsession/LXDE/run.log 2>/dev/null')
        guest.run('journalctl -b --no-pager -n 40 _COMM=Xorg 2>/dev/null; journalctl -b --no-pager -u getty@tty1 -n 20')
        time.sleep(30)
        guest.screenshot('desktop-02')

        # Fase 2, o caminho do gabinete: menu principal > Start desktop (o
        # setup como root abre o LXDE por runuser) com o xorg.conf de 15 kHz
        # que a lib gera para um monitor de arcade.
        print('DESKTOP: menu principal > Start desktop, xorg.conf de 15 kHz', flush=True)
        load = 'for f in %s/lib/*.sh; do . "$f"; done' % LIB
        guest.run("bash -c '%s; conf_set monitor generic_15; conf_set connector Virtual-1; "
                  "conf_set boot_resolution 640x240S; xorg_generate' && cat /etc/X11/xorg.conf.d/10-fliperos.conf" % load)
        guest.run('rm -f /home/fliperos/.local/share/xorg/Xorg.0.log; echo setup > /etc/fliperos/session; '
                  'pkill -u fliperos -x xinit; true')
        time.sleep(60)
        guest.screenshot('desktop-03-menu')
        for key in ('down', 'down', 'ret'):
            guest.key(key)
            time.sleep(3)
        time.sleep(150)
        guest.screenshot('desktop-04')
        guest.run("ps -eo user,args | grep -E 'Xorg|xinit|lxsession|openbox|lxpanel|pcmanfm' | grep -v grep")
        guest.run("grep -E '\\(EE\\)|\\(WW\\)|Modeline|Output|modeset' /home/fliperos/.local/share/xorg/Xorg.0.log | tail -n 60")
        guest.run('tail -n 30 /var/log/fliperos-setup.log')
    finally:
        guest.close()


def push(guest, paths, dest='/tmp/repo'):
    """Leva arquivos do repositorio (cwd) para a VM pelo console serial."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        for p in paths:
            tar.add(p, arcname=p, filter=lambda ti: None if '__pycache__' in ti.name else ti)
    lines = base64.encodebytes(buf.getvalue()).decode().splitlines()
    guest.run("export PS2=''; rm -rf %s /tmp/push.tgz; mkdir -p %s" % (dest, dest))
    guest.send("base64 -d > /tmp/push.tgz << 'B64EOF'")
    for line in lines:
        guest.send(line)
    guest.send('B64EOF')
    guest.wait('VMROOT> ')
    assert guest.run('tar xzf /tmp/push.tgz -C %s' % dest) == 0, 'push falhou'


def dev(iso):
    """Sem ISO nova: o disco do modo install recebe os arquivos do
    repositorio de agora (o fliperos-rootfs.sh roda dentro da VM). O menu e
    usado por um gamepad falso (uinput) ate o Start desktop, que abre pelo
    laco do fliperos-tty1; depois a resolucao do desktop e os quirks."""
    print('DEV: disco instalado + arquivos do repositorio', flush=True)
    guest = Guest('dev', disk(False) + ['-vga', 'std'], monitor=True)
    load = 'for f in %s/lib/*.sh; do . "$f"; done' % LIB
    # Sem o LC_ALL=C deste shell (um terminal VTE leria as bordas do Gum como
    # ASCII).
    as_user = "runuser -u fliperos -- env -u LC_ALL LANG=C.UTF-8 DISPLAY=:0 "
    try:
        guest.root_shell()
        push(guest, ['fliperos-setup', 'config', 'fliperos-rootfs.sh', 'fliperos-video-check.py',
                     'tools/vm-fakepad.py', 'updates'])
        assert guest.run('bash /tmp/repo/fliperos-rootfs.sh / > /tmp/rootfs.log 2>&1 || '
                         '{ tail /tmp/rootfs.log; false; }') == 0, 'fliperos-rootfs.sh falhou'
        guest.run('python3 /tmp/repo/config/fliperos-update record /tmp/repo', 1800)
        guest.run('grep -o "<application title=.Screen Resolution.*" /home/fliperos/.config/openbox/lxde-rc.xml')
        guest.run('systemctl daemon-reload; systemctl restart fliperos-padkeys; sleep 2; '
                  'systemctl is-active fliperos-padkeys')
        guest.run('echo setup > /etc/fliperos/session; rm -f /etc/fliperos/firstboot '
                  '/home/fliperos/.local/share/xorg/Xorg.0.log; systemctl restart getty@tty1')
        time.sleep(45)
        guest.screenshot('dev-01-menu')
        guest.run('ls -l /run/fliperos/padkeys')

        print('DEV: gamepad falso: baixo, baixo, A (Start desktop)', flush=True)
        guest.run('python3 /tmp/repo/tools/vm-fakepad.py down down a', timeout=120)
        time.sleep(120)
        guest.screenshot('dev-02-desktop')
        guest.run("ps -eo user,args | grep -E 'Xorg|lxsession|fliperos-setup' | grep -v grep")
        guest.run("grep -E '\\(EE\\) +[^ ]' /home/fliperos/.local/share/xorg/Xorg.0.log | tail; "
                  "ls -l /run/fliperos/padkeys; cat /run/fliperos/launch")

        print('DEV: resolucao guardada (320x240) aplicada no desktop', flush=True)
        guest.run("runuser -u fliperos -- sh -c 'mkdir -p ~/.config/fliperos; "
                  "echo 320 240 60 > ~/.config/fliperos/desktop-mode'")
        guest.run(as_user + '/opt/fliperos/bin/fliperos-resolution --apply-saved; echo apply=$?; '
                  + as_user + 'xrandr --query | head -3')
        time.sleep(10)
        guest.screenshot('dev-03-320x240')

        print('DEV: Screen Resolution: 384x288 sem confirmar (volta), depois o do boot', flush=True)
        guest.run("runuser -u fliperos -- rm -f /home/fliperos/.config/fliperos/desktop-mode; ("
                  + as_user + "WINIT_X11_SCALE_FACTOR=1 setsid alacritty --title 'Screen Resolution' "
                  "-e /opt/fliperos/bin/fliperos-resolution > /dev/null 2>&1 &)")
        time.sleep(25)
        guest.screenshot('dev-04-app')
        for key in ('down', 'down', 'ret'):
            guest.key(key)
            time.sleep(2)
        time.sleep(10)
        guest.screenshot('dev-05-384x288-confirm')
        guest.run(as_user + 'xrandr --query | head -3')
        time.sleep(25)
        guest.screenshot('dev-06-reverted')
        guest.run(as_user + 'xrandr --query | head -3')
        for key in ('ret', 'up', 'up', 'ret'):
            guest.key(key)
            time.sleep(3)
        time.sleep(8)
        guest.screenshot('dev-07-boot-confirm')
        guest.key('ret')
        time.sleep(8)
        guest.screenshot('dev-08-back-to-list')
        guest.run(as_user + 'xrandr --query | head -3; ls -l /home/fliperos/.config/fliperos/')

        print('DEV: quirk salvo na linha do kernel', flush=True)
        guest.run("bash -c '%s; quirk_add \"Test encoder\" 0x16c0:0x05e1:0x40 && boot_apply'; "
                  "cat /etc/fliperos/quirks.conf; grep -o 'usbhid.quirks=[^ ]*' /etc/default/fliperos-boot "
                  "/boot/efi/limine/limine.conf" % load, 300)
    finally:
        guest.close()


SITE_VIDEO = 'video=Virtual-1:640x480'


def site_session(guest, session, wait, shots):
    """Troca o launcher do tty1 e fotografa; shots = [(espera, nome, tecla)]."""
    guest.run("pkill -u fliperos -f '[a]ttractplus|[e]s-de|[e]mulationstation|[p]egasus-fe|[x]init'; sleep 3; "
              "echo %s > /etc/fliperos/session; systemctl restart getty@tty1" % session)
    time.sleep(wait)
    for pause, name, key in shots:
        if key:
            guest.key(key)
        time.sleep(pause)
        guest.screenshot(name)


def site(iso):
    """Fotos para o site (website/public/screenshots): o disco do modo
    install com os arquivos do repositorio de agora, console em 640x480 como
    no tubo, e depois a midia live num disco descartavel a parte."""
    print('SITE: disco instalado + arquivos do repositorio, console 640x480', flush=True)
    guest = Guest('site-prep', disk(False) + ['-vga', 'std'])
    try:
        guest.root_shell()
        push(guest, ['fliperos-setup', 'config', 'fliperos-rootfs.sh', 'fliperos-video-check.py',
                     'fliperos-limine-update.py', 'updates'])
        assert guest.run('bash /tmp/repo/fliperos-rootfs.sh / > /tmp/rootfs.log 2>&1 || '
                         '{ tail /tmp/rootfs.log; false; }', 1800) == 0, 'fliperos-rootfs.sh falhou'
        # Com os arquivos de agora o disco ja esta no ultimo update: sem isso o
        # aviso de update do boot tomaria o tty1 no lugar do menu.
        guest.run('python3 /tmp/repo/config/fliperos-update record /tmp/repo', 1800)
        guest.run("sed -i -E 's/ video=[^ \"]*//g; s|^FLIPEROS_CMDLINE=\"(.*)\"$|FLIPEROS_CMDLINE=\"\\1 %s\"|' "
                  "/etc/default/fliperos-boot && grep FLIPEROS_CMDLINE /etc/default/fliperos-boot && "
                  "/usr/local/sbin/fliperos-limine-update" % SITE_VIDEO, 300)
        guest.run('rm -f /etc/fliperos/firstboot; echo setup > /etc/fliperos/session; '
                  'for b in attractplus emulationstation pegasus-fe; do command -v $b || echo "sem $b"; done')
        guest.send('poweroff')
        guest.wait('Power down', timeout=300)
    finally:
        guest.close()

    guest = Guest('site', disk(False) + ['-vga', 'std'], monitor=True)
    try:
        guest.root_shell()
        guest.run('cat /proc/cmdline')
        time.sleep(20)
        guest.screenshot('site-menu')
        for key, pause, name in (('down', 2, None), ('ret', 8, 'site-setup'), ('ret', 10, 'site-video')):
            guest.key(key)
            time.sleep(pause)
            if name:
                guest.screenshot(name)
        for _ in range(4):
            guest.key('esc')
            time.sleep(2)

        print('SITE: frontends e desktop', flush=True)
        site_session(guest, 'attractplus', 120, [(0, 'site-attract-mode', None)])
        site_session(guest, 'emulationstation', 180, [(0, 'site-es-de', None), (5, 'site-es-de-2', 'ret')])
        site_session(guest, 'pegasus', 150, [(0, 'site-pegasus', None)])
        site_session(guest, 'lxde', 150, [])
        guest.run("runuser -u fliperos -- env DISPLAY=:0 xrandr --output Virtual-1 --mode 640x480; true")
        time.sleep(15)
        guest.screenshot('site-desktop')
        guest.key('ctrl-esc')
        time.sleep(5)
        guest.screenshot('site-desktop-menu')
        guest.run("pkill -u fliperos -x xinit; echo setup > /etc/fliperos/session")
        guest.send('poweroff')
        guest.wait('Power down', timeout=300)
    finally:
        guest.close()

    print('SITE: midia live (disco descartavel), telas do instalador', flush=True)
    boot = extract_boot(iso)
    scratch = BASE / 'site-live.qcow2'
    scratch.unlink(missing_ok=True)
    subprocess.run(['qemu-img', 'create', '-f', 'qcow2', str(scratch), '20G'], check=True, capture_output=True)
    guest = Guest('site-live', ['-drive', 'file=%s,format=qcow2,if=virtio' % scratch, '-vga', 'std',
                                '-kernel', str(boot / 'vmlinuz'), '-initrd', str(boot / 'initrd.img'),
                                '-append', 'boot=live fliperos.boot=svga consoleblank=0 ' + SITE_VIDEO,
                                '-cdrom', str(iso)], monitor=True)
    try:
        time.sleep(240)
        steps = [(0, 'site-live-1', None), (20, 'site-live-2', 'ret'), (15, 'site-live-3', 'ret'),
                 (10, 'site-live-4', 'ret'), (10, 'site-live-5', 'ret'), (10, 'site-live-6', 'n'),
                 (15, 'site-live-7', None)]
        for pause, name, key in steps:
            if key:
                guest.key(key)
            time.sleep(pause)
            guest.screenshot(name)
    finally:
        guest.close()
        scratch.unlink(missing_ok=True)


if __name__ == '__main__':
    modes = {'install': install, 'screens': screens, 'desktop': desktop, 'dev': dev, 'site': site}
    if len(sys.argv) != 3 or sys.argv[1] not in modes:
        print(__doc__)
        sys.exit(2)
    modes[sys.argv[1]](Path(sys.argv[2]))
