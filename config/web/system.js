// Sistema: o status (o video, a CPU, a GPU, a memoria, os discos e a rede,
// do /api/status de cada segundo), os processos e os logs, os ajustes, o
// modo lab e o terminal.
"use strict";

// O anel de um medidor (CPU, memoria): a cor pelo quanto esta usado.
function ringSvg(pct) {
  const p = Math.max(0, Math.min(100, pct || 0)), r = 26, len = 2 * Math.PI * r;
  const color = p > 90 ? "var(--red)" : p > 70 ? "var(--orange)" : "var(--green)";
  return '<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="' + r + '" class="ring-base"/>' +
    '<circle cx="32" cy="32" r="' + r + '" class="ring-fill" stroke="' + color + '" stroke-dasharray="' + (len * p / 100).toFixed(1) +
    " " + len.toFixed(1) + '" transform="rotate(-90 32 32)"/><text x="32" y="37" text-anchor="middle">' + Math.round(p) + "%</text></svg>";
}

// Uma barra com a cor pelo quanto esta usado.
function bar(pct) {
  const p = Math.max(0, Math.min(100, pct || 0));
  const box = el("div", { class: "sbar " + (p > 90 ? "hot" : p > 70 ? "warn" : "") }, el("i"));
  box.firstChild.style.width = p + "%";
  return box;
}

// O nome de gente de cada sensor e o limite padrao da peca, quando o sensor
// nao diz o dele.
function sensorName(x) {
  const s = x.sensor;
  if (/coretemp|k10temp|zenpower|cpu/.test(s)) return ["CPU", x.label || s, 95];
  if (/amdgpu|radeon|nouveau|nvidia/.test(s)) return ["GPU", x.label || s, 95];
  if (/nvme|drivetemp|sata/.test(s)) return [t("st_disk"), x.label || s, 70];
  if (/iwl|rtw|ath|mt7|wifi/.test(s)) return ["Wi-Fi", x.label || s, 90];
  if (/acpitz|pch|it87|nct/.test(s)) return [t("st_board"), x.label || s, 90];
  return [s, x.label, 90];
}

// Os termometros: feitos uma vez por sensor; a coluna sobe e desce suave.
const therms = new Map();
function renderTemps(rows) {
  const box = $("temps"), seen = new Set();
  rows.slice(0, 10).forEach((x, i) => {
    const key = x.sensor + "|" + x.label + "|" + i;
    seen.add(key);
    let th = therms.get(key);
    const [name, label, fallback] = sensorName(x);
    const limit = x.max || fallback, top = Math.max(110, limit + 10);
    if (!th) {
      th = { node: el("div", { class: "therm" }, el("div", { class: "therm-tube" }, el("div", { class: "glass" }, el("div", { class: "fill" })),
        el("div", { class: "bulb" }), el("div", { class: "limit" })), el("div", { class: "deg" }), el("b", {}, name), el("small", {}, label)) };
      th.fill = th.node.querySelector(".fill");
      th.deg = th.node.querySelector(".deg");
      th.limit = th.node.querySelector(".limit");
      box.append(th.node);
      therms.set(key, th);
    }
    const ratio = x.celsius / limit;
    const level = ratio < .55 ? "t1" : ratio < .75 ? "t2" : ratio < .88 ? "t3" : "t4";
    th.node.className = "therm " + level;
    th.fill.style.height = Math.min(100, (x.celsius / top) * 100) + "%";
    th.limit.style.bottom = "calc(30px + " + (limit / top) + " * (100% - 30px))";
    th.deg.textContent = Math.round(x.celsius) + "°";
    th.node.title = name + " " + label + ": " + x.celsius + " °C (" + t("st_limit") + " " + limit + " °C)";
  });
  for (const [key, th] of therms) if (!seen.has(key)) { th.node.remove(); therms.delete(key); }
  $("temps").closest(".dcard").hidden = !rows.length;
}

// Uma linha de fato: o rotulo e o valor.
const kv = (label, value) => el("div", { class: "kv" }, el("span", {}, label), el("b", {}, value));

