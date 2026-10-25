# O roteiro do video: os cartoes (CARDS), as legendas de cada trecho (SUBS,
# PT e EN; o tempo conta do comeco do trecho), a ordem (PLAN) e as gravacoes
# de cada cena (CLIPS). Executado dentro do compose.py. Mudou um texto: so o
# "tools/video/render.sh compose" de novo.

# O painel web (render.sh web): os eventos do tablet e a hora do quadro 0 da
# gravacao do tubo (sync.py). Sem eles, o video sai sem esse trecho.
WEB = os.path.exists(V + "/web/events.txt") and os.path.exists(V + "/clips/tube0.txt")
EV = {"start": 0.0, "end": 0.0}
TUBE0 = 0.0
if WEB:
    EV = dict((l.split(" ", 1)[1].strip(), float(l.split()[0])) for l in open(V + "/web/events.txt"))
    TUBE0 = float(open(V + "/clips/tube0.txt").read())
else:
    print("No web panel recording (render.sh web): the video goes without it.")
WEB_START, WEB_END = EV["start"], EV["end"]

CARDS = {
    "intro": ("FLIPEROS", "Arcade Linux feito para CRT", "Arcade Linux built for CRT", None),
    "c1": ("INSTALAÇÃO", "Do pendrive ao disco", "From the USB stick to the disk", "1"),
    "c2": ("PRIMEIRO BOOT", "O sistema instalado", "The installed system", "2"),
    "c3": ("SETUP", "Tudo configurado no próprio gabinete", "Everything set up on the cabinet itself", "3"),
    "c4": ("BAIXAR JOGOS", "Romsets filtrados, links magnet e BIOS", "Filtered romsets, magnet links and BIOS", "4"),
    "c5": ("FRONTEND", "As suas listas de jogos, com vídeo", "Your game lists, with video", "5"),
    "c6": ("PAINEL WEB", "O gabinete pelo tablet ou celular", "The cabinet from a tablet or phone", "6"),
    "outro": ("FLIPEROS", "fliperos.juniorter.in  ·  github.com/juniorterin/fliperOS",
              "Grátis e de código aberto  ·  Free and open source", None),
}

