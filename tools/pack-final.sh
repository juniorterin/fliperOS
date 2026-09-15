#!/usr/bin/env bash
set -euo pipefail
[[ -f /.dockerenv && -d /audit/root/etc ]] || exit 1
root=/audit/root
cp /workspace/fliperos-*.sh /workspace/fliperos-*.py /workspace/crt15-edid.bin "$root/opt/fliperos/"
cp -a /workspace/config "$root/opt/fliperos/"
cp /workspace/README.md /workspace/fliperos-doc.html "$root/opt/fliperos/"
bash /workspace/fliperos-install-video.sh "$root"
kernel=$(find "$root/lib/modules" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort -V | tail -1)
cp "$root/usr/src/linux-headers-$kernel/.config" "$root/boot/config-$kernel"
rm -f "$root/boot"/*.dpkg-bak "$root/boot"/*.new
cp /workspace/config/grub.cfg /audit/iso/boot/grub/grub.cfg
mksquashfs "$root" /audit/iso/live/filesystem.squashfs -noappend -comp zstd -Xcompression-level 6 \
    -processors 2 -no-progress -wildcards -e 'dev/*' 'proc/*' 'sys/*' 'run/*' 'tmp/*' > /audit/squash.log
grub-mkrescue -o /audit/fliperos-0.6.iso /audit/iso -- -volid FLIPEROS_0_6 > /audit/iso.log 2>&1
sha256sum /audit/fliperos-0.6.iso
