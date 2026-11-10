# shellcheck shell=bash
# RetroAchievements (menu principal > RetroAchievements e o painel web): o
# login na conta do site, as conquistas ligadas ou nao e o modo hardcore,
# para todos os emuladores que tem conquistas (RetroArch, DuckStation, PCSX2,
# Dolphin, Flycast).
#
# O login troca usuario e senha pelo token da conta (a API do site, a mesma
# do rcheevos dos emuladores); so o token fica guardado, em
# /etc/fliperos/cheevos (do root, lido pelo grupo do usuario):
#   enabled=1  user=NOME  token=TOKEN  hardcore=0|1  time=EPOCH
# O RetroArch le /etc/fliperos/retroarch/cheevos.cfg, que nasce daqui (o
# fliperos-kms-run o poe no --appendconfig); os outros recebem a conta no ini
# de cada um a cada abertura (config/fliperos-cheevos, pelo fliperos-x11-run),
# e ja agora nos que ja existem.

CHEEVOS_FILE=${CHEEVOS_FILE:-$FLIPEROS_ETC/cheevos}
CHEEVOS_RA_CFG=${CHEEVOS_RA_CFG:-$FLIPEROS_ETC/retroarch/cheevos.cfg}
CHEEVOS_API=${CHEEVOS_API:-https://retroachievements.org/dorequest.php}
CHEEVOS_TOOL=${CHEEVOS_TOOL:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-cheevos}
CHEEVOS_HOME=${CHEEVOS_HOME:-/home/$FLIPEROS_USER}
# A pagina de cadastro do site (Create an account, no Setup e no painel).
CHEEVOS_SIGNUP_URL=https://retroachievements.org/createaccount.php
# O navegador do gabinete (config/fliperos-browser) abre o endereco deste
# arquivo; com o pedido em CHEEVOS_BROWSER_PENDING, o Setup volta na tela do
# RetroAchievements quando ele fecha.
BROWSER_URL_FILE=${BROWSER_URL_FILE:-/run/fliperos/browser-url}
CHEEVOS_BROWSER_PENDING=${CHEEVOS_BROWSER_PENDING:-/run/fliperos/cheevos-browser}

# cheevos_get CHAVE: o valor guardado (vazio sem ele).
cheevos_get() {
  sed -n "s/^$1=//p" "$CHEEVOS_FILE" 2> /dev/null | head -1
}

# cheevos_logged_in: ha uma conta (usuario e token)?
cheevos_logged_in() {
  [[ -n $(cheevos_get user) && -n $(cheevos_get token) ]]
}

# cheevos_on: conta feita e conquistas ligadas.
cheevos_on() {
  cheevos_logged_in && [[ $(cheevos_get enabled) == 1 ]]
}

# cheevos_label: uma linha para o menu.
cheevos_label() {
  if ! cheevos_logged_in; then
    echo "not signed in"
  elif cheevos_on; then
    echo "$(cheevos_get user)$([[ $(cheevos_get hardcore) == 1 ]] && echo ", hardcore")"
  else
    echo "$(cheevos_get user), off"
  fi
}

# cheevos_save USER TOKEN ENABLED HARDCORE grava o arquivo (0640, grupo do
# usuario: os emuladores o leem) e passa a conta aos emuladores.
cheevos_save() {
  local tmp group
  mkdir -p "$(dirname "$CHEEVOS_FILE")"
  tmp=$(umask 077 && mktemp "$CHEEVOS_FILE.XXXXXX") || return 1
  printf 'enabled=%s\nuser=%s\ntoken=%s\nhardcore=%s\ntime=%s\n' "$3" "$1" "$2" "$4" "$(date +%s)" > "$tmp"
  group=$(id -gn "$FLIPEROS_USER" 2> /dev/null) && chgrp "$group" "$tmp" 2> /dev/null
  chmod 640 "$tmp"
  mv -f "$tmp" "$CHEEVOS_FILE"
  log_info "RetroAchievements: ${1:-sem conta}, enabled=$3 hardcore=$4"
  cheevos_apply
}

# cheevos_apply: o cheevos.cfg do RetroArch e os inis que ja existem.
cheevos_apply() {
  local user token on=false hard=false tmp group format file
  user=$(cheevos_get user)
  token=$(cheevos_get token)
  cheevos_on && on=true
  [[ $on == true && $(cheevos_get hardcore) == 1 ]] && hard=true
  mkdir -p "$(dirname "$CHEEVOS_RA_CFG")"
  tmp=$(umask 077 && mktemp "$CHEEVOS_RA_CFG.XXXXXX") || return 1
  {
    echo "# Menu principal > RetroAchievements (lib/cheevos.sh): por cima do retroarch.cfg."
    printf 'cheevos_enable = "%s"\ncheevos_hardcore_mode_enable = "%s"\n' "$on" "$hard"
    printf 'cheevos_username = "%s"\ncheevos_token = "%s"\ncheevos_password = ""\n' "$user" "$token"
  } > "$tmp"
  group=$(id -gn "$FLIPEROS_USER" 2> /dev/null) && chgrp "$group" "$tmp" 2> /dev/null
  chmod 640 "$tmp"
  mv -f "$tmp" "$CHEEVOS_RA_CFG"
  [[ -x $CHEEVOS_TOOL ]] || return 0
  while read -r format file; do
    file=$CHEEVOS_HOME/$file
    [[ -f $file ]] || continue
    if [[ $EUID -eq 0 ]] && id "$FLIPEROS_USER" > /dev/null 2>&1; then
      runuser -u "$FLIPEROS_USER" -- "$CHEEVOS_TOOL" "$format" "$file" 2>> "$FLIPEROS_LOG" || true
    else
      "$CHEEVOS_TOOL" "$format" "$file" 2>> "$FLIPEROS_LOG" || true
    fi
  done << 'LIST'
duckstation .local/share/duckstation/settings.ini
pcsx2 .config/PCSX2/inis/PCSX2.ini
pcsx2 .config/PCSX2x6/inis/PCSX2.ini
dolphin .config/dolphin-emu/RetroAchievements.ini
flycast .config/flycast/emu.cfg
LIST
  return 0
}

# cheevos_login USUARIO (a senha pela entrada padrao: nem na linha de
# comando, nem no log). Status 0 e a conta guardada; 1 com o motivo na
# saida (senha errada, sem rede).
cheevos_login() {
  local user=$1 pass reply ok token name error
  IFS= read -r pass || true
  user=${user//[[:space:]]/}
  if [[ -z $user || -z $pass ]]; then
    echo "The user and the password are both needed."
    return 1
  fi
  # A senha vai para o curl pela entrada padrao (p@-), tambem fora da lista
  # de processos.
  reply=$(printf '%s' "$pass" | curl -sS --max-time 20 -A "FliperOS/1.0 (rcheevos login)" \
    --data-urlencode "r=login2" --data-urlencode "u=$user" --data-urlencode "p@-" "$CHEEVOS_API" 2>&1) || {
    log_warn "RetroAchievements: login sem resposta: $reply"
    echo "No answer from retroachievements.org (no network?)."
    return 1
  }
  ok=$(jq -r '.Success // false' <<< "$reply" 2> /dev/null)
  token=$(jq -r '.Token // empty' <<< "$reply" 2> /dev/null)
  name=$(jq -r '.User // empty' <<< "$reply" 2> /dev/null)
  if [[ $ok != true || -z $token ]]; then
    error=$(jq -r '.Error // empty' <<< "$reply" 2> /dev/null)
    log_warn "RetroAchievements: login recusado para $user: ${error:-resposta estranha}"
    echo "${error:-retroachievements.org gave an unexpected answer.}"
    return 1
  fi
  [[ $token =~ ^[A-Za-z0-9]+$ ]] || { echo "retroachievements.org gave an unexpected answer."; return 1; }
  [[ $name =~ ^[A-Za-z0-9_.-]+$ ]] || name=$user
  cheevos_save "$name" "$token" 1 "$(cheevos_get hardcore)"
}

# cheevos_logout: sai da conta (os emuladores perdem o usuario e o token).
cheevos_logout() {
  cheevos_save "" "" 0 "$(cheevos_get hardcore)"
}

# cheevos_cli status|login USUARIO|logout|enable on|off|hardcore on|off: o
# painel web. Status 2: pedido errado.
cheevos_cli() {
  local hard
  case ${1:-} in
    status)
      printf 'user=%s\nenabled=%s\nhardcore=%s\n' "$(cheevos_get user)" "$(cheevos_on && echo 1 || echo 0)" \
        "$([[ $(cheevos_get hardcore) == 1 ]] && echo 1 || echo 0)"
      ;;
    login)
      [[ -n ${2:-} ]] || return 2
      cheevos_login "$2"
      ;;
    logout) cheevos_logout ;;
    enable)
      [[ ${2:-} == on || ${2:-} == off ]] || return 2
      cheevos_logged_in || { echo "Sign in first."; return 1; }
      cheevos_save "$(cheevos_get user)" "$(cheevos_get token)" "$([[ $2 == on ]] && echo 1 || echo 0)" \
        "$(cheevos_get hardcore)"
      ;;
    hardcore)
      [[ ${2:-} == on || ${2:-} == off ]] || return 2
      hard=0
      [[ $2 == on ]] && hard=1
      cheevos_save "$(cheevos_get user)" "$(cheevos_get token)" "$(cheevos_get enabled)" "$hard"
      ;;
    *) return 2 ;;
  esac
}
