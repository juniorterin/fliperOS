// Frontend, o gabinete desenhado: mostra o que esta de verdade no tubo.
//  - O letreiro: a arte marquee do jogo aberto (ou o logo, ou o nome).
//  - A tela: ao vivo (WebRTC, pelo botao), a captura real a cada 10 s, o
//    video ou a snap do jogo (~/media), ou o modo atracao sem jogo.
//  - O painel: os botoes e o direcional acesos quando alguem aperta no
//    gabinete (/api/input/events, o mesmo do controle para o OBS); com um jogo
//    de arcade, as cores e as funcoes dos botoes do Arcade Database.
//  - A base: o FPS num LED de sete segmentos.
// Ao lado, "Jogando agora": o nome de verdade, a pasta, os controles, o modo
// de video no tubo, as partidas, o volume e o frontend por tras do jogo.
"use strict";

const fpsHistory = [];
let cabGame = null, cabFront = null, cabOnline = true, cabPanel = null;
let shotUrl = null, shotAt = 0, shotBusy = false, shotGame = "";
let inputEvents = null, crtLive = null, liveReady = false;

// ── Os icones dos controles (aqui e na folha do jogo) ─────────────
// Os jogadores em bonequinhos, o direcional em setas (8, 4 ou 2 direcoes) e
// os botoes em bolinhas, com as cores do jogo quando o Arcade Database as tem.
const WAYS = { 8: [0, 45, 90, 135, 180, 225, 270, 315], 4: [0, 90, 180, 270], 2: [90, 270] };
const BUTTON_COLORS = ["var(--pink)", "var(--cyan)", "var(--green)", "var(--yellow)", "var(--orange)", "var(--purple)"];

function controlInfo(game) {
  const control = String(game.control || game.Control || "").toLowerCase();
  const players = parseInt(game.players || game.Players, 10) || 0;
  const buttons = parseInt(game.buttons || game.Buttons, 10) || 0;
  let ways = 0, special = "";
  const m = control.match(/(\d)\s*-?\s*way/) || control.match(/joy\s*(\d)/);
  if (m && WAYS[m[1]]) ways = Number(m[1]);
  else if (/gun/.test(control)) special = "px-guncon";
  else if (/trackball|dial|spinner|paddle|positional|wheel|pedal|steer/.test(control)) special = "px-axes";
  else if (/joy|stick/.test(control) || buttons) ways = 8;
  return { players, buttons, ways, special, control };
}

function controlTitle(info) {
  const parts = [];
  if (info.players) parts.push(info.players === 1 ? t("players_1") : t("players_n").replace("%n", info.players));
  if (info.ways) parts.push(t("ways_n").replace("%n", info.ways));
  else if (info.control) parts.push(info.control);
  if (info.buttons) parts.push(info.buttons === 1 ? t("buttons_1") : t("buttons_n").replace("%n", info.buttons));
  return parts.join(" · ");
}

function arrowPad(ways) {
  const svg = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="11.6" class="pad-base"/>' +
    WAYS[ways].map((a) => '<polygon class="pad-arrow" points="12,1.2 14.6,4.6 12.9,4.6 12.9,7 11.1,7 11.1,4.6 9.4,4.6"' +
      ' transform="rotate(' + a + ' 12 12)"/>').join("") + '<circle cx="12" cy="12" r="2.4" class="pad-ball"/></svg>';
  const span = el("span", { class: "rose" });
  span.innerHTML = svg;
  return span;
}

