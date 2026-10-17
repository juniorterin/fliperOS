// O painel web do FliperOS (config/fliperos-web): pede /api/status a cada
// segundo e desenha os cartoes. O historico do FPS (1 minuto) fica so aqui
// no navegador. Ingles ou portugues pelo idioma do navegador (o botao troca;
// a escolha fica no localStorage, quando ele existe).
"use strict";

const TEXT = {
  en: {
    login_text: "Sign in with the cabinet's user and password (the same as SSH and the network share).",
    user: "User", password: "Password", enter: "Sign in", logout: "Sign out",
    offline: "The cabinet is not answering. Retrying…", now_playing: "Now playing",
    nothing: "Nothing open", frontend: "Frontend", fps_note: "Last minute, from the OpenGL layer of the game.",
    video: "Video", memory: "Memory", storage: "Storage", network: "Network", volume: "Volume", mute: "Mute / unmute",
    processes: "Processes", logs: "Logs", refresh: "Refresh", wanted: "Asked in Video Setup", applied: "On screen now",
    monitor: "Monitor", frequency: "Frequency", resolution: "Resolution", connector: "Connector",
    orientation: "Orientation", mode: "Mode", hsync: "Horizontal", vsync: "Vertical", scan: "Scan",
    interlaced: "interlaced", progressive: "progressive", framebuffer: "Console framebuffer",
    no_output: "No active output found.", load: "load", used: "used", of: "of", swap: "Swap",
    down: "down", up: "up", signal: "signal", name: "Name", cpu: "CPU", mem: "Memory",
    busy: "busy", vram: "VRAM", clock: "clock", temp: "temperature", power: "power",
    filtering: "flicker filter on", core: "core", wrong: "Wrong user or password.",
    uptime: "up", not_installed: "No volume control.",
    games: "Games", search: "Search games", play: "Play", close_game: "Close the game",
    confirm_launch: "Close what is on the cabinet screen and open %s?", launching: "Opening %s on the cabinet…",
    confirm_close: "Close the game on the cabinet?", first: "Showing the first %n. Type to filter.",
    no_games: "No games in this folder.", count: "%n games",
    page_frontend: "Frontend", page_files: "Files", page_settings: "Settings", page_status: "Status", page_terminal: "Terminal",
    settings: "Settings", settings_note: "Each change is saved and applied right away, through the Setup. Monitor, resolution and video driver stay in the Setup, on the cabinet screen.",
    saved: "Saved: %s", group_System: "System", group_Services: "Services", "group_480i games": "480i games", group_Colour: "Colour",
    downloads: "Downloads", dl_filter: "Filter (Setup > Games > Downloader):", dl_start: "Apply the filter and start",
    dl_note: "The filter itself is chosen in the Setup.", dl_roms: "ROM torrent", dl_chds: "CHD torrent", dl_none: "No link yet.",
    dl_add: "Add link", dl_default: "Use the link that comes with FliperOS", dl_paste: "magnet:?… (paste a link)", dl_remove: "Remove",
    dl_remove_ask: "Remove this torrent from the downloader?", dl_delete_ask: "Also delete what it already downloaded (not what reached the game folders)?",
    tasks: "Tasks", no_tasks: "Nothing running.", show_log: "Log", cancel: "Cancel", task_ok: "done", task_fail: "failed",
    trackball: "Trackball", ball_open: "Use the phone as a trackball", sensitivity: "Sensitivity", inertia: "Keeps rolling",
    ball_hint: "Roll with your finger (a quick flick keeps rolling; touch to stop it).", ball_on: "Connected: the cabinet sees a USB mouse.",
    btn_left: "Button 1", btn_middle: "3", btn_right: "Button 2",
    terminal: "Terminal", term_open: "Open the terminal", term_close: "Close", term_connecting: "Connecting…",
    term_on: "The cabinet's shell (zsh, user fliperos).", term_off: "Disconnected.",
    screen: "Screen", take_shot: "Take a screenshot", as_on_tube: "4:3, as on the tube", save_png: "Save PNG",
    shot_wait: "Taking the picture…", shot_from: "%w×%h, %s · %t", shot_x11: "desktop (X)", shot_gl: "OpenGL frame",
    files: "Files", up_folder: "Up", upload: "Upload files", new_folder: "New folder", folder_name: "Name of the new folder:",
    confirm_delete: "Delete %s from the cabinet?", uploading: "Sending %s… %p%", uploaded: "Sent: %n file(s).",
    exists_overwrite: "%s already exists there. Replace it?", empty_folder: "Empty folder.", delete: "Delete",
    size: "Size", modified: "Modified", drop_hint: "You can also drop files on the list to send them to this folder.",
  },
  pt: {
    login_text: "Entre com o usuário e a senha do gabinete (os mesmos do SSH e da pasta de rede).",
    user: "Usuário", password: "Senha", enter: "Entrar", logout: "Sair",
    offline: "O gabinete não está respondendo. Tentando de novo…", now_playing: "Jogando agora",
    nothing: "Nada aberto", frontend: "Frontend", fps_note: "Último minuto, da camada OpenGL do jogo.",
    video: "Vídeo", memory: "Memória", storage: "Armazenamento", network: "Rede", volume: "Volume", mute: "Mudo / som",
    processes: "Processos", logs: "Logs", refresh: "Atualizar", wanted: "Pedido no Video Setup", applied: "Na tela agora",
    monitor: "Monitor", frequency: "Frequência", resolution: "Resolução", connector: "Conector",
    orientation: "Orientação", mode: "Modo", hsync: "Horizontal", vsync: "Vertical", scan: "Varredura",
    interlaced: "entrelaçado", progressive: "progressivo", framebuffer: "Framebuffer do console",
    no_output: "Nenhuma saída ativa.", load: "carga", used: "usado", of: "de", swap: "Swap",
    down: "desce", up: "sobe", signal: "sinal", name: "Nome", cpu: "CPU", mem: "Memória",
    busy: "uso", vram: "VRAM", clock: "clock", temp: "temperatura", power: "consumo",
    filtering: "filtro de flicker ligado", core: "core", wrong: "Usuário ou senha errados.",
    uptime: "ligado há", not_installed: "Sem controle de volume.",
    games: "Jogos", search: "Buscar jogos", play: "Jogar", close_game: "Fechar o jogo",
    confirm_launch: "Fechar o que está na tela do gabinete e abrir %s?", launching: "Abrindo %s no gabinete…",
    confirm_close: "Fechar o jogo no gabinete?", first: "Mostrando os primeiros %n. Digite para filtrar.",
    no_games: "Nenhum jogo nesta pasta.", count: "%n jogos",
    page_frontend: "Frontend", page_files: "Arquivos", page_settings: "Configurações", page_status: "Status", page_terminal: "Terminal",
    settings: "Configurações", settings_note: "Cada mudança é gravada e aplicada na hora, pelo Setup. Monitor, resolução e driver de vídeo ficam no Setup, na tela do gabinete.",
    saved: "Gravado: %s", group_System: "Sistema", group_Services: "Serviços", "group_480i games": "Jogos 480i", group_Colour: "Cor",
    downloads: "Downloads", dl_filter: "Filtro (Setup > Games > Downloader):", dl_start: "Aplicar o filtro e começar",
    dl_note: "O filtro em si é escolhido no Setup.", dl_roms: "Torrent das ROMs", dl_chds: "Torrent dos CHDs", dl_none: "Sem link ainda.",
    dl_add: "Cadastrar link", dl_default: "Usar o link que vem no FliperOS", dl_paste: "magnet:?… (cole um link)", dl_remove: "Remover",
    dl_remove_ask: "Tirar este torrent do downloader?", dl_delete_ask: "Apagar também o que ele já baixou (não o que já chegou às pastas dos jogos)?",
    tasks: "Tarefas", no_tasks: "Nada rodando.", show_log: "Log", cancel: "Cancelar", task_ok: "pronto", task_fail: "falhou",
    trackball: "Trackball", ball_open: "Usar o celular como trackball", sensitivity: "Sensibilidade", inertia: "Continua rolando",
    ball_hint: "Role com o dedo (um giro rápido continua rolando; toque para parar).", ball_on: "Conectado: o gabinete vê um mouse USB.",
    btn_left: "Botão 1", btn_middle: "3", btn_right: "Botão 2",
    terminal: "Terminal", term_open: "Abrir o terminal", term_close: "Fechar", term_connecting: "Conectando…",
    term_on: "O shell do gabinete (zsh, usuário fliperos).", term_off: "Desconectado.",
    screen: "Tela", take_shot: "Tirar screenshot", as_on_tube: "4:3, como no tubo", save_png: "Salvar PNG",
    shot_wait: "Tirando a foto…", shot_from: "%w×%h, %s · %t", shot_x11: "desktop (X)", shot_gl: "quadro OpenGL",
    files: "Arquivos", up_folder: "Subir", upload: "Enviar arquivos", new_folder: "Nova pasta", folder_name: "Nome da pasta nova:",
    confirm_delete: "Apagar %s do gabinete?", uploading: "Enviando %s… %p%", uploaded: "Enviado(s): %n arquivo(s).",
    exists_overwrite: "%s já existe lá. Substituir?", empty_folder: "Pasta vazia.", delete: "Apagar",
    size: "Tamanho", modified: "Modificado", drop_hint: "Também dá para soltar arquivos na lista para enviá-los a esta pasta.",
  },
};

