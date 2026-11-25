# shellcheck shell=bash
# Setup > Audio > Menu sounds: seis eventos (o cursor andando, entrar, voltar,
# abrir o jogo, fechar o jogo e o dialogo de alerta), cada um com o arquivo e o
# volume dele (lib/audio.sh, gui/fesound.py). Os arquivos ficam em
# ~/media/fliperos-sounds e se escolhem no seletor de arquivos. O Frontend
# sounds, no Tab > Frontend options do frontend, e o espelho desta tela.

# menu_sound_hint EVENTO: a dica do evento (cabe nas 2 linhas de 34 colunas).
menu_sound_hint() {
  case $1 in
    move) echo "Plays when the cursor moves through a list." ;;
    enter) echo "Plays when you go into something." ;;
    back) echo "Plays when you go back." ;;
    open) echo "Plays when a game is opened." ;;
    close) echo "Plays when a game closes." ;;
    alert) echo "Plays when an alert or a question opens." ;;
  esac
}

screen_menu_sounds() {
  local title="Menu sounds" choice last="" id label file volume
  local -a entries
  sounds_seed
  while true; do
    entries=("master|Sounds ($(menu_sounds_label))|Turns all the menu sounds on or off.")
    while IFS='|' read -r id label file volume; do
      entries+=("snd-$id|$label: ${file,,}, $volume%|$(menu_sound_hint "$id")")
    done < <(menu_sound_rows)
    entries+=("folder|Sounds folder|Where the sound files are, and how to add yours."
      "return|Return|Back to Audio Setup.")
    choice=$(ui_menu_hints "$title" "Pick an event, then its sound and volume. The frontend uses the same ones." "$last" \
      "${entries[@]}") || return 0
    last=$choice
    case $choice in
      master)
        if [[ $(menu_sounds_state) == on ]]; then menu_sounds_set off; else menu_sounds_set on; fi
        ui_sounds
        ;;
      snd-*) screen_menu_sound_event "${choice#snd-}" ;;
      folder)
        ui_msg "Sounds folder" "$(sounds_dir)" "" \
          "Put your sounds there (WAV, OGG, MP3 or FLAC) and choose them here." \
          "The music of the frontend goes in the music folder inside it." \
          "On the network it is the FliperOS share, folder media/fliperos-sounds."
        ;;
      return) return 0 ;;
    esac
  done
}

# screen_menu_sound_event EVENTO: o arquivo (o seletor de arquivos), o volume,
# ouvir, o padrao e mudo de um evento.
screen_menu_sound_event() {
  local event=$1 id label file volume choice last="" start picked
  while true; do
    IFS='|' read -r id label file volume < <(menu_sound_row "$event")
    [[ -n $id ]] || return 0
    choice=$(ui_menu_hints "$label" "$(ui_fields "Sound|${file,,}" "Volume|$volume%")" "$last" \
      "file|Sound file|Choose a WAV, OGG, MP3 or FLAC from the sounds folder." \
      "volume|Volume|From 0 to 100." \
      "snd-play|Play|Hear it now, with this volume." \
      "snd-default|Use the default|The sound FliperOS comes with." \
      "off|No sound|Keep this event quiet." \
      "return|Return|Back to the menu sounds.") || return 0
    last=$choice
    case $choice in
      file)
        start=$(sounds_dir)
        [[ -d $start ]] || start=${FOLDERS_HOME:-/}
        picked=$(ui_browse "$label" "Choose the sound for $label (WAV, OGG, MP3 or FLAC)." "$start" file \
          .wav .ogg .mp3 .flac) || continue
        menu_sound_set_file "$event" "$picked"
        ui_sounds
        menu_sound_play "$event"
        ;;
      volume)
        choice=$(ui_input "Volume" "Volume of $label (0-100)" "$volume") || continue
        if menu_sound_set_volume "$event" "$choice"; then
          ui_sounds
          menu_sound_play "$event"
        else
          ui_msg "Volume" "Type a number from 0 to 100."
        fi
        ;;
      snd-play)
        if [[ $(menu_sounds_state) == off ]]; then
          ui_msg "$label" "The menu sounds are off: turn them on in Menu sounds."
        else
          menu_sound_play "$event"
        fi
        ;;
      snd-default)
        menu_sound_set_file "$event" ""
        ui_sounds
        menu_sound_play "$event"
        ;;
      off)
        menu_sound_set_file "$event" off
        ui_sounds
        ;;
      return) return 0 ;;
    esac
  done
}
