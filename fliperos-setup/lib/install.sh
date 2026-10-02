# shellcheck shell=bash
# Instalacao em disco, a partir do squashfs da midia live.
#
# E o caminho do instalador anterior (fliperos-install.py, validado em VM
# ate o boot BIOS e UEFI do disco instalado), agora contando o progresso de
# verdade: a copia do sistema usa o "unsquashfs -percentage", a mesma
# tecnica do worker_select_iso_install do gasetup. Fala com a tela so por
# eventos (lib/progress.sh); a saida dos comandos vai para o log.

INSTALL_TARGET=${INSTALL_TARGET:-/mnt/fliperos-target}
INSTALL_LOCK=${INSTALL_LOCK:-/run/lock/fliperos-install.lock}
LIMINE_SHARE=usr/local/share/limine

install_unmount() {
  if mountpoint -q "$INSTALL_TARGET" 2> /dev/null; then
    umount -R "$INSTALL_TARGET" >> "$FLIPEROS_LOG" 2>&1 ||
      umount -R -l "$INSTALL_TARGET" >> "$FLIPEROS_LOG" 2>&1
  fi
  return 0
}

# install_preflight confere, ANTES de apagar qualquer disco, que da para ir
# ate o fim.
install_preflight() {
  local tool file
  [[ $EUID -eq 0 ]] || { ev_fail "The installer must run as root"; return 1; }
  if [[ -f /.dockerenv ]] || grep -qi microsoft /proc/sys/kernel/osrelease 2> /dev/null; then
    ev_fail "Blocked inside Docker/WSL: boot the FliperOS media on the target PC"
    return 1
  fi
  is_live || { ev_fail "Boot from the FliperOS installation media first"; return 1; }
  [[ -f $LIVE_IMAGE ]] || { ev_fail "System image not found: $LIVE_IMAGE"; return 1; }
  for tool in wipefs parted partprobe udevadm mkfs.vfat mkfs.ext4 unsquashfs blkid chroot findmnt flock; do
    have "$tool" || { ev_fail "Missing tool: $tool"; return 1; }
  done
  # O disco novo recebe o Limine do proprio squashfs; a midia tem os mesmos
  # arquivos.
  for file in /usr/local/bin/limine "/$LIMINE_SHARE/limine-bios.sys" "/$LIMINE_SHARE/BOOTX64.EFI" \
    "$LIMINE_UPDATE" /usr/sbin/update-initramfs; do
    [[ -f $file ]] || { ev_fail "Incomplete installation media: $file"; return 1; }
  done
}

