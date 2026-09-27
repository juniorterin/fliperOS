#!/usr/bin/env bash
# ============================================================
#  FliperOS — monta o repositorio APT a partir dos .deb gerados
#
#  Uso: bash packaging/make-repo.sh [--packages DIR] [--output DIR]
#                                   [--sign KEYID]
#
#  Gera um repositorio PLANO (flat), sem pool/ nem dists/, porque e o unico
#  formato que funciona tanto em GitHub Pages quanto em GitHub Releases — nos
#  Releases todos os arquivos ficam no mesmo nivel de URL, sem subdiretorio.
#
#  O cliente aponta para ele com:
#    deb [trusted=yes] https://HOST/CAMINHO/ ./
#  Com --sign, a assinatura permite dispensar o trusted=yes.
# ============================================================
set -euo pipefail

GRN='\033[0;32m'; YLW='\033[1;33m'; RED='\033[0;31m'
CYN='\033[0;36m'; DIM='\033[2m'; BLD='\033[1m'; RST='\033[0m'
ok()   { echo -e "${GRN}✓${RST} $*"; }
warn() { echo -e "${YLW}⚠${RST} $*"; }
err()  { echo -e "${RED}✗${RST} $*" >&2; exit 1; }
step() { echo -e "\n${BLD}${CYN}══ $* ══${RST}"; }

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
PACKAGES="$ROOT/output/packages"
OUTPUT="$ROOT/output/repo"
SIGN_KEY=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --packages) [[ $# -ge 2 ]] || err "--packages requer diretorio"; PACKAGES="$2"; shift 2 ;;
    --output)   [[ $# -ge 2 ]] || err "--output requer diretorio"; OUTPUT="$2"; shift 2 ;;
    --sign)     [[ $# -ge 2 ]] || err "--sign requer key id"; SIGN_KEY="$2"; shift 2 ;;
    *)          err "Opcao desconhecida: $1" ;;
  esac
done

command -v dpkg-scanpackages >/dev/null || err "dpkg-scanpackages ausente (pacote dpkg-dev)"
command -v apt-ftparchive   >/dev/null || err "apt-ftparchive ausente (pacote apt-utils)"
[[ -d "$PACKAGES" ]] || err "Diretorio de pacotes nao existe: $PACKAGES"

shopt -s nullglob
debs=("$PACKAGES"/*.deb)
[[ ${#debs[@]} -gt 0 ]] || err "Nenhum .deb em $PACKAGES — rode packaging/build-deb.sh primeiro"

step "Montando repositorio plano com ${#debs[@]} pacote(s)"
rm -rf "$OUTPUT"
mkdir -p "$OUTPUT"
for deb in "${debs[@]}"; do
  cp "$deb" "$OUTPUT/"
done

cd "$OUTPUT"
dpkg-scanpackages --multiversion . > Packages 2>/dev/null
gzip -9c Packages > Packages.gz
ok "Packages: $(grep -c '^Package:' Packages) entrada(s)"

# apt-ftparchive calcula os hashes de Packages/Packages.gz no Release; sem
# isso o apt recusa o repositorio.
apt-ftparchive -o APT::FTPArchive::Release::Origin=FliperOS \
               -o APT::FTPArchive::Release::Label=FliperOS \
               -o APT::FTPArchive::Release::Architectures=amd64 \
               release . > Release
ok "Release gerado"

if [[ -n "$SIGN_KEY" ]]; then
  command -v gpg >/dev/null || err "gpg ausente, necessario para --sign"
  gpg --default-key "$SIGN_KEY" --clearsign -o InRelease Release
  gpg --default-key "$SIGN_KEY" -abs -o Release.gpg Release
  ok "Assinado com $SIGN_KEY (InRelease e Release.gpg)"
else
  warn "Repositorio NAO assinado — o cliente precisa de [trusted=yes]"
fi

echo
ok "Repositorio em $OUTPUT"
echo -e "${DIM}Publique o conteudo e aponte o cliente para a URL base, com './' no fim da linha deb.${RST}"