function renderStatus(s) {
  // O video no tubo: os kHz no mostrador, a faixa (15, 25 ou 31 kHz) e o modo.
  const v = s.video || {}, w = v.wanted || {};
  const out = (v.outputs || []).find((o) => o.active);
  led($("st-khz"), out ? Number(out.horizontal_khz).toFixed(2) : "--.--");
  const khz = out ? Number(out.horizontal_khz) : 0;
  const band = !out ? "" : khz < 20 ? "15 kHz" : khz < 28 ? "25 kHz" : "31 kHz";
  $("st-band").textContent = band;
  $("st-band").className = "band " + (khz < 20 ? "b15" : khz < 28 ? "b25" : "b31");
  $("st-mode").replaceChildren(...(out ? [
    el("span", { class: "chip-s" }, icon("g-screenh"), out.width + "×" + out.height),
    el("span", { class: "chip-s" }, Number(out.vertical_hz).toFixed(2) + " Hz"),
    el("span", { class: "chip-s" }, out.interlaced ? t("interlaced") : t("progressive")),
    el("span", { class: "chip-s" }, icon("g-ext"), out.connector + " · " + out.card.replace("/dev/dri/", "")),
  ] : [el("span", { class: "dim" }, t("no_output"))]));
  $("modelines").replaceChildren(...(v.outputs || []).filter((o) => o.active).map((o) =>
    el("div", { class: "modeline" }, o.connector + ": Modeline " + o.modeline)));
  const table = $("video-table");
  table.replaceChildren(...[["monitor", w.monitor], ["frequency", w.frequency], ["resolution", w.boot_resolution],
    ["connector", w.connector], ["orientation", w.orientation], ["framebuffer", v.framebuffer]]
    .map(([k, val]) => el("tr", {}, el("th", {}, t(k)), el("td", {}, val || "-"))));

  // CPU: o anel, a carga e os nucleos em barras que sobem e descem.
  const cpu = s.cpu || {};
  $("cpu-ring").innerHTML = ringSvg(cpu.total);
  $("cpu-total").textContent = (cpu.total ?? 0).toFixed(0) + "%";
  $("load").textContent = t("load") + " " + (s.load || []).join(" ");
  const cores = $("cores"), list = cpu.cores || [];
  if (cores.children.length !== list.length) {
    cores.replaceChildren(...list.map((_, i) => el("div", { class: "core" }, el("div", { class: "col" }, el("i")), el("small", {}, "#" + i))));
  }
  list.forEach((c, i) => {
    const bar = cores.children[i].querySelector("i");
    bar.style.height = Math.max(2, c) + "%";
    bar.className = c > 90 ? "hot" : c > 70 ? "warn" : "";
    cores.children[i].title = "#" + i + " " + c.toFixed(0) + "%";
  });

  renderTemps(s.temperatures || []);

  // GPU: o nome, o driver, e o que a placa diz (uso, VRAM, relogio, consumo).
  $("gpus").replaceChildren(...(Array.isArray(s.gpus) ? s.gpus : []).map((g) => {
    const box = el("div", { class: "gpu" }, el("div", { class: "gpu-head" }, el("b", {}, g.name || g.slot), el("span", { class: "tag" }, g.driver)));
    if (g.busy != null) box.append(kv(t("busy"), g.busy + "%"), bar(g.busy));
    if (g.vram_total) box.append(kv(t("vram"), bytes(g.vram_used) + " " + t("of") + " " + bytes(g.vram_total)), bar((100 * g.vram_used) / g.vram_total));
    if (g.clock) box.append(kv(t("clock"), g.clock));
    if (g.celsius != null) box.append(kv(t("temp"), g.celsius + " °C"));
    if (g.watts != null) box.append(kv(t("power"), g.watts + " W"));
    return box;
  }));

  // Memoria: o anel e a troca.
  const m = s.memory || {};
  const used = m.total ? (100 * m.used) / m.total : 0;
  const ring = el("div", { class: "ring" });
  ring.innerHTML = ringSvg(used);
  $("memory").replaceChildren(el("div", { class: "ring-row" }, ring, el("div", { class: "ring-text" },
    el("b", {}, bytes(m.used)), el("span", { class: "dim" }, t("of") + " " + bytes(m.total)))),
  m.swap_total ? el("div", {}, kv(t("swap"), bytes(m.swap_used) + " " + t("of") + " " + bytes(m.swap_total)),
    bar((100 * m.swap_used) / m.swap_total)) : "");

  // Os discos montados.
  $("disks").replaceChildren(...(Array.isArray(s.disks) ? s.disks : []).map((d) => el("div", { class: "disk" },
    el("div", { class: "disk-head" }, icon("px-disk"), el("b", {}, d.mount), el("span", { class: "dim" }, bytes(d.used) + " / " + bytes(d.total))),
    bar(d.total ? (100 * d.used) / d.total : 0))));

  // A rede: cada placa, os enderecos, o trafego e o sinal do Wi-Fi.
  const net = Object.entries(s.network || {});
  $("network").replaceChildren(...net.map(([name, n]) => el("div", { class: "nic" },
    el("div", { class: "nic-head" }, icon(/^w/.test(name) ? "px-network" : "px-link"), el("b", {}, name),
      el("span", { class: "dim" }, (n.ipv4 || []).join(", ") || "-")),
    el("div", { class: "nic-rates" }, el("span", { class: "down" }, "↓ " + rate(n.rx_bps)), el("span", { class: "up" }, "↑ " + rate(n.tx_bps))))),
  s.wifi ? el("div", { class: "wifi" }, el("span", { class: "signal", "data-bars": String(Math.ceil((s.wifi.signal || 0) / 25)) },
    el("i"), el("i"), el("i"), el("i")), el("b", {}, s.wifi.ssid), el("span", { class: "dim" }, t("signal") + " " + s.wifi.signal + "%")) : "");

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

// ── Configuracoes ────────────────────────────────────────────────
// Os ajustes do Setup que podem mudar daqui (fliperos-setup --settings):
// cada mudanca grava na hora. Os grupos abertos ficam abertos.

const openGroups = new Set(["Video"]);
// Os icones do Setup em cada grupo e em cada ajuste (os do carrossel no tubo).
const GROUP_ICONS = { System: "px-system", Video: "px-video", Audio: "px-audio", Power: "px-power", Services: "px-services",
  "Interlaced hacks": "px-mode480", Colour: "px-colour", Scanlines: "px-scanlines", "GunCon 2": "px-guncon",
  "Live screen": "px-outputs" };
const SETTING_ICONS = [["monitor", "px-video"], ["resolution", "px-resolution"], ["video.previous", "px-reset"],
  ["cabinet_name", "px-cabinetname"], ["launcher", "px-frontend"], ["latency", "px-latency"], ["debug", "px-debug"],
  ["menu_sounds", "px-audio"], ["stream_audio", "px-audio"], ["stream_quality", "px-video"], ["marquee_overlay", "px-outputs"],
  ["orientation", "px-orientation"], ["splash", "px-desktop"], ["mm_games", "px-outputs"], ["osd", "px-layout"],
  ["audio_card", "px-audio"], ["mame_latency", "px-latency"], ["audio.", "px-mixer"], ["power.", "px-power"],
  ["service.", "px-services"], ["mode480.", "px-mode480"], ["color.", "px-colour"], ["scanlines", "px-scanlines"],
  ["scanline.", "px-scanlines"], ["gun_flash", "px-guncon"], ["gun_offscreen_reload", "px-guncon"], ["gun.", "px-guncon"]];
const settingIcon = (key) => (SETTING_ICONS.find(([k]) => key === k || (k.endsWith(".") && key.startsWith(k))) || [0, "px-setup"])[1];

// A ordem dos grupos, a do Setup no tubo: o video e as telas dele, o som, os
// controles, a rede, a tela ao vivo, o sistema e, por ultimo, desligar. Os
// grupos que nao vem do --settings (Geometria, Rede, Senha, Novidades) entram
// no lugar deles; um grupo novo do Setup que nao esteja aqui vai para o fim,
// antes de Power.
const SETTINGS_ORDER = ["Video", "Geometry", "Colour", "Scanlines", "Interlaced hacks", "Audio", "GunCon 2",
  "Network", "Live screen", "System", "Password", "Services", "Version", "Whatsnew", "Power"];

async function loadSettings() {
  const res = await api("/api/settings");
  const rows = (await res.json()).settings || [];
  const groups = new Map();
  for (const row of rows) {
    if (!groups.has(row.group)) groups.set(row.group, []);
    groups.get(row.group).push(row);
  }
  const boxes = new Map();
  for (const [group, items] of groups) {
    const details = el("details", { class: "box-" + group.toLowerCase().replace(/[^a-z0-9]+/g, "-") },
      el("summary", {}, icon(GROUP_ICONS[group] || "px-setup"), t("group_" + group)));
    if (openGroups.has(group)) details.open = true;
    details.addEventListener("toggle", () => {
      details.open ? openGroups.add(group) : openGroups.delete(group);
    });
    if (group === "Interlaced hacks") details.append(...mode480Rows(items));
    else for (const row of items) details.append(settingRow(row));
    boxes.set(group, details);
  }
  const [geometry, network] = await Promise.all([geometryBox().catch(() => null), wifiBox().catch(() => null)]);
  if (geometry) boxes.set("Geometry", geometry);
  if (network) boxes.set("Network", network);
  boxes.set("Password", passwordBox());
  boxes.set("Version", versionBox());
  boxes.set("Whatsnew", whatsnewBox());
  const known = SETTINGS_ORDER.filter((name) => boxes.has(name));
  const extra = [...boxes.keys()].filter((name) => !SETTINGS_ORDER.includes(name));
  const order = [...known.filter((name) => name !== "Power"), ...extra, ...known.filter((name) => name === "Power")];
  $("settings").replaceChildren(...order.map((name) => boxes.get(name)));
}

// settingsBox: um grupo dos que nao vem do --settings (Geometria, Rede...),
// que tambem lembra se estava aberto.
function settingsBox(name, iconName, ...content) {
  const details = el("details", { class: "box-" + name.toLowerCase() },
    el("summary", {}, icon(iconName), t("group_" + name)), ...content);
  if (openGroups.has(name)) details.open = true;
  details.addEventListener("toggle", () => { details.open ? openGroups.add(name) : openGroups.delete(name); });
  return details;
}

// Setup > Network: as interfaces, as redes ao alcance (so ao pedir: a busca
// leva uns segundos) e conectar com a senha.
async function wifiBox() {
  const res = await api("/api/wifi");
  const devices = (await res.json()).devices || [];
  const wifi = devices.filter((d) => d.type === "wifi");
  const list = el("div", { class: "nics" }, ...devices.map((d) => el("div", { class: "nic-row" },
    icon(d.type === "wifi" ? "px-network" : "px-link"), el("b", {}, d.device),
    el("span", { class: "tag " + (d.state === "connected" ? "on" : "") }, d.state),
    el("span", { class: "dim" }, [d.connection, d.ip].filter(Boolean).join(" · ")))));
  const nets = el("div", { class: "wifi-nets" });
  const scan = el("button", { type: "button", class: "btn ghost" }, icon("px-scan"), t("wifi_scan"));
  scan.disabled = !wifi.length;
  scan.addEventListener("click", async () => {
    scan.disabled = true;
    nets.replaceChildren(el("div", { class: "dim" }, t("wifi_scanning")));
    try {
      const r = await api("/api/wifi?scan=1");
      const found = (await r.json()).networks || [];
      nets.replaceChildren(found.length ? el("div", { class: "dim" }, t("wifi_nets")) : el("div", { class: "dim" }, t("wifi_nonet")),
        ...found.map((n) => {
          const b = el("button", { type: "button", class: "wifi-net" }, wifiBars(Number(n.signal)), el("b", {}, n.ssid),
            el("span", { class: "dim" }, n.security || t("wifi_open")));
          b.addEventListener("click", () => wifiConnect(n.device, n.ssid, !!n.security, false));
          return b;
        }));
    } finally {
      scan.disabled = false;
    }
  });
  const hidden = el("button", { type: "button", class: "btn ghost" }, icon("px-add"), t("wifi_hidden"));
  hidden.disabled = !wifi.length;
  hidden.addEventListener("click", async () => {
    const ssid = await ask({ title: t("wifi_hidden"), text: t("wifi_name"), input: "" });
    if (ssid) wifiConnect(wifi[0].device, ssid, true, true);
  });
  return settingsBox("Network", "px-network", el("div", { class: "setting" }, list,
    wifi.length ? el("div", { class: "row start" }, scan, hidden) : el("div", { class: "dim" }, t("wifi_none")), nets));
}

// wifiBars: o sinal em 4 barrinhas (como o do Status).
function wifiBars(signal) {
  const bars = signal >= 75 ? 4 : signal >= 50 ? 3 : signal >= 25 ? 2 : 1;
  return el("span", { class: "signal", "data-bars": String(bars), title: signal + "%" }, el("i"), el("i"), el("i"), el("i"));
}

async function wifiConnect(device, ssid, secured, isHidden) {
  let password = "";
  if (secured) {
    password = await ask({ title: ssid, text: t("wifi_pass").replace("%s", ssid), yes: t("wifi_connect"), input: "" });
    if (password === null) return;
  }
  toast(ssid + "…");
  const r = await api("/api/wifi", { method: "POST", body: JSON.stringify({ device, ssid, password, hidden: isHidden }) });
  toast(t(r.ok ? "wifi_ok" : "wifi_fail").replace("%s", ssid), r.ok ? "ok" : "bad");
  if (r.ok) loadSettings().catch(() => {});
}

// Setup > System > Password: a de agora e a nova duas vezes.
function passwordBox() {
  const field = (key, auto) => el("input", { type: "password", autocomplete: auto, "aria-label": t(key), placeholder: t(key) });
  const current = field("pw_current", "current-password"), first = field("pw_new", "new-password"), again = field("pw_again", "new-password");
  const save = el("button", { type: "submit", class: "btn" }, icon("px-password"), t("pw_save"));
  const form = el("form", { class: "setting pw" }, current, first, again, el("div", { class: "row start" }, save),
    el("div", { class: "dim" }, t("pw_note")));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (first.value !== again.value) return toast(t("pw_diff"), "bad");
    if (first.value.length < 4) return toast(t("pw_short"), "bad");
    save.disabled = true;
    try {
      const r = await api("/api/password", { method: "POST", body: JSON.stringify({ current: current.value, password: first.value }) });
      const data = await r.json().catch(() => ({}));
      toast(r.ok ? t("pw_done") : r.status === 403 ? t("pw_wrong") : (data.error || r.statusText), r.ok ? "ok" : "bad");
      if (r.ok) form.reset();
    } finally {
      save.disabled = false;
    }
  });
  return settingsBox("Password", "px-password", form);
}

