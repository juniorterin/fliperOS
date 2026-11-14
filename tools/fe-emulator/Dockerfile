# O emulador do frontend (tools/fe-emulator): o fliperos-frontend de verdade
# numa tela X de mentira (Xvfb), vista no navegador pelo noVNC. Roda em
# qualquer maquina com Docker, sem gabinete, sem placa e sem Python. O
# xdotool e o x11grab do ffmpeg apertam teclas e tiram prints sem navegador.
#   docker build -t fliperos-fe-emulator tools/fe-emulator
FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      python3 python3-pygame python3-pil ffmpeg jq util-linux \
      xvfb x11vnc novnc websockify xdotool \
    && rm -rf /var/lib/apt/lists/*
COPY start.sh fake-run lan-relay.py /emu/
# Os lancadores dos jogos (os unicos que o frontend aceita) sao o fake-run.
RUN chmod 755 /emu/start.sh /emu/fake-run /emu/lan-relay.py && mkdir -p /opt/fliperos/bin \
    && ln -s /emu/fake-run /opt/fliperos/bin/fliperos-x11-run && ln -s /emu/fake-run /opt/fliperos/bin/fliperos-kms-run
# 6080: o noVNC. 55436/udp: a presenca dos gabinetes da rede (lan-relay.py).
EXPOSE 6080 55436/udp
CMD ["/emu/start.sh"]
