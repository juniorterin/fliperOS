#!/usr/bin/env python3
"""A pagina do styleguide do FliperOS, so para quem desenvolve (docs/styleguide/index.html).

  python3 tools/styleguide.py [SAIDA]       gera a pagina (docs/styleguide/index.html)

Ela le o que o codigo ja diz, sem copiar nada a mao:
  - os tokens de cor, raio e fonte do painel web (:root de config/web/style.css);
  - as cores do Setup e do frontend (config/../fliperos-setup/gui/theme.py);
  - os icones do painel (config/web/icons.svg) e a lista de icones do Setup;
  - os tamanhos de letra, os raios e as cores soltas que cada .css usa.
e mostra os componentes de verdade, desenhados com os proprios .css do painel
(a pagina os carrega por caminho relativo: abra o arquivo no navegador).

O que nao e padrao aparece como "auditoria": um token com o mesmo valor de
outro, uma cor do painel que nao e a do Setup, tamanhos de letra e raios fora
da escala, cores escritas no CSS em vez do token. Rode de novo depois de mexer
nos .css ou no tema.
"""
import html
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "config", "web")
THEME = os.path.join(ROOT, "fliperos-setup", "gui", "theme.py")
OUT = os.path.join(ROOT, "docs", "styleguide", "index.html")
CSS_FILES = ("style.css", "setup.css", "cabinet.css", "input.css", "overlay.css", "stream.css")

# O papel de cada cor (o que o Setup, o painel e o site ja fazem; a regra para o codigo novo).
ROLES = (
    ("purple", "Primary action, the border of the selected thing at rest, the brand."),
    ("pink", "Selection and focus: the cursor, the active tab, the title of the selected tile."),
    ("cyan", "Information, links and the values of a setting (kHz, sizes, addresses)."),
    ("green", "Good, on, ready, installed, progress."),
    ("yellow", "Attention that is not an error: a number, a waiting state, a warning chip."),
    ("orange", "A warning that needs a decision (the bar of the filter notice, the percent)."),
    ("red", "Error, off, delete, a danger button. Never decoration."),
    ("fg", "Text."),
    ("muted", "Secondary text: hints, labels."),
    ("dim", "The least important text: units, captions."),
)
# A escala que o painel deve seguir (a proposta; a auditoria conta o que foge dela).
FONT_SCALE = (11, 12, 13, 14, 15, 18, 22, 26)
RADIUS_SCALE = (2, 4, 6, 8, 10, 12, 14, 16, 999)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def root_tokens(css):
    """As variaveis do primeiro :root: [(nome, valor)]."""
    block = re.search(r":root\s*\{(.*?)\n\}", css, re.S)
    return re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", block.group(1)) if block else []


def theme_colors(text):
    """As cores (R, G, B) do theme.py: {NOME: "#rrggbb"}."""
    out = {}
    for name, r, g, b in re.findall(r"^([A-Z_]+) = \((0x[0-9A-Fa-f]{2}), (0x[0-9A-Fa-f]{2}), (0x[0-9A-Fa-f]{2})\)", text, re.M):
        out[name] = "#%02x%02x%02x" % (int(r, 16), int(g, 16), int(b, 16))
    return out


def icons(svg):
    return re.findall(r'<symbol id="((?:px|g)-[\w-]+)"', svg)


def audit(files):
    """O que cada .css usa fora do padrao: {arquivo: {...}} e o total de tamanhos de letra."""
    sizes, radii, report = Counter(), Counter(), {}
    for name, css in files.items():
        body = re.sub(r":root\s*\{.*?\n\}", "", css, count=1, flags=re.S)
        body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
        colors = re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", body)
        fonts = re.findall(r"font-size\s*:\s*([\d.]+)px", body)
        rads = re.findall(r"border-radius\s*:\s*(\d+)px", body)
        sizes.update(fonts)
        radii.update(rads)
        report[name] = {"hex": len(colors), "tokens": len(re.findall(r"var\(--", body)),
                        "off_font": sorted({f for f in fonts if float(f) not in FONT_SCALE}, key=float),
                        "off_radius": sorted({r for r in rads if int(r) not in RADIUS_SCALE}, key=int)}
    return report, sizes, radii


def duplicates(tokens):
    seen, out = {}, []
    for name, value in tokens:
        key = value.strip().lower()
        if key in seen and key.startswith("#"):
            out.append((seen[key], name, value.strip()))
        else:
            seen.setdefault(key, name)
    return out


