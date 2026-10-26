// Frontend, a vitrine: as pastas com jogos (as mesmas dos frontends), as
// trilhas de favoritos e mais jogados, a busca com os filtros do Setup, a
// grade (ou lista) com a arte de ~/media e a folha de cada jogo.
//  - A grade carrega de 60 em 60 ao rolar; a regua de letras pula para a
//    letra; o contador diz quantos de quantos estao a vista.
//  - A folha: o video ou a snap, Jogar (fecha o que esta no tubo e abre o
//    jogo; quando ele fecha, volta o que estava), Favorito, os controles em
//    icones, as imagens, o painel de botoes e a historia (Arcade Database nos
//    arcades, libretro-thumbnails nos consoles; o navegador guarda 30 dias).
"use strict";

const GAMES_BATCH = 60;
const INFO_KEY = "fliperos-info:";
const INFO_DAYS = 30;
let systemsList = [], gameSystem = null, allGames = [], gameFilters = [], foundGames = [], gamesShown = 0;
let gameChip = "", gameView = "grid", searchTimer = null;
try {
  gameView = localStorage.getItem("fliperos-view") === "list" ? "list" : "grid";
} catch (e) { /* sem armazenamento */ }

// ── As pastas ────────────────────────────────────────────────────
async function loadSystems() {
  const res = await api("/api/systems");
  const data = await res.json();
  systemsList = (data.systems || []).filter((s) => s.games > 0);
  let keep = gameSystem && gameSystem.key;
  try { keep = keep || localStorage.getItem("fliperos-system") || ""; } catch (e) { /* sem armazenamento */ }
  // Sem escolha guardada, a pasta com mais jogos.
  gameSystem = systemsList.find((s) => s.key === keep) || systemsList.slice().sort((a, b) => b.games - a.games)[0] || null;
  $("systems-count").textContent = t("systems_n").replace("%n", systemsList.length);
  renderSystems();
  await loadGames();
}

function systemIcon(s, cls) {
  return s.icon ? el("img", { src: "/gui/icons/" + s.icon + ".png", alt: "", class: cls || "" })
    : el("span", { class: "mono " + (cls || "") }, s.name.slice(0, 1).toUpperCase());
}

function renderSystems() {
  const box = $("systems");
  box.replaceChildren(...systemsList.map((s, i) => {
    const mosaic = el("div", { class: "mosaic" + (s.covers.length ? "" : " empty") });
    const covers = s.covers.length ? s.covers : [];
    for (let j = 0; j < 4; j++) {
      const name = covers[j % Math.max(1, covers.length)];
      mosaic.append(name ? el("img", { src: mediaUrl(s.key, name, "snap"), alt: "", loading: "lazy" })
        : el("i", { style: "--h:" + nameHue(s.name + j) }));
    }
    const card = el("button", { type: "button", class: "sys" + (gameSystem && s.key === gameSystem.key ? " on" : ""),
      "aria-pressed": String(gameSystem && s.key === gameSystem.key) },
    mosaic, el("span", { class: "info" }, systemIcon(s), el("span", {}, el("b", {}, s.name),
      el("small", {}, gamesCount(s.games)))));
    card.style.animationDelay = i * 0.05 + "s";
    card.addEventListener("click", () => {
      gameSystem = s;
      try { localStorage.setItem("fliperos-system", s.key); } catch (e) { /* sem armazenamento */ }
      box.querySelectorAll(".sys").forEach((c) => { c.classList.toggle("on", c === card); c.setAttribute("aria-pressed", String(c === card)); });
      loadGames().catch(() => {});
      $("games-head").scrollIntoView({ behavior: "smooth", block: "start" });
    });
    return card;
  }));
}

async function loadGames() {
  if (!gameSystem) { allGames = []; gameFilters = []; renderChips(); renderGames(); renderRails(); return; }
  const res = await api("/api/games?system=" + encodeURIComponent(gameSystem.key));
  const data = await res.json();
  allGames = data.games || [];
  gameFilters = data.filters || [];
  $("games-system").textContent = gameSystem.name;
  $("games-icon").replaceChildren(systemIcon(gameSystem, "head-icon"));
  $("games-count").textContent = gamesCount(allGames.length);
  renderChips();
  renderRails();
  renderGames();
}