let lang = "en";
try {
  lang = localStorage.getItem("fliperos-lang") || (navigator.language || "").slice(0, 2);
} catch (e) {
  lang = (navigator.language || "").slice(0, 2);
}
if (!TEXT[lang]) lang = "en";
const t = (key) => TEXT[lang][key] || TEXT.en[key] || key;
const $ = (id) => document.getElementById(id);

function translate() {
  document.documentElement.lang = lang === "pt" ? "pt-BR" : "en";
  document.querySelectorAll("[data-t]").forEach((el) => { el.textContent = t(el.dataset.t); });
  document.querySelectorAll("[data-tp]").forEach((el) => { el.placeholder = t(el.dataset.tp); });
  $("lang").textContent = lang === "pt" ? "EN" : "PT";
}

function el(tag, attrs, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") node.className = v; else node.setAttribute(k, v);
  }
  for (const c of children) node.append(c instanceof Node ? c : document.createTextNode(c == null ? "" : String(c)));
  return node;
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
  }
});

$("logout").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" }).catch(() => {});
  showLogin();
});

$("lang").addEventListener("click", () => {
  lang = lang === "pt" ? "en" : "pt";
  try { localStorage.setItem("fliperos-lang", lang); } catch (e) { /* sem armazenamento */ }
  translate();
  if (last) render(last);
  renderGames();
  loadSettings().catch(() => {});
});

// ── O FPS do ultimo minuto ───────────────────────────────────────

const fpsHistory = [];
function drawFps() {
  const canvas = $("fps-chart"), ctx = canvas.getContext("2d");
  const ratio = window.devicePixelRatio || 1, w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * ratio; canvas.height = h * ratio;
  ctx.scale(ratio, ratio);
  ctx.clearRect(0, 0, w, h);
  const css = getComputedStyle(document.documentElement);
  const top = Math.max(60, ...fpsHistory.map((p) => p || 0)) * 1.1;
  ctx.strokeStyle = css.getPropertyValue("--line");
  ctx.setLineDash([3, 3]);
  const y60 = h - (60 / top) * h;
  ctx.beginPath(); ctx.moveTo(0, y60); ctx.lineTo(w, y60); ctx.stroke();
  ctx.setLineDash([]);
  ctx.strokeStyle = css.getPropertyValue("--green");
  ctx.lineWidth = 2;
  ctx.beginPath();
  let pen = false;
  fpsHistory.forEach((v, i) => {
    const x = (i / 59) * w;
    if (v == null) { pen = false; return; }
    const y = h - (v / top) * h;
    if (pen) ctx.lineTo(x, y); else ctx.moveTo(x, y);
    pen = true;
  });
  ctx.stroke();
}

// ── Os cartoes ───────────────────────────────────────────────────

