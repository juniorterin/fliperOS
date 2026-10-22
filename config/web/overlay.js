// O marquee para o OBS (overlay.html): pede o estado do marquee a cada
// segundo (/api/overlay/state, com a chave do endereco) e desenha a arte do
// jogo ou do sistema, o nome quando nao ha arte, o texto de abertura (os
// recordes, "Now Playing") rolando uma vez, as conquistas e o placar versus.
"use strict";

const params = new URLSearchParams(location.search);
const key = params.get("key") || "";
const showText = params.get("text") !== "0";
if (params.get("led") === "1") document.documentElement.classList.add("led");

const $ = (id) => document.getElementById(id);
let lastTime = null, lastArt = null, popTimer = null;

function setText(el, text) {
  el.textContent = text || "";
}

function ticker(text) {
  const box = $("ticker"), span = $("ticker-text");
  if (!showText || !text) { box.hidden = true; return; }
  // Rola uma vez, mais devagar quanto mais comprido.
  span.style.animation = "none";
  setText(span, text);
  span.style.setProperty("--time", Math.max(8, Math.min(40, text.length * 0.35)) + "s");
  box.hidden = false;
  void span.offsetWidth;
  span.style.animation = "";
  span.onanimationend = () => { box.hidden = true; };
}

function popup(text) {
  if (!showText || !text) return;
  setText($("pop-text"), text);
  $("pop").hidden = false;
  clearTimeout(popTimer);
  popTimer = setTimeout(() => { $("pop").hidden = true; }, 8000);
}

function showArt(url) {
  const art = $("art");
  if (url === lastArt) return;
  lastArt = url;
  if (!url) { art.hidden = true; art.removeAttribute("src"); return; }
  const next = new Image();
  next.onload = () => {
    if (lastArt !== url) return;
    // A arte feita para o DMD (128x32) fica em pixels; o resto, suave.
    art.classList.toggle("pixel", next.naturalWidth <= 256 && next.naturalHeight <= 64);
    art.src = url;
    art.hidden = false;
    render.title();
  };
  next.onerror = () => { if (lastArt === url) { art.hidden = true; render.title(); } };
  next.src = url;
}

const render = {
  state: {},
  title() {
    // O nome do jogo (ou do sistema) so quando nao ha arte.
    const s = render.state, title = $("title");
    const versus = s.event === "versus";
    title.hidden = versus || !$("art").hidden || !showText || !(s.title || s.system);
    setText(title, s.title || (s.system || "").toUpperCase());
    title.classList.toggle("system", s.event === "system");
  },
};

function apply(data) {
  const s = data.state || {};
  render.state = s;
  const versus = s.event === "versus";
  $("versus").hidden = !versus;
  if (versus) {
    setText($("vs-left"), s.left || "P1");
    setText($("vs-right"), s.right || "P2");
    setText($("vs-wins-left"), s.wins_left && s.wins_left !== "-" ? s.wins_left : "0");
    setText($("vs-wins-right"), s.wins_right && s.wins_right !== "-" ? s.wins_right : "0");
    setText($("vs-score-left"), s.score_left && s.score_left !== "-" ? s.score_left : "");
    setText($("vs-score-right"), s.score_right && s.score_right !== "-" ? s.score_right : "");
  }
  showArt(versus || !data.enabled ? null : data.art || null);
  render.title();
  if (s.time !== lastTime) {
    const first = lastTime === null;
    lastTime = s.time;
    // Na primeira leitura nada rola: o texto ja era velho quando a pagina abriu.
    if (!first && s.event === "achievement") popup(s.text);
    else if (!first && s.event === "game") ticker(s.text);
  }
}

async function poll() {
  try {
    const res = await fetch("/api/overlay/state?key=" + encodeURIComponent(key), { cache: "no-store" });
    if (res.status === 403) {
      $("error").hidden = false;
      setText($("error"), "FliperOS: wrong overlay address (copy it again from the web panel).");
    } else if (res.ok) {
      $("error").hidden = true;
      apply(await res.json());
    }
  } catch (e) {
    // O gabinete desligado: fica o que estava.
  }
  setTimeout(poll, 1000);
}

poll();
