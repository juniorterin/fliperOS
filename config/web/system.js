// Sistema: o status (o video, a CPU, a GPU, a memoria, os discos e a rede,
// do /api/status de cada segundo), os processos e os logs, as pecas das
// listas de ajustes (a area inteira usa as mesmas), os ajustes do Setup, as
// abas RetroAchievements e Backup na nuvem, o modo lab e o terminal.
"use strict";

// ── Status ───────────────────────────────────────────────────────

// Um medidor fino: a cor pelo quanto esta usado (ou pelo nivel dado).
function stMeter(pct, level) {
  const box = el("div", { class: "st-meter" }, el("i"));
  stMeterSet(box, pct, level);
  return box;
}
function stMeterSet(box, pct, level) {
  const p = Math.max(0, Math.min(100, pct || 0));
  box.firstChild.style.width = p + "%";
  const cls = level != null ? level : p > 90 ? "hot" : p > 70 ? "warn" : "";
  if (box.firstChild.className !== cls) box.firstChild.className = cls;
}

// keyedRows: as linhas de uma lista que muda a cada segundo, feitas uma vez
// por chave (as barras andam suave, nada pisca); make(item) devolve
// { node, update(item) }.
function keyedRows(box, items, keyOf, make) {
  if (!box.keyed) box.keyed = new Map();
  const seen = new Set();
  items.forEach((item, i) => {
    const key = keyOf(item, i);
    seen.add(key);
    let row = box.keyed.get(key);
    if (!row) {
      row = make(item);
      box.keyed.set(key, row);
    }
    row.update(item);
    if (box.children[i] !== row.node) box.insertBefore(row.node, box.children[i] || null);
  });
  for (const [key, row] of box.keyed) {
    if (!seen.has(key)) {
      row.node.remove();
      box.keyed.delete(key);
    }
  }
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

// As temperaturas: o nome, a barra ate o limite da peca e os graus.
function renderTemps(rows) {
  keyedRows($("temps"), rows.slice(0, 10), (x, i) => lang + x.sensor + "|" + x.label + "|" + i, () => {
    const name = el("span", { class: "st-temp-name" }), bar = stMeter(0), deg = el("span", { class: "val" });
    const node = el("div", { class: "st-temp" }, name, bar, deg);
    return { node, update(x) {
      const [kind, label, fallback] = sensorName(x);
      const limit = x.max || fallback, ratio = x.celsius / limit;
      setText(name, kind + (label && label !== kind ? " · " + label : ""));
      stMeterSet(bar, ratio * 100, ratio < .75 ? "" : ratio < .88 ? "warn" : "hot");
      setText(deg, Math.round(x.celsius) + "°");
      node.title = kind + " " + (label || "") + ": " + x.celsius + " °C (" + t("st_limit") + " " + limit + " °C)";
    } };
  });
  $("temps").closest(".st-card").hidden = !rows.length;
}

// A placa do tubo: a da saida acesa (a primeira, sem saida).
function statusGpu(s) {
  const gpus = Array.isArray(s.gpus) ? s.gpus : [];
  const out = ((s.video || {}).outputs || []).find((o) => o.active);
  const card = out && out.card ? out.card.replace("/dev/dri/", "") : "";
  return gpus.find((g) => g.card === card) || gpus[0] || null;
}

// O nome curto da placa (o lspci da o fabricante inteiro e o chip):
// "Advanced Micro Devices, Inc. [AMD/ATI] Oland PRO [Radeon R7 240/340]" vira
// "AMD Radeon R7 240/340".
function gpuName(name) {
  if (!name) return "";
  const model = /\[([^\]]+)\]\s*$/.exec(name);
  const vendor = /AMD|ATI/.test(name) ? "AMD " : /NVIDIA/i.test(name) ? "NVIDIA " : /Intel/.test(name) ? "Intel " : "";
  return model && !/^AMD\/ATI$/.test(model[1]) ? vendor + model[1] : name.replace(/ Corporation| Inc\.|,/g, "");
}

// Uma linha de fato: o rotulo e o valor.
const kv = (label, value) => el("div", { class: "st-kv" }, el("span", {}, label), el("span", { class: "val" }, value));