# install_copy_system copia o squashfs para o disco contando de 8% a 80%.
install_copy_system() {
  local line pct last=-1 rc=1 tail=""
  log_line cmd "\$ unsquashfs -percentage -f -d $INSTALL_TARGET $LIVE_IMAGE"
  while IFS= read -r line; do
    line=${line//$'\r'/}
    if [[ $line =~ ^[[:space:]]*([0-9]{1,3})[[:space:]]*$ ]]; then
      pct=${BASH_REMATCH[1]}
      ((pct > 100)) && pct=100
      if ((pct != last)); then
        last=$pct
        ev_pct $((8 + pct * 72 / 100))
      fi
    elif [[ $line == "@rc "* ]]; then
      # O status do unsquashfs chega como ultima linha.
      rc=${line#@rc }
    elif [[ -n $line ]]; then
      tail=$line
      printf '%s\n' "$line" >> "$FLIPEROS_LOG"
    fi
  done < <(unsquashfs -percentage -f -d "$INSTALL_TARGET" "$LIVE_IMAGE" 2>&1; printf '@rc %s\n' "$?")
  ((rc == 0)) && return 0
  ev_fail "Copying the system failed: ${tail:-unsquashfs exited with status $rc}"
  return 1
}

# install_write_fstab ALVO RAIZ ESP
install_write_fstab() {
  local target=$1 root_uuid efi_uuid
  root_uuid=$(blkid -s UUID -o value "$2") || return 1
  efi_uuid=$(blkid -s UUID -o value "$3") || return 1
  printf 'UUID=%s / ext4 defaults 0 1\nUUID=%s /boot/efi vfat umask=0077 0 2\n' \
    "$root_uuid" "$efi_uuid" > "$target/etc/fstab"
}

# install_configure_video ALVO [video] leva para o disco o que foi decidido
# nesta sessao: fliperos.conf, Switchres, MAME, Xorg e a linha do kernel.
# Com "video" (Recovery Mode, placa trocada) so as chaves de video mudam no
# fliperos.conf do disco; latencia, audio, launcher e o resto ficam.
install_configure_video() {
  local target=$1 only=${2:-} file key value
  mkdir -p "$target$FLIPEROS_ETC"
  if [[ $only == video ]]; then
    for key in $VIDEO_CONF_KEYS; do
      if value=$(conf_get "$key" 2> /dev/null); then
        conf_set "$key" "$value" "$target$FLIPEROS_CONF"
      else
        conf_unset "$key" "$target$FLIPEROS_CONF"
      fi
    done
    for key in $VIDEO_CONF_KEEP; do
      value=$(conf_get "$key" 2> /dev/null) && conf_set "$key" "$value" "$target$FLIPEROS_CONF"
    done
  else
    [[ -f $FLIPEROS_CONF ]] && cp -f "$FLIPEROS_CONF" "$target$FLIPEROS_CONF"
    [[ -f $QUIRKS_FILE ]] && cp -p "$QUIRKS_FILE" "$target$QUIRKS_FILE"
  fi
  for file in "$SWITCHRES_INI" "$MAME_INI"; do
    [[ -f $file ]] && cp -p "$file" "$target$file"
  done
  # Resolucao personalizada: o EDID gerado nesta sessao vai junto (o
  # update-initramfs do disco novo o poe no initramfs).
  if [[ -f $EDID_DIR/custom_resolution.bin ]]; then
    install -D -m 644 "$EDID_DIR/custom_resolution.bin" "$target$EDID_DIR/custom_resolution.bin"
  fi
  xorg_generate "$target$XORG_CONF" || return 1
  # O retroarch.cfg do disco vem da imagem (super resolucao); a largura sai
  # da placa testada nesta sessao.
  [[ -f $target$RETROARCH_CFG ]] && video_retroarch_super "$target$RETROARCH_CFG"
  # A linha sai do fliperos.conf e dos quirks do disco: nele esta o modo de
  # latencia, e o Recovery Mode nao apaga os quirks que ja estavam la.
  boot_write_cmdline "$(FLIPEROS_CONF=$target$FLIPEROS_CONF QUIRKS_FILE=$target$QUIRKS_FILE \
    boot_install_cmdline)" "$target$BOOT_DEFAULTS"
}

# install_configure_user ALVO: rede e audio configurados na midia vao
# junto, e o primeiro boot pergunta o launcher padrao.
install_configure_user() {
  local target=$1 conn
  printf 'Installed from the FliperOS installation media\n' > "$target$FLIPEROS_ETC/installed"
  : > "$target$FLIPEROS_ETC/firstboot"
  for conn in /etc/NetworkManager/system-connections/*.nmconnection; do
    [[ -f $conn ]] || continue
    install -D -m 600 -o root -g root "$conn" "$target$conn"
  done
  [[ -f /etc/asound.conf ]] && cp -f /etc/asound.conf "$target/etc/asound.conf"
  # Identidade propria: machine-id e chaves SSH novas nesta maquina.
  : > "$target/etc/machine-id"
  rm -f "$target"/etc/ssh/ssh_host_*
  return 0
}

install_bind_mounts() {
  local target=$1 dir
  for dir in dev proc sys run; do
    mkdir -p "$target/$dir"
    mount --rbind "/$dir" "$target/$dir" || return 1
    mount --make-rslave "$target/$dir" || return 1
  done
}

# install_bootloader ALVO DISCO grava o Limine a partir dos arquivos do
# PROPRIO disco: o estagio 2 do bios-install e o limine-bios.sys da ESP tem
# de ser da mesma versao. Exige a ESP em ALVO/boot/efi e o chroot montado.
install_bootloader() {
  local target=$1 disk=$2 esp=$1/boot/efi
  install -D -m 644 "$target/$LIMINE_SHARE/BOOTX64.EFI" "$esp/EFI/BOOT/BOOTX64.EFI" || return 1
  install -D -m 644 "$target/$LIMINE_SHARE/limine-bios.sys" "$esp/limine/limine-bios.sys" || return 1
  run_logged chroot "$target" "$LIMINE_UPDATE" || return 1
  # --force: a particao 1 e a de BIOS boot que o proprio instalador criou e
  # zerou. Sem ele, um resto de sistema de arquivos do disco antigo naquele
  # trecho ("contains a recognised filesystem") barra a instalacao.
  run_logged chroot "$target" /usr/local/bin/limine bios-install --force "$disk" 1
}

# install_run DISCO IDENTIDADE instala no disco. IDENTIDADE e o
# "tamanho|serial|modelo" lido quando a pessoa escolheu o disco: se o disco
# trocou nesse meio tempo, nada e apagado.
install_run() {
  local disk=$1 identity=$2 esp root cmd lockfd reason
  ev_step 1 "Checking the installation media"
  install_preflight || return 1
  exec {lockfd}> "$INSTALL_LOCK"
  if ! flock -n "$lockfd"; then
    ev_fail "Another installation or repair is already running"
    return 1
  fi
  install_unmount

  ev_step 2 "Checking $disk"
  if [[ $(disk_identity "$disk") != "$identity" ]]; then
    ev_fail "The disk changed since it was selected; select it again"
    return 1
  fi
  reason=$(disk_list | awk -F'|' -v p="$disk" '$1 == p { print $6 }')
  if [[ -n $reason ]]; then
    ev_fail "$disk can't be used: $reason"
    return 1
  fi

  ev_step 3 "Creating the partition table"
  while IFS= read -r cmd; do
    case $cmd in
      partprobe*) ev_step 4 "Creating partitions" ;;
      mkfs.vfat*) ev_step 5 "Formatting the boot partition" ;;
      mkfs.ext4*) ev_step 6 "Formatting the system partition" ;;
    esac
    # shellcheck disable=SC2086 # os argumentos nao tem espacos
    ev_run $cmd || return 1
  done < <(disk_partition_commands "$disk")
  esp=$(disk_partition_path "$disk" 2)
  root=$(disk_partition_path "$disk" 3)
  ev_msg "Partitions created on $disk"

  ev_step 7 "Mounting the new system"
  mkdir -p "$INSTALL_TARGET"
  ev_run mount "$root" "$INSTALL_TARGET" || return 1

  ev_step 8 "Copying system files"
  install_copy_system || { install_unmount; return 1; }
  ev_msg "System files copied"
  mkdir -p "$INSTALL_TARGET/boot/efi"
  ev_run mount "$esp" "$INSTALL_TARGET/boot/efi" || { install_unmount; return 1; }

  ev_step 81 "Configuring the system"
  if ! install_write_fstab "$INSTALL_TARGET" "$root" "$esp"; then
    ev_fail "Could not write /etc/fstab"
    install_unmount
    return 1
  fi

  ev_step 82 "Configuring video"
  if ! install_configure_video "$INSTALL_TARGET"; then
    ev_fail "Could not write the video settings"
    install_unmount
    return 1
  fi
  ev_msg "Video: $(conf_get connector 2> /dev/null || echo "boot menu settings"), monitor $(conf_get monitor 2> /dev/null || echo default)"

  ev_step 83 "Configuring the user and the launcher"
  if ! install_configure_user "$INSTALL_TARGET"; then
    ev_fail "Could not configure the user"
    install_unmount
    return 1
  fi

  ev_step 84 "Generating the initramfs"
  if ! install_bind_mounts "$INSTALL_TARGET"; then
    ev_fail "Could not prepare the chroot"
    install_unmount
    return 1
  fi
  ev_run chroot "$INSTALL_TARGET" ssh-keygen -A || { install_unmount; return 1; }
  ev_run chroot "$INSTALL_TARGET" update-initramfs -u -k all || { install_unmount; return 1; }

  ev_step 94 "Installing the bootloader"
  if ! install_bootloader "$INSTALL_TARGET" "$disk"; then
    ev_fail "Limine could not be installed on $disk"
    install_unmount
    return 1
  fi
  ev_msg "Limine installed (BIOS and UEFI)"

  ev_step 98 "Finishing"
  sync
  install_unmount
  if mountpoint -q "$INSTALL_TARGET" 2> /dev/null; then
    ev_fail "Could not unmount $INSTALL_TARGET; keep the PC on and check the log"
    return 1
  fi
  exec {lockfd}>&-
  ev_step 100 "Installation complete"
  return 0
}
