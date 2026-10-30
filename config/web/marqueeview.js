// A previa do marquee: no Frontend, ao lado do Jogando agora, liga-se um modo (Pixelcade ou ZeDMD) e o
// painel mostra, no proprio cartao, no Ao vivo, na previa do marquee para o OBS e no
// letreiro do gabinete desenhado, o que aquele painel de LED mostraria para
// o jogo aberto. A arte segue as regras de cada um: o ZeDMD usa dmd/, marquee/
// e logo/ de ~/media (config/fliperos-dmd); o Pixelcade, marquee/ e logo/.
// Sem arte, o nome do jogo (ou do frontend). A escolha fica no navegador.
"use strict";

Object.assign(TEXT.en, {
  mq_title: "Marquee preview", mq_on: "Marquee preview mode", mq_device: "Show the marquee of",
  mq_note: "Shows on this panel what the LED marquee would display for the game that is open, without the hardware: here, in Live, in the marquee preview and on the cabinet drawing.",
  mq_pixelcade: "Pixelcade (LED 128×32)", mq_zedmd: "ZeDMD (LED 128×32)",
  mq_art_pixelcade: "Art: marquee, then logo, then the name.", mq_art_zedmd: "Art: dmd, then marquee, then logo, then the name.",
  mq_live: "Marquee as it will appear",
  mq_show: "When both exist, the marquee shows", mq_show_art: "Art", mq_show_score: "Scoreboard",
  mq_inst_ok: "%s is installed on the cabinet.", mq_inst_no_note: "%s is not installed on the cabinet (the preview works without it).",
  mq_inst_busy: "Installing %s… (see the tasks)", mq_inst_title: "Install %s?",
  mq_inst_text: "%s is not installed on the cabinet. The preview here works without it, but the real display needs it. Install it now? It downloads files and takes a while.",
  mq_inst_yes: "Install", mq_inst_no: "Not now", mq_hi: "High scores:",
});
Object.assign(TEXT.pt, {
  mq_title: "Prévia do marquee", mq_on: "Modo prévia do marquee", mq_device: "Mostrar o marquee do",
  mq_note: "Mostra neste painel o que o marquee de LED exibiria para o jogo aberto, sem o hardware: aqui, no Ao vivo, na prévia do marquee e no desenho do gabinete.",
  mq_pixelcade: "Pixelcade (LED 128×32)", mq_zedmd: "ZeDMD (LED 128×32)",
  mq_art_pixelcade: "Arte: marquee, depois logo, depois o nome.", mq_art_zedmd: "Arte: dmd, depois marquee, depois logo, depois o nome.",
  mq_live: "O marquee como vai aparecer",
  mq_show: "Quando existem os dois, o marquee mostra", mq_show_art: "Arte", mq_show_score: "Placar",
  mq_inst_ok: "%s está instalado no gabinete.", mq_inst_no_note: "%s não está instalado no gabinete (a prévia funciona sem ele).",
  mq_inst_busy: "Instalando %s… (veja as tarefas)", mq_inst_title: "Instalar o %s?",
  mq_inst_text: "O %s não está instalado no gabinete. A prévia aqui funciona sem ele, mas o display de verdade precisa dele. Instalar agora? Baixa arquivos e demora um pouco.",
  mq_inst_yes: "Instalar", mq_inst_no: "Agora não", mq_hi: "Recordes:",
});

// O que cada painel desenha: as letras de arte (campo "art" dos jogos) na
// ordem em que o dispositivo as procura, e as colunas de pontos do painel.
const MQ_DEVICES = {
  pixelcade: { name: "Pixelcade", size: "128×32", cols: 128, art: ["m", "l"] },
  zedmd: { name: "ZeDMD", size: "128×32", cols: 128, art: ["d", "m", "l"] },
};
const MQ_KINDS = { d: "dmd", m: "marquee", l: "logo" };
const MQ_STORE = "fliperos-marquee-preview";

