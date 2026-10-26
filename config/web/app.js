// O painel web do FliperOS (config/fliperos-web): o login, as quatro areas
// (Frontend, Ao vivo, Biblioteca, Sistema; o endereco e #area/aba) e o
// /api/status a cada segundo, parado com a aba escondida. Ingles ou portugues
// pelo idioma do navegador (o botao troca; a escolha fica no localStorage).
"use strict";

// As areas e as abas de cada uma, com os icones do Setup.
const AREAS = {
  frontend: { icon: "px-frontend", subs: [] },
  live: { icon: "px-video", subs: [["watch", "px-video"], ["obs", "px-outputs"]] },
  library: { icon: "px-games", subs: [["overview", "px-games"], ["install", "px-emulators"], ["downloads", "px-torrent"],
    ["romfilter", "px-filter"], ["art", "px-scraper"], ["files", "px-dest"]] },
  system: { icon: "px-setup", subs: [["status", "px-chip"], ["logs", "px-romlist"], ["settings", "px-setup"],
    ["terminal", "px-shell"], ["lab", "px-lab"]] },
};
// Os enderecos das dez paginas de antes continuam abrindo (o /lab manda
// para #status), e o codigo de cada pagina confere o nome antigo (page).
const OLD_PAGES = { status: "system/status", settings: "system/settings", terminal: "system/terminal",
  downloads: "library/downloads", scraper: "library/art", install: "library/install", files: "library/files",
  romfilter: "library/romfilter" };
const PAGE_OF = { "library/downloads": "downloads", "library/art": "scraper", "library/install": "install",
  "library/files": "files", "library/romfilter": "romfilter", "library/overview": "overview", "system/status": "status",
  "system/logs": "logs", "system/settings": "settings", "system/terminal": "terminal", "system/lab": "lab" };

let sub = "";

function resolve(hash) {
  const name = OLD_PAGES[hash] || hash;
  const [a, s] = name.split("/");
  if (!AREAS[a]) return ["frontend", ""];
  const subs = AREAS[a].subs.map(([n]) => n);
  return [a, subs.includes(s) ? s : subs[0] || ""];
}

// ── Login ────────────────────────────────────────────────────────
function showLogin() {
  $("app").hidden = true;
  $("login").hidden = false;
  stop();
  $("password").focus();
}

$("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("login-error").textContent = "";
  const res = await fetch("/api/login", {
    method: "POST", credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-FliperOS": "1" },
    body: JSON.stringify({ user: $("user").value, password: $("password").value }),
  });
  if (res.ok) {
    $("password").value = "";
    start();
  } else {
    const data = await res.json().catch(() => ({}));
    $("login-error").textContent = res.status === 401 ? t("wrong") : data.error || res.statusText;
    const form = $("login-form");
    form.classList.remove("shake");
    void form.offsetWidth;
    form.classList.add("shake");
  }
});

async function logout() {
  await api("/api/logout", { method: "POST" }).catch(() => {});
  showLogin();
}
$("logout").addEventListener("click", logout);
$("logout2").addEventListener("click", logout);

function switchLang() {
  lang = lang === "pt" ? "en" : "pt";
  try { localStorage.setItem("fliperos-lang", lang); } catch (e) { /* sem armazenamento */ }
  translate();
  showPage(area + (sub ? "/" + sub : ""));
  if (lastStatus) render(lastStatus);
  renderSystems();
  renderChips();
  renderRails();
  renderGames();
  renderTools();
  renderRomFilter();
  loadSettings().catch(() => {});
}
$("lang").addEventListener("click", switchLang);
$("lang2").addEventListener("click", switchLang);

// O menu do celular (o idioma e sair, que no PC ficam na barra lateral).
$("menu-btn").addEventListener("click", () => {
  const menu = $("top-menu");
  menu.hidden = !menu.hidden;
  $("menu-btn").setAttribute("aria-expanded", String(!menu.hidden));
});
document.addEventListener("click", (ev) => {
  if (!$("top-menu").hidden && !ev.target.closest("#top-menu, #menu-btn")) $("top-menu").hidden = true;
});

