#!/usr/bin/env bash
# Compila o firmware do Open Source Cartridge Reader (github.com/sanni/cartreader)
# com o patch do FliperOS (patches/oscr: o dump pela USB, que o frontend usa,
# gui/femedia.py), num Ubuntu 24.04 no Docker com o arduino-cli. Sai em
# output/oscr um .hex por variante do HW5: sem e com o modulo VSELECT (a
# tensao trocada pelo firmware).
#
#   bash tools/oscr-firmware.sh
#
# Gravar no OSCR (o seletor de tensao em 5V, como pede o OSCR Tool), pelo
# cabo USB, com o avrdude:
#
#   avrdude -p atmega2560 -c wiring -P /dev/ttyUSB0 -b 115200 -D -U flash:w:OSCR-HW5-fliperos.hex:i
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p output/oscr
dir=$(pwd)
command -v cygpath > /dev/null && dir=$(cygpath -w "$dir")
MSYS_NO_PATHCONV=1 docker run --rm -i -v "$dir:/w" -w /w ubuntu:24.04 bash -s << 'EOF'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends git ca-certificates curl > /dev/null
curl -fsSL https://downloads.arduino.cc/arduino-cli/arduino-cli_1.1.1_Linux_64bit.tar.gz | tar -xz -C /usr/local/bin arduino-cli
arduino-cli core update-index > /dev/null
arduino-cli core install arduino:avr > /dev/null
# As bibliotecas que o README do OSCR pede.
arduino-cli lib install SdFat U8g2 "Adafruit NeoPixel" RotaryEncoder "Etherkit Si5351" RTClib "Adafruit BusIO" > /dev/null
git init -q /tmp/oscr
git -C /tmp/oscr fetch -q --depth 1 https://github.com/sanni/cartreader 060d8ae0bf4be40bfc6a368bf6fbf7b594b3884d
git -C /tmp/oscr -c advice.detachedHead=false checkout -q FETCH_HEAD
git -C /tmp/oscr apply --whitespace=nowarn /w/patches/oscr/*.patch
for variant in hw5 hw5-vselect; do
  # O sketch numa pasta com o nome dele (Cart_Reader/Cart_Reader.ino).
  rm -rf /tmp/Cart_Reader /tmp/build
  cp -r /tmp/oscr/Cart_Reader /tmp/Cart_Reader
  config=/tmp/Cart_Reader/Config.h
  sed -i 's|^//#define HW5|#define HW5|' "$config"
  [[ $variant == hw5-vselect ]] && sed -i 's|^//#define ENABLE_VSELECT|#define ENABLE_VSELECT|' "$config"
  grep -q '^#define HW5' "$config"
  # O uso da flash e da RAM (o Mega tem 8 KB: o OSCR ja usa quase tudo).
  arduino-cli compile --fqbn arduino:avr:mega:cpu=atmega2560 --output-dir /tmp/build /tmp/Cart_Reader |
    grep -E 'Sketch uses|Global variables'
  name=OSCR-$(tr a-z A-Z <<< "$variant")-fliperos.hex
  cp /tmp/build/Cart_Reader.ino.hex "/w/output/oscr/$name"
  rm -rf /tmp/Cart_Reader
  echo "output/oscr/$name"
done
EOF
