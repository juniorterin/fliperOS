// Ao vivo: a tela do gabinete (WebRTC) e os enderecos para o OBS.
"use strict";

// ── Ao vivo: a tela do gabinete (WebRTC) ─────────────────────────
// O go2rtc do gabinete (config/fliperos-stream) manda o que esta no tubo em
// H.264 (e o som em Opus, se ligado). A oferta vai pelo painel
// (/api/stream/offer); o video chega direto, pela rede local. Sem STUN: as
// duas pontas estao na mesma rede. O som comeca mudo (o navegador so toca
// som depois de um clique). Sair da pagina para a transmissao: o ffmpeg do
// gabinete so roda enquanto alguem assiste.

let live = null, liveStats = null, liveStatus = null, liveObsPath = "", liveError = "", liveNoVaapi = false;

// O endereco da tela para o OBS, montado pelas escolhas do cartao: quadros,
// formato (4:3 como no tubo ou esticado), som; o tamanho e o que digitar no
// OBS. As escolhas ficam no navegador.
const OBS_OPTS = ["obs-fps", "obs-fit", "obs-size", "obs-sound", "ovl-led", "ovl-text", "ovl-size", "pad-players", "pad-demo"];

function obsSaved() {
  try {
    const saved = JSON.parse(localStorage.getItem("fliperos-obs") || "{}");
    for (const id of OBS_OPTS) {
      if (!(id in saved)) continue;
      if ($(id).type === "checkbox") $(id).checked = !!saved[id]; else $(id).value = saved[id];
    }
  } catch (e) { /* sem armazenamento */ }
}

function obsSave() {
  const saved = {};
  for (const id of OBS_OPTS) saved[id] = $(id).type === "checkbox" ? $(id).checked : $(id).value;
  try { localStorage.setItem("fliperos-obs", JSON.stringify(saved)); } catch (e) { /* sem armazenamento */ }
}

function sizeText(value) {
  const [w, h] = value.split("x");
  return t("obs_wh").replace("%w", w).replace("%h", h);
}

function liveObsUrl() {
  $("obs-wh").textContent = sizeText($("obs-size").value);
  if (!liveObsPath) return;
  let url = location.origin + liveObsPath + "&fps=" + $("obs-fps").value;
  if ($("obs-fit").value) url += "&fit=" + $("obs-fit").value;
  if (!$("obs-sound").checked) url += "&muted=1";
  $("live-url").value = url;
  $("live-open").href = url;
}

function liveFact(id, text, cls) {
  const dd = $(id);
  dd.textContent = text;
  dd.className = cls || "";
}

function liveIdle() {
  // O palco sem video: o que falta para assistir, ou o botao grande.
  const s = liveStatus || {};
  const ready = s.installed && s.active;
  $("live-idle").hidden = !!live;
  $("live-play").hidden = !ready;
  // Depois de uma tentativa que falhou, o porque fica no palco ate a proxima.
  $("live-idle-text").textContent = !s.installed ? t("live_not_installed") : !s.active ? t("live_off_note")
    : liveError || t("live_ready").replace("%e", s.encoder === "vaapi" ? t("live_hw") : "x264");
  $("live-idle").classList.toggle("bad", !!liveError && !live);
  $("live-start").hidden = !!live || !ready;
}