function renderStatus(s) {
  // O video no tubo: os kHz no mostrador, a faixa, o modo, a saida e o driver.
  const v = s.video || {}, w = v.wanted || {};
  const out = (v.outputs || []).find((o) => o.active);
  const khz = out ? Number(out.horizontal_khz) : 0;
  setText($("st-khz"), out ? khz.toFixed(2) : "--.--");
  $("st-led").classList.toggle("off", !out);
  const gpu = statusGpu(s);
  const chips = out ? [[khz < 20 ? "15 kHz" : khz < 28 ? "25 kHz" : "31 kHz", "band " + (khz < 20 ? "b15" : khz < 28 ? "b25" : "b31")],
    [out.width + "×" + out.height], [Number(out.vertical_hz).toFixed(2) + " Hz"],
    [out.interlaced ? t("interlaced") : t("progressive")], [out.connector + " · " + out.card.replace("/dev/dri/", "")]] : [];
  if (gpu && gpu.driver) chips.push(["driver " + gpu.driver, "drv"]);
  const chipKey = lang + JSON.stringify(chips);
  if ($("st-mode").dataset.key !== chipKey) {
    $("st-mode").dataset.key = chipKey;
    $("st-mode").replaceChildren(...(chips.length ? chips.map(([text, cls]) => el("span", { class: "st-chip" + (cls ? " " + cls : "") }, text))
      : [el("span", { class: "dim" }, t("no_output"))]));
  }
  const lines = (v.outputs || []).filter((o) => o.active).map((o) => o.connector + ": Modeline " + o.modeline);
  if ($("modelines").dataset.key !== lines.join("\n")) {
    $("modelines").dataset.key = lines.join("\n");
    $("modelines").replaceChildren(...lines.map((line) => el("div", { class: "modeline" }, line)));
  }
  const wanted = [["monitor", w.monitor], ["frequency", w.frequency], ["resolution", w.boot_resolution],
    ["connector", w.connector], ["orientation", w.orientation], ["framebuffer", v.framebuffer]];
  const wantedKey = lang + JSON.stringify(wanted);
  if ($("video-table").dataset.key !== wantedKey) {
    $("video-table").dataset.key = wantedKey;
    $("video-table").replaceChildren(...wanted.map(([k, val]) => el("tr", {}, el("th", {}, t(k)), el("td", {}, val || "-"))));
  }

  // CPU: o total, a carga e cada nucleo numa coluna de segmentos, como um VU.
  const cpu = s.cpu || {};
  setText($("cpu-total"), (cpu.total ?? 0).toFixed(0) + "%");
  setText($("load"), t("load") + " " + (s.load || []).join(" "));
  const cores = $("cores"), list = cpu.cores || [];
  if (cores.children.length !== list.length) {
    cores.replaceChildren(...list.map((_, i) => el("div", { class: "st-core" },
      el("div", { class: "vcol" }, ...Array.from({ length: 10 }, () => el("i"))), el("small", {}, "#" + i))));
  }
  list.forEach((c, i) => {
    const core = cores.children[i], lit = Math.max(1, Math.round(c / 10));
    [...core.firstChild.children].forEach((seg, k) => {
      const cls = k < lit ? "on" + (k >= 8 ? " h" : k >= 6 ? " w" : "") : "";
      if (seg.className !== cls) seg.className = cls;
    });
    core.title = t("st_core").replace("%n", i).replace("%p", c.toFixed(0));
  });

  renderTemps(s.temperatures || []);

  // GPU: o nome e o que a placa diz (uso, VRAM, relogio, temperatura, consumo).
  const gpus = Array.isArray(s.gpus) ? s.gpus : [];
  keyedRows($("gpus"), gpus, (g) => lang + (g.slot || g.card), () => {
    const name = el("b", { class: "st-name" }), busy = el("span", { class: "val" }), busyBar = stMeter(0);
    const vram = el("span", { class: "val" }), vramBar = stMeter(0), facts = el("div", { class: "st-facts" });
    const busyRow = el("div", {}, el("div", { class: "st-kv" }, el("span", {}, t("busy")), busy), busyBar);
    const vramRow = el("div", {}, el("div", { class: "st-kv" }, el("span", {}, t("vram")), vram), vramBar);
    return { node: el("div", { class: "st-gpu" }, name, busyRow, vramRow, facts), update(g) {
      setText(name, gpuName(g.name) || g.slot);
      name.title = g.name || "";
      busyRow.hidden = g.busy == null;
      if (g.busy != null) { setText(busy, g.busy + "%"); stMeterSet(busyBar, g.busy); }
      vramRow.hidden = !g.vram_total;
      if (g.vram_total) {
        setText(vram, bytes(g.vram_used) + " " + t("of") + " " + bytes(g.vram_total));
        stMeterSet(vramBar, (100 * g.vram_used) / g.vram_total);
      }
      const rows = [[t("clock"), g.clock], [t("temp"), g.celsius != null ? g.celsius + " °C" : ""],
        [t("power"), g.watts != null ? g.watts + " W" : ""]].filter(([, x]) => x);
      const key = JSON.stringify(rows);
      if (facts.dataset.key !== key) {
        facts.dataset.key = key;
        facts.replaceChildren(...rows.map(([k, x]) => kv(k, x)));
      }
    } };
  });
  $("gpus-none").hidden = gpus.length > 0;

  // Memoria: o usado, o total, a barra e a troca.
  const m = s.memory || {};
  setText($("mem-used"), bytes(m.used));
  setText($("mem-total"), t("of") + " " + bytes(m.total));
  stMeterSet($("mem-bar"), m.total ? (100 * m.used) / m.total : 0);
  $("mem-swap").hidden = !m.swap_total;
  if (m.swap_total) {
    setText($("mem-swap-val"), bytes(m.swap_used) + " " + t("of") + " " + bytes(m.swap_total));
    stMeterSet($("mem-swap-bar"), (100 * m.swap_used) / m.swap_total);
  }

  // Os discos montados e a rede (cada placa, o endereco, o trafego e o sinal).
  keyedRows($("disks"), Array.isArray(s.disks) ? s.disks : [], (d) => lang + d.mount, () => {
    const mount = el("b"), size = el("span", { class: "dim" }), bar = stMeter(0);
    return { node: el("div", { class: "st-disk" }, el("div", { class: "st-kv" }, mount, size), bar), update(d) {
      setText(mount, d.mount);
      setText(size, bytes(d.used) + " " + t("of") + " " + bytes(d.total));
      stMeterSet(bar, d.total ? (100 * d.used) / d.total : 0);
    } };
  });
  const nics = Object.entries(s.network || {}).map(([name, n]) => ({ name, n, wifi: /^w/.test(name) ? s.wifi : null }));
  keyedRows($("network"), nics, (x) => lang + x.name, () => {
    const head = el("b"), ip = el("span", { class: "dim" }), sig = el("span", { class: "dim" }), rates = el("span", { class: "val" });
    return { node: el("div", { class: "st-nic" }, el("div", { class: "st-kv" }, head, ip), el("div", { class: "st-kv" }, sig, rates)),
      update(x) {
        setText(head, x.name + (x.wifi && x.wifi.ssid ? " · " + x.wifi.ssid : ""));
        setText(ip, (x.n.ipv4 || []).join(", ") || "-");
        setText(sig, x.wifi ? t("signal") + " " + x.wifi.signal + "%" : "");
        setText(rates, "↓ " + rate(x.n.rx_bps) + "   ↑ " + rate(x.n.tx_bps));
      } };
  });

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

// ── O hardware (Status) ──────────────────────────────────────────
// /api/hardware: a placa-mae, a CPU (com o socket), a memoria, os discos, o
// som (e qual saida esta em uso), os aparelhos ligados e o PCI com os
// enderecos. Lido ao abrir a aba. O botao copia o relatorio inteiro (/api/report).
let hwData = null;
const hwKv = (label, value) => el("div", { class: "st-kv" }, el("span", {}, label), el("span", { class: "val wrap" }, value));
const hwSet = (box, rows) => box.replaceChildren(...(rows.length ? rows : [el("span", { class: "dim" }, t("hw_none"))]));
const hwJoin = (...parts) => parts.filter((x) => x !== "" && x != null).join(" ");

async function hwLoad() {
  const res = await api("/api/hardware");
  if (!res.ok) return;
  hwData = await res.json();
  hwRender();
}

function hwRender() {
  const d = hwData;
  if (!d || d.error) return;
  const b = d.board || {}, c = d.cpu || {};
  const rows = [];
  const board = hwJoin(b.vendor, b.name, b.version);
  if (board) rows.push(hwKv(t("hw_board"), board));
  const system = hwJoin(b.system_vendor, b.product);
  if (system && system !== board) rows.push(hwKv(t("hw_system"), system));
  if (b.bios_version) rows.push(hwKv("BIOS", hwJoin(b.bios_vendor, b.bios_version, b.bios_date)));
  if (c.model) rows.push(hwKv("CPU", c.model));
  if (c.socket || c.socket_designation) rows.push(hwKv(t("hw_socket"), hwJoin(c.socket, c.socket_designation && "(" + c.socket_designation + ")")));
  rows.push(hwKv(t("hw_cores"), hwJoin((c.sockets || "?") + " × " + (c.cores_per_socket || "?") + " " + t("hw_cores_word"), "· " + c.threads + " " + t("hw_threads"),
    c.max_mhz ? "· " + c.max_mhz + " MHz" : "")));
  const cache = Object.entries(c.cache || {}).map(([k, v]) => k + " " + v).join(", ");
  if (cache) rows.push(hwKv("Cache", cache));
  (d.memory || []).forEach((m) => rows.push(hwKv(t("hw_ram") + (m.locator ? " " + m.locator : ""), hwJoin(m.size, m.type, m.speed, m.maker))));
  if (d.kernel) rows.push(hwKv(t("hw_kernel"), hwJoin(d.kernel.os, d.kernel.release)));
  hwSet($("hw-machine"), rows);

  hwSet($("hw-storage"), (d.storage || []).map((disk) => el("div", { class: "st-nic" },
    hwKv(hwJoin(disk.vendor, disk.model) || disk.name, bytes(disk.size)),
    el("div", { class: "dim" }, hwJoin("/dev/" + disk.name, "·", (disk.tran || "?").toUpperCase(), disk.kind.toUpperCase(), disk.removable ? "· " + t("hw_removable") : "")),
    ...disk.parts.map((p) => el("div", { class: "dim hw-part" }, hwJoin(p.name, bytes(p.size), p.fstype, p.label, p.mount && "→ " + p.mount))))));

  const sound = (d.sound && d.sound.cards) || [];
  hwSet($("hw-sound"), sound.map((card) => el("div", { class: "st-nic" },
    el("div", { class: "st-kv" }, el("b", {}, card.name),
      el("span", { class: "hw-tags" },
        card.selected ? el("span", { class: "st-chip drv" }, t("hw_output_chosen")) : "",
        card.playing ? el("span", { class: "st-chip b15" }, t("hw_playing")) : "")),
    el("div", { class: "dim" }, hwJoin("card " + card.index, "·", card.driver, "·", card.bus.toUpperCase(), card.address)),
    ...card.devices.map((x) => el("div", { class: "dim hw-part" }, "hw:" + card.index + "," + x.device + " · " + x.name)))));

  const devices = [];
  const group = (title, items) => { if (items.length) devices.push(el("div", { class: "st-nic" }, el("b", {}, title), ...items)); };
  group(t("hw_monitors"), (d.monitors || []).map((m) => hwKv(m.connector, hwJoin(m.maker, m.name, m.year && "(" + m.year + ")", m.mode))));
  group(t("hw_input"), (d.input || []).map((i) => hwKv(i.name, hwJoin(i.kind, "·", i.bus, i.ids))));
  group("USB", (d.usb || []).map((u) => hwKv(u.name || u.ids, u.ids)));
  group(t("hw_network"), (d.network || []).map((n) => hwKv(n.name, hwJoin(n.kind, "·", n.driver, n.address))));
  if (d.bluetooth) group("Bluetooth", [hwKv(t("hw_adapter"), t("hw_present"))]);
  hwSet($("hw-devices"), devices);

  const pci = d.pci || [];
  const table = el("table", {}, el("thead", {}, el("tr", {}, ...["hw_addr", "hw_class", "hw_device", "hw_driver"].map((k) => el("th", {}, t(k))))),
    el("tbody", {}, ...pci.map((p) => el("tr", {}, el("td", { class: "mono" }, p.slot), el("td", {}, p.class),
      el("td", {}, hwJoin(p.vendor, p.device), el("small", { class: "dim" }, " [" + p.ids + "]")), el("td", {}, p.driver || "-")))));
  $("hw-pci").replaceChildren(pci.length ? el("details", { class: "st-more", open: "" },
    el("summary", {}, icon("g-chevd"), el("span", {}, t("hw_pci_count").replace("%n", pci.length))),
    el("div", { class: "table-wrap" }, table)) : el("span", { class: "dim" }, t("hw_none")));
}

// Copiar o relatorio: o hardware e todos os ajustes do Setup num texto so.
$("hw-copy").addEventListener("click", async () => {
  const button = $("hw-copy");
  button.disabled = true;
  try {
    const res = await api("/api/report");
    if (!res.ok) { toast(t("hw_copy_fail"), "bad"); return; }
    await copyText(await res.text(), null);
  } catch (e) {
    toast(t("hw_copy_fail"), "bad");
  } finally {
    button.disabled = false;
  }
});

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
// Copiar o log: as ultimas linhas que o servidor entrega (2000, bem mais que
// as 300 da tela), com o nome do log em cima, para colar num pedido de ajuda.
$("log-copy").addEventListener("click", async () => {
  const name = $("log-name").value;
  if (!name) return;
  let text = $("log-text").textContent;
  try {
    const res = await api("/api/log?name=" + encodeURIComponent(name) + "&lines=2000");
    if (res.ok) text = (await res.json()).text || text;
  } catch (e) { /* fica o que esta na tela */ }
  if (!text) { toast(t("log_copy_empty"), "bad"); return; }
  await copyText("# " + name + "\n" + text, null);
});

// ── As listas de ajustes ─────────────────────────────────────────
// A area Sistema inteira usa as mesmas pecas: uma secao (um rotulo pequeno
// em maiusculas e um bloco) e, no bloco, uma linha por ajuste: o nome a
// esquerda, o controle a direita, a explicacao atras do (i), aberta embaixo.

function uiSection(title, rows, note, attrs) {
  const sec = el("section", Object.assign({ class: "ssec" }, attrs || {}));
  if (title) sec.append(el("h3", {}, title));
  sec.append(el("div", { class: "slist" }, ...rows));
  if (note) sec.append(el("p", { class: "ssec-note" }, note));
  return sec;
}

// uiRow({ label, sub, control, help, cls, before, after, href, mono, id }):
// before vai antes do nome (as barras do sinal, uma etiqueta); after vai
// embaixo, na largura toda (o nivel do filtro, um formulario). Com href, a
// linha e um link.
function uiRow(o) {
  const attrs = { class: "srow" + (o.cls ? " " + o.cls : "") + (o.sub ? " has-sub" : "") };
  if (o.href) attrs.href = o.href;
  if (o.id) attrs.id = o.id;
  const row = el(o.href ? "a" : "div", attrs);
  const lbl = el("div", { class: "lbl" }, ...(o.before || []), el("b", {}, o.label));
  row.append(lbl);
  const controls = [].concat(o.control || []).filter(Boolean);
  if (controls.length) row.append(el("div", { class: "ctl" }, ...controls));
  if (o.sub) row.append(el("div", { class: "srow-sub" + (o.mono ? " code-txt" : "") }, o.sub));
  if (o.help) {
    const help = el("div", { class: "help", hidden: "" }, o.help);
    const btn = el("button", { type: "button", class: "info-btn", "aria-label": t("setup_about").replace("%s", o.label),
      "aria-expanded": "false" }, icon("g-info"));
    btn.addEventListener("click", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      help.hidden = !help.hidden;
      btn.setAttribute("aria-expanded", String(!help.hidden));
    });
    lbl.append(btn);
    row.append(help);
  }
  for (const node of o.after || []) row.append(node);
  return row;
}