let last = null;
function render(s) {
  last = s;
  $("version").textContent = s.version ? "v" + s.version : "";
  const ips = Object.values(s.network || {}).flatMap((n) => n.ipv4 || []);
  $("host").textContent = [s.host, ips.join(", "), s.uptime ? t("uptime") + " " + duration(s.uptime) : ""]
    .filter(Boolean).join(" · ");

  // Jogando agora.
  const game = s.running && s.running.game, front = s.running && s.running.frontend;
  $("game").textContent = game ? (game.file || game.program) : t("nothing");
  const fps = s.fps;
  $("game-detail").textContent = game
    ? [game.program, fps && fps.core ? t("core") + " " + fps.core : "", fps && fps.filtering ? t("filtering") : ""]
      .filter(Boolean).join(" · ")
    : "";
  $("frontend").textContent = front ? t("frontend") + ": " + front.program : "";
  $("close-game").hidden = !game;
  $("fps").textContent = fps ? fps.fps.toFixed(1) : "-";
  fpsHistory.push(fps ? fps.fps : null);
  while (fpsHistory.length > 60) fpsHistory.shift();
  drawFps();

  // Video: o pedido e o aplicado.
  const v = s.video || {}, w = v.wanted || {};
  const table = $("video-table");
  table.replaceChildren();
  const add = (k, val) => table.append(el("tr", {}, el("th", {}, t(k)), el("td", {}, val || "-")));
  table.append(el("tr", {}, el("th", { colspan: "2" }, t("wanted"))));
  add("monitor", w.monitor); add("frequency", w.frequency); add("resolution", w.boot_resolution);
  add("connector", w.connector); add("orientation", w.orientation);
  table.append(el("tr", {}, el("th", { colspan: "2" }, t("applied"))));
  const active = (v.outputs || []).filter((o) => o.active);
  $("modelines").replaceChildren();
  if (!active.length) add("mode", t("no_output"));
  for (const o of active) {
    add("connector", o.connector + " (" + o.card.replace("/dev/dri/", "") + ")");
    add("mode", o.width + "x" + o.height);
    add("hsync", o.horizontal_khz + " kHz");
    add("vsync", o.vertical_hz + " Hz");
    add("scan", o.interlaced ? t("interlaced") : t("progressive"));
    $("modelines").append(el("div", { class: "modeline" }, o.connector + ": Modeline " + o.modeline));
  }
  if (v.framebuffer) add("framebuffer", v.framebuffer);

  // CPU.
  const cpu = s.cpu || {};
  $("cpu-total").textContent = (cpu.total ?? 0).toFixed(0) + "%";
  $("cpu-bar").style.width = (cpu.total || 0) + "%";
  $("load").textContent = t("load") + " " + (s.load || []).join(" ");
  $("cores").replaceChildren(...(cpu.cores || []).map((c, i) =>
    el("div", { class: "core" }, "#" + i + " " + c.toFixed(0) + "%", meter(c))));
  $("temps").replaceChildren(...(s.temperatures || []).filter((x) => !/amdgpu|radeon|nouveau/.test(x.sensor))
    .slice(0, 6).map((x) => el("div", {}, el("span", {}, x.sensor + (x.label ? " " + x.label : "")),
      el("span", {}, x.celsius + " °C"))));

  // GPU.
  $("gpus").replaceChildren(...(Array.isArray(s.gpus) ? s.gpus : []).map((g) => {
    const lines = [el("div", { class: "row" }, el("span", {}, g.name || g.slot), el("span", { class: "tag" }, g.driver))];
    if (g.busy != null) lines.push(el("div", { class: "dim" }, t("busy") + " " + g.busy + "%"), meter(g.busy));
    const facts = [];
    if (g.vram_total) facts.push(t("vram") + " " + bytes(g.vram_used) + " " + t("of") + " " + bytes(g.vram_total));
    if (g.clock) facts.push(t("clock") + " " + g.clock);
    if (g.celsius != null) facts.push(t("temp") + " " + g.celsius + " °C");
    if (g.watts != null) facts.push(t("power") + " " + g.watts + " W");
    if (facts.length) lines.push(el("div", { class: "dim" }, facts.join(" · ")));
    return el("div", { class: "item" }, ...lines);
  }));

  // Memoria.
  const m = s.memory || {};
  $("memory").replaceChildren(
    el("div", { class: "row" }, el("span", {}, bytes(m.used) + " " + t("of") + " " + bytes(m.total)),
      el("span", { class: "dim" }, m.total ? Math.round((100 * m.used) / m.total) + "%" : "")),
    meter(m.total ? (100 * m.used) / m.total : 0),
    m.swap_total ? el("div", { class: "dim" }, t("swap") + " " + bytes(m.swap_used) + " " + t("of") + " " + bytes(m.swap_total)) : "");
  // Armazenamento: cada disco montado.
  $("disks").replaceChildren(...(Array.isArray(s.disks) ? s.disks : []).map((d) => el("div", { class: "item" },
    el("div", { class: "row" }, el("span", {}, d.mount), el("span", { class: "dim" }, bytes(d.used) + " / " + bytes(d.total))),
    meter(d.total ? (100 * d.used) / d.total : 0))));

  // Rede.
  const net = Object.entries(s.network || {});
  $("network").replaceChildren(...net.map(([name, n]) => el("div", { class: "item" },
    el("div", { class: "row" }, el("span", {}, name), el("span", { class: "dim" }, (n.ipv4 || []).join(", "))),
    el("div", { class: "dim" }, "↓ " + rate(n.rx_bps) + " · ↑ " + rate(n.tx_bps)))),
  s.wifi ? el("div", { class: "dim" }, "Wi-Fi " + s.wifi.ssid + " · " + t("signal") + " " + s.wifi.signal + "%") : "");

  // Volume.
  const vol = s.volume && s.volume.percent;
  $("vol-value").textContent = vol == null ? "-" : vol + "%";
  if (vol != null && document.activeElement !== $("vol")) $("vol").value = vol;
  $("vol").disabled = vol == null;

  renderProcesses(s.processes || []);
}

// ── Processos ────────────────────────────────────────────────────
// A tabela tem colunas de largura fixa e as mesmas linhas a cada segundo
// (so o texto muda): o layout nao pula quando um nome comprido aparece ou
// some. O nome que nao cabe termina em "…" e, de tempos em tempos, rola
// como um letreiro ate o fim e volta (banner()).

const PROC_ROWS = 15;
let procCells = null;
let lastProcesses = [];
// A ordem: a coluna e o sentido (o clique no cabecalho troca; no mesmo
// cabecalho, inverte). Lembrada no navegador, quando da.
const PROC_COLUMNS = [
  { key: "pid", label: () => "PID", num: false, first: "asc" },
  { key: "name", label: () => t("name"), num: false, first: "asc" },
  { key: "cpu", label: () => t("cpu"), num: true, first: "desc" },
  { key: "mem_mb", label: () => t("mem"), num: true, first: "desc" },
];
let procSort = { key: "cpu", dir: "desc" };
try {
  const saved = JSON.parse(localStorage.getItem("fliperos-proc-sort") || "null");
  if (saved && PROC_COLUMNS.some((c) => c.key === saved.key) && (saved.dir === "asc" || saved.dir === "desc")) {
    procSort = saved;
  }
} catch (e) { /* sem armazenamento */ }

