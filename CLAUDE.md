# fliperos — avisos importantes antes de mexer no build da ISO

O WSL2 NÃO suporta corretamente `chroot` + `debootstrap` com `mount --bind /dev` —
isso expõe o /dev real do host dentro do chroot, corrompe o /dev/null do host
(vira arquivo comum em vez de character device), e deixa mounts presos que
quebram a próxima tentativa. Isso já causou um loop de tentativas de
umount/mknod sem resolver a causa raiz.

Regras pra trabalhar nesse build:

1. NÃO rode `debootstrap`/`chroot` com bind-mount de `/dev` direto no WSL2.
   Se o script fizer isso, pare e proponha migrar o build pra Docker (um
   container isolado não tem esse problema de /dev do host vazando).
2. Se o `/dev/null` do host aparecer corrompido de novo (regular file em vez
   de character device — confira com `stat /dev/null`), isso é sinal de que
   algo já vazou do chroot. Pare o build imediatamente, não tente só
   re-`mknod` e rodar de novo.
3. Se a mesma categoria de erro (mount preso, /dev corrompido, umount
   falhando) se repetir 2 vezes seguidas, PARE e pergunte ao usuário antes de
   tentar uma terceira variação — não fique ciclando sozinho.
4. Não invoque skills de design ou qualquer coisa não relacionada a
   build/sistema pra essa tarefa.

# Docker Desktop neste Windows

O Docker cai quando o Windows fica sem memória comprometida (commit): erro
1455 ("arquivo de paginação muito pequeno") e "engine stopped unexpectedly"
no log. Em 2026-10-16 o commit chegou a 127,8 de 127,9 GB com só ~21 GB de
RAM em uso — memória reservada de VMs do WSL derrubadas à força, que só volta
reiniciando o Windows. Várias sessões do Claude dividem este Docker.

5. Antes de um job pesado (ISO, kernel, pacotes, as duas suítes de teste) e
   antes de reiniciar o Docker, rode
   `powershell -NoProfile -File tools\docker-health.ps1`. Saída 1 (commit
   acima de 85%): não comece nada pesado nem reinicie o Docker; avise o
   usuário que o Windows precisa reiniciar.
6. Um job pesado de Docker por vez, entre todas as sessões: confira
   `docker ps` antes. Dois builds pesados em paralelo derrubaram o Docker.
7. Nunca mate `com.docker.backend` nem rode `wsl --shutdown` para
   "destravar" o Docker: isso deixa outra VM com memória presa. Se ele não
   responde com memória sobrando, uma sessão só faz Quit pela bandeja e
   abre de novo, uma vez; se não voltar, pergunte ao usuário.