// uiClickable: a linha inteira abre algo (Abrir no gabinete), pelo clique
// ou pelo Enter; os controles dentro dela continuam deles.
function uiClickable(row, open) {
  row.classList.add("tap");
  row.tabIndex = 0;
  row.setAttribute("role", "button");
  row.addEventListener("click", (ev) => {
    if (!ev.target.closest(".ctl button, .ctl a, .ctl input, .ctl select, .info-btn, .help, .srow-form")) open();
  });
  row.addEventListener("keydown", (ev) => {
    if ((ev.key === "Enter" || ev.key === " ") && ev.target === row) {
      ev.preventDefault();
      open();
    }
  });
  return row;
}

// Os controles: change/pick devolvem false (ou uma promessa de false) quando
// a gravacao falhou, e o controle volta ao que era.
function uiSwitch(on, label, change) {
  const b = el("button", { type: "button", class: "tgl", role: "switch", "aria-checked": String(!!on), "aria-label": label });
  b.addEventListener("click", async () => {
    const next = b.getAttribute("aria-checked") !== "true";
    b.setAttribute("aria-checked", String(next));
    b.disabled = true;
    let ok = false;
    try { ok = (await change(next)) !== false; } catch (e) { ok = false; }
    if (!ok) b.setAttribute("aria-checked", String(!next));
    b.disabled = false;
  });
  return b;
}