// show: o que o marquee mostra quando ha arte e placar (score: o placar, o
// texto de abertura e as conquistas; art: so a arte).
let mq = { on: false, device: "pixelcade", show: "score" };
try {
  const saved = JSON.parse(localStorage.getItem(MQ_STORE) || "null");
  if (saved) {
    mq.on = !!saved.on;
    if (MQ_DEVICES[saved.device]) mq.device = saved.device;
    if (saved.show === "art" || saved.show === "score") mq.show = saved.show;
  }
} catch (e) { /* sem armazenamento */ }

function mqSave() {
  try { localStorage.setItem(MQ_STORE, JSON.stringify(mq)); } catch (e) { /* sem armazenamento */ }
}

// O painel de LED de um lugar da pagina: a imagem, o nome (sem imagem), os
// pontos por cima e o selo com o dispositivo.
function mqBuild(box) {
  if (box.firstChild) return;
  box.append(el("img", { alt: "", hidden: "" }), el("span", { class: "mq-name" }),
    el("div", { class: "mq-versus", hidden: "" }, el("span", { class: "mq-side" }, el("b"), el("small")), el("span", { class: "mq-wins" }),
      el("span", { class: "mq-side" }, el("b"), el("small"))),
    el("div", { class: "mq-ticker", hidden: "" }, el("span")), el("div", { class: "mq-pop", hidden: "" }),
    el("span", { class: "mq-hi", hidden: "" }),
    el("div", { class: "mq-syslogo", hidden: "" }, el("img", { class: "old", alt: "", hidden: "" }), el("img", { class: "new", alt: "" })),
    el("img", { class: "mq-idle", alt: "", hidden: "" }),
    el("i", { class: "mq-dots" }), el("small", { class: "mq-tag" }));
}

// ── O placar ─────────────────────────────────────────────────────
// O mesmo estado do marquee do OBS (/api/marquee/state, que o
// fliperos-pixelcade grava com marquee_overlay=on): o placar versus no lugar
// da arte, o texto de abertura (os recordes) rolando uma vez e as conquistas.
// Alem do evento versus (que o marquee do LED so manda depois da primeira
// vitoria), o painel mostra o placar que o detector le agora (data.live),
// mesmo em 0 x 0: assim se ve que o jogo tem placar desde o comeco.
let mqState = {}, mqLive = null, mqHi = [], mqLastTime = null, mqPopTimer = null, mqTried = false;

// Os recordes do jogo (o .hi do plugin hiscore, lido pelo hi2txt no
// servidor): o primeiro no painel de LED ("HI 19,130 DAA") e os tres
// primeiros na linha do cartao.
const mqScore = (s) => Number(s).toLocaleString(locale());
function mqDrawHi(box) {
  const hi = box.querySelector(".mq-hi"), top = mqHi[0];
  hi.hidden = !top || mq.show !== "score";
  if (top) hi.textContent = "HI " + mqScore(top.score) + (top.name ? " " + top.name : "");
}
function mqDrawHiList() {
  const line = $("mq-hi-list");
  line.hidden = !mqHi.length;
  line.textContent = mqHi.length ? t("mq_hi") + " " + mqHi.slice(0, 3).map((r, i) =>
    "#" + (r.rank || i + 1) + " " + mqScore(r.score) + (r.name ? " " + r.name : "")).join("  ·  ") : "";
}

