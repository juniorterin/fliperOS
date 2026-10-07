# shellcheck shell=bash
# Splash do boot (Setup > Splash screen): os temas do Plymouth em
# ~/splashscreen, um por pasta (o fliperos-roms poe la os da imagem). Usar
# um copia a pasta para o Plymouth com os caminhos de la, o marca como
# padrao (o alternative default.plymouth) e refaz o initramfs, o unico lugar
# de onde o Plymouth do boot le o tema; o hook do initramfs leva o initrd
# novo para a ESP (fliperos-limine-update). A previa sobe o plymouthd com o
# tema por alguns segundos, como no boot.

SPLASH_DIR=${SPLASH_DIR:-/home/$FLIPEROS_USER/splashscreen}
SPLASH_BUNDLED=${SPLASH_BUNDLED:-/usr/share/fliperos/splashscreen}
PLYMOUTH_THEMES=${PLYMOUTH_THEMES:-/usr/share/plymouth/themes}
SPLASH_PREVIEW_SECONDS=${SPLASH_PREVIEW_SECONDS:-10}
# Onde achar mais temas (os do Plymouth no Gnome-look, os mais novos primeiro).
SPLASH_MORE_URL=${SPLASH_MORE_URL:-https://www.gnome-look.org/browse?cat=108&ord=latest}
PLYMOUTH=${PLYMOUTH:-plymouth}
PLYMOUTHD=${PLYMOUTHD:-plymouthd}
UPDATE_ALTERNATIVES=${UPDATE_ALTERNATIVES:-update-alternatives}
UPDATE_INITRAMFS=${UPDATE_INITRAMFS:-update-initramfs}

# splash_valid_name NOME: o nome da pasta vira o do tema no Plymouth.
splash_valid_name() {
  [[ $1 =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ && $1 != *.plymouth ]]
}

# splash_theme_file PASTA imprime o .plymouth do tema: o de mesmo nome da
# pasta ou, se so ha um, esse.
splash_theme_file() {
  local dir=${1%/} files
  if [[ -f $dir/$(basename "$dir").plymouth ]]; then
    printf '%s\n' "$dir/$(basename "$dir").plymouth"
    return 0
  fi
  files=("$dir"/*.plymouth)
  [[ ${#files[@]} == 1 && -f ${files[0]} ]] || return 1
  printf '%s\n' "${files[0]}"
}

# splash_key ARQUIVO CHAVE le "Chave=valor" do .plymouth.
splash_key() {
  awk -v k="$2" '{ sub(/\r$/, "") } index($0, k "=") == 1 { print substr($0, length(k) + 2); exit }' "$1"
}

# splash_source NOME imprime a pasta do tema (a de ~/splashscreen vence a da
# imagem).
splash_source() {
  local dir
  splash_valid_name "$1" || return 1
  for dir in "$SPLASH_DIR/$1" "$SPLASH_BUNDLED/$1"; do
    if [[ -d $dir ]] && splash_theme_file "$dir" > /dev/null; then
      printf '%s\n' "$dir"
      return 0
    fi
  done
  return 1
}

# splash_list imprime "nome|Nome - descricao" de cada tema.
splash_list() {
  local dir name file seen=" " label desc
  for dir in "$SPLASH_DIR"/*/ "$SPLASH_BUNDLED"/*/; do
    [[ -d $dir ]] || continue
    name=$(basename "$dir")
    [[ $seen == *" $name "* ]] && continue
    splash_valid_name "$name" || continue
    file=$(splash_theme_file "$dir") || continue
    [[ -n $(splash_key "$file" ModuleName) ]] || continue
    seen+="$name "
    label=$(splash_key "$file" Name)
    desc=$(splash_key "$file" Description)
    printf '%s|%s\n' "$name" "${label:-$name}${desc:+ - $desc}"
  done
}

# splash_current imprime o tema do boot.
splash_current() {
  local file
  file=$(readlink -f "$PLYMOUTH_THEMES/default.plymouth") || return 1
  [[ -f $file ]] || return 1
  basename "$(dirname "$file")"
}

# splash_stage NOME copia o tema para o Plymouth como NOME/NOME.plymouth,
# com o ImageDir e o ScriptFile apontando para la.
splash_stage() {
  local name=$1 src file dest
  src=$(splash_source "$name") || return 1
  file=$(splash_theme_file "$src") || return 1
  dest=$PLYMOUTH_THEMES/$name
  rm -rf "$dest.new"
  mkdir -p "$PLYMOUTH_THEMES"
  cp -r "$src" "$dest.new" || return 1
  awk -v d="$dest" '
    { sub(/\r$/, "") }
    /^ImageDir=/ { print "ImageDir=" d; next }
    /^ScriptFile=/ { f = $0; sub(/^ScriptFile=/, "", f); sub(/.*\//, "", f); print "ScriptFile=" d "/" f; next }
    { print }' "$file" > "$dest.new/.theme" || return 1
  rm -f "$dest.new/${file##*/}"
  mv -f "$dest.new/.theme" "$dest.new/$name.plymouth"
  chmod -R a+rX "$dest.new"
  rm -rf "$dest"
  mv "$dest.new" "$dest"
  log_info "splash: $src -> $dest"
}

# splash_set NOME faz do tema o do boot (vale no proximo boot).
splash_set() {
  local name=$1 file
  splash_stage "$name" || return 1
  file=$PLYMOUTH_THEMES/$name/$name.plymouth
  run_logged "$UPDATE_ALTERNATIVES" --install "$PLYMOUTH_THEMES/default.plymouth" default.plymouth "$file" 100 &&
    run_logged "$UPDATE_ALTERNATIVES" --set default.plymouth "$file" &&
    run_logged "$UPDATE_INITRAMFS" -u || return 1
  conf_set splash "$name"
}

# splash_preview NOME mostra o tema por SPLASH_PREVIEW_SECONDS: o plymouthd
# com plymouth.splash=NOME, que vale por cima do tema padrao.
splash_preview() {
  local name=$1
  splash_stage "$name" || return 1
  # Um plymouthd ainda no ar (o do boot) seria o que apareceria.
  "$PLYMOUTH" --ping 2> /dev/null && return 1
  mkdir -p /run/fliperos
  run_logged "$PLYMOUTHD" --mode=boot --tty="${SPLASH_TTY:-/dev/tty1}" --pid-file=/run/fliperos/plymouth-preview.pid \
    --kernel-command-line="quiet splash plymouth.splash=$name" || return 1
  run_logged "$PLYMOUTH" show-splash
  sleep "$SPLASH_PREVIEW_SECONDS"
  run_logged "$PLYMOUTH" quit
  return 0
}