// Cloud backup (config/fliperos-cloud): os hi-scores, saves e configuracoes
// numa nuvem pelo rclone. Google Drive e Dropbox pelo login do site (o
// endereco da pagina que nao abre volta colado aqui); WebDAV, SFTP e Mega
// com usuario e senha. Sincroniza ao apertar e, ligado, ao fechar cada jogo.
const CLOUD_FIELDS = { webdav: ["url", "user", "pass"], sftp: ["host", "port", "user", "pass"], mega: ["user", "pass"] };
async function cloudPage() {
  const state = await (await api("/api/cloud")).json();
  const reload = () => loadCloud().catch(() => {});
  const post = async (body) => {
    const r = await api("/api/cloud", { method: "POST", body: JSON.stringify(body) });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) toast(data.error || r.statusText, "bad");
    return r.ok ? data : null;
  };
  const content = el("div", { class: "stack" });
  if (!state.installed) {
    const install = el("button", { type: "button", class: "btn" }, icon("px-install"), t("cl_install"));
    install.addEventListener("click", async () => {
      if (await post({ action: "install" })) { toast(t("inst_started")); loadTasks().catch(() => {}); }
    });
    content.append(el("div", {}, t("cl_missing")), el("div", { class: "row start" }, install));
  } else if (!state.remote) {
    const kind = el("select", { "aria-label": t("cl_provider") },
      // O Google Drive so com o cliente do FliperOS (Entrar com o Google).
      ...["drive", "dropbox", "webdav", "sftp", "mega"].filter((k) => k !== "drive" || state.device)
        .map((k) => el("option", { value: k }, t("cl_" + k))));
    const area = el("div", { class: "stack" });
    let polling = null;
    const draw = () => {
      if (polling) { clearTimeout(polling); polling = null; }
      if (kind.value === "drive") {
        // Entrar com o Google, como numa smart TV: o QR code e o codigo; a
        // espera roda no gabinete, e o painel so le o estado a cada 2 s.
        const go = el("button", { type: "button", class: "btn" }, icon("px-password"), t("cl_google"));
        const box = el("div", { class: "stack google-wait", hidden: "" });
        const cancel = el("button", { type: "button", class: "btn ghost" }, icon("px-cancel"), t("cancel"));
        let shown = "";
        const show = (s) => {
          if (s.state === "ok") { toast(t("cl_connected").replace("%s", s.account || "Google Drive"), "ok"); reload(); return true; }
          if (s.state === "denied" || s.state === "error" || s.state === "stopped") {
            box.replaceChildren(el("div", { class: "bad" }, s.error || t("cl_google_stopped")));
            go.hidden = false;
            return true;
          }
          if (s.state === "syncing") {
            box.replaceChildren(el("div", {}, t("cl_google_syncing").replace("%s", s.account || "")));
          } else if (s.code && s.code !== shown) {
            shown = s.code;
            const qr = el("div", { class: "qr" });
            qr.innerHTML = s.qr || "";
            box.replaceChildren(el("div", { class: "row start google-row" }, qr, el("div", { class: "stack" },
              el("div", {}, t("cl_code_step1")),
              el("a", { class: "btn ghost", href: s.url, target: "_blank", rel: "noopener" }, icon("px-link"), s.url.replace(/^https?:\/\//, "")),
              el("div", {}, t("cl_code_step2")), el("div", { class: "device-code" }, s.code),
              el("div", { class: "dim" }, t("cl_code_wait")), cancel)));
          }
          box.hidden = false;
          go.hidden = true;
          return false;
        };
        const watch = async () => {
          const r = await api("/api/cloud", { method: "POST", body: JSON.stringify({ action: "google-status" }) }).catch(() => null);
          const s = r && r.ok ? await r.json() : null;
          if (s && show(s)) return;
          if ($("cloud-page").contains(box)) polling = setTimeout(watch, 2000);
        };
        go.addEventListener("click", async () => {
          go.disabled = true;
          const s = await post({ action: "google-start" });
          go.disabled = false;
          if (s && !show(s)) polling = setTimeout(watch, 2000);
        });
        cancel.addEventListener("click", async () => {
          if (polling) clearTimeout(polling);
          await post({ action: "google-cancel" });
          box.hidden = true;
          go.hidden = false;
          shown = "";
        });
        area.replaceChildren(el("div", { class: "dim" }, t("cl_code_help")), go, box);
      } else if (CLOUD_FIELDS[kind.value]) {
        const inputs = CLOUD_FIELDS[kind.value].map((f) => el("input", { type: f === "pass" ? "password" : "text",
          autocomplete: "off", "aria-label": t("cl_f_" + f), placeholder: t("cl_f_" + f) }));
        const save = el("button", { type: "submit", class: "btn" }, icon("px-save"), t("cl_save"));
        const form = el("form", { class: "stack" }, ...inputs, el("div", { class: "row start" }, save));
        form.addEventListener("submit", async (event) => {
          event.preventDefault();
          save.disabled = true;
          const fields = Object.fromEntries(CLOUD_FIELDS[kind.value].map((f, i) => [f, inputs[i].value.trim()]));
          try { if (await post({ action: "remote", kind: kind.value, fields })) { toast(t("cl_saved"), "ok"); reload(); } }
          finally { save.disabled = false; }
        });
        area.replaceChildren(form);
      } else {
        const start = el("button", { type: "button", class: "btn" }, icon("px-password"), t("cl_signin"));
        const answer = el("input", { type: "text", autocomplete: "off", "aria-label": t("cl_paste"), placeholder: t("cl_paste") });
        const done = el("button", { type: "submit", class: "btn" }, icon("px-ok"), t("cl_save"));
        const form = el("form", { class: "stack", hidden: "" }, el("div", { class: "dim" }, t("cl_paste_help")), answer,
          el("div", { class: "row start" }, done));
        start.addEventListener("click", async () => {
          // A aba abre ja no clique (o navegador bloqueia a que abre depois de esperar).
          const tab = window.open("about:blank", "_blank");
          start.disabled = true;
          try {
            const data = await post({ action: "authorize", kind: kind.value });
            if (data && data.url) {
              if (tab) tab.location = data.url; else window.open(data.url, "_blank");
              form.hidden = false;
              answer.focus();
            } else if (tab) tab.close();
          } finally { start.disabled = false; }
        });
        form.addEventListener("submit", async (event) => {
          event.preventDefault();
          done.disabled = true;
          try { if (await post({ action: "authorized", kind: kind.value, answer: answer.value.trim() })) { toast(t("cl_saved"), "ok"); reload(); } }
          finally { done.disabled = false; }
        });
        area.replaceChildren(el("div", { class: "row start" }, start), form);
      }
    };
    kind.addEventListener("change", draw);
    draw();
    content.append(el("label", { class: "row start" }, el("span", {}, t("cl_provider")), kind), area);
  } else {
    const checks = ["hiscores", "saves", "config"].map((w) => {
      const box = el("input", { type: "checkbox", "aria-label": t("cl_w_" + w) });
      box.checked = state.what.includes(w);
      box.addEventListener("change", () => post({ action: "what", what: checks.filter((c) => c.box.checked).map((c) => c.w) }));
      return { w, box, label: el("label", { class: "row start" }, box, el("span", {}, t("cl_w_" + w))) };
    });
    const auto = el("select", { "aria-label": t("cl_auto") }, el("option", { value: "on" }, t("ra_on")), el("option", { value: "off" }, t("ra_off")));
    auto.value = state.auto ? "on" : "off";
    auto.addEventListener("change", () => post({ action: "auto", on: auto.value === "on" }));
    const run = (direction, label, glyph) => {
      const b = el("button", { type: "button", class: direction === "both" ? "btn" : "btn ghost" }, icon(glyph), t(label));
      b.addEventListener("click", () => startTask("/api/cloud", { action: "sync", direction }));
      return b;
    };
    const forget = el("button", { type: "button", class: "btn ghost" }, icon("px-remove"), t("cl_forget"));
    forget.addEventListener("click", async () => {
      if (!(await ask({ title: t("group_Cloud"), text: t("cl_forget_ask"), yes: t("cl_forget") }))) return;
      if (await post({ action: "forget" })) reload();
    });
    const last = state.last ? new Date(state.last * 1000).toLocaleString() + (state.result === "failed" ? " · " + t("cl_failed") : "") : t("cl_never");
    content.append(el("div", {}, state.remote === "drive" && state.account ? t("cl_connected").replace("%s", state.account)
      : t("cl_account").replace("%s", t("cl_" + state.remote) || state.remote)),
      ...checks.map((c) => c.label), el("label", { class: "row start" }, el("span", {}, t("cl_auto")), auto),
      el("div", { class: "row start" }, run("both", "cl_sync", "px-reset"), run("push", "cl_push", "px-up"), run("pull", "cl_pull", "px-install")),
      el("div", { class: "dim" }, t("cl_last").replace("%s", last)), el("div", { class: "row start" }, forget));
  }
  content.append(el("div", { class: "dim" }, t("cl_note")));
  return content;
}

// Setup > Games > RetroAchievements: entrar com a conta do site (so o token
// fica no gabinete), ligar as conquistas e o modo hardcore, sair.
async function cheevosPage() {
  const state = await (await api("/api/cheevos")).json();
  const post = async (body) => {
    const r = await api("/api/cheevos", { method: "POST", body: JSON.stringify(body) });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) toast(data.error || r.statusText, "bad");
    return r.ok;
  };
  const reload = () => loadCheevos().catch(() => {});
  const content = el("div", { class: "stack" });
  if (state.user) {
    const onOff = (key, value) => {
      const select = el("select", { "aria-label": t(key) }, el("option", { value: "on" }, t("ra_on")), el("option", { value: "off" }, t("ra_off")));
      select.value = value ? "on" : "off";
      select.addEventListener("change", async () => { if (await post({ action: key, on: select.value === "on" })) reload(); });
      return el("label", { class: "row start" }, el("span", {}, t("ra_" + key)), select);
    };
    const out = el("button", { type: "button", class: "btn ghost" }, icon("px-power"), t("ra_logout"));
    out.addEventListener("click", async () => {
      if (!(await ask({ title: "RetroAchievements", text: t("ra_logout_ask").replace("%s", state.user), yes: t("ra_logout") }))) return;
      if (await post({ action: "logout" })) reload();
    });
    // A Web API Key da conta: com ela o frontend mostra as conquistas de cada jogo.
    const key = el("input", { type: "password", autocomplete: "off", "aria-label": t("ra_apikey"),
      placeholder: state.apikey ? t("ra_apikey_set") : t("ra_apikey") });
    const save = el("button", { type: "submit", class: "btn" }, icon("px-password"), t("ra_apikey_save"));
    // A aba da conta no site onde fica a chave (Settings > Applications), numa aba nova.
    const where = el("a", { class: "btn ghost", href: "https://retroachievements.org/settings?tab=applications", target: "_blank",
      rel: "noopener" }, icon("px-password"), t("ra_apikey_get"));
    const keyForm = el("form", { class: "stack" }, el("span", {}, t("ra_apikey")), key,
      el("div", { class: "row start" }, save, where), el("div", { class: "dim" }, t("ra_apikey_hint")));
    keyForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      save.disabled = true;
      try {
        if (await post({ action: "apikey", key: key.value.trim() })) {
          toast(t(key.value.trim() ? "ra_apikey_saved" : "ra_apikey_removed"), "ok");
          reload();
        }
      } finally {
        key.value = "";
        save.disabled = false;
      }
    });
    content.append(el("div", {}, t("ra_as").replace("%s", state.user)), onOff("enable", state.enabled),
      onOff("hardcore", state.hardcore), keyForm, el("div", { class: "row start" }, out));
  } else {
    const user = el("input", { autocomplete: "off", "aria-label": t("user"), placeholder: t("user") });
    const pass = el("input", { type: "password", autocomplete: "off", "aria-label": t("password"), placeholder: t("password") });
    const go = el("button", { type: "submit", class: "btn" }, icon("px-password"), t("ra_login"));
    const form = el("form", { class: "stack" }, user, pass, el("div", { class: "row start" }, go));
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      go.disabled = true;
      try {
        if (await post({ action: "login", user: user.value.trim(), password: pass.value })) {
          toast(t("ra_done"), "ok");
          reload();
        }
      } finally {
        pass.value = "";
        go.disabled = false;
      }
    });
    // Sem conta: o cadastro no site, numa aba nova do navegador de quem usa o painel.
    const signup = el("a", { class: "btn ghost", href: "https://retroachievements.org/createaccount.php",
      target: "_blank", rel: "noopener" }, icon("px-add"), t("ra_signup"));
    content.append(form, el("div", { class: "row start" }, el("span", { class: "dim" }, t("ra_no_account")), signup));
  }
  content.append(el("div", { class: "dim" }, t("ra_note")));
  return content;
}

