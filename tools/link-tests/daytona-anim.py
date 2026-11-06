#!/usr/bin/env python3
"""A animacao do link de quatro gabinetes de corrida para o site: Daytona USA,
quatro gabinetes em forma de Formula 1 em pixel art (RaceCab de pixelcab.py,
os mesmos da sala RACE LINK da home) ligados em anel, como as placas de link
da Sega. As telas do frontend sao as reais (link-story.py daytona): o 1 escolhe
o jogo e abre o LINK PLAY, o jogo aparece no alto da lista dos outros, cada um
entra, o 1 aperta START e cada um abre o jogo com o numero do seu carro. O jogo
e o de verdade, quatro MAME ligados (daytona-link.sh): o boot de cada um ate o
"Network checking", o anel se fechando, e dai em diante as quatro telas juntas,
quadro a quadro, ate a corrida.

    docker run --rm -v "$PWD:/w" -v SHOTS:/shots:ro -v JOGO:/game:ro -v ARTE:/art:ro -v OUT:/out -w /w fliperos-video \\
        python3 tools/link-tests/daytona-anim.py /shots /game /art /out

JOGO: a saida do daytona-link.sh (cab1..cab4/daytona/NNNN.png e cabN.log, cujas
linhas SHOT dao o quadro de cada PNG, contado do link pronto). ARTE: a ~/media
do gabinete (logo/model2/daytona.png vai no letreiro). Saida: daytona-pt.webp,
daytona-en.webp e os .gif de mesmo nome, 1200x900 (4:3).
PREVIEW=2,9.5,16 grava so esses instantes (daytona-pt-<t>.png).
"""
import math
import os
import shutil
import sys
import tempfile

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixelcab import (C, W, H, RaceCab, at, background, bezier, caption, chain, crt, draw_cables, encode, font, label,
                      paste_logo, race_live, racer, screen_mask, trip)

SHOTS, GAME, ART, OUT = sys.argv[1:5]
PX = 4
LW, LH = W // PX, H // PX
FPS = 12.5
GAME_FPS = 57.5                                   # o Model 2

STEPS = {
    "pt": ["O gabinete 1 escolhe o Daytona USA e abre o LINK PLAY",
           "O jogo aparece no alto da lista dos outros gabinetes",
           "O gabinete 2 entra e copia o jogo pelo cabo",
           "O gabinete 3 entra",
           "O gabinete 4 entra e o 1 aperta START",
           "Cada um abre o jogo com o número do seu carro",
           "O anel acha os quatro: até 4 jogadores",
           "Ficha e START: a mesma escolha de pista nos quatro",
           "A corrida: quatro carros, cada tela no seu"],
    "en": ["Cabinet 1 picks Daytona USA and opens LINK PLAY",
           "The game shows up at the top of the other cabinets' lists",
           "Cabinet 2 joins and copies the game over the cable",
           "Cabinet 3 joins",
           "Cabinet 4 joins and cabinet 1 presses START",
           "Each opens the game with its own car number",
           "The ring finds all four: up to 4 players",
           "Coin and START: the same circuit select on all four",
           "The race: four cars, each screen on its own"],
}

# Os quatro lado a lado, com um vao de dois pixels; o anel: os cabos de um ao
# seguinte e um cabo comprido de volta do 4 ao 1, deitado na frente.
CABS = [RaceCab(39 + 74 * i, 36, 54, 198, (64, 48), i + 1) for i in range(4)]
FLOOR = CABS[0].floor
CABLES = chain(CABS) + [bezier((CABS[3].cx + 14, FLOOR + 1), (CABS[0].cx - 14, FLOOR + 1), FLOOR + 19)]

# ── O roteiro ─────────────────────────────────────────────────────
JOIN = [(6.6, 9.4), (9.6, 12.2), (12.4, 15.0)]   # cada um que entra: comeca a agir, entra na sala
T_PRESS = 15.3                                    # o 1 aperta START
T_COUNT = 15.6
K = 0.12                                          # a contagem: 0,5 s reais por quadro, comprimida
BOOT = 0.4                                        # cada tela do boot (uma a cada 120 quadros do jogo)
# Os trechos do jogo, todos juntos depois do link: (de, ate, passo), em
# quadros contados do link pronto; o passo e quantos quadros gravados andam
# por quadro da animacao (1 = tempo real com um PNG a cada 5 quadros). Na
# gravacao do daytona-link.sh (EVERY=5 END=5000): a tela "4 jogadores" dos
# quatro (do quadro ~60), a ficha no 600, a escolha de pista com a mesma
# contagem nos quatro (700 a 1550) e a corrida, todos ja correndo (3000 em
# diante). A largada nao entra: o master largou alguns segundos depois.
SEGMENTS = [(int(a), int(b), float(c)) for a, b, c in
            (s.split(":") for s in os.environ.get("SEGMENTS", "1:590:3,590:700:2,700:1550:5,3000:3550:1").split(","))]