// A troca de sistema no frontend do FliperOS: o logotipo escrito do sistema
// (o do Arcadeflow, desenhado no gabinete pelo fliperos-syslogo) entra
// deslizando pelo lado para onde a lista andou, com o de antes saindo, e
// pisca duas vezes (stream.css, o mesmo tempo do Pixelcade e do ZeDMD). Fica
// ate o proximo evento. fresh: o evento acabou de chegar (ao abrir a pagina o
// logotipo so aparece parado).
// Sem jogo aberto e sem evento que desenhe algo (o jogo acabou de fechar e o
// frontend ainda nao mandou o sistema), fica o ultimo logotipo de sistema, e
// nao o nome FLIPEROS.
let mqFresh = false, mqLastSys = "";
function mqDrawLogo(box) {
  const wrap = box.querySelector(".mq-syslogo"), s = mqState;
  if (!wrap) return;
  if (s.event === "system" && s.logo) mqLastSys = s.logo;
  const open = typeof cabGame !== "undefined" && cabOnline && !!cabGame;
  const hold = !open && !!mqLastSys && !["system", "attract", "versus"].includes(s.event);
  const on = (s.event === "system" && !!s.logo) || hold;
  wrap.hidden = !on;
  box.classList.toggle("sys", on);
  if (!on) { delete box.dataset.logoKey; return; }
  const name = hold ? mqLastSys : s.logo;
  const k = name + "|" + (hold ? "hold" : s.time);
  if (box.dataset.logoKey === k || (hold && box.dataset.logoKey && box.dataset.logoKey.startsWith(name + "|"))) return;
  box.dataset.logoKey = k;
  const [gone, now] = wrap.querySelectorAll("img");
  const url = (n) => "/api/marquee/logo?name=" + encodeURIComponent(n);
  now.src = url(name);
  const slide = mqFresh && !hold;
  gone.hidden = !(slide && s.old);
  if (!gone.hidden) gone.src = url(s.old);
  wrap.style.setProperty("--side", s.step === "-1" ? "-1" : "1");
  wrap.classList.remove("go");
  void wrap.offsetWidth;
  if (slide) wrap.classList.add("go");
}

// O marquee parado: o evento attract (o frontend do FliperOS sem apertos por
// 30 s, ou o protetor de tela do ES-DE e do Attract-Mode Plus). O Pixelcade e o
// ZeDMD tocam a animacao do logo (o GIF 128x32), e a previa tambem, recomecando
// a cada evento.
function mqDrawIdle(box) {
  const img = box.querySelector(".mq-idle");
  if (!img) return;
  const on = mqState.event === "attract";
  img.hidden = !on;
  box.classList.toggle("ani", on);
  if (!on) { delete box.dataset.idleKey; return; }
  const k = String(mqState.time);
  if (box.dataset.idleKey === k) return;
  box.dataset.idleKey = k;
  img.onerror = () => { img.hidden = true; box.classList.remove("ani"); };
  img.src = "/api/marquee/idle?t=" + encodeURIComponent(k);
}

function mqDrawState(box) {
  mqDrawIdle(box);
  mqDrawLogo(box);
  mqDrawHi(box);
  const s = mqState.event === "versus" || !mqLive ? mqState : Object.assign({ left: "P1", right: "P2" }, mqLive);
  const versus = (mqState.event === "versus" || !!mqLive) && mq.show === "score";
  box.classList.toggle("vs", versus);
  const vs = box.querySelector(".mq-versus");
  vs.hidden = !versus;
  if (!versus) return;
  const num = (v) => (v && v !== "-" ? v : "");
  const sides = vs.querySelectorAll(".mq-side");
  sides[0].firstChild.textContent = s.left || "P1";
  sides[0].lastChild.textContent = num(s.score_left);
  sides[1].firstChild.textContent = s.right || "P2";
  sides[1].lastChild.textContent = num(s.score_right);
  vs.querySelector(".mq-wins").textContent = (num(s.wins_left) || "0") + " – " + (num(s.wins_right) || "0");
}

function mqEvents(s, first) {
  if (s.time === mqLastTime) return;
  mqLastTime = s.time;
  // Na primeira leitura nada rola: o texto ja era velho quando a pagina abriu.
  if (first || !s.text || mq.show !== "score") return;
  document.querySelectorAll(".mq-led").forEach((box) => {
    if (box.hidden) return;
    if (s.event === "achievement") {
      const pop = box.querySelector(".mq-pop");
      pop.textContent = "🏆 " + s.text;
      pop.hidden = false;
      clearTimeout(mqPopTimer);
      mqPopTimer = setTimeout(() => { document.querySelectorAll(".mq-pop").forEach((p) => { p.hidden = true; }); }, 8000);
    } else if (s.event === "game") {
      const tick = box.querySelector(".mq-ticker"), span = tick.firstChild;
      span.style.animation = "none";
      span.textContent = s.text;
      span.style.setProperty("--time", Math.max(8, Math.min(40, s.text.length * 0.35)) + "s");
      tick.hidden = false;
      void span.offsetWidth;
      span.style.animation = "";
      span.onanimationend = () => { tick.hidden = true; };
    }
  });
}