async function loadLive() {
  const res = await api("/api/stream");
  liveStatus = await res.json();
  const s = liveStatus, setup = $("live-setup");
  liveFact("live-service", !s.installed ? t("live_absent") : s.active ? t("live_running") : t("live_stopped"),
    s.installed && s.active ? "on" : "off");
  liveFact("live-encoder", !s.installed ? "-" : s.encoder === "vaapi" ? t("live_enc_hw") : t("live_enc_sw"));
  liveFact("live-audio", s.audio ? t("live_audio_on") : t("live_audio_off"), s.audio ? "on" : "off");
  // A rede da rota padrao: no Wi-Fi a recomendacao do cabo em destaque.
  liveFact("live-net", s.link === "wifi" ? t("live_net_wifi") : s.link === "wired" ? t("live_net_wired") : "-",
    s.link === "wifi" ? "off" : s.link === "wired" ? "on" : "");
  $("live-net-tip").textContent = t(s.link === "wifi" ? "live_net_tip_wifi" : "live_net_tip");
  $("live-net-tip").classList.toggle("warn", s.link === "wifi");
  setup.replaceChildren();
  // Sem o VA-API que a placa pede, instalar de novo o traz (fliperos-extras).
  if (!s.installed || liveNoVaapi) {
    const install = el("button", { type: "button", class: "btn small" }, icon("g-tasks"), t("live_install"));
    install.addEventListener("click", async () => {
      const r = await api("/api/stream/install", { method: "POST", body: "{}" });
      const data = await r.json().catch(() => ({}));
      toast(r.ok ? t("live_installing") : data.error || r.statusText);
    });
    setup.append(install);
  } else {
    // Ligar ou desligar o servico (Setup > System > Services > Live screen).
    const svc = el("button", { type: "button", class: s.active ? "btn ghost small" : "btn small" }, icon("g-power"),
      t(s.active ? "live_turn_off" : "live_turn_on"));
    svc.addEventListener("click", async () => {
      if (s.active) liveStop();
      await api("/api/settings", { method: "POST",
        body: JSON.stringify({ key: "service.stream", value: s.active ? "off" : "boot" }) });
      setTimeout(() => loadLive().catch(() => {}), 2500);
    });
    // O som: a copia no loopback do ALSA (Settings > Live screen sound).
    const sound = el("button", { type: "button", class: "btn ghost small" }, icon(s.audio ? "g-mute" : "g-volume"),
      t(s.audio ? "live_sound_off" : "live_sound_on"));
    sound.addEventListener("click", async () => {
      sound.disabled = true;
      const r = await api("/api/settings", { method: "POST",
        body: JSON.stringify({ key: "stream_audio", value: s.audio ? "off" : "on" }) });
      if (!r.ok) toast((await r.json().catch(() => ({}))).error || r.statusText);
      loadLive().catch(() => {});
    });
    // A qualidade (Settings > Live screen quality): a taxa e o preset do
    // codificador. Vale na proxima conexao, entao o que esta passando reconecta.
    const quality = el("select", { "aria-label": t("live_quality") },
      ...["light", "normal", "high", "max"].map((q) => el("option", { value: q }, t("live_q_" + q))));
    quality.value = s.quality || "normal";
    quality.addEventListener("change", async () => {
      quality.disabled = true;
      const r = await api("/api/settings", { method: "POST",
        body: JSON.stringify({ key: "stream_quality", value: quality.value }) });
      if (!r.ok) toast((await r.json().catch(() => ({}))).error || r.statusText);
      else if (live) liveStart();
      loadLive().catch(() => {});
    });
    setup.append(svc, sound, el("label", { class: "live-quality dim" }, t("live_quality"), quality));
  }
  // O endereco sempre a vista; sem a tela ao vivo no ar, o aviso do porque.
  const r = await api("/api/overlay");
  liveObsPath = (await r.json()).live;
  liveObsUrl();
  $("live-obs-off").hidden = s.installed && s.active;
  liveIdle();
}

function liveIce(pc) {
  // As candidatas da rede local saem em instantes; sem esperar mais que 2 s.
  if (pc.iceGatheringState === "complete") return Promise.resolve();
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, 2000);
    pc.addEventListener("icegatheringstatechange", () => {
      if (pc.iceGatheringState === "complete") { clearTimeout(timer); resolve(); }
    });
  });
}

// Uma tentativa que falhou: o motivo no palco (com o botao de tentar de
// novo) e embaixo dele.
function liveFail(text) {
  liveError = text;
  liveIdle();
  $("live-note").textContent = text;
}