const gamesCount = (n) => (n === 1 ? t("count_one") : t("count").replace("%n", num(n)));

// ── Os filtros (os do Setup, como o Attract-Mode os aplica) ──────
// As regras na ordem; uma regra que falha tira o jogo, uma excecao que bate o
// poe de volta. Com uma regex (um caractere especial no valor), equals e a
// palavra inteira; sem, a comparacao ignora maiusculas.
const NUMERIC_OPS = { greater_than: (a, b) => a > b, less_than: (a, b) => a < b,
  greater_than_or_equal: (a, b) => a >= b, less_than_or_equal: (a, b) => a <= b };

function ruleMatches(rule, game) {
  const target = String(game[rule.field] == null ? "" : game[rule.field]), what = rule.what || "";
  if (NUMERIC_OPS[rule.op]) return NUMERIC_OPS[rule.op](parseFloat(target) || 0, parseFloat(what) || 0);
  if (rule.rex === undefined) {
    rule.rex = null;
    if (/[.+*?^$()[\]{}|\\]/.test(what)) {
      try { rule.rex = [new RegExp("^(?:" + what + ")$", "i"), new RegExp(what, "i")]; } catch (e) { /* literal */ }
    }
  }
  const low = target.toLowerCase(), w = what.toLowerCase(), rex = rule.rex;
  switch (rule.op) {
    case "equals": return !target ? !what : rex ? rex[0].test(target) : low === w;
    case "not_equals": return !target ? !!what : rex ? !rex[0].test(target) : low !== w;
    case "contains": return !!target && (rex ? rex[1].test(target) : low.includes(w));
    case "not_contains": return !target || (rex ? !rex[1].test(target) : !low.includes(w));
    default: return true;
  }
}

function compareValues(a, b) {
  const x = a == null ? "" : String(a), y = b == null ? "" : String(b);
  const nx = Number(x), ny = Number(y);
  if (x !== "" && y !== "" && !isNaN(nx) && !isNaN(ny)) return nx - ny;
  return x.localeCompare(y, undefined, { sensitivity: "base" });
}

function applyFilter(list, filter) {
  if (!filter) return list;
  let out = list.filter((game) => {
    for (const rule of filter.rules || []) {
      if (ruleMatches(rule, game) === !!rule.exception) return !!rule.exception;
    }
    return true;
  });
  if (filter.sort_by) out = out.slice().sort((a, b) => compareValues(a[filter.sort_by], b[filter.sort_by]));
  if (filter.reverse) out.reverse();
  if (filter.limit > 0) out = out.slice(0, filter.limit);
  else if (filter.limit < 0) out = out.slice(filter.limit);
  return out;
}

const FAV_FILTER = { name: "__fav", rules: [{ field: "Favourite", op: "equals", what: "1" }] };

function filterOptions() {
  // Os do Setup (sem eles, todos os jogos) e os favoritos, se nenhum filtro os tem.
  const rows = gameFilters.map((f) => ({ value: f.name, label: f.name, filter: f }));
  if (!rows.length) rows.push({ value: "__all", label: t("filter_all"), filter: null });
  if (!gameFilters.some((f) => (f.rules || []).some((r) => r.field === "Favourite"))) {
    rows.splice(1, 0, { value: "__fav", label: t("favourites"), filter: FAV_FILTER, star: true });
  }
  return rows;
}

function renderChips() {
  const rows = filterOptions();
  try { gameChip = gameChip || localStorage.getItem("fliperos-filter") || ""; } catch (e) { /* sem armazenamento */ }
  if (!rows.some((r) => r.value === gameChip)) gameChip = rows[0].value;
  $("game-chips").replaceChildren(...rows.map((r) => {
    const chip = el("button", { type: "button", class: "chip" + (r.value === gameChip ? " on" : ""),
      "aria-pressed": String(r.value === gameChip) }, r.star ? icon("g-star", "yellow") : "", r.label);
    chip.addEventListener("click", () => {
      gameChip = r.value;
      try { localStorage.setItem("fliperos-filter", gameChip); } catch (e) { /* sem armazenamento */ }
      renderChips();
      renderGames();
    });
    return chip;
  }));
}