async function mqPoll() {
  if (!mq.on) return;
  try {
    const res = await api("/api/marquee/state");
    const data = await res.json();
    if (!data.enabled && !mqTried) {
      // Sem marquee_overlay o fliperos-pixelcade nao grava o placar: liga uma vez.
      mqTried = true;
      await api("/api/settings", { method: "POST", body: JSON.stringify({ key: "marquee_overlay", value: "on" }) });
    }
    const first = mqLastTime === null;
    mqState = data.state || {};
    mqLive = data.live && data.live.rom ? data.live : null;
    mqHi = Array.isArray(data.hi) ? data.hi : [];
    mqDrawHiList();
    mqFresh = !first && mqState.time !== mqLastTime;
    mqEvents(mqState, first);
    document.querySelectorAll(".mq-led").forEach((box) => { if (!box.hidden && box.firstChild) mqDrawState(box); });
  } catch (e) { /* o gabinete desligado: fica o que estava */ }
}
let mqTimer = null;
function mqWatch() {
  clearInterval(mqTimer);
  mqTimer = mq.on ? setInterval(mqPoll, 1000) : null;
  if (mq.on) mqPoll();
}

// A imagem do jogo para o dispositivo, tentando uma arte depois da outra e,
// sem nenhuma, o nome em texto.
function mqShow(box, urls, title, sub) {
  const img = box.querySelector("img"), name = box.querySelector(".mq-name");
  name.replaceChildren(el("b", {}, title), sub ? el("small", {}, sub) : "");
  name.classList.toggle("long", title.length > 18);
  let n = 0;
  const next = () => {
    if (n >= urls.length) { img.hidden = true; img.removeAttribute("src"); name.hidden = false; box.classList.remove("logo"); return; }
    const u = urls[n++];
    img.onload = () => { img.hidden = false; name.hidden = true; box.classList.toggle("logo", u.logo); };
    img.onerror = next;
    img.src = u.url;
  };
  next();
}