// uiChoice: 2 ou 3 opcoes curtas, lado a lado.
function uiChoice(options, value, label, pick) {
  const box = el("div", { class: "choice", role: "group", "aria-label": label });
  const mark = (v) => [...box.children].forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.value === v)));
  for (const o of options) {
    const b = el("button", { type: "button", "data-value": o.value }, o.label);
    b.addEventListener("click", async () => {
      if (b.getAttribute("aria-pressed") === "true" || box.classList.contains("busy")) return;
      const before = value;
      mark(o.value);
      box.classList.add("busy");
      let ok = false;
      try { ok = (await pick(o.value)) !== false; } catch (e) { ok = false; }
      box.classList.remove("busy");
      if (ok) value = o.value; else mark(before);
    });
    box.append(b);
  }
  mark(value);
  return box;
}

function uiSelect(options, value, label, change) {
  const s = el("select", { class: "sel", "aria-label": label }, ...options.map((o) => el("option", { value: o.value }, o.label)));
  s.value = value;
  let current = s.value;
  s.addEventListener("change", async () => {
    const next = s.value;
    s.disabled = true;
    let ok = false;
    try { ok = (await change(next)) !== false; } catch (e) { ok = false; }
    s.disabled = false;
    if (ok) current = next; else s.value = current;
  });
  return s;
}

// Um botao de texto (a acao da linha) e um so de icone.
function uiButton(text, run, cls) {
  const b = el("button", { type: "button", class: "btn-text" + (cls ? " " + cls : "") }, text);
  b.addEventListener("click", async (ev) => {
    ev.stopPropagation();
    b.disabled = true;
    try { await run(b); } catch (e) { if (e.message !== "login") toast(e.message, "bad"); } finally { b.disabled = false; }
  });
  return b;
}
function uiIconButton(glyph, label, run) {
  const b = el("button", { type: "button", class: "ibtn", "aria-label": label, title: label },
    glyph.startsWith("g-") ? icon(glyph) : glyph);
  b.addEventListener("click", async (ev) => {
    ev.stopPropagation();
    b.disabled = true;
    try { await run(b); } catch (e) { if (e.message !== "login") toast(e.message, "bad"); } finally { b.disabled = false; }
  });
  return b;
}

// "no gabinete ↗": a etiqueta das linhas que abrem uma tela no tubo.
const uiCabGo = (text) => el("span", { class: "cab-go" }, el("span", { class: "tagcab" }, icon("px-arcade"), text), icon("g-ext"));

// Um campo de formulario aberto embaixo de uma linha.
const uiField = (attrs) => el("input", Object.assign({ class: "fld", autocomplete: "off" }, attrs));

// ── Os ajustes do Setup ──────────────────────────────────────────
// Os ajustes que podem mudar daqui (fliperos-setup --settings): cada mudanca
// grava na hora. A arvore do Setup que os mostra, item por item, fica em
// setup.js (loadSettings); aqui a linha de cada ajuste e as caixas.

const settingKeyIn = (table, key) => table[key] || (Object.entries(table).find(([k]) => k.endsWith(".") && key.startsWith(k)) || [])[1];
const settingLabel = (row) => (lang === "pt" && SETTING_NAMES_PT[row.key]) || row.label;

function settingHelp(row) {
  if (lang !== "pt" || !row.help) return row.help || "";
  if (SETTING_HELP_PT[row.key]) return SETTING_HELP_PT[row.key];
  for (const [re, pt] of SETTING_HELP_PT_RE) if (re.test(row.help)) return row.help.replace(re, pt);
  return row.help;
}

function settingOptions(row) {
  const table = SETTING_OPTIONS[lang] || {};
  const own = settingKeyIn(table, row.key) || {}, all = table["*"] || {};
  return (row.options || []).map((o) => ({ value: o.value, label: own[o.value] || all[o.value] || o.label }));
}

// O controle de cada escolha: liga/desliga vira chave; 2 ou 3 opcoes curtas,
// botoes lado a lado; o resto, um seletor.
function settingKind(row, options) {
  if (row.type !== "choice") return row.type;
  if (options.length === 2 && options.every((o) => o.value === "on" || o.value === "off")) return "switch";
  const total = options.reduce((n, o) => n + o.label.length, 0);
  return options.length <= 3 && options.every((o) => o.label.length <= 12) && total <= 32 ? "buttons" : "select";
}

const settingActionLabel = (row) => (SETTING_ACTIONS[lang] || {})[row.key] || SETTING_ACTIONS.en[row.key] || t("set_go");

