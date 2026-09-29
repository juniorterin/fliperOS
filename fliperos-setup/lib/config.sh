# shellcheck shell=bash
# Estado do setup e arquivos de configuracao.
#
# /etc/fliperos/fliperos.conf e o equivalente do ga.conf do GroovyArcade:
# chave=valor com tudo que o setup decidiu (GPU, conector, monitor, modo de
# boot, orientacao, launcher). O instalador copia esse arquivo para o disco.

# conf_get CHAVE [ARQUIVO] imprime o valor (vazio se nao existir).
conf_get() {
  local key=$1 file=${2:-$FLIPEROS_CONF} line
  [[ -f $file ]] || return 1
  while IFS= read -r line || [[ -n $line ]]; do
    [[ $line == "#"* ]] && continue
    if [[ ${line%%=*} == "$key" && $line == *=* ]]; then
      printf '%s\n' "${line#*=}"
      return 0
    fi
  done < "$file"
  return 1
}

# conf_set CHAVE VALOR [ARQUIVO] troca a linha da chave ou acrescenta.
conf_set() {
  local key=$1 value=$2 file=${3:-$FLIPEROS_CONF} line found=0 tmp
  mkdir -p "$(dirname "$file")"
  tmp=$(mktemp "$file.XXXXXX") || return 1
  if [[ -f $file ]]; then
    while IFS= read -r line || [[ -n $line ]]; do
      if [[ $line != "#"* && $line == *=* && ${line%%=*} == "$key" ]]; then
        ((found)) || printf '%s=%s\n' "$key" "$value" >> "$tmp"
        found=1
        continue
      fi
      printf '%s\n' "$line" >> "$tmp"
    done < "$file"
  fi
  ((found)) || printf '%s=%s\n' "$key" "$value" >> "$tmp"
  chmod 644 "$tmp"
  mv -f "$tmp" "$file"
  log_info "conf: $key=$value"
}

conf_unset() {
  local key=$1 file=${2:-$FLIPEROS_CONF} line tmp
  [[ -f $file ]] || return 0
  tmp=$(mktemp "$file.XXXXXX") || return 1
  while IFS= read -r line || [[ -n $line ]]; do
    [[ $line == *=* && ${line%%=*} == "$key" ]] && continue
    printf '%s\n' "$line" >> "$tmp"
  done < "$file"
  chmod 644 "$tmp"
  mv -f "$tmp" "$file"
}

# ini_get ARQUIVO CHAVE le "chave valor" do switchres.ini ou do mame.ini.
ini_get() {
  local file=$1 key=$2
  [[ -f $file ]] || return 1
  awk -v k="$key" '
    { sub(/\r$/, "") }
    $1 == k && NF >= 2 { sub("^[ \t]*" k "[ \t]+", ""); print; found = 1; exit }
    END { exit !found }' "$file"
}

# ini_set ARQUIVO CHAVE VALOR troca o valor mantendo o recuo e o alinhamento
# da linha, como o set_mame_config_value do gasetup; sem a chave, acrescenta.
# O arquivo e reescrito no lugar para manter dono e permissao (o mame.ini e
# do usuario fliperos).
ini_set() {
  local file=$1 key=$2 value=$3 out
  if [[ ! -f $file ]]; then
    mkdir -p "$(dirname "$file")"
    printf '%-25s %s\n' "$key" "$value" > "$file"
    return
  fi
  out=$(awk -v k="$key" -v v="$value" '
    { sub(/\r$/, "") }
    $1 == k && match($0, "^[ \t]*" k "[ \t]+") {
      print substr($0, 1, RLENGTH) v
      found = 1
      next
    }
    { print }
    END { if (!found) printf "%-25s %s\n", k, v }' "$file") || return 1
  printf '%s\n' "$out" > "$file"
  log_info "ini: $file $key=$value"
}

# ── Linha do kernel ──────────────────────────────────────────────
# As funcoes recebem a linha como texto e imprimem a linha nova.

# cmdline_get LINHA CHAVE imprime o valor do primeiro parametro.
cmdline_get() {
  local word
  for word in $1; do
    if [[ $word == "$2" ]]; then
      printf '\n'
      return 0
    fi
    if [[ $word == "$2="* ]]; then
      printf '%s\n' "${word#*=}"
      return 0
    fi
  done
  return 1
}

# cmdline_set LINHA CHAVE [VALOR] troca (ou acrescenta) o parametro.
cmdline_set() {
  local line=$1 key=$2 value=${3-} word param out=() done=0
  param=$key
  [[ -n $value ]] && param="$key=$value"
  for word in $line; do
    if [[ $word == "$key" || $word == "$key="* ]]; then
      ((done)) || out+=("$param")
      done=1
      continue
    fi
    out+=("$word")
  done
  ((done)) || out+=("$param")
  printf '%s\n' "${out[*]}"
}

# cmdline_remove LINHA CHAVE tira todos os parametros com a chave.
cmdline_remove() {
  local word out=()
  for word in $1; do
    [[ $word == "$2" || $word == "$2="* ]] && continue
    out+=("$word")
  done
  printf '%s\n' "${out[*]}"
}

# cmdline_without_video tira todo parametro de modo de video (video= global
# ou por conector, e o EDID forcado): e o ponto de partida para gravar o que
# o teste de saidas decidiu.
cmdline_without_video() {
  local word out=()
  for word in $1; do
    case $word in
      video=* | drm.edid_firmware=* | drm_kms_helper.edid_firmware=*) continue ;;
    esac
    out+=("$word")
  done
  printf '%s\n' "${out[*]}"
}

