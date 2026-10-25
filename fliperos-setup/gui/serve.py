# O servidor da interface grafica: desenha as telas que o fliperos-setup
# pede (lib/ui.sh) e devolve a resposta.
#
# O Setup e Bash: cada ui_menu, ui_yesno etc. escreve um pedido em PASTA/req
# e le a resposta em PASTA/resp (dois FIFOs). Um pedido sao campos separados
# por \x1f e terminados por \x1e:
#
#     comando \x1f status \x1f versao \x1f argumento... \x1e
#
# e a resposta e "codigo \x1f texto \x1e" (o codigo e o status de saida da
# funcao do ui.sh: 0, 1 = Esc, 124 = o tempo acabou). Os itens de um menu vem
# como "valor \x1d rotulo \x1d dica".
#
# Entre um pedido e outro a ultima tela fica no video, com o fundo animado.
#
# Para os testes: FLIPEROS_GUI_HEADLESS=1 roda sem video, FLIPEROS_GUI_KEYS
# sao teclas apertadas em ordem e FLIPEROS_GUI_SHOTS e a pasta onde cada
# tela e gravada em PNG.

import errno
import os
import re
import select
import signal
import time

FS, RS, GS = "\x1f", "\x1e", "\x1d"
SGR = re.compile(r"\x1b\[([0-9;]*)m")
# Um rotulo com a explicacao entre parenteses no fim.
NOTE = re.compile(r"^(.*\S) \(([^()]+)\)$")


def plain(s):
    return SGR.sub("", s)


