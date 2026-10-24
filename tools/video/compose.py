"""Monta o video de apresentacao do FliperOS (1920x1080, 30 fps, sem som):
os cartoes, as cenas no CRT, o painel web no tablet ao lado do tubo de
verdade, e a legenda dupla (PT em cima, EN embaixo), mais os .srt. O
roteiro (a ordem, os cartoes e as legendas) e o script.py.

    python3 /t/compose.py          (tools/video/render.sh compose)
    ONLY=s3 python3 /t/compose.py  (so um trecho, para conferir)
"""
import glob
import os
import subprocess

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

V = "/v"
OUT = V + "/out"
os.makedirs(OUT, exist_ok=True)
WW, HH, FPS = 1920, 1080, 30
PIXEL = "/g/fonts/PressStart2P-Regular.ttf"
SANS = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
SANSB = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
LOGO = "/repo/website/public/fliperos-logo.png"
BG, BG2, FG = (25, 26, 33), (40, 42, 54), (248, 248, 242)
PINK, PURPLE, CYAN, GREEN, COMMENT = (255, 121, 198), (189, 147, 249), (139, 233, 253), (80, 250, 123), (98, 114, 164)
RAINBOW = [(255, 85, 85), (255, 184, 108), (241, 250, 140), (80, 250, 123), (139, 233, 253), (189, 147, 249)]

# A tela do CRT sozinha e lado a lado com o tablet.
SOLO = (480, 56, 960, 720)
TUBE = (70, 96, 960, 720)
TAB = (1196, 52, 598, 860)


def run(*cmd):
    subprocess.run(list(cmd), check=True)