# cmdline_video_params LINHA imprime so os parametros de video, na ordem.
cmdline_video_params() {
  local word out=()
  for word in $1; do
    case $word in
      video=* | drm.edid_firmware=*) out+=("$word") ;;
    esac
  done
  printf '%s\n' "${out[*]}"
}

# cmdline_video_spec LINHA CONECTOR imprime o que vem depois de video=CONECTOR:
cmdline_video_spec() {
  local word
  for word in $1; do
    if [[ $word == "video=$2:"* ]]; then
      printf '%s\n' "${word#"video=$2:"}"
      return 0
    fi
  done
  return 1
}

# cmdline_set_video LINHA CONECTOR SPEC troca o video= do conector.
cmdline_set_video() {
  local line=$1 conn=$2 spec=$3 word out=() done=0
  for word in $line; do
    if [[ $word == "video=$conn:"* ]]; then
      ((done)) || out+=("video=$conn:$spec")
      done=1
      continue
    fi
    out+=("$word")
  done
  ((done)) || out+=("video=$conn:$spec")
  printf '%s\n' "${out[*]}"
}

# cmdline_set_video_option LINHA CONECTOR NOME VALOR troca uma opcao
# ",nome=valor" do video= do conector (panel_orientation, por exemplo).
cmdline_set_video_option() {
  local line=$1 conn=$2 name=$3 value=$4 spec part parts=() out=() done=0
  if ! spec=$(cmdline_video_spec "$line" "$conn"); then
    cmdline_set_video "$line" "$conn" "$name=$value"
    return
  fi
  IFS=',' read -r -a parts <<< "$spec"
  for part in "${parts[@]}"; do
    if [[ $part == "$name="* ]]; then
      ((done)) || out+=("$name=$value")
      done=1
      continue
    fi
    out+=("$part")
  done
  ((done)) || out+=("$name=$value")
  local joined
  joined=$(IFS=,; printf '%s' "${out[*]}")
  cmdline_set_video "$line" "$conn" "$joined"
}

# cmdline_remove_video_option LINHA CONECTOR NOME tira a opcao; se o video=
# ficar vazio, ele sai inteiro.
cmdline_remove_video_option() {
  local line=$1 conn=$2 name=$3 spec part parts=() out=() word res=()
  if ! spec=$(cmdline_video_spec "$line" "$conn"); then
    printf '%s\n' "$line"
    return
  fi
  IFS=',' read -r -a parts <<< "$spec"
  for part in "${parts[@]}"; do
    [[ $part == "$name="* ]] && continue
    out+=("$part")
  done
  if ((${#out[@]} == 0)); then
    for word in $line; do
      [[ $word == "video=$conn:"* ]] && continue
      res+=("$word")
    done
    printf '%s\n' "${res[*]}"
    return
  fi
  local joined
  joined=$(IFS=,; printf '%s' "${out[*]}")
  cmdline_set_video "$line" "$conn" "$joined"
}