T_COIN_SEG = int(os.environ.get("COIN_SEG", "1"))  # o trecho em que entra a ficha (o passo 8)
T_RACE_SEG = int(os.environ.get("RACE_SEG", "3"))  # o trecho da corrida (o passo 9)


def frontend_screens(launch):
    """As telas do frontend de cada gabinete: (inicio, imagem)."""
    a = [(0.0, "a-list-0"), (0.5, "a-list-1"), (1.0, "a-list-2"), (1.5, "a-list-3"), (2.5, "a-popup-0"),
         (3.4, "a-popup-1"), (4.4, "a-wait-0")]
    out = [a]
    for i, side in enumerate("bcd"):
        s, e = JOIN[i]
        out.append([(0.0, side + "-list-0"), (5.6, side + "-list-1"), (s, side + "-list-2"), (s + 0.6, side + "-popup-0"),
                    (s + 1.0, side + "-popup-1")] + [(s + 1.6 + k * 0.3, "%s-copy-%d" % (side, k)) for k in range(4)])
    for i, side in enumerate("abcd"):
        for j, (s, e) in enumerate(JOIN):
            if j + 1 >= i:
                out[i].append((e, "%s-join-%d" % (side, j + 1)))
        out[i] += [(T_COUNT + k * K, "%s-start-%d" % (side, k)) for k in range(launch[i])]
    return out


PRESSES = [[(0.5, "up"), (1.0, "up"), (1.5, "up"), (2.5, "a"), (3.4, "right"), (4.4, "a"), (T_PRESS, "a")]]
PRESSES += [[(s, "up"), (s + 0.6, "a"), (s + 1.0, "right"), (s + 1.6, "a")] for s, e in JOIN]


def launches():
    """O quadro da contagem em que cada gabinete abre o jogo: o STARTING
    (verde, embaixo das oito vagas) some."""
    out = []
    for side in "abcd":
        k = 0
        while os.path.isfile(os.path.join(SHOTS, "%s-start-%d.png" % (side, k))):
            im = Image.open(os.path.join(SHOTS, "%s-start-%d.png" % (side, k))).convert("RGB").crop((60, 174, 260, 190))
            if not any(g > 200 and r < 140 and b < 160 for r, g, b in im.getdata()) and k > 0:
                break
            k += 1
        out.append(k)
    return out


def recording(i):
    """O jogo do gabinete i: as telas do boot (antes do link, na ordem) e as
    depois do link ({quadro: arquivo})."""
    folder = os.path.join(GAME, "cab%d" % (i + 1), "daytona")
    files = sorted(os.listdir(folder))
    shots = [int(l.split()[1]) for l in open(os.path.join(GAME, "cab%d.log" % (i + 1))) if l.startswith("SHOT ")]
    boot, after = [], {}
    for n, f in zip(shots, files):
        if n < 0:
            im = Image.open(os.path.join(folder, f)).convert("L")
            if max(im.getdata()) > 40:            # as telas pretas do comeco do boot ficam de fora
                boot.append(os.path.join(folder, f))
        else:
            after[n] = os.path.join(folder, f)
    return boot, after


