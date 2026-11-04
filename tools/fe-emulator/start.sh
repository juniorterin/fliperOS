#!/bin/bash
# Dentro do container do emulador do frontend (tools/fe-emulator/run.sh):
# monta a pasta pessoal de mentira, abre a tela X (Xvfb), o VNC e o noVNC
# (o navegador em http://localhost:6080) e roda o fliperos-frontend do
# repositorio (/g), de novo sempre que ele fecha.
#
# A pasta pessoal fica no volume /emu-home e e montada uma vez so:
# - com /demo.tar (a biblioteca de amostra do gabinete, tools/video/render.sh
#   library), os jogos dela com tela, capa, logo, marquee e video;
# - sem ele, uma amostra pequena so com os nomes (o scrape automatico do
#   frontend busca a midia na internet, como no gabinete).
#
# O lan-relay.py traz a presenca dos gabinetes da rede: as festas (lobbies)
# abertas aparecem no alto da lista, como no gabinete.
set -e
H=/emu-home/home
SIZE=${FE_EMU_SIZE:-960x720}
useradd -M -d $H fliperos 2> /dev/null || true

sample() {
  mkdir -p $H/.cache/fliperos $H/.local/share/fliperos/lists $H/.config/fliperos
  cat > $H/.cache/fliperos/frontend-systems << EOF
mame|$H/roms/mame|arcade|MAME|/opt/fliperos/bin/fliperos-x11-run|groovymame [name]|.zip;.7z|1
model2|$H/roms/model2|arcade|Model 2|/opt/fliperos/bin/fliperos-x11-run|fliperos-model2 [name]|.zip|1
model3|$H/roms/model3|arcade|Supermodel|/opt/fliperos/bin/fliperos-x11-run|supermodel "[romfilename]"|.zip|1
naomi|$H/roms/naomi|naomi|Naomi|/opt/fliperos/bin/fliperos-x11-run|flycast "[romfilename]"|.zip;.7z|1
retroarch/snes9x|$H/roms/retroarch/snes9x|snes|Super Nintendo (Snes9x)|/opt/fliperos/bin/fliperos-kms-run|retroarch -L snes9x_libretro.so "[romfilename]"|.sfc;.smc;.zip|0
EOF
  printf '\tfilter               "All Games"\n\t\tsort_by              Title\n' > $H/.cache/fliperos/frontend-filters
  printf '\tfilter               "Fighting Games"\n\t\tsort_by              Title\n\t\trule                 Category equals Fight.+\n' \
    >> $H/.cache/fliperos/frontend-filters
  local list=$H/.local/share/fliperos/lists/MAME.txt
  echo '#Name;Title;Emulator;CloneOf;Year;Manufacturer;Category;Players;Rotation;Control;Status;DisplayCount;DisplayType;AltRomname;AltTitle;Extra;Buttons;Series;Language;Region;Rating' > "$list"
  while IFS=';' read -r name title clone year maker cat players buttons; do
    echo "$name;$title;MAME;$clone;$year;$maker;$cat;$players;0;joystick (8-way);good;1;raster;;;;$buttons;;;;" >> "$list"
  done << 'EOF'
1944;1944: The Loop Master (Europe 000620);;2000;Eighting / Raizing (Capcom license);Shooter / Flying Vertical;2;2
dino;Cadillacs and Dinosaurs (World 930201);;1993;Capcom;Fighter / Scrolling;3;2
galaga;Galaga (Namco rev. B);;1981;Namco;Shooter / Flying Vertical;2;1
kof98;The King of Fighters '98 - The Slugfest / King of Fighters '98 - Dream Match Never Ends;;1998;SNK;Fighter / Versus;2;4
mslug;Metal Slug - Super Vehicle-001;;1996;Nazca;Platform / Run Jump;2;3
pacman;Pac-Man (Midway);;1980;Namco (Midway license);Maze / Collect;2;0
punisher;The Punisher (World 930422);;1993;Capcom;Fighter / Scrolling;2;2
samsho5;Samurai Shodown V / Samurai Spirits Zero (NGM-2700, set 1);;2003;Yuki Enterprise / SNK Playmore;Fighter / Versus;2;4
samsho5a;Samurai Shodown V / Samurai Spirits Zero (NGM-2700, set 2);samsho5;2003;Yuki Enterprise / SNK Playmore;Fighter / Versus;2;4
sf2;Street Fighter II: The World Warrior (World 910522);;1991;Capcom;Fighter / Versus;2;6
simpsons;The Simpsons (4 Players World, set 1);;1991;Konami;Fighter / Scrolling;4;2
tmnt;Teenage Mutant Ninja Turtles (World 4 Players, version X);;1989;Konami;Fighter / Scrolling;4;2
EOF
  mkdir -p $H/roms/mame $H/roms/retroarch/snes9x
  cut -d';' -f1 "$list" | tail -n +2 | while read -r name; do : > "$H/roms/mame/$name.zip"; done
  for f in "Chrono Trigger (USA)" "Super Mario World (USA)" "Super Metroid (Japan, USA)"; do
    : > "$H/roms/retroarch/snes9x/$f.sfc"
  done
}

