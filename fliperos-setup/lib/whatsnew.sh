# shellcheck shell=bash
# O que ha de novo no FliperOS: a secao da versao no CHANGELOG.md (o
# fliperos-rootfs.sh o poe em /usr/local/share/fliperos, na ISO e em cada
# update) e os titulos dos updates aplicados, do log do fliperos-update, com
# as notas de cada um (updates/notes/NNNN.md, na mesma pasta). O
# menu principal mostra uma vez, depois de uma versao ou de um update novo
# (screens/whatsnew.sh); Setup > System > What's new mostra de novo.
#
# O que ja foi visto fica no fliperos.conf: whatsnew_version e
# whatsnew_level (o nivel do update).

WHATSNEW_CHANGELOG=${WHATSNEW_CHANGELOG:-/usr/local/share/fliperos/CHANGELOG.md}
WHATSNEW_UPDATE_LOG=${WHATSNEW_UPDATE_LOG:-/var/log/fliperos-update.log}
WHATSNEW_NOTES=${WHATSNEW_NOTES:-/usr/local/share/fliperos/update-notes}

# whatsnew_level: o nivel do ultimo update aplicado (0: nenhum).
whatsnew_level() {
  local level
  level=$(cat "$FLIPEROS_ETC/patch-level" 2> /dev/null) || level=0
  [[ $level =~ ^[0-9]+$ ]] || level=0
  echo "$level"
}

# whatsnew_updates [DEPOIS_DE]: "N<TAB>titulo" dos updates aplicados, do mais
# novo ao mais velho, so os acima de DEPOIS_DE. O log do fliperos-update tem
# "DATA HORA update N (titulo): X files replaced..." antes de cada um e
# "DATA HORA update N applied" quando ele termina; sem o segundo, nao entrou.
whatsnew_updates() {
  local after=${1:-0}
  [[ -f $WHATSNEW_UPDATE_LOG ]] || return 0
  awk -v after="$after" '
    $3 == "update" && $4 ~ /^[0-9]+$/ && NF == 5 && $5 == "applied" {
      if ($4 + 0 > after + 0 && ($4 in title)) done[$4] = title[$4]
      next
    }
    $3 == "update" && $4 ~ /^[0-9]+$/ && $5 ~ /^\(/ {
      t = $0
      sub(/^[^ ]+ [^ ]+ update [0-9]+ \(/, "", t)
      sub(/\): [0-9]+ files replaced.*$/, "", t)
      title[$4] = t
    }
    END { for (n in done) printf "%d\t%s\n", n, done[n] }
  ' "$WHATSNEW_UPDATE_LOG" | sort -t $'\t' -k1,1nr
}

# whatsnew_plain: o Markdown do CHANGELOG em texto (sem **, ` e o endereco
# dos links), e o "## 0.10" como "FliperOS 0.10".
whatsnew_plain() {
  sed -E -e 's/\*\*//g' -e 's/`//g' -e 's/\[([^]]*)\]\([^)]*\)/\1/g' -e 's/^## (.*)/FliperOS \1/'
}

# whatsnew_sections DE ATE: as secoes do CHANGELOG das versoes acima de DE
# ate ATE (vazio em DE: so a de ATE), da mais nova a mais velha.
whatsnew_sections() {
  local from=$1 to=$2 version
  [[ -f $WHATSNEW_CHANGELOG ]] || return 0
  while read -r version; do
    if [[ -z $from ]]; then
      [[ $version == "$to" ]] || continue
    else
      [[ $version != "$from" && $(printf '%s\n%s\n' "$from" "$version" | sort -V | tail -1) == "$version" ]] || continue
      [[ $(printf '%s\n%s\n' "$to" "$version" | sort -V | tail -1) == "$to" ]] || continue
    fi
    awk -v version="$version" '/^## / { on = ($2 == version) } on' "$WHATSNEW_CHANGELOG"
    echo
  done < <(awk '/^## / { print $2 }' "$WHATSNEW_CHANGELOG")
}

# whatsnew_text [all]: o texto da tela. Sem "all", so o que nao foi visto:
# os updates acima do whatsnew_level e as versoes acima da whatsnew_version
# (nunca vista: so a desta versao, sem a lista dos updates). Com "all", todos
# os updates aplicados e o CHANGELOG inteiro.
whatsnew_text() {
  local version=$FLIPEROS_SETUP_VERSION level seen_version seen_level updates sections n title notes
  level=$(whatsnew_level)
  if [[ ${1:-} == all ]]; then
    updates=$(whatsnew_updates 0)
    sections=$( [[ -f $WHATSNEW_CHANGELOG ]] && sed -n '/^## /,$p' "$WHATSNEW_CHANGELOG")
  else
    seen_version=$(conf_get whatsnew_version 2> /dev/null) || seen_version=""
    seen_level=$(conf_get whatsnew_level 2> /dev/null) || seen_level=""
    updates=""
    [[ -n $seen_level ]] && updates=$(whatsnew_updates "$seen_level")
    sections=""
    [[ $seen_version != "$version" ]] && sections=$(whatsnew_sections "$seen_version" "$version")
  fi
  [[ -n $updates || -n $sections ]] || return 0
  if ((level)); then
    echo "This is FliperOS $version, update $level."
  else
    echo "This is FliperOS $version."
  fi
  if [[ -n $updates ]]; then
    printf '\nUpdates installed:\n'
    while IFS=$'\t' read -r n title; do
      printf -- '- %s. %s\n' "$n" "$title"
      notes=$(printf '%s/%04d.md' "$WHATSNEW_NOTES" "$n")
      [[ ! -s $notes ]] || whatsnew_plain < "$notes" | sed 's/^./  &/'
    done <<< "$updates"
  fi
  [[ -z $sections ]] || printf '\n%s\n' "$sections" | whatsnew_plain
}

# whatsnew_seen [RAIZ]: marca esta versao e o nivel de agora como vistos (o
# fliperos.conf de RAIZ, na instalacao: um disco novo nao tem nada de novo).
whatsnew_seen() {
  local root=${1:-} level
  level=$(FLIPEROS_ETC=$root$FLIPEROS_ETC whatsnew_level)
  conf_set whatsnew_version "$FLIPEROS_SETUP_VERSION" "$root$FLIPEROS_CONF"
  conf_set whatsnew_level "$level" "$root$FLIPEROS_CONF"
}
