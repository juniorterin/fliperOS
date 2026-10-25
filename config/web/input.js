// O controle para o OBS (input.html): um painel por jogador, aceso pelos
// comandos apertados que o gabinete manda (/api/overlay/input/events, com a
// chave do endereco). O CSS e o do painel web (/api/overlay/input/css).
//
// O que o CSS ve, por jogador:
//   <section class="pad p1" data-player="1">       .pad.active: algo apertado
//     <div class="label">P1</div>
//     <div class="stick up left" data-dir="up-left"> as direcoes apertadas
//       <div class="gate"></div><div class="ball"></div></div>
//     <div class="buttons">
//       <div class="button b1 on" data-control="b1"><span>1</span></div> ... b6
//     </div>
//     <div class="system">
//       <div class="button start" data-control="start"><span>Start</span></div>
//       <div class="button coin" data-control="coin"><span>Coin</span></div>
//     </div>
//   </section>
// No <body>: players-N (quantos paineis). Os botoes 1 2 3 em cima e 4 5 6
// embaixo, como no Button mapping.
"use strict";

const params = new URLSearchParams(location.search);
const key = params.get("key") || "";
const demo = params.get("demo") === "1";
const players = (params.get("players") || "1").split(",").filter((p) => /^[1-4]$/.test(p));
if (!players.length) players.push("1");
const $ = (id) => document.getElementById(id);
const DIRS = ["up", "down", "left", "right"];
const pads = {};

function node(tag, cls, text) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text != null) el.append(text);
  return el;
}

function button(control, text) {
  const el = node("div", "button " + control);
  el.dataset.control = control;
  el.append(node("span", null, text));
  return el;
}

function build() {
  document.body.classList.add("players-" + players.length);
  for (const player of players) {
    const pad = node("section", "pad p" + player);
    pad.dataset.player = player;
    const stick = node("div", "stick");
    stick.append(node("div", "gate"), node("div", "ball"));
    const buttons = node("div", "buttons");
    for (let n = 1; n <= 6; n++) buttons.append(button("b" + n, String(n)));
    const system = node("div", "system");
    system.append(button("start", "Start"), button("coin", "Coin"));
    pad.append(node("div", "label", "P" + player), stick, buttons, system);
    $("pads").append(pad);
    pads[player] = { pad, stick, controls: pad.querySelectorAll("[data-control]") };
  }
}

function show(state) {
  for (const player of players) {
    const p = pads[player], on = new Set(state[player] || []);
    for (const el of p.controls) el.classList.toggle("on", on.has(el.dataset.control));
    const dirs = DIRS.filter((d) => on.has(d));
    for (const d of DIRS) p.stick.classList.toggle(d, on.has(d));
    p.stick.dataset.dir = dirs.join("-");
    p.pad.classList.toggle("active", on.size > 0);
  }
}

async function loadStyle() {
  try {
    const res = await fetch("/api/overlay/input/css?key=" + encodeURIComponent(key), { cache: "no-store" });
    if (res.status === 403) return error("FliperOS: wrong overlay address (copy it again from the web panel).");
    if (res.ok) $("style").textContent = await res.text();
  } catch (e) {
    setTimeout(loadStyle, 3000);
  }
}

function error(text) {
  $("error").hidden = !text;
  $("error").textContent = text || "";
}

function listen() {
  // O EventSource reconecta sozinho quando o gabinete volta.
  const events = new EventSource("/api/overlay/input/events?key=" + encodeURIComponent(key));
  events.onmessage = (ev) => {
    error("");
    try { show(JSON.parse(ev.data)); } catch (e) { /* linha estragada */ }
  };
  events.onerror = () => show({});
}

// A demonstracao: um golpe de luta (meia-lua para frente + soco) e os outros
// botoes, em volta, para ver o CSS sem ninguem no gabinete.
function runDemo() {
  const steps = [["down"], ["down", "right"], ["right", "b1"], ["right"], [], ["b2"], ["b3"], [], ["b4"], ["b5"],
    ["b6"], [], ["up"], ["up", "left"], ["left", "b4", "b5"], [], ["start"], ["coin"], []];
  let i = 0;
  setInterval(() => {
    const step = steps[i++ % steps.length];
    show(Object.fromEntries(players.map((p) => [p, step])));
  }, 280);
}

build();
// Na previa do painel (&preview=1) o CSS e o que esta sendo escrito, que o
// painel poe no <style>.
if (!(params.get("preview") === "1" && window.parent !== window)) loadStyle();
if (demo) runDemo(); else listen();
