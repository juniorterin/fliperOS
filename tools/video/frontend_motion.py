#!/usr/bin/env python3
"""Grava as animacoes do frontend para o site e o Telegram: o frontend de verdade
(fliperos-setup/gui, sem nenhum remendo) com uma biblioteca de jogos de mentira, uma rede
de mentira (festas de link e de party) e o relogio virtual a 50 quadros por segundo. As
teclas sao as do frontend (fe.act), de modo que o que se ve e o que o gabinete faz.

    python3 tools/video/frontend_motion.py PASTA menu|more|all [--sheet]

  menu   o menu do jogo num jogo de link e de party: o PLAY pulsa, o globo do link gira, a onda
         nos gabinetes, o party com as vagas enchendo e os jogadores em onda, o aperto que
         pisca em verde e o STARTED que treme       -> frontend-menu.webp
  more   a pagina "+": os componentes entrando, a troca de pagina que desliza e o replay
         ao voltar                                  -> frontend-page.webp
  sounds Tab > FRONTEND SOUNDS: os seis sons, o volume de cada um, o seletor de arquivos, a trilha
         (uma pasta de musicas) e o volume do video de preview     -> frontend-sounds.webp
  music  a barra NOW PLAYING que entra quando uma faixa comeca, como a das conquistas, com o
         nome que corre quando nao cabe                            -> frontend-music.webp
  --sheet  tambem grava a folha de contato (NOME-folha.png) para conferir os quadros

Cada WebP e animado, 320x240, 25 quadros por segundo (os passos de 0,07 s do movimento
pedem mais que os 12 fps das outras animacoes do site), para website/public/screenshots/anim
e docs/telegram/img. Precisa de pygame e Pillow (o WSL tem; no Windows, so em Docker).
"""
import importlib.util
import json
import lzma
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUI = ROOT / "fliperos-setup" / "gui"
FPS = 50
SSF2T = ("docs/telegram/img/0.22-ssf2t-party-fight.png", "docs/telegram/img/0.22-ssf2t-party-2.png")

# A pagina "+" do Super Street Fighter II Turbo, como o Arcade Database a preenche.
INFO = {
    "year": "1994", "manufacturer": "Capcom", "genre": "Fighter / Versus", "nplayers": "2P simultaneous",
    "input_controls": "joystick (8-way)", "serie": "Street Fighter", "screen_resolution": "384x224",
    "screen_orientation": "horizontal", "status": "good", "languages": "English, Japanese", "rate": 70,
    "input_buttons": "6",
    "buttons_colors": ("P1_BUTTON1:blue:Light Punch;P1_BUTTON2:white:Middle Punch;P1_BUTTON3:red:Strong Punch;"
                       "P1_BUTTON4:blue:Light Kick;P1_BUTTON5:white:Middle Kick;P1_BUTTON6:red:Strong Kick"),
    "history_copyright_short": "Arcade History",
    "history": (
        "Super Street Fighter II Turbo published 32 years ago:\n(c) 1994 Capcom.\n\n"
        "The fifth chapter of the series adds new moves, a faster game and the Super Combo gauge. "
        "Sixteen fighters pick a side on a crowded dock, the guard goes up, the opening comes and the "
        "super closes the round. Two players share the same cabinet and the same joystick layout.\n\n"
        "- TECHNICAL -\nBoard: Capcom CPS-2. Sound: QSound. Screen: 384x224, horizontal. "
        "Six buttons: three punches and three kicks.\n\n"
        "- TRIVIA -\nIn Japan it came out as Super Street Fighter II X: Grand Master Challenge. "
        "A hidden fighter waits for the player who clears the game with a perfect score.\n\n"
        "- SERIES -\nIt follows Super Street Fighter II and was followed by the Alpha games. "
        "Many later ports use its balance as the reference.\n"),
}

