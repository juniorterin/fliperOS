#!/usr/bin/env bash
# Shared assets used by setup, new ISO builds and audited ISO repacks.
set -euo pipefail
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
root=${1:-/}
profile=${2:-15khz}
[[ -d "$root/etc" ]] || { echo "Rootfs invalido: $root" >&2; exit 2; }

# Nome instalado (crt15.bin) fica fixo pros tres perfis de proposito —
# fliperos-install.py, config/grub.cfg, config/fliperos-edid-hook e as
# ferramentas de auditoria em tools/ todos referenciam esse nome fixo e
# nao precisam saber qual perfil de frequencia foi escolhido no build; so
# o CONTEUDO do arquivo muda (ver README, secao de perfis de monitor).
case "$profile" in
  15khz) EDID_SRC="crt15-edid.bin"; XORG_SRC="config/xorg.conf"
         MAME_SRC="config/mame.ini"; SR_SRC="config/switchres.ini"
         MIN_KHZ=15.0; MAX_KHZ=16.0 ;;
  25khz) EDID_SRC="crt25-edid.bin"; XORG_SRC="config/xorg-25khz.conf"
         MAME_SRC="config/mame-25khz.ini"; SR_SRC="config/switchres-25khz.ini"
         MIN_KHZ=24.5; MAX_KHZ=25.5 ;;
  31khz) EDID_SRC="crt31-edid.bin"; XORG_SRC="config/xorg-31khz.conf"
         MAME_SRC="config/mame-31khz.ini"; SR_SRC="config/switchres-31khz.ini"
         MIN_KHZ=31.0; MAX_KHZ=32.0 ;;
  *) echo "Perfil de monitor invalido: $profile (15khz, 25khz ou 31khz)" >&2; exit 2 ;;
esac

install -Dm644 "$src/$EDID_SRC" "$root/lib/firmware/edid/crt15.bin"
install -Dm755 "$src/fliperos-video-check.py" "$root/usr/local/bin/fliperos-video-check"
install -Dm755 "$src/fliperos-video-autodetect.py" "$root/usr/local/bin/fliperos-video-autodetect"
install -Dm755 "$src/fliperos-install.py" "$root/usr/local/bin/fliperos-install"
install -Dm755 "$src/fliperos-config.py" "$root/usr/local/bin/fliperos-config"
# Wrappers de whiptail compartilhados pelo setup e pelo instalador. Ficam numa
# lib porque duplicar primitivas de interface nos dois scripts divergiria; os
# scripts procuram aqui e tambem ao lado deles (que e o caso no repositorio).
install -Dm644 "$src/fliperos_tui.py" "$root/usr/local/lib/fliperos/fliperos_tui.py"

# Light gun e volantes. A calibracao do GunCon 2 se perde a cada reconexao do
# USB, entao a regra de udev a reaplica chamando este script.
install -Dm755 "$src/config/fliperos-guncon2-calibrate" \
  "$root/usr/local/bin/fliperos-guncon2-calibrate"
install -Dm644 "$src/config/99-fliperos-input.rules" \
  "$root/etc/udev/rules.d/99-fliperos-input.rules"
if [[ ! -f "$root/etc/fliperos/guncon2.conf" ]]; then
    cat > "$root/etc/fliperos/guncon2.conf" <<'EOF'
# Faixa util do GunCon 2 neste monitor. Os valores abaixo sao o exemplo do
# upstream e NAO servem pra todo tubo — calibre no seu e ajuste aqui.
X_MIN=175
X_MAX=720
Y_MIN=20
Y_MAX=240
EOF
fi

# Sessao de boot: qual launcher abre ao ligar e um dado de configuracao, nao
# uma linha fixa no .bash_profile (ver config/fliperos-sessions.conf).
install -Dm644 "$src/config/fliperos-sessions.conf" "$root/etc/fliperos/sessions.conf"
install -Dm755 "$src/config/fliperos-session" "$root/opt/fliperos/bin/fliperos-session"
if [[ ! -f "$root/etc/fliperos/session" ]]; then
    printf 'launcher\n' > "$root/etc/fliperos/session"
fi

# Splash grafico. O tema nao usa imagem: no modo do CRT (640x240) arte feita
# pra 1080p fica ilegivel, entao e texto renderizado pelo plugin label.
install -Dm644 "$src/config/plymouth/fliperos.plymouth" \
  "$root/usr/share/plymouth/themes/fliperos/fliperos.plymouth"
install -Dm644 "$src/config/plymouth/fliperos.script" \
  "$root/usr/share/plymouth/themes/fliperos/fliperos.script"