def swatch(name, value, note=""):
    return ('<div class="sg-sw"><i style="background:%s"></i><b>%s</b><code>%s</code><small>%s</small></div>'
            % (html.escape(value), html.escape(name), html.escape(value), html.escape(note)))


COMPONENTS = (
    ("Buttons", "style.css", '<button class="btn">Primary</button> <button class="btn ghost">Ghost</button> '
     '<button class="btn small">Small</button> <button class="btn red">Danger</button>',
     "One primary per screen; Ghost for the others; Danger only for what deletes."),
    ("Tags", "style.css", '<span class="tag">tag</span> <span class="tag on">on</span> <span class="tag off">off</span>',
     "State in one word: on is green, off is dim. Not for actions."),
    ("Chips", "setup.css", '<span class="st-chip">driver</span> <span class="st-chip b15">15 kHz</span> '
     '<span class="st-chip b25">25 kHz</span> <span class="st-chip b31">31 kHz</span> <span class="st-chip drv">amdgpu</span>',
     "Facts about the tube (the band colours) and the driver."),
    ("Meter", "setup.css", '<div class="st-meter" style="max-width:320px"><i style="width:45%"></i></div>',
     "Progress and usage: green, orange near the limit (warn), red at it (hot)."),
    ("Setting rows", "setup.css", '<section class="ssec"><div class="slist"><div class="srow"><div class="lbl"><b>Setting</b>'
     '<small>What it does, in one line.</small></div><div class="ctl"><select class="sel"><option>Option</option></select></div></div>'
     '<div class="srow"><div class="lbl"><b>Another</b></div><div class="ctl"><input class="fld" value="text"></div></div></div></section>',
     "The Setup is lists of rows: name and hint on the left, the control on the right."),
    ("Card", "setup.css", '<section class="st-card" style="max-width:360px"><h3>Memory</h3><div class="st-big">3.2 GB</div>'
     '<div class="dim">of 8 GB</div></section>', "A block of the Status page: a small uppercase title, then the value."),
    ("Toast", "style.css", '<div class="toast ok" style="position:static"><span>Saved.</span></div> '
     '<div class="toast bad" style="position:static"><span>Could not save.</span></div>',
     "Short feedback, 4.5 s. The result of an action, never a question."),
    ("Table", "style.css", '<div class="table-wrap"><table><tr><th>Name</th><th>Size</th></tr><tr><td>sf2.zip</td><td>2 MB</td></tr></table></div>',
     "Lists with columns (processes, files)."),
)

RULES = (
    ("Two languages", "Every string is in English and Portuguese: config/web/text.js and setup-text.js have the same keys (a test counts them); the Setup is English only, the web panel and the frontend are bilingual where they are for the person."),
    ("Text that does not fit runs", "Never cut text on a screen: the selected row runs (feview.ticker, scroll_text); a hint fits 2 lines of 34 columns."),
    ("Every menu item has an icon", "A new Setup item gets a drawing in gui/theme.py (GuiMenuIconTests) and an px-ID in icons.svg for the web."),
    ("Anything over a game is responsive", "The OSD and the notices adapt to every frame size and to the vertical monitor; preview with the real fit()/layer_view()."),
    ("Screenshots in proportion", "Never a stretched print: 640x240 is shown 4:3 (releases, the site, Telegram)."),
    ("Colours are roles", "Use the role of the table above, not a colour you like; the web uses var(--token), never the hex."),
    ("One place for each thing", "A panel setting is a row of the Setup tree (setup.js) with the same id as the Setup menu; a parity test fails when one is missing."),
    ("Fixes are general", "Never a mapping for one person's panel or game: fix the class of problem."),
)