# (sistema, set, titulo, ano, fabricante, categoria, jogadores, controle, botoes)
GAMES = [
    ("mame", "1944", "1944: The Loop Master", "2000", "Capcom", "Shooter / Flying Vertical", "2", "joystick (8-way)", "2"),
    ("mame", "aof", "Art of Fighting", "1992", "SNK", "Fighter / Versus", "2", "joystick (8-way)", "4"),
    ("model3", "dirtdvls", "Dirt Devils", "1998", "Sega", "Driving / Race", "1", "paddle,pedal", "4"),
    ("model2", "daytona", "Daytona USA", "1994", "Sega", "Driving / Race (chase view)", "1", "paddle,pedal", "6"),
    ("mame", "ssf2tb", "Super Street Fighter II: The Tournament Battle", "1993", "Capcom", "Fighter / Versus", "2",
     "joystick (8-way)", "6"),
    ("mame", "ssf2t", "Super Street Fighter II Turbo", "1994", "Capcom", "Fighter / Versus", "2", "joystick (8-way)", "6"),
    ("retroarch/fbneo", "xmen", "X-Men (4 Players)", "1992", "Konami", "Fighter / 2.5D", "4", "joystick (8-way)", "3"),
    ("mame", "kof98", "The King of Fighters '98", "1998", "SNK", "Fighter / Versus", "2", "joystick (8-way)", "4"),
]
SYSTEMS = (("mame", "MAME"), ("model2", "Model 2"), ("model3", "Supermodel"), ("retroarch/fbneo", "FBNeo"))

# Os outros gabinetes da rede de mentira: uma sala de espera de Daytona (2 de 8), uma festa do
# Tournament Battle que ja comecou e um party de X-Men aberto por um gabinete de 2 controles.
NET = [
    {"v": 1, "id": "a1", "name": "CABINET-A", "ip": "10.9.9.2", "game": "daytona", "system": "model2", "link": "daytona",
     "party": "a1", "slot": 1, "max": 8, "state": "lobby"},
    {"v": 1, "id": "a2", "name": "CABINET-B", "ip": "10.9.9.3", "game": "daytona", "system": "model2", "link": "daytona",
     "party": "a1", "slot": 2, "max": 8, "state": "lobby"},
    {"v": 1, "id": "c1", "name": "CABINET-C", "ip": "10.9.9.4", "game": "ssf2tb", "system": "mame", "link": "ssf2tb",
     "party": "c1", "slot": 1, "max": 4, "state": "playing"},
    {"v": 1, "id": "c2", "name": "CABINET-D", "ip": "10.9.9.5", "game": "ssf2tb", "system": "mame", "link": "ssf2tb",
     "party": "c1", "slot": 2, "max": 4, "state": "playing"},
    {"v": 1, "id": "f1", "name": "CABINET-F", "ip": "10.9.9.7", "game": "xmen", "system": "retroarch/fbneo",
     "link": "netplay", "party": "f1", "slot": 1, "take": 2, "max": 4, "state": "lobby"},
]


def prepare_art(folder):
    """A captura do SSF2T (a do README de 0.22) como tela, cartaz e capa (um corte dela)."""
    from PIL import Image
    fight, party = (Image.open(ROOT / p).convert("RGB") for p in SSF2T)
    fight.save(folder / "snap.png")
    party.save(folder / "marquee.png")
    fight.crop((0, 40, 402, 576)).save(folder / "box.png")