function currentFilter() {
  const row = filterOptions().find((r) => r.value === gameChip);
  return row ? row.filter : null;
}

// ── As trilhas: favoritos e mais jogados ─────────────────────────
function renderRails() {
  const favs = allGames.filter((g) => g.Favourite);
  const top = allGames.filter((g) => g.PlayedCount).sort((a, b) => (b.PlayedTime || 0) - (a.PlayedTime || 0)).slice(0, 15);
  const name = gameSystem ? gameSystem.name : "";
  $("rail-fav-box").hidden = !favs.length;
  $("rail-fav-title").textContent = t("fav_of").replace("%s", name);
  $("rail-fav").replaceChildren(...favs.map((g, i) => gameCard(g, i)));
  $("rail-top-box").hidden = top.length < 3;
  $("rail-top-title").textContent = t("top_of").replace("%s", name);
  $("rail-top").replaceChildren(...top.map((g, i) => gameCard(g, i)));
}

// ── A grade ──────────────────────────────────────────────────────
const gameTitle = (g) => g.Title || g.Name;

function renderGames() {
  const query = $("game-search").value.trim().toLowerCase();
  let found = applyFilter(allGames, currentFilter());
  if (query) found = found.filter((g) => gameTitle(g).toLowerCase().includes(query) || g.Name.toLowerCase().includes(query));
  foundGames = found;
  gamesShown = 0;
  const grid = $("games");
  grid.classList.toggle("list", gameView === "list");
  grid.replaceChildren();
  $("view-grid").classList.toggle("on", gameView === "grid");
  $("view-list").classList.toggle("on", gameView === "list");
  $("games-empty").hidden = !!allGames.length;
  $("games-toolbar").hidden = !allGames.length;
  if (allGames.length && !found.length) grid.append(el("p", { class: "no-match" }, t("no_match")));
  moreGames();
  renderLetters();
}

function moreGames() {
  const next = foundGames.slice(gamesShown, gamesShown + GAMES_BATCH);
  const first = gamesShown === 0;
  $("games").append(...next.map((g, i) => gameCard(g, i, first)));
  gamesShown += next.length;
  $("games-shown").textContent = foundGames.length ? t("shown").replace("%n", num(gamesShown)).replace("%t", num(foundGames.length)) : "";
}

// O proximo lote quando o fim da grade chega perto.
new IntersectionObserver((entries) => {
  if (entries[0].isIntersecting && gamesShown < foundGames.length) moreGames();
}, { rootMargin: "800px" }).observe($("games-more"));

function cover(g) {
  // A capa de quem nao tem imagem: as iniciais em pixel sobre uma cor do nome.
  const words = gameTitle(g).replace(/[^\p{L}\p{N} ]/gu, " ").trim().split(/\s+/);
  const initials = (words.length > 1 ? words[0][0] + words[1][0] : (words[0] || "?").slice(0, 2)).toUpperCase();
  const box = el("div", { class: "cover", style: "--h:" + nameHue(gameTitle(g)) }, el("b", {}, initials));
  if (gameSystem) box.append(systemIcon(gameSystem, "cover-icon"));
  return box;
}

function gamePicture(g, kinds) {
  const art = g.art || "";
  const kind = kinds.find((k) => art.includes(k[0]));
  if (!kind) return cover(g);
  const img = el("img", { src: mediaUrl(gameSystem.key, g.Name, kind[1]), alt: "", loading: "lazy", decoding: "async",
    class: "pic-" + kind[1] });
  img.addEventListener("error", () => img.replaceWith(cover(g)));
  return img;
}