// settingPost grava um ajuste. Os que refazem a imagem do boot (row.task)
// voltam como tarefa: o andamento fica na gaveta, e a lista se refaz no fim.
async function settingPost(row, value) {
  const res = await api("/api/settings", { method: "POST", body: JSON.stringify({ key: row.key, value }) });
  const data = await res.json().catch(() => ({}));
  if (res.ok && data.task) {
    toast(t("set_task").replace("%s", settingLabel(row)));
    taskNext = 0;
    if (row.restart) restartWhenDone(data.task.id, settingLabel(row)).catch(() => {});
  }
  return { res, data };
}

// settingSave: grava e diz; true quando gravou.
async function settingSave(row, value) {
  const { res, data } = await settingPost(row, value);
  if (res.ok && data.task) {
    row.value = value;
    return true;
  }
  if (res.ok) {
    row.value = data.setting ? data.setting.value : value;
    toast(t("saved").replace("%s", settingLabel(row)), "ok");
    return true;
  }
  toast(data.error || res.statusText, "bad");
  return false;
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
  const label = settingLabel(row), help = settingHelp(row);
  const id = "set-" + row.key.replace(/[^a-z0-9]/gi, "-");
  if (row.type === "action") {
    // Um botao (voltar as cores ao padrao, reiniciar): depois dele, os outros
    // ajustes do grupo mudaram, e a lista volta do Setup.
    const danger = row.key.startsWith("power.");
    const go = uiButton(settingActionLabel(row), async () => {
      if (!(await ask({ title: label, text: help, yes: settingActionLabel(row), danger }))) return;
      const { res, data } = await settingPost(row, "1");
      toast(res.ok ? t("saved").replace("%s", label) : (data.error || res.statusText), res.ok ? "ok" : "bad");
      if (res.ok && !danger) loadSettings().catch(() => {});
    }, danger ? "red" : "");
    const back = row.key === "video.previous" && /^Back to (.*?): /.exec(row.help || "");
    return uiRow({ label, sub: back ? back[1] : "", control: go, help, id, cls: danger ? "danger" : "" });
  }
  if (row.type === "text") {
    // Um texto (o nome do gabinete): grava ao sair do campo ou no Enter.
    const input = el("input", { type: "text", class: "txt", value: row.value, maxlength: String(row.max || 64),
      autocomplete: "off", spellcheck: "false", "aria-label": label });
    input.addEventListener("keydown", (ev) => { if (ev.key === "Enter") { ev.preventDefault(); input.blur(); } });
    input.addEventListener("change", async () => {
      input.disabled = true;
      try {
        const { res, data } = await settingPost(row, input.value.trim());
        if (res.ok && data.setting) {
          input.value = row.value = data.setting.value;
          toast(t("saved").replace("%s", label), "ok");
        } else {
          input.value = row.value;
          toast(data.error || res.statusText, "bad");
        }
      } finally {
        input.disabled = false;
      }
    });
    return uiRow({ label, control: input, help, id });
  }
  if (row.type === "number") return uiRow({ label, control: settingSlider(row, label), help, id, cls: "has-slider" });
  const options = settingOptions(row);
  const kind = settingKind(row, options);
  let control;
  if (kind === "switch") {
    control = uiSwitch(row.value === "on", label, (on) => settingSave(row, on ? "on" : "off"));
  } else if (kind === "buttons") {
    control = uiChoice(options, row.value, label, (value) => settingSave(row, value));
  } else {
    control = uiSelect(options, row.value, label, async (value) => {
      if (CONFIRM_SETTINGS.includes(row.key)) {
        const name = (options.find((o) => o.value === value) || {}).label || value;
        if (!(await ask({ title: label, text: t("set_video_ask").replace("%s", name), yes: t("set_go") }))) return false;
      }
      return settingSave(row, value);
    });
  }
  const long = kind === "buttons" && options.reduce((n, o) => n + o.label.length, 0) > 20;
  return uiRow({ label, control, help, id, cls: long ? "wrap-ctl" : "" });
}

// Os numeros (a calibracao de cor, a pistola): um slider com o valor ao
// lado; grava enquanto anda (um a cada 300 ms: a cor muda na tela do jogo
// com o dedo ainda no slider) e ao soltar. O - e o + dao um passo por toque.
function settingSlider(row, label) {
  const range = el("input", { type: "range", min: String(row.min), max: String(row.max), step: String(row.step || 1),
    value: row.value, "aria-label": label });
  const shown = el("output", { class: "val" }, prettyNumber(row.key, row.value));
  let timer = null, busy = false;
  const save = async (dragging) => {
    busy = true;
    try {
      const { res, data } = await settingPost(row, range.value);
      if (dragging) return;
      if (res.ok && data.setting) range.value = row.value = data.setting.value;
      else if (res.ok) row.value = range.value;
      else {
        range.value = row.value;
        toast(data.error || res.statusText, "bad");
      }
      shown.textContent = prettyNumber(row.key, range.value);
    } finally {
      busy = false;
    }
  };
  range.addEventListener("input", () => {
    shown.textContent = prettyNumber(row.key, range.value);
    clearTimeout(timer);
    timer = setTimeout(() => { if (!busy) save(true); }, 300);
  });
  range.addEventListener("change", () => { clearTimeout(timer); save(false); });
  const stepper = (sign) => {
    const b = el("button", { type: "button", class: "step", "aria-label": t(sign < 0 ? "less" : "more") + ": " + label },
      sign < 0 ? "−" : "+");
    b.addEventListener("click", () => {
      const step = Number(row.step || 1);
      range.value = String(Math.min(Number(row.max), Math.max(Number(row.min), Number(range.value) + sign * step)));
      shown.textContent = prettyNumber(row.key, range.value);
      clearTimeout(timer);
      timer = setTimeout(() => { if (!busy) save(false); }, 400);
    });
    return b;
  };
  return el("div", { class: "slider" }, stepper(-1), range, stepper(1), shown);
}

// prettyNumber: o valor como o Setup mostra (1.00, 6500 K, 100%, +5, 150 ms).
function prettyNumber(key, value) {
  const v = Number(value);
  if (/gamma$/.test(key)) return (v / 100).toFixed(2);
  if (/temperature$/.test(key)) return v + " K";
  if (/(contrast|gain|saturation|strength|thickness|_pct|flash_level)$/.test(key) || key === "scanline.brightness") return v + "%";
  if (/(_ms|latency)$/.test(key)) return v + " ms";
  if (/hue$/.test(key)) return v + "°";
  if (key === "scanline.height") return v ? String(v) : "auto";
  return v > 0 ? "+" + v : String(v);
}

