"""No gabinete: os jogos de cada lista com toda a midia (tela, capa, logo,
marquee, video) e a informacao salva. Imprime por sistema os nomes, os
famosos primeiro."""
import os
import sys

HOME = os.path.expanduser("~")
LISTS = os.path.join(HOME, ".local/share/fliperos/lists")
FAMOUS = """sf2 sf2ce ssf2t sfa3 sfiii3 mslug mslug2 mslugx mslug3 kof98 kof2002 garou samsho samsho2 rbff2 mvsc
xmvsf msh sfa2 dino punisher ddonpach dodonpac 1944 19xx progear outrun sharrier pacman mspacman galaga dkong
simpsons tmnt tmnt2 xmen aliens ffight captcomm wof avsp dstlk nwarr cybots batcir mk mk2 mk3 umk3 nbajam
tekken3 tekken2 tektagt sfex2 strider mmatrix sexyparo esprade gunbird2 dariusg rtype rtype2 gradius
twinbee bublbobl rastan contra 1942 commando ghouls gng ddragon dino metamoqt asurabus pbobble2 puzzloop
cvs2 mvsc2 vf4 doa2 ggxx samsptk mslug6 kof98um vf2 daytona fvipers hotd srallyc vf3 daytona2 fvipers2""".split()
KINDS = ("snap", "box", "logo", "marquee")


def has(kind, key, name):
    base = os.path.join(HOME, "media", kind, key)
    return any(os.path.exists(os.path.join(base, name + e)) for e in (".png", ".jpg"))


def video(key, name):
    base = os.path.join(HOME, "media", "preview", key)
    return any(os.path.exists(os.path.join(base, name + e)) for e in (".mp4", ".mkv", ".avi"))


systems = {}
for line in open(os.path.join(HOME, ".cache/fliperos/frontend-systems")):
    p = line.strip().split("|")
    if len(p) >= 7:
        systems[p[3]] = (p[0], p[1])
for fname in sorted(os.listdir(LISTS)):
    if not fname.endswith(".txt") or fname == "Arcade.txt":
        continue
    title = fname[:-4]
    if title not in systems:
        continue
    key, folder = systems[title]
    names = []
    for line in open(os.path.join(LISTS, fname), encoding="utf-8", errors="replace"):
        if line.startswith("#"):
            continue
        name = line.split(";")[0]
        full = all(has(k, key, name) for k in KINDS) and video(key, name) and \
            os.path.exists(os.path.join(HOME, "media/info", key, name + ".en.json"))
        if full:
            names.append(name)
    names.sort(key=lambda n: (n not in FAMOUS, FAMOUS.index(n) if n in FAMOUS else 0, n))
    print("%s|%s|%d|%s" % (key, title, len(names), " ".join(names[:80])))