function gameCard(g, i, enter = true) {
  const shot = el("div", { class: "shot" }, gamePicture(g, [["s", "snap"], ["b", "box"], ["m", "marquee"], ["l", "logo"]]));
  if (g.Favourite) shot.append(el("span", { class: "star" }, icon("g-star")));
  const card = el("button", { type: "button", class: enter && i < 24 ? "game enter" : "game" }, shot,
    el("span", { class: "meta" }, el("b", {}, gameTitle(g)), el("span", {}, [g.Year, g.Manufacturer].filter(Boolean).join(" · "))));
  card.style.animationDelay = Math.min(i, 12) * 0.03 + "s";
  card.dataset.letter = letterOf(g);
  card.addEventListener("click", () => openGame(g));
  // No PC: passar o mouse toca o video do jogo depois de um instante.
  if ((g.art || "").includes("v") && matchMedia("(hover: hover)").matches) {
    let timer = null, video = null;
    card.addEventListener("mouseenter", () => {
      timer = setTimeout(() => {
        video = el("video", { muted: "", loop: "", playsinline: "", class: "preview", src: mediaUrl(gameSystem.key, g.Name, "preview") });
        video.muted = true;
        shot.append(video);
        video.play().catch(() => {});
      }, 600);
    });
    card.addEventListener("mouseleave", () => {
      clearTimeout(timer);
      if (video) { video.pause(); video.remove(); video = null; }
    });
  }
  return card;
}

// ── A regua de letras ────────────────────────────────────────────
function letterOf(g) {
  const ch = gameTitle(g).normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/^[^\p{L}\p{N}]+/u, "").slice(0, 1).toUpperCase();
  return /[A-Z]/.test(ch) ? ch : "#";
}

function renderLetters() {
  const box = $("letters");
  const have = new Set(foundGames.map(letterOf));
  box.hidden = foundGames.length < 40;
  box.replaceChildren(...["#", ..."ABCDEFGHIJKLMNOPQRSTUVWXYZ"].map((ch) =>
    el("button", { type: "button", "data-letter": ch, class: have.has(ch) ? "" : "off", tabindex: "-1" }, ch)));
}

function jumpTo(letter) {
  const index = foundGames.findIndex((g) => letterOf(g) === letter);
  if (index < 0) return;
  while (gamesShown <= index) moreGames();
  const card = $("games").children[index];
  if (card) card.scrollIntoView({ block: "center" });
  $("letters").querySelectorAll("button").forEach((b) => b.classList.toggle("now", b.dataset.letter === letter));
}

// Um toque pula; arrastar o dedo passa pelas letras.
(() => {
  const box = $("letters");
  let dragging = false;
  const at = (ev) => {
    const target = document.elementFromPoint(ev.clientX, ev.clientY);
    if (target && target.dataset && target.dataset.letter && !target.classList.contains("off")) jumpTo(target.dataset.letter);
  };
  box.addEventListener("pointerdown", (ev) => { dragging = true; box.setPointerCapture(ev.pointerId); at(ev); });
  box.addEventListener("pointermove", (ev) => { if (dragging) at(ev); });
  box.addEventListener("pointerup", () => { dragging = false; });
  box.addEventListener("pointercancel", () => { dragging = false; });
})();

// O botao de voltar ao topo, depois de descer bastante.
window.addEventListener("scroll", () => {
  $("to-top").hidden = !(area === "frontend" && window.scrollY > 1400);
}, { passive: true });
$("to-top").addEventListener("click", () => $("games-head").scrollIntoView({ behavior: "smooth" }));

$("game-search").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(renderGames, 150);
});
for (const [id, view] of [["view-grid", "grid"], ["view-list", "list"]]) {
  $(id).addEventListener("click", () => {
    gameView = view;
    try { localStorage.setItem("fliperos-view", view); } catch (e) { /* sem armazenamento */ }
    renderGames();
  });
}

// ── As informacoes da internet (guardadas no navegador 30 dias) ──
async function gameInfo(system, name) {
  const key = INFO_KEY + system + ":" + name;
  try {
    const hit = JSON.parse(localStorage.getItem(key) || "null");
    if (hit && Date.now() - hit.t < INFO_DAYS * 86400000) return hit.d;
  } catch (e) { /* sem armazenamento */ }
  const res = await api("/api/gameinfo?system=" + encodeURIComponent(system) + "&game=" + encodeURIComponent(name));
  if (!res.ok) throw new Error(res.statusText);
  const data = await res.json();
  cacheInfo(key, data);
  return data;
}

