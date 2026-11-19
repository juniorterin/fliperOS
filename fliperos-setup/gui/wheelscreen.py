# A tela da calibracao de volante, pedais e analogico na interface grafica:
# o config/fliperos-calibrate a usa no lugar do desenho no terminal quando o
# Setup esta na interface grafica (FLIPEROS_CALIBRATE_GUI=1), como a
# gunscreen.py na GunCon 2. Tem a conversa da Screen de la para os eixos
# (axes(state), key, flush, restore): o calibrador manda o estado inteiro a
# cada quadro (AxesSession.state) e esta tela so desenha.
#
# O fundo e o animado que o menu do Setup sorteou (FLIPEROS_GUI_BG), com o
# letreiro e a legenda das teclas do frame() dos widgets. O volante gira
# com o de verdade, os pedais enchem, os botoes acendem e ficam verdes
# depois de apertados (o teste deles), e no fim o force feedback puxa e
# treme. Em pe (FLIPEROS_GUI_ORIENTATION), a tela de 240x320 gira inteira.

import math
import os
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

import theme as T  # noqa: E402

T.set_orientation(os.environ.get("FLIPEROS_GUI_ORIENTATION", "horizontal"))

import background  # noqa: E402
import tiny  # noqa: E402
import widgets as W  # noqa: E402

FPS = 30
# A cor de cada pedal pela ordem (o primeiro costuma ser o acelerador).
PEDAL_COLORS = [T.GREEN, T.RED, T.ORANGE, T.PURPLE]
# O arco do curso em volta do volante: de -135 a +135 graus do topo.
GAUGE = 135


