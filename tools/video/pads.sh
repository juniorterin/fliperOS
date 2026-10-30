#!/bin/bash
# No gabinete, como root: solta os controles Xbox 360 USB do driver xpad, ou os
# religa. O vpad.py cria controles virtuais no lugar deles (o SDL numera os
# controles na ordem em que aparecem, e o Button mapping fala em 0 e 1).
# Quem chama (render.sh gifs-live) sempre religa no fim.
#   pads.sh unbind | bind
LIST=/tmp/xpad-unbound
case ${1:-} in
  unbind)
    : > $LIST
    for d in /sys/bus/usb/drivers/xpad/[0-9]*:*; do
      [[ -e $d ]] && basename "$d" >> $LIST
    done
    while read -r i; do echo "$i" > /sys/bus/usb/drivers/xpad/unbind; done < $LIST
    echo "unbound: $(tr '\n' ' ' < $LIST)"
    ;;
  bind)
    [[ -f $LIST ]] || { echo "nothing to bind"; exit 0; }
    while read -r i; do echo "$i" > /sys/bus/usb/drivers/xpad/bind; done < $LIST
    rm -f $LIST
    echo "bound"
    ;;
  *) echo "Usage: pads.sh unbind|bind" >&2; exit 2 ;;
esac