class Server:
    def __init__(self, app, directory):
        import theme as T
        import widgets

        self.app, self.W, self.T = app, widgets, T
        self.dir = directory
        self.req = os.open(os.path.join(directory, "req"), os.O_RDWR | os.O_NONBLOCK)
        self.buf = b""
        self.ctx = {"status": "", "version": ""}
        self.screen = None      # a tela que esta no video
        self.parent = os.getppid()  # o Setup: sem ele, o servidor sai
        self.replied = time.monotonic()  # a ultima resposta (a ampulheta)
        self.shots = os.environ.get("FLIPEROS_GUI_SHOTS", "")
        self.count = 0
        # As cores do ui_c (lib/ui.sh): 30 + indice ate 7, 82 + indice depois.
        self.colors = {31: T.RED, 32: T.GREEN, 33: T.YELLOW, 34: T.PURPLE, 35: T.PINK, 36: T.CYAN,
                       90: T.COMMENT, 93: T.ORANGE}

    def lines(self, args):
        """Os textos de uma tela como linhas (texto, cor): cada linha fica
        com a cor do primeiro trecho colorido dela."""
        out = []
        for arg in args:
            for line in arg.split("\n"):
                found = SGR.search(line)
                code = int(found.group(1) or 0) if found and found.group(1).isdigit() else 0
                out.append((plain(line), self.colors.get(code, self.T.FG)))
        return out

    def entries(self, args):
        """Os itens de um menu: (valor, rotulo, dica). Um rotulo sem dica que
        termina com um parentese ("Pixelcade (LED/LCD marquee)") vira o nome
        e a dica: o nome cabe grande no carrossel."""
        out = []
        for arg in args:
            value, label, hint = (plain(arg).split(GS) + ["", ""])[:3]
            # Cada parentese do fim vira uma frase da dica, na ordem:
            # "Hypseus Singe (Laserdisc) (installed)" -> "Laserdisc. Installed".
            notes = []
            found = NOTE.match(label)
            while found:
                notes.insert(0, found.group(2)[:1].upper() + found.group(2)[1:])
                label = found.group(1)
                found = NOTE.match(label)
            if notes:
                hint = ". ".join(notes + ([hint] if hint else []))
            out.append((value, label, hint))
        return out

    @staticmethod
    def tile(kind, data):
        """O dado de um azulejo do ui_board, do texto do pedido para o que o
        mini() de widgets.py desenha."""
        def flags(s):
            return [x == "1" for x in s.split(",")]

        if kind in ("people", "dots"):
            n, _, top = data.partition(",")
            return (int(n) if n.isdigit() else 0, int(top) if top.isdigit() else 8)
        if kind == "switch":
            on, _, label = data.partition(",")
            return (on == "1", label)
        if kind == "blocks":
            marks, _, label = data.partition(";")
            return (flags(marks), label)
        if kind == "lamps":
            return int(data) if data.isdigit() else 0
        if kind == "screens":
            return tuple((flags(data) + [False, False])[:2])
        return data.upper()

    def download(self, title, pct, step, msgs):
        """A tela do download do Downloader a partir da linha de status do
        fliperos-downloader ("ROMs 3.5 GB of 9.6 GB, 18 peers; CHDs ...;
        2.4 MB/s, 3 h left"): uma barra por torrent, a velocidade e o tempo."""
        units = {"B": 1, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12}

        def size(s):
            found = re.match(r"([\d.]+)\s*([KMGT]?)", s.replace(",", "."))
            return float(found.group(1)) * units[found.group(2) or "B"] if found else 0

        parts, speed, left = [], "-", "-"
        for line in [step] + msgs:
            found = re.match(r"^(\S+) (.+?) of (.+?)(?:, (\d+) peers)?(?: \((.+)\))?$", line)
            rate = re.match(r"^(.+)/s, (.+) left$", line)
            if rate:
                speed, left = rate.group(1) + "/s", rate.group(2)
            elif found:
                total = size(found.group(3))
                frac = size(found.group(2)) / total if total else 0
                parts.append((found.group(1).upper(), found.group(2), found.group(3), int(found.group(4) or 0),
                              min(1, frac)))
            elif line.strip():
                name, _, state = line.partition(" ")
                parts.append((name.upper(), state.upper(), "", 0, 1 if state == "done" else 0))
        return self.W.Download(title, parts[:2], pct, speed, left)

    # O laco -----------------------------------------------------------

    def shot(self, name):
        if self.shots:
            self.count += 1
            self.app.fixed_time = 3.0
            self.app.save(self.screen, self.ctx, os.path.join(self.shots, "%03d-%s" % (self.count, name)))

    def ask(self, screen, name):
        """Mostra a tela e espera a resposta dela."""
        app = self.app
        self.screen = screen
        app.flush()
        self.shot(name)
        redraw = True
        while True:
            # O Setup morto com a tela aberta (o painel web fechando o menu
            # para abrir um jogo, um SIGKILL): sem sair daqui, o servidor
            # ficava orfao e dono da placa, e nem o X do jogo nem a proxima
            # interface abriam.
            if os.getppid() != self.parent:
                raise SystemExit(0)
            for key in app.keys():
                if key == "quit":
                    return ("back", None)
                app.beep(key)
                result = screen.key(key)
                redraw = True
                if result:
                    return result
            tick = getattr(screen, "tick", None)
            result = tick() if tick else None
            if result == "redraw":
                redraw = True
            elif result:
                return result
            app.show(screen, self.ctx, redraw)
            redraw = False
            app.tick()

    def busy(self):
        """A ampulheta: num aviso de "aguarde" ou no progresso, e quando a
        tela respondida fica parada mais de 0,3 s (o Setup esta trabalhando
        antes da proxima)."""
        if isinstance(self.screen, self.W.Live) or (isinstance(self.screen, self.W.Message)
                                                   and not self.screen.wait):
            return True
        return self.screen is not None and time.monotonic() - self.replied > 0.3

    def put(self, screen, name):
        """Mostra a tela e volta na hora (um aviso, o progresso)."""
        self.screen = screen
        self.shot(name)
        self.app.show(screen, self.ctx)

    def request(self):
        """O proximo pedido; enquanto ele nao chega, o fundo segue animado."""
        redraw = True
        while RS.encode() not in self.buf:
            if os.getppid() != self.parent:
                raise SystemExit(0)     # o Setup morreu
            ready, _, _ = select.select([self.req], [], [], 0)
            if ready:
                try:
                    self.buf += os.read(self.req, 65536)
                except BlockingIOError:
                    pass
                continue
            if self.app.window is not None:
                self.app.pygame.event.pump()
                # Uma tela que muda sozinha (o tempo do Button mapping).
                tick = getattr(self.screen, "tick", None)
                if tick and tick() == "redraw":
                    redraw = True
                self.app.show(self.screen, self.ctx, redraw, self.busy())
                redraw = False
            self.app.tick()
        record, self.buf = self.buf.split(RS.encode(), 1)
        return record.decode("utf-8", "replace").lstrip("\n").split(FS)

    def reply(self, rc, value=""):
        self.replied = time.monotonic()
        data = ("%d%s%s%s" % (rc, FS, value, RS)).encode()
        path = os.path.join(self.dir, "resp")
        deadline = time.monotonic() + 10
        while True:
            try:
                fd = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
                break
            except OSError as error:
                # Ainda ninguem lendo: o Setup abre o FIFO logo depois de pedir.
                if error.errno != errno.ENXIO or time.monotonic() > deadline:
                    return
                time.sleep(0.005)
        try:
            os.set_blocking(fd, True)
            os.write(fd, data)
        except OSError:
            pass
        finally:
            os.close(fd)

    # Os pedidos -------------------------------------------------------

    def handle(self, cmd, a):
        W = self.W
        if cmd in ("menu", "radio", "check"):
            title, text, current, style = plain(a[0]), plain(a[1]), a[2], a[3]
            entries = self.entries(a[4:])
            if not entries:
                return 1, ""
            marked = current.split(",") if cmd == "check" else [current] if cmd == "radio" else []
            tiles = {}
            if style == "layout":
                # Buttons layout: "3-button games   [ ][ ][ ] / [1][2][3]" vira
                # o nome e o icone do painel com os botoes nas posicoes.
                fixed = []
                for value, label, hint in entries:
                    cells = re.findall(r"\[(.)\]", label)
                    if len(cells) == 6:
                        tiles[value] = W.layout_tile([cells.index(str(n)) + 1 for n in range(1, 7) if str(n) in cells])
                        label = label.split("  ")[0].strip()
                    fixed.append((value, label, hint))
                entries = fixed
            options = [(e[0], e[1]) for e in entries]
            if cmd == "radio" and style in ("people", "dots") and all(e[0].isdigit() for e in entries):
                # Ate quantos: as figuras acesas ate o valor.
                screen = W.Stepper(title, text, options, current if current in dict(options) else options[0][0], style)
            elif cmd == "check" and style == "controls":
                screen = W.ToggleGrid(title, text, [(v, label, "") for v, label in options], marked, 5, W.control_art)
            elif cmd == "check" and style == "years":
                screen = W.ToggleGrid(title, text, [(v, label, label[2:]) for v, label in options], marked, 6)
            else:
                screen = W.Menu(title, entries, current, text, cmd, marked, tiles, vertical=style == "list")
            action, value = self.ask(screen, cmd)
            if action != "select":
                return 1, ""
            if cmd == "check":
                return 0, ",".join(e[0] for e in entries if e[0] in value)
            return 0, value
        if cmd == "board":
            items = []
            for arg in a[4:]:
                key, name, kind, data, about = (plain(arg).split(GS) + [""] * 4)[:5]
                items.append((key, name, kind, self.tile(kind, data), about))
            if not items:
                return 1, ""
            cursor = max(0, [i[0] for i in items].index(a[2]) if a[2] in [i[0] for i in items] else 0)
            # a[3]: o arquivo do placar, que a contagem do Setup escreve depois.
            action, value = self.ask(W.FilterBoard(plain(a[0]), items, cursor, note=plain(a[1]), score=a[3]), cmd)
            return (0, value) if action == "select" else (1, "")
        if cmd == "grid":
            # titulo, texto, colunas ("valor|rotulo" separados por GS), opcoes
            # ("ask=valor;cursor=chave"), linhas ("chave GS rotulo GS coluna
            # marcada GS ajuda GS valores permitidos")... Status 2: a linha
            # foi marcada na coluna do ask (a chave e as marcas, numa linha
            # cada).
            columns = [tuple(c.split("|", 1)) for c in plain(a[2]).split(GS) if "|" in c]
            opts = dict(o.split("=", 1) for o in plain(a[3]).split(";") if "=" in o)
            rows = [tuple((plain(r).split(GS) + [""] * 4)[:5]) for r in a[4:]]
            if not columns or not rows:
                return 1, ""
            grid = W.Grid(plain(a[0]), plain(a[1]), columns, rows, ask=opts.get("ask", ""),
                          cursor=opts.get("cursor", ""), live=opts.get("live", "0") == "1")
            action, value = self.ask(grid, cmd)
            if action == "ask":
                return 2, value
            return (0, value) if action == "select" else (1, "")
        if cmd == "yesno":
            screen = W.YesNo(plain(a[0]), self.lines(a[4:]), a[1], plain(a[2]).upper(), plain(a[3]).upper())
            action, value = self.ask(screen, cmd)
            return (0 if action == "select" and value == "yes" else 1), ""
        if cmd in ("msg", "info"):
            lines = self.lines(a[1:])
            kind = "error" if any(color == self.T.RED for _, color in lines) else "info"
            screen = W.Message(plain(a[0]), lines, kind, wait=cmd == "msg")
            if cmd == "msg":
                self.ask(screen, cmd)
            else:
                self.put(screen, cmd)
            return 0, ""
        if cmd == "input":
            # Com botoes (a partir de a[4], pares rotulo e explicacao): status
            # 3 para o primeiro, 4 para o segundo...
            buttons = [(" button%d" % i, plain(a[j]).upper(), plain(a[j + 1]))
                       for i, j in enumerate(range(4, len(a) - 1, 2)) if a[j]]
            # A senha (e o SSID oculto, "keyboard") com o teclado na tela.
            screen = W.Input(plain(a[0]), self.lines([a[1]]), a[2], a[3] == "password", action=buttons,
                             keyboard=a[3] in ("password", "keyboard"))
            action, value = self.ask(screen, cmd)
            for i, b in enumerate(buttons):
                if action == "select" and value == b[0]:
                    return 3 + i, ""
            return (0, value) if action == "select" else (1, "")
        if cmd == "timed":
            screen = W.Timed(plain(a[0]), self.lines(a[3:]), plain(a[2]), int(a[1]))
            action, _ = self.ask(screen, cmd)
            return {"select": 0, "timeout": 124}.get(action, 1), ""
        if cmd == "pager":
            self.ask(W.Pager(plain(a[0]), plain(a[1]), a[2] == "inicio"), cmd)
            return 0, ""
        if cmd == "progress":
            # titulo, alvo, porcento, etapa, rodape, estilo, mensagens...
            pct = int(a[2]) if a[2].isdigit() else 0
            msgs = [plain(m) for m in a[6:]]
            if a[5] == "download":
                self.put(self.download(plain(a[0]), pct, plain(a[3]), msgs), cmd)
            else:
                self.put(W.Live(plain(a[0]), plain(a[1]), pct, plain(a[3]), plain(a[4]), msgs), cmd)
            return 0, ""
        if cmd == "capture":
            # titulo, jogador, comando, numero, total, segundos, ja apertados...
            self.put(W.Capture(plain(a[0]), int(a[1]), a[2], a[6:], int(a[3]), int(a[4]), int(a[5]), int(a[5])), cmd)
            return 0, ""
        if cmd == "layout":
            # titulo, botoes do jogo, padrao (1 = oferecer), posicoes ja postas...
            order = [int(p) for p in a[3:] if p.isdigit()]
            action, value = self.ask(W.LayoutEdit(plain(a[0]), int(a[1]), order, a[2] == "1"), cmd)
            return (0, str(value)) if action == "select" else (1, "")
        if cmd == "keywait":
            deadline = time.monotonic() + float(a[0])
            while time.monotonic() < deadline:
                if self.app.keys():
                    return 0, ""
                self.app.show(self.screen, self.ctx, False)
                self.app.tick()
            return 1, ""
        if cmd == "suspend":
            self.app.close()
            return 0, ""
        if cmd == "resume":
            if self.app.window is None:
                self.app.open()
            self.app.show(self.screen, self.ctx)
            return 0, ""
        if cmd == "orient":
            # A orientacao do monitor mudou em Video Setup: a imagem gira ja.
            self.app.set_orientation(a[0])
            self.app.show(self.screen, self.ctx)
            return 0, ""
        if cmd == "ping":
            return 0, ""
        return 2, ""

    def run(self):
        while True:
            fields = self.request()
            if len(fields) < 3:
                continue
            cmd, self.ctx["status"], self.ctx["version"] = fields[0], fields[1], fields[2]
            if cmd == "quit":
                self.reply(0)
                return
            try:
                rc, value = self.handle(cmd, fields[3:])
            except (IndexError, ValueError):
                rc, value = 2, ""
            self.reply(rc, value)