async function liveStart() {
  liveStop();
  liveError = "";
  const video = $("live"), fps = Number($("live-fps").value);
  $("live-note").textContent = t("live_connecting");
  const pc = new RTCPeerConnection({ iceServers: [] });
  live = pc;
  liveIdle();
  $("live-idle-text").textContent = t("live_connecting");
  $("live-idle").hidden = false;
  $("live-play").hidden = true;
  const stream = new MediaStream();
  pc.addTransceiver("video", { direction: "recvonly" });
  pc.addTransceiver("audio", { direction: "recvonly" });
  // Com som desde o comeco (o Assistir e um clique, o navegador deixa); se o
  // navegador recusar mesmo assim, comeca mudo e o botao mostra.
  video.muted = false;
  liveMuteButton();
  // O stream vai ao <video> uma vez so: dar o srcObject de novo na faixa do
  // som interrompia o play (AbortError), e o video ficava mudo sem motivo.
  video.srcObject = stream;
  pc.ontrack = (ev) => {
    stream.addTrack(ev.track);
    video.play().catch((e) => {
      if (e.name !== "NotAllowedError" || video.muted) return;
      video.muted = true;
      liveMuteButton();
      video.play().catch(() => {});
    });
    if (ev.track.kind === "audio") $("live-sound").hidden = false;
  };
  video.onplaying = () => { if (live === pc) $("live-idle").hidden = true; };
  pc.onconnectionstatechange = () => {
    if (live !== pc) return;
    if (pc.connectionState === "failed" || pc.connectionState === "disconnected") {
      liveStop(true);
      liveFail(t("live_lost"));
    }
  };
  // O painel responde em ate uns 25 s (o go2rtc desiste em 20); sem resposta
  // ate 35 s, desiste daqui.
  const abort = new AbortController(), timer = setTimeout(() => abort.abort(), 35000);
  try {
    await pc.setLocalDescription(await pc.createOffer());
    await liveIce(pc);
    const res = await api("/api/stream/offer", { method: "POST", signal: abort.signal,
      body: JSON.stringify({ fps, sdp: pc.localDescription.sdp }) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      if (data.code === "no_vaapi") { liveNoVaapi = true; loadLive().catch(() => {}); }
      throw new Error(data.code === "no_vaapi" ? t("live_err_vaapi")
        : data.code === "capture" ? t("live_err_capture").replace("%s", data.error.replace(/^.*?: /, ""))
          : data.code === "go2rtc" ? t("live_err_go2rtc") : data.error || res.statusText);
    }
    if (live !== pc) return;
    await pc.setRemoteDescription({ type: "answer", sdp: data.sdp });
  } catch (e) {
    if (live === pc) liveStop(true);
    if (e.message !== "login" && live === null) liveFail(e.name === "AbortError" ? t("live_err_timeout") : String(e.message || e));
    return;
  } finally {
    clearTimeout(timer);
  }
  // Conectou, mas a imagem nao chega: o porque em vez de "Conectando" para sempre.
  setTimeout(() => {
    if (live === pc && !$("live-idle").hidden) {
      liveStop(true);
      liveFail(t("live_err_nopicture"));
    }
  }, 15000);
  $("live-stop").hidden = false;
  $("live-full").hidden = false;
  $("live-badge").hidden = false;
  liveStats = setInterval(() => liveShowStats(pc), 1000);
}

// O balao do atraso para o OBS: sem medida, o convite a assistir aqui.
let liveSyncSamples = [], liveSyncPrev = {};
function liveSync(video, audio) {
  const p = $("live-sync-text");
  if (video == null) {
    liveSyncSamples = [];
    delete p.dataset.measured;
    p.textContent = t("sync_idle");
    return;
  }
  p.dataset.measured = "1";
  liveSyncSamples = liveSyncSamples.concat([[video, audio]]).slice(-10);
  const mean = (i) => Math.round(liveSyncSamples.reduce((sum, s) => sum + s[i], 0) / liveSyncSamples.length / 10) * 10;
  p.innerHTML = t("sync_on").replaceAll("%v", String(mean(0))).replaceAll("%a", String(mean(1)));
}

async function liveShowStats(pc) {
  // O que chega: o tamanho, os quadros por segundo e o atraso do buffer.
  if (live !== pc) return;
  let text = "", video = null, audio = null, rtt = 0;
  const fps = Number($("live-fps").value);
  // O atraso do ultimo segundo (a diferenca entre duas leituras): a media da
  // sessao toda carregava o comeco, quando o Chrome ainda acerta a sincronia
  // da imagem com o som.
  const prev = liveSyncPrev.pc === pc ? liveSyncPrev : {};
  const now = { pc };
  const recent = (key, sum, n) => {
    now[key] = [sum, n];
    const [sum0, n0] = prev[key] || [0, 0];
    return n > n0 ? (1000 * (sum - sum0)) / (n - n0) : null;
  };
  const stats = await pc.getStats();
  stats.forEach((s) => {
    if (s.type === "inbound-rtp" && s.kind === "video") {
      const delay = s.jitterBufferEmittedCount ? Math.round((1000 * s.jitterBufferDelay) / s.jitterBufferEmittedCount) : null;
      text = (s.frameWidth ? s.frameWidth + "×" + s.frameHeight + " · " : "") + Math.round(s.framesPerSecond || 0) + " fps"
        + (delay != null ? " · " + t("live_buffer").replace("%n", delay) : "");
      const buffer = recent("vjb", s.jitterBufferDelay || 0, s.jitterBufferEmittedCount || 0);
      const decode = recent("vdec", s.totalDecodeTime || 0, s.framesDecoded || 0);
      if (buffer != null) video = buffer + (decode || 0);
    }
    if (s.type === "inbound-rtp" && s.kind === "audio") {
      audio = recent("ajb", s.jitterBufferDelay || 0, s.jitterBufferEmittedCount || 0);
    }
    if (s.type === "candidate-pair" && s.nominated && s.currentRoundTripTime) rtt = s.currentRoundTripTime * 1000;
  });
  liveSyncPrev = now;
  if (text) $("live-note").textContent = text;
  // O atraso todo: o do navegador (buffer e decodificacao), meia volta da
  // rede e o do gabinete. A imagem: a captura e o x264 sem quadros B, uns 2
  // quadros. O som: o periodo do loopback (1024 amostras a 48 kHz, 21 ms) e o
  // quadro do Opus (10 ms).
  if (video != null) {
    const v = video + rtt / 2 + 2000 / fps;
    liveSync(v, audio != null ? audio + rtt / 2 + 31 : v);
  }
}

function liveStop(keepNote) {
  if (liveStats) clearInterval(liveStats);
  liveStats = null;
  if (live) live.close();
  live = null;
  const video = $("live");
  video.srcObject = null;
  video.muted = true;
  $("live-pixels").hidden = true;
  liveSync(null);
  $("live-sound").hidden = true;
  $("live-sound").replaceChildren(icon("g-mute"), t("live_unmute"));
  $("live-stop").hidden = true;
  $("live-full").hidden = true;
  $("live-badge").hidden = true;
  if (!keepNote) $("live-note").textContent = "";
  liveIdle();
}

// Os pixels nitidos: cada quadro do video (640x480) copiado no canvas por
// cima, que a pagina aumenta sem suavizar (o Chrome sempre suaviza o <video>).
(() => {
  const video = $("live"), canvas = $("live-pixels"), ctx = canvas.getContext("2d", { alpha: false });
  const next = () => video.requestVideoFrameCallback ? video.requestVideoFrameCallback(draw) : requestAnimationFrame(draw);
  const draw = () => {
    const w = video.videoWidth, h = video.videoHeight;
    if (w && live) {
      if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
      ctx.drawImage(video, 0, 0, w, h);
      canvas.hidden = false;
    }
    next();
  };
  next();
})();

$("live-start").addEventListener("click", () => liveStart());
$("live-play").addEventListener("click", () => liveStart());
$("live-stop").addEventListener("click", () => liveStop());
$("live-fps").addEventListener("change", () => { if (live) liveStart(); });
obsSaved();
for (const id of ["obs-fps", "obs-fit", "obs-size", "obs-sound"]) {
  $(id).addEventListener("change", () => { obsSave(); liveObsUrl(); });
}
for (const id of ["ovl-led", "ovl-text", "ovl-size"]) {
  $(id).addEventListener("change", () => { obsSave(); overlayUrl(); });
}
$("live-tube").addEventListener("change", () => $("live-stage").classList.toggle("tube", $("live-tube").checked));
// O botao do som mostra o que um clique faz (mudo: "Ligar o som").
function liveMuteButton() {
  const muted = $("live").muted;
  $("live-sound").replaceChildren(icon(muted ? "g-mute" : "g-volume"), t(muted ? "live_unmute" : "live_mute"));
}

// Os quadros por segundo em botoes (o select escondido continua sendo o valor).
function liveFpsPick() {
  const box = $("live-fps-pick"), select = $("live-fps");
  box.replaceChildren(...[...select.options].map((o) => {
    const b = el("button", { type: "button", class: o.value === select.value ? "on" : "" }, o.value, el("small", {}, "FPS"));
    b.addEventListener("click", () => {
      select.value = o.value;
      select.dispatchEvent(new Event("change"));
      liveFpsPick();
    });
    return b;
  }));
}
liveFpsPick();

// O OBS: uma pagina por vez (a tela, o letreiro ou o controle), lembrada.
function obsPick(name) {
  try { name = name || localStorage.getItem("fliperos-obs-pick") || "screen"; } catch (e) { name = name || "screen"; }
  document.querySelectorAll(".obs-pick [data-obs]").forEach((b) => {
    b.classList.toggle("on", b.dataset.obs === name);
    b.setAttribute("aria-selected", String(b.dataset.obs === name));
  });
  document.querySelectorAll(".obs-panel[data-obs]").forEach((p) => { p.hidden = p.dataset.obs !== name; });
  try { localStorage.setItem("fliperos-obs-pick", name); } catch (e) { /* sem armazenamento */ }
}
document.querySelectorAll(".obs-pick [data-obs]").forEach((b) => b.addEventListener("click", () => obsPick(b.dataset.obs)));
obsPick();

$("live-sound").addEventListener("click", () => {
  $("live").muted = !$("live").muted;
  liveMuteButton();
});
// A tela cheia: a do palco; no iPhone so o <video> vai a tela cheia (o
// player do sistema, em 4:3 como o quadro de 640x480).
$("live-full").addEventListener("click", () => {
  const stage = $("live-stage"), video = $("live");
  const full = stage.requestFullscreen || stage.webkitRequestFullscreen;
  if (full) Promise.resolve(full.call(stage)).catch(() => {});
  else if (video.webkitEnterFullscreen) video.webkitEnterFullscreen();
});
$("live-copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("live-url").value); } catch (e) {
    $("live-url").select();
    document.execCommand("copy");
  }
  toast(t("copied"));
});