// Os jogos entrelacados: uma linha por programa, o modo em botoes (640x240,
// entrelacado com filtro, entrelacado puro) e, so com o filtro, o nivel dele
// na mesma linha, logo embaixo. O Setup manda duas linhas por programa
// (mode480.CHAVE e deflicker.CHAVE); aqui elas viram uma so. Os primeiros
// ficam a vista; o resto atras de "Mais N programas".
const M480_SHOWN = 6;

function mode480Rows(items) {
  const levels = new Map(items.filter((r) => r.key.startsWith("deflicker.")).map((r) => [r.key.slice(10), r]));
  const rows = items.filter((r) => r.key.startsWith("mode480.")).map((r) => mode480Row(r, levels.get(r.key.slice(8))));
  if (rows.length > M480_SHOWN + 1) {
    const rest = rows.slice(M480_SHOWN);
    rest.forEach((r) => { r.hidden = true; });
    const names = rest.map((r) => r.dataset.name);
    const more = uiClickable(uiRow({ label: t("setup_more").replace("%n", rest.length),
      sub: names.slice(0, 4).join(", ") + (names.length > 4 ? "…" : ""), control: icon("g-chevd"), cls: "more-row" }), () => {
      rest.forEach((r) => { r.hidden = false; });
      more.remove();
    });
    rows.splice(M480_SHOWN, 0, more);
  }
  return rows;
}

function mode480Row(row, level) {
  let lvl = null;
  const options = row.options.map((o) => ({ value: o.value, label: t("m480s_" + o.value) }));
  const r = uiRow({ label: row.label, help: lang === "pt" ? "" : row.help, cls: "m480",
    control: uiChoice(options, row.value, row.label, async (value) => {
      const ok = await settingSave(row, value);
      if (ok) drawLevel();
      return ok;
    }) });
  r.dataset.name = row.label;
  function drawLevel() {
    if (lvl) lvl.remove();
    lvl = null;
    if (!level || row.value !== "filter") return;
    lvl = el("div", { class: "lvl" }, el("span", {}, t("m480_level_short")),
      uiChoice(level.options.map((o) => ({ value: o.value, label: t("m480_" + o.value) })), level.value,
        t("m480_level_short") + ": " + row.label, (value) => settingSave(level, value)));
    r.append(lvl);
  }
  drawLevel();
  return r;
}

// ── As caixas que nao vem do --settings ──────────────────────────

// Setup > Network: as placas, as redes ao alcance (so ao pedir: a busca leva
// uns segundos) e conectar com a senha.
async function wifiRows() {
  const devices = (await (await api("/api/wifi")).json()).devices || [];
  const wifi = devices.filter((d) => d.type === "wifi");
  const joined = new Set(wifi.filter((d) => d.state === "connected").map((d) => d.connection));
  const rows = devices.map((d) => uiRow({ label: d.connection || d.device, sub: [d.device, d.ip].filter(Boolean).join(" · "),
    control: d.state === "connected" ? el("span", { class: "okmark" }, icon("g-check"), t(d.type === "wifi" ? "wifi_connected" : "bt_connected"))
      : el("span", { class: "dim" }, d.state) }));
  if (!wifi.length) return [...rows, uiRow({ label: "Wi-Fi", sub: t("wifi_none") })];
  let found = [];
  const scanRow = uiRow({ label: t("wifi_scan"), control: uiButton(t("wifi_scan_go"), async () => {
    found.forEach((n) => n.remove());
    found = [uiRow({ label: t("wifi_scanning"), cls: "dim-row" })];
    scanRow.after(...found);
    const r = await api("/api/wifi?scan=1");
    const nets = (await r.json()).networks || [];
    found.forEach((n) => n.remove());
    found = nets.length ? nets.map((n) => uiRow({ label: n.ssid, before: [wifiBars(Number(n.signal))], sub: n.security || t("wifi_open"),
      control: joined.has(n.ssid) ? el("span", { class: "okmark" }, icon("g-check"), t("wifi_connected"))
        : uiButton(t("wifi_connect"), () => wifiConnect(n.device, n.ssid, !!n.security, false)) }))
      : [uiRow({ label: t("wifi_nonet"), cls: "dim-row" })];
    scanRow.after(...found);
  }) });
  const hidden = uiRow({ label: t("wifi_hidden"), sub: t("wifi_hidden_sub"), control: uiButton(t("wifi_connect"), async () => {
    const ssid = await ask({ title: t("wifi_hidden"), text: t("wifi_name"), input: "" });
    if (ssid) wifiConnect(wifi[0].device, ssid, true, true);
  }) });
  return [...rows, scanRow, hidden];
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

// Setup > System > Password: Trocar abre a de agora e a nova duas vezes.
function passwordRow() {
  const field = (key, auto) => uiField({ type: "password", autocomplete: auto, "aria-label": t(key), placeholder: t(key) });
  const current = field("pw_current", "current-password"), first = field("pw_new", "new-password"), again = field("pw_again", "new-password");
  const save = el("button", { type: "submit", class: "btn small" }, t("pw_save"));
  const form = el("form", { class: "srow-form", hidden: "" }, current, first, again, el("div", { class: "srow-form-foot" }, save),
    el("p", { class: "dim" }, t("pw_note")));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (first.value !== again.value) return toast(t("pw_diff"), "bad");
    if (first.value.length < 4) return toast(t("pw_short"), "bad");
    save.disabled = true;
    try {
      const r = await api("/api/password", { method: "POST", body: JSON.stringify({ current: current.value, password: first.value }) });
      const data = await r.json().catch(() => ({}));
      toast(r.ok ? t("pw_done") : r.status === 403 ? t("pw_wrong") : (data.error || r.statusText), r.ok ? "ok" : "bad");
      if (r.ok) {
        form.reset();
        form.hidden = true;
      }
    } finally {
      save.disabled = false;
    }
  });
  const open = uiButton(t("pw_change"), () => {
    form.hidden = !form.hidden;
    if (!form.hidden) current.focus();
  });
  return uiRow({ label: t("si_password"), sub: t("sih_password"), control: open, after: [form] });
}