function cacheInfo(key, data) {
  const value = JSON.stringify({ t: Date.now(), d: data });
  for (let tries = 0; tries < 2; tries++) {
    try { localStorage.setItem(key, value); return; } catch (e) {
      // Cheio: sai a metade mais antiga das informacoes guardadas.
      try {
        const old = Object.keys(localStorage).filter((k) => k.startsWith(INFO_KEY))
          .map((k) => [k, (JSON.parse(localStorage.getItem(k)) || {}).t || 0]).sort((a, b) => a[1] - b[1]);
        if (!old.length) return;
        old.slice(0, Math.ceil(old.length / 2)).forEach(([k]) => localStorage.removeItem(k));
      } catch (e2) { return; }
    }
  }
}

// ── A folha do jogo ──────────────────────────────────────────────
function fact(glyph, label, value) {
  return el("div", { class: "fact-cell" }, typeof glyph === "string" ? icon(glyph) : glyph, el("small", {}, label), el("b", {}, value));
}

function picture(url, label, cls) {
  const img = el("img", { src: url, alt: label, loading: "lazy", referrerpolicy: "no-referrer" });
  const fig = el("figure", { class: cls || "" }, el("button", { type: "button", class: "pic" }, img), el("figcaption", {}, label));
  img.addEventListener("error", () => fig.remove());
  fig.firstChild.addEventListener("click", () => viewer(url));
  return fig;
}

// As imagens grandes, por cima de tudo; um toque fecha.
function viewer(url) {
  const box = el("div", { class: "viewer", role: "dialog" }, el("img", { src: url, alt: "" }));
  box.addEventListener("click", () => box.remove());
  document.body.append(box);
}

