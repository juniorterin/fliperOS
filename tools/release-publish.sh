#!/usr/bin/env bash
# Publica uma ISO nos Releases do GitHub com o changelog da versao, como os
# releases do GroovyArcade (github.com/substring/os/releases): o texto e a
# secao da versao no CHANGELOG.md, e junto da ISO vai a lista de pacotes.
#
#   bash tools/release-publish.sh ISO                publica (a versao sai do nome: fliperos-0.8.1.iso)
#   bash tools/release-publish.sh --prerelease ISO   idem, marcado como pre-release
#   bash tools/release-publish.sh --replace ISO      troca um release que ja existe (apaga e publica de novo)
#   bash tools/release-publish.sh --to DIR ISO       so prepara os arquivos e o texto em DIR (sem GitHub)
#   bash tools/release-publish.sh --notes VERSAO     so mostra o texto da versao
#
# Antes de publicar, a ISO passa pela auditoria (tools/verify-iso.sh: tem de
# ser a do repositorio de agora) e nao pode levar rede Wi-Fi gravada (a senha
# do --wifi-psk fica em texto na imagem). O GitHub aceita ate 2 GiB por
# arquivo: ISO maior vai em partes (.001, .002...), com a instrucao de juntar
# no texto do release.
#
# No container fliperos-vmtest (tools/Dockerfile.vmtest), com o login do gh
# num volume:
#
#   docker run -it --rm -v fliperos-gh:/root/.config/gh fliperos-vmtest gh auth login     (uma vez)
#   docker run --rm -v "${PWD}:/w:ro" -v fliperos-gh:/root/.config/gh -w /w fliperos-vmtest bash tools/release-publish.sh /w/output/fliperos-0.8.1.iso
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
limit=2147483648 part=1900M
replace=0 to="" iso="" flags=()
die() { echo "release-publish: $*" >&2; exit 1; }
# O repositorio vem montado de fora do container, com outro dono.
g() { git -c safe.directory="$root" -C "$root" "$@"; }

# notes VERSAO: a secao "## VERSAO" do CHANGELOG.md, sem o titulo.
notes() {
  awk -v version="$1" '/^## / { on = ($2 == version); next } on' "$root/CHANGELOG.md" | sed -e '/./,$!d'
}

while (($#)); do
  case $1 in
    --notes)
      text=$(notes "${2:?--notes needs the version}")
      [[ -n $text ]] || die "CHANGELOG.md has no \"## $2\" section"
      printf '%s\n' "$text"
      exit 0 ;;
    --replace) replace=1; shift ;;
    --prerelease) flags+=(--prerelease); shift ;;
    --to) to=${2:?--to needs a folder}; shift 2 ;;
    *) iso=$1; shift ;;
  esac
done
[[ -f $iso ]] || die "Usage: release-publish.sh [--prerelease] [--replace] [--to DIR] path/fliperos-VERSION.iso"
name=${iso##*/}
version=$(sed -n 's/^fliperos-\(.*\)\.iso$/\1/p' <<< "$name")
[[ -n $version ]] || die "the ISO name must be fliperos-VERSION.iso: $name"
body=$(notes "$version")
[[ -n $body ]] || die "CHANGELOG.md has no \"## $version\" section: write what changed before publishing"

repo=$(g remote get-url origin | sed -E 's|^.*github\.com[:/]||; s|\.git$||')

out=${to:-$(mktemp -d /tmp/fliperos-release.XXXXXX)}
audit=$(mktemp -d /tmp/fliperos-release-audit.XXXXXX)
mkdir -p "$out"

# ── A ISO e a do repositorio, e nao leva nada da pessoa ───────
FLIPEROS_VERIFY_DIR=$audit bash "$root/tools/verify-iso.sh" "$iso" \
  || die "the ISO failed the audit: only an ISO built from the current repository is published"
if grep -q 'squashfs-root/etc/NetworkManager/system-connections/.' "$audit/files.txt"; then
  grep 'squashfs-root/etc/NetworkManager/system-connections/.' "$audit/files.txt" >&2
  die "the ISO carries a saved network (--wifi-ssid/--wifi-psk): the password would go public. Build another without it"
fi

# ── Lista de pacotes (o pkglist do GroovyArcade) ──────────────
pkglist=$out/fliperos-$version-pkglist.txt
unsquashfs -cat "$audit/filesystem.squashfs" var/lib/dpkg/status > "$audit/status"
awk '/^Package: / { name = $2 } /^Status: / { ok = /install ok installed/ } /^Architecture: / { arch = $2 }
     /^Version: / { if (ok) print name, $2, arch }' "$audit/status" | sort > "$pkglist"
[[ -s $pkglist ]] || die "empty package list"

# ── A ISO, inteira ou em partes ───────────────────────────────
size=$(stat -c %s "$iso")
if ((size < limit)); then
  assets=("$iso")
else
  split -b "$part" -a 3 --numeric-suffixes=1 "$iso" "$out/$name."
  assets=("$out/$name".[0-9][0-9][0-9])
fi
sums=$out/fliperos-$version.sha256
sha=$(sha256sum "$iso" | cut -d' ' -f1)
echo "$sha  $name" > "$sums"
if ((${#assets[@]} > 1)); then
  (cd "$out" && sha256sum "$name".[0-9][0-9][0-9]) >> "$sums"
fi

{
  printf '%s\n\n**Download:**\n\n' "$body"
  if ((${#assets[@]} > 1)); then
    joined=$(printf ' + %s' "${assets[@]##*/}")
    echo "The ISO is $(numfmt --to=iec-i --suffix=B "$size") and GitHub accepts up to 2 GiB per file, so it comes in ${#assets[@]} parts. Download all of them and join them:"
    echo
    echo "- Windows (Command Prompt): \`copy /b ${joined# + } $name\`"
    echo "- Linux and macOS: \`cat $name.0* > $name\`"
    echo
  fi
  echo "SHA-256 of \`$name\`: \`$sha\` (\`sha256sum -c ${sums##*/}\` checks everything downloaded)."
  echo
  echo "Write the ISO byte for byte and disable Secure Boot: [Install](https://github.com/$repo/wiki/Install)."
} > "$out/notes.md"
assets+=("$sums" "$pkglist")

if [[ -n $to ]]; then
  echo "Release $version prepared in $to (text in notes.md):"
  ls -l "${assets[@]}"
  exit 0
fi

# ── GitHub ────────────────────────────────────────────────────
command -v gh > /dev/null || die "gh (GitHub CLI) is missing"
gh auth status > /dev/null 2>&1 || die "gh is not logged in: gh auth login"
commit=$(g rev-parse HEAD)
gh api "repos/$repo/commits/$commit" > /dev/null 2>&1 \
  || die "commit ${commit:0:7} is not on GitHub: push before publishing"
if gh release view "$version" -R "$repo" > /dev/null 2>&1; then
  ((replace)) || die "release $version already exists: a new ISO needs a new version (FLIPEROS_VERSION), or --replace to replace this one"
  gh release delete "$version" -R "$repo" --yes --cleanup-tag
fi
gh release create "$version" "${assets[@]}" -R "$repo" --target "$commit" \
  --title "FliperOS $version" --notes-file "$out/notes.md" "${flags[@]}"
echo "Release published: https://github.com/$repo/releases/tag/$version"