// ── Marquee para o OBS ───────────────────────────────────────────
// Ligado aqui (ou no Setup), o marquee do jogo na tela vira uma pagina
// (/overlay/marquee) para o Browser Source do OBS: fundo transparente, a
// arte do jogo, os recordes, as conquistas e o placar versus. O endereco
// tem uma chave (o OBS nao faz login); uma chave nova invalida a antiga.

async function loadOverlay() {
  const res = await api("/api/overlay");
  showOverlay(await res.json());
}

let ovlData = null;

function showOverlay(data) {
  ovlData = data;
  $("ovl-on").checked = !!data.enabled;
  $("ovl-box").hidden = !data.enabled;
  overlayUrl();
  padUrl();
}

// O endereco do marquee com as escolhas (os pontos de LED, os textos); a
// previa segue o mesmo endereco.
function overlayUrl() {
  $("ovl-wh").textContent = sizeText($("ovl-size").value);
  if (!ovlData) return;
  let url = location.origin + ovlData.path;
  if ($("ovl-led").checked) url += "&led=1";
  if (!$("ovl-text").checked) url += "&text=0";
  $("ovl-url").value = url;
  $("ovl-open").href = url;
  const preview = $("ovl-preview");
  if (ovlData.enabled && preview.dataset.src !== url) {
    preview.src = url;
    preview.dataset.src = url;
  } else if (!ovlData.enabled && preview.dataset.src) {
    preview.removeAttribute("src");
    delete preview.dataset.src;
  }
}

