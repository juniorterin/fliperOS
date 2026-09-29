# Ambiente dos testes: o mesmo Ubuntu da ISO, com o mesmo awk (mawk) e jq
# que o fliperos-setup usa, mais o python3 que roda os testes.
#   docker build -t fliperos-tests -f tests/Dockerfile tests
#   docker run --rm -v "$PWD:/w" -w /w fliperos-tests python3 tests/test_setup.py
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 jq util-linux \
    && rm -rf /var/lib/apt/lists/*
