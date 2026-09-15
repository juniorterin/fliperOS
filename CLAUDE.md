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
