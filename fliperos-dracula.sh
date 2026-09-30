#!/usr/bin/env bash
# Tema Dracula (https://draculatheme.com) do desktop e do terminal numa raiz:
#
#   fliperos-dracula.sh RAIZ
#
# - GTK 2 e 3: o tema oficial dracula/gtk (o GTK 2 usa as engines murrine e
#   pixmap, que o fliperos-mkiso.sh instala);
# - Openbox: o dracula/gtk nao tem tema de Openbox; o de config/openbox-3 usa
#   a mesma paleta;
# - terminal: Oh My Zsh com o tema oficial dracula/zsh, em
#   /usr/local/share/oh-my-zsh (o ~/.zshrc do usuario e o config/zshrc).
# Tudo fixado por commit. O LXDE escolhe o tema em config/lxde (lxsession e
# lxde-rc.xml).
set -euo pipefail
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
root=${1:?Uso: fliperos-dracula.sh RAIZ}

DRACULA_GTK_COMMIT="71640b9456110f3bac2130d0b387a3154a9fb4d2"
OHMYZSH_COMMIT="4d4cfc287e9d887b81242c0e431b5f49f9cec5c1"
DRACULA_ZSH_COMMIT="a3e27d47ea2ed1e3b435f44aa71caf71d3219af6"

work=$(mktemp -d /tmp/fliperos-dracula.XXXXXX)
trap 'rm -rf "$work"' EXIT

# fetch REPO COMMIT DESTINO: so os arquivos daquele commit, sem o .git (o
# GitHub entrega um commit pelo hash com --depth 1).
fetch() {
  git init -q "$work/repo"
  git -C "$work/repo" fetch -q --depth 1 "https://github.com/$1" "$2"
  mkdir -p "$3"
  git -C "$work/repo" archive FETCH_HEAD | tar -x -C "$3"
  rm -rf "$work/repo"
}

fetch dracula/gtk "$DRACULA_GTK_COMMIT" "$work/gtk"

theme="$root/usr/share/themes/Dracula"
rm -rf "$theme"
mkdir -p "$theme"
for part in index.theme assets gtk-2.0 gtk-3.0 gtk-3.20 gtk-4.0 metacity-1; do
  cp -r "$work/gtk/$part" "$theme/"
done
install -Dm644 "$src/config/openbox-3/themerc" "$theme/openbox-3/themerc"
install -Dm644 "$work/gtk/LICENSE" "$theme/LICENSE"
find "$theme" -type d -exec chmod 755 {} +
find "$theme" -type f -exec chmod 644 {} +
echo "Dracula GTK ${DRACULA_GTK_COMMIT:0:7} + Openbox em $theme"

# Oh My Zsh para todos, com o tema no custom/themes dele. O tema procura o
# lib/async.zsh ao lado do proprio arquivo.
omz="$root/usr/local/share/oh-my-zsh"
rm -rf "$omz"
fetch ohmyzsh/ohmyzsh "$OHMYZSH_COMMIT" "$omz"
fetch dracula/zsh "$DRACULA_ZSH_COMMIT" "$work/zsh"
install -Dm644 "$work/zsh/dracula.zsh-theme" "$omz/custom/themes/dracula.zsh-theme"
install -Dm644 "$work/zsh/lib/async.zsh" "$omz/custom/themes/lib/async.zsh"
install -Dm644 "$work/zsh/LICENSE" "$omz/custom/themes/dracula.LICENSE"
# Sem escrita para o grupo e os outros: o compaudit do zsh recusa carregar
# completions de pastas assim ("insecure directories").
find "$omz" -type d -exec chmod 755 {} +
find "$omz" -type f -exec chmod go-w {} +
echo "Oh My Zsh ${OHMYZSH_COMMIT:0:7} + Dracula zsh ${DRACULA_ZSH_COMMIT:0:7} em $omz"
