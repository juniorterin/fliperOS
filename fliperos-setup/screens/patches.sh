# shellcheck shell=bash
# O update do FliperOS no boot (fliperos-setup --update-check): avisa, mostra
# os arquivos mudados nesta maquina que ele troca (com copia antes) e
# pergunta. "Agora nao" pergunta de novo no proximo boot.

# Quantos arquivos cabem na tela; o resto fica em "View the files".
PATCH_FILES_SHOWN=6

screen_update_check() {
  local title="FliperOS update" list n reboot name result files text choice count shown=0 more
  local -a titles=()
  list=$(patch_pending) || return 0
  [[ -n $list ]] || return 0
  while IFS=$'\t' read -r n reboot name; do
    titles+=("  $n. $name")
  done <<< "$list"
  result=$(mktemp)
  files=$(mktemp)
  if ! run_with_progress "Checking the FliperOS update" "" patch_plan "$result"; then
    rm -f "$result" "$files"
    return 0
  fi
  awk -F'\t' '$1 == "local" || $1 == "unknown" { print $2 }' "$result" > "$files"
  count=$(grep -c . "$files")
  text="$(printf '%s\n' "There is a FliperOS update (${#titles[@]} part(s), applied in order):" "${titles[@]}")"
  if ((count)); then
    text+=$'\n\n'"Files changed on this machine that it replaces (a copy of each is kept in $PATCH_BACKUPS):"
    while IFS= read -r n && ((shown < PATCH_FILES_SHOWN)); do
      text+=$'\n'"  $n"
      shown=$((shown + 1))
    done < "$files"
    more=$((count - shown))
    ((more > 0)) && text+=$'\n'"  ...and $more more (View the files)"
  else
    text+=$'\n\n'"No file changed on this machine is replaced."
  fi
  text+=$'\n'"The Setup choices (video, latency, buttons) are applied again afterwards."
  while true; do
    if ((count)); then
      choice=$(ui_menu "$title" "$text" apply "apply|Apply now" "files|View the files" \
        "later|Not now (asks again at the next boot)") || choice=later
    else
      choice=$(ui_menu "$title" "$text" apply "apply|Apply now" \
        "later|Not now (asks again at the next boot)") || choice=later
    fi
    case $choice in
      files) ui_pager "Files the update replaces" "$files" inicio ;;
      apply) break ;;
      *)
        log_info "FliperOS update: not now"
        rm -f "$result" "$files"
        return 0
        ;;
    esac
  done
  rm -f "$files"
  if run_with_progress "Updating FliperOS" "" patch_apply "$result"; then
    reboot=$(awk -F'\t' '$1 == "applied" && $3 == "yes" { print "yes"; exit }' "$result")
    n=$(awk -F'\t' '$1 == "applied" { n = $2 } END { print n }' "$result")
    rm -f "$result"
    if [[ $reboot == yes ]]; then
      ui_yesno "$title" "FliperOS is up to date (update $n). It needs a restart to finish. Restart now?" yes &&
        systemctl reboot
    else
      ui_msg "$title" "FliperOS is up to date (update $n)." "The copies of the replaced files are in $PATCH_BACKUPS."
    fi
  else
    rm -f "$result"
    ui_msg "$title" "$(ui_bad "The update did not finish.")" \
      "Nothing after the failed part was applied; it is offered again at the next boot." \
      "Log: /var/log/fliperos-update.log. Copies of the replaced files: $PATCH_BACKUPS."
  fi
  return 0
}