// As abas Sistema > RetroAchievements e Sistema > Backup na nuvem.
async function loadCheevos() {
  $("cheevos-page").replaceChildren(await cheevosPage());
}
async function loadCloud() {
  $("cloud-page").replaceChildren(await cloudPage());
}

// Setup > System > What's new: o texto so ao abrir o grupo.
function whatsnewBox() {
  const pre = el("pre", { class: "log whatsnew" });
  const box = settingsBox("Whatsnew", "px-up", el("div", { class: "setting" }, pre));
  const fill = async () => {
    if (!box.open || pre.textContent) return;
    const r = await api("/api/whatsnew");
    pre.textContent = ((await r.json()).text || "").trim() || t("wn_none");
  };
  box.addEventListener("toggle", () => fill().catch(() => {}));
  fill().catch(() => {});
  return box;
}

// Setup > System > FliperOS version: os updates da imagem ao mais novo (a
// lista vem da rede, so ao abrir o grupo). "Usar" leva o gabinete a um
// (fliperos-update goto, como tarefa); um mais velho fica preso nele ate sair
// um update novo, e "Seguir os updates" volta ao mais novo.
function versionBox() {
  const body = el("div", { class: "setting versions" });
  const box = settingsBox("Version", "px-up", body);
  let loaded = false;
  const fill = async () => {
    if (!box.open || loaded) return;
    loaded = true;
    body.replaceChildren(el("div", { class: "dim" }, "…"));
    const r = await api("/api/versions");
    if (!r.ok) {
      loaded = false;
      body.replaceChildren(el("div", { class: "dim" }, t("ver_error")));
      return;
    }
    const v = await r.json();
    const head = el("div", { class: "row start" }, el("b", {}, t("ver_now").replace("%s", v.level)),
      v.level === v.latest && v.hold == null ? el("span", { class: "tag on" }, t("ver_newest")) : "",
      v.hold != null ? el("span", { class: "tag" }, t("ver_held")) : "");
    const rows = (v.updates || []).map((u) => {
      const use = el("button", { type: "button", class: "btn ghost" }, icon("px-ok"), t("ver_use"));
      use.disabled = u.state === "current" && (v.hold != null || v.level === v.latest);
      use.addEventListener("click", () => versionGo(u.n, v, box));
      return el("div", { class: "nic-row" }, el("b", {}, String(u.n)), el("span", {}, u.title),
        u.state === "current" ? el("span", { class: "tag on" }, t("ver_installed")) : "",
        u.reboot ? el("span", { class: "tag" }, t("ver_restart")) : "", use);
    });
    const parts = [head];
    if (v.reboot) parts.push(el("div", { class: "dim" }, t("ver_reboot")));
    if (v.hold != null) {
      const follow = el("button", { type: "button", class: "btn" }, icon("px-install"), t("ver_follow"));
      follow.addEventListener("click", () => versionGo("latest", v, box));
      parts.push(el("div", { class: "row start" }, follow));
    }
    parts.push(el("div", { class: "nics" }, ...rows), el("div", { class: "dim" }, t("ver_note")));
    body.replaceChildren(...parts);
  };
  box.addEventListener("toggle", () => fill().catch(() => { loaded = false; }));
  fill().catch(() => { loaded = false; });
  return box;
}

