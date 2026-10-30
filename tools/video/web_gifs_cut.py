"""Corta as animacoes do site da gravacao do web_gifs.py: cada par de marcas
"nome:start" / "nome:end" de events.txt vira /gifs/web-nome.webp (WebP animado,
12 quadros por segundo, 760 de largura).

    python3 web_gifs_cut.py /web /gifs [NOME...]
"""
import glob
import os
import subprocess
import sys

SRC, DST = sys.argv[1], sys.argv[2]
ONLY = set(sys.argv[3:])
FPS, WIDTH, QUALITY = 12, 760, 55

marks = {}
for line in open(os.path.join(SRC, "events.txt")):
    stamp, _, name = line.strip().partition(" ")
    marks[name] = float(stamp)
frames = sorted((float(os.path.basename(p)[:-4]), p) for p in glob.glob(os.path.join(SRC, "frames", "*.jpg")))
os.makedirs(DST, exist_ok=True)

for name in sorted({n.split(":")[0] for n in marks if n.endswith(":start")}):
    if ONLY and name not in ONLY:
        continue
    start, end = marks[name + ":start"], marks.get(name + ":end")
    if not end:
        continue
    picked = [(t, p) for t, p in frames if start <= t <= end]
    if len(picked) < 2:
        print(name, "no frames")
        continue
    listing = os.path.join(DST, name + ".txt")
    with open(listing, "w") as f:
        for i, (t, p) in enumerate(picked):
            nxt = picked[i + 1][0] if i + 1 < len(picked) else end
            f.write("file '%s'\nduration %.4f\n" % (p, max(nxt - t, 0.001)))
        f.write("file '%s'\n" % picked[-1][1])
    out = os.path.join(DST, "web-%s.webp" % name)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listing, "-an",
                    "-vf", "fps=%d,scale=%d:-2:flags=lanczos" % (FPS, WIDTH), "-c:v", "libwebp_anim", "-lossless", "0",
                    "-quality", str(QUALITY), "-loop", "0", out], check=True)
    os.remove(listing)
    print(name, len(picked), "frames,", "%.1f s," % (end - start), os.path.getsize(out) // 1024, "KB")