function sortProcesses(list) {
  const { key, dir } = procSort, sign = dir === "asc" ? 1 : -1;
  return list.slice().sort((a, b) => {
    const x = a[key], y = b[key];
    const order = typeof x === "string" ? x.localeCompare(y, undefined, { sensitivity: "base" }) : x - y;
    // Empate: o que mais usa CPU, depois o PID (a ordem nao fica pulando).
    return sign * order || b.cpu - a.cpu || a.pid - b.pid;
  });
}

function procHeader() {
  return el("tr", {}, ...PROC_COLUMNS.map((c) => {
    const active = procSort.key === c.key;
    const arrow = active ? (procSort.dir === "asc" ? " ▲" : " ▼") : "";
    const button = el("button", { type: "button", class: "sort" }, c.label() + arrow);
    button.addEventListener("click", () => {
      procSort = active ? { key: c.key, dir: procSort.dir === "asc" ? "desc" : "asc" } : { key: c.key, dir: c.first };
      try { localStorage.setItem("fliperos-proc-sort", JSON.stringify(procSort)); } catch (e) { /* sem armazenamento */ }
      $("procs").tHead.replaceChildren(procHeader());
      renderProcesses(lastProcesses);
    });
    const th = el("th", { class: c.num ? "num" : "", scope: "col" }, button);
    th.setAttribute("aria-sort", active ? (procSort.dir === "asc" ? "ascending" : "descending") : "none");
    return th;
  }));
}

function procTable() {
  const table = $("procs");
  const head = procHeader();
  const body = el("tbody");
  procCells = [];
  for (let i = 0; i < PROC_ROWS; i++) {
    const text = el("span");
    const cells = { pid: el("td"), name: el("td", { class: "name" }, el("span", { class: "clip" }, text)), text,
      cpu: el("td", { class: "num" }), mem: el("td", { class: "num" }) };
    cells.row = el("tr", {}, cells.pid, cells.name, cells.cpu, cells.mem);
    body.append(cells.row);
    procCells.push(cells);
  }
  table.replaceChildren(el("colgroup", {}, el("col", { class: "c-pid" }), el("col"), el("col", { class: "c-cpu" }),
    el("col", { class: "c-mem" })), el("thead", {}, head), body);
}

function setText(node, value) {
  if (node.textContent !== value) node.textContent = value;
}

function renderProcesses(all) {
  lastProcesses = all;
  const list = sortProcesses(all);
  if (!procCells || procCells.lang !== lang) {
    procTable();
    procCells.lang = lang;
  }
  procCells.forEach((cells, i) => {
    const p = list[i];
    cells.row.hidden = !p;
    if (!p) return;
    setText(cells.pid, String(p.pid));
    if (cells.text.textContent !== p.name) {
      // Outro nome nesta linha: o letreiro recomeca do inicio.
      cells.name.classList.remove("rolling");
      cells.text.textContent = p.name;
      cells.name.title = p.name;
    }
    setText(cells.cpu, p.cpu.toFixed(1) + "%");
    setText(cells.mem, p.mem_mb + " MB");
  });
}