def build(which, home):
    """O Frontend de verdade, com a biblioteca e a rede de mentira; devolve (frontend, modulo)."""
    sys.path.insert(0, str(GUI))
    os.environ["HOME"] = os.environ["FLIPEROS_HOME"] = str(home)
    art = home / "art"
    art.mkdir()
    prepare_art(art)
    # O link de mentira: a tabela de presenca, o FBNeo que sabe o X-Men e um core "instalado" que salva
    # estado deterministico (o que o net play do RetroArch pede).
    os.environ["FLIPEROS_LINK_NVRAM"] = str(ROOT / "config" / "link-nvram")
    with lzma.open(home / "fbneo.tsv.xz", "wt") as f:
        f.write("\txmen\t\t\n")
    os.environ["FLIPEROS_FBNEO_INDEX"] = str(home / "fbneo.tsv.xz")
    for folder, name, text in (("cores", "fbneo_libretro.so", ""), ("info", "fbneo_libretro.info",
                                                                   'savestate_features = "deterministic"\n')):
        (home / folder).mkdir()
        (home / folder / name).write_text(text)
    os.environ["FLIPEROS_RA_CORES"], os.environ["FLIPEROS_RA_INFO"] = str(home / "cores"), str(home / "info")
    (home / "net.json").write_text(json.dumps({"table": NET}))
    os.environ["FLIPEROS_LINK_FAKE"] = str(home / "net.json")
    # Os sons e a trilha (Tab > Frontend sounds): a pasta fliperos-sounds com os sons padrao, uns
    # outros e musicas (vazias: a gravacao e sem som).
    os.environ["FLIPEROS_SOUNDS_DIR"] = str(home / "media" / "fliperos-sounds")
    import fesound
    fesound.seed()
    sounds, music = Path(fesound.sounds_dir()), Path(fesound.music_dir())
    for name in ("coin.wav", "laser.wav", "power-up.wav"):
        shutil.copyfile(sounds / "enter.wav", sounds / name)
    for name in ("BurtySounds - Retrowave.mp3", "Night Drive.mp3", "Neon Skyline.ogg"):
        (music / name).write_bytes(b"x")
    for folder, names in (("Synthwave", ("Outrun.mp3", "Chrome Sunset.mp3", "Grid Runner.mp3")),
                          ("Arcade classics", ("Insert Coin.mp3", "High Score.mp3"))):
        (music / folder).mkdir()
        for name in names:
            (music / folder / name).write_bytes(b"x")
    import fedata
    systems = [{"key": key, "folder": str(home / "roms" / key), "platform": "arcade", "name": name,
                "exe": "/x/fliperos-x11-run", "args": "x [name]", "extensions": [".zip"], "arcade": True}
               for key, name in SYSTEMS]
    for system in systems:
        os.makedirs(system["folder"], exist_ok=True)

    class FakeLibrary(fedata.Library):
        def __init__(self):
            self.lock = threading.Lock()
            self.systems = systems
            self.filters = [fedata.FAVOURITES, {"name": "All Games", "rules": [], "sort_by": "", "reverse": False, "limit": 0}]
            self.info = fedata.web.GameInfo()
            self.cache, self.stamps = {}, {}
            self.refreshing, self.generation = False, 0
            self.epoch, self.counts, self.count_lock = 0, {}, threading.Lock()

        def games(self, category):
            out = []
            for system, name, title, year, maker, cat, players, control, buttons in GAMES:
                out.append({"Name": name, "Title": title, "Year": year, "Manufacturer": maker, "Category": cat,
                            "Players": players, "Control": control, "Buttons": buttons,
                            "_system": next(s for s in systems if s["key"] == system), "file": name + ".zip"})
            out.sort(key=lambda g: g["Title"].lower())
            return out

        def media(self, game, kind):
            path = art / (kind + ".png")
            return str(path) if game["Name"] in ("ssf2t", "ssf2tb") and path.is_file() else None

        def command(self, game):
            return ["/x/fliperos-x11-run", "groovymame", game["Name"]]

        def changed(self):
            return False

        def refresh(self, done=None):
            pass

        def hidden(self):
            return set()

        def favourites(self):
            return set()

        def set_favourite(self, *args, **kwargs):
            pass

    fedata.Library = FakeLibrary
    sys.argv = ["fliperos-frontend"]
    spec = importlib.util.spec_from_loader("fe", SourceFileLoader("fe", str(GUI / "fliperos-frontend")))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Args:
        shot = str(home / "shot")      # so para o construtor nao abrir janela, nem threads
        media = False

    fe = module.Frontend(Args)
    fe.link.local_players = 2          # um gabinete de 2 controles: o X-Men (4 jogadores) tem party
    fe.overlay, fe.ov, fe.mode = None, {}, "list"
    fe.rebuild()
    return fe, module