let mqKey = "", mqStarted = false;
function mqPaint(game) {
  document.documentElement.classList.toggle("mq-on", mq.on);
  // O placar so e pedido depois do login (o primeiro status chega aqui).
  if (!mqStarted) { mqStarted = true; mqWatch(); if (mq.on) mqCheckInstall(false); }
  const front = typeof cabFront !== "undefined" && cabFront ? cabFront.program : "";
  const key = [mq.on, mq.device, lang, game ? game.system + "/" + game.name + "/" + (game.art || "") : "-", front].join("|");
  if (key === mqKey) return;
  mqKey = key;
  mqControls();
  const dev = MQ_DEVICES[mq.device];
  const marquee = $("cab-marquee");
  if (marquee) marquee.classList.toggle("mq-on", mq.on);
  const title = game ? (game.title || game.name || game.file || game.program || "") : front ? frontName(front) : "FliperOS";
  const sub = game ? [game.manufacturer, game.year].filter(Boolean).join(" · ") : "";
  const urls = game && game.art ? dev.art.filter((l) => game.art.includes(l)).map((l) => ({ url: mediaUrl(game.system, game.name, MQ_KINDS[l]), logo: l === "l" })) : [];
  // Sem jogo, no frontend do FliperOS (ou em nenhum): o logotipo animado
  // (tools/marquee-logo-anim.py) no lugar do nome em texto, que fica de reserva.
  if (!game && (!front || front === "fliperos-frontend")) urls.push({ url: "marquee-fliperos.gif", logo: false });
  document.querySelectorAll(".mq-led").forEach((box) => {
    box.hidden = !mq.on;
    if (!mq.on) return;
    mqBuild(box);
    box.dataset.device = mq.device;
    box.style.setProperty("--cols", String(dev.cols));
    box.querySelector(".mq-tag").textContent = dev.name + " " + dev.size;
    mqShow(box, urls, title.replace(/\s*\(.*$/, "").toUpperCase(), sub.toUpperCase());
    // O jogo abriu ou fechou: o logotipo e a animacao na hora, sem esperar o proximo estado.
    mqDrawState(box);
  });
}

// Os controles do cartao (no Frontend).
function mqControls() {
  $("mq-on").checked = mq.on;
  $("mq-device").value = mq.device;
  $("mq-device").disabled = !mq.on;
  $("mq-art").textContent = t("mq_art_" + mq.device);
  document.querySelectorAll(".mq-show button").forEach((b) => b.classList.toggle("on", b.dataset.show === mq.show));
}
// Arte ou placar (no cartao do Frontend): o texto e a conquista que
// estavam rolando saem, e o placar volta ou some na hora.
document.querySelectorAll(".mq-show button").forEach((b) => b.addEventListener("click", () => {
  mq.show = b.dataset.show;
  mqSave();
  mqControls();
  if (mq.show !== "score") document.querySelectorAll(".mq-ticker, .mq-pop").forEach((n) => { n.hidden = true; });
  mqPoll();
}));
function mqChanged() {
  const was = { on: mq.on, device: mq.device };
  mq.on = $("mq-on").checked;
  mq.device = MQ_DEVICES[$("mq-device").value] ? $("mq-device").value : "pixelcade";
  mqSave();
  mqControls();
  mqKey = "";
  mqPaint(cabOnline ? cabGame : null);
  mqWatch();
  // Ligou ou trocou o dispositivo: ele esta instalado? Se nao, pergunta.
  if (mq.on && (!was.on || was.device !== mq.device)) mqCheckInstall(true);
}

// ── O dispositivo esta instalado? ────────────────────────────────
// Pixelcade e ZeDMD sao "extras" da pagina Install (/api/install). A previa
// funciona sem eles, mas o display de verdade precisa: ao ligar o modo ou
// trocar o dispositivo, se falta, um dialogo oferece instalar (a tarefa vai
// para a gaveta de tarefas, como na pagina Install).
let mqInstTimer = null;

function mqInstNote(row) {
  const name = MQ_DEVICES[mq.device].name;
  $("mq-inst").textContent = t(row.installed ? "mq_inst_ok" : "mq_inst_no_note").replace("%s", name);
  $("mq-inst-go").hidden = row.installed;
}

async function mqCheckInstall(offer) {
  const device = mq.device;
  let row = null;
  try {
    row = ((await (await api("/api/install")).json()).extras || []).find((e) => e.name === device);
  } catch (e) { return; }
  if (!row || device !== mq.device) return;
  mqInstNote(row);
  if (row.installed || !offer) return;
  const yes = await ask({ title: t("mq_inst_title").replace("%s", MQ_DEVICES[device].name),
    text: t("mq_inst_text").replace("%s", MQ_DEVICES[device].name), yes: t("mq_inst_yes"), no: t("mq_inst_no") });
  if (yes) mqInstall(device);
}

async function mqInstall(device) {
  await startTask("/api/install", { group: "extras", name: device });
  $("mq-inst").textContent = t("mq_inst_busy").replace("%s", MQ_DEVICES[device].name);
  $("mq-inst-go").hidden = true;
  // Quando a tarefa termina o aviso vira "instalado" (confere a cada 5 s).
  clearInterval(mqInstTimer);
  let tries = 0;
  mqInstTimer = setInterval(async () => {
    if (++tries > 120 || device !== mq.device) { clearInterval(mqInstTimer); return; }
    try {
      const row = ((await (await api("/api/install")).json()).extras || []).find((e) => e.name === device);
      if (row && row.installed) { mqInstNote(row); clearInterval(mqInstTimer); }
    } catch (e) { /* o gabinete reiniciando */ }
  }, 5000);
}
$("mq-inst-go").addEventListener("click", () => mqInstall(mq.device));
$("mq-on").addEventListener("change", mqChanged);
$("mq-device").addEventListener("change", mqChanged);
mqControls();
