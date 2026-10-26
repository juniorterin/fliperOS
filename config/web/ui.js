// As pecas que todas as areas do painel usam: o idioma, o DOM, os icones
// (icons.svg: os do Setup e os glifos, tools/web-icons.py), os formatos, os
// pedidos a API, os toasts, o dialogo de confirmar e a folha do jogo.
"use strict";

let lang = "en";
try {
  lang = localStorage.getItem("fliperos-lang") || (navigator.language || "").slice(0, 2);
} catch (e) {
  lang = (navigator.language || "").slice(0, 2);
}
if (!TEXT[lang]) lang = "en";
const t = (key) => TEXT[lang][key] || TEXT.en[key] || key;
const $ = (id) => document.getElementById(id);
const locale = () => (lang === "pt" ? "pt-BR" : "en");
// A area aberta (frontend, live, library, system) e o nome antigo da pagina,
// que o codigo de cada aba confere (app.js, showPage).
let area = "", page = "";
const num = (n) => Number(n).toLocaleString(locale());

function translate() {
  document.documentElement.lang = locale();
  document.querySelectorAll("[data-t]").forEach((node) => { node.textContent = t(node.dataset.t); });
  document.querySelectorAll("[data-tp]").forEach((node) => { node.placeholder = t(node.dataset.tp); });
  // Os botoes so de icone: o nome no aria-label e no balao do mouse.
  document.querySelectorAll("[data-ta]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.ta));
    node.title = t(node.dataset.ta);
  });
  $("lang").textContent = lang === "pt" ? "EN" : "PT";
  $("lang2").textContent = lang === "pt" ? "English" : "Português";
  // O balao do atraso: sem medida, o convite (com medida ele se refaz a cada segundo).
  const sync = $("live-sync-text");
  if (sync && !sync.dataset.measured) sync.textContent = t("sync_idle");
}

function el(tag, attrs, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") node.className = v; else node.setAttribute(k, v);
  }
  for (const c of children) node.append(c instanceof Node ? c : document.createTextNode(c == null ? "" : String(c)));
  return node;
}

// Um icone do sprite: "px-NOME" (os do Setup, coloridos) ou "g-NOME" (os
// glifos, na cor do texto).
function icon(name, cls) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", (name.startsWith("px-") ? "px" : "g") + (cls ? " " + cls : ""));
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", "icons.svg#" + name);
  svg.append(use);
  return svg;
}

function bytes(n) {
  if (n == null) return "-";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return (n >= 100 || i === 0 ? n.toFixed(0) : n.toFixed(1)) + " " + units[i];
}
const rate = (bps) => bytes(bps) + "/s";

function meter(pct) {
  const bar = el("div", { class: "meter" + (pct > 90 ? " hot" : pct > 70 ? " warn" : "") }, el("div"));
  bar.firstChild.style.width = Math.max(0, Math.min(100, pct || 0)) + "%";
  return bar;
}

function duration(s) {
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  return (d ? d + "d " : "") + (d || h ? h + "h " : "") + m + "min";
}

async function api(path, options) {
  const opts = Object.assign({ credentials: "same-origin", headers: {} }, options || {});
  if (opts.method === "POST") {
    opts.headers["Content-Type"] = "application/json";
    opts.headers["X-FliperOS"] = "1";
  }
  const res = await fetch(path, opts);
  if (res.status === 401) { showLogin(); throw new Error("login"); }
  return res;
}

// A midia de um jogo no gabinete (~/media, /api/media).
function mediaUrl(system, game, kind) {
  return "/api/media?system=" + encodeURIComponent(system) + "&game=" + encodeURIComponent(game) + "&kind=" + kind;
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector('script[src="' + src + '"]')) return resolve();
    const s = el("script", { src });
    s.onload = resolve;
    s.onerror = () => reject(new Error(src));
    document.head.append(s);
  });
}

// Os avisos de baixo: empilhados, com o icone do tipo (ok, erro, aviso).
function toast(text, kind) {
  const glyph = kind === "ok" ? "g-check" : kind === "bad" ? "g-warn" : "g-info";
  const box = el("div", { class: "toast " + (kind || "info"), role: "status" }, icon(glyph), el("span", {}, text));
  const list = $("toasts");
  list.append(box);
  while (list.children.length > 3) list.firstChild.remove();
  setTimeout(() => { box.classList.add("out"); setTimeout(() => box.remove(), 300); }, 4500);
}

// Copiar: o navigator.clipboard so existe em HTTPS; no painel (HTTP) vai
// pelo campo selecionado.
async function copyText(text, field) {
  try { await navigator.clipboard.writeText(text); } catch (e) {
    const input = field || el("textarea", { class: "offscreen" }, text);
    if (!field) document.body.append(input);
    input.select();
    document.execCommand("copy");
    if (!field) input.remove();
  }
  toast(t("copied"), "ok");
}

// Confirmar (ou perguntar, com input): o dialogo do painel no lugar do
// confirm() do navegador. Resolve com true/false (ou o texto, ou null).
function ask({ title, text = "", yes = t("ok"), no = t("cancel"), danger = false, input = null }) {
  const dlg = $("ask");
  $("ask-title").textContent = title;
  $("ask-text").textContent = text;
  $("ask-text").hidden = !text;
  $("ask-yes").textContent = yes;
  $("ask-no").textContent = no;
  $("ask-yes").className = "btn" + (danger ? " red" : "");
  const field = $("ask-input");
  field.hidden = input === null;
  field.value = input || "";
  return new Promise((resolve) => {
    dlg.onclose = () => {
      const ok = dlg.returnValue === "yes";
      resolve(input === null ? ok : ok ? field.value.trim() : null);
    };
    dlg.returnValue = "";
    dlg.showModal();
    (input === null ? $("ask-yes") : field).focus();
  });
}

// A folha (o jogo): sobe de baixo no celular, vem do lado no PC. Ela entra no
// historico, entao o Voltar do celular a fecha.
let sheetOpen = false;
function openSheet(build) {
  const back = $("sheet-back"), sheet = $("sheet");
  sheet.replaceChildren(...build());
  sheet.scrollTop = 0;
  back.hidden = false;
  document.body.classList.add("no-scroll");
  if (!sheetOpen) history.pushState({ sheet: 1 }, "");
  sheetOpen = true;
}
function closeSheet(fromHistory) {
  if (!sheetOpen) return;
  sheetOpen = false;
  $("sheet-back").hidden = true;
  document.body.classList.remove("no-scroll");
  $("sheet").querySelectorAll("video").forEach((v) => { v.pause(); v.removeAttribute("src"); v.load(); });
  if (!fromHistory) history.back();
}
window.addEventListener("popstate", () => closeSheet(true));
$("sheet-back").addEventListener("click", (ev) => { if (ev.target === $("sheet-back")) closeSheet(); });
document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && sheetOpen) closeSheet(); });

// Uma cor pelo nome (as capas geradas dos jogos sem imagem).
function nameHue(text) {
  let h = 0;
  for (const ch of text) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return h;
}