def page(tokens, theme, svg_icons, report, sizes, radii, dupes, components=COMPONENTS):
    web = {n: v for n, v in tokens}
    out = ['<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
           "<title>FliperOS style guide</title>",
           '<link rel="stylesheet" href="../../config/web/style.css"><link rel="stylesheet" href="../../config/web/setup.css">',
           "<style>", STYLE, "</style></head><body><div class=\"stars\"></div><main class=\"sg\">",
           "<h1>FliperOS style guide</h1>",
           '<p class="lead">For developers only. Generated by <code>tools/styleguide.py</code> from the CSS of the web panel, the theme of the '
           "Setup and the icon sprite; the samples below are drawn with the real stylesheets. Run the tool again after changing them.</p>",
           '<nav class="sg-nav"><a href="#colours">Colours</a><a href="#tokens">Tokens</a><a href="#type">Type</a><a href="#components">Components</a>'
           '<a href="#setup">Setup &amp; frontend</a><a href="#icons">Icons</a><a href="#audit">Audit</a><a href="#rules">Rules</a></nav>']
    # Cores: o papel de cada uma, com o token do painel e a constante do Setup.
    out.append('<section id="colours"><h2>Colours (Dracula)</h2><div class="sg-grid">')
    gui = {"purple": "PURPLE", "pink": "PINK", "cyan": "CYAN", "green": "GREEN", "yellow": "YELLOW", "orange": "ORANGE", "red": "RED",
           "fg": "FG", "muted": "", "dim": "COMMENT"}
    for name, role in ROLES:
        value = web.get("--" + name, "")
        theme_value = theme.get(gui.get(name, ""), "")
        note = role + ("  GUI " + gui[name] + " " + theme_value if theme_value else "")
        out.append(swatch("--" + name, value, note))
    out.append("</div></section>")
    out.append('<section id="tokens"><h2>Tokens of the web panel (:root)</h2><div class="sg-grid">')
    for name, value in tokens:
        if value.strip().startswith("#"):
            out.append(swatch(name, value.strip(), "used by var(%s)" % name))
    out.append("</div><p>Other tokens: %s.</p></section>" % ", ".join(
        "<code>%s: %s</code>" % (html.escape(n), html.escape(v.strip())) for n, v in tokens if not v.strip().startswith("#")))
    out.append('<section id="type"><h2>Type</h2><p>Titles: <code>--px</code> (Press Start 2P, the pixel font of the Setup); text: system-ui.</p>'
               '<div class="sg-type">')
    for size in FONT_SCALE:
        out.append('<div><span style="font-size:%dpx">The quick brown fox %d px</span><small>%d uses</small></div>' % (size, size, sizes.get(str(size), 0)))
    out.append("</div></section>")
    out.append('<section id="components"><h2>Components</h2>')
    for title, file, sample, note in components:
        out.append('<div class="sg-comp"><h3>%s <small>%s</small></h3><div class="sg-live">%s</div><p>%s</p></div>' % (
            html.escape(title), html.escape(file), sample, html.escape(note)))
    out.append("</section>")
    out.append('<section id="setup"><h2>Setup &amp; frontend (320x240, pygame)</h2><p>Drawn at 320x240 on the 15 kHz tube (the safe area leaves 16 px on each side and '
               '10 at the top); the GUI palette is <code>gui/theme.py</code>.</p><div class="sg-grid">')
    for name, value in theme.items():
        out.append(swatch(name, value, "theme.py"))
    out.append("</div></section>")
    px = [i for i in svg_icons if i.startswith("px-")]
    out.append('<section id="icons"><h2>Icons (%d pixel icons, %d glyphs)</h2><div class="sg-icons">' % (len(px), len(svg_icons) - len(px)))
    for name in svg_icons:
        out.append('<div><svg class="%s"><use href="../../config/web/icons.svg#%s"/></svg><small>%s</small></div>' % (
            "px" if name.startswith("px-") else "g", html.escape(name), html.escape(name)))
    out.append("</div></section>")
    out.append('<section id="audit"><h2>Audit: what is not the standard</h2>')
    out.append("<p>The scale proposed: font sizes %s px; radii %s px; colours only as <code>var(--token)</code>.</p>" % (
        ", ".join(map(str, FONT_SCALE)), ", ".join(map(str, RADIUS_SCALE))))
    out.append("<table><tr><th>File</th><th>Hex colours (not tokens)</th><th>var(--token)</th><th>Font sizes off the scale</th><th>Radii off the scale</th></tr>")
    for name, r in report.items():
        out.append("<tr><td>%s</td><td>%d</td><td>%d</td><td>%s</td><td>%s</td></tr>" % (
            html.escape(name), r["hex"], r["tokens"], html.escape(", ".join(r["off_font"]) or "-"), html.escape(", ".join(r["off_radius"]) or "-")))
    out.append("</table>")
    out.append("<h3>Tokens with the same value</h3><ul>%s</ul>" % ("".join(
        "<li><code>%s</code> and <code>%s</code> are both <code>%s</code>: keep one value and define the other as <code>var(%s)</code>.</li>"
        % (a, b, html.escape(v), a) for a, b, v in dupes) or "<li>None.</li>"))
    mismatch = []
    for web_name, gui_name in (("--pink", "PINK"), ("--purple", "PURPLE"), ("--cyan", "CYAN"), ("--green", "GREEN"), ("--yellow", "YELLOW"),
                               ("--orange", "ORANGE"), ("--red", "RED"), ("--fg", "FG"), ("--line", "LINE"), ("--space", "SPACE"),
                               ("--bg", "BG"), ("--deep", "BG_DEEP"), ("--dim", "COMMENT")):
        if web.get(web_name, "").strip().lower() != theme.get(gui_name, "").lower():
            mismatch.append((web_name, web.get(web_name, "?").strip(), gui_name, theme.get(gui_name, "?")))
    out.append("<h3>The same colour with a different value in the web and in the Setup</h3><ul>%s</ul></section>" % ("".join(
        "<li><code>%s</code> %s &ne; <code>%s</code> %s</li>" % (a, b, c, d) for a, b, c, d in mismatch) or "<li>None.</li>"))
    out.append('<section id="rules"><h2>Rules</h2><dl>%s</dl></section>' % "".join(
        "<dt>%s</dt><dd>%s</dd>" % (html.escape(t), html.escape(d)) for t, d in RULES))
    out.append("</main></body></html>\n")
    return "\n".join(out)


