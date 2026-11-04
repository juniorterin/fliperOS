#!/usr/bin/env python3
"""A animacao do link de quatro gabinetes para o site: Super Street Fighter II:
The Tournament Battle, em pixel art (pixelcab.py), quatro gabinetes numa
corrente de cabos como a do jogo. As telas do frontend sao as reais
(link-story.py ssf2tb): o 1 escolhe o jogo e abre o LINK PLAY, o jogo aparece no
alto da lista dos outros, cada um entra, e cada um abre o jogo seis segundos
depois do anterior. O jogo e o de verdade, quatro MAME ligados
(ssf2tb-tournament.sh): o titulo, a tela de entrada dos oito lugares, a chave do
torneio (diferente em cada maquina) e as quatro lutas ao mesmo tempo.

    docker run --rm -v "$PWD:/w" -v SHOTS:/shots:ro -v JOGO:/game:ro -v OUT:/out -w /w fliperos-video \\
        python3 tools/link-tests/ssf2tb-anim.py /shots /game /out

JOGO: a saida do ssf2tb-tournament.sh (cab1..cab4/ssf2tb/NNNN.png, 12 por segundo).
Saida: ssf2tb-pt.webp, ssf2tb-en.webp e os .gif de mesmo nome, 1200x900 (4:3).
PREVIEW=2,9.5,16 grava so esses instantes (ssf2tb-pt-<t>.png).
"""
import math
import os
import shutil
import sys
import tempfile

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixelcab import (C, W, H, Cab, at, background, caption, chain, controls, crt, draw_cables, encode, font, label,
                      marquee, paste_logo, screen_mask, trip)

SHOTS, GAME, OUT = sys.argv[1:4]
PX = 4
LW, LH = W // PX, H // PX
FPS = 12.5

STEPS = {
    "pt": ["O gabinete 1 escolhe o Tournament Battle e abre o LINK PLAY",
           "O jogo aparece no alto da lista dos outros gabinetes",
           "O gabinete 2 entra e copia o jogo pelo cabo",
           "O gabinete 3 entra",
           "O gabinete 4 entra: a sala está cheia",
           "Cada um abre o jogo, um após o outro",
           "O torneio: cada máquina mostra a sua chave",
           "Quatro lutas ao mesmo tempo, oito lutadores"],
    "en": ["Cabinet 1 picks Tournament Battle and opens LINK PLAY",
           "The game shows up at the top of the other cabinets' lists",
           "Cabinet 2 joins and copies the game over the cable",
           "Cabinet 3 joins",
           "Cabinet 4 joins: the lobby is full",
           "Each opens the game, one after another",
           "The tournament: each machine shows its own bracket",
           "Four fights at once, eight fighters"],
}
SLOTS = ["P1-2", "P3-4", "P5-6", "P7-8"]
# As cores dos oito lugares do jogo (a tela de entrada): uma alavanca de cada.
BALLS = [((255, 85, 85), (98, 114, 255)), ((241, 250, 140), (80, 250, 123)),
         ((189, 147, 249), (139, 233, 253)), ((255, 184, 108), (200, 200, 210))]

CABS = [Cab(39 + 74 * i, 35, 46, 198, (64, 48), side=0, socket="front") for i in range(4)]
CABLES = chain(CABS, 222)

# ── O roteiro ─────────────────────────────────────────────────────
JOIN = [(6.6, 9.4), (9.6, 12.2), (12.4, 15.0)]   # cada um que entra: comeca a agir, entra na sala
T_COUNT = 15.0
K = 0.12                                          # a contagem: 0,5 s reais por quadro, comprimida
T_ENTRY = None                                    # calculado: quando o ultimo abre o jogo
TITLE, ENTRY, BRACKET, FIGHT = (0, 30), (80, 110), (300, 392), (392, 452)   # trechos da gravacao


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


PRESSES = [[(0.5, "down"), (1.0, "down"), (1.5, "down"), (2.5, "a"), (3.4, "right"), (4.4, "a")]]
PRESSES += [[(s, "up"), (s + 0.6, "a"), (s + 1.0, "right"), (s + 1.6, "a")] for s, e in JOIN]


def launches():
    """O quadro da contagem em que cada gabinete abre o jogo: o STARTING (verde) some."""
    out = []
    for side in "abcd":
        k = 0
        while os.path.isfile(os.path.join(SHOTS, "%s-start-%d.png" % (side, k))):
            im = Image.open(os.path.join(SHOTS, "%s-start-%d.png" % (side, k))).convert("RGB").crop((60, 118, 260, 132))
            if not any(g > 200 and r < 140 and b < 160 for r, g, b in im.getdata()) and k > 0:
                break
            k += 1
        out.append(k)
    return out