// ── As areas ─────────────────────────────────────────────────────
function showPage(hash) {
  const [a, s] = resolve(hash);
  const before = area;
  const apply = () => {
    area = a;
    sub = s;
    page = PAGE_OF[a + "/" + s] || a;
    document.body.dataset.area = a;
    document.querySelectorAll(".area").forEach((box) => {
      box.hidden = box.dataset.area !== a;
      box.querySelectorAll(":scope > .sub[data-sub]").forEach((part) => { part.hidden = part.dataset.sub !== s; });
    });
    document.querySelectorAll("[data-area]").forEach((link) => {
      if (link.tagName !== "A") return;
      if (link.dataset.area === a) link.setAttribute("aria-current", "page"); else link.removeAttribute("aria-current");
    });
    $("page-title").textContent = t("area_" + a).toUpperCase();
    $("page-sub").textContent = t("intro_" + a);
    $("area-icon").setAttribute("href", "icons.svg#" + AREAS[a].icon);
    $("subtabs").hidden = !AREAS[a].subs.length;
    $("subtabs").replaceChildren(...AREAS[a].subs.map(([name, glyph]) => el("a", {
      href: "#" + a + "/" + name, class: name === s ? "on" : "", "aria-current": name === s ? "page" : "false" },
    icon(glyph), t("sub_" + name))));
  };
  if (document.startViewTransition && before && before !== a && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    document.startViewTransition(apply);
  } else apply();
  area = a;
  sub = s;
  page = PAGE_OF[a + "/" + s] || a;
  try { localStorage.setItem("fliperos-page", a + (s ? "/" + s : "")); } catch (e) { /* sem armazenamento */ }
  if (sheetOpen) closeSheet();
  $("top-menu").hidden = true;
  if (before !== a) window.scrollTo(0, 0);
  cabinetShown(a === "frontend");
  // O que cada aba busca ao aparecer.
  if (page === "files") loadFiles().catch(() => {});
  else if (page === "downloads") { loadDownloader().catch(() => {}); loadBios().catch(() => {}); }
  else if (page === "scraper") loadScraper().catch(() => {});
  else if (page === "install") loadInstall().catch(() => {});
  else if (page === "settings") loadSettings().catch(() => {});
  else if (page === "lab") loadLab().catch(() => {});
  else if (page === "romfilter") { if (!rf.loaded) loadRomFilter("").catch(() => {}); }
  else if (page === "logs") loadLogs().catch(() => {});
  else if (page === "terminal" && termFit) requestAnimationFrame(() => termFit.fit());
  if (a === "live") {
    loadLive().catch(() => {});
    loadOverlay().catch(() => {});
    loadPadStyle().catch(() => {});
  } else padPreview(false);
  // Fora da area Ao vivo a transmissao para: o ffmpeg do gabinete so roda
  // enquanto alguem assiste.
  if (a !== "live" && live) liveStop();
}

window.addEventListener("hashchange", () => showPage(location.hash.slice(1)));

function firstPage() {
  let saved = "";
  try { saved = localStorage.getItem("fliperos-page") || ""; } catch (e) { /* sem armazenamento */ }
  return location.hash.slice(1) || saved || "frontend";
}

// A visao geral da Biblioteca: um cartao por ferramenta.
function renderTools() {
  const tools = [["install", "px-emulators"], ["downloads", "px-torrent"], ["romfilter", "px-filter"], ["art", "px-scraper"],
    ["files", "px-dest"]];
  $("tools").replaceChildren(...tools.map(([name, glyph], i) => {
    const card = el("a", { class: "tool", href: "#library/" + name }, icon(glyph, "big"), el("h3", {}, t("tool_" + name)),
      el("p", {}, t("tool_" + name + "_text")), el("span", { class: "tool-foot" }, el("span", { class: "btn small ghost" }, t("open"), icon("g-chev"))));
    card.style.animationDelay = i * 0.06 + "s";
    return card;
  }));
}

// ── O status a cada segundo ──────────────────────────────────────
let lastStatus = null;

function render(s) {
  lastStatus = s;
  $("version").textContent = s.version ? "v" + s.version : "";
  const ips = Object.values(s.network || {}).flatMap((n) => n.ipv4 || []);
  const host = [ips.join(", "), s.uptime ? t("uptime") + " " + duration(s.uptime) : ""].filter(Boolean).join(" · ");
  $("host-name").textContent = s.host || "FliperOS";
  $("host").textContent = host;
  $("host2").textContent = [s.host, host].filter(Boolean).join(" · ");
  renderCabinet(s);
  if (area === "system") renderStatus(s);
}

function connection(ok) {
  $("conn").className = "pill " + (ok ? "ok" : "bad");
  $("conn-text").textContent = t(ok ? "conn_ok" : "conn_off");
  $("conn-dot").className = "dot " + (ok ? "ok" : "bad");
}

let timer = null, ticks = 0;
async function tick() {
  if (document.visibilityState === "hidden") return;
  try {
    const res = await api("/api/status");
    render(await res.json());
    connection(true);
    // O Downloader e os pacotes de arte, a cada 3 s, com a aba deles aberta.
    if (ticks++ % 3 === 0) {
      if (page === "downloads") loadDownloader().catch(() => {});
      if (page === "scraper") loadPacks().catch(() => {});
    }
    tasksTick(Date.now());
  } catch (e) {
    if (e.message !== "login") { connection(false); renderCabinet(null); }
  }
}
// De volta a aba: o status na hora.
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible" && timer) tick(); });

function start() {
  $("login").hidden = true;
  $("app").hidden = false;
  stop();
  tick();
  loadSystems().catch(() => {});
  loadFiles("").catch(() => {});
  renderTools();
  showPage(firstPage());
  timer = setInterval(tick, 1000);
}
function stop() {
  if (timer) clearInterval(timer);
  timer = null;
  cabinetShown(false);
}

translate();
fetch("/api/me", { credentials: "same-origin" }).then((res) => (res.ok ? start() : showLogin())).catch(showLogin);