// Video Setup > Geometry: o crt_range em uso (o publicado para o monitor, ou
// um digitado). O ajuste com a grade de teste e no tubo (Abrir no gabinete).
async function geometryRows(ctx) {
  const g = ctx ? await ctx.json("/api/geometry") : await (await api("/api/geometry")).json();
  const field = el("input", { type: "text", class: "fld code-txt", value: g.range || g.preset || "", spellcheck: "false",
    "aria-label": "crt_range0" });
  const save = uiButton(t("geo_save"), async () => {
    const r = await api("/api/geometry", { method: "POST", body: JSON.stringify({ action: "set", range: field.value }) });
    toast(r.ok ? t("geo_saved") : r.status === 409 ? t("geo_freq") : t("geo_bad"), r.ok ? "ok" : "bad");
    if (r.ok) loadSettings().catch(() => {});
  });
  save.hidden = true;
  field.addEventListener("input", () => { save.hidden = field.value === (g.range || g.preset || ""); });
  field.addEventListener("keydown", (ev) => { if (ev.key === "Enter") { ev.preventDefault(); save.click(); } });
  return [uiRow({ label: t("geo_monitor"), sub: (g.label || g.monitor || "-") + " · " + t(g.range ? "geo_custom" : "geo_preset"),
    control: save, help: t("geo_note"), after: [field], cls: "has-field" })];
}

// Setup > System > FliperOS version: os updates da imagem ao mais novo (a
// lista vem da rede). "Usar" leva o gabinete a um (fliperos-update goto,
// como tarefa); um mais velho fica preso nele ate sair um update novo, e
// "Seguir os updates" volta ao mais novo.
async function versionPage(box) {
  const body = el("div", {}, el("p", { class: "dim setup-loading" }, el("span", { class: "spinner" }), t("setup_loading")));
  box.append(el("h2", {}, t("si_version")), el("p", { class: "lead" }, t("sih_version")), body);
  const r = await api("/api/versions");
  if (!r.ok) {
    body.replaceChildren(el("p", { class: "dim" }, t("ver_error")));
    return;
  }
  const v = await r.json();
  const tags = [v.level === v.latest && v.hold == null ? t("ver_newest") : "", v.hold != null ? t("ver_held") : ""].filter(Boolean);
  const now = uiRow({ label: t("ver_now").replace("%s", v.level), sub: tags.join(" · "),
    control: v.hold != null ? uiButton(t("ver_follow"), () => versionGo("latest", v)) : "" });
  const rows = (v.updates || []).map((u) => {
    const use = uiButton(t("ver_use"), () => versionGo(u.n, v));
    use.disabled = u.state === "current" && (v.hold != null || v.level === v.latest);
    return uiRow({ label: u.title, before: [el("span", { class: "vnum" }, String(u.n))],
      sub: [u.state === "current" ? t("ver_installed") : "", u.reboot ? t("ver_restart") : ""].filter(Boolean).join(" · "),
      control: u.state === "current" && use.disabled ? el("span", { class: "okmark" }, icon("g-check"), t("ver_installed")) : use });
  });
  body.replaceChildren(uiSection("", [now], v.reboot ? t("ver_reboot") : ""), uiSection(t("ss_updates"), rows, t("ver_note")));
}

