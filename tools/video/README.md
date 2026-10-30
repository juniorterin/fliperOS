# Vídeo de apresentação

O vídeo que mostra o uso do FliperOS: instalação, primeiro boot, Setup, downloads, frontend e o painel web num tablet ao lado do tubo de verdade. São 1920x1080 a 30 fps, sem som, com legenda dupla (português em cima, inglês embaixo).

Tudo roda em Docker. O comando é `tools/video/render.sh`, e a saída fica em `.shots/video/out`:

- `fliperos-apresentacao.mp4`: o vídeo com a legenda gravada na imagem;
- `fliperos-apresentacao-sem-legenda.mp4`: o mesmo vídeo, sem legenda;
- `fliperos-apresentacao.pt-BR.srt` e `fliperos-apresentacao.en.srt`: as legendas para o YouTube.

## Do zero

```sh
sh tools/video/render.sh all 192.168.1.155
```

Ou etapa por etapa:

| Etapa | O que faz | Precisa do gabinete |
| --- | --- | --- |
| `images` | Cria as imagens `fliperos-guitest`, `fliperos-video` e `fliperos-video-web` | não |
| `library IP` | Copia do gabinete a biblioteca de amostra do frontend: jogos conhecidos com tela, capa, logo, marquee, vídeo e informação (~750 MB, em `.shots/video/demo.tar`) | sim |
| `scenes [CENA]` | Grava as cenas do CRT em `.shots/video/clips` (todas, ou só a cena dada) | não |
| `web IP` | Grava o painel web no tablet e, ao mesmo tempo, a tela do gabinete | sim |
| `gifs [CENA]` | Grava as animações do site que não são o painel (`tools/video/gifs/`): hoje o modo comercial, com duas fichas | não |
| `gifs-live IP` | Grava o painel web no desktop com o Street Fighter II rodando e os botões sendo apertados, e corta as animações do site | sim |
| `compose [TRECHO]` | Monta o vídeo (ou só um trecho, para conferir) | não |

Mudou só um texto? Basta rodar `compose` de novo. Mudou uma cena? Rode `scenes NOME` e depois `compose`.

## Onde está cada coisa

- **`script.py`** é o roteiro do vídeo:
  - `CARDS`: os cartões de abertura, de capítulo e de fim;
  - `SUBS`: as legendas de cada trecho, em PT e EN, com o tempo contado do começo do trecho;
  - `PLAN`: a ordem dos trechos e a duração de cada cartão;
  - `CLIPS`: a gravação de cada cena.
- **`scenes/`** tem uma cena por arquivo:
  - as do Setup (`def script(R)`) são telas de `fliperos-setup/gui`. Elas são gravadas em tempo virtual por `gui_rec.py`, com `R.push`, `R.key`, `R.type`, `R.wait`, `R.boot`...;
  - as do frontend (`TIMELINE`) são o `fliperos-frontend` de verdade, com a biblioteca de amostra e os vídeos dos jogos. Elas são gravadas em tempo real por `fe_rec.py`; cada linha é `(segundo, tecla)`.
- **`web_rec.py`** é o roteiro do painel web: o que o "dedo" toca e quando.
- **`compose.py`** cuida do visual: o fundo, as molduras do CRT e do tablet, as scanlines, os cartões e o estilo das legendas.

## A etapa `web`

Ela mexe no gabinete, então:

- deixe o gabinete no frontend, sem jogo aberto;
- tenha o `sf2.zip` em `~/roms/mame`.

Durante a gravação, o painel:

1. abre o Street Fighter II no gabinete;
2. leva a saturação a 0 e a 190, e depois a devolve ao valor de antes;
3. abre o terminal;
4. fecha o jogo.

A tela do gabinete é gravada no próprio gabinete, a partir da tela ao vivo do painel (go2rtc), por 190 s. Depois, `sync.py` alinha o tubo com o tablet pela abertura do SF2, que aparece nos dois.

## As animações do painel web para o site

`sh tools/video/render.sh gifs-live IP` grava `web-library`, `web-frontend`, `web-live`, `web-controller` e `web-settings` em `.shots/video/gifs`, prontas para `website/public/screenshots/anim`. Mexe no gabinete como a etapa `web`: abre o SF2 pelo painel, fecha no fim e deixa a saturação como estava.

Quem aperta os botões é o `vpad.py`, que roda no gabinete e cria um Xbox 360 virtual (uinput) por controle do Button mapping, com o mesmo VID/PID e os mesmos eixos de um xpad de verdade. O SDL numera os controles na ordem em que aparecem e o mapa fala em 0 e 1, então o `pads.sh` solta os Xbox 360 de verdade do driver `xpad` enquanto grava, e o `render.sh` os religa no fim, mesmo se a gravação falhar. O `fliperos-buttons watch` (o controle do OBS), a página do gabinete e o MAME enxergam os controles virtuais como os do painel de verdade.

- **`web_gifs.py`** é o roteiro: biblioteca (busca e Jogar), a página do gabinete, Ao vivo, o controle do OBS, os ajustes de cor e o fechamento do jogo. O lutador do SF2 está nele, com golpes longos o bastante para aparecerem a 12 quadros por segundo. `STOP_AT=marca` e `SKIP_PLAY=1` servem para ensaiar sem repetir tudo.
- **`web_gifs_cut.py`** corta cada par de marcas `nome:start` / `nome:end` em um WebP animado.
- **`gifs/commercial.py`** é a cena do frontend em modo comercial (`render.sh gifs commercial`, com a biblioteca de amostra e sem o gabinete): INSERT COIN, duas fichas com 2 s entre elas e o relógio.
