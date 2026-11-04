#!/usr/bin/env python3
"""A animacao do net play para o site: dois gabinetes candy em pixel art (pixelcab.py)
ligados por um cabo de rede, com as telas REAIS do frontend (link-story.py
netplay) e o jogo rodando (o video de previa do gabinete). O gabinete 1 escolhe
o Escape Kids e abre a festa, espera; o gabinete 2 ve o jogo no alto da lista,
entra, copia o jogo e os dois jogam. Pulsos andam no cabo quando passa algo pela
rede.

    docker run --rm -v "$PWD:/w" -v SHOTS:/shots:ro -v ARTE:/art:ro -v OUT:/out -w /w fliperos-video \\
        python3 tools/link-tests/netplay-anim.py /shots /art /art/esckids.mp4 /out

Saida: netplay-pt.webp, netplay-en.webp e os .gif de mesmo nome, 1200x900 (4:3).
PREVIEW=2,9.5,16 grava so esses instantes (netplay-pt-<t>.png), para acertar o desenho.
"""
import math
import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixelcab import (C, W, H, Cab, at, background, caption, chain, controls, crt, draw_cables, encode, font, label,
                      marquee, paste_logo, screen_mask, trip)

SHOTS, ART, VIDEO, OUT = sys.argv[1:5]
PX = 5                   # cada pixel da arte vira PX x PX
LW, LH = W // PX, H // PX
FPS = 12.5
GAME_FROM = 2.0          # segundos do video em que o jogo ja esta correndo

STEPS = {
    "pt": ["O gabinete 1 escolhe Escape Kids e abre o NET PLAY",
           "Esperando outro gabinete",
           "O gabinete 2 vê o jogo no alto da lista e entra",
           "Ele copia o jogo pelo cabo",
           "Os dois na sala: o jogo começa",
           "Jogando juntos: P1-P2 aqui, P3-P4 lá"],
    "en": ["Cabinet 1 picks Escape Kids and opens NET PLAY",
           "Waiting for another cabinet",
           "Cabinet 2 sees the game at the top of its list and joins",
           "It copies the game over the cable",
           "Both in the lobby: the game starts",
           "Playing together: P1-P2 here, P3-P4 there"],
}
CAB_NAME = {"pt": "GABINETE %d", "en": "CABINET %d"}

# ── O roteiro ─────────────────────────────────────────────────────
# Cada tela: (inicio, imagem); "game" = o jogo. Cada aperto: (instante, tecla).
K = 0.35                                    # a contagem da sala, comprimida (0.5 s reais por quadro)
T_LOBBY = 13.8
T_GAME_A = T_LOBBY + 5 * K                  # o anfitriao abre o jogo (a-start-5 ja e depois)
T_GAME_B = T_LOBBY + 14 * K                 # o convidado, seis segundos (reais) depois
END = T_GAME_B + 6.0
LOOP = 0.8                                  # a volta ao comeco, em fusao
SCREENS = [
    [(0.0, "a-list-0"), (0.5, "a-list-1"), (1.0, "a-list-2"), (1.5, "a-list-3"), (2.5, "a-popup-0"),
     (3.4, "a-popup-1"), (4.6, "a-wait-0"), (T_LOBBY - 0.9, "a-join-1")]
    + [(T_LOBBY + k * K, "a-start-%d" % k) for k in range(5)] + [(T_GAME_A, "game")],
    [(0.0, "b-list-0"), (7.6, "b-list-1"), (8.8, "b-list-2"), (9.8, "b-popup-0"), (10.5, "b-popup-1"),
     (11.8, "b-copy-0"), (12.3, "b-copy-1"), (12.8, "b-copy-2"), (13.3, "b-copy-3"), (T_LOBBY - 0.4, "b-join-1")]
    + [(T_LOBBY + k * K, "b-start-%d" % k) for k in range(14)] + [(T_GAME_B, "game")],
]
PRESSES = [[(0.5, "down"), (1.0, "down"), (1.5, "down"), (2.5, "a"), (3.4, "right"), (4.6, "a")],
           [(8.8, "up"), (9.8, "a"), (10.5, "right"), (11.8, "a")]]
STEP_AT = [(0.0, 0), (4.6, 1), (7.6, 2), (11.8, 3), (T_LOBBY, 4), (T_GAME_B, 5)]
ACTING = [(0.0, 0), (7.6, 1), (T_LOBBY, None)]

CABS = [Cab(52, 47, 30, 166, (72, 54)), Cab(188, 47, 30, 166, (72, 54))]
CABLES = chain(CABS)


