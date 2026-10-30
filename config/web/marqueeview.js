// A previa do marquee: no Status liga-se um modo (Pixelcade ou ZeDMD) e o
// painel mostra, no Status, no Ao vivo, na previa do marquee para o OBS e no
// letreiro do gabinete desenhado, o que aquele painel de LED mostraria para
// o jogo aberto. A arte segue as regras de cada um: o ZeDMD usa dmd/, marquee/
// e logo/ de ~/media (config/fliperos-dmd); o Pixelcade, marquee/ e logo/.
// Sem arte, o nome do jogo (ou do frontend). A escolha fica no navegador.
"use strict";

Object.assign(TEXT.en, {
  mq_title: "Marquee preview", mq_on: "Marquee preview mode", mq_device: "Show the marquee of",
  mq_note: "Shows on this panel what the LED marquee would display for the game that is open, without the hardware: here, in Live, in the marquee preview and on the cabinet drawing.",
  mq_pixelcade: "Pixelcade (LED 128×32)", mq_zedmd: "ZeDMD (128×32, shown on 256×64)",
  mq_art_pixelcade: "Art: marquee, then logo, then the name.", mq_art_zedmd: "Art: dmd, then marquee, then logo, then the name.",
  mq_live: "Marquee as it will appear",
});
Object.assign(TEXT.pt, {
  mq_title: "Prévia do marquee", mq_on: "Modo prévia do marquee", mq_device: "Mostrar o marquee do",
  mq_note: "Mostra neste painel o que o marquee de LED exibiria para o jogo aberto, sem o hardware: aqui, no Ao vivo, na prévia do marquee e no desenho do gabinete.",
  mq_pixelcade: "Pixelcade (LED 128×32)", mq_zedmd: "ZeDMD (128×32, em painel 256×64)",
  mq_art_pixelcade: "Arte: marquee, depois logo, depois o nome.", mq_art_zedmd: "Arte: dmd, depois marquee, depois logo, depois o nome.",
  mq_live: "O marquee como vai aparecer",
});

// O que cada painel desenha: as letras de arte (campo "art" dos jogos) na
// ordem em que o dispositivo as procura, e as colunas de pontos do painel.
const MQ_DEVICES = {
  pixelcade: { name: "Pixelcade", size: "128×32", cols: 128, art: ["m", "l"] },
  zedmd: { name: "ZeDMD", size: "256×64", cols: 256, art: ["d", "m", "l"] },
};
const MQ_KINDS = { d: "dmd", m: "marquee", l: "logo" };
const MQ_STORE = "fliperos-marquee-preview";

let mq = { on: false, device: "pixelcade" };
try {
  const saved = JSON.parse(localStorage.getItem(MQ_STORE) || "null");
  if (saved) { mq.on = !!saved.on; if (MQ_DEVICES[saved.device]) mq.device = saved.device; }
} catch (e) { /* sem armazenamento */ }

function mqSave() {
  try { localStorage.setItem(MQ_STORE, JSON.stringify(mq)); } catch (e) { /* sem armazenamento */ }
}

// O painel de LED de um lugar da pagina: a imagem, o nome (sem imagem), os
// pontos por cima e o selo com o dispositivo.
function mqBuild(box) {
  if (box.firstChild) return;
  box.append(el("img", { alt: "", hidden: "" }), el("span", { class: "mq-name" }), el("i", { class: "mq-dots" }), el("small", { class: "mq-tag" }));
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

let mqKey = "";
function mqPaint(game) {
  document.documentElement.classList.toggle("mq-on", mq.on);
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
  document.querySelectorAll(".mq-led").forEach((box) => {
    box.hidden = !mq.on;
    if (!mq.on) return;
    mqBuild(box);
    box.dataset.device = mq.device;
    box.style.setProperty("--cols", String(dev.cols));
    box.querySelector(".mq-tag").textContent = dev.name + " " + dev.size;
    mqShow(box, urls, title.replace(/\s*\(.*$/, "").toUpperCase(), sub.toUpperCase());
  });
}

// Os controles do Status.
function mqControls() {
  $("mq-on").checked = mq.on;
  $("mq-device").value = mq.device;
  $("mq-device").disabled = !mq.on;
  $("mq-art").textContent = t("mq_art_" + mq.device);
}
function mqChanged() {
  mq.on = $("mq-on").checked;
  mq.device = MQ_DEVICES[$("mq-device").value] ? $("mq-device").value : "pixelcade";
  mqSave();
  mqControls();
  mqKey = "";
  mqPaint(cabOnline ? cabGame : null);
}
$("mq-on").addEventListener("change", mqChanged);
$("mq-device").addEventListener("change", mqChanged);
mqControls();