class WheelScreen:
    def __init__(self, window=True):
        background.set_size(T.WIDTH, T.HEIGHT)
        self.bg = background.pick(os.environ.get("FLIPEROS_GUI_BG") or None)
        self.surf = pygame.Surface((T.WIDTH, T.HEIGHT))
        self.ui = pygame.Surface((T.WIDTH, T.HEIGHT), pygame.SRCALPHA)
        self.start = time.monotonic()
        self.fixed_time = None   # os prints: um instante fixo do fundo
        self.drawn = 0.0
        self.hat_tested = set()   # os lados do direcional ja apertados
        self.window = None
        pygame.font.init()
        if window:
            self.open()

    def open(self):
        T.request_vsync()
        pygame.display.init()
        size, flags = T.MODE, 0
        if os.environ.get("SDL_VIDEODRIVER", "kmsdrm") == "kmsdrm":
            flags = pygame.FULLSCREEN
            modes = pygame.display.list_modes()
            if not isinstance(modes, list) or size not in modes:
                info = pygame.display.Info()
                size = (info.current_w, info.current_h)
        self.window = pygame.display.set_mode(size, flags)
        pygame.mouse.set_visible(False)

    # A conversa da Screen do calibrador ---------------------------------

    def key(self):
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "\033"
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return "\n"
        return ""

    def flush(self):
        if self.window is not None:
            pygame.event.clear()

    def restore(self):
        if self.window is None:
            return
        pygame.display.quit()
        try:
            import drmmaster
            drmmaster.drop()
        except Exception:
            pass
        self.window = None

    def axes(self, state):
        now = time.monotonic()
        if now - self.drawn < 1 / FPS:
            return
        self.drawn = now
        frame = T.upright(self.render(state))
        pygame.transform.scale(frame, self.window.get_size(), self.window)
        pygame.display.flip()

    # O desenho ----------------------------------------------------------

    def render(self, state):
        """O quadro na tela logica: o fundo do Setup e, por cima, a tela."""
        t = self.fixed_time if self.fixed_time is not None else time.monotonic() - self.start
        ui = self.ui
        title = "WHEEL & PEDALS" if state["wheel"] else "CONTROLLER"
        W.frame(ui, {"status": ""}, title, state["keys"])
        self.header(ui, state, t)
        top = self.instructions(ui, state)
        hold_y = W.footer_y() - 7
        if state["step"] == "buttons":
            self.controller(ui, state, top, hold_y - 4)
        elif state["step"] in ("result", "nomove"):
            self.panel(ui, state, top, hold_y - 4)
        else:
            self.controls(ui, state, top, hold_y - 4, t)
        self.hold_bar(ui, state["hold"], hold_y)
        self.bg.draw(self.surf, t)
        self.surf.blit(ui, (0, 0))
        return self.surf

    def header(self, ui, state, t):
        name = plain_name(state["name"]).upper()
        w = W.width(name)
        if w <= T.SAFE_W:
            W.text(ui, name, T.COMMENT, (T.WIDTH - w) // 2, 30)
        else:
            W.scroll_text(ui, name, T.COMMENT, T.SAFE_X, 30, T.SAFE_W)

    def instructions(self, ui, state):
        y = 42
        for line in state["text"]:
            for part in W.wrap(line, T.SAFE_W):
                W.centered(ui, part, T.FG, y)
                y += 10
        if state["step"] == "ff" and state["ff"]:
            y = self.ff_chips(ui, state["ff"], y + 3)
        return y + 4

    def ff_chips(self, ui, ff, y):
        """As etapas do teste: a que esta tocando em amarelo, as feitas em
        verde (com o lado que o volante andou), as outras apagadas."""
        labels = []
        for i, (phase, moved) in enumerate(ff["phases"]):
            if phase == "shake":
                label = "SHAKE"
            else:
                label = {-1: "< PULL", 1: "PULL >"}.get(moved, "PULL")
            labels.append(label)
        widths = [W.width(s) + 8 for s in labels]
        x = (T.WIDTH - sum(widths) - 6 * (len(labels) - 1)) // 2
        for i, (label, w) in enumerate(zip(labels, widths)):
            playing = i == ff["phase"]
            done = ff["phase"] < 0 or i < ff["phase"]
            if playing:
                W.block(ui, (x, y, w, 12), T.YELLOW, T.SPACE)
                W.text(ui, label, T.SPACE, x + 4, y + 2)
            else:
                pygame.draw.rect(ui, T.BG_DEEP, (x, y, w, 12))
                pygame.draw.rect(ui, T.GREEN if done else T.LINE, (x, y, w, 12), 1)
                W.text(ui, label, T.GREEN if done else T.COMMENT, x + 4, y + 2)
            x += w + 6
        return y + 14

    # Os eixos -----------------------------------------------------------

    def controls(self, ui, state, top, bottom, t):
        axes = state["axes"]
        wheel = next((a for a in axes if a["kind"] == "wheel"), None)
        pedals = [a for a in axes if a["kind"] == "pedal"]
        sticks, others = pairs([a for a in axes if a["kind"] == "center"])
        shake = state["step"] == "ff" and state["ff"] and state["ff"]["phase"] >= 0 \
            and state["ff"]["phases"][state["ff"]["phase"]][0] == "shake"
        jitter = (round(math.sin(t * 90)), 0) if shake else (0, 0)
        portrait = T.HEIGHT > T.WIDTH
        big = [wheel] if wheel else []
        if portrait:
            # Em pe: o volante (ou os analogicos) em cima, os pedais embaixo.
            split = top + (bottom - top) * 3 // 5 if pedals or others else bottom
            self.main_area(ui, big, sticks, others if not pedals else [], (T.SAFE_X, top, T.SAFE_W, split - top),
                           state, jitter)
            if pedals or (others and big + sticks):
                self.pedals(ui, pedals, others if pedals else [], (T.SAFE_X, split + 6, T.SAFE_W, bottom - split - 6))
            return
        # Deitado: o volante a esquerda, os pedais a direita.
        if pedals:
            split = T.SAFE_X + T.SAFE_W * 9 // 16 if big + sticks else T.SAFE_X
            if big + sticks:
                self.main_area(ui, big, sticks, [], (T.SAFE_X, top, split - T.SAFE_X, bottom - top), state, jitter)
            self.pedals(ui, pedals, others, (split, top, T.SAFE_X + T.SAFE_W - split, bottom - top))
        else:
            self.main_area(ui, big, sticks, others, (T.SAFE_X, top, T.SAFE_W, bottom - top), state, jitter)

    def main_area(self, ui, big, sticks, others, rect, state, jitter):
        x, y, w, h = rect
        rows = len(others)
        bars_h = rows * 18
        area_h = h - bars_h
        items = big + sticks
        if items:
            cell = w // len(items)
            for i, item in enumerate(items):
                cx = x + cell * i + cell // 2
                if isinstance(item, dict):
                    # O arco (r + 7) e o texto dos graus embaixo (14) cabem na area.
                    g = max(20, min(cell // 2 - 4, (area_h - 14) // 2))
                    cy = y + (area_h - 14 - 2 * g) // 2 + g
                    self.wheel(ui, item, cx + jitter[0], cy, g - 7, state["degrees"], state.get("layout"))
                else:
                    r = max(12, min(cell // 2 - 10, (area_h - 10) // 2 - 2))
                    self.stick(ui, item, cx, y + (area_h - 10) // 2, r)
        by = y + area_h
        for axis in others:
            self.hbar(ui, axis, (x + 4, by, w - 8, 16))
            by += 18

    def wheel(self, ui, axis, cx, cy, r, degrees, layout=None):
        """O volante visto de frente, girado como o de verdade, e o arco do
        curso: o trecho ja alcancado em amarelo e a posicao em ciano."""
        frac = axis["frac"]
        turn = frac * (degrees / 2 if degrees else GAUGE)
        g = r + 7
        rect = (cx - g, cy - g, 2 * g, 2 * g)
        lo, hi = min(axis["seen"]), max(axis["seen"])
        arc(ui, T.LINE, rect, -GAUGE, GAUGE, 3)
        arc(ui, T.YELLOW, rect, lo * GAUGE, hi * GAUGE, 3)
        dot = polar(cx, cy, g, frac * GAUGE)
        pygame.draw.circle(ui, T.SPACE, dot, 4)
        pygame.draw.circle(ui, T.CYAN, dot, 3)
        # O volante desenhado parado e girado inteiro, com a sombra fixa.
        pygame.draw.circle(ui, T.SPACE, (cx + 2, cy + 3), r)
        art = pygame.transform.rotate(wheel_with_caps(r, layout), -turn)
        ui.blit(art, art.get_rect(center=(cx, cy)))
        label = wheel_text(frac, degrees)
        W.text(ui, label, T.FG, cx - W.width(label) // 2, cy + g + 6)

    def stick(self, ui, pair, cx, cy, r):
        """Um analogico: a caixa, a cruz do centro, o curso visto e a bola."""
        ax, ay = pair
        pygame.draw.rect(ui, T.BG_DEEP, (cx - r, cy - r, 2 * r, 2 * r))
        pygame.draw.rect(ui, T.LINE, (cx - r, cy - r, 2 * r, 2 * r), 1)
        pygame.draw.line(ui, T.LINE, (cx - r, cy), (cx + r, cy))
        pygame.draw.line(ui, T.LINE, (cx, cy - r), (cx, cy + r))
        x0, x1 = (round(cx + f * r) for f in sorted(ax["seen"]))
        y0, y1 = (round(cy + f * r) for f in sorted(ay["seen"]))
        pygame.draw.rect(ui, T.YELLOW, (x0, y0, max(1, x1 - x0), max(1, y1 - y0)), 1)
        bx, by = round(cx + ax["frac"] * r), round(cy + ay["frac"] * r)
        pygame.draw.circle(ui, T.SPACE, (bx + 1, by + 2), 5)
        pygame.draw.circle(ui, T.CYAN, (bx, by), 5)
        tiny.centered(ui, "%s / %s" % (ax["label"], ay["label"]), T.COMMENT, cx, cy + r + 4)

    def hbar(self, ui, axis, rect):
        """Um eixo centrado avulso: a barra do meio para o lado."""
        x, y, w, h = rect
        tiny.text(ui, axis["label"], T.COMMENT, x, y)
        bx, bw, by = x, w, y + 7
        pygame.draw.rect(ui, T.BG_DEEP, (bx, by, bw, 7))
        mid = bx + bw // 2
        pos = round(mid + axis["frac"] * (bw // 2))
        pygame.draw.rect(ui, T.CYAN, (min(mid, pos), by, max(1, abs(pos - mid)), 7))
        for f in axis["seen"]:
            pygame.draw.line(ui, T.YELLOW, (round(mid + f * (bw // 2)), by), (round(mid + f * (bw // 2)), by + 6))
        pygame.draw.line(ui, T.FG, (mid, by - 1), (mid, by + 7))

    def pedals(self, ui, pedals, others, rect):
        """Os pedais em barras de pe: enchem de baixo para cima com a pressao,
        o maximo ja alcancado fica marcado em amarelo."""
        x, y, w, h = rect
        items = pedals + others
        if not items:
            return
        step = min(40, w // len(items))
        bw = min(22, step - 10)
        x0 = x + (w - step * len(items)) // 2 + (step - bw) // 2
        bar_top, bar_h = y + 12, max(16, h - 26)
        for i, axis in enumerate(items):
            bx = x0 + i * step
            label = axis["label"]
            if axis["kind"] != "pedal":
                frac, top = (axis["frac"] + 1) / 2, (max(axis["seen"]) + 1) / 2
                color = T.CYAN
            else:
                frac, top = axis["frac"], max(axis["seen"])
                color = PEDAL_COLORS[pedals.index(axis) % len(PEDAL_COLORS)]
            pct = "%d%%" % round(frac * 100)
            tiny.centered(ui, pct, T.FG, bx + bw // 2, y + 3)
            pygame.draw.rect(ui, T.SPACE, (bx + 2, bar_top + 2, bw, bar_h))
            pygame.draw.rect(ui, T.BG_DEEP, (bx, bar_top, bw, bar_h))
            fill = round(frac * (bar_h - 2))
            if fill:
                pygame.draw.rect(ui, color, (bx + 1, bar_top + bar_h - 1 - fill, bw - 2, fill))
                pygame.draw.rect(ui, W.shade(color, 1.4), (bx + 1, bar_top + bar_h - 1 - fill, bw - 2, 1))
            # As ranhuras do pedal, por cima do enchimento.
            for gy in range(bar_top + 4, bar_top + bar_h - 2, 5):
                pygame.draw.line(ui, W.shade(T.SPACE, 1.0), (bx + 3, gy), (bx + bw - 4, gy))
            mark = bar_top + bar_h - 1 - round(top * (bar_h - 2))
            if top > 0.01:
                pygame.draw.rect(ui, T.YELLOW, (bx - 2, mark - 1, bw + 4, 2))
            pygame.draw.rect(ui, T.LINE, (bx, bar_top, bw, bar_h), 1)
            tiny.centered(ui, label, T.COMMENT, bx + bw // 2, bar_top + bar_h + 4)

    # A tela dos botoes ---------------------------------------------------

    def controller(self, ui, state, top, bottom):
        """O controle desenhado com cada botao no lugar dele (o volante de
        frente ou o joypad); aceso enquanto apertado, verde depois de
        testado. Os botoes sem lugar vao numa fileira embaixo."""
        layout = state["layout"]
        family, symbols, slots = layout["family"], layout["symbols"], layout["slots"]
        hat = state["hat"]
        if hat is not None and hat != (0, 0):
            self.hat_tested.update(d for d in ((hat[0], 0), (0, hat[1])) if d != (0, 0))
        if family == "grid":
            self.buttons(ui, state, bottom, top)
            return
        placed = {slot: (i, st) for i, (slot, st) in enumerate(zip(slots, state["buttons"])) if slot}
        extra = [(i, st) for i, (slot, st) in enumerate(zip(slots, state["buttons"])) if not slot]
        if extra:
            bottom = self.extra_row(ui, extra, bottom)
        h = bottom - top
        ui.set_clip(pygame.Rect(0, top, T.WIDTH, h))
        if family == "wheel":
            spots = WHEEL_SPOTS
            used = [spots[s] for s in spots if s in placed or (s == "dpad" and hat is not None)]
            if T.HEIGHT > T.WIDTH:
                # Em pe ha altura: o volante inteiro, com o cambio embaixo.
                spots = dict(WHEEL_SPOTS, gear_up=(0.88, 1.24, 'gear'), gear_down=(0.88, 1.54, 'gear'))
                used = [spots[s] for s in spots if s in placed or (s == "dpad" and hat is not None)]
                used += [(-1.0, 0, 'rim'), (1.0, 0, 'rim'), (0, -1.0, 'rim'), (0, 1.0, 'rim')]
                cx, cy, r = fit_zone(used, (T.SAFE_X, top, T.SAFE_W, h))
            else:
                # Deitado: so a regiao dos botoes, ampliada; o aro fica
                # cortado em cima e logo abaixo do botao mais baixo.
                cx, cy, r = fit_zone(used, (T.SAFE_X, top, T.SAFE_W, h))
                low = max(sy + EXTENT[k][1] for _sx, sy, k in used)
                ui.set_clip(pygame.Rect(0, top, T.WIDTH, min(h, round(cy + low * r) + 6 - top)))
            for side, slot in ((-1, "l1"), (1, "r1")):
                if slot in placed:
                    i, (pressed, tested) = placed[slot]
                    draw_paddle(ui, cx, cy, r, side, slot_label(slot, family, symbols, i)[0],
                                "ask" if pressed else "done" if tested else "todo")
            draw_wheel_face(ui, cx, cy, r)
        else:
            spots = PAD_SPOTS
            # Dos gatilhos (-0.9 raio) ao fim das alcas (+0.8): 1.7 raios de altura.
            r = max(24, min(int((h - 12) / 1.75), int(T.SAFE_W / 2.6)))
            cx, cy = T.WIDTH // 2, top + 6 + int(r * 0.92)
            draw_pad_body(ui, cx, cy, r)
        s = r / 60
        dpad_buttons = {k: placed[k] for k in ("dup", "ddown", "dleft", "dright") if k in placed}
        if "dpad" in spots and (hat is not None or dpad_buttons):
            x, y = spots["dpad"][:2]
            self.dpad_big(ui, round(cx + x * r), round(cy + y * r), s, hat, dpad_buttons)
        for slot, (i, (pressed, tested)) in placed.items():
            if slot not in spots or slot.startswith("d") and slot in dpad_buttons:
                continue
            x, y, kind = spots[slot]
            if kind == "paddle":
                continue   # desenhadas antes do volante, atras do aro
            label, color = slot_label(slot, family, symbols, i)
            draw_control(ui, kind, round(cx + x * r), round(cy + y * r), s, label, color,
                         "ask" if pressed else "done" if tested else "todo")
        ui.set_clip(None)

    def extra_row(self, ui, extra, bottom):
        """Os botoes que o desenho nao tem, numerados, numa fileira."""
        gap, r = 24, 9
        y = bottom - r - 1
        x = (T.WIDTH - len(extra) * gap) // 2 + r
        for n, (i, (pressed, tested)) in enumerate(extra):
            st = "ask" if pressed else "done" if tested else "todo"
            W.arcade_button(ui, x + n * gap, y, r, st)
            center_text(ui, str(i + 1), T.COMMENT if st == "todo" else T.SPACE, x + n * gap, y, big=True)
        return y - r - 4

    def dpad_big(self, ui, cx, cy, s, hat, buttons):
        """O direcional em cruz: o braco apertado aceso, os ja testados
        verdes (pelo hat ou pelos botoes BTN_DPAD de um joypad)."""
        arms = {(-1, 0): "dleft", (1, 0): "dright", (0, -1): "dup", (0, 1): "ddown"}
        colors = {}
        for (dx, dy), name in arms.items():
            if name in buttons:
                _i, (on, tested) = buttons[name]
            else:
                on = hat is not None and ((dx and dx == hat[0]) or (dy and dy == hat[1]))
                tested = (dx, dy) in self.hat_tested
            colors[(dx, dy)] = T.YELLOW if on else T.GREEN if tested else None
        draw_dpad(ui, cx, cy, s, colors)

    def buttons(self, ui, state, bottom, top=0):
        """Os botoes numerados em fileiras (painel, encoder), centrados entre
        top e bottom, o direcional (hat) na frente."""
        buttons = state["buttons"]
        hat = state["hat"]
        if not buttons and hat is None:
            return bottom
        dpad_w = 48 if hat is not None else 0
        room = T.SAFE_W - dpad_w
        per_row = max(1, min(6, room // 40))
        count = -(-len(buttons) // per_row)
        per_row = -(-len(buttons) // count)   # fileiras iguais: 14 = 7 + 7
        rows = [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)] or [[]]
        # Os botoes do maior tamanho que cabe (14 px de raio no maximo).
        gap = min(40, room // max(1, per_row), (bottom - top - 4) // max(1, len(rows)))
        r = max(7, min(14, gap // 2 - 5))
        y0 = top + (bottom - top - (len(rows) - 1) * gap) // 2
        widest = max(len(row) for row in rows) * gap
        x0 = (T.WIDTH - widest - dpad_w) // 2
        if hat is not None:
            self.dpad_big(ui, x0 + 18, y0 + (len(rows) - 1) * gap // 2, 1.6, hat, {})
            x0 += dpad_w
        n = 0
        for ri, row in enumerate(rows):
            for ci, (pressed, tested) in enumerate(row):
                n += 1
                cx, cy = x0 + ci * gap + gap // 2, y0 + ri * gap
                state_name = "ask" if pressed else "done" if tested else "todo"
                W.arcade_button(ui, cx, cy, r, state_name)
                center_text(ui, str(n), T.COMMENT if state_name == "todo" else T.SPACE, cx, cy, big=r >= 9)
        return y0 - r - 3

    def hold_bar(self, ui, hold, y):
        if hold <= 0:
            return
        w = round(T.SAFE_W * hold)
        pygame.draw.rect(ui, T.BG_DEEP, (T.SAFE_X, y, T.SAFE_W, 4))
        pygame.draw.rect(ui, T.YELLOW, (T.SAFE_X, y, w, 4))

    def panel(self, ui, state, top, bottom):
        """O resultado (a calibracao nova) ou o aviso de que nada mexeu."""
        rows = state["result"]
        h = min(bottom - top, 24 + 11 * max(1, len(rows)))
        rect = (T.SAFE_X + 8, top + max(0, (bottom - top - h) // 2), T.SAFE_W - 16, h)
        W.block(ui, rect, T.BG_DEEP, T.SPACE)
        pygame.draw.rect(ui, T.LINE, rect, 1)
        x, y = rect[0] + 8, rect[1] + 6
        if state["step"] == "nomove":
            W.centered(ui, "NOTHING MOVED", T.RED, y + (h - 20) // 2)
            return
        W.centered(ui, "NEW CALIBRATION", T.YELLOW, y)
        y += 14
        for label, lo, hi, flat in rows:
            W.text(ui, label.replace("PEDAL ", "")[:8], T.CYAN, x, y)
            value = "%d..%d" % (lo, hi)
            W.text(ui, value, T.FG, rect[0] + rect[2] - 8, y, right=True)
            y += 11


# Os lugares dos botoes, em raios do volante (ou do corpo do joypad) a partir
# do centro, e o tipo de cada um. O volante: o direcional no raio esquerdo,
# os quatro de PlayStation no direito, SELECT/START e L3/R3 no de baixo,
# L2/R2 em cima, as borboletas (L1/R1) atras do aro e o cambio do lado.
WHEEL_SPOTS = {
    'dpad': (-0.52, -0.02, 'dpad'),
    'triangle': (0.50, -0.24, 'face'), 'circle': (0.72, -0.02, 'face'),
    'cross': (0.50, 0.20, 'face'), 'square': (0.28, -0.02, 'face'),
    'l2': (-0.32, -0.30, 'round'), 'r2': (0.32, -0.30, 'round'),
    'select': (-0.26, 0.36, 'pill'), 'start': (0.26, 0.36, 'pill'),
    'l3': (-0.15, 0.62, 'round'), 'r3': (0.15, 0.62, 'round'),
    'l1': (-1.10, 0.0, 'paddle'), 'r1': (1.10, 0.0, 'paddle'),
    'gear_up': (1.45, 0.26, 'gear'), 'gear_down': (1.45, 0.62, 'gear'),
}
# Quanto cada tipo de botao ocupa em volta do centro dele, em raios (com o
# rotulo de cima das borboletas e do cambio), para enquadrar a regiao.
EXTENT = {'face': (0.12, 0.12), 'round': (0.11, 0.11), 'pill': (0.27, 0.09), 'paddle': (0.24, 0.50), 'rim': (0.02, 0.02),
          'gear': (0.15, 0.30), 'dpad': (0.20, 0.20), 'stick': (0.13, 0.13), 'shoulder': (0.25, 0.09)}


def fit_zone(spots, rect):
    """(cx, cy, r): o centro e o raio do volante para a regiao dos botoes
    (spots) encher o retangulo; o resto do volante fica cortado."""
    x, y, w, h = rect
    if not spots:
        r = min(w, h) // 3
        return x + w // 2, y + h // 2, r
    x0 = min(sx - EXTENT[k][0] for sx, _sy, k in spots)
    x1 = max(sx + EXTENT[k][0] for sx, _sy, k in spots)
    y0 = min(sy - EXTENT[k][1] for _sx, sy, k in spots)
    y1 = max(sy + EXTENT[k][1] for _sx, sy, k in spots)
    r = max(24, min(150, int(min((w - 8) / (x1 - x0), (h - 8) / (y1 - y0)))))
    return round(x + w / 2 - r * (x0 + x1) / 2), round(y + h / 2 - r * (y0 + y1) / 2), r
PAD_SPOTS = {
    'dpad': (-0.70, -0.06, 'dpad'),
    'north': (0.70, -0.32, 'face'), 'east': (0.96, -0.06, 'face'),
    'south': (0.70, 0.20, 'face'), 'west': (0.44, -0.06, 'face'),
    'select': (-0.24, -0.22, 'pill'), 'start': (0.24, -0.22, 'pill'), 'mode': (0.0, 0.08, 'round'),
    'thumbl': (-0.36, 0.40, 'stick'), 'thumbr': (0.36, 0.40, 'stick'),
    'tl': (-0.78, -0.68, 'shoulder'), 'tr': (0.78, -0.68, 'shoulder'),
    'tl2': (-0.78, -0.88, 'shoulder'), 'tr2': (0.78, -0.88, 'shoulder'),
}
# As cores dos simbolos: as do PlayStation e as letras do Xbox.
PS_COLORS = {'cross': (0x7C, 0xB2, 0xE8), 'circle': (0xFF, 0x6E, 0x6E), 'triangle': (0x50, 0xE0, 0xB4),
             'square': (0xFF, 0x92, 0xDF)}
PAD_PS = {'south': 'cross', 'east': 'circle', 'north': 'triangle', 'west': 'square'}
PAD_XBOX = {'south': ('A', T.GREEN), 'east': ('B', T.RED), 'west': ('X', T.CYAN), 'north': ('Y', T.YELLOW)}
NAMES = {'l1': 'L1', 'r1': 'R1', 'l2': 'L2', 'r2': 'R2', 'l3': 'L3', 'r3': 'R3', 'select': 'SELECT',
         'start': 'START', 'gear_up': '+', 'gear_down': '-', 'mode': 'HOME', 'thumbl': 'L3', 'thumbr': 'R3'}
PAD_NAMES = {'ps': {'tl': 'L1', 'tr': 'R1', 'tl2': 'L2', 'tr2': 'R2', 'select': 'SHARE', 'start': 'START'},
             'xbox': {'tl': 'LB', 'tr': 'RB', 'tl2': 'LT', 'tr2': 'RT', 'select': 'BACK', 'start': 'START'}}


def slot_label(slot, family, symbols, index):
    """(rotulo, cor) de um botao: o simbolo do PlayStation (rotulo com '@'
    na frente, desenhado), a letra do Xbox, o nome ou o numero."""
    if family == 'pad':
        if slot in PAD_PS and symbols == 'ps':
            return '@' + PAD_PS[slot], PS_COLORS[PAD_PS[slot]]
        if slot in PAD_XBOX:
            return PAD_XBOX[slot]
        return PAD_NAMES.get(symbols, {}).get(slot) or NAMES.get(slot, str(index + 1)), T.FG
    if symbols == 'numbers':
        return str(index + 1), T.FG
    if slot in PS_COLORS:
        return '@' + slot, PS_COLORS[slot]
    return NAMES.get(slot, str(index + 1)), T.FG


# As cores do volante: o aro de couro escuro com costura, as asas dos raios
# com luz em cima, os nichos rebaixados dos botoes e as tampas pretas.
RIM, RIM_HI, RIM_LO, STITCH = (0x34, 0x36, 0x4A), (0x72, 0x77, 0x9C), (0x1C, 0x1D, 0x28), (0x5C, 0x60, 0x80)
SPOKE, SPOKE_HI, SPOKE_LO = (0x46, 0x49, 0x60), (0x6A, 0x6E, 0x8C), (0x2A, 0x2C, 0x3A)
POD, POD_DARK, POD_LIP = (0x1F, 0x20, 0x2B), (0x12, 0x13, 0x1A), (0x5A, 0x5E, 0x7A)
HUB, CAP, CAP_HI, CAP_EDGE = (0x26, 0x27, 0x34), (0x1C, 0x1D, 0x27), (0x4A, 0x4D, 0x66), (0x56, 0x5A, 0x76)
_ART = {}


def wheel_art(r):
    """O volante de frente, parado, numa superficie transparente (guardada
    por raio): as asas e o raio de baixo, o console e os nichos dos botoes,
    o cubo com o emblema de arco-iris do letreiro e o aro com costura e a
    faixa laranja do centro. A tela de calibracao a gira inteira."""
    if r in _ART:
        return _ART[r]
    size = 2 * r + 6
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2

    def p(x, y):
        return round(cx + x * r), round(cy + y * r)

    ring = max(5, r // 6)
    # As asas (raios da esquerda e da direita, largos no cubo) e o de baixo.
    wings = [[p(-0.16, -0.40), p(-0.88, -0.20), p(-0.88, 0.22), p(-0.16, 0.30)],
             [p(0.16, -0.40), p(0.88, -0.20), p(0.88, 0.22), p(0.16, 0.30)],
             [p(-0.24, 0.20), p(-0.17, 0.90), p(0.17, 0.90), p(0.24, 0.20)]]
    for poly in wings:
        pygame.draw.polygon(s, T.SPACE, [(x + 1, y + 2) for x, y in poly])
    for poly in wings:
        pygame.draw.polygon(s, SPOKE, poly)
    for poly in wings[:2]:
        pygame.draw.line(s, SPOKE_HI, poly[0], poly[1], max(1, r // 40))
        pygame.draw.line(s, SPOKE_LO, poly[3], poly[2], max(1, r // 40))
    pygame.draw.line(s, SPOKE_HI, wings[2][0], wings[2][1])
    pygame.draw.line(s, SPOKE_LO, wings[2][3], wings[2][2])
    # O console de baixo (SELECT, START, L3, R3) e os nichos.
    x0, y0 = p(-0.40, 0.27)
    x1, y1 = p(0.40, 0.76)
    console = pygame.Rect(x0, y0, x1 - x0, y1 - y0)
    pygame.draw.rect(s, T.SPACE, console.move(1, 2), border_radius=max(3, r // 10))
    pygame.draw.rect(s, SPOKE, console, border_radius=max(3, r // 10))
    pygame.draw.rect(s, POD, console.inflate(-max(4, r // 14), -max(4, r // 14)), border_radius=max(2, r // 12))
    pygame.draw.line(s, POD_LIP, (console.left + r // 10, console.bottom - 2), (console.right - r // 10, console.bottom - 2))
    for (x, y), rad in (((-0.52, -0.02), 0.25), ((0.50, -0.02), 0.37), ((-0.32, -0.30), 0.12), ((0.32, -0.30), 0.12)):
        pod(s, p(x, y), max(4, round(rad * r)))
    # O cubo e o emblema: as faixas do letreiro do Setup num disco.
    hub = max(7, round(r * 0.22))
    pygame.draw.circle(s, T.SPACE, (cx + 1, cy + 2), hub + 1)
    pygame.draw.circle(s, T.SPACE, (cx, cy), hub + 1)
    pygame.draw.circle(s, HUB, (cx, cy), hub)
    arc(s, CAP_EDGE, (cx - hub + 1, cy - hub + 1, 2 * hub - 2, 2 * hub - 2), -70, 70, 1)
    emblem = max(3, round(hub * 0.6))
    for y in range(-emblem, emblem + 1):
        half = int((emblem * emblem - y * y) ** 0.5)
        color = W.RAINBOW[min(len(W.RAINBOW) - 1, (y + emblem) * len(W.RAINBOW) // (2 * emblem + 1))]
        pygame.draw.line(s, color, (cx - half, cy + y), (cx + half, cy + y))
    # O aro: couro com luz em cima, sombra por dentro embaixo e a costura.
    pygame.draw.circle(s, T.SPACE, (cx, cy), r + 1, ring + 3)
    pygame.draw.circle(s, RIM, (cx, cy), r, ring + 1)
    arc(s, RIM_HI, (cx - r + 1, cy - r + 1, 2 * r - 2, 2 * r - 2), -150, 30, 2 if r >= 40 else 1)
    inner = r - ring
    arc(s, RIM_LO, (cx - inner, cy - inner, 2 * inner, 2 * inner), 60, 260, 2 if r >= 40 else 1)
    mid = r - ring // 2 - 1
    step = 8 if r >= 60 else 12
    for a in range(0, 360, step):
        if abs((a + 180) % 360 - 180) > 8:
            surf_point(s, polar(cx, cy, mid, a), STITCH)
    # A faixa laranja do centro, no topo do aro.
    band = [polar(cx, cy, r, a) for a in (-5, 5)] + [polar(cx, cy, inner - 1, a) for a in (5, -5)]
    pygame.draw.polygon(s, T.ORANGE, band)
    pygame.draw.line(s, W.shade(T.ORANGE, 1.4), polar(cx, cy, r - 1, 0), polar(cx, cy, inner, 0))
    _ART[r] = s
    return s


def surf_point(s, xy, color):
    s.fill(color, (xy[0], xy[1], 1, 1))


def pod(s, c, rad):
    """Um nicho rebaixado: borda escura em cima (sombra) e o labio claro
    embaixo."""
    pygame.draw.circle(s, T.SPACE, c, rad + 1)
    pygame.draw.circle(s, POD, c, rad)
    box = (c[0] - rad + 1, c[1] - rad + 1, 2 * rad - 2, 2 * rad - 2)
    arc(s, POD_DARK, box, -70, 70, 2 if rad >= 10 else 1)
    arc(s, POD_LIP, box, 120, 240, 1)


def draw_wheel_face(surf, cx, cy, r):
    """O volante de frente, parado (a tela dos botoes)."""
    pygame.draw.circle(surf, T.SPACE, (cx + 2, cy + 3), r + 1)
    art = wheel_art(r)
    surf.blit(art, art.get_rect(center=(cx, cy)))


def draw_paddle(surf, cx, cy, r, side, label, state):
    """A borboleta atras do aro: uma lamina curva saindo de tras dele, do
    lado side (-1 esquerda, 1 direita), com as ranhuras e o rotulo de fora."""
    on, done = state == "ask", state == "done"
    mid = 90 * side
    span, r0, r1 = 24, r * 0.90, r * 1.19
    outer = [polar(cx, cy, r1, mid + a) for a in range(-span, span + 1, 3)]
    inner = [polar(cx, cy, r0, mid + a) for a in range(span, -span - 1, -3)]
    blade = outer + inner
    pygame.draw.polygon(surf, T.SPACE, [(x + 2, y + 3) for x, y in blade])
    pygame.draw.polygon(surf, T.YELLOW if on else SPOKE, blade)
    pygame.draw.lines(surf, W.shade(T.YELLOW, 1.4) if on else SPOKE_HI, False, outer[: len(outer) // 2 + 1], 1)
    for a in (-12, 0, 12):
        pygame.draw.line(surf, W.shade(T.YELLOW, 0.7) if on else SPOKE_LO,
                         polar(cx, cy, r * 1.02, mid + a), polar(cx, cy, r1 - 3, mid + a))
    edge = T.YELLOW if on else T.GREEN if done else T.SPACE
    pygame.draw.polygon(surf, edge, blade, 2 if done else 1)
    lx, ly = polar(cx, cy, r1 + 4, mid + side * 32)
    center_text(surf, label, T.YELLOW if on else T.GREEN if done else T.COMMENT, lx, ly)


def center_text(surf, s, color, cx, cy, big=False):
    """O texto com o centro dos pixels acesos exatamente em (cx, cy): a
    fonte grande (8 px) ou a pequena (tiny, 5 px)."""
    if big:
        img = T.font().render(s, False, color)
    else:
        img = pygame.Surface((tiny.width(s) + 2, 7), pygame.SRCALPHA)
        tiny.text(img, s, color, 0, 0)
    rects = pygame.mask.from_surface(img).get_bounding_rects()
    if not rects:
        return
    box = rects[0].unionall(rects[1:])
    surf.blit(img, (cx - box.x - box.w // 2, cy - box.y - box.h // 2))


# O direcional como o do guia dos controles do frontend (feview.dpad): a
# cruz cinza com a borda escura, um triangulo afundado em cada braco e o meio
# rebaixado. Medidas dele em s = 1 (40 de ponta a ponta, braco de 14).
DPAD_FACE, DPAD_EDGE, DPAD_GROOVE, DPAD_MIDDLE = (0x3C, 0x3E, 0x48), (0x10, 0x10, 0x16), (0x22, 0x23, 0x2A), \
    (0x30, 0x32, 0x3A)


def draw_dpad(surf, cx, cy, s, colors):
    """O direcional em cruz; colors e {(dx, dy): cor} dos bracos acesos
    (amarelo apertado, verde testado), que ganham a cor no lugar do cinza."""
    k = s * 0.6
    half, arm = max(6, round(20 * k)), max(3, round(7 * k))
    for grow, color in ((2, DPAD_EDGE), (0, DPAD_FACE)):
        pygame.draw.rect(surf, color, (cx - arm - grow, cy - half - grow, 2 * arm + 2 * grow, 2 * half + 2 * grow),
                         border_radius=3)
        pygame.draw.rect(surf, color, (cx - half - grow, cy - arm - grow, 2 * half + 2 * grow, 2 * arm + 2 * grow),
                         border_radius=3)
    for (dx, dy), color in colors.items():
        if color:
            # O braco aceso, do meio ate a ponta.
            if dx:
                x0 = cx + (arm if dx > 0 else -half)
                pygame.draw.rect(surf, color, (x0, cy - arm, half - arm, 2 * arm), border_radius=2)
            else:
                y0 = cy + (arm if dy > 0 else -half)
                pygame.draw.rect(surf, color, (cx - arm, y0, 2 * arm, half - arm), border_radius=2)
    tip = max(2, round(4 * k))
    for d in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        groove = W.shade(colors[d], 0.55) if colors.get(d) else DPAD_GROOVE
        fe_arrow(surf, cx + d[0] * round(14 * k), cy + d[1] * round(14 * k), d, groove, tip)
    pygame.draw.circle(surf, DPAD_MIDDLE, (cx, cy), max(2, round(5 * k)))


def fe_arrow(surf, cx, cy, d, color, size):
    """O triangulo de um braco, o mesmo do feview.arrow."""
    dx, dy = d
    pts = [(cx + dx * size, cy + dy * size), (cx - dy * size - dx * 2, cy + dx * size - dy * 2),
           (cx + dy * size - dx * 2, cy - dx * size - dy * 2)]
    pygame.draw.polygon(surf, color, pts)


_CAPS = {}


def wheel_with_caps(r, layout):
    """O volante da tela de calibracao (o que gira): o desenho com as
    tampas dos botoes que o controle tem, todas apagadas."""
    if not layout or layout.get("family") != "wheel":
        return wheel_art(r)
    slots = tuple(s for s in layout["slots"] if s)
    key = (r, slots, layout["symbols"])
    if key not in _CAPS:
        art = wheel_art(r).copy()
        c = art.get_width() // 2
        s = r / 60
        draw_dpad(art, round(c + WHEEL_SPOTS["dpad"][0] * r), round(c + WHEEL_SPOTS["dpad"][1] * r), s, {})
        for i, slot in enumerate(layout["slots"]):
            if slot in WHEEL_SPOTS and WHEEL_SPOTS[slot][2] not in ("paddle", "gear"):
                x, y, kind = WHEEL_SPOTS[slot]
                label, color = slot_label(slot, "wheel", layout["symbols"], i)
                draw_control(art, kind, round(c + x * r), round(c + y * r), s, label, color, "todo", show_text=False)
        _CAPS[key] = art
    return _CAPS[key]


def draw_pad_body(surf, cx, cy, r):
    """O corpo de um joypad visto de frente: a barra e as duas alcas."""
    w, h = int(r * 2.3), int(r * 1.0)
    body = W.shade(T.LINE, 0.85)
    for dx in (-1, 1):
        pygame.draw.circle(surf, T.SPACE, (cx + dx * int(r * 0.78) + 2, cy + int(r * 0.30) + 3), int(r * 0.48))
    pygame.draw.rect(surf, T.SPACE, (cx - w // 2 + 2, cy - h // 2 + 3, w, h), border_radius=r // 3)
    for dx in (-1, 1):
        pygame.draw.circle(surf, body, (cx + dx * int(r * 0.78), cy + int(r * 0.30)), int(r * 0.48))
    pygame.draw.rect(surf, body, (cx - w // 2, cy - h // 2, w, h), border_radius=r // 3)
    pygame.draw.rect(surf, W.shade(T.LINE, 1.3), (cx - w // 2, cy - h // 2, w, h), 1, border_radius=r // 3)


def draw_control(surf, kind, cx, cy, s, label, color, state, show_text=True):
    """Um botao no desenho: state e "ask" (apertado agora), "done" (ja
    testado) ou "todo". kind: face, round, pill, gear, shoulder, stick. A
    tampa e preta com o brilho de cupula; apertado, ela acende (na cor do
    simbolo, ou amarela); testado, o aro fica verde."""
    on, done = state == "ask", state == "done"
    symbol = label.startswith('@')
    lit = color if symbol and color != T.FG else T.YELLOW
    cap = lit if on else CAP
    edge = T.GREEN if done and not on else W.shade(lit, 0.7) if on else CAP_EDGE
    ink = T.SPACE if on else color if symbol else T.GREEN if done else T.FG
    if kind in ("face", "round", "stick", "gear"):
        r = max(4, round({'face': 6.5, 'stick': 7.5, 'gear': 8.5}.get(kind, 6.5) * s))
        if on:
            pygame.draw.circle(surf, T.PINK, (cx, cy), r + 2)
        pygame.draw.circle(surf, T.SPACE, (cx + 1, cy + 2), r + 1)
        pygame.draw.circle(surf, T.SPACE, (cx, cy), r + 1)
        pygame.draw.circle(surf, cap, (cx, cy), r)
        # O brilho da cupula, em cima a esquerda.
        pygame.draw.circle(surf, W.shade(cap, 1.35) if on else CAP_HI, (cx - r // 3, cy - r // 3), max(1, r // 4))
        pygame.draw.circle(surf, edge, (cx, cy), r, 2 if done or on else 1)
        if kind == "stick":
            pygame.draw.circle(surf, edge, (cx, cy), max(2, r - 3), 1)
        if kind == "gear":
            # O cambio: + e - desenhados do tamanho do botao.
            a, t = max(3, r // 2), max(2, r // 4)
            pygame.draw.rect(surf, ink, (cx - a, cy - t // 2, 2 * a + 1, t))
            if label == "+":
                pygame.draw.rect(surf, ink, (cx - t // 2, cy - a, t, 2 * a + 1))
                center_text(surf, "SHIFT", T.COMMENT, cx, cy - r - 7)
            return
        if symbol:
            draw_symbol(surf, label[1:], cx, cy, max(2, round(r * 0.42)), ink)
        else:
            if show_text:
                center_text(surf, label, ink, cx, cy, big=r >= 9 and len(label) <= 2)
        return
    if kind in ("pill", "shoulder"):
        w = max(tiny.width(label) + 10, round((26 if kind == "shoulder" else 22) * s))
        h = max(8, round((9 if kind == "shoulder" else 8) * s))
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.rect(surf, T.SPACE, rect.inflate(2, 2).move(1, 2), border_radius=h // 2 + 1)
        pygame.draw.rect(surf, T.SPACE, rect.inflate(2, 2), border_radius=h // 2 + 1)
        pygame.draw.rect(surf, cap, rect, border_radius=h // 2)
        pygame.draw.line(surf, W.shade(cap, 1.35) if on else CAP_HI, (rect.left + h // 2, rect.top + 1),
                         (rect.right - h // 2, rect.top + 1))
        pygame.draw.rect(surf, edge, rect, 2 if done or on else 1, border_radius=h // 2)
        if show_text:
            center_text(surf, label, ink, cx, cy, big=h >= 12 and W.width(label) <= w - 8)


def draw_symbol(surf, name, cx, cy, a, color):
    """Os simbolos do PlayStation desenhados (a fonte nao os tem), de meia
    largura a do botao."""
    t = 2 if a >= 4 else 1
    if name == 'cross':
        pygame.draw.line(surf, color, (cx - a, cy - a), (cx + a, cy + a), t)
        pygame.draw.line(surf, color, (cx - a, cy + a), (cx + a, cy - a), t)
    elif name == 'circle':
        pygame.draw.circle(surf, color, (cx, cy), a, t)
    elif name == 'triangle':
        pygame.draw.polygon(surf, color, [(cx, cy - a), (cx - a, cy + a * 3 // 4), (cx + a, cy + a * 3 // 4)], t)
    elif name == 'square':
        pygame.draw.rect(surf, color, (cx - a + 1, cy - a + 1, 2 * a - 1, 2 * a - 1), t)


def pairs(axes):
    """Os analogicos em pares X/Y e RX/RY (cada um uma caixa); o que sobra
    vai em barras."""
    by = {a["code"]: a for a in axes}
    sticks = []
    for x, y in ((0, 1), (3, 4)):
        if x in by and y in by:
            sticks.append((by.pop(x), by.pop(y)))
    return sticks, [a for a in axes if a["code"] in by]


def polar(cx, cy, r, degrees):
    """O ponto a r pixels do centro, degrees a partir do topo, no sentido
    horario."""
    a = math.radians(degrees - 90)
    return round(cx + r * math.cos(a)), round(cy + r * math.sin(a))


def arc(surf, color, rect, start, end, width):
    """Arco de start a end graus do topo, no sentido horario, como uma linha
    de pontos a cada 3 graus (o pygame.draw.arc grosso sai furado)."""
    if end - start < 1:
        return
    x, y, w, _h = rect
    cx, cy, r = x + w // 2, y + w // 2, w // 2
    steps = max(2, int((end - start) / 3) + 1)
    points = [polar(cx, cy, r, start + (end - start) * i / (steps - 1)) for i in range(steps)]
    pygame.draw.lines(surf, color, False, points, width)
    for p in (points[0], points[-1]):
        pygame.draw.circle(surf, color, p, max(1, width // 2))


def plain_name(name):
    """O nome sem a palavra repetida que o kernel junta ("Logitech Logitech
    Driving Force Pro": o fabricante e o produto do USB comecam igual)."""
    words = name.split()
    out = [w for i, w in enumerate(words) if i == 0 or w.lower() != words[i - 1].lower()]
    return " ".join(out)


def wheel_text(frac, degrees):
    side = "LEFT" if frac < -0.01 else "RIGHT" if frac > 0.01 else "CENTER"
    if degrees:
        return "%d° %s" % (round(abs(frac) * degrees / 2), side)
    return "%d%% %s" % (round(abs(frac) * 100), side)