async function versionGo(target, v, box) {
  const n = target === "latest" ? v.latest : target;
  const text = target === "latest" ? t("ver_follow_ask")
    : n < v.level ? t("ver_back_ask").replace("%s", n)
    : n > v.level ? t("ver_fwd_ask").replace("%s", n) : t("ver_stay_ask").replace("%s", n);
  if (!(await ask({ title: t("group_Version"), text, yes: t("ver_use"), danger: n < v.level }))) return;
  const r = await api("/api/versions", { method: "POST", body: JSON.stringify({ update: target }) });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) return toast(data.error || r.statusText, "bad");
  toast(t("ver_task"));
  taskNext = 0;
  let task = data;
  while (task.running) {
    await new Promise((done) => setTimeout(done, 1500));
    const q = await api("/api/task?id=" + data.id);
    if (!q.ok) return;
    task = await q.json();
  }
  if (task.rc !== 0) return toast(t("ver_fail"), "bad");
  toast(t("ver_done").replace("%s", n), "ok");
  const after = await (await api("/api/versions")).json().catch(() => ({}));
  if (after.reboot && (await ask({ title: t("group_Version"), text: t("set_restart"), yes: t("set_restart_now"), no: t("set_later") }))) {
    const p = await api("/api/settings", { method: "POST", body: JSON.stringify({ key: "power.reboot", value: "1" }) });
    toast(p.ok ? t("set_restarting") : p.statusText, p.ok ? "ok" : "bad");
    return;
  }
  loadSettings().catch(() => {});
}

