# shellcheck shell=bash
# Recovery Mode: reparos num FliperOS ja instalado, a partir da midia.
# Equivale ao worker_rescue_menu do gasetup (chroot na instalacao, "Fix
# UEFI boot") mais os reparos que o instalador anterior ja tinha.

RECOVERY_TARGET=${RECOVERY_TARGET:-/mnt/fliperos-recovery}

# Tudo que a reextracao do sistema NAO sobrescreve: ROMs, saves, a home,
# identidade da maquina e a configuracao que ja funciona nesse disco.
RECOVERY_PRESERVE=(
  /opt/fliperos/roms /opt/fliperos/saves /home /etc/machine-id /etc/ssh /etc/fstab
  /etc/fliperos /etc/switchres.ini /etc/default/fliperos-boot /etc/asound.conf
  /etc/NetworkManager/system-connections /etc/X11/xorg.conf.d /boot
)

# recovery_find imprime "disco|particao|conector|monitor" para cada disco
# com FliperOS: particao ext4 rotulada FliperOS com o marcador de instalacao.
recovery_find() {
  local part disk probe
  probe=$(mktemp -d /tmp/fliperos-probe.XXXXXX) || return 1
  while read -r part disk; do
    [[ -n $part ]] || continue
    mount -o ro "$part" "$probe" 2> /dev/null || continue
    if [[ -f $probe$FLIPEROS_ETC/installed ]]; then
      printf '%s|%s|%s|%s\n' "$disk" "$part" \
        "$(conf_get connector "$probe$FLIPEROS_CONF" 2> /dev/null || cat "$probe$FLIPEROS_ETC/connector" 2> /dev/null)" \
        "$(conf_get monitor "$probe$FLIPEROS_CONF" 2> /dev/null)"
    fi
    umount "$probe" 2> /dev/null
  done < <(lsblk --json -p -o PATH,LABEL,PKNAME,MOUNTPOINTS 2> /dev/null | jq -r '
    .. | objects | select(.label? == "FliperOS")
    | select(([.mountpoints // [] | .[] | select(. != null)] | length) == 0)
    | "\(.path) \(.pkname)"')
  rmdir "$probe" 2> /dev/null
  return 0
}

# recovery_mount DISCO monta raiz, ESP e o chroot do disco.
recovery_mount() {
  local disk=$1 root esp dir
  root=$(disk_partition_path "$disk" 3)
  esp=$(disk_partition_path "$disk" 2)
  recovery_umount
  mkdir -p "$RECOVERY_TARGET"
  run_logged mount "$root" "$RECOVERY_TARGET" || return 1
  mkdir -p "$RECOVERY_TARGET/boot/efi"
  run_logged mount "$esp" "$RECOVERY_TARGET/boot/efi" || { recovery_umount; return 1; }
  for dir in dev proc sys run; do
    if ! mount --rbind "/$dir" "$RECOVERY_TARGET/$dir" || ! mount --make-rslave "$RECOVERY_TARGET/$dir"; then
      recovery_umount
      return 1
    fi
  done
}

recovery_umount() {
  if mountpoint -q "$RECOVERY_TARGET" 2> /dev/null; then
    umount -R "$RECOVERY_TARGET" >> "$FLIPEROS_LOG" 2>&1 || umount -R -l "$RECOVERY_TARGET" >> "$FLIPEROS_LOG" 2>&1
  fi
  return 0
}

# recovery_bootloader DISCO reinstala o Limine (BIOS e UEFI) e refaz o menu
# com o kernel do disco: o "Fix UEFI boot" do gasetup, para os dois modos.
recovery_bootloader() {
  local disk=$1
  ev_step 10 "Mounting $disk"
  recovery_mount "$disk" || { ev_fail "Could not mount the installed system"; return 1; }
  ev_step 50 "Installing the bootloader"
  if ! install_bootloader "$RECOVERY_TARGET" "$disk"; then
    recovery_umount
    ev_fail "Limine could not be installed"
    return 1
  fi
  ev_step 95 "Unmounting"
  sync
  recovery_umount
  ev_step 100 "Bootloader reinstalled"
}

# recovery_video DISCO leva para o disco a configuracao de video desta
# sessao (teste de saidas e Video Setup): para quando a placa de video foi
# trocada e o sistema instalado ficou sem imagem. So o video: o modo de
# latencia, o audio e o launcher do disco ficam como estavam.
recovery_video() {
  local disk=$1
  ev_step 10 "Mounting $disk"
  recovery_mount "$disk" || { ev_fail "Could not mount the installed system"; return 1; }
  ev_step 30 "Writing the video settings"
  if ! install_configure_video "$RECOVERY_TARGET" video; then
    recovery_umount
    ev_fail "Could not write the video settings"
    return 1
  fi
  ev_step 50 "Generating the initramfs"
  ev_run chroot "$RECOVERY_TARGET" update-initramfs -u -k all || { recovery_umount; return 1; }
  ev_step 95 "Unmounting"
  sync
  recovery_umount
  ev_step 100 "Video settings applied"
}

# recovery_dpkg_extra ANTIGO NOVO imprime os paragrafos do status do dpkg
# ANTIGO cujo pacote (nome e arquitetura) nao esta no NOVO.
recovery_dpkg_extra() {
  awk '
    function key(p,   pkg, arch) {
      pkg = p
      sub(/^(.*\n)?Package: */, "", pkg)
      sub(/\n.*/, "", pkg)
      arch = ""
      if (p ~ /(^|\n)Architecture: /) {
        arch = p
        sub(/^(.*\n)?Architecture: */, "", arch)
        sub(/\n.*/, "", arch)
      }
      return pkg ":" arch
    }
    BEGIN { RS = ""; ORS = "\n\n" }
    FNR == NR { seen[key($0)] = 1; next }
    !(key($0) in seen) { print }' "$2" "$1"
}

# recovery_dpkg_merge ANTIGO NOVO: o banco do dpkg fica o da midia (coerente
# com os arquivos que voltaram) mais os pacotes instalados depois da
# instalacao (frontends do repositorio e suas dependencias), cujos arquivos o
# rsync nao apaga. Sem isso o apt esqueceria que eles existem.
recovery_dpkg_merge() {
  local old=$1 new=$2 extra
  [[ -s $old && -f $new ]] || return 0
  extra=$(recovery_dpkg_extra "$old" "$new") || return 1
  [[ -n $extra ]] || return 0
  printf '\n%s\n' "$extra" >> "$new"
  log_info "recovery: $(grep -c '^Package:' <<< "$extra") pacote(s) instalados depois mantidos no dpkg"
}

# recovery_restore DISCO reextrai o sistema da midia por cima do disco,
# preservando RECOVERY_PRESERVE: conserta pacotes e binarios corrompidos. Os
# pacotes do sistema voltam a versao da midia (o System Update os atualiza
# de novo); os instalados depois continuam registrados.
recovery_restore() {
  local disk=$1 src excludes=() p status
  ev_step 5 "Mounting $disk"
  recovery_mount "$disk" || { ev_fail "Could not mount the installed system"; return 1; }
  status=$(mktemp /tmp/fliperos-dpkg-status.XXXXXX) || { recovery_umount; return 1; }
  cp -f "$RECOVERY_TARGET/var/lib/dpkg/status" "$status" 2> /dev/null || : > "$status"
  src=$(mktemp -d /mnt/fliperos-restore.XXXXXX) || { rm -f "$status"; recovery_umount; return 1; }
  ev_step 10 "Extracting the system from the installation media"
  if ! ev_run unsquashfs -f -d "$src" "$LIVE_IMAGE"; then
    rm -rf "$src" "$status"
    recovery_umount
    return 1
  fi
  for p in "${RECOVERY_PRESERVE[@]}"; do
    excludes+=(--exclude="$p")
  done
  ev_step 60 "Restoring system files"
  if ! ev_run rsync -aHAX "${excludes[@]}" "$src/" "$RECOVERY_TARGET/"; then
    rm -rf "$src" "$status"
    recovery_umount
    return 1
  fi
  rm -rf "$src"
  ev_step 75 "Keeping the packages installed later"
  if ! recovery_dpkg_merge "$status" "$RECOVERY_TARGET/var/lib/dpkg/status"; then
    rm -f "$status"
    recovery_umount
    ev_fail "Could not update the package database"
    return 1
  fi
  rm -f "$status"
  ev_step 80 "Generating the initramfs"
  ev_run chroot "$RECOVERY_TARGET" update-initramfs -u -k all || { recovery_umount; return 1; }
  ev_step 90 "Installing the bootloader"
  install_bootloader "$RECOVERY_TARGET" "$disk" || { recovery_umount; ev_fail "Limine could not be installed"; return 1; }
  sync
  recovery_umount
  ev_step 100 "System files restored"
}