function openGame(g) {
  const system = gameSystem, art = g.art || "";
  const media = el("div", { class: "sheet-media" });
  const still = art.includes("s") ? mediaUrl(system.key, g.Name, "snap") : art.includes("b") ? mediaUrl(system.key, g.Name, "box") : "";
  if (still) media.append(el("img", { class: "blur", src: still, alt: "" }));
  if (art.includes("v")) {
    const video = el("video", { class: "main-shot", src: mediaUrl(system.key, g.Name, "preview"), muted: "", loop: "", playsinline: "", autoplay: "" });
    video.muted = true;
    media.append(video, el("span", { class: "video-tag" }, icon("g-play"), t("video_tag")));
  } else if (still) media.append(el("img", { class: "main-shot", src: still, alt: "" }));
  else media.append(el("div", { class: "main-shot cover-box" }, cover(g)));
  if (art.includes("l")) media.append(el("img", { class: "logo-over", src: mediaUrl(system.key, g.Name, "logo"), alt: "" }));
  const close = el("button", { type: "button", class: "sheet-close", "aria-label": t("close") }, icon("g-close"));
  close.addEventListener("click", () => closeSheet());
  media.append(el("div", { class: "handle" }), close);

  const play = el("button", { type: "button", class: "play-btn" }, icon("g-coin", "coin"), t("play_big"));
  play.addEventListener("click", () => playGame(g, play));
  const fav = el("button", { type: "button", class: "fav-btn" + (g.Favourite ? " on" : ""), "aria-pressed": String(!!g.Favourite) },
    icon(g.Favourite ? "g-star" : "g-staro"), t(g.Favourite ? "favourited" : "favourite"));
  fav.addEventListener("click", () => toggleFavourite(g, fav));

  const facts = el("div", { class: "fact-grid" });
  const genre = g.Category || "";
  if (genre) facts.append(fact("px-games", t("g_genre"), genre));
  const ctrlCell = el("div", { class: "fact-cell ctrl-cell" }, el("small", {}, t("controls")));
  const ctrl = controlIcons(g, null, true);
  if (ctrl) { ctrlCell.append(ctrl); facts.append(ctrlCell); }
  if (g.Rotation !== undefined) {
    facts.append(fact("px-orientation", t("g_screen"), /^(90|270)$/.test(String(g.Rotation)) ? t("orient_v") : t("orient_h")));
  }
  if (g.Status) {
    const status = g.Status.toLowerCase();
    facts.append(fact(el("span", { class: "lamp " + status }), t("g_status"), t("lamp_" + status) !== "lamp_" + status ? t("lamp_" + status) : g.Status));
  }
  if (g.PlayedCount) facts.append(fact("px-latency", t("g_played"), t("g_played_n").replace("%n", g.PlayedCount).replace("%t", duration(g.PlayedTime || 0))));
  if (g.CloneOf) facts.append(fact("px-link", t("g_parent"), g.CloneOf));
  facts.append(fact("px-dest", t("g_file"), g.file || g.Name));

  const gallery = el("div", { class: "gallery" });
  for (const [letter, kind, label] of [["s", "snap", "pic_snap"], ["m", "marquee", "pic_marquee"], ["b", "box", "pic_boxart"], ["l", "logo", "pic_logo"]]) {
    if (art.includes(letter)) gallery.append(picture(mediaUrl(system.key, g.Name, kind), t(label), kind === "marquee" ? "wide" : ""));
  }
  const online = el("div", { class: "loading", role: "status" }, el("span", { class: "spinner" }), el("span", {}, t("g_loading")));
  const about = el("div", { class: "about" });
  const body = el("div", { class: "sheet-body" },
    el("h2", { id: "sheet-title" }, gameTitle(g)),
    el("p", { class: "sheet-meta" }, [g.Year, g.Manufacturer].filter(Boolean).join(" · "), " ", systemIcon(system, "inl"), " ", system.name),
    el("div", { class: "cta" }, play, fav), facts,
    el("h3", {}, t("pictures")), gallery, online, about);
  openSheet(() => [media, body]);

  // A descricao salva (~/media/texto) e as informacoes da internet.
  if (art.includes("t")) {
    api(mediaUrl(system.key, g.Name, "texto")).then((r) => (r.ok ? r.text() : "")).then((text) => {
      if (text && !about.querySelector(".desc")) about.prepend(el("h3", {}, t("about")), describe(text));
    }).catch(() => {});
  }
  gameInfo(system.key, g.Name).then((data) => {
    online.remove();
    showOnline(data, gallery, about, ctrlCell, g);
  }).catch(() => online.replaceWith(el("p", { class: "dim" }, t("g_offline"))));
}

// Um texto longo comeca curto, com Ler mais.
function describe(text) {
  const p = el("p", { class: "desc clamp" }, text);
  const more = el("button", { type: "button", class: "link" }, t("read_more"), icon("g-chevd"));
  more.addEventListener("click", () => {
    const open = p.classList.toggle("clamp");
    more.replaceChildren(t(open ? "read_more" : "read_less"), icon(open ? "g-chevd" : "g-top"));
  });
  return el("div", { class: "desc-box" }, p, text.length > 280 ? more : "");
}