// Video Setup > Geometry: o monitor e o crt_range em uso, um digitado e a
// volta ao padrao do monitor. O ajuste com a grade de teste e no tubo, com as
// setas: fica no Setup do gabinete.
async function geometryBox() {
  const res = await api("/api/geometry");
  const g = await res.json();
  const details = el("details", { class: "geometry" }, el("summary", {}, icon("px-geometry"), t("group_Geometry")));
  if (openGroups.has("Geometry")) details.open = true;
  details.addEventListener("toggle", () => { details.open ? openGroups.add("Geometry") : openGroups.delete("Geometry"); });
  const field = el("input", { type: "text", class: "mono", value: g.range || g.preset || "", spellcheck: "false", "aria-label": "crt_range0" });
  const save = el("button", { type: "button" }, t("geo_save"));
  save.addEventListener("click", async () => {
    const r = await api("/api/geometry", { method: "POST", body: JSON.stringify({ action: "set", range: field.value }) });
    const data = await r.json().catch(() => ({}));
    toast(r.ok ? t("geo_saved") : r.status === 409 ? t("geo_freq") : t("geo_bad"), r.ok ? "ok" : "bad");
    if (r.ok) loadSettings().catch(() => {});
  });
  const reset = el("button", { type: "button", class: "ghost" }, t("geo_reset"));
  reset.disabled = !g.range;
  reset.addEventListener("click", async () => {
    if (!(await ask({ title: t("geo_reset"), text: t("geo_reset_text"), yes: t("geo_reset") }))) return;
    const r = await api("/api/geometry", { method: "POST", body: JSON.stringify({ action: "reset" }) });
    toast(r.ok ? t("geo_was_reset") : r.statusText, r.ok ? "ok" : "bad");
    loadSettings().catch(() => {});
  });
  details.append(el("div", { class: "setting geo" },
    el("div", { class: "geo-head" }, el("span", { class: "dim" }, t("monitor")), el("b", {}, g.label || g.monitor || "-"),
      el("span", { class: "tag " + (g.range ? "on" : "") }, t(g.range ? "geo_custom" : "geo_preset"))),
    el("label", {}, t("geo_range")), field, el("div", { class: "row start" }, save, reset),
    el("div", { class: "dim" }, t("geo_note"))));
  return details;
}

