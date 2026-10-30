"""Grava as animacoes do painel web para o site, com o gabinete de verdade:
abre o Street Fighter II pelo painel, e enquanto ele roda aperta os botoes por
controles virtuais (vpad.py, no gabinete) para o gabinete mostrar o jogo, a
tela ao vivo e o controle do OBS acendendo. Um desktop de 1280x800, o ponteiro
e o clique desenhados na pagina.

    python3 web_gifs.py http://IP:8081 /out IP

Cada trecho (frontend, live, controller, settings, library) vira um par de
marcas em /out/events.txt ("epoch nome:start" e "epoch nome:end"); os quadros
ficam em /out/frames/<epoch>.jpg. O web_gifs_cut.py corta os GIFs deles.

Variaveis: FLIPEROS_USER, FLIPEROS_PASSWORD (login do painel e do ssh),
STOP_AT (para na marca, para ensaiar), SKIP_PLAY=1 (o jogo ja esta aberto).
"""
import base64
import json
import os
import random
import subprocess
import sys
import threading
import time
import urllib.request

import websocket

BASE, OUT, CAB = sys.argv[1], sys.argv[2], sys.argv[3]
USER = os.environ.get("FLIPEROS_USER", "fliperos")
PASS = os.environ.get("FLIPEROS_PASSWORD", "fliperos")
W, H = 1280, 800
os.makedirs(OUT + "/frames", exist_ok=True)