if [ ! -e /emu-home/.ready ]; then
  rm -rf $H && mkdir -p $H
  if [ -s /demo.tar ]; then
    echo "fe-emulator: abrindo a biblioteca de amostra (uma vez so)..."
    tar xf /demo.tar -C $H
    # Os arquivos de jogo da amostra (vazios) e so os sistemas que tem jogo.
    sed -i "s#/home/fliperos#$H#g" $H/.cache/fliperos/frontend-systems
    while IFS=$'\t' read -r key file; do
      [ -n "$key" ] || continue
      folder=$(awk -F'|' -v k="$key" '$1 == k { print $2; exit }' $H/.cache/fliperos/frontend-systems)
      mkdir -p "$folder"
      : > "$folder/$file"
    done < $H/demo-roms.txt
    # Os sistemas da amostra, e os de jogos de link (o lan-relay.py poe neles
    # os jogos das festas da rede).
    keep=$(cut -f1 $H/demo-roms.txt | sort -u | tr '\n' '|')
    awk -F'|' -v keep="|${keep}mame|model2|model3|naomi|naomi2|atomiswave|" 'index(keep, "|" $1 "|")' \
      $H/.cache/fliperos/frontend-systems > /tmp/systems
    cp /tmp/systems $H/.cache/fliperos/frontend-systems
  else
    echo "fe-emulator: sem demo.tar, usando a amostra pequena (so nomes)"
    sample
  fi
  # O 5 (filtros) nao tem tecla no padrao: aqui fica no G.
  [ -e $H/.config/fliperos/frontend.json ] || echo '{"controls": {"b5": {"key": 103}}}' > $H/.config/fliperos/frontend.json
  chown -R fliperos $H 2> /dev/null || true
  touch /emu-home/.ready
fi

# O Setup de mentira: responde com o que a pasta pessoal tem.
cat > /emu/fliperos-setup << EOF
#!/bin/bash
case \$1 in
  --systems) cat $H/.cache/fliperos/frontend-systems ;;
  --filters) cat $H/.cache/fliperos/frontend-filters ;;
esac
EOF
chmod +x /emu/fliperos-setup

Xvfb :0 -screen 0 "${SIZE}x24" -nolisten tcp > /tmp/xvfb.log 2>&1 &
for _ in $(seq 50); do [ -e /tmp/.X11-unix/X0 ] && break; sleep 0.1; done
x11vnc -display :0 -forever -shared -nopw -localhost -rfbport 5900 -quiet > /tmp/x11vnc.log 2>&1 &
websockify --web /usr/share/novnc 6080 localhost:5900 > /tmp/websockify.log 2>&1 &
python3 -I /emu/lan-relay.py /tmp/link-table.json $H/.cache/fliperos/frontend-systems &
echo "fe-emulator: pronto em http://localhost:${FE_EMU_PORT:-6080}/vnc.html?autoconnect=1&resize=scale"

export DISPLAY=:0 SDL_VIDEODRIVER=x11 SDL_AUDIODRIVER=dummy
export HOME=$H FLIPEROS_HOME=$H FLIPEROS_SETUP=/emu/fliperos-setup FLIPEROS_BUTTONS_MAP=/nonexistent
export FLIPEROS_VIDEO_AUDIO=null FLIPEROS_WEB_MODULE=/config/fliperos-web PYTHONDONTWRITEBYTECODE=1
# A rede dos gabinetes e a do lan-relay.py: o frontend ve as festas, mas nao
# se anuncia e nao entra em nenhuma.
export FLIPEROS_LINK_FAKE=/tmp/link-table.json
cd /g
while true; do
  python3 -I /g/fliperos-frontend || echo "fe-emulator: o frontend saiu com erro ($?)"
  echo "fe-emulator: o frontend fechou; abrindo de novo"
  sleep 1
done
