"""Acha a hora (epoch) do quadro 0 da gravacao do tubo, para ela andar junto
com o tablet: o instante em que a tela de aviso do SF2 (preta, so texto) vira
a abertura colorida aparece no tubo (segundos do arquivo) e no tablet (a
aba Live mostra o tubo por WebRTC). Grava /v/clips/tube0.txt, que o
script.py le.

    python3 /t/sync.py          (tools/video/render.sh web)
"""
import glob
import os
import subprocess

from PIL import Image, ImageStat

V = "/v"
WEBRTC_DELAY = 0.15            # o atraso do video ao vivo no navegador
ev = dict((l.split(" ", 1)[1].strip(), float(l.split()[0])) for l in open(V + "/web/events.txt"))

# Tubo: 10 quadros por segundo; depois do preto do jogo abrindo, o primeiro
# quadro colorido.
os.makedirs("/tmp/tube", exist_ok=True)
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", V + "/clips/tube.mkv", "-vf", "fps=10,scale=160:120",
                "/tmp/tube/%05d.png"], check=True)
tube_at = None
seen_dark = False
for i, f in enumerate(sorted(glob.glob("/tmp/tube/*.png"))):
    hsv = ImageStat.Stat(Image.open(f).convert("HSV")).mean
    if i / 10 > 15 and hsv[2] < 25:
        seen_dark = True
    if seen_dark and hsv[1] > 60 and hsv[2] > 60:
        tube_at = i / 10 - 0.05
        break

# Tablet: na aba Live, o brilho da parte de cima da pagina (o video) salta
# quando a abertura colorida chega.
tablet_at, last = None, None
for f in sorted(glob.glob(V + "/web/frames/*.jpg")):
    ts = float(os.path.basename(f)[:-4])
    if not ev["live"] <= ts <= ev["settings"]:
        continue
    value = ImageStat.Stat(Image.open(f).crop((20, 100, 800, 620)).convert("HSV")).mean[2]
    if last is not None and last < 20 and value > 45:
        tablet_at = ts
        break
    last = value
if tube_at is None or tablet_at is None:
    raise SystemExit("sync: the SF2 opening was not found (tube %s, tablet %s)" % (tube_at, tablet_at))
tube0 = tablet_at - WEBRTC_DELAY - tube_at
open(V + "/clips/tube0.txt", "w").write("%.3f\n" % tube0)
print("tube at %.2f s, tablet at %.3f: tube frame 0 = %.3f" % (tube_at, tablet_at, tube0))