# Os TRES perfis vao pra imagem, nao so o escolhido no build: fliperos-config
# troca de perfil no sistema instalado (regravando o EDID e o initramfs), o que
# tira a escolha de frequencia do momento do build. O perfil ativo fica aqui.
printf '%s\n' "$profile" > "$root/etc/fliperos/profile"
install -Dm644 "$src/crt15-edid.bin"        "$root/etc/fliperos/profiles/15khz/edid.bin"
install -Dm644 "$src/config/switchres.ini"  "$root/etc/fliperos/profiles/15khz/switchres.ini"
install -Dm644 "$src/config/xorg.conf"      "$root/etc/fliperos/profiles/15khz/xorg.conf"
install -Dm644 "$src/config/mame.ini"       "$root/etc/fliperos/profiles/15khz/mame.ini"
install -Dm644 "$src/crt25-edid.bin"             "$root/etc/fliperos/profiles/25khz/edid.bin"
install -Dm644 "$src/config/switchres-25khz.ini" "$root/etc/fliperos/profiles/25khz/switchres.ini"
install -Dm644 "$src/config/xorg-25khz.conf"     "$root/etc/fliperos/profiles/25khz/xorg.conf"
install -Dm644 "$src/config/mame-25khz.ini"      "$root/etc/fliperos/profiles/25khz/mame.ini"
install -Dm644 "$src/crt31-edid.bin"             "$root/etc/fliperos/profiles/31khz/edid.bin"
install -Dm644 "$src/config/switchres-31khz.ini" "$root/etc/fliperos/profiles/31khz/switchres.ini"
install -Dm644 "$src/config/xorg-31khz.conf"     "$root/etc/fliperos/profiles/31khz/xorg.conf"
install -Dm644 "$src/config/mame-31khz.ini"      "$root/etc/fliperos/profiles/31khz/mame.ini"
install -Dm755 "$src/config/fliperos-edid-hook" "$root/etc/initramfs-tools/hooks/fliperos-edid"
install -Dm644 "$src/$SR_SRC" "$root/etc/fliperos/switchres.ini"
install -Dm644 "$src/$SR_SRC" "$root/etc/switchres.ini"
install -Dm644 "$src/$XORG_SRC" "$root/etc/fliperos/xorg.conf"
if [[ ! -f "$root/etc/fliperos/connector" ]]; then
    printf 'VGA-1\n' > "$root/etc/fliperos/connector"
fi
for name in fliperos-x11-run fliperos-kms-run fliperos-x11-client fliperos-launcher; do
    install -Dm755 "$src/config/$name" "$root/opt/fliperos/bin/$name"
done
mkdir -p "$root/usr/local/bin"
ln -sf /opt/fliperos/bin/fliperos-launcher "$root/usr/local/bin/fliperos-launcher"
install -Dm644 "$src/$MAME_SRC" "$root/etc/fliperos/mame/mame.ini"
install -Dm644 "$src/config/retroarch.cfg" "$root/etc/fliperos/retroarch/retroarch.cfg"
install -Dm644 "$src/config/fliperos-video-check.service" "$root/etc/systemd/system/fliperos-video-check.service"
sed -i "s|--connector VGA-1 --wait 15|--connector VGA-1 --wait 15 --min-khz $MIN_KHZ --max-khz $MAX_KHZ|" \
  "$root/etc/systemd/system/fliperos-video-check.service"
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
    # A midia abre no MENU DE SETUP, nao no instalador: numa maquina sem cabo
    # de rede o Wi-Fi tem de ser configurado antes, e o instalador e um item
    # dentro do menu. No disco, abre a sessao escolhida e, ao sair dela, o
    # mesmo menu (o gasetup faz assim no .bash_profile: frontend -> setup).
    cat > "$root/home/fliperos/.bash_profile" <<'EOF'
if [[ -z "${DISPLAY:-}" && "$(tty)" == /dev/tty1 ]]; then
    if [[ ! -f /etc/fliperos/installed ]]; then
        sudo /usr/local/bin/fliperos-config
    else
        /opt/fliperos/bin/fliperos-session
        sudo /usr/local/bin/fliperos-config
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
    if [ ! -f /etc/fliperos/installed ]; then
        echo "FliperOS: sudo fliperos-config (Wi-Fi, video e instalar em disco)"
    else
        echo "Configuracao: sudo fliperos-config (sessao, video, rede, compartilhamento)"
    fi
    echo "Diagnostico: sudo fliperos-video-check"
fi
EOF
