// Os jogos do marquee (games.html): o que cada jogo mostra alem da arte e em
// qual emulador. Os dados: /api/marquee/games (o login do painel).
"use strict";

const STRINGS = {
  en: {
    title: "Marquee games", search: "Search by name or set",
    lead: "What the marquee (for OBS and the LED one) shows for each game, and in which emulator.",
    login: "Log in to the web panel first, then open this page again.",
    art: "The game's art", art_text: "Every game of every emulator: the marquee or logo from ~/media (the Scraper) or from the Pixelcade art.",
    all: "all emulators",
    hs: "High scores (the top 3)", hs_text: "Read from the high-score files (.hi) that MAME writes, by hi2txt. RetroArch: the MAME cores (games in ~/roms/mame).",
    hs_missing: "hi2txt is not downloaded yet: Setup > System > Extras > Pixelcade (or ZeDMD) downloads it.",
    vs: "Versus scoreboard", vs_text: "The wins of each side in the session (and the points, where the game has them), read from the game's memory.",
    vs_missing: "No game yet: Setup > System > Extras > Pixelcade (or ZeDMD) downloads Fightcade's detectors.",
    ach: "Achievements", ach_text: "RetroArch, with a RetroAchievements account: every game the site supports.",
    ach_link: "See the games on retroachievements.org", wins: "wins", score: "points", games: "%n games", none: "No game matches.",
  },
  pt: {
    title: "Jogos do marquee", search: "Buscar pelo nome ou pelo set",
    lead: "O que o marquee (o do OBS e o de LED) mostra em cada jogo, e em qual emulador.",
    login: "Entre no painel web primeiro e abra esta página de novo.",
    art: "A arte do jogo", art_text: "Todo jogo de todo emulador: o marquee ou o logo de ~/media (o Scraper) ou da arte do Pixelcade.",
    all: "todos os emuladores",
    hs: "Recordes (os 3 primeiros)", hs_text: "Lidos dos arquivos de recordes (.hi) que o MAME grava, pelo hi2txt. No RetroArch: os cores do MAME (jogos em ~/roms/mame).",
    hs_missing: "O hi2txt ainda não foi baixado: Setup > System > Extras > Pixelcade (ou ZeDMD) baixa.",
    vs: "Placar versus", vs_text: "As vitórias de cada lado na sessão (e os pontos, nos jogos que têm), lidos da memória do jogo.",
    vs_missing: "Nenhum jogo ainda: Setup > System > Extras > Pixelcade (ou ZeDMD) baixa os detectores do Fightcade.",
    ach: "Conquistas", ach_text: "RetroArch, com uma conta do RetroAchievements: todo jogo que o site aceita.",
    ach_link: "Ver os jogos no retroachievements.org", wins: "vitórias", score: "pontos", games: "%n jogos", none: "Nenhum jogo com esse nome.",
  },
};
const EMULATORS = { groovymame: "GroovyMAME", fbneo: "RetroArch (FBNeo)", retroarch: "RetroArch", "sm2-emu": "SM2-Emu (Model 2)" };

let lang = "en";
try { lang = localStorage.getItem("fliperos-lang") || ""; } catch (e) { /* sem armazenamento */ }
if (!STRINGS[lang]) lang = (navigator.language || "").startsWith("pt") ? "pt" : "en";
const t = (key) => STRINGS[lang][key];
document.documentElement.lang = lang === "pt" ? "pt-BR" : "en";

function el(tag, attrs, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, v);
  node.append(...children.filter((c) => c != null));
  return node;
}

// Uma secao: o titulo, o texto, os emuladores e a lista (que a busca filtra).
function feature(title, text, emus, items, missing) {
  const card = el("section", { class: "card feature" }, el("h2", {}, title), el("p", {}, text));
  card.append(el("div", { class: "emus" }, ...emus.map(([name, n]) =>
    el("span", { class: "emu" }, name, n != null ? el("small", {}, t("games").replace("%n", n)) : null))));
  if (missing) card.append(el("p", { class: "missing" }, missing));
  if (items) {
    const list = el("ul", { class: "list" });
    for (const item of items) {
      const li = el("li", {}, el("span", { title: item.title || item.name }, item.title || item.name,
        ...(item.tags || []).map((tag) => el("span", { class: "tag" }, tag))), el("code", {}, item.name));
      li.dataset.q = (item.name + " " + (item.title || "")).toLowerCase();
      list.append(li);
    }
    const none = el("p", { class: "dim", hidden: "" }, t("none"));
    card.append(list, none);
    card.filter = (q) => {
      let shown = 0;
      for (const li of list.children) {
        li.hidden = !!q && !li.dataset.q.includes(q);
        if (!li.hidden) shown++;
      }
      none.hidden = shown > 0 || !items.length;
    };
  }
  return card;
}

async function main() {
  document.title = "FliperOS — " + t("title");
  document.getElementById("h").textContent = t("title");
  document.getElementById("lead").textContent = t("lead");
  const q = document.getElementById("q");
  q.placeholder = t("search");
  const res = await fetch("/api/marquee/games", { credentials: "same-origin", headers: { "X-FliperOS": "1" } });
  if (!res.ok) {
    const error = document.getElementById("error");
    error.textContent = res.status === 401 ? t("login") : res.statusText;
    error.hidden = false;
    return;
  }
  const data = await res.json();
  const title = (name) => data.titles[name] || "";
  const sections = [];
  sections.push(feature(t("art"), t("art_text"), [[t("all")]]));
  const hs = data.highscores;
  sections.push(feature(t("hs"), t("hs_text"), [["GroovyMAME", hs ? hs.length : null], ["RetroArch (MAME)"]],
    hs && hs.map((name) => ({ name, title: title(name) })), hs ? null : t("hs_missing")));
  // O versus: um item por jogo, com os emuladores e o que ha em cada um.
  const games = new Map(), counts = new Map();
  for (const [emu, name, what] of data.versus) {
    if (!games.has(name)) games.set(name, { name, title: title(name), tags: [] });
    games.get(name).tags.push((EMULATORS[emu] || emu) + " · " + what.split(",").map((w) => t(w) || w).join(", "));
    counts.set(emu, (counts.get(emu) || 0) + 1);
  }
  const vs = [...games.values()].sort((a, b) => (a.title || a.name).localeCompare(b.title || b.name));
  sections.push(feature(t("vs"), t("vs_text"), [...counts].map(([emu, n]) => [EMULATORS[emu] || emu, n]), vs,
    vs.length ? null : t("vs_missing")));
  const ach = feature(t("ach"), t("ach_text"), [["RetroArch"]]);
  ach.append(el("a", { href: "https://retroachievements.org/gameList.php", target: "_blank", rel: "noopener" }, t("ach_link")));
  sections.push(ach);
  document.getElementById("features").append(...sections);
  q.addEventListener("input", () => {
    const text = q.value.trim().toLowerCase();
    for (const s of sections) if (s.filter) s.filter(text);
  });
}

main().catch((e) => {
  const error = document.getElementById("error");
  error.textContent = String(e.message || e);
  error.hidden = false;
});