# ── Os controles virtuais, no gabinete, por um ssh que fica aberto ──
pad = subprocess.Popen(["sshpass", "-p", PASS, "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
                        "-o", "LogLevel=error", "%s@%s" % (USER, CAB), "python3 -u /tmp/vpad.py"],
                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
pad_lock = threading.Lock()


def pad_reader():
    for line in pad.stdout:
        if line.startswith("ready"):
            print("vpad", line.strip(), flush=True)


threading.Thread(target=pad_reader, daemon=True).start()


def vp(command):
    with pad_lock:
        try:
            pad.stdin.write(command + "\n")
            pad.stdin.flush()
        except OSError:
            pass


def hold(controls, seconds=0.1, player=1):
    vp("down %d %s" % (player, controls))
    time.sleep(seconds)
    vp("up %d %s" % (player, controls))


# ── O Chromium ──
subprocess.Popen(["chromium", "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--remote-debugging-port=9222",
                  "--remote-allow-origins=*", "--hide-scrollbars", "--autoplay-policy=no-user-gesture-required",
                  "--window-size=%d,%d" % (W, H), "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(60):
    try:
        target = next(t for t in json.load(urllib.request.urlopen("http://127.0.0.1:9222/json/list")) if t["type"] == "page")
        break
    except Exception:
        time.sleep(0.5)
ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=120)
lock = threading.Lock()
pending, results = {}, {}
seq = [0]
frames = [0]
events = open(OUT + "/events.txt", "w")


def send(msg):
    with lock:
        ws.send(json.dumps(msg))


def read_loop():
    while True:
        msg = json.loads(ws.recv())
        if msg.get("method") == "Page.screencastFrame":
            p = msg["params"]
            ts = p["metadata"].get("timestamp") or time.time()
            with open("%s/frames/%.4f.jpg" % (OUT, ts), "wb") as f:
                f.write(base64.b64decode(p["data"]))
            frames[0] += 1
            send({"id": 0, "method": "Page.screencastFrameAck", "params": {"sessionId": p["sessionId"]}})
        elif "id" in msg and msg["id"] in pending:
            results[msg["id"]] = msg
            pending.pop(msg["id"]).set()


threading.Thread(target=read_loop, daemon=True).start()


def call(method, **params):
    seq[0] += 1
    n = seq[0]
    ev = threading.Event()
    pending[n] = ev
    send({"id": n, "method": method, "params": params})
    ev.wait(60)
    msg = results.pop(n, {})
    if "error" in msg:
        raise RuntimeError(msg["error"])
    return msg.get("result", {})


def js(code):
    return call("Runtime.evaluate", expression=code, awaitPromise=True, returnByValue=True).get("result", {}).get("value")


def mark(name):
    events.write("%.4f %s\n" % (time.time(), name))
    events.flush()
    print(name, "frames", frames[0], flush=True)
    if name == os.environ.get("STOP_AT"):
        finish()


def finish():
    vp("quit")
    time.sleep(1)
    print("frames", frames[0], flush=True)
    os._exit(0)


# O ponteiro: uma seta que anda ate o alvo, e o circulo do clique.
CURSOR_CSS = """
.fcursor { position: fixed; left: 40px; top: 40px; width: 22px; height: 28px; z-index: 99999; pointer-events: none;
  transition: left .55s cubic-bezier(.3,.7,.2,1), top .55s cubic-bezier(.3,.7,.2,1);
  filter: drop-shadow(0 2px 3px rgba(0,0,0,.6)); }
.tapdot { position: fixed; width: 44px; height: 44px; margin: -22px 0 0 -22px; border-radius: 50%;
  background: rgba(255, 121, 198, .45); border: 2px solid rgba(255, 255, 255, .85); z-index: 99998;
  pointer-events: none; animation: tapdot .5s ease-out forwards; }
@keyframes tapdot { from { transform: scale(.4); opacity: 1; } to { transform: scale(1.4); opacity: 0; } }
"""


def decorate():
    js("""(() => { if (document.getElementById('fcss')) return;
      const s = document.createElement('style'); s.id = 'fcss'; s.textContent = %s; document.head.append(s);
      const c = document.createElement('div'); c.className = 'fcursor';
      c.innerHTML = '<svg viewBox="0 0 22 28" width="22" height="28"><path d="M2 2 L2 22 L7 17.5 L10.5 25.5 L14 24 L10.5 16.5 L17 16.5 Z" fill="#fff" stroke="#111" stroke-width="1.6" stroke-linejoin="round"/></svg>';
      document.body.append(c); })()""" % json.dumps(CURSOR_CSS))


def tap(selector_js, click=True, scroll=True):
    """Leva o ponteiro ate o elemento (uma expressao JS) e clica nele."""
    found = js("""(() => { const e = %s; if (!e) return false;
      if (%s) e.scrollIntoView({block: 'nearest', behavior: 'smooth'}); return true; })()""" % (selector_js, "true" if scroll else "false"))
    if not found:
        print("NOT FOUND", selector_js[:120], flush=True)
        return False
    time.sleep(0.6 if scroll else 0.1)
    js("""(() => { const e = %s; const r = e.getBoundingClientRect(); const c = document.querySelector('.fcursor');
      if (c) { c.style.left = (r.left + r.width / 2) + 'px'; c.style.top = (r.top + r.height / 2) + 'px'; } })()""" % selector_js)
    time.sleep(0.7)
    js("""(() => { const e = %s; const r = e.getBoundingClientRect();
      const d = document.createElement('div'); d.className = 'tapdot';
      d.style.left = (r.left + r.width / 2) + 'px'; d.style.top = (r.top + r.height / 2) + 'px';
      document.body.append(d); setTimeout(() => d.remove(), 700); %s })()""" % (selector_js, "e.click();" if click else ""))
    time.sleep(0.4)
    return True


def typing(selector_js, text, each=0.09):
    js("(() => { const e = %s; e.focus(); e.value = ''; })()" % selector_js)
    for ch in text:
        call("Input.insertText", text=ch)
        time.sleep(each)


def go(route):
    js("location.hash = %s" % json.dumps(route))
    time.sleep(1.2)
    js("window.scrollTo({top: 0})")


# ── O lutador: o que o jogador faria no Street Fighter II ──
fight = {"on": False, "stop": False}


def fighter():
    random.seed(7)
    while not fight["stop"]:
        if not fight["on"]:
            time.sleep(0.1)
            continue
        move = random.choice(["walk", "hadouken", "jump", "punch", "kick", "hadouken", "back", "sweep"])
        # Cada aperto dura o bastante (0,2 a 0,6 s) para o stick andar e o botao
        # acender na animacao de 12 quadros por segundo.
        if move == "walk":
            hold("right", random.uniform(0.45, 0.8))
        elif move == "back":
            hold("left", random.uniform(0.35, 0.6))
        elif move == "hadouken":
            hold("down", 0.2)
            hold("down,right", 0.2)
            hold("right,b%d" % random.choice([1, 2, 3]), 0.3)
        elif move == "jump":
            hold("up,right" if random.random() < .6 else "up", 0.3)
            time.sleep(0.15)
            hold("b%d" % random.choice([4, 5, 6]), 0.25)
        elif move == "punch":
            hold("b%d" % random.choice([1, 2, 3]), 0.28)
        elif move == "kick":
            hold("b%d" % random.choice([4, 5, 6]), 0.28)
        elif move == "sweep":
            hold("down,b%d" % random.choice([4, 5, 6]), 0.3)
        time.sleep(random.uniform(0.25, 0.5))


threading.Thread(target=fighter, daemon=True).start()


def start_match():
    """Ficha, Start e o lutador (Ryu, o primeiro da selecao). Os toques
    repetidos valem se o jogo ainda estava abrindo: uma ficha a mais ou um
    soco a mais na selecao nao atrapalham."""
    for _ in range(2):
        hold("coin", 0.25)
        time.sleep(0.8)
    hold("start", 0.25)
    time.sleep(3.0)
    hold("start", 0.25)
    time.sleep(2.0)
    for _ in range(3):
        hold("b1", 0.25)       # escolhe o personagem sob o cursor
        time.sleep(1.5)


# ── O roteiro ──
call("Page.enable")
call("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=1, mobile=False)
call("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "dark"}])
call("Page.navigate", url=BASE + "/")
time.sleep(3)
js("localStorage.setItem('fliperos-lang', 'en'); localStorage.setItem('fliperos-page', 'frontend')")
call("Page.reload")
time.sleep(3)
# Entrar (fora da gravacao)
js("document.getElementById('user').value = %s; document.getElementById('password').value = %s; "
   "document.querySelector('#login-form button').click()" % (json.dumps(USER), json.dumps(PASS)))
time.sleep(4)
decorate()
call("Page.startScreencast", format="jpeg", quality=72, maxWidth=W, maxHeight=H, everyNthFrame=1)
time.sleep(1.0)
mark("start")

# 1. Biblioteca de jogos: o MAME, a busca, o Street Fighter II, Jogar.
if not os.environ.get("SKIP_PLAY"):
    mark("library:start")
    go("#frontend")
    time.sleep(1.5)
    tap("[...document.querySelectorAll('#systems .sys')].find(x => /mame/i.test(x.textContent))")
    time.sleep(2.5)
    tap("document.getElementById('game-search')")
    typing("document.getElementById('game-search')", "street fighter ii", 0.1)
    js("document.getElementById('game-search').dispatchEvent(new Event('input'))")
    time.sleep(2.5)
    # O SF2 original (o set "sf2"), nao o bootleg nem os hacks.
    tap("[...document.querySelectorAll('#games .game')].find(g => /\\(World 910522\\)/.test(g.textContent)) || document.querySelector('#games .game')")
    time.sleep(3.0)
    tap("document.querySelector('.play-btn')", scroll=False)
    time.sleep(0.8)
    tap("document.getElementById('ask-yes')", scroll=False)
    time.sleep(3.0)
    mark("library:end")
    # O jogo abre no gabinete (o frontend fecha e o MAME muda o video).
    time.sleep(24)
start_match()
fight["on"] = True
time.sleep(8)

# 2. A pagina do gabinete: o jogo na tela e os botoes acesos.
go("#frontend")
js("document.getElementById('cab').scrollIntoView({block: 'start'})")
time.sleep(1.0)
tap("document.getElementById('now-live')", scroll=False)     # "Live in the tube": a tela do desenho anda
time.sleep(5.0)                                              # a conexao e os primeiros quadros
mark("frontend:start")
time.sleep(float(os.environ.get("T_FRONTEND", "10")))
mark("frontend:end")

# 3. Ao vivo: a tela do gabinete, com o jogo.
go("#live")
time.sleep(1.5)
tap("document.getElementById('live-start')", scroll=False)
time.sleep(3.5)                                              # a conexao WebRTC
js("window.scrollTo({top: 75, behavior: 'smooth'})")         # a tela inteira cabe na pagina
mark("live:start")
time.sleep(float(os.environ.get("T_LIVE", "8")))
mark("live:end")

# 4. O controle para o OBS, aceso pelos botoes de verdade.
go("#live/obs")
time.sleep(1.0)
js("document.querySelector('.obs-pick [data-obs=\"pad\"]').click()")
js("(() => { const d = document.getElementById('pad-demo'); if (d && d.checked) d.click(); const p = document.getElementById('pad-players'); "
   "p.value = '1,2'; p.dispatchEvent(new Event('change')); })()")
time.sleep(1.5)
js("document.getElementById('pad-preview').scrollIntoView({block: 'center', behavior: 'smooth'})")
time.sleep(1.5)
mark("controller:start")
time.sleep(float(os.environ.get("T_CONTROLLER", "10")))
mark("controller:end")

# 5. Ajustes: a saturacao muda no jogo enquanto o dedo anda.
go("#system/settings")
time.sleep(2.0)
js("[...document.querySelectorAll('#settings summary')].forEach(s => { if (/colou?r|cor/i.test(s.textContent)) s.parentElement.open = true; })")
time.sleep(1.0)
sat = "[...document.querySelectorAll('#settings input[type=range]')].find(i => /saturation/.test(i.id))"
js("(() => { const e = %s; if (e) e.scrollIntoView({block: 'center', behavior: 'smooth'}); })()" % sat)
time.sleep(1.5)
orig = js("(%s || {}).value" % sat)
mark("settings:start")
tap(sat, click=False, scroll=False)


def slide(to, steps=22, each=0.07):
    start = int(js("%s.value" % sat))
    for i in range(1, steps + 1):
        v = round(start + (to - start) * i / steps)
        js("(() => { const e = %s; e.value = %d; e.dispatchEvent(new Event('input')); })()" % (sat, v))
        time.sleep(each)
    js("%s.dispatchEvent(new Event('change'))" % sat)


if orig is not None:
    slide(0)
    time.sleep(1.8)
    slide(190)
    time.sleep(1.8)
    slide(int(orig))
time.sleep(1.2)
mark("settings:end")

# 6. O jogo fecha pelo painel, e o gabinete volta ao que estava.
fight["on"] = False
vp("release")
go("#frontend")
time.sleep(1.5)
tap("document.getElementById('close-game')")
time.sleep(1.0)
js("(() => { const d = document.getElementById('ask'); if (d && d.open) document.getElementById('ask-yes').click(); })()")
time.sleep(6.0)
mark("end")
call("Page.stopScreencast")
fight["stop"] = True
finish()