function controlIcons(game, colors, big) {
  const info = controlInfo(game);
  const box = el("span", { class: "ctrl" + (big ? " big" : ""), title: controlTitle(info) });
  if (info.players) {
    const people = el("span", { class: "players" });
    for (let i = 0; i < Math.min(info.players, 4); i++) people.append(icon("g-player"));
    box.append(people);
  }
  if (info.ways || info.special) {
    if (box.children.length) box.append(el("i", { class: "sep" }));
    box.append(info.ways ? arrowPad(info.ways) : icon(info.special));
  }
  if (info.buttons) {
    const dots = el("span", { class: "dots" });
    for (let i = 0; i < Math.min(info.buttons, 8); i++) {
      const dot = el("i");
      const c = colors && colors[i];
      dot.style.setProperty("--c", c && /^[a-z]+$/i.test(c) ? c : BUTTON_COLORS[i % 6]);
      dots.append(dot);
    }
    box.append(dots);
  }
  return box.children.length ? box : null;
}

// ── O LED de sete segmentos ──────────────────────────────────────
const SEGMENTS = { a: [1, 0, 8, 2], b: [8, 1, 2, 8], c: [8, 9, 2, 8], d: [1, 16, 8, 2], e: [0, 9, 2, 8], f: [0, 1, 2, 8],
  g: [1, 8, 8, 2] };
const DIGITS = { 0: "abcdef", 1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc", 5: "afgcd", 6: "afgedc", 7: "abc", 8: "abcdefg",
  9: "abcdfg", "-": "g", " ": "" };

function led(node, text) {
  if (node.dataset.value === text) return;
  node.dataset.value = text;
  let html = "";
  for (const ch of text) {
    if (ch === ".") { html += '<svg viewBox="0 0 3 18"><rect x="0" y="15" width="3" height="3" class="on"/></svg>'; continue; }
    const lit = DIGITS[ch] || "";
    html += '<svg viewBox="0 0 10 18" shape-rendering="crispEdges">' + Object.entries(SEGMENTS).map(([s, [x, y, w, h]]) =>
      '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" class="' + (lit.includes(s) ? "on" : "off") + '"/>').join("") + "</svg>";
  }
  node.innerHTML = html;
}

// ── O FPS do ultimo minuto ───────────────────────────────────────
function drawFps() {
  const canvas = $("fps-chart"), ctx = canvas.getContext("2d");
  const ratio = window.devicePixelRatio || 1, w = canvas.clientWidth, h = canvas.clientHeight;
  if (!w) return;
  canvas.width = w * ratio; canvas.height = h * ratio;
  ctx.scale(ratio, ratio);
  ctx.clearRect(0, 0, w, h);
  const top = Math.max(60, ...fpsHistory.map((p) => p || 0)) * 1.1;
  ctx.strokeStyle = "rgba(68,71,90,.9)";
  ctx.setLineDash([3, 3]);
  const y60 = h - (60 / top) * h;
  ctx.beginPath(); ctx.moveTo(0, y60); ctx.lineTo(w, y60); ctx.stroke();
  ctx.setLineDash([]);
  ctx.strokeStyle = "#50fa7b";
  ctx.shadowColor = "#50fa7b";
  ctx.shadowBlur = 6;
  ctx.lineWidth = 2;
  ctx.beginPath();
  let pen = false;
  fpsHistory.forEach((v, i) => {
    const x = (i / 59) * w;
    if (v == null) { pen = false; return; }
    const y = h - (v / top) * h;
    if (pen) ctx.lineTo(x, y); else ctx.moveTo(x, y);
    pen = true;
  });
  ctx.stroke();
}

// ── A tela do tubo ───────────────────────────────────────────────
// Uma troca de jogo: chiado, e a tela "liga" com o jogo novo.
function crtFlash(kind) {
  const crt = $("crt");
  crt.classList.remove("power-on", "power-off", "static");
  void crt.offsetWidth;
  crt.classList.add(kind);
}

