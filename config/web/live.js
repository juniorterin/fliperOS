// A tela ao vivo para o OBS (live.html): a mesma conexao WebRTC do painel,
// pela chave do endereco (/api/overlay/offer), sem login. Fica aberta: se a
// conexao cai (o gabinete reiniciou, o jogo trocou de resolucao), conecta de
// novo sozinha.
"use strict";

const params = new URLSearchParams(location.search);
const key = params.get("key") || "";
const fps = [15, 30, 60].includes(Number(params.get("fps"))) ? Number(params.get("fps")) : 60;
if (params.get("fit") === "fill") document.documentElement.classList.add("fill");
const video = document.getElementById("video");
video.muted = params.get("muted") === "1";
let pc = null, retry = null;

// Cada quadro do video copiado para o canvas do mesmo tamanho (640x480), que a
// pagina aumenta sem suavizar: o <video> o Chrome sempre suaviza.
function pixels(video, canvas) {
  const ctx = canvas.getContext("2d", { alpha: false });
  const next = () => video.requestVideoFrameCallback ? video.requestVideoFrameCallback(draw) : requestAnimationFrame(draw);
  const draw = () => {
    const w = video.videoWidth, h = video.videoHeight;
    canvas.hidden = !w;
    if (w) {
      if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
      ctx.drawImage(video, 0, 0, w, h);
    }
    next();
  };
  next();
}
pixels(video, document.getElementById("pixels"));

function note(text, bad) {
  const p = document.getElementById("note");
  p.hidden = !text;
  p.textContent = text || "";
  p.classList.toggle("bad", !!bad);
}

function again(text) {
  if (pc) pc.close();
  pc = null;
  note(text, true);
  clearTimeout(retry);
  retry = setTimeout(connect, 3000);
}

async function connect() {
  note("FliperOS: connecting…");
  const conn = new RTCPeerConnection({ iceServers: [] });
  pc = conn;
  const stream = new MediaStream();
  conn.addTransceiver("video", { direction: "recvonly" });
  conn.addTransceiver("audio", { direction: "recvonly" });
  conn.ontrack = (ev) => {
    stream.addTrack(ev.track);
    video.srcObject = stream;
    // Fora do OBS o navegador pode recusar som sem um clique: mudo, entao.
    video.play().catch(() => { video.muted = true; video.play().catch(() => {}); });
  };
  conn.onconnectionstatechange = () => {
    if (pc !== conn) return;
    if (conn.connectionState === "connected") note("");
    if (conn.connectionState === "failed" || conn.connectionState === "disconnected") again("FliperOS: reconnecting…");
  };
  try {
    await conn.setLocalDescription(await conn.createOffer());
    await new Promise((resolve) => {
      if (conn.iceGatheringState === "complete") return resolve();
      const timer = setTimeout(resolve, 2000);
      conn.addEventListener("icegatheringstatechange", () => {
        if (conn.iceGatheringState === "complete") { clearTimeout(timer); resolve(); }
      });
    });
    const res = await fetch("/api/overlay/offer?key=" + encodeURIComponent(key), {
      method: "POST", headers: { "Content-Type": "application/json", "X-FliperOS": "1" },
      body: JSON.stringify({ fps, sdp: conn.localDescription.sdp }),
    });
    if (res.status === 403) {
      if (pc === conn) { conn.close(); pc = null; }
      note("FliperOS: wrong live address (copy it again from the web panel).", true);
      return;
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    if (pc === conn) await conn.setRemoteDescription({ type: "answer", sdp: data.sdp });
  } catch (e) {
    if (pc === conn) again("FliperOS: " + (e.message || e) + " (trying again)");
  }
}

connect();
