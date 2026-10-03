O que mais pesa no atraso entre apertar o botão e a imagem mudar é igual no FliperOS e no GroovyArcade: os mesmos patches de kernel (a mesma saída de vídeo no radeon/amdgpu), o mesmo Switchres e GroovyMAME, e o CRT, que não processa a imagem. O FliperOS aplica os ajustes que o GA já faz e acrescenta outros, em dois modos escolhidos em **Setup > Latency** (`fliperos-setup/lib/latency.sh`).

| Ajuste | GroovyArcade | FliperOS Standard | FliperOS Low latency |
| --- | --- | --- | --- |
| `mitigations=off audit=0` no kernel | sim | sim | sim |
| USB lido a 1000 Hz (`usbhid.jspoll=1 kbpoll=1 mousepoll=1`) | não | sim | sim |
| CPU no governador `performance` | enquanto o frontend roda | enquanto o frontend roda | sempre, desde o boot |
| Preempção do kernel | `linux-15khz` (há também um `linux-rt`) | 6.18 `PREEMPT_DYNAMIC`, modo voluntary | `preempt=full` |
| GroovyMAME `lowlatency 1`, `autoframedelay 1`, `framedelay 0` | `lowlatency` (o resto é padrão) | sim | sim |
| RetroArch `video_max_swapchain_images = 2` | sim | sim | sim |
| RetroArch `video_threaded` desligado, `input_poll_type_behavior = 2` | padrão | sim | sim |
| RetroArch frame delay automático | não | não | sim |
| RetroArch preemptive frames (1 quadro) | não | não | sim |
| apt e man-db rodando sozinhos | não existem (Arch) | mascarados | mascarados |

**O que cada ajuste faz:**

- **`mitigations=off audit=0`** — a linha padrão do GA. Desliga as proteções do kernel contra Spectre/Meltdown, que custam mais nas CPUs antigas (sem correção no hardware) típicas de gabinete. É troca de segurança por desempenho, aceitável numa máquina que só roda jogos.
- **USB a 1000 Hz** — um controle full-speed é lido a cada 8 ms (125 Hz); a espera média cai de ~4 ms para ~0,5 ms. Vale para o que usa o driver `usbhid` (encoders tipo Zero Delay/Xin-Mo, I-PAC como teclado, trackball); controles de Xbox usam o `xpad` e não mudam. Se algum controle se comportar mal, `usb_poll=default` no `/etc/fliperos/fliperos.conf` e aplicar o modo de novo volta ao polling original.
- **Governador `performance`** — o frame delay conta com um tempo fixo de emulação por quadro; com a CPU subindo o clock só depois que a carga aparece, esse tempo varia. No modo padrão vale só durante a sessão (o `fliperos-session` chama `fliperos-setup --session-start/--session-end`, como o `cpu_governor.sh` do galauncher); no de baixa latência, desde o boot (`fliperos-latency.service`).
- **`preempt=full`** — o kernel 6.18 do FliperOS é `PREEMPT_DYNAMIC`; com este parâmetro ele passa a interromper qualquer trabalho do kernel para rodar o emulador, o que o antigo kernel `lowlatency` do Ubuntu fazia. Reduz mais a variação (jitter) do que a média.
- **Frame delay** (`autoframedelay` do GroovyMAME, `video_frame_delay_auto` do RetroArch) — o emulador espera parte do quadro antes de emular, e lê os controles mais perto da hora em que a imagem sai: até quase um quadro (16,7 ms) a menos. O automático recua sozinho quando a CPU não dá conta.
- **Preemptive frames** — tira o atraso interno do próprio jogo (1 quadro), refazendo o último quadro só quando a entrada muda (mais leve que o run-ahead, que refaz todo quadro). Precisa de core com savestate; os que não têm desligam o recurso com aviso.
- **apt e man-db** — os timers do Ubuntu rodariam `apt update` e a reindexação do `man` no meio de uma partida. Atualizar fica no Setup > System Update, como no GA.

**O que ficou de fora, e por quê:** kernel `PREEMPT_RT` (o GA tem um `linux-rt`), porque o `preempt=full` cobre o uso de gabinete e o RT troca vazão por previsibilidade, que só vale com medição mostrando ganho; limitar os C-states da CPU, porque o ganho seria de microssegundos ao acordar a CPU, contra mais consumo e calor; e o `video_hard_sync` do RetroArch, porque no KMS a swapchain de 2 imagens já espera cada flip.

**Comparado com o GA:** no mesmo hardware, espere empate no modo Standard (com uma vantagem de poucos ms do USB a 1000 Hz) e até 1 a 2 quadros a menos nos jogos do RetroArch no modo Low latency. Um GA configurado à mão chega ao mesmo; a diferença é o FliperOS vir assim de fábrica.

## Hardware recomendado

| Uso | CPU | Memória e disco | GPU |
| --- | --- | --- | --- |
| **Standard** (até PS1 e a maior parte do arcade) | x86-64 com 2 núcleos | 4 GB, 16 GB de disco | AMD com saída VGA ou DVI-I, da faixa do CRT_EmuDriver (HD 2000 a R7/R9 GCN 1.0) |
| **Low latency** | AVX2 (x86-64-v3: Intel Core de 4ª geração, AMD Ryzen ou mais novos), 4 threads, 3,0 GHz ou mais | 4 GB (8 GB melhor) | idem |
| **Tudo** (PS2, Model 3, Dreamcast) | 4 núcleos físicos com AVX2 e single-thread PassMark ≥ 2000 (Core i7-7700, Ryzen 5 3600 ou mais novos) | 16 GB, SSD | idem: em resolução de CRT até a R7 240 passa do mínimo do PCSX2 (G3D ≥ 600) |

A faixa "Tudo" segue o nível *Moderate* dos [requisitos do PCSX2](https://pcsx2.net/docs/setup/requirements), o emulador mais pesado da ISO; a GPU mais forte que o PCSX2 pede nesse nível é para resolução aumentada, que não existe num CRT. Placas sem saída analógica (as AMD depois da GCN 1.0, as NVIDIA recentes) precisam de conversor DisplayPort/HDMI para VGA.

**Conferir a máquina:** Setup > Latency mostra CPU, núcleos, clock, nível de instruções, memória, GPU e as saídas analógicas, e **Check this computer** compara com o mínimo do modo Low latency (`lib/hardware.sh`: x86-64-v3, 4 threads, 3,0 GHz, 4 GB). Escolher Low latency numa máquina abaixo disso pede confirmação.

## Medir

A única comparação confiável é medir, no mesmo gabinete, o mesmo jogo e a mesma versão do emulador. Filme o botão e a tela juntos com um celular em câmera lenta de 240 fps (~4 ms por quadro de vídeo), 20 a 30 apertos por configuração, e conte os quadros do vídeo entre o botão descer e a imagem reagir.
