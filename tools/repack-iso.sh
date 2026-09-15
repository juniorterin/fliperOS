#!/usr/bin/env bash
# Run in the isolated audit container; never mount the host /dev into a chroot.
set -euo pipefail
[[ -f /.dockerenv ]] || { echo 'Use the audit Docker container'; exit 1; }
src=/workspace
root=/audit/root
[[ -d "$root/etc" && -f /audit/filesystem.squashfs ]] || exit 1
mkdir -p "$root/dev/pts" "$root/proc" "$root/sys" "$root/boot" /audit/iso/boot/grub /audit/iso/live
for item in null:1:3 zero:1:5 random:1:8 urandom:1:9; do
    IFS=: read -r name major minor <<< "$item"
    [[ -c "$root/dev/$name" ]] || mknod -m 666 "$root/dev/$name" c "$major" "$minor"
done
cp /etc/resolv.conf "$root/etc/resolv.conf"
printf '#!/bin/sh\nexit 101\n' > "$root/usr/sbin/policy-rc.d"
chmod +x "$root/usr/sbin/policy-rc.d"
xorriso -osirrox on -indev "$src/output/fliperos-0.5.iso" \
    -extract /boot/vmlinuz /audit/vmlinuz 2>/audit/kernel-extract.log
kernel=$(find "$root/lib/modules" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort -V | tail -1)
cp /audit/vmlinuz "$root/boot/vmlinuz-$kernel"
cp /audit/initrd.img "$root/boot/initrd.img-$kernel"
chroot "$root" apt-get update -qq
chroot "$root" env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 pciutils libdrm-tests edid-decode squashfs-tools grub-pc-bin grub-efi-amd64-bin grub2-common
mkdir -p "$root/opt/fliperos"
cp "$src"/fliperos-*.sh "$src"/fliperos-*.py "$src/crt15-edid.bin" "$root/opt/fliperos/"
cp -a "$src/config" "$root/opt/fliperos/"
bash "$src/fliperos-install-video.sh" "$root"
ln -sf /opt/fliperos/bin/fliperos-launcher "$root/usr/local/bin/fliperos-launcher"
mkdir -p "$root/etc/systemd/system/ssh.service.d"
printf '[Service]\nExecStartPre=/usr/bin/ssh-keygen -A\n' > "$root/etc/systemd/system/ssh.service.d/keys.conf"
rm -f "$root"/etc/ssh/ssh_host_*
truncate -s 0 "$root/etc/machine-id"
chroot "$root" update-initramfs -u -k "$kernel"
chroot "$root" lsinitramfs "/boot/initrd.img-$kernel" | grep 'firmware/edid/crt15.bin'
chroot "$root" /usr/local/bin/switchres 640 240 60 --calc --ini /etc/fliperos/switchres.ini
chroot "$root" /usr/local/bin/switchres 640 480 60 --calc --ini /etc/fliperos/switchres.ini
chroot "$root" visudo -c
chroot "$root" apt-get clean
rm -f "$root/usr/sbin/policy-rc.d"
cp "$root/boot/vmlinuz-$kernel" /audit/iso/boot/vmlinuz
cp "$root/boot/initrd.img-$kernel" /audit/iso/boot/initrd.img
cp "$src/config/grub.cfg" /audit/iso/boot/grub/grub.cfg
mksquashfs "$root" /audit/iso/live/filesystem.squashfs -noappend -comp zstd -Xcompression-level 6 -processors 2 \
    -no-progress -wildcards -e 'dev/*' 'proc/*' 'sys/*' 'run/*' 'tmp/*' > /audit/squash.log
grub-mkrescue -o /audit/fliperos-0.6.iso /audit/iso -- -volid FLIPEROS_0_6 > /audit/iso.log 2>&1
sha256sum /audit/fliperos-0.6.iso
