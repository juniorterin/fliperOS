# shellcheck shell=bash
# O update do FliperOS no boot (fliperos-setup --update-check): mostra o que
# muda (o changelog de cada parte, com rolagem), os arquivos mudados nesta
# maquina que ele troca (com copia antes) e pergunta. "Agora nao" pergunta de
# novo no proximo boot.

# Quantos arquivos cabem na tela; o resto fica em "View the files".
PATCH_FILES_SHOWN=6

screen_update_check() {
  local title="FliperOS update" list n reboot name result files notes text choice count shown=0 more
  local -a titles=() options
  list=$(patch_pending) || return 0
  [[ -n $list ]] || return 0
  while IFS=$'\t' read -r n reboot name; do
    titles+=("  $n. $name")
  done <<< "$list"
  result=$(mktemp)
  files=$(mktemp)
  notes=$(mktemp)
  # O que muda, antes de tudo: o changelog das partes, na tela com rolagem.
  if patch_notes "$notes"; then
    ui_pager "What's new in this FliperOS update" "$notes" inicio
  fi
  if ! run_with_progress "Checking the FliperOS update" "" patch_plan "$result"; then
    rm -f "$result" "$files" "$notes"
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
    options=("apply|Apply now")
    [[ -s $notes ]] && options+=("notes|Read what changes")
    ((count)) && options+=("files|View the files")
    options+=("later|Not now (installs when the cabinet powers off)")
    choice=$(ui_menu "$title" "$text" apply "${options[@]}") || choice=later
    case $choice in
      notes) ui_pager "What's new in this FliperOS update" "$notes" inicio ;;
      files) ui_pager "Files the update replaces" "$files" inicio ;;
      apply) break ;;
      *)
        log_info "FliperOS update: not now"
        rm -f "$result" "$files" "$notes"
        return 0
        ;;
    esac
  done
  rm -f "$files" "$notes"
  if run_with_progress "Updating FliperOS" "" patch_apply "$result"; then
    reboot=$(awk -F'\t' '$1 == "applied" && $3 == "yes" { print "yes"; exit }' "$result")
    n=$(awk -F'\t' '$1 == "applied" { n = $2 } END { print n }' "$result")
    rm -f "$result"
    if [[ $reboot == yes ]]; then
      ui_yesno "$title" "FliperOS is up to date (update $n). It needs a restart to finish. Restart now?" yes &&
        screen_power_now reboot
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

# screen_update_version (Setup > System > FliperOS version): escolhe o update
# que o gabinete usa, do que veio na ISO ao mais novo (fliperos-update goto).
# Um mais velho desfaz os que vieram depois e fica nele: o boot nao pergunta
# nem o desligar aplica, ate sair um update novo. O mais novo volta a seguir
# os updates.
screen_update_version() {
  local title="FliperOS version" list key value level=0 latest=0 hold="" reboot=no n state flag name text
  local choice default result ask applied
  local -a entries
  ui_info "$title" "Reading the update list..."
  if ! list=$(patch_versions) || [[ -z $list ]]; then
    ui_msg "$title" "$(ui_bad "Could not read the update list.")" "Check the network and try again."
    return 0
  fi
  entries=()
  while IFS=$'\t' read -r n state flag name; do
    if [[ $n == *=* ]]; then
      key=${n%%=*}
      value=${n#*=}
      case $key in
        level) level=$value ;;
        latest) latest=$value ;;
        hold) hold=$value ;;
        reboot) reboot=$value ;;
      esac
      continue
    fi
    case $state in
      current) value="Installed now." ;;
      older) value="Earlier: undoes the ones after it." ;;
      *) value="Newer: installs the ones up to it." ;;
    esac
    ((n == latest)) && value+=" The newest."
    [[ $flag == yes ]] && value+=" Needs a restart."
    entries+=("$n|Update $n: $name|$value")
  done <<< "$list"
  text="This cabinet is at update $level"
  if [[ -n $hold ]]; then
    text+=", chosen by hand: the boot only offers an update newer than $latest."
  elif ((level == latest)); then
    text+=", the newest."
  else
    text+="."
  fi
  [[ $reboot == yes ]] && text+=" Restart the computer to finish the last change."
  text+=" Choose the update to use."
  default=$level
  [[ -n $hold ]] && entries=("latest|Follow the updates|Back to the newest and to the updates offered at boot." "${entries[@]}")
  choice=$(UI_STYLE=list ui_menu_hints "$title" "$text" "$default" "${entries[@]}" \
    "return|Return|Back to System.") || return 0
  case $choice in
    return | "") return 0 ;;
    latest) n=$latest ;;
    *) n=$choice ;;
  esac
  if ((n == level)); then
    if ((n < latest)) && [[ -z $hold ]]; then
      ui_yesno "$title" "Stay on update $n? The boot stops offering the updates after it until a new one comes out." no ||
        return 0
    elif [[ $choice != latest ]]; then
      ui_msg "$title" "This cabinet is already at update $n."
      return 0
    fi
  elif ((n < level)); then
    ask="Go back to update $n? The updates after it are undone (the files they replace are copied to $PATCH_BACKUPS) and the cabinet stays on update $n until a new update comes out."
    ui_yesno "$title" "$ask" no || return 0
    screen_need_internet "$title" || return 0
  else
    ui_yesno "$title" "Install the updates up to update $n?" yes || return 0
    screen_need_internet "$title" || return 0
  fi
  result=$(mktemp)
  if run_with_progress "Changing the FliperOS version" "" patch_goto "$n" "$result"; then
    applied=$(awk -F'\t' '($1 == "applied" || $1 == "back") && $3 == "yes" { print "yes"; exit }' "$result")
    rm -f "$result"
    UI_STATUS=$(status_line)
    if [[ $applied == yes ]]; then
      ui_yesno "$title" "FliperOS is at update $n. It needs a restart to finish. Restart now?" yes &&
        screen_power_now reboot
    else
      ui_msg "$title" "FliperOS is at update $n." "The copies of the replaced files are in $PATCH_BACKUPS."
    fi
  else
    rm -f "$result"
    ui_msg "$title" "$(ui_bad "The change did not finish.")" \
      "Log: /var/log/fliperos-update.log. Copies of the replaced files: $PATCH_BACKUPS."
  fi
  return 0
}
