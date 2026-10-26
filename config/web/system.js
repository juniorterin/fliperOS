// Sistema: o status (o video, a CPU, a GPU, a memoria, os discos e a rede,
// do /api/status de cada segundo), os processos e os logs, os ajustes, o
// modo lab e o terminal.
"use strict";

function renderStatus(s) {
  // Video: o pedido e o aplicado.
  const v = s.video || {}, w = v.wanted || {};
  const table = $("video-table");
  table.replaceChildren();
  const add = (k, val) => table.append(el("tr", {}, el("th", {}, t(k)), el("td", {}, val || "-")));
  table.append(el("tr", {}, el("th", { colspan: "2", class: "vid-part" }, t("wanted"))));
  add("monitor", w.monitor); add("frequency", w.frequency); add("resolution", w.boot_resolution);
  add("connector", w.connector); add("orientation", w.orientation);
  table.append(el("tr", {}, el("th", { colspan: "2", class: "vid-part" }, t("applied"))));
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
    if (group === "480i hacks") details.append(...mode480Rows(items));
    else for (const row of items) details.append(settingRow(row));
    boxes.push(details);
  }
  $("settings").replaceChildren(...boxes);
}

function settingRow(row) {
  const id = "set-" + row.key.replace(/[^a-z0-9]/gi, "-");
  let control;
  if (row.type === "action") {
    // Um botao (o voltar ao padrao das cores): depois dele, os outros
    // ajustes do grupo mudaram, e a lista volta do Setup.
    const button = el("button", { id, type: "button", class: "ghost" }, row.label);
    button.addEventListener("click", async () => {
      if (!confirm(row.help)) return;
      button.disabled = true;
      try {
        const res = await api("/api/settings", { method: "POST", body: JSON.stringify({ key: row.key, value: "1" }) });
        const data = await res.json().catch(() => ({}));
        toast(res.ok ? t("saved").replace("%s", row.label) : (data.error || res.statusText));
        await loadSettings();
      } finally {
        button.disabled = false;
      }
    });
    return el("div", { class: "setting" }, button, el("div", { class: "dim" }, row.help));
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
    if (!number) control.disabled = true;
    busy = true;
    try {
      const res = await api("/api/settings", { method: "POST", body: JSON.stringify({ key: row.key, value: control.value }) });
      const data = await res.json().catch(() => ({}));
      if (dragging) return;
      if (res.ok && data.setting) {
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
  return el("div", { class: "setting" }, el("label", { for: id }, row.label), field, about);
}

// Os jogos 480i: um cartao por emulador, com o modo em botoes (640x240,
// 480i com filtro, 480i puro) e, so no 480i com filtro, o nivel do filtro
// logo embaixo. O Setup manda duas linhas por emulador (mode480.CHAVE e
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