def main(App, args):
    def stop(*_):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGHUP, stop)
    headless = os.environ.get("FLIPEROS_GUI_HEADLESS") == "1"
    app = App(False, headless, args.bg, os.environ.get("FLIPEROS_GUI_KEYS", "").split())
    # Um fundo por abertura do menu, nunca o mesmo da vez anterior: o ultimo
    # fica ao lado da pasta do servidor (que o Setup refaz a cada abertura).
    import background

    last = os.path.join(os.path.dirname(os.path.abspath(args.serve)), "gui-background")
    try:
        with open(last) as f:
            previous = f.read().strip()
    except OSError:
        previous = None
    # gui-background-next: um fundo pedido para a proxima abertura (stars,
    # snow, water, fire ou smoke), usado uma vez.
    try:
        with open(last + "-next") as f:
            wanted = f.read().strip()
        os.remove(last + "-next")
    except OSError:
        wanted = ""
    if not args.bg:
        if wanted in background.BACKGROUNDS:
            app.bg = background.pick(wanted, seed=os.getpid())
        else:
            app.bg = background.pick(exclude=previous)
    try:
        with open(last, "w") as f:
            f.write(getattr(app.bg, "name", ""))
    except OSError:
        pass
    try:
        if not headless:
            app.load_sounds()
        server = Server(app, args.serve)
        # O Setup espera este arquivo para comecar a pedir telas.
        open(os.path.join(args.serve, "ready"), "w").close()
        server.run()
    finally:
        app.close()
        app.pygame.quit()
    return 0