def scenario(which, fe, info):
    """(eventos, duracao): (hora, funcao) com as teclas do jogador."""
    def key(name):
        return lambda: fe.act(name)

    def go_to(name):
        def move():
            fe.cursor = next(i for i, r in enumerate(fe.rows) if r[0] and r[0]["Name"] == name and r[2] != "elsewhere")
        return move

    if which == "more":
        def open_more():
            # O open_more de verdade, sem a thread que le o Arcade Database (as informacoes ja estao aqui).
            fe.overlay = "more"
            fe.ov = {"game": fe.game(), "info": dict(info), "loading": False, "scroll": 0, "t0": time.monotonic()}
        fe.open_more = open_more
        go_to("ssf2t")()
        return [(0.70, key("b1")), (1.45, key("right")), (1.80, key("right")), (2.70, key("b1")),    # o menu e o "+"
                (5.00, key("right")),                                                                # a pagina 2
                (7.30, key("down")), (7.70, key("down")), (8.10, key("down")),                       # rola o texto
                (8.90, key("left")), (10.50, key("right")),                                          # voltar anima de novo
                (12.30, key("b2")), (13.20, key("b2"))], 14.0
    def now_playing(title):
        # O que o laco faz quando a trilha comeca uma faixa (sound_tick): a barra entra agora.
        return lambda: setattr(fe, "nowplaying", (title, time.monotonic()))

    def step_to(name):
        # Um aperto de baixo (ou de cima) em direcao a linha do seletor que comeca com NAME; agendado
        # varias vezes, anda ate la e para.
        def step():
            entries = fe.ov.get("entries") or []
            want = next((i for i, e in enumerate(entries) if e[1].lower().startswith(name.lower())), None)
            if want is not None and fe.ov["sel"] != want:
                fe.act("down" if want > fe.ov["sel"] else "up")
        return step

    def walk(name, start, count=9, gap=0.14):
        return [(start + gap * i, step_to(name)) for i in range(count)]

    if which == "sounds":
        go_to("ssf2t")()
        sounds_row = 5 + [k for k, _ in fe.view.FE_OPTIONS].index("sounds")
        return ([(0.6, key("tab"))] + [(1.3 + 0.09 * i, key("down")) for i in range(sounds_row)] +
                [(2.8, key("b1")),                                                       # Frontend sounds: BROWSE
                 (3.5, key("down")), (4.0, key("down")),                                  # BACK
                 (4.5, key("right")), (4.7, key("right")), (4.9, key("right")),           # mais alto
                 (5.5, key("down")),                                                      # OPEN GAME
                 (6.0, key("left")), (6.2, key("left")), (6.4, key("left")),              # mais baixo
                 (6.9, key("down")), (7.5, key("b1"))] +                                  # CLOSE GAME: o seletor
                walk("laser", 8.0) +
                [(9.6, key("b1")),                                                        # escolhe laser.wav
                 (10.3, key("down")), (10.8, key("down")), (11.3, key("b1"))] +           # MUSIC: o seletor
                walk("synthwave", 11.8) +
                [(13.4, key("b1"))] +                                                     # entra na pasta
                walk("use this", 13.9, 5) +
                [(14.9, key("b1")), (15.1, now_playing("Synthwave - Outrun")),           # USE THIS FOLDER
                 (15.8, key("down")),                                                     # MUSIC VOLUME
                 (16.3, key("right")), (16.5, key("right")), (16.7, key("right")), (16.9, key("right")),
                 (17.5, key("down")),                                                     # PAUSE MUSIC: desligado por padrao
                 (18.1, key("right")), (19.0, key("right")),                              # liga e desliga
                 (19.7, key("down")),                                                     # PREVIEW VOLUME
                 (20.2, key("left")), (20.4, key("left")), (20.6, key("left")),
                 (21.4, key("b2")), (22.0, key("b2"))]), 23.2                              # volta ao Tab e fecha
    if which == "music":
        go_to("1944")()
        return [(0.4, now_playing("BurtySounds - Retrowave")),
                (1.6, key("down")), (2.3, key("down")), (3.0, key("down")), (3.7, key("down")),
                (6.4, now_playing("Neon Skyline - A Very Long Track Title That Needs To Run")),
                (7.5, key("down")), (8.2, key("down")), (8.9, key("up")), (9.6, key("up"))], 13.0
    fe.link_join = lambda party, take=None: setattr(fe, "overlay", None)      # entrar na sala nao e o assunto
    fe.link_host = lambda take=None: setattr(fe, "overlay", None)
    return [(0.0, go_to("daytona")), (0.5, key("b1")),             # abre o menu: o PLAY pulsa
            (2.1, key("right")),                                    # JOIN LINK: o globo gira e a onda nos gabinetes
            (4.4, key("right")), (5.8, key("left")),                # NEW LINK e de volta
            (6.6, key("b1")),                                       # aperta o JOIN: pisca em verde e entra
            (7.6, go_to("xmen")), (7.8, key("b1")), (9.0, key("right")),    # o party: vagas e jogadores
            (11.6, key("b1")),
            (12.6, go_to("ssf2tb")), (12.8, key("b1")), (13.6, key("right")),   # a festa que ja comecou
            (15.6, key("b1")),                                      # STARTED: treme e avisa, o menu fica
            (17.2, key("b2"))], 18.2