async function versionGo(target, v) {
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

// Setup > System > What's new: o que mudou em cada versao e os updates.
async function whatsnewPage(box) {
  const pre = el("pre", { class: "log whatsnew" }, "…");
  box.append(el("h2", {}, t("si_whatsnew")), el("p", { class: "lead" }, t("sih_whatsnew")), pre);
  const r = await api("/api/whatsnew");
  pre.textContent = ((await r.json()).text || "").trim() || t("wn_none");
}

// ── Backup na nuvem ──────────────────────────────────────────────
// config/fliperos-cloud: os hi-scores, saves e configuracoes numa nuvem pelo
// rclone. Google Drive e Dropbox pelo login do site (o endereco da pagina que
// nao abre volta colado aqui); WebDAV, SFTP e Mega com usuario e senha.
// Sincroniza ao apertar e, ligado, ao fechar cada jogo.
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
  const page = el("div", { class: "spage" }, el("h2", {}, t("sub_cloud")), el("p", { class: "lead" }, t("cl_lead")));
  if (!state.installed) {
    page.append(uiSection("", [uiRow({ label: "rclone", sub: t("cl_missing"), control: uiButton(t("cl_install"), async () => {
      if (await post({ action: "install" })) { toast(t("inst_started")); loadTasks().catch(() => {}); }
    }) })]));
  } else if (!state.remote) {
    const kind = el("select", { class: "sel", "aria-label": t("cl_provider") },
      // O Google Drive so com o cliente do FliperOS (Entrar com o Google).
      ...["drive", "dropbox", "webdav", "sftp", "mega"].filter((k) => k !== "drive" || state.device)
        .map((k) => el("option", { value: k }, t("cl_" + k))));
    const area = el("div", { class: "srow-form stack" });
    let polling = null;
    const draw = () => {
      if (polling) { clearTimeout(polling); polling = null; }
      if (kind.value === "drive") {
        // Entrar com o Google, como numa smart TV: o QR code e o codigo; a
        // espera roda no gabinete, e o painel so le o estado a cada 2 s.
        const go = el("button", { type: "button", class: "btn small" }, t("cl_google"));
        const box = el("div", { class: "stack google-wait", hidden: "" });
        const cancel = el("button", { type: "button", class: "btn ghost small" }, t("cancel"));
        let shown = "";
        const show = (s) => {
          if (s.state === "ok") { toast(t("cl_connected").replace("%s", s.account || "Google Drive"), "ok"); reload(); return true; }
          if (s.state === "denied" || s.state === "error" || s.state === "stopped") {
            box.replaceChildren(el("div", { class: "bad" }, s.error || t("cl_google_stopped")));
            go.hidden = false;
            return true;
          }
          if (s.state === "syncing") {
            // A primeira sincronizacao, com a barra (pct do fliperos-cloud).
            const pct = /^\d+$/.test(s.pct || "") ? Number(s.pct) : null;
            box.replaceChildren(el("div", {}, t("cl_google_syncing").replace("%s", s.account || "") + (pct != null ? " " + pct + "%" : "")),
              ...(pct != null ? [stMeter(pct, "")] : []));
          } else if (s.code && s.code !== shown) {
            shown = s.code;
            const qr = el("div", { class: "qr" });
            qr.innerHTML = s.qr || "";
            box.replaceChildren(el("div", { class: "row start google-row" }, qr, el("div", { class: "stack" },
              el("div", {}, t("cl_code_step1")),
              el("a", { class: "btn-text", href: s.url, target: "_blank", rel: "noopener" }, s.url.replace(/^https?:\/\//, "")),
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
        const inputs = CLOUD_FIELDS[kind.value].map((f) => uiField({ type: f === "pass" ? "password" : "text",
          "aria-label": t("cl_f_" + f), placeholder: t("cl_f_" + f) }));
        const save = el("button", { type: "submit", class: "btn small" }, t("cl_save"));
        const form = el("form", { class: "stack" }, ...inputs, el("div", { class: "srow-form-foot" }, save));
        form.addEventListener("submit", async (event) => {
          event.preventDefault();
          save.disabled = true;
          const fields = Object.fromEntries(CLOUD_FIELDS[kind.value].map((f, i) => [f, inputs[i].value.trim()]));
          try { if (await post({ action: "remote", kind: kind.value, fields })) { toast(t("cl_saved"), "ok"); reload(); } }
          finally { save.disabled = false; }
        });
        area.replaceChildren(form);
      } else {
        const start = el("button", { type: "button", class: "btn small" }, t("cl_signin"));
        const answer = uiField({ type: "text", "aria-label": t("cl_paste"), placeholder: t("cl_paste") });
        const done = el("button", { type: "submit", class: "btn small" }, t("cl_save"));
        const form = el("form", { class: "stack", hidden: "" }, el("div", { class: "dim" }, t("cl_paste_help")), answer,
          el("div", { class: "srow-form-foot" }, done));
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
        area.replaceChildren(el("div", { class: "srow-form-foot" }, start), form);
      }
    };
    kind.addEventListener("change", draw);
    draw();
    page.append(uiSection("", [uiRow({ label: t("cl_provider"), control: kind, after: [area] })]));
  } else {
    const what = (w) => uiRow({ label: t("cl_w_" + w), control: uiSwitch(state.what.includes(w), t("cl_w_" + w), async (on) => {
      const chosen = new Set(state.what);
      if (on) chosen.add(w); else chosen.delete(w);
      const list = ["hiscores", "saves", "config"].filter((x) => chosen.has(x));
      if (!(await post({ action: "what", what: list }))) return false;
      state.what = list;
      return true;
    }) });
    const auto = uiRow({ label: t("cl_auto"), control: uiSwitch(state.auto, t("cl_auto"), async (on) => !!(await post({ action: "auto", on }))) });
    const run = (direction, label) => uiButton(t(label), () => startTask("/api/cloud", { action: "sync", direction }), direction === "both" ? "" : "quiet");
    const forget = uiButton(t("cl_forget_go"), async () => {
      if (!(await ask({ title: t("group_Cloud"), text: t("cl_forget_ask"), yes: t("cl_forget"), danger: true }))) return;
      if (await post({ action: "forget" })) reload();
    }, "red");
    const last = state.last ? new Date(state.last * 1000).toLocaleString() + (state.result === "failed" ? " · " + t("cl_failed") : "") : t("cl_never");
    page.append(uiSection(t("ra_account"), [uiRow({ label: t("cl_" + state.remote) || state.remote, sub: state.account || "", control: forget })]),
      uiSection(t("cl_what"), ["hiscores", "saves", "config"].map(what)),
      uiSection("", [auto, uiRow({ label: t("cl_sync"), sub: t("cl_last").replace("%s", last), cls: "wrap-ctl",
        control: [run("both", "cl_sync_go"), run("push", "cl_push_go"), run("pull", "cl_pull_go")] })]));
  }
  page.append(el("p", { class: "ssec-note" }, t("cl_note")));
  return page;
}

// ── RetroAchievements ────────────────────────────────────────────
// Entrar com a conta do site (so o token fica no gabinete), ligar as
// conquistas e o modo hardcore, a Web API Key, sair.
async function cheevosPage() {
  const state = await (await api("/api/cheevos")).json();
  const post = async (body) => {
    const r = await api("/api/cheevos", { method: "POST", body: JSON.stringify(body) });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) toast(data.error || r.statusText, "bad");
    return r.ok;
  };
  const reload = () => loadCheevos().catch(() => {});
  const page = el("div", { class: "spage" }, el("h2", {}, "RetroAchievements"), el("p", { class: "lead" }, t("ra_lead")));
  if (state.user) {
    const onOff = (key, value) => uiRow({ label: t("ra_" + key), control: uiSwitch(value, t("ra_" + key), async (on) => {
      const ok = await post({ action: key, on });
      if (ok) reload();
      return ok;
    }) });
    const out = uiButton(t("ra_logout"), async () => {
      if (!(await ask({ title: "RetroAchievements", text: t("ra_logout_ask").replace("%s", state.user), yes: t("ra_logout") }))) return;
      if (await post({ action: "logout" })) reload();
    });
    // A Web API Key da conta: com ela o frontend mostra as conquistas de cada jogo.
    const key = uiField({ type: "password", "aria-label": t("ra_apikey"), placeholder: state.apikey ? t("ra_apikey_set") : t("ra_apikey") });
    const save = el("button", { type: "submit", class: "btn small" }, t("ra_apikey_save"));
    // A aba da conta no site onde fica a chave (Settings > Applications), numa aba nova.
    const where = el("a", { class: "btn-text", href: "https://retroachievements.org/settings?tab=applications", target: "_blank",
      rel: "noopener" }, t("ra_apikey_get"));
    const keyForm = el("form", { class: "srow-form inline" }, key, save);
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
    page.append(uiSection(t("ra_account"), [uiRow({ label: state.user, sub: t("ra_as").replace("%s", state.user), control: out }),
      onOff("enable", state.enabled), onOff("hardcore", state.hardcore)]),
    uiSection(t("ra_key_title"), [uiRow({ label: t("ra_apikey"), sub: t("ra_apikey_hint"), control: where, after: [keyForm], cls: "has-field" })]));
  } else {
    const user = uiField({ "aria-label": t("user"), placeholder: t("user") });
    const pass = uiField({ type: "password", "aria-label": t("password"), placeholder: t("password") });
    const go = el("button", { type: "submit", class: "btn small" }, t("ra_login"));
    const form = el("form", { class: "srow-form" }, user, pass, el("div", { class: "srow-form-foot" }, go));
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
    const signup = el("a", { class: "btn-text", href: "https://retroachievements.org/createaccount.php",
      target: "_blank", rel: "noopener" }, t("ra_signup"));
    page.append(uiSection(t("ra_account"), [uiRow({ label: t("ra_login"), after: [form], cls: "has-field" }),
      uiRow({ label: t("ra_no_account"), control: signup })]));
  }
  page.append(el("p", { class: "ssec-note" }, t("ra_note")));
  return page;
}

// As abas Sistema > RetroAchievements e Sistema > Backup na nuvem.
async function loadCheevos() {
  $("cheevos-page").replaceChildren(await cheevosPage());
}
async function loadCloud() {
  $("cloud-page").replaceChildren(await cloudPage());
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
      theme: { background: "#08090c", foreground: "#f8f8f2", cursor: "#f8f8f2", selectionBackground: "#44475a",
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
