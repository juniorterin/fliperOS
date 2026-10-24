# O render do video de apresentacao (tools/video/render.sh): o ambiente dos
# prints da interface grafica (tools/Dockerfile.guitest, com o pygame), mais o
# ffmpeg (com a libass da legenda), o PIL, as fontes Noto e o sshpass para
# falar com o gabinete.
#   docker build -t fliperos-guitest -f tools/Dockerfile.guitest tools
#   docker build -t fliperos-video tools/video
FROM fliperos-guitest
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ffmpeg python3-pil fonts-noto-core fonts-dejavu-core openssh-client sshpass \
    && rm -rf /var/lib/apt/lists/*
