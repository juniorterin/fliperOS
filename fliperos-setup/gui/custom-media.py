#!/usr/bin/env python3
"""As midias de exemplo de um jogo personalizado (Setup > Games > Custom
games): uma imagem, um video e um texto com o nome do jogo e o caminho de
cada arquivo, e o logotipo (o nome com contorno, fundo transparente), nos
lugares em que os frontends os procuram. Assim o jogo ja aparece com arte no
frontend, e quem quiser sabe qual arquivo trocar.

    custom-media.py --name NOME --group GRUPO [--snap ARQ.png] [--video ARQ.mp4] [--text ARQ.txt] [--logo ARQ.png]

Cada arquivo so e criado se ainda nao existe (o de verdade, posto pela
pessoa, nunca e trocado). As cores e o texto sao sorteados: cada jogo fica
com a sua cara. O video precisa do ffmpeg (H.264); sem ele, fica de fora.
"""
import argparse
import colorsys
import os
import random
import shutil
import subprocess
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

W, H = 640, 480                 # a imagem, em 4:3
VW, VH, FPS, SECONDS = 320, 240, 30, 4

STORIES = (
    "{name} is waiting for its story. Nobody has written it yet.",
    "A game of the {group} collection. Its best moments are still to be told.",
    "{name}: one more credit, one more try. The rest of the story is yours to write.",
    "They say {name} hides a secret in the last stage. Nobody wrote it down yet.",
    "{name} came to this cabinet without a manual. Write its story here.",
)


def palette(rng):
    """Duas cores do mesmo matiz (o fundo em degrade) e a do texto."""
    hue = rng.random()
    top = [round(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.65, 0.55)]
    bottom = [round(c * 255) for c in colorsys.hsv_to_rgb((hue + 0.08) % 1, 0.8, 0.18)]
    accent = [round(c * 255) for c in colorsys.hsv_to_rgb((hue + 0.5) % 1, 0.55, 1.0)]
    return top, bottom, accent


def gradient(surf, top, bottom):
    w, h = surf.get_size()
    for y in range(h):
        t = y / max(1, h - 1)
        surf.fill([round(a + (b - a) * t) for a, b in zip(top, bottom)], (0, y, w, 1))


def fit_font(text, width, size):
    """A maior fonte (ate size) em que o texto cabe em width."""
    while size > 10:
        font = pygame.font.Font(None, size)
        if font.size(text)[0] <= width:
            return font
        size -= 2
    return pygame.font.Font(None, 10)