// banner: os nomes que nao cabem rolam ate o fim (devagar, uns 40 px por
// segundo, parando nas pontas) e voltam ao "…".
function banner() {
  // Sem animacao pedida pelo sistema: fica so o "…" (o title tem o nome).
  if (window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  for (const cells of procCells || []) {
    const clip = cells.name.firstChild;
    if (cells.row.hidden || cells.name.classList.contains("rolling")) continue;
    const extra = clip.scrollWidth - clip.clientWidth;
    if (extra <= 2) continue;
    cells.text.style.setProperty("--shift", -extra + "px");
    cells.text.style.setProperty("--time", Math.max(3, extra / 40 + 2) + "s");
    cells.name.classList.add("rolling");
  }
}
document.addEventListener("animationend", (event) => {
  const cell = event.target.closest && event.target.closest("td.name");
  if (cell) cell.classList.remove("rolling");
});
setInterval(banner, 5000);

// ── Volume e logs ────────────────────────────────────────────────

async function volume(body) {
  const res = await api("/api/volume", { method: "POST", body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (data.percent != null) { $("vol").value = data.percent; $("vol-value").textContent = data.percent + "%"; }
}
$("vol-up").addEventListener("click", () => volume({ action: "up" }));
$("vol-down").addEventListener("click", () => volume({ action: "down" }));
$("vol-mute").addEventListener("click", () => volume({ action: "mute" }));
$("vol").addEventListener("change", () => volume({ set: Number($("vol").value) }));

async function loadLogs() {
  const res = await api("/api/logs");
  const data = await res.json();
  const select = $("log-name"), keep = select.value;
  select.replaceChildren(...data.logs.map((n) => el("option", { value: n }, n)));
  if (data.logs.includes(keep)) select.value = keep;
  await showLog();
}
async function showLog() {
  const name = $("log-name").value;
  if (!name) { $("log-text").textContent = ""; return; }
  const res = await api("/api/log?name=" + encodeURIComponent(name) + "&lines=300");
  const data = await res.json();
  const pre = $("log-text");
  pre.textContent = data.text || "";
  pre.scrollTop = pre.scrollHeight;
}
$("log-name").addEventListener("change", showLog);
$("log-refresh").addEventListener("click", showLog);

// ── Jogos: abrir e fechar no gabinete ────────────────────────────
// As pastas com jogos (as mesmas dos frontends), a busca e o botao de
// jogar. Abrir fecha o que esta na tela; quando o jogo fecha, volta o que
// estava (o frontend, o desktop ou o menu).

const GAMES_SHOWN = 300;
let allGames = [];

function toast(text) {
  const box = el("div", { class: "toast", role: "status" }, text);
  document.body.append(box);
  setTimeout(() => box.remove(), 4000);
}

async function loadSystems() {
  const res = await api("/api/systems");
  const data = await res.json();
  const select = $("system");
  let keep = select.value;
  try { keep = keep || localStorage.getItem("fliperos-system") || ""; } catch (e) { /* sem armazenamento */ }
  const rows = (data.systems || []).filter((s) => s.games > 0);
  select.replaceChildren(...rows.map((s) => el("option", { value: s.key }, s.name + " (" + s.games + ")")));
  if (rows.some((s) => s.key === keep)) select.value = keep;
  await loadGames();
}

async function loadGames() {
  const key = $("system").value;
  if (!key) { allGames = []; renderGames(); return; }
  try { localStorage.setItem("fliperos-system", key); } catch (e) { /* sem armazenamento */ }
  const res = await api("/api/games?system=" + encodeURIComponent(key));
  allGames = (await res.json()).games || [];
  renderGames();
}

function renderGames() {
  const query = $("game-search").value.trim().toLowerCase();
  const found = query ? allGames.filter((g) => g.toLowerCase().includes(query)) : allGames;
  const shown = found.slice(0, GAMES_SHOWN);
  $("games").replaceChildren(...shown.map((game) => {
    const button = el("button", { type: "button", "aria-label": t("play") + " " + game }, "▶ " + t("play"));
    button.addEventListener("click", () => play(game));
    return el("li", {}, el("span", { title: game }, game), button);
  }));
  $("games-note").textContent = !allGames.length ? t("no_games")
    : found.length > GAMES_SHOWN ? t("first").replace("%n", GAMES_SHOWN)
      : t("count").replace("%n", found.length);
}

async function play(game) {
  if (!confirm(t("confirm_launch").replace("%s", game))) return;
  const res = await api("/api/launch", { method: "POST", body: JSON.stringify({ system: $("system").value, game }) });
  const data = await res.json().catch(() => ({}));
  toast(res.ok ? t("launching").replace("%s", game) : data.error || res.statusText);
}

$("system").addEventListener("change", () => loadGames().catch(() => {}));
$("game-search").addEventListener("input", renderGames);
$("close-game").addEventListener("click", async () => {
  if (!confirm(t("confirm_close"))) return;
  await api("/api/close", { method: "POST", body: "{}" }).catch(() => {});
});

// ── Configuracoes ────────────────────────────────────────────────
// Os ajustes do Setup que podem mudar daqui (fliperos-setup --settings):
// cada mudanca grava na hora. Os grupos abertos ficam abertos.

const openGroups = new Set(["System"]);

async function loadSettings() {
  const res = await api("/api/settings");
  const rows = (await res.json()).settings || [];
  const groups = new Map();
  for (const row of rows) {
    if (!groups.has(row.group)) groups.set(row.group, []);
    groups.get(row.group).push(row);
  }
  const boxes = [];
  for (const [group, items] of groups) {
    const details = el("details", {}, el("summary", {}, t("group_" + group)));
    if (openGroups.has(group)) details.open = true;
    details.addEventListener("toggle", () => {
      details.open ? openGroups.add(group) : openGroups.delete(group);
    });
    for (const row of items) details.append(settingRow(row));
    boxes.push(details);
  }
  $("settings").replaceChildren(...boxes);
}

function settingRow(row) {
  const id = "set-" + row.key.replace(/[^a-z0-9]/gi, "-");
  let control;
  if (row.type === "choice") {
    control = el("select", { id }, ...row.options.map((o) => el("option", { value: o.value }, o.label)));
    control.value = row.value;
  } else {
    control = el("input", { id, type: "number", min: String(row.min), max: String(row.max), step: "1", value: row.value });
  }
  const about = el("div", { class: "dim" }, row.help);
  control.addEventListener("change", async () => {
    control.disabled = true;
    try {
      const res = await api("/api/settings", { method: "POST", body: JSON.stringify({ key: row.key, value: control.value }) });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.setting) {
        control.value = data.setting.value;
        about.textContent = data.setting.help;
        row.value = data.setting.value;
        toast(t("saved").replace("%s", row.label));
      } else {
        control.value = row.value;
        toast(data.error || res.statusText);
      }
    } finally {
      control.disabled = false;
    }
  });
  return el("div", { class: "setting" }, el("label", { for: id }, row.label), control, about);
}

// ── Downloads e tarefas ──────────────────────────────────────────
// O Downloader do Setup (o filtro do MAME ROM Cleaner escolhe o que baixar
// dos torrents): o andamento, os links e o comecar. O que leva minutos vira
// uma tarefa, com a etapa, a porcentagem e o log.

let dlState = {}, openLogs = new Set();

async function loadDownloader() {
  const res = await api("/api/downloader");
  dlState = await res.json();
  const pct = Number(dlState.pct || 0);
  $("dl-text").textContent = dlState.line || "";
  $("dl-pct").textContent = dlState.state === "downloading" ? pct + "%" : "";
  $("dl-bar").style.width = pct + "%";
  $("dl-filter").textContent = dlState.filter || "-";
  if (document.activeElement && document.activeElement.closest(".dl-kind")) return;
  $("dl-kinds").replaceChildren(...["roms", "chds"].map((kind) => {
    const name = dlState[kind + "_name"];
    const box = el("div", { class: "dl-kind" }, el("strong", {}, t("dl_" + kind)),
      el("div", { class: name ? "" : "dim" }, name ? name + " · " + (dlState[kind + "_sets"] || 0) + " sets" : t("dl_none")));
    if (name) {
      const remove = el("button", { type: "button", class: "ghost danger" }, t("dl_remove"));
      remove.addEventListener("click", async () => {
        if (!confirm(t("dl_remove_ask"))) return;
        const del = confirm(t("dl_delete_ask"));
        await api("/api/downloader", { method: "POST", body: JSON.stringify({ action: "remove", kind, delete: del }) });
        loadDownloader();
      });
      box.append(remove);
    } else {
      const input = el("input", { type: "text", placeholder: t("dl_paste"), autocomplete: "off" });
      const add = el("button", { type: "button" }, t("dl_add"));
      add.addEventListener("click", () => downloaderTask({ action: "add", kind, magnet: input.value.trim() }));
      box.append(el("div", { class: "row" }, input, add));
      if (dlState["default_" + kind]) {
        const def = el("button", { type: "button", class: "ghost" }, t("dl_default"));
        def.addEventListener("click", () => downloaderTask({ action: "add", kind }));
        box.append(def);
      }
    }
    return box;
  }));
}

async function downloaderTask(body) {
  const res = await api("/api/downloader", { method: "POST", body: JSON.stringify(body) });
  if (!res.ok) toast((await res.json().catch(() => ({}))).error || res.statusText);
  loadTasks();
  loadDownloader();
}
$("dl-start").addEventListener("click", () => downloaderTask({ action: "start" }));

async function loadTasks() {
  const res = await api("/api/tasks");
  const tasks = (await res.json()).tasks || [];
  const list = $("tasks");
  if (!tasks.length) { list.replaceChildren(el("li", { class: "dim" }, t("no_tasks"))); return; }
  const rows = [];
  for (const task of tasks) {
    const state = task.running ? (task.pct != null ? task.pct + "%" : "…")
      : task.rc === 0 ? "✓ " + t("task_ok") : "✗ " + t("task_fail") + " (" + task.rc + ")";
    const head = el("div", { class: "row" }, el("strong", {}, task.name),
      el("span", { class: task.running ? "dim" : task.rc === 0 ? "ok" : "fail" }, state));
    const item = el("li", {}, head);
    if (task.running) item.append(meter(task.pct || 0));
    const detail = task.error || task.step || task.last;
    if (detail) item.append(el("div", { class: "dim" }, detail));
    const actions = el("div", { class: "row" });
    const logButton = el("button", { type: "button", class: "ghost" }, t("show_log"));
    logButton.addEventListener("click", () => {
      openLogs.has(task.id) ? openLogs.delete(task.id) : openLogs.add(task.id);
      loadTasks();
    });
    actions.append(logButton);
    if (task.running) {
      const cancel = el("button", { type: "button", class: "ghost danger" }, t("cancel"));
      cancel.addEventListener("click", async () => {
        await api("/api/task/cancel", { method: "POST", body: JSON.stringify({ id: task.id }) });
        loadTasks();
      });
      actions.append(cancel);
    }
    item.append(actions);
    if (openLogs.has(task.id)) {
      const r = await api("/api/task?id=" + task.id);
      const pre = el("pre", { class: "log" }, (await r.json()).log || "");
      item.append(pre);
      requestAnimationFrame(() => { pre.scrollTop = pre.scrollHeight; });
    }
    rows.push(item);
  }
  list.replaceChildren(...rows);
}

// ── Trackball: o celular como mouse do gabinete ──────────────────
// O dedo na area rola a bola: os movimentos vao pelo WebSocket
// /api/trackball, juntados a cada quadro da tela. Soltando depois de um
// giro rapido, a bola continua rolando e freia aos poucos, como um trackball
// de fliperama; um toque a segura.

let ball = null, ballSend = { x: 0, y: 0 }, ballVel = { x: 0, y: 0 }, ballLast = null, ballSpin = 0;

function ballWs(msg) {
  if (ball && ball.readyState === 1) ball.send(JSON.stringify(msg));
}

function ballFlush() {
  const dx = Math.trunc(ballSend.x), dy = Math.trunc(ballSend.y);
  if (dx || dy) {
    ballWs({ m: [dx, dy] });
    ballSend.x -= dx;
    ballSend.y -= dy;
  }
}

function ballFrame(time) {
  // A inercia: anda com a velocidade e freia (a cada 16 ms, 6%).
  if (ballSpin && !ballLast) {
    const dt = Math.min(50, time - ballSpin);
    ballSpin = time;
    ballSend.x += ballVel.x * dt;
    ballSend.y += ballVel.y * dt;
    const friction = Math.pow(0.94, dt / 16);
    ballVel.x *= friction;
    ballVel.y *= friction;
    if (Math.abs(ballVel.x) + Math.abs(ballVel.y) < 0.01) ballSpin = 0;
  }
  ballFlush();
  if (ball) requestAnimationFrame(ballFrame);
}

function openBall() {
  const scheme = location.protocol === "https:" ? "wss://" : "ws://";
  ball = new WebSocket(scheme + location.host + "/api/trackball");
  ball.onopen = () => {
    $("ball").hidden = false;
    $("ball-open").hidden = true;
    $("ball-note").textContent = t("ball_on");
    requestAnimationFrame(ballFrame);
  };
  ball.onclose = () => {
    $("ball").hidden = true;
    $("ball-open").hidden = false;
    $("ball-note").textContent = t("term_off");
    ball = null;
  };
}

$("ball-open").addEventListener("click", openBall);
const pad = $("ball-pad");
pad.addEventListener("pointerdown", (ev) => {
  pad.setPointerCapture(ev.pointerId);
  pad.classList.add("active");
  ballSpin = 0;
  ballVel = { x: 0, y: 0 };
  ballLast = { x: ev.clientX, y: ev.clientY, t: ev.timeStamp };
});
pad.addEventListener("pointermove", (ev) => {
  if (!ballLast) return;
  const sens = Number($("ball-sens").value);
  const dx = (ev.clientX - ballLast.x) * sens, dy = (ev.clientY - ballLast.y) * sens;
  const dt = Math.max(1, ev.timeStamp - ballLast.t);
  ballSend.x += dx;
  ballSend.y += dy;
  // A velocidade (por ms), suavizada: e a que a bola leva ao soltar.
  ballVel.x = 0.6 * (dx / dt) + 0.4 * ballVel.x;
  ballVel.y = 0.6 * (dy / dt) + 0.4 * ballVel.y;
  ballLast = { x: ev.clientX, y: ev.clientY, t: ev.timeStamp };
});
function padUp(ev) {
  if (!ballLast) return;
  // Parado antes de soltar (mais de 60 ms): sem inercia.
  const still = ev.timeStamp - ballLast.t > 60;
  ballLast = null;
  pad.classList.remove("active");
  if ($("ball-spin").checked && !still) ballSpin = performance.now();
}
pad.addEventListener("pointerup", padUp);
pad.addEventListener("pointercancel", padUp);
pad.addEventListener("wheel", (ev) => {
  ev.preventDefault();
  ballWs({ m: [0, 0], w: ev.deltaY > 0 ? -1 : 1 });
}, { passive: false });
document.querySelectorAll(".ball-buttons button").forEach((button) => {
  const name = button.dataset.button;
  const up = () => {
    if (!button.classList.contains("down")) return;
    button.classList.remove("down");
    ballWs({ b: [name, 0] });
  };
  button.addEventListener("pointerdown", (ev) => {
    button.setPointerCapture(ev.pointerId);
    button.classList.add("down");
    ballWs({ b: [name, 1] });
  });
  button.addEventListener("pointerup", up);
  button.addEventListener("pointercancel", up);
  button.addEventListener("contextmenu", (ev) => ev.preventDefault());
});

// ── Terminal ─────────────────────────────────────────────────────
// O shell do gabinete pelo WebSocket /api/terminal, desenhado pelo xterm.js
// (carregado so quando o terminal abre). Teclas vao como binario; o tamanho,
// como texto {"resize": [colunas, linhas]}.

let term = null, termSocket = null, termFit = null;

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector('script[src="' + src + '"]')) return resolve();
    const s = el("script", { src });
    s.onload = resolve;
    s.onerror = () => reject(new Error(src));
    document.head.append(s);
  });
}