// settingPost grava um ajuste. Os que refazem a imagem do boot (row.task)
// voltam como tarefa: o andamento fica na gaveta, e a lista se refaz no fim.
async function settingPost(row, value) {
  const res = await api("/api/settings", { method: "POST", body: JSON.stringify({ key: row.key, value }) });
  const data = await res.json().catch(() => ({}));
  if (res.ok && data.task) {
    toast(t("set_task").replace("%s", row.label));
    taskNext = 0;
    if (row.restart) restartWhenDone(data.task.id, row.label).catch(() => {});
  }
  return { res, data };
}

// restartWhenDone: o monitor, a resolucao, a orientacao so valem no proximo
// boot. Quando a tarefa termina bem, a pagina oferece reiniciar ja.
async function restartWhenDone(id, label) {
  let task = { running: true };
  while (task.running) {
    await new Promise((done) => setTimeout(done, 1500));
    const r = await api("/api/task?id=" + id);
    if (!r.ok) return;
    task = await r.json();
  }
  if (task.rc !== 0) return;
  if (!(await ask({ title: label, text: t("set_restart"), yes: t("set_restart_now"), no: t("set_later") }))) return;
  const r = await api("/api/settings", { method: "POST", body: JSON.stringify({ key: "power.reboot", value: "1" }) });
  toast(r.ok ? t("set_restarting") : r.statusText, r.ok ? "ok" : "bad");
}

// Os ajustes que podem deixar o tubo sem imagem pedem confirmacao antes.
const CONFIRM_SETTINGS = ["monitor", "resolution"];

function settingRow(row) {
  const id = "set-" + row.key.replace(/[^a-z0-9]/gi, "-");
  let control;
  if (row.type === "action") {
    // Um botao (o voltar ao padrao das cores): depois dele, os outros
    // ajustes do grupo mudaram, e a lista volta do Setup.
    const danger = row.key.startsWith("power.");
    const button = el("button", { id, type: "button", class: "btn " + (danger ? "red" : "ghost") }, icon(settingIcon(row.key)), row.label);
    button.addEventListener("click", async () => {
      if (!(await ask({ title: row.label, text: row.help, yes: t("set_go"), danger }))) return;
      button.disabled = true;
      try {
        const { res, data } = await settingPost(row, "1");
        toast(res.ok ? t("saved").replace("%s", row.label) : (data.error || res.statusText), res.ok ? "ok" : "bad");
        if (!danger) await loadSettings();
      } finally {
        button.disabled = false;
      }
    });
    return el("div", { class: "setting" }, button, el("div", { class: "dim" }, row.help));
  }
  if (row.type === "text") {
    // Um texto (o nome do gabinete): grava no Gravar ou no Enter.
    const input = el("input", { id, type: "text", value: row.value, maxlength: String(row.max || 64),
      autocomplete: "off", spellcheck: "false" });
    const button = el("button", { type: "submit", class: "btn ghost" }, icon("px-save"), t("geo_save"));
    const about = el("div", { class: "dim" }, row.help);
    const form = el("form", { class: "text-setting" }, input, button);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      button.disabled = true;
      try {
        const { res, data } = await settingPost(row, input.value.trim());
        if (res.ok && data.setting) {
          input.value = row.value = data.setting.value;
          about.textContent = data.setting.help;
          toast(t("saved").replace("%s", row.label), "ok");
        } else {
          toast(data.error || res.statusText, "bad");
        }
      } finally {
        button.disabled = false;
      }
    });
    return el("div", { class: "setting" }, el("label", { for: id }, icon(settingIcon(row.key)), row.label), form, about);
  }
  if (row.type === "choice") {
    control = el("select", { id }, ...row.options.map((o) => el("option", { value: o.value }, o.label)));
    control.value = row.value;
  } else {
    // Os numeros (a calibracao de cor): um slider com o valor ao lado, que
    // anda junto; grava ao soltar.
    control = el("input", { id, type: "range", min: String(row.min), max: String(row.max),
      step: String(row.step || 1), value: row.value });
  }
  const about = el("div", { class: "dim" }, row.help);
  let shown = null;
  // Os sliders gravam tambem enquanto andam (um a cada 300 ms): a cor muda
  // na tela do jogo com o dedo ainda no slider. Eles nao ficam desligados
  // enquanto gravam, senao o arrasto parava.
  let timer = null, busy = false;
  if (row.type === "number") {
    shown = el("output", { for: id, class: "slider-value" }, prettyNumber(row.key, row.value));
    control.addEventListener("input", () => {
      shown.textContent = prettyNumber(row.key, control.value);
      clearTimeout(timer);
      timer = setTimeout(() => { if (!busy) save(true); }, 300);
    });
  }
  control.addEventListener("change", () => { clearTimeout(timer); save(false); });
  async function save(dragging) {
    const number = row.type === "number";
    if (CONFIRM_SETTINGS.includes(row.key)) {
      const label = (row.options.find((o) => o.value === control.value) || {}).label || control.value;
      if (!(await ask({ title: row.label, text: t("set_video_ask").replace("%s", label), yes: t("set_go") }))) {
        control.value = row.value;
        return;
      }
    }
    if (!number) control.disabled = true;
    busy = true;
    try {
      const { res, data } = await settingPost(row, control.value);
      if (dragging) return;
      if (res.ok && data.task) {
        row.value = control.value;
      } else if (res.ok && data.setting) {
        control.value = data.setting.value;
        about.textContent = data.setting.help;
        row.value = data.setting.value;
        toast(t("saved").replace("%s", row.label));
      } else {
        control.value = row.value;
        toast(data.error || res.statusText);
      }
      if (shown) shown.textContent = prettyNumber(row.key, control.value);
    } finally {
      busy = false;
      control.disabled = false;
    }
  }
  let field = control;
  if (shown) {
    // - e +: um passo do ajuste por toque, para acertar sem arrastar. Os
    // toques seguidos gravam juntos, um pouco depois do ultimo.
    const stepper = (sign, label) => {
      const button = el("button", { type: "button", class: "step", "aria-label": t(sign < 0 ? "less" : "more") + ": " + row.label }, label);
      button.addEventListener("click", () => {
        const step = Number(row.step || 1);
        const value = Math.min(Number(row.max), Math.max(Number(row.min), Number(control.value) + sign * step));
        control.value = String(value);
        shown.textContent = prettyNumber(row.key, control.value);
        clearTimeout(timer);
        timer = setTimeout(() => { if (!busy) save(false); }, 400);
      });
      return button;
    };
    field = el("div", { class: "slider" }, stepper(-1, "−"), control, stepper(1, "+"), shown);
  }
  return el("div", { class: "setting" }, el("label", { for: id }, icon(settingIcon(row.key)), row.label), field, about);
}