def centered(surf, text, font, color, cy):
    img = font.render(text, True, color)
    surf.blit(img, ((surf.get_width() - img.get_width()) // 2, cy - img.get_height() // 2))


def frame(size, name, group, hint, colors, t=None):
    """Uma imagem: o fundo, o nome grande, o grupo e, embaixo, o arquivo a
    trocar. t (0 a 1): no video, uma faixa clara passa e o nome pulsa."""
    w, h = size
    top, bottom, accent = colors
    surf = pygame.Surface(size)
    gradient(surf, top, bottom)
    # Linhas de fundo, como as de um tubo.
    shade = pygame.Surface((w, 1), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 40))
    for y in range(0, h, 4):
        surf.blit(shade, (0, y))
    if t is not None:
        band = pygame.Surface((w // 6, h), pygame.SRCALPHA)
        band.fill((255, 255, 255, 36))
        surf.blit(band, (round(-w // 6 + (w + w // 6) * t), 0))
    pulse = 1.0 if t is None else 0.92 + 0.08 * abs(((t * 4) % 2) - 1)
    big = fit_font(name.upper(), round(w * 0.86), round(h * 0.22 * pulse))
    centered(surf, name.upper(), big, accent, round(h * 0.42))
    small = fit_font(group, round(w * 0.8), round(h * 0.09))
    centered(surf, group, small, (235, 235, 235), round(h * 0.62))
    note = fit_font(hint, round(w * 0.94), round(h * 0.055))
    centered(surf, hint, note, (200, 200, 200), round(h * 0.9))
    return surf


def owned(path):
    """O arquivo do jogador, como a pasta em que esta."""
    try:
        st = os.stat(os.path.dirname(path))
        os.chown(path, st.st_uid, st.st_gid)
    except OSError:
        pass


def make_snap(path, args, colors):
    pygame.image.save(frame((W, H), args.name, args.group, "Replace: " + args.snap_hint, colors), path)
    owned(path)


def make_logo(path, args, colors):
    """O logotipo (o wheel dos frontends): o nome em uma ou duas linhas, na cor
    do jogo, com contorno escuro e sombra, recortado no tamanho do texto."""
    _, bottom, accent = colors
    words = args.name.upper().split()
    lines = [" ".join(words)]
    if len(words) > 1 and len(lines[0]) > 12:
        # Nome comprido: duas linhas, partidas no meio.
        half = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
        lines = [" ".join(words[:half]), " ".join(words[half:])]
    font = fit_font(max(lines, key=len), 560, 110 if len(lines) == 1 else 80)
    edge, shadow = 5, 6
    imgs = [font.render(line, True, accent) for line in lines]
    rims = [font.render(line, True, [max(0, c - 10) for c in bottom]) for line in lines]
    w = max(i.get_width() for i in imgs) + 2 * edge + shadow
    h = sum(i.get_height() for i in imgs) + 2 * edge + shadow
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    y = edge
    for img, rim in zip(imgs, rims):
        x = (w - shadow - img.get_width()) // 2
        dark = rim.copy()
        dark.set_alpha(150)
        surf.blit(dark, (x + shadow, y + shadow))
        for dx in range(-edge, edge + 1):
            for dy in range(-edge, edge + 1):
                if dx * dx + dy * dy <= edge * edge:
                    surf.blit(rim, (x + dx, y + dy))
        surf.blit(img, (x, y))
        y += img.get_height()
    pygame.image.save(surf, path)
    owned(path)


def make_video(path, args, colors):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("custom-media: no ffmpeg, no video", file=sys.stderr)
        return
    tmp = path + ".new.mp4"
    cmd = [ffmpeg, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (VW, VH),
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        frames = FPS * SECONDS
        for i in range(frames):
            surf = frame((VW, VH), args.name, args.group, "Replace: " + args.video_hint, colors, i / frames)
            proc.stdin.write(pygame.image.tostring(surf, "RGB"))
        proc.stdin.close()
    except BrokenPipeError:
        pass
    if proc.wait() == 0 and os.path.getsize(tmp) > 0:
        os.replace(tmp, path)
        owned(path)
    else:
        print("custom-media: ffmpeg failed, no video", file=sys.stderr)
        try:
            os.remove(tmp)
        except OSError:
            pass


def make_text(path, args, rng):
    story = rng.choice(STORIES).format(name=args.name, group=args.group)
    with open(path, "w", encoding="utf-8") as f:
        f.write("%s Replace this text with the game's description: %s\n" % (story, args.text_hint))
    owned(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--group", required=True)
    ap.add_argument("--snap")
    ap.add_argument("--video")
    ap.add_argument("--text")
    ap.add_argument("--logo")
    ap.add_argument("--home", default="", help="the start of the paths that the hints show as ~")
    args = ap.parse_args()
    short = lambda p: ("~" + p[len(args.home):]) if p and args.home and p.startswith(args.home + "/") else (p or "")
    args.snap_hint, args.video_hint, args.text_hint = short(args.snap), short(args.video), short(args.text)
    rng = random.Random()
    colors = palette(rng)
    pygame.font.init()
    made = []
    for path, make in ((args.snap, lambda p: make_snap(p, args, colors)),
                       (args.video, lambda p: make_video(p, args, colors)),
                       (args.text, lambda p: make_text(p, args, rng)),
                       (args.logo, lambda p: make_logo(p, args, colors))):
        if not path or os.path.exists(path):
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        make(path)
        if os.path.exists(path):
            made.append(path)
    for path in made:
        print(path)


if __name__ == "__main__":
    main()