STYLE = """
body { background: var(--space); }
.sg { max-width: 1100px; margin: 0 auto; padding: 32px 20px 80px; }
.sg h1 { font-family: var(--px); font-size: 22px; color: var(--pink); }
.sg h2 { margin-top: 44px; padding-top: 14px; border-top: 1px solid var(--hair); font-size: 18px; color: var(--purple); }
.sg h3 { font-size: 14px; color: var(--cyan); } .sg h3 small, .sg-comp small { color: var(--dim); font-weight: 400; margin-left: 8px; }
.sg .lead { color: var(--muted); max-width: 70ch; }
.sg-nav { display: flex; flex-wrap: wrap; gap: 8px 16px; margin: 18px 0; } .sg-nav a { color: var(--cyan); }
.sg-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 12px; }
.sg-sw { display: grid; grid-template-columns: 44px 1fr; gap: 2px 12px; align-items: center; padding: 10px; border-radius: 10px; background: var(--surface); }
.sg-sw i { grid-row: span 3; width: 44px; height: 44px; border-radius: 8px; border: 1px solid var(--hair); }
.sg-sw b { font-size: 13px; } .sg-sw code { color: var(--value); font-size: 12px; } .sg-sw small { color: var(--dim); font-size: 11.5px; }
.sg-type { display: grid; gap: 8px; } .sg-type small { margin-left: 12px; color: var(--dim); }
.sg-comp { margin: 18px 0; } .sg-live { padding: 18px; border-radius: 12px; background: var(--surface); }
.sg-comp p, .sg dd { color: var(--muted); margin: 6px 0 0; }
.sg-icons { display: grid; grid-template-columns: repeat(auto-fill, minmax(92px, 1fr)); gap: 10px; }
.sg-icons div { display: grid; justify-items: center; gap: 4px; padding: 8px 4px; border-radius: 8px; background: var(--surface); }
.sg-icons small { font-size: 10.5px; color: var(--dim); word-break: break-all; text-align: center; }
.sg table { border-collapse: collapse; width: 100%; font-size: 13.5px; } .sg td, .sg th { padding: 6px 10px; border-bottom: 1px solid var(--hair); text-align: left; }
.sg dt { margin-top: 14px; font-weight: 700; color: var(--fg); }
"""


def build(root=ROOT):
    """O HTML do styleguide lido do repositorio em root."""
    web = os.path.join(root, "config", "web")
    files = {n: read(os.path.join(web, n)) for n in CSS_FILES if os.path.isfile(os.path.join(web, n))}
    tokens = root_tokens(files["style.css"])
    theme = theme_colors(read(os.path.join(root, "fliperos-setup", "gui", "theme.py")))
    report, sizes, radii = audit(files)
    return page(tokens, theme, icons(read(os.path.join(web, "icons.svg"))), report, sizes, radii, duplicates(tokens))


def main(argv):
    out = argv[0] if argv else OUT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(build())
    print("styleguide: %s" % os.path.relpath(out, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