function crtShow() {
  const img = $("crt-img"), video = $("crt-video"), tag = $("crt-tag"), game = cabGame;
  const live = !!crtLive;
  const fresh = shotUrl && shotGame === gameKey(game) && Date.now() - shotAt < 60000;
  let mode = "attract";
  if (!cabOnline) mode = "off";
  else if (live) mode = "live";
  else if (fresh) mode = "shot";
  else if (game && game.art && game.art.includes("v")) mode = "video";
  else if (game && game.art && game.art.includes("s")) mode = "snap";
  else if (shotUrl && Date.now() - shotAt < 60000) mode = "shot";
  $("cab").dataset.state = mode === "off" ? "off" : game ? "game" : cabFront ? "front" : "attract";
  $("crt-live").hidden = mode !== "live";
  video.hidden = mode !== "video";
  img.hidden = !(mode === "shot" || mode === "snap");
  $("crt-attract").hidden = mode !== "attract";
  if (mode === "shot" && img.src !== shotUrl) crtImage(img, shotUrl);
  if (mode === "snap") {
    const url = mediaUrl(game.system, game.name, "snap");
    if (img.dataset.src !== url) { img.dataset.src = url; crtImage(img, url); }
  } else if (mode === "shot") img.dataset.src = "";
  if (mode === "video") {
    const url = mediaUrl(game.system, game.name, "preview");
    if (video.dataset.src !== url) { video.dataset.src = url; video.src = url; video.play().catch(() => {}); }
  } else if (!video.paused) video.pause();
  tag.hidden = !["shot", "snap", "video"].includes(mode);
  if (mode === "shot") tag.textContent = t("crt_shot").replace("%s", shotAge());
  else tag.textContent = t("crt_art");
  $("crt-attract-text").textContent = mode === "attract" && cabFront ? frontName(cabFront.program).toUpperCase() : "INSERT COIN";
}

// Uma imagem nova na tela do tubo aparece aos poucos.
function crtImage(img, url) {
  img.classList.add("fade");
  img.classList.remove("in");
  img.onload = () => img.classList.add("in");
  img.src = url;
}

function shotAge() {
  const s = Math.round((Date.now() - shotAt) / 1000);
  return s < 3 ? t("now_word") : t("ago_s").replace("%n", s);
}

const gameKey = (game) => (game ? game.pid + ":" + (game.name || game.file || "") : "");

// O PNG do que esta na tela (/api/screenshot): o quadro do jogo ou do
// frontend pela camada OpenGL, o desktop pelo X.
async function takeShot(manual) {
  if (shotBusy) return;
  shotBusy = true;
  $("shot-take").disabled = true;
  if (manual) $("shot-note").textContent = t("shot_wait");
  try {
    const res = await api("/api/screenshot");
    if (!res.ok) {
      if (manual) $("shot-note").textContent = (await res.json().catch(() => ({}))).error || res.statusText;
      return;
    }
    const blob = await res.blob();
    if (shotUrl) URL.revokeObjectURL(shotUrl);
    shotUrl = URL.createObjectURL(blob);
    shotAt = Date.now();
    shotGame = gameKey(cabGame);
    if (manual) {
      crtFlash("flash");
      const source = res.headers.get("X-Shot-Source") === "x11" ? t("shot_x11") : t("shot_gl");
      $("shot-note").textContent = source;
    }
    const save = $("shot-save");
    save.href = shotUrl;
    save.download = "fliperos-" + new Date().toISOString().replace(/[:.]/g, "-") + ".png";
    save.hidden = false;
    crtShow();
  } catch (e) {
    if (e.message !== "login" && manual) $("shot-note").textContent = String(e);
  } finally {
    $("shot-take").disabled = false;
    shotBusy = false;
  }
}

// A captura sozinha a cada 10 s, com o Frontend aberto e a aba a vista.
setInterval(() => {
  if ($("shot-auto").checked && document.visibilityState === "visible" && area === "frontend" && !$("app").hidden
      && cabOnline && !crtLive) takeShot(false);
}, 10000);
$("shot-take").addEventListener("click", () => takeShot(true));

