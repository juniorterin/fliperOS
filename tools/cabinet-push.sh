#!/bin/sh
# Leva os arquivos deste repositorio para um FliperOS ja instalado, pela
# rede, e roda la o tools/cabinet-update.sh. Roda no container fliperos-ssh
# (ssh + sshpass; o Windows nao passa senha ao ssh):
#
#   docker build -t fliperos-ssh -f tools/Dockerfile.ssh tools
#   docker run --rm -v "${PWD}:/w:ro" -w /w fliperos-ssh sh tools/cabinet-push.sh 192.168.1.111
#
# Usuario e senha sao os padroes da imagem (fliperos/fliperos); outros em
# FLIPEROS_USER e FLIPEROS_PASSWORD. O repositorio de frontends vai junto
# se existir output/repo.
set -eu
host=${1:?Uso: cabinet-push.sh IP}
user=${FLIPEROS_USER:-fliperos}
pass=${FLIPEROS_PASSWORD:-fliperos}
opts="-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/tmp/known_hosts -o LogLevel=ERROR -o ConnectTimeout=10"

bundle=/tmp/fliperos-update.tar
set -- fliperos-setup config fliperos-rootfs.sh fliperos-video-check.py fliperos-limine-update.py tools/cabinet-update.sh
tar cf "$bundle" --exclude=__pycache__ "$@"
# O repositorio de frontends vai como repo/ dentro do pacote.
[ -d output/repo ] && tar rf "$bundle" -C output repo
gzip -f "$bundle"
bundle=$bundle.gz
echo "Pacote: $(du -h "$bundle" | cut -f1)"

# shellcheck disable=SC2086 # opcoes do ssh, uma por palavra
sshpass -p "$pass" scp $opts "$bundle" "$user@$host:/tmp/fliperos-update.tgz"
# shellcheck disable=SC2086
sshpass -p "$pass" ssh $opts "$user@$host" bash -s << EOF
set -e
rm -rf /tmp/fliperos-update
mkdir -p /tmp/fliperos-update
tar xzf /tmp/fliperos-update.tgz -C /tmp/fliperos-update
echo '$pass' | sudo -S -p '' bash /tmp/fliperos-update/tools/cabinet-update.sh
EOF
