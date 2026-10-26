// Biblioteca > Filtro de ROMs.
"use strict";

// ── ROM filter ───────────────────────────────────────────────────
// O filtro do MAME ROM Cleaner (os parametros, os presets e as opcoes vem do
// Setup: /api/romfilter, fliperos-setup --romfilter). Dois usos: o filtro
// do Downloader (o que ele baixa dos torrents; Save o grava) ou limpar uma
// pasta com um romset (a previa e copiar ou mover para a pasta do emulador,
// como tarefa). Como o painel de azulejos do Setup: cada parametro e um
// azulejo com o valor e um desenho pequeno; o de duas opcoes troca no
// clique, os outros abrem as opcoes num dialogo. O placar conta os jogos e
// o tamanho do que passa, a cada mudanca; so vale a ultima contagem.

const rf = { mode: "downloader", target: "", folder: "", info: null, values: {}, base: {}, preset: "cabinet",
  seq: 0, timer: null, loaded: false, task: null, items: [], dirPath: "" };

// Os grupos dos azulejos (as chaves do Setup; uma nova cai em Outros).
const RF_GROUPS = [
  ["rf_g_games", ["arcade", "status", "clones", "region", "bootlegs", "prototypes", "mature", "chd", "vector"]],
  ["rf_g_play", ["players", "buttons", "controls", "modes"]],
  ["rf_g_screen", ["orientation", "lines"]],
  ["rf_g_kind", ["genres", "decades"]],
  ["rf_g_hardware", ["hardware", "systems"]],
];

function rfParams() {
  return rf.info ? rf.info.params.filter((p) => p.visible) : [];
}

function rfPresetValues(name) {
  const preset = rf.info && rf.info.presets.find((p) => p.value === name);
  return preset ? Object.assign({}, preset.values) : {};
}

async function loadRomFilter(target, keep) {
  const query = "target=" + encodeURIComponent(target || rf.target || "groovymame") +
    (rf.mode === "cleaner" && rf.folder ? "&folder=" + encodeURIComponent(rf.folder) : "");
  const res = await api("/api/romfilter?" + query);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { $("rf-note").textContent = data.error || res.statusText; return; }
  const saved = data.saved;
  // A primeira vez no Downloader: o emulador do filtro salvo.
  if (!rf.loaded && rf.mode === "downloader" && saved && saved.target && saved.target !== (target || "groovymame") &&
      data.targets.some((x) => x.value === saved.target)) {
    rf.loaded = true;
    return loadRomFilter(saved.target);
  }
  rf.info = data;
  rf.target = target || rf.target || "groovymame";
  if (keep) {
    // A pasta mudou, o emulador nao: os valores ficam.
  } else if (rf.mode === "downloader" && saved && saved.target === rf.target) {
    rf.preset = saved.preset || "custom";
    rf.values = {};
    for (const p of data.params) rf.values[p.key] = saved[p.key] != null ? saved[p.key] : "";
    rf.base = Object.assign({}, rf.values);
  } else {
    // O MAME 2010 comeca so com a placa do PlayStation, como no Setup.
    rf.preset = rf.target === "mame2010" ? "psx" : "cabinet";
    rf.values = rfPresetValues(rf.preset);
    rf.base = Object.assign({}, rf.values);
  }
  rf.loaded = true;
  renderRomFilter();
  rfCount();
}