async function openTerminal() {
  $("term-note").textContent = t("term_connecting");
  if (!document.querySelector('link[href="xterm.css"]')) {
    document.head.append(el("link", { rel: "stylesheet", href: "xterm.css" }));
  }
  await loadScript("xterm.js");
  await loadScript("xterm-addon-fit.js");
  const box = $("term");
  box.hidden = false;
  if (!term) {
    term = new window.Terminal({
      cursorBlink: true, fontSize: 14, scrollback: 5000,
      fontFamily: '"JetBrains Mono", ui-monospace, Menlo, Consolas, monospace',
      theme: { background: "#191a21", foreground: "#f8f8f2", cursor: "#f8f8f2", selectionBackground: "#44475a",
        black: "#21222c", red: "#ff5555", green: "#50fa7b", yellow: "#f1fa8c", blue: "#bd93f9", magenta: "#ff79c6",
        cyan: "#8be9fd", white: "#f8f8f2", brightBlack: "#6272a4", brightRed: "#ff6e6e", brightGreen: "#69ff94",
        brightYellow: "#ffffa5", brightBlue: "#d6acff", brightMagenta: "#ff92df", brightCyan: "#a4ffff",
        brightWhite: "#ffffff" },
    });
    termFit = new window.FitAddon.FitAddon();
    term.loadAddon(termFit);
    term.open(box);
    term.onData((data) => {
      if (termSocket && termSocket.readyState === 1) termSocket.send(new TextEncoder().encode(data));
    });
    term.onResize(({ cols, rows }) => {
      if (termSocket && termSocket.readyState === 1) termSocket.send(JSON.stringify({ resize: [cols, rows] }));
    });
    new ResizeObserver(() => { if (!box.hidden) termFit.fit(); }).observe(box);
  }
  termFit.fit();
  const scheme = location.protocol === "https:" ? "wss://" : "ws://";
  termSocket = new WebSocket(scheme + location.host + "/api/terminal");
  termSocket.binaryType = "arraybuffer";
  termSocket.onopen = () => {
    $("term-note").textContent = t("term_on");
    $("term-open").hidden = true;
    $("term-close").hidden = false;
    termSocket.send(JSON.stringify({ resize: [term.cols, term.rows] }));
    term.focus();
  };
  termSocket.onmessage = (ev) => term.write(new Uint8Array(ev.data));
  termSocket.onclose = () => {
    $("term-note").textContent = t("term_off");
    $("term-open").hidden = false;
    $("term-close").hidden = true;
    termSocket = null;
  };
}

