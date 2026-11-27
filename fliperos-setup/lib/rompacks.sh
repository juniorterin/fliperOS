# shellcheck shell=bash
# Setup > Games > Game Packages > ROMs e Create package > ROMs: os pacotes de
# ROM do FliperOS (config/fliperos-rompack). TITULO.fliperos-EMULADOR.zip leva
# as ROMs dos jogos escolhidos de um emulador ou core e o que vai com elas
# (BIOS e sets pais, arte, nvram, saves, cheats, ajustes por jogo); instalar o
# poe de volta nos mesmos lugares da home. Moram na mesma pasta dos pacotes de
# jogo de PC (CUSTOM_GAMES_PACKAGES, lib/customgames.sh).

ROMPACK_CMD=${ROMPACK_CMD:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-rompack}
# O nome de cada tipo de arte (as pastas de ~/media) nas telas.
declare -A ROMPACK_MEDIA_LABELS=([snap]="Pictures" [preview]="Videos" [logo]="Logos" [box]="Boxes and flyers"
  [marquee]="Marquees" [dmd]="LED marquee (DMD) art" [texto]="Texts" [icon]="Icons")

# rompack_kinds ALVO: o que pode ir junto das ROMs, "chave|rotulo" na ordem da
# tela: as BIOS, cada tipo de arte que os jogos do alvo tem (media:snap...), a
# memoria, os saves, os cheats e os ajustes.
rompack_kinds() {
  local m
  printf '%s\n' "bios|BIOS and parent sets the games need"
  while IFS= read -r m; do
    [[ -n $m ]] && printf 'media:%s|%s (~/media/%s)\n' "$m" "${ROMPACK_MEDIA_LABELS[$m]:-$m}" "$m"
  done < <(rompack_tool games "$1" --media-types 2>> "${FLIPEROS_LOG:-/dev/null}")
  printf '%s\n' "nvram|Memory (NVRAM): settings, scores, unlocks" "save|Saves and save states" "cheats|Cheats" \
    "config|Game settings and button remaps"
}

rompack_tool() {
  # O grupo de um pacote vai aos frontends pela tela (screen_custom_games_refresh).
  FLIPEROS_ROMPACK_NO_REFRESH=1 python3 "$ROMPACK_CMD" --packages "$CUSTOM_GAMES_PACKAGES" "$@"
}

# rompack_is_package ARQUIVO: o nome e de um pacote de ROM (e nao de um jogo
# de PC)?
rompack_is_package() {
  local name=${1##*/}
  name=${name,,}
  [[ $name =~ \.fliperos-[a-z0-9][a-z0-9-]*\.zip$ && $name != *.fliperos-customgame.zip ]]
}

# rompack_packages: "ZIP|TITULO|EMULADOR|JOGOS|ESTADO|BYTES|MOTIVO" de cada
# pacote de ROM da pasta (ESTADO: new, partial, installed ou bad).
rompack_packages() {
  rompack_tool packages --text 2>> "${FLIPEROS_LOG:-/dev/null}"
}

# rompack_targets: "ID|NOME|JOGOS" dos emuladores e cores com jogos.
rompack_targets() {
  rompack_tool targets --text 2>> "${FLIPEROS_LOG:-/dev/null}"
}

# rompack_games ALVO: "NOME|BYTES" dos jogos do alvo.
rompack_games() {
  rompack_tool games "$1" --text 2>> "${FLIPEROS_LOG:-/dev/null}"
}

# rompack_install ZIP [replace]: com os eventos da tela de progresso.
rompack_install() {
  local -a opts=()
  [[ ${2:-} == replace ]] && opts+=(--replace)
  log_line cmd "\$ fliperos-rompack install $1 ${opts[*]}"
  rompack_tool install "$1" "${opts[@]}" --progress 0 100 2>> "${FLIPEROS_LOG:-/dev/null}"
}

# rompack_create ALVO TITULO TIPOS LISTA [replace|""] [GRUPO [LOGO]]: o pacote
# (LISTA: um arquivo com um jogo por linha; TIPOS: separados por virgula). Com
# GRUPO, o grupo proprio (um sistema nos frontends), com o LOGO da lista do
# fliperos-syslogo. Status 3: ele ja existe (sem replace).
rompack_create() {
  local -a opts=(--target "$1" --title "$2" --kinds "$3" --games-file "$4")
  [[ ${5:-} == replace ]] && opts+=(--replace)
  [[ -n ${6:-} ]] && opts+=(--group "$6")
  [[ -n ${7:-} ]] && opts+=(--logo-system "$7")
  log_line cmd "\$ fliperos-rompack create ${opts[*]}"
  rompack_tool create "${opts[@]}" --progress 0 100 2>> "${FLIPEROS_LOG:-/dev/null}"
}