function renderRomFilter() {
  const info = rf.info;
  if (!info) return;
  document.querySelectorAll(".rf-tabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.mode === rf.mode)));
  $("rf-source").hidden = rf.mode !== "cleaner";
  $("rf-folder").textContent = rf.folder || t("rf_no_folder");
  $("rf-folder").classList.toggle("empty", !rf.folder);
  $("rf-browse").textContent = rf.folder ? t("rf_change") : t("rf_choose");
  $("rf-target").replaceChildren(...info.targets.map((x) => el("option", { value: x.value }, x.label)));
  $("rf-target").value = rf.target;
  const presets = info.presets.map((p) => el("option", { value: p.value }, p.label));
  presets.push(el("option", { value: "custom" }, t("rf_custom")));
  $("rf-preset").replaceChildren(...presets);
  $("rf-preset").value = rf.preset;
  $("rf-data").textContent = info.data || "-";
  $("rf-dest").textContent = rf.mode === "downloader" ? t("rf_dest_dl") : (info.dest ? info.dest.label : "-");
  $("rf-save").hidden = rf.mode !== "downloader";
  $("rf-scan").hidden = rf.mode !== "cleaner";
  $("rf-scan").disabled = !rf.folder;
  $("rf-note").textContent = rf.mode === "downloader"
    ? (info.saved_label ? t("rf_saved_now").replace("%s", info.saved_label) : t("rf_not_saved")) : "";
  renderBoard();
}

function renderBoard() {
  const byKey = new Map(rfParams().map((p) => [p.key, p]));
  const groups = RF_GROUPS.map(([label, keys]) => [label, keys.filter((k) => byKey.has(k))]);
  const rest = [...byKey.keys()].filter((k) => !RF_GROUPS.some(([, keys]) => keys.includes(k)));
  if (rest.length) groups.push(["rf_g_other", rest]);
  $("rf-board").replaceChildren(...groups.filter(([, keys]) => keys.length).map(([label, keys]) =>
    el("section", { class: "rf-group" }, el("h3", {}, t(label)),
      el("div", { class: "rf-tiles" }, ...keys.map((k) => rfTile(byKey.get(k)))))));
}

// O rotulo curto de uma opcao (sem o parentese: "Low (up to 288 lines...)").
const rfNum = (n) => Number(n).toLocaleString(lang === "pt" ? "pt-BR" : "en");
const rfShort = (o) => o.label.replace(/\s*\(.*\)\s*$/, "");

function rfEmptyText(p) {
  return t(p.key === "controls" ? "rf_s_buttons" : p.key === "hardware" ? "rf_s_any" : "rf_s_all");
}

function rfSummary(p, value) {
  if (p.type === "radio") {
    const o = p.options.find((x) => x.value === value);
    return o ? rfShort(o) : value || "-";
  }
  const set = new Set((value || "").split(","));
  const picked = p.options.filter((o) => set.has(o.value));
  if (!picked.length) return rfEmptyText(p);
  if (picked.length === p.options.length) return t("rf_s_all");
  if (picked.length <= 2) return picked.map(rfShort).join(", ");
  return t("rf_s_n_of").replace("%n", picked.length).replace("%m", p.options.length);
}

function rfVisual(p, value) {
  const opts = p.options.map((o) => o.value);
  if (p.type === "radio" && opts.length > 2 && opts.every((v) => /^\d+$/.test(v))) {
    // Jogadores e botoes: as figuras acesas ate o numero (Any: todas).
    const max = Math.max(...opts.map(Number)), n = Number(value) || max;
    const box = el("span", { class: "rf-pips" + (p.key === "players" ? " people" : ""), "aria-hidden": "true" });
    for (let i = 1; i <= max; i++) box.append(el("i", { class: i <= n ? "on" : "" }));
    return box;
  }
  if (p.key === "status") {
    const n = opts.indexOf(value) + 1, box = el("span", { class: "rf-lamps", "aria-hidden": "true" });
    for (let i = 1; i <= opts.length; i++) box.append(el("i", { class: i <= n ? "on l" + i : "" }));
    return box;
  }
  if (p.type === "radio" && opts.length === 2 && (opts.includes("yes") || opts.includes("no"))) {
    return el("span", { class: "rf-switch" + (value === "yes" ? " on" : ""), "aria-hidden": "true" }, el("i"));
  }
  if (p.type === "check" && opts.length <= 6) {
    const set = new Set((value || "").split(",")), all = !value && p.key !== "controls" && p.key !== "hardware";
    const box = el("span", { class: "rf-blocks " + p.key, "aria-hidden": "true" });
    for (const o of p.options) box.append(el("i", { class: all || set.has(o.value) ? "on" : "" }));
    return box;
  }
  return null;
}

function rfTile(p) {
  const value = rf.values[p.key] || "";
  const toggle = p.type === "radio" && p.options.length === 2;
  const attrs = { type: "button", class: "rf-tile" + ((rf.base[p.key] || "") !== value ? " changed" : ""), title: p.help };
  if (!toggle) attrs["aria-haspopup"] = "dialog";
  // Sem desenho, uma linha a mais: o que esta marcado, ou o que o parametro faz.
  let visual = rfVisual(p, value);
  if (!visual) {
    const set = new Set(value.split(","));
    const picked = p.type === "check" ? p.options.filter((o) => set.has(o.value)).map(rfShort) : [];
    const detail = picked.length && picked.length < p.options.length ? picked.join(", ") : p.help;
    visual = el("span", { class: "rf-tile-detail" }, detail);
  }
  const tile = el("button", attrs, el("span", { class: "rf-tile-title" }, p.title),
    el("span", { class: "rf-tile-value" }, rfSummary(p, value)), visual);
  tile.addEventListener("click", () => {
    if (!toggle) { rfEdit(p); return; }
    rf.values[p.key] = (p.options.find((o) => o.value !== value) || p.options[0]).value;
    rfChanged();
  });
  return tile;
}

function rfChanged() {
  rf.preset = "custom";
  $("rf-preset").value = "custom";
  rfHidePreview();
  renderBoard();
  rfCount();
}

// O dialogo das opcoes: as de uma escolha fecham ao escolher; as de varias
// ficam abertas (o placar conta atras), com busca nas listas longas.
function rfDialog(title, help) {
  $("rf-dlg-title").textContent = title;
  $("rf-dlg-help").textContent = help || "";
  $("rf-dlg-help").hidden = !help;
  return $("rf-dialog");
}

function rfEdit(p) {
  const dlg = rfDialog(p.title, p.help);
  const body = $("rf-dlg-body");
  $("rf-dlg-foot").replaceChildren(el("button", { value: "close" }, t("rf_done")));
  if (p.type === "radio") {
    body.replaceChildren(el("div", { class: "rf-choices", role: "listbox", "aria-label": p.title },
      ...p.options.map((o) => {
        const b = el("button", { type: "button", class: "rf-choice", role: "option",
          "aria-selected": String(o.value === (rf.values[p.key] || "")) }, o.label);
        b.addEventListener("click", () => { rf.values[p.key] = o.value; dlg.close(); rfChanged(); });
        return b;
      })));
  } else {
    const picked = new Set((rf.values[p.key] || "").split(",").filter(Boolean));
    const chips = el("div", { class: "chips" }), hint = el("p", { class: "dim" });
    const note = () => {
      hint.textContent = picked.size ? t("rf_n_marked").replace("%n", picked.size).replace("%m", p.options.length)
        : rfEmptyText(p) + " · " + t("rf_none_means");
    };
    const save = () => {
      rf.values[p.key] = p.options.map((o) => o.value).filter((v) => picked.has(v)).join(",");
      note();
      rfChanged();
    };
    const draw = () => chips.replaceChildren(...p.options.map((o) => {
      const c = el("button", { type: "button", "aria-pressed": String(picked.has(o.value)) }, o.label);
      c.addEventListener("click", () => {
        if (picked.has(o.value)) picked.delete(o.value); else picked.add(o.value);
        c.setAttribute("aria-pressed", String(picked.has(o.value)));
        save();
      });
      return c;
    }));
    const tools = el("div", { class: "chip-tools" });
    if (p.options.length > 12) {
      const search = el("input", { type: "search", placeholder: t("rf_find"), "aria-label": t("rf_find") });
      // Enter no campo nao fecha o dialogo (o form dele e method=dialog).
      search.addEventListener("keydown", (ev) => { if (ev.key === "Enter") ev.preventDefault(); });
      search.addEventListener("input", () => {
        const q = search.value.trim().toLowerCase();
        chips.querySelectorAll("button").forEach((c) => { c.hidden = !!q && !c.textContent.toLowerCase().includes(q); });
      });
      tools.append(search);
    }
    const all = el("button", { type: "button", class: "ghost" }, t("rf_all"));
    const none = el("button", { type: "button", class: "ghost" }, t("rf_none"));
    all.addEventListener("click", () => { p.options.forEach((o) => picked.add(o.value)); draw(); save(); });
    none.addEventListener("click", () => { picked.clear(); draw(); save(); });
    tools.append(all, none);
    draw();
    note();
    body.replaceChildren(tools, chips, hint);
  }
  dlg.showModal();
}

// As pastas, no mesmo dialogo: os lugares de sempre, depois a arvore.
async function rfDirs(path) {
  const dlg = rfDialog(t("rf_folder"), t("rf_folder_help"));
  const body = $("rf-dlg-body"), foot = $("rf-dlg-foot");
  const res = await api("/api/dirs?path=" + encodeURIComponent(path || ""));
  const data = await res.json().catch(() => ({}));
  const cancel = el("button", { value: "close", class: "ghost" }, t("cancel"));
  if (!res.ok) {
    body.replaceChildren(el("p", { class: "error" }, data.error || res.statusText));
    foot.replaceChildren(cancel);
  } else {
    rf.dirPath = data.path;
    const list = el("div", { class: "rf-dirs" });
    const go = (label, to) => {
      const b = el("button", { type: "button", title: to }, label);
      b.addEventListener("click", () => rfDirs(to).catch(() => {}));
      list.append(b);
    };
    if (!data.path) {
      data.places.forEach((place) => go("💾 " + place, place));
      go("📁 /", "/");
    } else {
      go("⬆ ..", data.parent);
      data.dirs.forEach((name) => go("📁 " + name, (data.path === "/" ? "" : data.path) + "/" + name));
      if (!data.dirs.length) list.append(el("p", { class: "dim" }, t("rf_no_subfolders")));
    }
    body.replaceChildren(...(data.path ? [el("p", { class: "rf-path" }, data.path)] : []), list);
    const use = el("button", { type: "button", "data-icon": "✔" }, t("rf_use_this"));
    use.disabled = !data.path;
    use.addEventListener("click", () => {
      rf.folder = data.path;
      dlg.close();
      rfHidePreview();
      rfPickFolder().catch(() => {});
    });
    foot.replaceChildren(cancel, use);
  }
  if (!dlg.open) dlg.showModal();
}

async function rfPickFolder() {
  // O emulador provavel pelo nome da pasta (como no Setup), e o filtro dele.
  await loadRomFilter(rf.target, true);
  const guess = rf.info && rf.info.default_target;
  if (guess && guess !== rf.target) await loadRomFilter(guess);
}

function rfBody(extra) {
  return JSON.stringify(Object.assign({ target: rf.target, folder: rf.mode === "cleaner" ? rf.folder : "",
    values: rf.values }, extra || {}));
}

function rfCount() {
  clearTimeout(rf.timer);
  const score = document.querySelector(".rf-score");
  if (rf.mode === "cleaner" && !rf.folder) {
    score.classList.remove("busy");
    $("rf-games").textContent = "-"; $("rf-size").textContent = "-";
    $("rf-count-note").textContent = t("rf_pick_folder");
    return;
  }
  score.classList.add("busy");
  $("rf-count-note").textContent = t("rf_counting");
  rf.timer = setTimeout(async () => {
    const seq = ++rf.seq;
    const res = await api("/api/romfilter/count", { method: "POST", body: rfBody() }).catch(() => null);
    if (seq !== rf.seq || !res || res.status === 409) return;
    const data = await res.json().catch(() => ({}));
    score.classList.remove("busy");
    if (res.ok) {
      $("rf-games").textContent = data.games != null ? rfNum(data.games) : "-";
      $("rf-size").textContent = data.bytes != null ? bytes(Number(data.bytes)) : "-";
      $("rf-count-note").textContent = rf.mode === "downloader" ? t("rf_from_torrent") : t("rf_from_folder");
    } else {
      $("rf-games").textContent = "-"; $("rf-size").textContent = "-";
      $("rf-count-note").textContent = data.error || res.statusText;
    }
  }, 450);
}

async function rfSave() {
  $("rf-note").textContent = t("rf_saving");
  const res = await api("/api/romfilter/save", { method: "POST", body: rfBody({ preset: rf.preset }) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { $("rf-note").textContent = data.error || res.statusText; return; }
  if (rf.info) rf.info.saved_label = data.saved || "";
  rf.base = Object.assign({}, rf.values);
  $("rf-note").textContent = t("rf_saved_now").replace("%s", data.saved || "");
  renderBoard();
  toast(t("rf_saved_toast"));
}

function rfHidePreview() {
  const card = $("rf-preview");
  card.setAttribute("data-off", "");
  card.hidden = true;
}

function rfStat(label, value, bad) {
  return el("div", { class: "rf-stat" + (bad ? " bad" : "") }, el("small", {}, label), el("strong", {}, value));
}

function rfRows(query) {
  const q = (query || "").trim().toLowerCase();
  const rows = rf.items.filter((i) => !q || i.name.toLowerCase().includes(q) || i.title.toLowerCase().includes(q));
  const shown = rows.slice(0, 1500);
  const body = el("tbody", {}, ...shown.map((i) => el("tr", {}, el("td", { title: i.name }, i.name),
    el("td", { title: i.title }, i.title))));
  if (rows.length > shown.length) {
    body.append(el("tr", {}, el("td", { colspan: "2", class: "dim" }, t("first").replace("%n", shown.length))));
  }
  return el("table", {}, body);
}

async function rfScan() {
  const card = $("rf-preview"), box = $("rf-preview-body");
  card.removeAttribute("data-off");
  card.hidden = false;
  box.replaceChildren(el("p", { class: "dim" }, t("rf_reading")));
  card.scrollIntoView({ behavior: "smooth", block: "start" });
  const res = await api("/api/romfilter/scan", { method: "POST", body: rfBody() });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { box.replaceChildren(el("p", { class: "error" }, data.error || res.statusText)); return; }
  const s = data.summary || {};
  rf.items = data.items || [];
  const tooBig = (s.move_bytes || 0) > (s.free_bytes || 0);
  const stats = el("div", { class: "rf-stats" },
    rfStat(t("rf_going"), t("rf_sets_n").replace("%n", rfNum(s.move || 0))),
    rfStat(t("rf_size"), bytes(s.move_bytes || 0)),
    rfStat(t("rf_free"), bytes(s.free_bytes || 0) + (tooBig ? " · " + t("rf_no_space") : ""), tooBig),
    rfStat(t("rf_in_folder"), t("rf_sets_n").replace("%n", rfNum(s.sets || 0))),
    rfStat(t("rf_needed"), String(s.needed || 0)));
  if (s.unknown) stats.append(rfStat(t("rf_unknown"), String(s.unknown)));
  const parts = [stats, el("p", { class: "rf-meta" }, t("rf_to") + " ", el("span", { id: "rf-prev-dest" }, s.dest_label || "-"))];
  if (rf.items.length) {
    const search = el("input", { type: "search", placeholder: t("search"), "aria-label": t("search") });
    const list = el("div", { class: "rf-list" }, rfRows(""));
    search.addEventListener("input", () => list.replaceChildren(rfRows(search.value)));
    parts.push(search, list);
  }
  const actions = el("div", { class: "rf-score-actions" });
  if (s.move > 0) {
    const copy = el("button", { type: "button", "data-icon": "📋" }, t("rf_copy"));
    copy.disabled = tooBig;
    copy.addEventListener("click", () => rfRun("copy"));
    actions.append(copy);
    if (rf.info && rf.info.writable) {
      const move = el("button", { type: "button", class: "ghost", "data-icon": "✂" }, t("rf_move"));
      move.addEventListener("click", () => rfRun("move"));
      actions.append(move);
    }
  } else {
    actions.append(el("span", { class: "dim" }, t("rf_nothing")));
  }
  parts.push(actions, el("div", { id: "rf-run", class: "rf-run", role: "status" }));
  box.replaceChildren(...parts);
}

async function rfRun(transfer) {
  const what = transfer === "move" ? t("rf_confirm_move") : t("rf_confirm_copy");
  if (!confirm(what.replace("%s", rf.folder))) return;
  const res = await api("/api/romfilter/run", { method: "POST", body: rfBody({ transfer }) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { toast(data.error || res.statusText); return; }
  rf.task = data.id;
  rfFollow();
}

async function rfFollow() {
  // O andamento da tarefa aqui mesmo (ela tambem aparece em Arquivos > Tarefas).
  const box = $("rf-run");
  if (!rf.task || !box) return;
  const res = await api("/api/task?id=" + rf.task).catch(() => null);
  if (!res || !res.ok) return;
  const task = await res.json();
  const text = task.running ? (task.step || "…") + (task.pct != null ? " · " + task.pct + "%" : "")
    : task.rc === 0 ? "✓ " + (task.last || t("task_ok")) : "✗ " + (task.error || t("task_fail"));
  box.replaceChildren(...(task.running ? [meter(task.pct || 0)] : []),
    el("span", { class: task.running ? "dim" : task.rc === 0 ? "ok" : "error" }, text));
  if (task.running) setTimeout(rfFollow, 1500); else rf.task = null;
}

document.querySelectorAll(".rf-tabs button").forEach((b) => b.addEventListener("click", () => {
  if (rf.mode === b.dataset.mode) return;
  rf.mode = b.dataset.mode;
  rfHidePreview();
  loadRomFilter(rf.target).catch(() => {});
}));
$("rf-target").addEventListener("change", () => { rfHidePreview(); loadRomFilter($("rf-target").value).catch(() => {}); });
$("rf-preset").addEventListener("change", () => {
  const name = $("rf-preset").value;
  if (name === "custom") return;
  rf.preset = name;
  rf.values = rfPresetValues(name);
  rf.base = Object.assign({}, rf.values);
  rfHidePreview();
  renderBoard();
  rfCount();
});
$("rf-browse").addEventListener("click", () => {
  rfDirs(rf.folder ? rf.folder.split("/").slice(0, -1).join("/") || "/" : "").catch(() => {});
});
$("rf-dialog").addEventListener("click", (ev) => { if (ev.target === $("rf-dialog")) $("rf-dialog").close(); });
$("rf-save").addEventListener("click", () => rfSave().catch(() => {}));
$("rf-scan").addEventListener("click", () => rfScan().catch(() => {}));