SUBS = {
    "s1": [
        (0.3, 4.1, "O pendrive com a ISO do FliperOS já liga em 15 kHz, direto no CRT.",
         "The FliperOS ISO boots straight to 15 kHz, right on the CRT."),
        (4.1, 8.4, "Install to HD/SSD: nem precisa de monitor LCD para instalar.",
         "Install to HD/SSD: no LCD monitor needed to install."),
        (8.4, 11.2, "Primeiro, o tipo de monitor ligado ao computador.",
         "First, the kind of monitor connected to the computer."),
        (11.2, 16.9, "Escolha o disco: modelo, tamanho e tipo de cada um.",
         "Pick the drive: model, size and bus of each one."),
        (17.0, 35.8, "A instalação mostra cada etapa e uma barra de progresso de verdade.",
         "The installation shows each step and a real progress bar."),
        (35.9, 40.3, "Pronto: tira o pendrive e reinicia.", "Done: remove the USB stick and reboot."),
    ],
    "s2": [
        (0.2, 3.5, "O primeiro boot do sistema instalado.", "The first boot of the installed system."),
        (3.5, 9.4, "Escolha o que abre ao ligar: o frontend do FliperOS é o padrão.",
         "Choose what starts at power-on: the FliperOS frontend is the default."),
        (9.4, 13.1, "O menu do FliperOS: tudo pelo joystick e pelos botões do painel.",
         "The FliperOS menu: everything from the panel's joystick and buttons."),
    ],
    "s3": [
        (0.2, 7.0, "Video Setup: monitor, resolução, geometria, jogos 480i e cor.",
         "Video Setup: monitor, resolution, geometry, 480i hacks and colour."),
        (7.0, 14.2, "Calibração de cor com botões − e +: muda na hora, até com um jogo aberto.",
         "Colour calibration with − and + buttons: it changes at once, even mid-game."),
        (14.4, 20.3, "Wi-Fi escolhido numa lista, com a senha digitada no próprio CRT.",
         "Wi-Fi picked from a list, with the password typed right on the CRT."),
        (20.5, 29.9, "Mapeamento de botões: aperte cada controle do painel quando ele pedir.",
         "Button mapping: press each control of the panel when it asks."),
        (30.0, 36.8, "Layout dos botões: onde ficam os botões de cada jogo, por quantos ele usa.",
         "Buttons layout: where a game's buttons go, by how many it uses."),
        (37.0, 46.5, "GunCon 2: uma calibração feita para o tubo, três cantos e um tiro de conferência.",
         "GunCon 2: a calibration made for the tube, three corners and a check shot."),
        (46.7, 54.1, "Emuladores e jogos: a versão de cada um e o que o update traz.",
         "Emulators & Games: each one's version and what its update brings."),
    ],
    "s3b": [
        (0.2, 12.1, "Latência: modo Standard ou Low latency, e a checagem deste computador.",
         "Latency: Standard or Low latency mode, and a check of this computer."),
        (12.3, 21.5, "What's new: o que mudou em cada versão e em cada update.",
         "What's new: what changed in each version and each update."),
        (21.7, 30.0, "Extras pela rede: Wine, Steam, Pixelcade, ZeDMD, pistolas e luzes.",
         "Extras over the network: Wine, Steam, Pixelcade, ZeDMD, guns and lights."),
        (30.2, 36.0, "Desligar e reiniciar no mesmo carrossel.", "Power off and reboot from the same carousel."),
    ],
    "s4": [
        (0.2, 9.0, "Downloader: os jogos vão direto para as pastas dos emuladores.",
         "Downloader: the games go straight to the emulator folders."),
        (9.2, 23.0, "O filtro do romset: jogadores, botões, controles, anos... e o placar de jogos e tamanho.",
         "The romset filter: players, buttons, controls, years... and the games and size counter."),
        (23.2, 29.3, "Cole o link magnet do romset do MAME, ou abra o navegador para achar.",
         "Paste the magnet link of the MAME romset, or open the browser to find it."),
        (29.4, 40.7, "Ele baixa só os jogos que passaram no filtro, em segundo plano.",
         "It downloads only the games that passed the filter, in the background."),
        (40.9, 47.3, "Download BIOS: as BIOS que os seus jogos pedem, conferidas pelo hash.",
         "Download BIOS: the BIOS your games need, checked by their hash."),
    ],
    "s5": [
        (0.2, 3.5, "O frontend do FliperOS abre com um guia dos botões do painel.",
         "The FliperOS frontend opens with a guide to the panel's buttons."),
        (3.6, 12.8, "Modo lista: o vídeo do jogo toca ao lado das informações.",
         "List view: the game's video plays next to its info."),
        (13.0, 27.5, "O [+] abre os clones, e um clone abre como qualquer jogo.",
         "The [+] unfolds the clones, and a clone opens like any game."),
        (28.0, 38.5, "O cartão e a página +: os botões no layout do seu painel e a descrição.",
         "The card and the + page: the buttons on your panel's layout and the description."),
        (38.6, 46.2, "À direita, fotos e mais dados. Texto comprido rola como letreiro.",
         "To the right, pictures and more data. Long text scrolls like a marquee."),
        (46.4, 56.2, "Filtros: favoritos, mais jogados e os filtros do Setup.",
         "Filters: favourites, most played and the Setup's own filters."),
        (56.4, 63.3, "Tab: classificar, renomear, fazer o scrape ou apagar um jogo.",
         "Tab: classify, rename, scrape or delete a game."),
        (63.5, 82.3, "Tela cheia: o vídeo de cada jogo ao fundo, e os clones com o selo CLONE.",
         "Full screen: each game's video behind it, and clones with a CLONE tag."),
        (82.5, 92.0, "Grade: cada miniatura toca o seu vídeo.", "Grid: every tile plays its own video."),
        (92.0, 101.0, "Jogar: o jogo abre no modo de vídeo certo para o tubo.",
         "Play: the game opens in the right video mode for the tube."),
        (101.0, 105.8, "Botão 4 favorita; Start troca o modo de exibição.",
         "Button 4 adds a favourite; Start switches the view."),
    ],
    "s5b": [
        (0.2, 14.4, "Naomi, Atomiswave, Model 2 e 3, MAME 2010: cada pasta é uma game list.",
         "Naomi, Atomiswave, Model 2 and 3, MAME 2010: each folder is a game list."),
        (14.5, 26.8, "Esquerda e direita trocam de lista; a arte e os vídeos chegam sozinhos.",
         "Left and right switch lists; the art and videos arrive by themselves."),
        (27.0, 45.8, "Model 2 pelo SM2-Emu, a toda velocidade até em CPUs antigas.",
         "Model 2 through SM2-Emu, at full speed even on older CPUs."),
    ],
}
W0 = WEB_START
SUBS["web"] = [] if not WEB else [
    (0.2, EV["search"] - W0, "Painel web: abra http://fliperos.local no celular, no tablet ou no PC.",
     "Web panel: open http://fliperos.local on a phone, tablet or PC."),
    (EV["search"] - W0, EV["before-play"] - W0, "Busque um jogo e veja tudo dele: fotos, botões no layout do painel, história.",
     "Search a game and see it all: pictures, buttons on the panel's layout, history."),
    (EV["before-play"] - W0, EV["live"] - W0, "Jogar: o jogo abre no gabinete. À esquerda, o tubo de verdade.",
     "Play: the game opens on the cabinet. On the left, the real tube."),
    (EV["live"] - W0, EV["settings"] - W0, "Ao vivo: a tela do gabinete no navegador, por WebRTC, e um endereço para o OBS.",
     "Live: the cabinet's screen in the browser over WebRTC, plus an address for OBS."),
    (EV["settings"] - W0, EV["status"] - W0, "Ajustes com o jogo aberto: a saturação muda no tubo enquanto o dedo anda.",
     "Settings mid-game: the saturation changes on the tube as the finger moves."),
    (EV["status"] - W0, EV["files"] - W0, "Status: FPS, o modo de vídeo de 15 kHz, CPU, GPU e um screenshot do tubo.",
     "Status: FPS, the 15 kHz video mode, CPU, GPU and a screenshot of the tube."),
    (EV["files"] - W0, EV["terminal"] - W0, "Arquivos, filtro de ROMs e downloads, tudo pelo navegador.",
     "Files, ROM filter and downloads, all from the browser."),
    (EV["terminal"] - W0, EV["close"] - W0, "Terminal: o shell do gabinete numa aba, sem instalar nada.",
     "Terminal: the cabinet's shell in a tab, with nothing to install."),
    (EV["close"] - W0, WEB_END - W0 - 0.3, "Fechar o jogo: o gabinete volta para o frontend.",
     "Close the game: the cabinet goes back to the frontend."),
]

