# Gum, a interface de texto do Setup, com os patches do FliperOS
# (packaging/patches/gum): as setas da paginacao, os sons do menu, o espaco e
# os baloes de dica do choose. Binario estatico (Go), em /usr/local/bin/gum,
# na frente do /usr/bin/gum do .deb oficial (que fica com as paginas de
# manual e o completion) no PATH, inclusive no do sudo.
#
# Era compilado no build da ISO, por cima do /usr/bin/gum: um gabinete
# atualizado so pela rede ficava com o gum da ISO que instalou (sem os
# baloes, numa ISO de antes deles). Como pacote, ele chega pelos updates
# (updates/packages.list) e a ISO instala o mesmo .deb.

PKG_NAME="fliperos-gum"
GUM_TAG="v2.0.2"
GUM_COMMIT="879f048103adf0214b85943b52d8d65b08d772c5"
# O Go que compila (o da imagem golang da mesma versao).
GO_VERSION="1.26.7"
GO_SHA256="ffb5f8de10c62550dfddab66b36b57030721e0a44a3218e9e1181d7b59f121ca"
PKG_VERSION="2.0.2"
PKG_REVISION="1fliperos1"
PKG_SECTION="utils"
PKG_HOMEPAGE="https://github.com/charmbracelet/gum"
PKG_SUMMARY="Gum with the FliperOS Setup patches"
PKG_DESCRIPTION="Gum, the terminal interface tool the FliperOS Setup is drawn with, with
FliperOS's patches: pagination arrows, menu sounds, the space key and the
hint balloons of choose.

Installed in /usr/local/bin, in front of the official package's /usr/bin/gum."

PKG_BUILD_DEPS="git ca-certificates curl"

# Binario estatico (CGO_ENABLED=0): nada para o dpkg-shlibdeps.
PKG_SHLIB_TARGETS=""

pkg_build() {
  local here patch go=$SRC/go dir=$SRC/gum
  here=$(dirname "${BASH_SOURCE[0]}")
  curl -fsSL --retry 3 --max-time 600 -o "$SRC/go.tgz" "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" &&
    echo "$GO_SHA256  $SRC/go.tgz" | sha256sum -c --quiet - &&
    mkdir -p "$go" && tar xzf "$SRC/go.tgz" -C "$go" --strip-components=1 ||
    return 1
  git clone -q --depth 1 --branch "$GUM_TAG" https://github.com/charmbracelet/gum "$dir" || return 1
  if [[ $(git -C "$dir" rev-parse HEAD) != "$GUM_COMMIT" ]]; then
    echo "tag $GUM_TAG is no longer the pinned commit" >&2
    return 1
  fi
  for patch in "$here"/../patches/gum/*.patch; do
    git -C "$dir" apply "$patch" || return 1
  done
  (cd "$dir" && CGO_ENABLED=0 GOPATH="$SRC/gopath" GOCACHE="$SRC/gocache" \
    "$go/bin/go" build -trimpath -ldflags "-s -w -X main.Version=${GUM_TAG#v}-fliperos" -o "$SRC/gum-bin" .) &&
    install -Dm755 "$SRC/gum-bin" "$STAGING/usr/local/bin/gum" ||
    return 1
  chmod -R u+w "$SRC/gopath" 2> /dev/null || true
}
