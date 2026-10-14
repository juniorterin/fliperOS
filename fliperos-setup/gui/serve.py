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
NOTE = re.compile(r"^(.{2,}?) \((.+)\)$")


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
            found = None if hint else NOTE.match(label)
            if found:
                label, hint = found.group(1), found.group(2)[:1].upper() + found.group(2)[1:]
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

    def put(self, screen, name):
        """Mostra a tela e volta na hora (um aviso, o progresso)."""
        self.screen = screen
        self.shot(name)
        self.app.show(screen, self.ctx)

    def request(self):
        """O proximo pedido; enquanto ele nao chega, o fundo segue animado."""
        redraw = True
        while RS.encode() not in self.buf:
            if os.getppid() == 1:
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
                self.app.show(self.screen, self.ctx, redraw)
                redraw = False
            self.app.tick()
        record, self.buf = self.buf.split(RS.encode(), 1)
        return record.decode("utf-8", "replace").lstrip("\n").split(FS)

    def reply(self, rc, value=""):
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
            options = [(e[0], e[1]) for e in entries]
            if cmd == "radio" and style in ("people", "dots") and all(e[0].isdigit() for e in entries):
                # Ate quantos: as figuras acesas ate o valor.
                screen = W.Stepper(title, text, options, current if current in dict(options) else options[0][0], style)
            elif cmd == "check" and style == "controls":
                screen = W.ToggleGrid(title, text, [(v, label, "") for v, label in options], marked, 5, W.control_art)
            elif cmd == "check" and style == "years":
                screen = W.ToggleGrid(title, text, [(v, label, label[2:]) for v, label in options], marked, 6)
            else:
                screen = W.Menu(title, entries, current, text, cmd, marked)
            action, value = self.ask(screen, cmd)
            if action != "select":
                return 1, ""
            if cmd == "check":
                return 0, ",".join(e[0] for e in entries if e[0] in value)
            return 0, value
        if cmd == "board":
            items = []
            for arg in a[3:]:
                key, name, kind, data, about = (plain(arg).split(GS) + [""] * 4)[:5]
                items.append((key, name, kind, self.tile(kind, data), about))
            if not items:
                return 1, ""
            cursor = max(0, [i[0] for i in items].index(a[2]) if a[2] in [i[0] for i in items] else 0)
            action, value = self.ask(W.FilterBoard(plain(a[0]), items, cursor, note=plain(a[1])), cmd)
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
            # Com um botao (a[4], explicado em a[5]): status 3 quando e ele.
            button = (" button", plain(a[4]).upper(), plain(a[5])) if len(a) > 5 and a[4] else None
            screen = W.Input(plain(a[0]), self.lines([a[1]]), a[2], a[3] == "password", action=button)
            action, value = self.ask(screen, cmd)
            if action == "select" and button and value == button[0]:
                return 3, ""
            return (0, value) if action == "select" else (1, "")
        if cmd == "timed":
            screen = W.Timed(plain(a[0]), self.lines(a[3:]), plain(a[2]), int(a[1]))
            action, _ = self.ask(screen, cmd)
            return {"select": 0, "timeout": 124}.get(action, 1), ""
        if cmd == "pager":
            self.ask(W.Pager(plain(a[0]), plain(a[1]), a[2] == "inicio"), cmd)
            return 0, ""
        if cmd == "progress":
            pct = int(a[2]) if a[2].isdigit() else 0
            self.put(W.Live(plain(a[0]), plain(a[1]), pct, plain(a[3]), plain(a[4]), [plain(m) for m in a[5:]]), cmd)
            return 0, ""
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
    try:
        if not headless:
            app.load_sounds()
        server = Server(app, args.serve)
        # O Setup espera este arquivo para comecar a pedir telas.
        open(os.path.join(args.serve, "ready"), "w").close()
        server.run()
    finally:
        app.pygame.quit()
    return 0