# ── As imagens ──
def background():
    im = Image.new("RGB", (WW, HH), BG)
    d = ImageDraw.Draw(im)
    for y in range(HH):
        k = y / HH
        d.line([(0, y), (WW, y)], fill=tuple(int(BG[i] + (BG2[i] - BG[i]) * (1 - abs(k - 0.4) * 1.6)) for i in range(3)))
    for x in range(0, WW, 48):
        d.line([(x, 0), (x, HH)], fill=(33, 34, 44))
    for y in range(0, HH, 48):
        d.line([(0, y), (WW, y)], fill=(33, 34, 44))
    glow = Image.new("RGB", (WW, HH), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse((WW * 0.2, -HH * 0.4, WW * 0.8, HH * 0.6), fill=(70, 40, 110))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    return ImageChops.add(im, glow)


def bezel(screen, radius=26, pad=40):
    """O gabinete em volta da tela: plastico escuro, a borda do tubo e o
    furo (transparente) onde a imagem entra."""
    x, y, w, h = screen
    im = Image.new("RGBA", (WW, HH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((x - pad - 6, y - pad - 6 + 10, x + w + pad + 6, y + h + pad + 6 + 10), radius + 8,
                        fill=(0, 0, 0, 120))
    d.rounded_rectangle((x - pad, y - pad, x + w + pad, y + h + pad), radius, fill=(44, 45, 56, 255),
                        outline=(68, 71, 90, 255), width=3)
    d.rounded_rectangle((x - 14, y - 14, x + w + 14, y + h + 14), 18, fill=(10, 10, 14, 255))
    d.rectangle((x, y, x + w - 1, y + h - 1), fill=(0, 0, 0, 0))
    f = ImageFont.truetype(PIXEL, 14)
    d.text((x + w // 2, y + h + pad // 2 + 2), "FLIPEROS", fill=(98, 114, 164, 255), font=f, anchor="mm")
    d.ellipse((x + w + pad - 30, y + h + pad // 2 - 4, x + w + pad - 22, y + h + pad // 2 + 4), fill=GREEN + (255,))
    return im


def tablet(screen):
    x, y, w, h = screen
    im = Image.new("RGBA", (WW, HH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((x - 30, y - 30 + 12, x + w + 30, y + h + 30 + 12), 52, fill=(0, 0, 0, 120))
    d.rounded_rectangle((x - 24, y - 24, x + w + 24, y + h + 24), 44, fill=(18, 18, 22, 255),
                        outline=(80, 82, 100, 255), width=3)
    d.rectangle((x, y, x + w - 1, y + h - 1), fill=(0, 0, 0, 0))
    d.ellipse((x + w // 2 - 4, y - 16, x + w // 2 + 4, y - 8), fill=(50, 52, 64, 255))
    return im


def scanlines(w, h):
    """As linhas do tubo: a cada 3 pixels (240 linhas em 720), uma escura."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for yy in range(2, h, 3):
        d.line([(0, yy), (w, yy)], fill=(0, 0, 0, 70))
    return im


def rainbow(d, x, y, w):
    for i, c in enumerate(RAINBOW):
        d.rectangle((x, y + i * 4, x + w, y + i * 4 + 3), fill=c)


def card(path, big, pt, en, number=None, logo=True):
    im = Image.open(OUT + "/bg.png").convert("RGB")
    d = ImageDraw.Draw(im)
    y = 250
    if logo:
        lg = Image.open(LOGO).convert("RGBA")
        lg = lg.resize((lg.width * 2 // 2, lg.height * 2 // 2), Image.NEAREST)
        im.paste(lg, ((WW - lg.width) // 2, 140), lg)
        y = 140 + lg.height + 40
    if number:
        # (a Press Start 2P nao tem o I maiusculo com acento)
        d.text((WW // 2, y), number, fill=PINK, font=ImageFont.truetype(SANSB, 34), anchor="mm")
        y += 84
    else:
        y += 24
    f = ImageFont.truetype(PIXEL, 56)
    d.text((WW // 2 + 4, y + 4), big, fill=(70, 40, 110), font=f, anchor="mm")
    d.text((WW // 2, y), big, fill=FG, font=f, anchor="mm")
    tw = d.textlength(big, font=f)
    rainbow(d, int(WW // 2 - tw // 2), y + 44, int(tw))
    y += 120
    d.text((WW // 2, y), pt, fill=FG, font=ImageFont.truetype(SANSB, 44), anchor="mm")
    d.text((WW // 2, y + 62), en, fill=CYAN, font=ImageFont.truetype(SANS, 36), anchor="mm")
    im.save(path)


# ── Os trechos ──
def seg_card(n, png, dur):
    out = "%s/seg%02d.mp4" % (OUT, n)
    run("ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-i", png, "-t", str(dur),
        "-vf", "fade=in:0:9,fade=out:st=%.2f:d=0.35,format=yuv420p" % (dur - 0.35), "-c:v", "libx264", "-crf", "12",
        "-preset", "veryfast", "-r", str(FPS), out)
    return out, dur


def seg_crt(n, clip, dur):
    out = "%s/seg%02d.mp4" % (OUT, n)
    x, y, w, h = SOLO
    run("ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-i", OUT + "/bg.png",
        "-i", clip, "-loop", "1", "-i", OUT + "/bezel_solo.png", "-loop", "1", "-i", OUT + "/scan.png",
        "-filter_complex",
        "[1:v]scale=%d:%d:flags=neighbor,setsar=1[s];[s][3:v]overlay=format=auto[ss];"
        "[0:v][ss]overlay=%d:%d[a];[a][2:v]overlay=0:0,"
        "fade=in:0:9,fade=out:st=%.2f:d=0.35,format=yuv420p[o]" % (w, h, x, y, dur - 0.35),
        "-map", "[o]", "-t", str(dur), "-c:v", "libx264", "-crf", "12", "-preset", "veryfast", "-r", str(FPS), out)
    return out, dur


def tablet_clip(start, end):
    frames = sorted(glob.glob(V + "/web/frames/*.jpg"), key=lambda f: float(os.path.basename(f)[:-4]))
    ts = [(float(os.path.basename(f)[:-4]), f) for f in frames]
    first = [p for p in ts if p[0] <= start][-1:]
    keep = first + [p for p in ts if start < p[0] < end]
    lines = []
    for i, (t, f) in enumerate(keep):
        t0 = max(t, start)
        t1 = keep[i + 1][0] if i + 1 < len(keep) else end
        lines += ["file '%s'" % f, "duration %.4f" % max(0.001, t1 - t0)]
    lines.append("file '%s'" % keep[-1][1])
    with open(OUT + "/tablet.txt", "w") as fh:
        fh.write("\n".join(lines) + "\n")
    x, y, w, h = TAB
    run("ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", OUT + "/tablet.txt",
        "-vf", "fps=%d,scale=%d:%d:flags=lanczos,format=yuv420p" % (FPS, w, h), "-t", "%.3f" % (end - start),
        "-c:v", "libx264", "-crf", "10", "-preset", "veryfast", OUT + "/tablet.mp4")


def seg_web(n, start, end, tube0):
    dur = end - start
    tablet_clip(start, end)
    out = "%s/seg%02d.mp4" % (OUT, n)
    tx, ty, tw, th = TUBE
    ax, ay, aw, ah = TAB
    run("ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-i", OUT + "/bg.png",
        "-ss", "%.3f" % (start - tube0), "-i", V + "/clips/tube.mkv", "-i", OUT + "/tablet.mp4",
        "-loop", "1", "-i", OUT + "/bezel_web.png", "-loop", "1", "-i", OUT + "/scan.png",
        "-filter_complex",
        "[1:v]fps=%d,scale=%d:%d:flags=lanczos,setsar=1[s];[s][4:v]overlay=format=auto[ss];"
        "[0:v][ss]overlay=%d:%d[a];[a][2:v]overlay=%d:%d[b];[b][3:v]overlay=0:0,"
        "fade=in:0:9,fade=out:st=%.2f:d=0.35,format=yuv420p[o]" % (FPS, tw, th, tx, ty, ax, ay, dur - 0.35),
        "-map", "[o]", "-t", "%.3f" % dur, "-c:v", "libx264", "-crf", "12", "-preset", "veryfast", "-r", str(FPS), out)
    return out, dur


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


# ── A legenda ──
def ts_ass(t):
    return "%d:%02d:%05.2f" % (t // 3600, (t % 3600) // 60, t % 60)


def ts_srt(t):
    ms = int(round(t * 1000))
    return "%02d:%02d:%02d,%03d" % (ms // 3600000, ms % 3600000 // 60000, ms % 60000 // 1000, ms % 1000)


def write_subs(subs):
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: PT,Noto Sans,44,&H00F2F8F8,&H00FFFFFF,&H00211A19,&H96000000,-1,0,0,0,100,100,0,0,1,3.2,1.5,2,120,120,92,1
Style: EN,Noto Sans,35,&H00FDE98B,&H00FFFFFF,&H00211A19,&H96000000,0,-1,0,0,100,100,0,0,1,2.8,1.2,2,120,120,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    pt, en = [], []
    for i, (a, b, p, e) in enumerate(subs, 1):
        ev.append("Dialogue: 0,%s,%s,PT,,0,0,0,,%s" % (ts_ass(a), ts_ass(b), p))
        ev.append("Dialogue: 0,%s,%s,EN,,0,0,0,,%s" % (ts_ass(a), ts_ass(b), e))
        pt += [str(i), "%s --> %s" % (ts_srt(a), ts_srt(b)), p, ""]
        en += [str(i), "%s --> %s" % (ts_srt(a), ts_srt(b)), e, ""]
    open(OUT + "/subs.ass", "w", encoding="utf-8").write(head + "\n".join(ev) + "\n")
    open(OUT + "/fliperos-apresentacao.pt-BR.srt", "w", encoding="utf-8").write("\n".join(pt))
    open(OUT + "/fliperos-apresentacao.en.srt", "w", encoding="utf-8").write("\n".join(en))


exec(open("/t/script.py", encoding="utf-8").read())
