# shellcheck shell=bash
# What's new (lib/whatsnew.sh): o changelog da versao e os updates
# aplicados, com rolagem.

# screen_whatsnew_check: no comeco do menu principal, uma vez depois de uma
# versao ou de um update novo. So no disco instalado.
screen_whatsnew_check() {
  local text
  is_installed && ! is_live || return 0
  text=$(mktemp)
  whatsnew_text > "$text"
  if [[ -s $text ]]; then
    log_info "What's new: FliperOS $FLIPEROS_SETUP_VERSION, update $(whatsnew_level)"
    ui_pager "What's new in FliperOS" "$text" inicio
  fi
  rm -f "$text"
  whatsnew_seen
}

# screen_whatsnew (Setup > System > What's new): os updates aplicados e o
# changelog de todas as versoes.
screen_whatsnew() {
  local text
  text=$(mktemp)
  whatsnew_text all > "$text"
  if [[ -s $text ]]; then
    ui_pager "What's new in FliperOS" "$text" inicio
  else
    ui_msg "What's new in FliperOS" "This is FliperOS $FLIPEROS_SETUP_VERSION." "The changelog is not on this system."
  fi
  rm -f "$text"
  is_installed && ! is_live && whatsnew_seen
  return 0
}