def record(which, out, sheet):
    from PIL import Image
    import pygame
    home = Path(tempfile.mkdtemp())
    fe, _ = build(which, home)
    import feview
    clock = [0.0]
    time.monotonic = lambda: fe.start + clock[0]       # o relogio do frontend e o virtual
    fe.shot = None                                     # o movimento toca (nos prints fica tudo parado)
    events, total = scenario(which, fe, INFO)
    frames, pending = [], sorted(events, key=lambda e: e[0])
    for k in range(10):                                # aquece (as imagens leem no 1o quadro): nao grava
        clock[0] = -0.5 + k * 0.04
        fe.tick(fe.start + clock[0])
        feview.draw(fe, fe.start + clock[0])
    for n in range(int(total * FPS)):
        clock[0] = n / FPS
        while pending and pending[0][0] <= clock[0] + 1e-9:
            pending.pop(0)[1]()
        fe.tick(fe.start + clock[0])
        feview.draw(fe, fe.start + clock[0])
        frames.append(fe.back.copy())

    def image(surface):
        return Image.frombytes("RGB", surface.get_size(), pygame.image.tostring(surface, "RGB"))
    name = {"menu": "frontend-menu", "more": "frontend-page", "sounds": "frontend-sounds", "music": "frontend-music"}[which]
    shown = [image(s) for s in frames[::2]]
    shown[0].save(out / (name + ".webp"), save_all=True, append_images=shown[1:], duration=1000 // (FPS // 2), loop=0,
                  quality=92, method=6)
    print(out / (name + ".webp"), len(shown), "frames", (out / (name + ".webp")).stat().st_size // 1024, "KB")
    if sheet:
        picks = frames[::len(frames) // 24]
        folha = Image.new("RGB", (4 * 326 + 6, ((len(picks) + 3) // 4) * 246 + 6), (24, 24, 32))
        for i, surface in enumerate(picks):
            folha.paste(image(surface), (6 + (i % 4) * 326, 6 + (i // 4) * 246))
        folha.save(out / (name + "-folha.png"))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2 or args[1] not in ("menu", "more", "sounds", "music", "all"):
        sys.exit(__doc__)
    out = Path(args[0])
    out.mkdir(parents=True, exist_ok=True)
    if args[1] == "all":
        for which in ("menu", "more", "sounds", "music"):         # um frontend por processo (o modulo guarda o estado)
            subprocess.run([sys.executable, "-I", __file__, str(out), which] + [a for a in sys.argv[1:] if a.startswith("--")],
                           check=True)
        return
    os.environ["SDL_VIDEODRIVER"] = os.environ["SDL_AUDIODRIVER"] = "dummy"
    record(args[1], out, "--sheet" in sys.argv)


if __name__ == "__main__":
    main()