def main():
    global T_ENTRY
    launch = launches()
    print("launch frames", launch)
    t_launch = [T_COUNT + k * K for k in launch]
    T_ENTRY = t_launch[-1] + 1.6
    t_bracket = T_ENTRY + (ENTRY[1] - ENTRY[0]) / FPS
    t_fight = t_bracket + (BRACKET[1] - BRACKET[0]) / FPS
    end = t_fight + (FIGHT[1] - FIGHT[0]) / FPS
    loop = 0.8
    screens = frontend_screens(launch)
    steps = [(0.0, 0), (4.4, 1), (JOIN[0][0], 2), (JOIN[1][0], 3), (JOIN[2][0], 4), (T_COUNT, 5), (t_bracket, 6),
             (t_fight, 7)]
    acting = [(0.0, 0), (JOIN[0][0], 1), (JOIN[1][0], 2), (JOIN[2][0], 3), (T_COUNT, None)]
    games = [sorted(os.listdir(os.path.join(GAME, "cab%d" % (i + 1), "ssf2tb"))) for i in range(4)]
    size = (CABS[0].scr[0] * PX, CABS[0].scr[1] * PX)
    mask = screen_mask(CABS[0].scr, PX)
    # O logo do letreiro: o da tela de titulo gravada (o do Tournament Battle; a
    # arte do gabinete so tem o do Super Street Fighter II comum), sem o preto.
    title = Image.open(os.path.join(GAME, "cab4", "ssf2tb", games[3][15])).convert("RGB").crop((28, 10, 356, 172))
    logo = title.convert("RGBA")
    logo.putalpha(title.convert("L").point(lambda v: 255 if v > 24 else 0))
    cache = {}

    def shot(name):
        if name not in cache:
            im = Image.open(os.path.join(SHOTS, name + ".png")).convert("RGB")
            cache[name] = crt(im.resize((im.width * 2, im.height * 2), Image.NEAREST), size)
        return cache[name]

    def game_frame(i, t):
        """O jogo do gabinete i: o titulo (do seu proprio boot) ate todos
        abrirem; depois, todos juntos, a entrada, a chave e as lutas."""
        if t < T_ENTRY:
            k = TITLE[0] + int((t - t_launch[i]) * FPS) % (TITLE[1] - TITLE[0])
        elif t < t_bracket:
            k = ENTRY[0] + int((t - T_ENTRY) * FPS)
        elif t < t_fight:
            k = BRACKET[0] + int((t - t_bracket) * FPS)
        else:
            k = min(FIGHT[1], FIGHT[0] + int((t - t_fight) * FPS))
        key = "g%d:%d" % (i, k)
        if key not in cache:
            cache[key] = crt(Image.open(os.path.join(GAME, "cab%d" % (i + 1), "ssf2tb", games[i][k])).convert("RGB"), size)
        return cache[key]

    def pulses(t):
        out = []
        for k in range(2):                       # o anuncio da festa, do 1 para todos
            for dst in (1, 2, 3):
                out += trip(t, 4.6 + k * 0.5, 0, dst, C["cyan"], 0.3)
        for j, (s, e) in enumerate(JOIN):        # cada entrada: o pedido e a copia
            out += trip(t, s + 1.6, j + 1, 0, C["pink"], 0.3)
            for k in range(10):
                out += trip(t, s + 1.7 + k * 0.1, 0, j + 1, C["green"], 0.25)
        if t >= T_ENTRY:                         # o jogo: a corrente conversando o tempo todo
            k = 0
            while T_ENTRY + k * 0.25 <= t:
                c = k % 3
                out += trip(t, T_ENTRY + k * 0.25, c, c + 1, C["green"], 0.3) if k % 2 == 0 else \
                    trip(t, T_ENTRY + k * 0.25, c + 1, c, C["pink"], 0.3)
                k += 1
        return out

    f_cap, f_num, f8 = font(24), font(24), font(8)
    bases = {lit: background(LW, LH, CABS, lit) for lit in (None, 0, 1, 2, 3)}
    for im in bases.values():                    # o letreiro neon na parede, em cima da fileira
        d = ImageDraw.Draw(im)
        d.fontmode = "1"
        sign = "TOURNAMENT BATTLE"
        x = (LW - int(d.textlength(sign, font=f8))) // 2
        rect = (x - 6, 32, LW - x + 5, 43)
        d.rectangle(rect, fill=C["ink"], outline=C["wainlo"])
        d.text((x + 1, 35), sign, font=f8, fill=C["wainlo"])
        d.text((x, 34), sign, font=f8, fill=C["pink"])
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
            for i, cab in enumerate(CABS):
                playing = tt >= t_launch[i]
                scrs.append(game_frame(i, tt) if playing else shot(at(screens[i], tt)))
                box = marquee(d, cab, "#%d" % (i + 1), playing, f8)
                if playing and logo is not None:
                    logos.append(box)
                label(d, cab, SLOTS[i], f8)
                press = next((k for when, k in PRESSES[i] if when <= tt < when + 0.3), None)
                controls(d, cab, press, BALLS[i])
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
            im.save(os.path.join(OUT, "ssf2tb-pt-%g.png" % t) if preview else os.path.join(frames, "%04d.png" % f))
        if preview:
            break
        webp, gif = (os.path.join(OUT, "ssf2tb-%s.%s" % (lang, ext)) for ext in ("webp", "gif"))
        encode(os.path.join(frames, "%04d.png"), webp, gif, FPS)
        shutil.copyfile(os.path.join(frames, "%04d.png" % int((t_bracket + 3) * FPS)),
                        os.path.join(OUT, "ssf2tb-%s-still.png" % lang))
        print(lang, n, "frames", os.path.getsize(webp) // 1024, "KB webp", os.path.getsize(gif) // 1024, "KB gif")
    shutil.rmtree(work)


if __name__ == "__main__":
    main()