// ── Ao vivo dentro do tubo ───────────────────────────────────────
// A mesma tela ao vivo da area Ao vivo (go2rtc pelo /api/stream/offer), sem
// som, a 30 quadros; cada quadro copiado num canvas de pixels nitidos.
async function crtLiveStart() {
  crtLiveStop();
  const video = $("crt-live-video"), canvas = $("crt-live"), ctx = canvas.getContext("2d", { alpha: false });
  const pc = new RTCPeerConnection({ iceServers: [] });
  crtLive = pc;
  $("now-live").classList.add("on");
  $("crt-live-btn").classList.add("on");
  crtFlash("static");
  const stream = new MediaStream();
  pc.addTransceiver("video", { direction: "recvonly" });
  video.srcObject = stream;
  pc.ontrack = (ev) => { stream.addTrack(ev.track); video.play().catch(() => {}); };
  const draw = () => {
    if (crtLive !== pc) return;
    if (video.videoWidth) {
      if (canvas.width !== video.videoWidth) { canvas.width = video.videoWidth; canvas.height = video.videoHeight; }
      ctx.drawImage(video, 0, 0);
    }
    video.requestVideoFrameCallback ? video.requestVideoFrameCallback(draw) : requestAnimationFrame(draw);
  };
  draw();
  pc.onconnectionstatechange = () => {
    if (crtLive === pc && ["failed", "disconnected"].includes(pc.connectionState)) { crtLiveStop(); toast(t("live_lost"), "bad"); }
  };
  try {
    await pc.setLocalDescription(await pc.createOffer());
    await liveIce(pc);
    const res = await api("/api/stream/offer", { method: "POST", body: JSON.stringify({ fps: 30, sdp: pc.localDescription.sdp }) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    if (crtLive !== pc) return;
    await pc.setRemoteDescription({ type: "answer", sdp: data.sdp });
    crtShow();
  } catch (e) {
    if (crtLive === pc) crtLiveStop();
    if (e.message !== "login") toast(String(e.message || e), "bad");
  }
}

function crtLiveStop() {
  if (crtLive) crtLive.close();
  crtLive = null;
  $("crt-live-video").srcObject = null;
  $("now-live").classList.remove("on");
  $("crt-live-btn").classList.remove("on");
  crtShow();
}

function crtLiveToggle() {
  if (crtLive) crtLiveStop(); else crtLiveStart();
}
$("now-live").addEventListener("click", crtLiveToggle);
$("crt-live-btn").addEventListener("click", crtLiveToggle);

// A tela ao vivo instalada e ligada: os botoes de ao vivo aparecem.
async function cabStream() {
  try {
    const s = await (await api("/api/stream")).json();
    liveReady = !!(s.installed && s.active);
  } catch (e) { liveReady = false; }
  $("now-live").hidden = !liveReady;
  $("crt-live-btn").hidden = !liveReady;
  $("crt-live-text").textContent = t("crt_live");
}

// ── O painel de controle aceso ───────────────────────────────────
function lightPanel(state) {
  for (const player of document.querySelectorAll(".cp .player")) {
    const on = new Set(state[player.dataset.player] || []);
    player.querySelectorAll("[data-control]").forEach((b) => b.classList.toggle("on", on.has(b.dataset.control)));
    const stick = player.querySelector(".stick");
    stick.className = "stick " + ["up", "down", "left", "right"].filter((d) => on.has(d)).join(" ");
  }
  const sys = new Set([...(state["1"] || []), ...(state["2"] || [])]);
  document.querySelectorAll(".sysbtns [data-control]").forEach((b) => b.classList.toggle("on", sys.has(b.dataset.control)));
  if (sys.has("coin")) coinDrop();
}

function inputStart() {
  if (inputEvents) return;
  inputEvents = new EventSource("/api/input/events");
  inputEvents.onmessage = (ev) => { try { lightPanel(JSON.parse(ev.data)); } catch (e) { /* linha estragada */ } };
  inputEvents.onerror = () => lightPanel({});
}

function inputStop() {
  if (inputEvents) inputEvents.close();
  inputEvents = null;
  lightPanel({});
}

// As cores e as funcoes dos botoes do jogo (o painel do Arcade Database, na
// posicao do Setup > Joysticks > Buttons layout).
function paintPanel(panel) {
  cabPanel = panel;
  document.querySelectorAll(".cp .btns").forEach((btns) => {
    btns.querySelectorAll("b").forEach((b, i) => {
      const cell = panel && panel[i];
      b.style.setProperty("--c", cell && /^[a-z]+$/i.test(cell.color) ? cell.color : BUTTON_COLORS[i]);
      b.classList.toggle("unused", !!panel && !cell);
      b.title = cell ? cell.label || "" : "";
    });
  });
}

// A ficha caindo (o Coin do gabinete, ou o Jogar daqui).
function coinDrop() {
  const base = document.querySelector(".coins");
  const coin = el("i", { class: "coin-fall" });
  base.append(coin);
  setTimeout(() => coin.remove(), 900);
}

// ── O letreiro ───────────────────────────────────────────────────
function marquee(game) {
  const img = $("cab-marquee-img"), box = $("cab-marquee-text");
  let url = "";
  if (game && game.art && game.art.includes("m")) url = mediaUrl(game.system, game.name, "marquee");
  else if (game && game.art && game.art.includes("l")) url = mediaUrl(game.system, game.name, "logo");
  if (img.dataset.src !== url) {
    img.dataset.src = url;
    img.hidden = !url;
    if (url) img.src = url;
    $("cab-marquee").classList.toggle("logo", !!url && !game.art.includes("m"));
    $("cab-marquee").classList.remove("lit");
    void $("cab-marquee").offsetWidth;
    $("cab-marquee").classList.add("lit");
  }
  box.hidden = !!url;
  const title = game ? game.title || game.name || game.file || game.program : cabFront ? frontName(cabFront.program) : "FliperOS";
  const text = title.replace(/\s*\(.*$/, "").toUpperCase();
  box.lastChild.textContent = game ? [game.manufacturer, game.year].filter(Boolean).join(" · ").toUpperCase() : "";
  // Mede de novo so quando o nome (ou se ele aparece) muda: o status chega a
  // cada poucos segundos e a rolagem nao pode recomecar.
  const key = text + "|" + box.hidden;
  if (box.dataset.key !== key) {
    box.dataset.key = key;
    box.firstChild.textContent = text;
    document.fonts.ready.then(() => requestAnimationFrame(() => cabRun(box)));
  }
}

// O nome que nao cabe no letreiro roda sem parar, como um letreiro de LED.
function cabRun(box) {
  const span = box.firstChild;
  box.classList.remove("run");
  if (box.hidden || !box.clientWidth) return;
  const room = box.getBoundingClientRect(), r = span.getBoundingClientRect();
  if (r.width <= room.width - 20) return;
  // Da direita (fora) ate sumir pela esquerda; o atraso negativo comeca com o
  // nome ja no lugar, a partir da esquerda do letreiro.
  const from = room.right - r.left, to = room.left - r.right, time = Math.max(6, span.textContent.length * 0.45);
  span.style.setProperty("--from", from + "px");
  span.style.setProperty("--to", to + "px");
  span.style.setProperty("--time", time + "s");
  span.style.setProperty("--delay", (-time * (room.left + 10 - r.left - from) / (to - from)).toFixed(2) + "s");
  box.classList.add("run");
}

// ── Os nomes dos frontends ───────────────────────────────────────
const FRONTENDS = { attractplus: ["Attract-Mode Plus", "attractplus"], attract: ["Attract-Mode", "attractplus"],
  emulationstation: ["ES-DE", "emulationstation"], "es-de": ["ES-DE", "emulationstation"],
  "pegasus-fe": ["Pegasus", "pegasus"], "fliperos-frontend": ["FliperOS", ""], "fliperos-gui": ["Setup", ""] };
const frontName = (program) => (FRONTENDS[program] || [program])[0];

function frontIcon(program) {
  const name = (FRONTENDS[program] || [])[1];
  return name ? el("img", { src: "/gui/icons/" + name + ".png", alt: "" }) : icon("px-frontend");
}

// ── Jogando agora ────────────────────────────────────────────────
function renderNow(s) {
  const game = cabGame, front = cabFront, fps = s && s.fps;
  $("now-eyebrow").textContent = !cabOnline ? t("cabinet_off") : game ? t("playing_now") : t("on_screen_now");
  $("now-card").classList.toggle("idle", !game);
  $("now-title").textContent = !cabOnline ? "—" : game ? game.title || game.name || game.file || game.program
    : front ? frontName(front.program) : t("idle_title");
  const sys = $("now-system");
  sys.hidden = !game;
  if (game) {
    const label = [game.system_name, game.program].filter(Boolean).join(" · ");
    if (sys.dataset.label !== label) {
      sys.dataset.label = label;
      sys.replaceChildren(game.icon ? el("img", { src: "/gui/icons/" + game.icon + ".png", alt: "" }) : icon("px-games"), label);
    }
  }
  const facts = $("now-facts"), key = game ? gameKey(game) + (cabPanel ? "p" : "") : "-";
  if (facts.dataset.key !== key) {
    facts.dataset.key = key;
    facts.replaceChildren();
    if (game) {
      const genre = [game.category, game.year, game.manufacturer].filter(Boolean).join(" · ");
      if (genre) facts.append(el("span", { class: "nfact" }, icon("px-games"), genre));
      const ctrl = controlIcons(game, cabPanel && cabPanel.map((c) => c && c.color));
      if (ctrl) { ctrl.classList.add("nfact"); facts.append(ctrl); }
      if (fps && fps.core) facts.append(el("span", { class: "nfact" }, icon("px-emulators"), t("core") + " " + fps.core));
    } else {
      facts.append(el("p", { class: "dim" }, cabOnline ? t("idle_text") : t("offline")));
    }
  }
  // O modo de video no tubo (o do Video Setup aplicado agora).
  const out = s && s.video && (s.video.outputs || []).find((o) => o.active);
  $("now-khz").textContent = out ? String(out.horizontal_khz).replace(".", lang === "pt" ? "," : ".") + " kHz" : "-";
  $("now-mode").textContent = out ? out.width + "×" + out.height + " · " + out.vertical_hz + " Hz · "
    + (out.interlaced ? t("interlaced") : t("progressive")) : "";
  const count = game && Number(game.playedcount || 0);
  $("now-played").textContent = !game ? "-" : !count ? t("never_played") : count === 1 ? t("played_once")
    : t("played_n").replace("%n", count);
  $("now-played-time").textContent = game && game.playedtime ? t("played_total").replace("%t", duration(game.playedtime)) : "";
  $("close-game").hidden = !game;
  // O frontend por tras do jogo.
  const ft = $("front-text"), fi = $("front-icon"), prog = front ? front.program : "";
  if (fi.dataset.program !== prog) { fi.dataset.program = prog; fi.replaceChildren(frontIcon(prog)); }
  ft.textContent = !front ? t("front_none") : (game ? t("front_back") : t("front_on")).replace("%s", frontName(front.program));
  // A barrinha do celular (quando o gabinete sai da tela).
  $("mini-title").textContent = $("now-title").textContent;
}

// ── O volume em blocos ───────────────────────────────────────────
function renderVolume(vol) {
  const percent = vol && vol.percent, vu = $("vu");
  if (!vu.children.length) {
    for (let i = 0; i < 20; i++) {
      const b = el("i", { "data-level": String((i + 1) * 5) });
      b.addEventListener("click", () => volume({ set: (i + 1) * 5 }));
      vu.append(b);
    }
  }
  const on = percent == null ? 0 : Math.round(percent / 5);
  [...vu.children].forEach((b, i) => { b.className = i < on ? "on" + (i >= 16 ? " r" : i >= 12 ? " y" : "") : ""; });
  vu.setAttribute("aria-valuenow", percent == null ? "0" : String(percent));
  $("vol-value").textContent = percent == null ? "-" : percent + "%";
  muteButton(vol && vol.muted);
}

async function volume(body) {
  const res = await api("/api/volume", { method: "POST", body: JSON.stringify(body) });
  renderVolume(await res.json().catch(() => ({})));
}
// O botao Mudo fica marcado enquanto o som esta mudo (pelas teclas do
// gabinete tambem: o status traz o estado do mixer).
function muteButton(muted) {
  $("vol-mute").setAttribute("aria-pressed", String(!!muted));
  $("vol-mute").classList.toggle("on", !!muted);
  $("vu").classList.toggle("muted", !!muted);
}
$("vol-up").addEventListener("click", () => volume({ action: "up" }));
$("vol-down").addEventListener("click", () => volume({ action: "down" }));
$("vol-mute").addEventListener("click", () => volume({ action: "mute" }));
$("vu").addEventListener("keydown", (ev) => {
  if (ev.key === "ArrowRight" || ev.key === "ArrowUp") { ev.preventDefault(); volume({ action: "up" }); }
  if (ev.key === "ArrowLeft" || ev.key === "ArrowDown") { ev.preventDefault(); volume({ action: "down" }); }
});

async function closeGame() {
  if (!(await ask({ title: t("confirm_close"), yes: t("close_game"), danger: true }))) return;
  await api("/api/close", { method: "POST", body: "{}" }).catch(() => {});
}
$("close-game").addEventListener("click", closeGame);
$("mini-close").addEventListener("click", closeGame);

// ── A cada status (1 s) ──────────────────────────────────────────
function renderCabinet(s) {
  const online = !!s;
  const game = s && s.running && s.running.game, front = s && s.running && s.running.frontend;
  const before = gameKey(cabGame), now = gameKey(game);
  cabOnline = online;
  cabFront = front || null;
  if (online) cabGame = game || null;
  if (online && before !== now) {
    // O jogo mudou: a tela liga com ele (ou desliga), e a captura antiga sai.
    crtFlash(game ? "power-on" : "power-off");
    paintPanel(null);
    if (game && game.system && game.name) {
      gameInfo(game.system, game.name).then((data) => { if (gameKey(cabGame) === now) { paintPanel(data.panel || null); renderNow(s); } })
        .catch(() => {});
      // A captura de verdade depois que o jogo abriu.
      setTimeout(() => { if (gameKey(cabGame) === now && $("shot-auto").checked && area === "frontend") takeShot(false); }, 5000);
    }
  }
  $("cab-pwr").classList.toggle("off", !online);
  marquee(online ? cabGame : null);
  mqPaint(online ? cabGame : null);
  const fps = s && s.fps;
  led($("fps-led"), fps ? fps.fps.toFixed(1).padStart(4, " ") : " --");
  $("fps-led").className = "led " + (!fps ? "" : fps.fps >= 58 ? "good" : fps.fps >= 45 ? "warn" : "bad");
  $("fps-note").textContent = fps && fps.filtering ? t("filtering") : "";
  $("mini-fps").textContent = fps ? fps.fps.toFixed(1) + " FPS" : "";
  if (online) {
    fpsHistory.push(fps ? fps.fps : null);
    while (fpsHistory.length > 60) fpsHistory.shift();
    if (area === "frontend") drawFps();
    renderVolume(s.volume);
  }
  renderNow(s);
  crtShow();
}

// A barrinha fixa do celular: aparece quando o gabinete sai da tela.
new IntersectionObserver(([entry]) => {
  $("mini-now").hidden = entry.isIntersecting || !cabGame || area !== "frontend";
}).observe($("cab"));

// Entrar e sair do Frontend: os botoes acesos e a captura so com ele aberto.
function cabinetShown(shown) {
  if (shown) {
    inputStart();
    cabStream();
    drawFps();
  } else {
    inputStop();
    crtLiveStop();
    $("mini-now").hidden = true;
  }
}
paintPanel(null);
