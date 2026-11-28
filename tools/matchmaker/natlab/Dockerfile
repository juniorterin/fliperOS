# The Matchmaker's NAT lab (tools/matchmaker/natlab/natlab.sh): two cabinets
# behind their own routers, the real Matchmaker server, a STUN and a TURN
# (coturn) on the lab's "internet", all in network namespaces of one
# privileged container. WireGuard comes from the host's kernel.
FROM ubuntu:24.04
RUN apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends \
      python3 python3-pip wireguard-tools iproute2 iptables iputils-ping coturn procps \
    && pip3 install --break-system-packages -q websockets==15.0.1 cryptography==46.0.3 \
    && rm -rf /var/lib/apt/lists/*
