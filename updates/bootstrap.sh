#!/usr/bin/env bash
# Leva os updates automaticos a um FliperOS instalado de uma ISO sem eles
# (0.7 e antes). Roda no gabinete, com rede:
#
#   curl -fsSL https://raw.githubusercontent.com/juniorterin/fliperOS/main/updates/bootstrap.sh | sudo bash
#
# Instala o fliperos-update e aplica, em ordem, todos os updates publicados
# (com a copia dos arquivos que eles trocam). Depois disso o gabinete
# pergunta sozinho, no boot, pelos proximos.
set -euo pipefail
raw=https://raw.githubusercontent.com/juniorterin/fliperOS/main
[[ $EUID -eq 0 ]] || { echo "Run as root: ... | sudo bash" >&2; exit 1; }
[[ -f /etc/fliperos/installed ]] || { echo "This is not an installed FliperOS." >&2; exit 1; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
curl -fsSL -m 60 "$raw/config/fliperos-update" -o "$tmp/fliperos-update"
python3 -m py_compile "$tmp/fliperos-update"
install -Dm755 "$tmp/fliperos-update" /opt/fliperos/bin/fliperos-update
pending=$(/opt/fliperos/bin/fliperos-update check)
if [[ -z $pending ]]; then
  echo "No update to apply (level $(/opt/fliperos/bin/fliperos-update level))."
  exit 0
fi
echo "Updates to apply, in order:"
printf '  %s\n' "$pending"
/opt/fliperos/bin/fliperos-update plan
/opt/fliperos/bin/fliperos-update apply
echo "Done. Restart the cabinet: from now on it asks for updates at boot."