$("term-open").addEventListener("click", () => openTerminal().catch((e) => { $("term-note").textContent = String(e); }));
$("term-close").addEventListener("click", () => { if (termSocket) termSocket.close(); });

// ── Tela: o screenshot ───────────────────────────────────────────
// O PNG do que esta na tela do gabinete (/api/screenshot): o quadro do jogo
// ou do frontend pela camada OpenGL, o desktop pelo X. Em 4:3 como no tubo,
// ou do tamanho do quadro (um 2560x240 fica largo).

let shotUrl = null;
$("shot-take").addEventListener("click", async () => {
  $("shot-take").disabled = true;
  $("shot-note").textContent = t("shot_wait");
  try {
    const res = await api("/api/screenshot");
    if (!res.ok) {
      $("shot-note").textContent = (await res.json().catch(() => ({}))).error || res.statusText;
      return;
    }
    const blob = await res.blob();
    if (shotUrl) URL.revokeObjectURL(shotUrl);
    shotUrl = URL.createObjectURL(blob);
    const img = $("shot");
    img.onload = () => {
      const source = res.headers.get("X-Shot-Source") === "x11" ? t("shot_x11") : t("shot_gl");
      $("shot-note").textContent = t("shot_from").replace("%w", img.naturalWidth).replace("%h", img.naturalHeight)
        .replace("%s", source).replace("%t", new Date().toLocaleTimeString(lang === "pt" ? "pt-BR" : "en"));
    };
    img.src = shotUrl;
    img.hidden = false;
    const save = $("shot-save");
    save.href = shotUrl;
    save.download = "fliperos-" + new Date().toISOString().replace(/[:.]/g, "-") + ".png";
    save.hidden = false;
  } catch (e) {
    if (e.message !== "login") $("shot-note").textContent = String(e);
  } finally {
    $("shot-take").disabled = false;
  }
});
$("shot-tube").addEventListener("change", () => $("shot").classList.toggle("tube", $("shot-tube").checked));

// ── Arquivos: as pastas do gabinete ──────────────────────────────
// roms, bios, media e splashscreen de ~: entrar nas pastas, baixar,
// enviar (um de cada vez, com o progresso; tambem soltando na lista), criar
// pasta e apagar.

let fileRoot = "roms", filePath = "";

function filesQuery(path) {
  return "root=" + encodeURIComponent(fileRoot) + "&path=" + encodeURIComponent(path);
}
const joinPath = (...parts) => parts.filter(Boolean).join("/");

function stamp(seconds) {
  const d = new Date(seconds * 1000);
  return d.toLocaleDateString(lang === "pt" ? "pt-BR" : "en") + " " +
    d.toLocaleTimeString(lang === "pt" ? "pt-BR" : "en", { hour: "2-digit", minute: "2-digit" });
}