$("ovl-on").addEventListener("change", async () => {
  const value = $("ovl-on").checked ? "on" : "off";
  const res = await api("/api/settings", { method: "POST", body: JSON.stringify({ key: "marquee_overlay", value }) });
  if (!res.ok) toast((await res.json().catch(() => ({}))).error || res.statusText);
  loadOverlay().catch(() => {});
});
$("ovl-copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("ovl-url").value); toast(t("copied")); } catch (e) {
    $("ovl-url").select();
    document.execCommand("copy");
    toast(t("copied"));
  }
});
$("ovl-new").addEventListener("click", async () => {
  if (!confirm(t("overlay_new_ask"))) return;
  const res = await api("/api/overlay", { method: "POST", body: JSON.stringify({ action: "newkey" }) });
  const data = await res.json();
  showOverlay(data);
  liveObsPath = data.live || liveObsPath;
  liveObsUrl();
});

// ── O controle para o OBS ────────────────────────────────────────
// /overlay/input: o direcional e os botoes do jogador acesos enquanto ele
// aperta (os controles do Button mapping), com a mesma chave do marquee. O
// CSS da pagina se escreve aqui: a previa troca o <style> dela a cada tecla,
// e Salvar o grava no gabinete (o OBS o pega ao recarregar a fonte).

