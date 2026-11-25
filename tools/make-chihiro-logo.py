"""O logotipo da Sega Chihiro (o da tela de boot da placa) como os outros sistemas: branco, fundo transparente.

  make-chihiro-logo.py CAPTURA.png SAIDA.png

CAPTURA: a tela de boot da placa (640x480) vista no xemu. O fundo e um degrade so na horizontal e a
tinta e preta: a transparencia vem de quanto cada ponto e mais escuro que o fundo da coluna dele.
"""
import sys

from PIL import Image, ImageFilter

src, dest = sys.argv[1], sys.argv[2]
shot = Image.open(src).convert('L')
W, H = shot.size
BOX = (98, 106, 543, 209)                      # a marca, com folga
# O degrade do fundo, por coluna (a faixa acima da marca).
back = [sorted(shot.getpixel((x, y)) for y in range(66, 94))[14] for x in range(W)]

crop = shot.crop(BOX)
cw, ch = crop.size
alpha = Image.new('L', (cw, ch), 0)
px, out = crop.load(), alpha.load()
for y in range(ch):
    for x in range(cw):
        b = back[BOX[0] + x]
        v = (b - px[x, y]) / max(b, 1)          # 0 = fundo, 1 = preto
        out[x, y] = max(0, min(255, round(v * 255)))
# O "TM" (o que fica a direita da marca, acima da elipse) nao faz parte do logotipo.
for y in range(166 - BOX[1], 184 - BOX[1]):
    for x in range(505 - BOX[0], 534 - BOX[0]):
        out[x, y] = 0
# Ampliar e voltar a borda nitida (os outros logotipos sao vetoriais): 4x, um desfoque curto e a curva.
SCALE = 4
big = alpha.resize((cw * SCALE, ch * SCALE), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.1))


def curve(v):
    t = max(0.0, min(1.0, (v / 255 - 0.30) / 0.40))
    return round((t * t * (3 - 2 * t)) * 255)


big = big.point([curve(v) for v in range(256)])
box = big.point(lambda v: 255 if v > 24 else 0).getbbox()
big = big.crop(box)
HEIGHT = 200
final = big.resize((max(1, round(big.width * HEIGHT / big.height)), HEIGHT), Image.LANCZOS)
logo = Image.new('RGBA', final.size, (255, 255, 255, 255))
logo.putalpha(final)
logo.save(dest, format='PNG', optimize=True)
print('logotipo: %dx%d (%.1f:1)' % (logo.width, logo.height, logo.width / logo.height))
