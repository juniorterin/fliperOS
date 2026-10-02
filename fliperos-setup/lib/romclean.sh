# shellcheck shell=bash
# MAME ROM Cleaner (Setup): tira de uma pasta de ROMs do MAME os sets que as
# regras escolhidas excluem, pelo XML da versao do MAME daquele romset
# (config/fliperos-romclean). Nada e apagado sem a pessoa escolher: o padrao
# e mover para a pasta irma "<pasta>-removed".

ROMCLEAN=${ROMCLEAN:-/opt/fliperos/bin/fliperos-romclean}
# O XML do MAME 2010 (0.139), do core mame2010 do RetroArch (o build e o
# cabinet-update.sh o baixam: fliperos-romclean fetch-mame2010).
MAME2010_XML=${MAME2010_XML:-/usr/local/share/fliperos/mame2010.xml.xz}
ROMS_ROOT=${ROMS_ROOT:-/home/fliperos/roms}
GROOVYMAME=${GROOVYMAME:-groovymame}

# As regras, na ordem da tela: "modo:regra|rotulo". O modo "exclude" tira o
# que casa; o "only" deixa so o que casa.
ROMCLEAN_RULES=(
  "exclude:clone|Remove clones"
  "exclude:bios|Remove BIOS and device sets no game here needs"
  "exclude:notworking|Remove games that don't work (preliminary)"
  "exclude:mechanical|Remove mechanical games (pinball, slots...)"
  "exclude:vertical|Remove vertical games"
  "exclude:horizontal|Remove horizontal games"
  "exclude:vector|Remove vector games"
  "exclude:chd|Remove games that need a CHD (disk or CD)"
  "only:psx|Keep only PlayStation-based hardware (ZN, System 11/12...)"
)

# romclean_default_source PASTA imprime o XML provavel do romset: o do MAME
# 2010 numa pasta que tem "2010" no nome (a do core, ~/roms/retroarch/
# mame2010), senao o do GroovyMAME instalado.
romclean_default_source() {
  if [[ ${1,,} == *2010* && -f $MAME2010_XML ]]; then
    echo mame2010
  else
    echo groovymame
  fi
}

# romclean_source_label FONTE imprime o nome da fonte do XML para a tela.
romclean_source_label() {
  case $1 in
    groovymame) echo "GroovyMAME $(groovymame_version)" ;;
    mame2010) echo "MAME 2010 (0.139)" ;;
    *) echo "$1" ;;
  esac
}

# groovymame_version imprime a versao do GroovyMAME instalado (0.289).
groovymame_version() {
  "$GROOVYMAME" -version 2> /dev/null | awk 'NR == 1 { print $1; exit }'
}

# romclean_dest PASTA imprime para onde vai o que sai: a pasta irma
# "<pasta>-removed", no mesmo disco (mover e so renomear).
romclean_dest() {
  printf '%s-removed\n' "${1%/}"
}

# romclean_scan PASTA FONTE PLANO REGRA... le o XML (groovymame = o
# -listxml do GroovyMAME, mame2010 = o do core, ou um arquivo) e escreve o
# plano; imprime o resumo do fliperos-romclean (chave=valor). REGRA e
# "exclude:clone", "only:psx"...
romclean_scan() {
  local folder=$1 source=$2 plan=$3 rule args=()
  shift 3
  for rule in "$@"; do
    args+=("--${rule%%:*}" "${rule#*:}")
  done
  case $source in
    groovymame)
      "$GROOVYMAME" -listxml 2> /dev/null |
        "$ROMCLEAN" scan --xml - --roms "$folder" --plan "$plan" "${args[@]}"
      ;;
    mame2010) "$ROMCLEAN" scan --xml "$MAME2010_XML" --roms "$folder" --plan "$plan" "${args[@]}" ;;
    *) "$ROMCLEAN" scan --xml "$source" --roms "$folder" --plan "$plan" "${args[@]}" ;;
  esac
}

# romclean_value RESUMO CHAVE imprime um valor do resumo do scan.
romclean_value() {
  sed -n "s/^$2=//p" <<< "$1" | tail -1
}

# romclean_list PLANO imprime o que sai, um set por linha: nome e titulo
# (cortado, para caber em 80 colunas e a lista no limite do ui_pager).
romclean_list() {
  awk -F'\t' '!/^#/ && !seen[$1]++ { printf "%-16s %s\n", $1, substr($4, 1, 58) }' "$1"
}

# romclean_apply PLANO move DESTINO | PLANO delete: faz o que o plano diz.
romclean_apply() {
  local plan=$1 action=$2 dest=${3:-}
  log_info "ROM cleaner: $action $(grep -cv '^#' "$plan") arquivos de $(sed -n 's/^# roms\t//p' "$plan")${dest:+ para $dest}"
  case $action in
    move) "$ROMCLEAN" apply "$plan" --move-to "$dest" ;;
    delete) "$ROMCLEAN" apply "$plan" --delete ;;
    *) return 2 ;;
  esac
}

# human_bytes N imprime o tamanho legivel (1.2 GB).
human_bytes() {
  awk -v b="$1" 'BEGIN { split("B KB MB GB TB", u); i = 1
    while (b >= 1024 && i < 5) { b /= 1024; i++ }
    printf (i == 1 ? "%d %s\n" : "%.1f %s\n"), b, u[i] }'
}