const padOn = { css: "", saved: "", custom: false, defaultCss: "" };

function padUrl() {
  const players = $("pad-players").value;
  $("pad-wh").textContent = sizeText(players.includes(",") ? "1600x400" : "800x400");
  if (!ovlData || !ovlData.input) return;
  const url = location.origin + ovlData.input + (players !== "1" ? "&players=" + players : "");
  $("pad-url").value = url;
  $("pad-open").href = url;
  // A pagina aberta, nao o #: o painel tambem abre na ultima pagina usada,
  // sem # no endereco, e ai a previa nao carregava.
  if (page === "live") padPreview(true);
}

// A previa: o mesmo endereco, com o CSS do editor; com Demonstracao, aperta
// sozinho (sem ela, abre os comandos do gabinete, como o OBS).
function padPreview(on) {
  const frame = $("pad-preview");
  frame.classList.toggle("wide", $("pad-players").value.includes(","));
  const src = on && $("pad-url").value ? $("pad-url").value + "&preview=1" + ($("pad-demo").checked ? "&demo=1" : "") : "";
  if (frame.dataset.src === src) return;
  frame.dataset.src = src;
  if (src) frame.src = src; else frame.removeAttribute("src");
}

function padApply() {
  try {
    const style = $("pad-preview").contentDocument.getElementById("style");
    if (style) style.textContent = $("pad-css").value;
  } catch (e) { /* a previa ainda carregando */ }
}

async function loadPadStyle() {
  const res = await api("/api/overlay/input/style");
  const data = await res.json();
  padOn.saved = data.css;
  padOn.custom = data.custom;
  padOn.defaultCss = data.default;
  // O que esta sendo escrito e nao foi salvo fica.
  if ($("pad-css").value === padOn.css || !$("pad-css").value) padSet(data.css);
  padState();
}

function padSet(css) {
  padOn.css = css;
  $("pad-css").value = css;
  padHighlight();
  padApply();
}

function padState() {
  const changed = $("pad-css").value !== padOn.saved;
  $("pad-css-state").textContent = t(changed ? "pad_css_changed" : padOn.custom ? "pad_css_custom" : "pad_css_default");
  $("pad-css-save").disabled = !changed;
  $("pad-css-reset").disabled = !padOn.custom && !changed;
}