function showOnline(data, gallery, about, ctrlCell, g) {
  for (const i of data.images || []) gallery.append(picture(i.url, t("pic_" + i.kind)));
  const info = data.info;
  if (!info) {
    if (data.source === "Arcade Database") about.append(el("p", { class: "dim" }, t("g_not_found")));
    return;
  }
  for (const [k, label] of [["url_image_ingame", "pic_snap"], ["url_image_title", "pic_title"], ["url_image_marquee", "pic_marquee"],
    ["url_image_flyer", "pic_flyer"], ["url_image_cabinet", "pic_cabinet"]]) {
    if (info[k]) gallery.append(picture(info[k], t(label), k === "url_image_marquee" ? "wide" : ""));
  }
  // Os controles com as cores dos botoes do jogo.
  const panel = (data.panel || []).filter(Boolean);
  if (panel.length) {
    const old = ctrlCell.querySelector(".ctrl");
    const colors = (data.panel || []).map((c) => c && c.color);
    const ctrl = controlIcons(Object.assign({}, g, { Buttons: g.Buttons || String(panel.length) }), colors, true);
    if (ctrl) { if (old) old.replaceWith(ctrl); else ctrlCell.append(ctrl); }
    // Os botoes do jogador 1 no painel, onde o Setup > Joysticks > Buttons
    // layout os poe (1 2 3 em cima, 4 5 6 embaixo), com a cor e a funcao.
    about.append(el("h3", {}, t("buttons_p1")), el("div", { class: "panel-layout" }, ...data.panel.map((cell, i) => {
      const dot = el("i");
      if (cell) dot.style.backgroundColor = /^[a-z]+$/i.test(cell.color) ? cell.color : "var(--purple)";
      const where = (i < 3 ? " top" : " bottom") + " c" + (i % 3);
      return el("div", { class: (cell ? "pbtn on" : "pbtn") + where }, dot, cell ? el("span", {}, cell.label || String(cell.button)) : "");
    })));
  }
  // A descricao e as secoes do arcade-history (tecnica, curiosidades...).
  const text = data.description !== undefined ? data.description : (info.history || "").trim();
  if (text && !about.querySelector(".desc")) about.append(el("h3", {}, t("about")), describe(text));
  for (const [title, body] of data.sections || []) {
    about.append(el("details", { class: "history-part" }, el("summary", {}, title), el("p", {}, body)));
  }
  const links = el("div", { class: "links" });
  if (info.url) links.append(el("a", { class: "link", href: info.url, target: "_blank", rel: "noopener" }, icon("g-ext"), "Arcade Database"));
  if (info.url_video_shortplay) links.append(el("a", { class: "link", href: info.url_video_shortplay, target: "_blank", rel: "noopener" }, icon("g-play"), t("g_video")));
  if (info.youtube_video_id) {
    links.append(el("a", { class: "link", target: "_blank", rel: "noopener",
      href: "https://www.youtube.com/watch?v=" + encodeURIComponent(info.youtube_video_id) }, icon("g-ext"), "YouTube"));
  }
  if (info.history_copyright_short) links.append(el("span", { class: "dim" }, info.history_copyright_short));
  // Salvo no gabinete (~/media/info): nao e buscado de novo.
  if (data.saved) {
    links.append(el("span", { class: "dim" }, t("g_saved").replace("%s", new Date(data.saved * 1000).toLocaleDateString(locale()))));
  }
  about.append(links);
}

async function playGame(g, button) {
  const name = gameTitle(g);
  if (!(await ask({ title: t("confirm_launch").replace("%s", name), yes: t("play") }))) return;
  button.classList.add("inserting");
  coinDrop();
  const res = await api("/api/launch", { method: "POST", body: JSON.stringify({ system: gameSystem.key, game: g.Name }) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { button.classList.remove("inserting"); toast(data.error || res.statusText, "bad"); return; }
  toast(t("launching").replace("%s", name), "ok");
  setTimeout(() => {
    closeSheet();
    crtFlash("static");
    $("cab").scrollIntoView({ behavior: "smooth", block: "start" });
  }, 500);
}

async function toggleFavourite(g, button) {
  const res = await api("/api/favourite", { method: "POST",
    body: JSON.stringify({ system: gameSystem.key, game: g.Name, on: !g.Favourite }) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { toast(data.error || res.statusText, "bad"); return; }
  if (data.favourite) g.Favourite = "1"; else delete g.Favourite;
  button.classList.toggle("on", !!g.Favourite);
  button.setAttribute("aria-pressed", String(!!g.Favourite));
  button.replaceChildren(icon(g.Favourite ? "g-star" : "g-staro"), t(g.Favourite ? "favourited" : "favourite"));
  if (g.Favourite) { button.classList.remove("burst"); void button.offsetWidth; button.classList.add("burst"); }
  renderRails();
  // A estrela no cartao da grade, sem refazer a grade (a posicao fica).
  [...$("games").children].forEach((card, i) => {
    if (foundGames[i] !== g) return;
    const star = card.querySelector(".star");
    if (g.Favourite && !star) card.querySelector(".shot").append(el("span", { class: "star" }, icon("g-star")));
    if (!g.Favourite && star) star.remove();
  });
}
