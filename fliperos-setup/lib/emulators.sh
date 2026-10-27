# shellcheck shell=bash
# Setup > Games > Emulators & Games: os emuladores do menu do desktop, quais estao
# instalados, e a instalacao dos que nao vem na imagem (o Model 2, compilado
# na maquina; o Fightcade 2, baixado do site dele; o KOF Final Attack no
# Ikemen GO, baixado do itch.io ou da pasta que a pessoa traz). O
# config/fliperos-emulators
# os instala, escrevendo os eventos da tela de progresso (lib/progress.sh).

EMULATORS_CMD=${EMULATORS_CMD:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-emulators}
KOF_CMD=${KOF_CMD:-/usr/local/bin/fliperos-kof}

# emulators_list imprime "nome|instalado (0 ou 1)|tipo|descricao" (tipo:
# image, build, fetch ou source).
emulators_list() {
  [[ -x $EMULATORS_CMD ]] || return 1
  "$EMULATORS_CMD" list
}

# emulators_field NOME CAMPO: um campo da linha do emulador.
emulators_field() {
  emulators_list | awk -F'|' -v n="$1" -v f="$2" '$1 == n { print $f; exit }'
}

# emulators_kof_find PASTA imprime a pasta do KOF Final Attack original (a
# que tem o "Final Attack.exe") achada em PASTA ou dentro dela.
emulators_kof_find() {
  [[ -x $KOF_CMD ]] && "$KOF_CMD" find "$1"
}

# emulators_install NOME [PASTA]: PASTA e a do jogo original (tipo source;
# sem ela, o jogo e baixado).
emulators_install() {
  local args=()
  ev_step 0 "Starting"
  if [[ ! -x $EMULATORS_CMD ]]; then
    ev_fail "the installer of the emulators ($EMULATORS_CMD) is missing"
    return 1
  fi
  [[ -z ${2:-} ]] || args=(--source "$2")
  log_line cmd "\$ $EMULATORS_CMD install $1 --progress ${args[*]}"
  "$EMULATORS_CMD" install "$1" --progress "${args[@]}" 2>> "$FLIPEROS_LOG"
}

# emulators_versions imprime "nome|versao instalada" (vazia: nao instalado
# ou sem como saber). Le arquivos, nao abre os emuladores.
emulators_versions() {
  [[ -x $EMULATORS_CMD ]] || return 1
  "$EMULATORS_CMD" versions
}

# emulators_latest NOME imprime "instalada|a do update|estado" (same, new ou
# unknown, este sem rede). Pergunta ao GitHub: alguns segundos.
emulators_latest() {
  [[ -x $EMULATORS_CMD ]] || return 1
  "$EMULATORS_CMD" latest "$1"
}

# ── O Vulkan pelo driver de video ────────────────────────────────
# Com o amdgpu (Setup > Video Setup > Video driver) os emuladores que tem
# Vulkan passam a usa-lo; com o radeon, que nao tem Vulkan, cada um volta ao
# renderizador de fabrica. Vale o driver que a placa usa de fato:
# emulators_vulkan_sync roda a cada sessao (--session-start) e so mexe
# quando ele muda (a troca, a volta do teste da troca, a instalacao).
# O Flycast vai do OpenGL ao Vulkan equivalente (pvr.rend 0 e 3, 4 e 5) e o
# Dolphin ao Vulkan; o PCSX2 e o DuckStation ficam no automatico, que ja
# escolhe o Vulkan onde ha. O RetroArch segue no glcore: o Vulkan dele
# (khr_display) nao troca o modo do CRT.
EMULATORS_HOME=${EMULATORS_HOME:-/home/$FLIPEROS_USER}
EMULATORS_INI_SET=${EMULATORS_INI_SET:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-ini-set}

# emulators_ini ARQUIVO SECAO CHAVE VALOR: a chave no ini do emulador, que
# continua do usuario (o ini-set grava um arquivo novo, de quem roda). Sem a
# pasta do emulador (nunca aberto, nao instalado), nada.
emulators_ini() {
  [[ -d ${1%/*} ]] || return 0
  bash "$EMULATORS_INI_SET" "$@" 2>> "$FLIPEROS_LOG" || return 1
  chown --reference="${1%/*}" "$1" 2> /dev/null
  return 0
}

# emulators_ini_get ARQUIVO CHAVE: o valor de "CHAVE = valor" (vazio sem ele).
emulators_ini_get() {
  sed -n "s/^$2 *= *//p" "$1" 2> /dev/null | head -1 | tr -d '\r'
}

# emulators_vulkan DRIVER (amdgpu ou radeon) acerta o renderizador de cada
# emulador.
emulators_vulkan() {
  local driver=$1 home=$EMULATORS_HOME file value
  [[ $driver == amdgpu || $driver == radeon ]] || return 0
  file=$home/.config/flycast/emu.cfg
  value=$(emulators_ini_get "$file" 'pvr\.rend')
  case $driver:$value in
    amdgpu:0) emulators_ini "$file" config pvr.rend 4 ;;
    amdgpu:3 | amdgpu:) emulators_ini "$file" config pvr.rend 5 ;;
    radeon:4) emulators_ini "$file" config pvr.rend 0 ;;
    radeon:5) emulators_ini "$file" config pvr.rend 3 ;;
  esac
  file=$home/.config/dolphin-emu/Dolphin.ini
  value=$(emulators_ini_get "$file" GFXBackend)
  if [[ $driver == amdgpu ]]; then
    [[ $value == Vulkan ]] || emulators_ini "$file" Core GFXBackend Vulkan
  elif [[ $value == Vulkan ]]; then
    emulators_ini "$file" Core GFXBackend OGL
  fi
  # PCSX2: -1 o automatico, 12 OpenGL, 14 Vulkan.
  file=$home/.config/PCSX2/inis/PCSX2.ini
  value=$(emulators_ini_get "$file" Renderer)
  if [[ -f $file ]] && [[ $driver:$value == amdgpu:12 || $driver:$value == radeon:14 ]]; then
    emulators_ini "$file" EmuCore/GS Renderer -1
  fi
  file=$home/.local/share/duckstation/settings.ini
  value=$(emulators_ini_get "$file" Renderer)
  if [[ -f $file ]] && [[ $driver:$value == amdgpu:OpenGL || $driver:$value == radeon:Vulkan ]]; then
    emulators_ini "$file" GPU Renderer Automatic
  fi
  log_info "emuladores no driver $driver: $([[ $driver == amdgpu ]] && echo Vulkan || echo o renderizador de fabrica)"
}

# emulators_vulkan_sync: o driver da placa AMD mudou desde a ultima vez
# (emulators_driver no fliperos.conf)? Os emuladores o acompanham.
emulators_vulkan_sync() {
  local card driver=""
  for card in "$DRM_SYSFS"/card[0-9]*; do
    [[ ${card##*/} == *-* ]] && continue
    case $(drm_card_driver "${card##*/}") in
      amdgpu | radeon) driver=$(drm_card_driver "${card##*/}") ;;
      *) continue ;;
    esac
    break
  done
  [[ -n $driver ]] || return 0
  [[ $(conf_get emulators_driver 2> /dev/null) == "$driver" ]] && return 0
  emulators_vulkan "$driver"
  conf_set emulators_driver "$driver"
}