// Os jogos entrelacados: um cartao por emulador, com o modo em botoes
// (640x240, entrelacado com filtro, entrelacado puro) e, so no com filtro, o
// nivel do filtro logo embaixo. O Setup manda duas linhas por emulador (mode480.CHAVE e
// deflicker.CHAVE); aqui elas viram uma so.
function mode480Rows(items) {
  const levels = new Map(items.filter((r) => r.key.startsWith("deflicker.")).map((r) => [r.key.slice(10), r]));
  const out = [el("div", { class: "setting m480-intro" },
    el("div", { class: "dim" }, t("m480_intro")))];
  for (const row of items.filter((r) => r.key.startsWith("mode480."))) {
    const level = levels.get(row.key.slice(8));
    const card = el("div", { class: "setting m480" }, el("label", {}, row.label),
      choiceChips(row, (o) => t("m480_" + o.value)));
    if (level && row.value === "filter") {
      card.append(el("div", { class: "m480-level" }, el("span", { class: "dim" }, t("m480_level")),
        choiceChips(level, (o) => t("m480_" + o.value))));
    }
    card.append(el("div", { class: "dim" }, row.help));
    out.push(card);
  }
  return out;
}

// choiceChips: as opcoes de um ajuste de escolha como botoes; o marcado e o
// valor de agora, e um clique grava e recarrega a lista.
function choiceChips(row, label) {
  return el("div", { class: "chips", role: "group", "aria-label": row.label }, ...row.options.map((o) => {
    const b = el("button", { type: "button", "aria-pressed": String(o.value === row.value) }, label(o));
    b.addEventListener("click", async () => {
      if (o.value === row.value) return;
      b.disabled = true;
      try {
        const res = await api("/api/settings", { method: "POST", body: JSON.stringify({ key: row.key, value: o.value }) });
        const data = await res.json().catch(() => ({}));
        toast(res.ok ? t("saved").replace("%s", row.label) : (data.error || res.statusText));
        await loadSettings();
      } finally {
        b.disabled = false;
      }
    });
    return b;
  }));
}

// prettyNumber: o valor como o Setup mostra (1.00, 6500 K, 100%, +5).
function prettyNumber(key, value) {
  const v = Number(value);
  if (/gamma$/.test(key)) return (v / 100).toFixed(2);
  if (/temperature$/.test(key)) return v + " K";
  if (/(contrast|gain|saturation)$/.test(key)) return v + "%";
  if (/hue$/.test(key)) return v + "°";
  return v > 0 ? "+" + v : String(v);
}

// ── Modo lab ─────────────────────────────────────────────────────
// Este painel num endereco temporario da internet (config/fliperos-lab):
// ligar e uma tarefa (baixa o cloudflared na primeira vez e espera o
// endereco); ligado, o endereco com a chave para copiar.

let labState = null;

async function loadLab() {
  const res = await api("/api/lab");
  showLab(await res.json());
}

function showLab(data) {
  labState = data;
  $("lab-note").textContent = t("lab_note").replace("%n", data.hours || 4);
  const until = data.expires ? new Date(data.expires * 1000).toLocaleTimeString(lang === "pt" ? "pt-BR" : "en",
    { hour: "2-digit", minute: "2-digit" }) : "";
  $("lab-state").textContent = data.active ? t("lab_on").replace("%s", until) + (data.you ? " " + t("lab_you") : "")
    : t("lab_off");
  $("lab-box").hidden = !data.active;
  $("lab-url").value = data.url || "";
  $("lab-start").hidden = !!data.active;
  $("lab-stop").hidden = !data.active;
}

async function labStart() {
  if (!confirm(t("lab_ask"))) return;
  $("lab-start").disabled = true;
  $("lab-step").hidden = false;
  $("lab-step").textContent = t("lab_starting");
  try {
    const res = await api("/api/lab", { method: "POST", body: JSON.stringify({ action: "start" }) });
    let task = await res.json();
    if (!res.ok) { toast(task.error || res.statusText); return; }
    while (task.running) {
      await new Promise((done) => setTimeout(done, 1500));
      task = await (await api("/api/task?id=" + task.id)).json();
      $("lab-step").textContent = task.step || t("lab_starting");
    }
    if (task.rc !== 0) toast(task.error || task.last || t("task_fail"));
  } finally {
    $("lab-start").disabled = false;
    $("lab-step").hidden = true;
    loadLab().catch(() => {});
  }
}

$("lab-start").addEventListener("click", () => labStart().catch(() => {}));
$("lab-stop").addEventListener("click", async () => {
  if (!confirm(t("lab_ask_stop"))) return;
  const res = await api("/api/lab", { method: "POST", body: JSON.stringify({ action: "stop" }) });
  if (res.ok) showLab(await res.json());
});
$("lab-copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("lab-url").value); toast(t("copied")); } catch (e) {
    $("lab-url").select();
    document.execCommand("copy");
    toast(t("copied"));
  }
});

// ── Terminal ─────────────────────────────────────────────────────
// O shell do gabinete pelo WebSocket /api/terminal, desenhado pelo xterm.js
// (carregado so quando o terminal abre). Teclas vao como binario; o tamanho,
// como texto {"resize": [colunas, linhas]}.

let term = null, termSocket = null, termFit = null;

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