def pulses(t):
    """O aviso da festa (o anfitriao anuncia o jogo na rede), a copia (um rio
    do 1 para o 2), o pedido de entrada, a sala e o jogo (dos dois lados)."""
    out = []
    for k in range(9):                          # o aviso da festa, de tempos em tempos
        out += trip(t, 4.8 + k * 0.8, 0, 1, C["cyan"], 0.7)
    for k in range(18):                         # a copia do jogo
        out += trip(t, 11.8 + k * 0.09, 0, 1, C["green"], 0.56)
    out += trip(t, 11.9, 1, 0, C["pink"], 0.7)  # o pedido de entrada, do 2 para o 1
    if t >= T_LOBBY:                            # a sala e o jogo: dos dois lados
        gap = 0.5 if t < T_GAME_B else 0.22
        k = 0
        while T_LOBBY + k * gap <= t:
            out += trip(t, T_LOBBY + k * gap, 0, 1, C["green"], 0.7) if k % 2 == 0 else \
                trip(t, T_LOBBY + k * gap, 1, 0, C["pink"], 0.7)
            k += 1
    return out


def load_shot(name):
    im = Image.open(os.path.join(SHOTS, name + ".png")).convert("RGB")
    return im.resize((im.width * 2, im.height * 2), Image.NEAREST)


def main():
    work = tempfile.mkdtemp()
    vid = os.path.join(work, "vid")
    os.makedirs(vid)
    subprocess.run(["ffmpeg", "-v", "error", "-ss", str(GAME_FROM), "-t", "12", "-i", VIDEO, "-vf", "fps=%g" % FPS,
                    os.path.join(vid, "%04d.png")], check=True)
    game = sorted(os.listdir(vid))
    logo_path = os.path.join(ART, "logo", "mame", "esckids.png")
    logo = Image.open(logo_path).convert("RGBA") if os.path.isfile(logo_path) else None
    size = (CABS[0].scr[0] * PX, CABS[0].scr[1] * PX)
    mask = screen_mask(CABS[0].scr, PX)
    cache = {}

    def screen(i, t):
        name = at(SCREENS[i], t)
        if name == "game":
            k = min(len(game) - 1, int((t - T_GAME_A) * FPS))     # o convidado entra no quadro do anfitriao
            name = "vid:" + game[k]
            if name not in cache:
                cache[name] = crt(Image.open(os.path.join(vid, game[k])).convert("RGB"), size)
        elif name not in cache:
            cache[name] = crt(load_shot(name), size)
        return cache[name], at(SCREENS[i], t) == "game"

    f_cap, f_num, f8 = font(24), font(24), font(8)
    bases = {lit: background(LW, LH, CABS, lit, globes=[(120, 66)]) for lit in (None, 0, 1)}
    preview = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
    for lang in ("pt",) if preview else ("pt", "en"):
        frames = os.path.join(work, lang)
        os.makedirs(frames)
        n = int(math.ceil((END + LOOP) * FPS))
        first = None
        for f in ([int(p * FPS) for p in preview] if preview else range(n)):
            t = f / FPS
            tt = min(t, END)
            low = bases[at(ACTING, tt)].copy()
            d = ImageDraw.Draw(low)
            d.fontmode = "1"
            draw_cables(d, CABLES, pulses(tt))
            scrs, logos = {}, []
            for i, cab in enumerate(CABS):
                scrs[i], playing = screen(i, tt)
                box = marquee(d, cab, CAB_NAME[lang] % (i + 1), playing, f8)
                if playing and logo is not None:
                    logos.append(box)
                label(d, cab, "P1-2" if i == 0 else "P3-4", f8)
                press = next((k for when, k in PRESSES[i] if when <= tt < when + 0.3), None)
                controls(d, cab, press)
            im = low.resize((W, H), Image.NEAREST)
            for i, cab in enumerate(CABS):
                im.paste(scrs[i], cab.screen_box(PX), mask)
            for box in logos:
                paste_logo(im, logo, box, PX)
            k = at(STEP_AT, tt)
            caption(im, STEPS[lang][k], k, len(STEPS[lang]), f_cap, f_num)
            if f == 0:
                first = im
            if t > END:                          # a volta: funde com o primeiro quadro
                im = Image.blend(im, first, min(1.0, (t - END) / LOOP))
            im.save(os.path.join(OUT, "netplay-pt-%g.png" % t) if preview else os.path.join(frames, "%04d.png" % f))
        if preview:
            break
        webp, gif = (os.path.join(OUT, "netplay-%s.%s" % (lang, ext)) for ext in ("webp", "gif"))
        encode(os.path.join(frames, "%04d.png"), webp, gif, FPS)
        shutil.copyfile(os.path.join(frames, "%04d.png" % int(16.5 * FPS)), os.path.join(OUT, "netplay-%s-still.png" % lang))
        print(lang, n, "frames", os.path.getsize(webp) // 1024, "KB webp", os.path.getsize(gif) // 1024, "KB gif")
    shutil.rmtree(work)


if __name__ == "__main__":
    main()
