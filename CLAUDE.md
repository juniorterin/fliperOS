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
RAM em uso: o serviço RunSwUSB da Realtek (`C:\Windows\runSW.exe`, sobra de
um adaptador Wi-Fi USB) vazava handles (432 mil em 16 dias). O
`tools\docker-health.ps1` mostra um processo assim como VAZANDO. Várias
sessões do Claude dividem este Docker.

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
   abre de novo, uma vez; se não voltar, pergunte ao usuário. Saída 3 do
   `docker-health.ps1` é o próprio WSL travado: reabrir o Docker não
   resolve, pergunte ao usuário direto (o que resolve é reiniciar o serviço
   do WSL como admin, ou o Windows).

# Releases e updates

Uma ISO nova (tag X.Y) e o System Update têm de terminar no mesmo ponto: quem
instala a ISO e quem só aplica os updates precisam ficar com o mesmo sistema.
Em 2026-11-05 o 0.20 saiu 3 commits depois do update 39 (GroovyMAME em KMS,
RetroArch em Vulkan no amdgpu, R9 380): as máquinas no nível 39 ficaram sem
eles até existir o update 40.

8. Antes de marcar uma versão, publique o update que cobre tudo o que mudou no
   sistema desde o último (`updates/notes/NNNN.md` + `updates/index`, com o
   `tools/make-update.sh`) e marque a tag nesse mesmo commit, ou no seguinte
   sem nada que mexa em `fliperos-setup`, `config`, `packaging`, `patches` ou
   nos scripts de build.
9. Confira antes da tag: `git log --oneline ULTIMO_UPDATE..HEAD -- fliperos-setup
   config packaging patches fliperos-rootfs.sh fliperos-mkiso.sh` (ULTIMO_UPDATE
   é o commit da última linha de `updates/index`) tem de sair vazio. Se não
   sair, publique o update primeiro.
10. Uma mudança que só vale depois de gerar um arquivo (um EDID, o initramfs,
    um modprobe.d) precisa de um passo no update que o gere nas máquinas que já
    têm a configuração (como o `boot_apply` do `tools/cabinet-update.sh`):
    instalar os arquivos novos não basta.
