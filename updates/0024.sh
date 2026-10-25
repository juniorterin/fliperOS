#!/usr/bin/env bash
# Update 24: o fliperos-padkeys novo so traduz o controle com o dono do
# /run/fliperos/padkeys vivo (o PID dentro dele). O servico ja rodando ainda
# e o antigo, que traduzia com qualquer arquivo: reiniciado, ele apaga o que
# um Setup morto deixou (o botao 2 saia como Esc nos jogos).
set -euo pipefail
systemctl try-restart fliperos-padkeys.service 2> /dev/null || true
