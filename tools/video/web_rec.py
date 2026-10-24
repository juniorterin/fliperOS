"""Grava o painel web do gabinete num tablet (820x1180, escala 2), pelo
screencast do Chromium: cada quadro em /out/frames/<epoch>.jpg e cada acao
em /out/events.txt (epoch e o nome), para juntar com a tela do tubo.

    python3 web_rec.py http://192.168.1.155:8081 /out
"""
import base64
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request

import websocket

BASE, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT + "/frames", exist_ok=True)
W, H, SCALE = 820, 1180, 2
subprocess.Popen(["chromium", "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--remote-debugging-port=9222",
                  "--remote-allow-origins=*", "--hide-scrollbars", "--autoplay-policy=no-user-gesture-required",
                  "--window-size=%d,%d" % (W, H), "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(60):
    try:
        page = next(t for t in json.load(urllib.request.urlopen("http://127.0.0.1:9222/json/list")) if t["type"] == "page")
        break
    except Exception:
        time.sleep(0.5)
ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=120)
lock = threading.Lock()
pending, results = {}, {}
seq = [0]
frames = [0]
events = open(OUT + "/events.txt", "w")


def send(msg):
    with lock:
        ws.send(json.dumps(msg))


def reader():
    import traceback
    try:
        read_loop()
    except Exception:
        traceback.print_exc()
        sys.stdout.flush()


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
        elif msg.get("method") == "Page.javascriptDialogOpening":
            # "Abrir o jogo no gabinete?": o OK, como o dedo apertaria.
            send({"id": 0, "method": "Page.handleJavaScriptDialog", "params": {"accept": True}})
        elif "id" in msg and msg["id"] in pending:
            results[msg["id"]] = msg
            pending.pop(msg["id"]).set()


threading.Thread(target=reader, daemon=True).start()


def call(method, **params):
    seq[0] += 1
    n = seq[0]
    ev = threading.Event()
    pending[n] = ev
    t0 = time.time()
    send({"id": n, "method": method, "params": params})
    ev.wait(60)
    if time.time() - t0 > 3:
        print("SLOW %.1fs %s %s" % (time.time() - t0, method, str(params)[:160]), flush=True)
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
    # Os testes: para antes de mexer no gabinete.
    if name == os.environ.get("STOP_AT"):
        print("stopped at", name)
        os._exit(0)


# O toque: um circulo que aparece e some onde o dedo tocou.
TAP_CSS = """
.tapdot { position: fixed; width: 44px; height: 44px; margin: -22px 0 0 -22px; border-radius: 50%;
  background: rgba(255, 121, 198, .45); border: 2px solid rgba(255, 255, 255, .85); z-index: 99999;
  pointer-events: none; animation: tapdot .55s ease-out forwards; }
@keyframes tapdot { from { transform: scale(.4); opacity: 1; } to { transform: scale(1.4); opacity: 0; } }
"""


def tap(selector_js, click=True):
    """Toca no elemento (uma expressao JS que devolve o elemento)."""
    js("""(() => { const e = %s; if (!e) return false;
      e.scrollIntoView({block: 'nearest', behavior: 'smooth'});
      const r = e.getBoundingClientRect();
      if (!document.getElementById('tapcss')) { const s = document.createElement('style'); s.id = 'tapcss';
        s.textContent = %s; document.head.append(s); }
      const d = document.createElement('div'); d.className = 'tapdot';
      d.style.left = (r.left + r.width / 2) + 'px'; d.style.top = (r.top + r.height / 2) + 'px';
      document.body.append(d); setTimeout(() => d.remove(), 700);
      %s return true; })()""" % (selector_js, json.dumps(TAP_CSS), "e.click();" if click else ""))
    time.sleep(0.35)


def typing(selector_js, text, each=0.08):
    js("(() => { const e = %s; e.focus(); e.value = ''; })()" % selector_js)
    for ch in text:
        call("Input.insertText", text=ch)
        time.sleep(each)


def scroll_to(selector_js, offset=-80):
    js("(() => { const e = %s; if (e) window.scrollTo({top: e.getBoundingClientRect().top + scrollY + %d, "
       "behavior: 'smooth'}); })()" % (selector_js, offset))


def page(name):
    tap("document.querySelector('nav a[data-page=\"%s\"]')" % name)
    js("window.scrollTo({top: 0})")


def by_text(tag, pattern):
    return "[...document.querySelectorAll('%s')].find(x => /%s/i.test(x.textContent))" % (tag, pattern)


call("Page.enable")
call("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=SCALE, mobile=True)
call("Emulation.setTouchEmulationEnabled", enabled=True)
call("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "dark"}])
call("Page.navigate", url=BASE + "/")
time.sleep(3)
js("localStorage.setItem('fliperos-lang', 'en'); localStorage.setItem('fliperos-page', 'frontend')")
call("Page.reload")
time.sleep(3)
call("Page.startScreencast", format="jpeg", quality=92, maxWidth=W * SCALE, maxHeight=H * SCALE, everyNthFrame=1)
time.sleep(1.5)
mark("start")

# Entrar
typing("document.getElementById('user')", "fliperos", 0.09)
typing("document.getElementById('password')", "fliperos", 0.09)
time.sleep(0.4)
tap("document.querySelector('#login-form button')")
mark("login")
time.sleep(3.0)

# A lista de jogos: o MAME, a busca, o Street Fighter II
scroll_to("document.getElementById('h-games')")
time.sleep(1.5)
js("""(() => { const s = document.getElementById('system');
  const o = [...s.options].find(o => /^mame/i.test(o.textContent));
  if (o) { s.value = o.value; s.dispatchEvent(new Event('change')); } })()""")
time.sleep(2.0)
tap("document.getElementById('game-search')", click=False)
typing("document.getElementById('game-search')", "street fighter ii", 0.1)
js("document.getElementById('game-search').dispatchEvent(new Event('input'))")
mark("search")
time.sleep(2.0)
tap("[...document.querySelectorAll('#games .game-head')].find(h => /World 910522/.test(h.textContent))")
mark("info")
time.sleep(3.5)
for y in (300, 300, 300):
    js("window.scrollBy({top: %d, behavior: 'smooth'})" % y)
    time.sleep(2.2)
time.sleep(1.0)
scroll_to("[...document.querySelectorAll('#games .game-head')].find(h => /World 910522/.test(h.textContent))")
time.sleep(1.5)
mark("before-play")
tap(by_text("#games button", "^\\s*(play|jogar)"))
mark("play")
time.sleep(1.5)
js("window.scrollTo({top: 0, behavior: 'smooth'})")
time.sleep(7.0)

# Ao vivo
page("live")
mark("live")
time.sleep(1.0)
tap("document.getElementById('live-start')")
time.sleep(9.0)

# Ajustes: a saturacao muda no jogo enquanto o dedo anda
page("settings")
mark("settings")
time.sleep(1.5)
tap(by_text("#settings summary", "colou?r|cor"))
time.sleep(1.2)
sat = "[...document.querySelectorAll('#settings input[type=range]')].find(i => /saturation/.test(i.id))"
scroll_to(sat, -300)
time.sleep(1.2)
orig = js("(%s || {}).value" % sat)
mark("saturation %s" % orig)


def slide(to, steps=24, each=0.06):
    start = int(js("%s.value" % sat))
    for i in range(1, steps + 1):
        v = round(start + (to - start) * i / steps)
        js("(() => { const e = %s; e.value = %d; e.dispatchEvent(new Event('input')); })()" % (sat, v))
        time.sleep(each)
    js("%s.dispatchEvent(new Event('change'))" % sat)


tap(sat, click=False)
slide(0)
time.sleep(2.5)
slide(190)
time.sleep(2.5)
slide(int(orig or 100))
mark("saturation back")
time.sleep(1.5)

# Estado
page("status")
mark("status")
time.sleep(2.5)
tap("document.getElementById('shot-take')")
time.sleep(4.0)
js("window.scrollBy({top: 500, behavior: 'smooth'})")
time.sleep(3.0)
js("window.scrollBy({top: 600, behavior: 'smooth'})")
time.sleep(2.5)

# Arquivos, filtro de ROMs, downloads
page("files")
mark("files")
time.sleep(2.0)
tap(by_text("#files a, #files button, #files td", "^\\s*roms\\s*$"))
time.sleep(2.5)
page("romfilter")
mark("romfilter")
time.sleep(4.0)
js("window.scrollBy({top: 600, behavior: 'smooth'})")
time.sleep(2.5)
page("downloads")
mark("downloads")
time.sleep(3.5)

# Terminal
page("terminal")
mark("terminal")
time.sleep(1.0)
tap("document.getElementById('term-open')")
time.sleep(2.5)
js("(() => { const t = document.querySelector('#term textarea'); if (t) t.focus(); })()")
for line in ("uptime\r", "ls ~/roms\r"):
    for ch in line:
        call("Input.insertText", text=ch)
        time.sleep(0.07)
    time.sleep(1.4)
time.sleep(1.5)

# De volta: fecha o jogo
page("frontend")
mark("close")
time.sleep(1.5)
tap("document.getElementById('close-game')")
time.sleep(6.0)
mark("end")
call("Page.stopScreencast")
time.sleep(0.5)
print("frames", frames[0])
os._exit(0)