// O realce do CSS: comentarios, seletores, propriedades, valores, numeros,
// cores, @regras e textos. Um nome antes de "{" e seletor; dentro do bloco,
// antes de ":" e propriedade, depois e valor.
function cssTokens(text) {
  const re = /(\/\*[\s\S]*?(?:\*\/|$))|("(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?)|(@[\w-]+)|(#[0-9a-fA-F]{3,8}\b)|(-?(?:\d+\.?\d*|\.\d+)(?:[a-zA-Z%]+)?)|([\w-]+(?=\())|([{}:;,()])|([^\s{}:;,()"'/@#]+|[/@#])|(\s+)/g;
  // Do ponto dado, o proximo "{" vem antes de um ";" ou "}"?
  const block = /[^;{}]*\{/y;
  const opensBlock = (at) => { block.lastIndex = at; return block.test(text); };
  const out = [];
  let depth = 0, value = false, m;
  while ((m = re.exec(text))) {
    const [tok, comment, str, at, hex, num, fn, punct] = m;
    let cls = "";
    if (comment) cls = "c";
    else if (str) cls = "q";
    else if (at) cls = "a";
    else if (punct) {
      cls = "x";
      if (tok === "{") { depth++; value = false; }
      else if (tok === "}") { depth = Math.max(0, depth - 1); value = false; }
      else if (tok === ";") value = false;
      else if (tok === ":" && depth > 0 && !value && !opensBlock(re.lastIndex)) value = true;
      else if (tok === ":" && !value) cls = "s";
    } else if (m[9]) cls = "";
    else if (value) cls = hex ? "h" : num ? "n" : fn ? "f" : "";
    else if (depth === 0 || opensBlock(m.index)) cls = "s";
    else cls = "p";
    out.push([cls, tok]);
  }
  return out;
}

// Formatar: uma propriedade por linha, dois espacos por nivel, uma linha
// em branco entre as regras e cada seletor de uma lista na sua linha. Os
// comentarios e os textos ficam como estao (os tokens do realce).
function cssFormat(text) {
  const toks = cssTokens(text).map(([, tok]) => tok);
  // nextOf[i]: o primeiro "{", ";" ou "}" depois do token i.
  const nextOf = new Array(toks.length + 1).fill("");
  for (let i = toks.length - 1; i >= 0; i--) {
    const t = toks[i + 1];
    nextOf[i] = t === "{" || t === ";" || t === "}" ? t : nextOf[i + 1];
  }
  let out = "", depth = 0, paren = 0, gap = "";
  const pad = () => "  ".repeat(depth);
  const line = () => { out = out.replace(/[ \t]+$/, ""); if (out && !out.endsWith("\n")) out += "\n"; };
  const fresh = () => out === "" || out.endsWith("\n");
  for (let i = 0; i < toks.length; i++) {
    const tok = toks[i];
    if (/^\s+$/.test(tok)) {
      gap = tok;
      // A linha em branco do original entre as regras fica.
      if (fresh() && out && depth === 0 && (tok.match(/\n/g) || []).length >= 2 && !out.endsWith("\n\n")) out += "\n";
      if (!fresh() && !out.endsWith(" ")) out += " ";
      continue;
    }
    const before = gap;
    gap = "";
    if (tok.startsWith("/*")) {
      if (fresh() && out && !before.includes("\n")) {
        // Depois do codigo na mesma linha: continua no fim dela.
        const breaks = out.match(/\n*$/)[0];
        out = out.slice(0, out.length - breaks.length) + "  " + tok + breaks;
      } else if (fresh()) {
        out += pad() + tok + "\n";
      } else {
        // No meio de um valor: fica ali.
        out = out.replace(/\s+$/, "") + " " + tok;
      }
      continue;
    }
    if (tok === "(") paren++;
    if (tok === ")") paren = Math.max(0, paren - 1);
    if (tok === "{") {
      out = out.replace(/\s+$/, "") + " {\n";
      depth++;
    } else if (tok === "}") {
      // A ultima declaracao sem ";" ganha o seu.
      const last = out.replace(/\s+$/, "");
      if (!/[;{}]$/.test(last) && !last.endsWith("*/") && !fresh()) out = last + ";";
      line();
      depth = Math.max(0, depth - 1);
      out += pad() + "}\n";
      if (depth === 0) out += "\n";
    } else if (tok === ";" && paren === 0) {
      out = out.replace(/\s+$/, "") + ";\n";
    } else if (tok === "," && depth === 0 && paren === 0) {
      out = out.replace(/\s+$/, "") + ",\n";
    } else {
      if (fresh()) out += pad();
      // O proximo { ; ou }: um "{" antes e seletor (a:hover num @media).
      if (tok === ":" && depth > 0 && paren === 0 && nextOf[i] !== "{") {
        // A propriedade: "nome: valor".
        out = out.replace(/\s+$/, "") + ":";
        if (toks[i + 1] && !/^\s/.test(toks[i + 1])) out += " ";
        continue;
      }
      out += tok;
    }
  }
  return out.replace(/\n{3,}/g, "\n\n").trim() + "\n";
}

function padHighlight() {
  const pre = $("pad-css-hl");
  pre.replaceChildren(...cssTokens($("pad-css").value).map(([cls, tok]) => cls ? el("span", { class: cls }, tok) : document.createTextNode(tok)),
    // A ultima linha vazia do textarea tambem ocupa altura no <pre>.
    document.createTextNode("\n "));
  pre.scrollTop = $("pad-css").scrollTop;
  pre.scrollLeft = $("pad-css").scrollLeft;
}

let padTimer = null;
$("pad-css").addEventListener("input", () => {
  padHighlight();
  padState();
  clearTimeout(padTimer);
  padTimer = setTimeout(padApply, 120);
});
$("pad-css").addEventListener("scroll", () => {
  $("pad-css-hl").scrollTop = $("pad-css").scrollTop;
  $("pad-css-hl").scrollLeft = $("pad-css").scrollLeft;
});
// Tab recua dois espacos em vez de sair do campo (Esc e depois Tab sai).
let padEsc = false;
$("pad-css").addEventListener("keydown", (ev) => {
  if (ev.key === "Escape") { padEsc = true; return; }
  if (ev.key !== "Tab" || padEsc || ev.ctrlKey || ev.altKey || ev.metaKey) { padEsc = false; return; }
  ev.preventDefault();
  const area = $("pad-css"), start = area.selectionStart, end = area.selectionEnd;
  if (ev.shiftKey) {
    const lineStart = area.value.lastIndexOf("\n", start - 1) + 1;
    if (area.value.startsWith("  ", lineStart)) {
      area.setRangeText("", lineStart, lineStart + 2, "preserve");
    }
  } else {
    area.setRangeText("  ", start, end, "end");
  }
  area.dispatchEvent(new Event("input"));
});
$("pad-preview").addEventListener("load", padApply);
$("pad-players").addEventListener("change", () => { obsSave(); padUrl(); });
$("pad-demo").addEventListener("change", () => { obsSave(); padPreview(true); });
$("pad-copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("pad-url").value); } catch (e) {
    $("pad-url").select();
    document.execCommand("copy");
  }
  toast(t("copied"));
});
async function padSave(body) {
  const res = await api("/api/overlay/input/style", { method: "POST", body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return toast(data.error || res.statusText);
  padOn.saved = data.css;
  padOn.custom = data.custom;
  padSet(data.css);
  padState();
  toast(t("pad_css_saved"));
}
$("pad-css-save").addEventListener("click", () => padSave({ css: $("pad-css").value }));
// Formatar entra no historico do campo (Ctrl+Z desfaz).
$("pad-css-format").addEventListener("click", () => {
  const area = $("pad-css"), css = cssFormat(area.value);
  if (css === area.value) return;
  area.focus();
  area.select();
  if (!document.execCommand("insertText", false, css)) area.value = css;
  area.setSelectionRange(0, 0);
  area.scrollTop = 0;
  area.dispatchEvent(new Event("input"));
});
$("pad-css-reset").addEventListener("click", () => {
  if (confirm(t("pad_css_reset_ask"))) padSave({ reset: true });
});
