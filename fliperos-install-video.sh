#!/usr/bin/env bash
# Shared assets used by setup, new ISO builds and audited ISO repacks.
set -euo pipefail
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
root=${1:-/}
[[ -d "$root/etc" ]] || { echo "Rootfs invalido: $root" >&2; exit 2; }
install -Dm644 "$src/crt15-edid.bin" "$root/lib/firmware/edid/crt15.bin"
install -Dm755 "$src/fliperos-video-check.py" "$root/usr/local/bin/fliperos-video-check"
install -Dm755 "$src/fliperos-video-autodetect.py" "$root/usr/local/bin/fliperos-video-autodetect"
install -Dm755 "$src/fliperos-install.py" "$root/usr/local/bin/fliperos-install"
install -Dm755 "$src/config/fliperos-edid-hook" "$root/etc/initramfs-tools/hooks/fliperos-edid"
install -Dm644 "$src/config/switchres.ini" "$root/etc/fliperos/switchres.ini"
install -Dm644 "$src/config/switchres.ini" "$root/etc/switchres.ini"
install -Dm644 "$src/config/xorg.conf" "$root/etc/fliperos/xorg.conf"
if [[ ! -f "$root/etc/fliperos/connector" ]]; then
    printf 'VGA-1\n' > "$root/etc/fliperos/connector"
fi
for name in fliperos-x11-run fliperos-x11-client fliperos-launcher; do
    install -Dm755 "$src/config/$name" "$root/opt/fliperos/bin/$name"
done
mkdir -p "$root/usr/local/bin"
ln -sf /opt/fliperos/bin/fliperos-launcher "$root/usr/local/bin/fliperos-launcher"
install -Dm644 "$src/config/mame.ini" "$root/etc/fliperos/mame/mame.ini"
install -Dm644 "$src/config/fliperos-video-check.service" "$root/etc/systemd/system/fliperos-video-check.service"
mkdir -p "$root/etc/systemd/system/multi-user.target.wants"
ln -sf ../fliperos-video-check.service "$root/etc/systemd/system/multi-user.target.wants/fliperos-video-check.service"
# Users, hostname, locale, Xorg and login are already configured in this image.
# Debian live-config would try to create its default user on the same UID 1000.
ln -sf /dev/null "$root/etc/systemd/system/live-config.service"
# Old oneshot switches were interactive, used an invalid API and could restore the old mode.
rm -f "$root/etc/systemd/system/multi-user.target.wants/fliperos-switchres-init.service"
rm -f "$root/etc/systemd/system/fliperos-switchres-init.service"
# Select SI/CIK radeon support without disabling amdgpu for every other GPU.
cat > "$root/etc/modprobe.d/fliperos.conf" <<'EOF'
options radeon si_support=1 cik_support=1 dpm=1
options amdgpu si_support=0 cik_support=0
EOF
# Show the live installation wizard automatically, as gasetup does.
if [[ -d "$root/home/fliperos" ]]; then
    cat > "$root/home/fliperos/.bash_profile" <<'EOF'
if [[ -z "${DISPLAY:-}" && "$(tty)" == /dev/tty1 ]]; then
    if [[ ! -f /etc/fliperos/installed ]]; then
        sudo /usr/local/bin/fliperos-install
    else
        /opt/fliperos/bin/fliperos-launcher
    fi
fi
EOF
    cat > "$root/etc/sudoers.d/fliperos-installer" <<'EOF'
fliperos ALL=(root) NOPASSWD: /usr/local/bin/fliperos-install
EOF
    chmod 440 "$root/etc/sudoers.d/fliperos-installer"
fi
# Both live and installed systems enter the setup menu, not an untested game.
cat > "$root/etc/profile.d/fliperos.sh" <<'EOF'
if [ "$(tty 2>/dev/null)" = /dev/tty1 ]; then
    echo "FliperOS: sudo fliperos-install (monitor / live / instalar em disco)"
    echo "Diagnostico: sudo fliperos-video-check"
fi
EOF