async function loadFiles(path) {
  const res = await api("/api/files?" + filesQuery(path == null ? filePath : path));
  if (!res.ok) { filePath = ""; return; }
  const data = await res.json();
  fileRoot = data.root;
  filePath = data.path;
  const select = $("file-root");
  if (select.options.length !== data.roots.length) {
    select.replaceChildren(...data.roots.map((r) => el("option", { value: r }, "~/" + r)));
  }
  select.value = fileRoot;
  // O caminho: cada pedaco leva de volta a ele.
  const parts = filePath ? filePath.split("/") : [];
  const crumbs = [el("button", { type: "button" }, "~/" + fileRoot)];
  crumbs[0].addEventListener("click", () => loadFiles(""));
  parts.forEach((part, i) => {
    const b = el("button", { type: "button" }, part);
    b.addEventListener("click", () => loadFiles(parts.slice(0, i + 1).join("/")));
    crumbs.push(el("span", {}, "/"), b);
  });
  $("crumbs").replaceChildren(...crumbs);
  $("file-up").disabled = !filePath;

  const table = $("files");
  const head = el("tr", {}, el("th", {}, t("name")), el("th", { class: "num" }, t("size")),
    el("th", { class: "fdate" }, t("modified")), el("th", {}, ""));
  const rows = data.entries.map((e) => {
    const target = joinPath(filePath, e.name);
    let link;
    if (e.dir) {
      link = el("button", { type: "button", title: e.name }, "📁 " + e.name);
      link.addEventListener("click", () => loadFiles(target));
    } else {
      link = el("a", { href: "/api/download?" + filesQuery(target), title: e.name, download: e.name }, "📄 " + e.name);
    }
    const del = el("button", { type: "button", class: "del", "aria-label": t("delete") + " " + e.name, title: t("delete") }, "🗑");
    del.addEventListener("click", async () => {
      if (!confirm(t("confirm_delete").replace("%s", e.name))) return;
      const r = await api("/api/delete", { method: "POST", body: JSON.stringify({ root: fileRoot, path: target }) });
      if (!r.ok) toast((await r.json().catch(() => ({}))).error || r.statusText);
      loadFiles();
    });
    return el("tr", {}, el("td", { class: "fname" }, link), el("td", { class: "num" }, e.dir ? "" : bytes(e.size)),
      el("td", { class: "fdate" }, stamp(e.mtime)), el("td", {}, del));
  });
  if (!rows.length) rows.push(el("tr", {}, el("td", { colspan: "4", class: "dim" }, t("empty_folder"))));
  table.replaceChildren(el("colgroup", {}, el("col"), el("col", { class: "c-size" }), el("col", { class: "c-date" }),
    el("col", { class: "c-del" })), el("thead", {}, head), el("tbody", {}, ...rows));
}

// sendFile: um arquivo pelo XMLHttpRequest (o fetch nao da o progresso do
// envio). Resolve com o status.
function sendFile(file, overwrite) {
  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/upload?" + filesQuery(filePath) + "&name=" + encodeURIComponent(file.name) +
      (overwrite ? "&overwrite=1" : ""));
    xhr.setRequestHeader("X-FliperOS", "1");
    xhr.upload.onprogress = (ev) => {
      if (ev.lengthComputable) {
        $("upload-status").textContent = t("uploading").replace("%s", file.name)
          .replace("%p", Math.round((100 * ev.loaded) / ev.total));
      }
    };
    xhr.onload = () => resolve(xhr.status);
    xhr.onerror = () => resolve(0);
    xhr.send(file);
  });
}

async function uploadFiles(files) {
  let sent = 0;
  for (const file of files) {
    let status = await sendFile(file, false);
    if (status === 409 && confirm(t("exists_overwrite").replace("%s", file.name))) status = await sendFile(file, true);
    if (status === 401) { showLogin(); return; }
    if (status === 200) sent++;
    else if (status !== 409) toast(file.name + ": " + (status || "network error"));
  }
  $("upload-status").textContent = t("uploaded").replace("%n", sent);
  loadFiles();
}

$("file-root").addEventListener("change", () => { fileRoot = $("file-root").value; loadFiles(""); });
$("file-up").addEventListener("click", () => loadFiles(filePath.split("/").slice(0, -1).join("/")));
$("file-input").addEventListener("change", () => {
  const files = Array.from($("file-input").files);
  $("file-input").value = "";
  if (files.length) uploadFiles(files);
});
$("file-mkdir").addEventListener("click", async () => {
  const name = prompt(t("folder_name"));
  if (!name) return;
  const r = await api("/api/mkdir", { method: "POST", body: JSON.stringify({ root: fileRoot, path: filePath, name }) });
  if (!r.ok) toast((await r.json().catch(() => ({}))).error || r.statusText);
  loadFiles();
});
const drop = $("file-drop");
drop.addEventListener("dragover", (ev) => { ev.preventDefault(); drop.classList.add("over"); });
drop.addEventListener("dragleave", () => drop.classList.remove("over"));
drop.addEventListener("drop", (ev) => {
  ev.preventDefault();
  drop.classList.remove("over");
  const files = Array.from(ev.dataTransfer.files || []);
  if (files.length) uploadFiles(files);
});

// ── O laco ───────────────────────────────────────────────────────

let timer = null;
// ── As paginas ───────────────────────────────────────────────────
// Frontend, Arquivos, Configuracoes, Status e Terminal: o endereco (#files)
// escolhe; sem ele, a ultima aberta (lembrada no navegador, quando da).

const PAGES = ["frontend", "files", "settings", "status", "terminal"];
let page = "frontend";

function showPage(name) {
  if (!PAGES.includes(name)) name = "frontend";
  page = name;
  // data-off: um cartao desligado por enquanto (o trackball).
  document.querySelectorAll("main > section[data-page]").forEach((s) => {
    s.hidden = s.dataset.page !== name || s.hasAttribute("data-off");
  });
  document.querySelectorAll(".pages a").forEach((a) => {
    if (a.dataset.page === name) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  try { localStorage.setItem("fliperos-page", name); } catch (e) { /* sem armazenamento */ }
  // O que cada pagina busca ao aparecer.
  if (name === "files") {
    loadFiles().catch(() => {});
    loadDownloader().catch(() => {});
    loadTasks().catch(() => {});
  } else if (name === "settings") {
    loadSettings().catch(() => {});
  } else if (name === "status") {
    loadLogs().catch(() => {});
  } else if (name === "terminal" && termFit) {
    requestAnimationFrame(() => termFit.fit());
  }
  if (name === "frontend") drawFps();
}

window.addEventListener("hashchange", () => showPage(location.hash.slice(1)));

function firstPage() {
  let saved = "";
  try { saved = localStorage.getItem("fliperos-page") || ""; } catch (e) { /* sem armazenamento */ }
  return location.hash.slice(1) || saved || "frontend";
}

let ticks = 0;
async function tick() {
  try {
    const res = await api("/api/status");
    render(await res.json());
    $("offline").hidden = true;
    // Os downloads e as tarefas, a cada 3 s.
    // Os downloads e as tarefas, a cada 3 s, com a pagina Arquivos aberta.
    if (ticks++ % 3 === 0 && page === "files") {
      loadDownloader().catch(() => {});
      loadTasks().catch(() => {});
    }
  } catch (e) {
    if (e.message !== "login") $("offline").hidden = false;
  }
}
function start() {
  $("login").hidden = true;
  $("app").hidden = false;
  stop();
  tick();
  loadSystems().catch(() => {});
  loadFiles("").catch(() => {});
  showPage(firstPage());
  timer = setInterval(tick, 1000);
}
function stop() {
  if (timer) clearInterval(timer);
  timer = null;
}

translate();
fetch("/api/me", { credentials: "same-origin" }).then((res) => (res.ok ? start() : showLogin())).catch(showLogin);
