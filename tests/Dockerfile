# Ambiente dos testes: o mesmo Ubuntu da ISO, com o mesmo awk (mawk) e jq
# que o fliperos-setup usa, mais o python3 que roda os testes, o git dos
# testes do fliperos-sm2emu e o curl dos downloads do fliperos-outputs (os
# testes baixam por file://). O xz dos testes que abrem os pacotes do
# RetroArch, o Pillow, o fontTools e a DejaVu dos que desenham (DMD,
# capturas, a arte e os logotipos do Arcadeflow) e o markdown do
# tools/render-docs.py: a mesma imagem roda o test_setup.py e o test_build.py.
#   docker build -t fliperos-tests -f tests/Dockerfile tests
#   docker run --rm -v "$PWD:/w" -w /w fliperos-tests python3 tests/test_setup.py
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 jq util-linux git curl ca-certificates xz-utils python3-pil python3-markdown \
      python3-fonttools fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
