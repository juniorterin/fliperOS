#!/bin/bash
# The Matchmaker's NAT lab: does the party tunnel (fliperos-setup/gui/fetunnel.py)
# find its way between two cabinets behind their own routers, and use the
# relay only when there is no other way?
#
#   docker build -t fliperos-natlab tools/matchmaker/natlab
#   MSYS_NO_PATHCONV=1 docker run --rm --privileged -v "$(pwd -W):/w:ro" fliperos-natlab \
#       bash /w/tools/matchmaker/natlab/natlab.sh [eim|symmetric|samehouse ...]
#
# The "internet" is a bridge (203.0.113.0/24) with the real Matchmaker server
# (ws://203.0.113.2:8080), a STUN responder (:3479) and coturn (:3478, the
# lab's stand-in for Cloudflare's TURN). Each cabinet sits behind a Linux
# router that masquerades (eim: keeps the port, the common home router;
# symmetric: --random-fully, a new port per destination, like many CGNATs).
#   eim        both behind ordinary NATs       -> direct
#   symmetric  both behind symmetric NATs      -> relay
#   samehouse  both behind the same router     -> direct, by the LAN address
set -uo pipefail
REPO=/w
LAB=$REPO/tools/matchmaker/natlab
STATE=/tmp/natlab
fails=0

ns() { ip netns exec "$@"; }

cleanup() {
  pkill -f natlab_cab.py 2> /dev/null
  pkill -f natlab_server.py 2> /dev/null
  pkill -x turnserver 2> /dev/null
  sleep 0.3
  for n in cab1 cab2 r1 r2 inet; do ip netns del "$n" 2> /dev/null; done
  rm -rf "$STATE"
}

router() { # router NAME PUBLIC LAN_PREFIX MODE
  local r=$1 pub=$2 lan=$3 mode=$4
  ip netns add "$r"
  ip link add "${r}w" type veth peer name "${r}i"
  ip link set "${r}w" netns "$r"
  ip link set "${r}i" netns inet
  ns inet ip link set "${r}i" master br0 up
  ns "$r" ip addr add "$pub/24" dev "${r}w"
  ns "$r" ip link set "${r}w" up
  ns "$r" ip link set lo up
  ns "$r" sysctl -qw net.ipv4.ip_forward=1
  local extra=()
  [[ $mode == symmetric ]] && extra=(--random-fully)
  ns "$r" iptables -t nat -A POSTROUTING -o "${r}w" -j MASQUERADE "${extra[@]}"
  # The firewall of a home router: nothing new comes in from the WAN. Without
  # it, an early handshake from the other cabinet is "confirmed" by conntrack
  # as traffic to the router itself, and the cabinet's own packet to it then
  # leaves with another port (a clash): no direct path. A real router drops
  # that packet before conntrack confirms it.
  ns "$r" iptables -A INPUT -i "${r}w" -m conntrack --ctstate NEW -j DROP
  ns "$r" iptables -A FORWARD -i "${r}w" -m conntrack --ctstate NEW -j DROP
}

cabinet() { # cabinet NAME ROUTER LAN_PREFIX
  local c=$1 r=$2 lan=$3
  ip netns add "$c"
  ip link add "${c}r" type veth peer name "${c}l"
  ip link set "${c}r" netns "$r"
  ip link set "${c}l" netns "$c"
  ns "$r" ip addr add "$lan.1/24" dev "${c}r"
  ns "$r" ip link set "${c}r" up
  ns "$c" ip addr add "$lan.10/24" dev "${c}l"
  ns "$c" ip link set "${c}l" up
  ns "$c" ip link set lo up
  ns "$c" ip route add default via "$lan.1"
}

scenario() {
  local name=$1 expect=$2
  echo "=== $name (expect $expect)"
  cleanup
  mkdir -p "$STATE"
  ip netns add inet
  ns inet ip link add br0 type bridge
  ns inet ip addr add 203.0.113.2/24 dev br0
  ns inet ip link set br0 up
  ns inet ip link set lo up
  case $name in
    eim)       router r1 203.0.113.11 x eim; router r2 203.0.113.12 x eim
               cabinet cab1 r1 192.168.1; cabinet cab2 r2 192.168.2 ;;
    symmetric) router r1 203.0.113.11 x symmetric; router r2 203.0.113.12 x symmetric
               cabinet cab1 r1 192.168.1; cabinet cab2 r2 192.168.2 ;;
    samehouse) router r1 203.0.113.11 x eim
               cabinet cab1 r1 192.168.1; cabinet cab2 r1 192.168.3 ;;
  esac
  ns inet turnserver -n --listening-ip=203.0.113.2 --relay-ip=203.0.113.2 --listening-port=3478 \
    --lt-cred-mech --user=lab:lab --realm=lab --no-tls --no-dtls --fingerprint \
    --min-port=49152 --max-port=49999 --no-cli --log-file=stdout > "$STATE/turn.log" 2>&1 &
  ns inet python3 "$LAB/natlab_server.py" "$REPO" 203.0.113.2 > "$STATE/server.log" 2>&1 &
  for _ in $(seq 50); do grep -q "server ready" "$STATE/server.log" && break; sleep 0.1; done
  ns cab1 python3 "$LAB/natlab_cab.py" "$REPO" 203.0.113.2 host CABONE "$STATE" > "$STATE/cab1.log" 2>&1 &
  local p1=$!
  ns cab2 python3 "$LAB/natlab_cab.py" "$REPO" 203.0.113.2 guest CABTWO "$STATE" > "$STATE/cab2.log" 2>&1 &
  local p2=$!
  wait $p1; local r1=$?
  wait $p2; local r2=$?
  cat "$STATE/cab1.log" "$STATE/cab2.log"
  local ok=1
  ((r1 == 0 && r2 == 0)) || ok=0
  grep -q "] PATH $expect" "$STATE/cab1.log" || ok=0
  grep -q "] PATH $expect" "$STATE/cab2.log" || ok=0
  [[ $name != samehouse ]] || grep -q "] PATH direct 192.168" "$STATE/cab2.log" || ok=0
  grep -q "ECHO ok" "$STATE/cab2.log" || ok=0
  if ((ok)); then
    echo "--- $name: PASS"
  else
    echo "--- $name: FAIL"
    tail -n 20 "$STATE/server.log" "$STATE/turn.log"
    fails=$((fails + 1))
  fi
}

declare -A expect=([eim]=direct [symmetric]=relay [samehouse]=direct)
for s in "${@:-eim symmetric samehouse}"; do
  for one in $s; do
    scenario "$one" "${expect[$one]}"
  done
done
cleanup
echo "=== natlab: $fails failed"
exit $((fails > 0))