PLAN = [("card", "intro", 7.0), ("card", "c1", 3.0), ("crt", "s1"), ("card", "c2", 3.0), ("crt", "s2"),
        ("card", "c3", 3.0), ("crt", "s3"), ("crt", "s3b"), ("card", "c4", 3.0), ("crt", "s4"),
        ("card", "c5", 3.0), ("crt", "s5"), ("crt", "s5b"), ("card", "c6", 3.0), ("web",), ("card", "outro", 8.0)]
if not WEB:
    PLAN = [p for p in PLAN if p not in (("web",), ("card", "c6", 3.0))]
CLIPS = {"s1": "s1_install.mkv", "s2": "s2_firstboot.mkv", "s3": "s3_setup.mkv", "s3b": "s3b_system.mkv",
         "s4": "s4_downloads.mkv", "s5": "s5_frontend.mkv", "s5b": "s5b_systems.mkv"}

background().save(OUT + "/bg.png")
bezel(SOLO).save(OUT + "/bezel_solo.png")
both = bezel(TUBE)
both.alpha_composite(tablet(TAB))
both.save(OUT + "/bezel_web.png")
scanlines(960, 720).save(OUT + "/scan.png")
for key, (big, pt, en, num) in CARDS.items():
    card(OUT + "/card_%s.png" % key, big, pt, en, ("CAPÍTULO %s · CHAPTER %s" % (num, num)) if num else None)

ONLY = os.environ.get("ONLY", "")
segs, subs, t = [], [], 0.0
for n, item in enumerate(PLAN):
    kind = item[0]
    if kind == "card":
        png = OUT + "/card_%s.png" % item[1]
        out, dur = ("%s/seg%02d.mp4" % (OUT, n), item[2]) if ONLY and ONLY != item[1] else seg_card(n, png, item[2])
    elif kind == "crt":
        clip = V + "/clips/" + CLIPS[item[1]]
        if not os.path.exists(clip):
            print("No %s (render.sh scenes): the video goes without it." % CLIPS[item[1]])
            continue
        dur = round(duration(clip) * FPS) / FPS
        out = "%s/seg%02d.mp4" % (OUT, n)
        if not ONLY or ONLY == item[1]:
            seg_crt(n, clip, dur)
        subs += [(t + a, t + b, p, e) for a, b, p, e in SUBS[item[1]]]
    else:
        dur = round((WEB_END - WEB_START) * FPS) / FPS
        out = "%s/seg%02d.mp4" % (OUT, n)
        if not ONLY or ONLY == "web":
            seg_web(n, WEB_START, WEB_START + dur, TUBE0)
        subs += [(t + a, t + b, p, e) for a, b, p, e in SUBS["web"]]
    segs.append(out)
    t += dur
    print("%-6s %-6s ends %6.1f" % (kind, item[1] if len(item) > 1 else "", t), flush=True)
write_subs(subs)
if not ONLY:
    with open(OUT + "/segs.txt", "w") as fh:
        fh.write("".join("file '%s'\n" % s for s in segs))
    run("ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", OUT + "/segs.txt", "-c", "copy",
        OUT + "/joined.mp4")
    run("ffmpeg", "-loglevel", "error", "-y", "-i", OUT + "/joined.mp4",
        "-vf", "ass=%s/subs.ass:fontsdir=/usr/share/fonts/truetype/noto" % OUT,
        "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", OUT + "/fliperos-apresentacao.mp4")
    run("ffmpeg", "-loglevel", "error", "-y", "-i", OUT + "/joined.mp4", "-c", "copy", "-movflags", "+faststart",
        OUT + "/fliperos-apresentacao-sem-legenda.mp4")
    print("total %.1f s" % t)