def ring(t, start, color, per=0.3, laps=1):
    """Um pacote dando a volta no anel a partir do 1: os tres cabos da fileira
    e o cabo comprido de volta (cabo 3, que vai do 4 ao 1)."""
    if t < start:
        return []
    k = int((t - start) // per)
    if k >= 4 * laps:
        return []
    p = ((t - start) - k * per) / per
    return [(k % 4, p, color)]


def main():
    launch = launches()
    print("launch frames", launch)
    t_launch = [T_COUNT + k * K for k in launch]
    recs = [recording(i) for i in range(4)]
    t_link = max(t_launch[i] + BOOT * len(recs[i][0]) for i in range(4)) + 0.6
    seg_t = [t_link]                              # o inicio de cada trecho na animacao
    for a, b, step in SEGMENTS:
        seg_t.append(seg_t[-1] + (b - a) / 5 / step / FPS)
    end = seg_t[-1]
    loop = 0.8
    screens = frontend_screens(launch)
    steps = [(0.0, 0), (4.4, 1), (JOIN[0][0], 2), (JOIN[1][0], 3), (JOIN[2][0], 4), (T_COUNT, 5), (t_link - 1.6, 6),
             (seg_t[T_COIN_SEG], 7), (seg_t[T_RACE_SEG], 8)]
    acting = [(0.0, 0), (JOIN[0][0], 1), (JOIN[1][0], 2), (JOIN[2][0], 3), (T_PRESS - 0.2, 0), (T_COUNT, None)]
    size = (CABS[0].scr[0] * PX, CABS[0].scr[1] * PX)
    mask = screen_mask(CABS[0].scr, PX)
    logo = Image.open(os.path.join(ART, "logo", "model2", "daytona.png")).convert("RGBA")
    cache = {}

    def shot(name):
        if name not in cache:
            im = Image.open(os.path.join(SHOTS, name + ".png")).convert("RGB")
            cache[name] = crt(im.resize((im.width * 2, im.height * 2), Image.NEAREST), size)
        return cache[name]

    def picture(path):
        if path not in cache:
            cache[path] = crt(Image.open(path).convert("RGB"), size)
        return cache[path]

    def game_frame(i, t):
        """O jogo do gabinete i: o boot dele ate o anel fechar; depois, todos
        no mesmo quadro."""
        boot, after = recs[i]
        if t < t_link:
            k = min(len(boot) - 1, int((t - t_launch[i]) / BOOT))
            return picture(boot[k])
        s = max(j for j in range(len(SEGMENTS)) if t >= seg_t[j]) if t < end else len(SEGMENTS) - 1
        a, b, step = SEGMENTS[s]
        f = min(b, a + int((t - seg_t[s]) * FPS * step) * 5)
        near = min(after, key=lambda n: abs(n - f))
        return picture(after[near])

    def pulses(t):
        out = []
        for k in range(2):                       # o anuncio da festa, do 1 para todos
            for dst in (1, 2, 3):
                out += trip(t, 4.6 + k * 0.5, 0, dst, C["cyan"], 0.3)
        for j, (s, e) in enumerate(JOIN):        # cada entrada: o pedido e a copia
            out += trip(t, s + 1.6, j + 1, 0, C["pink"], 0.3)
            for k in range(10):
                out += trip(t, s + 1.7 + k * 0.1, 0, j + 1, C["green"], 0.25)
        for k in range(3):                       # o master conta as maquinas do anel
            out += ring(t, t_link - 1.6 + k * 0.4, C["cyan"])
        if t >= t_link:                          # o jogo: um quadro dando a volta o tempo todo
            k = 0
            while t_link + k * 0.3 <= t:
                out += ring(t, t_link + k * 0.3, C["green"] if k % 2 else C["pink"], 0.3)
                k += 1
        return out

    f_cap, f_num, f8 = font(24), font(24), font(8)
    bases = {lit: background(LW, LH, CABS, lit, draw=racer) for lit in (None, 0, 1, 2, 3)}
    for im in bases.values():                    # o letreiro neon na parede, em cima da fileira
        d = ImageDraw.Draw(im)
        d.fontmode = "1"
        sign = "RACE LINK"
        x = (LW - int(d.textlength(sign, font=f8))) // 2
        d.rectangle((x - 6, 34, LW - x + 5, 45), fill=C["ink"], outline=C["comment"])
        d.text((x + 1, 37), sign, font=f8, fill=C["comment"])
        d.text((x, 36), sign, font=f8, fill=C["cyan"])
    t_race = seg_t[T_RACE_SEG]
    preview = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
    work = tempfile.mkdtemp()
    for lang in ("pt",) if preview else ("pt", "en"):
        frames = os.path.join(work, lang)
        os.makedirs(frames)
        n = int(math.ceil((end + loop) * FPS))
        first = None
        for f in ([int(p * FPS) for p in preview] if preview else range(n)):
            t = f / FPS
            tt = min(t, end)
            low = bases[at(acting, tt)].copy()
            d = ImageDraw.Draw(low)
            d.fontmode = "1"
            draw_cables(d, CABLES, pulses(tt))
            scrs, logos = [], []
            racing = tt >= t_race
            for i, cab in enumerate(CABS):
                playing = tt >= t_launch[i]
                scrs.append(game_frame(i, tt) if playing else shot(at(screens[i], tt)))
                press = next((k for when, k in PRESSES[i] if when <= tt < when + 0.3), None)
                box = race_live(d, cab, playing, str(i + 1), f8, press, roll=f if racing else 0,
                                light=racing and (f // 3) % 2 == 0)
                if playing:
                    logos.append(box)
                label(d, cab, "P%d" % (i + 1))
            im = low.resize((W, H), Image.NEAREST)
            for i, cab in enumerate(CABS):
                im.paste(scrs[i], cab.screen_box(PX), mask)
            for box in logos:
                paste_logo(im, logo, box, PX)
            k = at(steps, tt)
            caption(im, STEPS[lang][k], k, len(STEPS[lang]), f_cap, f_num)
            if f == 0:
                first = im
            if t > end:                          # a volta: funde com o primeiro quadro
                im = Image.blend(im, first, min(1.0, (t - end) / loop))
            im.save(os.path.join(OUT, "daytona-pt-%g.png" % t) if preview else os.path.join(frames, "%04d.png" % f))
        if preview:
            break
        webp, gif = (os.path.join(OUT, "daytona-%s.%s" % (lang, ext)) for ext in ("webp", "gif"))
        encode(os.path.join(frames, "%04d.png"), webp, gif, FPS)
        shutil.copyfile(os.path.join(frames, "%04d.png" % int((t_race + 3) * FPS)),
                        os.path.join(OUT, "daytona-%s-still.png" % lang))
        print(lang, n, "frames", os.path.getsize(webp) // 1024, "KB webp", os.path.getsize(gif) // 1024, "KB gif")
    shutil.rmtree(work)


if __name__ == "__main__":
    main()
