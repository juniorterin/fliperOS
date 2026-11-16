// Sistema > Setup > Jogos > Jogos custom (o Setup > Games > Custom games do
// gabinete): os grupos e os jogos, os pacotes novos, as pastas compactadas e
// a tabela para cadastrar muitos jogos de uma vez (texto e dropdowns, linhas
// novas, importar de uma pasta, colar de uma planilha, duplicar, a arte de
// cada linha). Tudo pelo fliperos-setup --customgames (config/fliperos-web,
// /api/customgames): um jogo so e a tabela com uma linha.
"use strict";

const cg = { info: null, rows: [], seq: 0, el: null, busy: false, defaultGroup: "" };
const CG_DRAFT = "fliperos-cg-draft";
// As colunas da tabela, na ordem; o rotulo de cada uma tambem vai em cada
// celula (no celular a linha vira um cartao).
const CG_COLUMNS = ["group", "name", "platform", "folder", "run", "mode", "category", "players", "buttons", "controls", "art"];
const CG_PLATFORMS = ["windows", "native", "command"];
// Colar de uma planilha: os nomes das colunas que o cabecalho pode ter.
const CG_PASTE_NAMES = {
  name: ["name", "nome", "game", "jogo", "title", "titulo", "título"], group: ["group", "grupo", "system", "sistema"],
  platform: ["type", "tipo", "platform", "plataforma"], folder: ["folder", "pasta", "path", "caminho"],
  run: ["executable", "executavel", "executável", "exe", "command", "comando", "executable or command", "executável ou comando"],
  mode: ["mode", "modo", "video", "vídeo", "resolution", "resolução"], category: ["category", "categoria", "genre", "gênero"],
  players: ["players", "jogadores"], buttons: ["buttons", "botoes", "botões"], controls: ["controls", "controles"],
};
const CG_PASTE_ORDER = ["name", "group", "platform", "folder", "run", "mode", "category", "players", "buttons", "controls"];

// ── A pagina ──

async function customGamesPage(box) {
  const add = el("button", { type: "button", class: "btn small" }, icon("g-plus"), t("cg_add"));
  add.addEventListener("click", () => cgAddOne());
  const group = el("button", { type: "button", class: "btn ghost small" }, t("cg_new_group"));
  group.addEventListener("click", () => cgNewGroup().then((name) => name && cgLoad()));
  const bulk = el("a", { class: "btn ghost small", href: "#cg-bulk" }, t("cg_bulk"));
  bulk.addEventListener("click", (ev) => { ev.preventDefault(); $("cg-bulk").scrollIntoView({ behavior: "smooth" }); });
  const zipInput = el("input", { type: "file", accept: ".zip", hidden: "" });
  zipInput.addEventListener("change", () => { const f = zipInput.files[0]; zipInput.value = ""; if (f) cgInstallZip(f); });
  const zip = el("button", { type: "button", class: "btn ghost small" }, t("cg_install_zip"));
  zip.addEventListener("click", () => zipInput.click());
  cg.el = {
    list: el("div", { class: "cg-list" }),
    pending: el("section", { class: "cg-sec", hidden: "" }),
    packed: el("section", { class: "cg-sec" }),
    bulk: el("section", { class: "cg-sec cg-bulk", id: "cg-bulk" }),
  };
  box.append(el("div", { class: "cg-head" }, el("h2", {}, t("cg_title")), el("p", { class: "lead" }, t("cg_intro")),
    el("div", { class: "cg-bar" }, add, bulk, group, zip, zipInput)),
  cg.el.list, cg.el.pending, cg.el.bulk, cg.el.packed);
  cgDraftLoad();
  await cgLoad();
}

async function cgLoad() {
  if (!cg.el) return;
  const res = await api("/api/customgames");
  const info = await res.json().catch(() => ({}));
  if (!res.ok) {
    cg.el.list.replaceChildren(el("p", { class: "error" }, info.error || res.statusText));
    return;
  }
  cg.info = info;
  if (!cg.defaultGroup || !cgGroups().includes(cg.defaultGroup)) cg.defaultGroup = cgGroups()[0] || "";
  cgRenderList();
  cgRenderPending();
  cgRenderPacked();
  cgRenderBulk();
}

// Os grupos que existem e os que as linhas da tabela ja criam.
function cgGroups() {
  const names = ((cg.info && cg.info.groups) || []).map((g) => g.name);
  for (const row of cg.rows) if (row.group && !names.includes(row.group)) names.push(row.group);
  if (cg.defaultGroup && !names.includes(cg.defaultGroup)) names.push(cg.defaultGroup);
  return names;
}

async function cgNewGroup() {
  const name = await ask({ title: t("cg_new_group"), text: t("cg_group_ask"), input: "" });
  if (!name) return null;
  if (!cgValidName(name)) { toast(t("cg_f_group") + ": / | .", "bad"); return null; }
  const res = await api("/api/customgames/group", { method: "POST", body: JSON.stringify({ name }) });
  if (!res.ok) { toast((await res.json().catch(() => ({}))).error || res.statusText, "bad"); return null; }
  return name;
}

const cgValidName = (s) => !!s && !!s.trim() && !/[/|\n]/.test(s) && !s.startsWith(".");
const cgModeLabel = (mode) => ((cg.info.modes || []).find((m) => m.value === mode) || { label: mode || "?" }).label;

function cgKindLabel(game) {
  return t("cg_" + (CG_PLATFORMS.includes(game.platform) ? game.platform : "script")).replace(/ \(.*/, "") + " " + cgModeLabel(game.mode);
}

// ── Os jogos ──

function cgRenderList() {
  const games = cg.info.games || [];
  const groups = cg.info.groups || [];
  if (!groups.length) {
    cg.el.list.replaceChildren(el("p", { class: "dim cg-empty" }, t("cg_empty")));
    return;
  }
  cg.el.list.replaceChildren(...groups.map((g) => {
    const mine = games.filter((x) => x.group === g.name);
    return el("section", { class: "cg-group" },
      el("h4", {}, icon("px-games"), g.name, el("span", { class: "dim" }, mine.length === 1 ? t("cg_game_1") : t("cg_games_n").replace("%n", mine.length))),
      el("div", { class: "cg-tiles" }, ...mine.map(cgTile)));
  }));
}

function cgTile(game) {
  const system = "custom/" + game.group;
  const img = el("img", { alt: "", loading: "lazy" });
  img.addEventListener("error", () => { img.replaceWith(el("div", { class: "cg-noimg" }, game.name.slice(0, 2).toUpperCase())); });
  img.src = mediaUrl(system, game.name, "snap");
  fadeIn(img);
  const actions = [["g-play", "cg_play", () => cgPlay(game)]];
  if (game.platform !== "script") actions.push(["px-edit", "cg_edit", () => cgEdit(game)]);
  if (game.platform === "windows" || game.platform === "native") actions.push(["px-install", "cg_package", () => cgPack(game)]);
  actions.push(["g-trash", "cg_delete", () => cgDelete(game)]);
  return el("div", { class: "cg-tile", tabindex: "0" }, el("div", { class: "cg-snap" }, img),
    el("b", { title: game.name }, game.name), el("span", { class: "tag" }, cgKindLabel(game)),
    el("div", { class: "cg-actions" }, ...actions.map(([glyph, label, fn]) => {
      const b = el("button", { type: "button", class: "icon-btn small", title: t(label), "aria-label": t(label) + ": " + game.name },
        icon(glyph));
      b.addEventListener("click", fn);
      return b;
    })));
}

async function cgPlay(game) {
  if (!(await ask({ title: game.name, text: t("confirm_launch").replace("%s", game.name), yes: t("cg_play") }))) return;
  const res = await api("/api/launch", { method: "POST", body: JSON.stringify({ system: "custom/" + game.group, game: game.name }) });
  const data = await res.json().catch(() => ({}));
  toast(res.ok ? t("launching").replace("%s", game.name) : data.error || res.statusText, res.ok ? "ok" : "bad");
}

async function cgDelete(game) {
  if (!(await ask({ title: game.name, text: t("cg_delete_ask").replace("%s", game.name).replace("%s", game.group),
    yes: t("cg_delete"), danger: true }))) return;
  let folder = false;
  if (game.platform === "windows" || game.platform === "native") {
    folder = await ask({ title: game.name, text: t("cg_with_folder") + "?", yes: t("cg_with_folder"), no: t("cg_keep_folder"),
      danger: true });
  }
  const res = await api("/api/customgames/delete", { method: "POST", body: JSON.stringify({ group: game.group, name: game.name, folder }) });
  toast(res.ok ? t("cg_deleted").replace("%s", game.name) : (await res.json().catch(() => ({}))).error || res.statusText,
    res.ok ? "ok" : "bad");
  cgLoad().catch(() => {});
}

async function cgPack(game) {
  const task = await cgTask("/api/customgames/pack", { group: game.group, name: game.name });
  if (task && task.rc === 0) toast(t("cg_packaged").replace("%s", game.group), "ok");
}

// cgTask: uma tarefa de jogos custom (instalar, empacotar...), esperada.
async function cgTask(path, body, onTick) {
  const res = await api(path, { method: "POST", body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { toast(res.status === 409 ? t("cg_busy") : data.error || res.statusText, "bad"); return null; }
  taskNext = 0;
  const task = await waitTask(data.id, onTick);
  if (task && task.rc !== 0) toast(task.error || task.last || t("task_fail"), "bad");
  cgLoad().catch(() => {});
  return task;
}

// ── Editar um jogo ──

async function cgEdit(game) {
  const row = cgRowFromGame(game);
  const command = game.platform === "command";
  const dlg = cgDialog();
  const ctl = cgControls(row, { dialog: true, editing: game });
  const fields = command ? ["name", "group", "run", "mode", "category", "players", "buttons", "controls", "art"]
    : ["mode", "category", "players", "buttons", "controls", "art"];
  const text = el("textarea", { rows: "3", placeholder: t("cg_ph_text"), "aria-label": t("cg_f_text") });
  const save = el("button", { type: "submit", class: "btn" }, icon("px-save"), t("cg_save"));
  const cancel = el("button", { type: "button", class: "btn ghost" }, t("cg_cancel"));
  cancel.addEventListener("click", () => dlg.close());
  const form = el("form", { class: "cg-form" }, el("h3", {}, t("cg_edit_title").replace("%s", game.name)),
    command ? "" : el("p", { class: "dim" }, t("cg_readonly")),
    ...fields.map((f) => cgField(f, ctl[f])), cgField("text", text),
    el("footer", {}, cancel, save));
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    save.disabled = true;
    try {
      const body = { group: game.group, name: game.name, mode: cgRowMode(row), category: row.category, players: row.players,
        buttons: row.buttons, controls: row.controls.join(",") };
      if (command) Object.assign(body, { new_group: row.group, new_name: row.name.trim(), command: row.command });
      const res = await api("/api/customgames/edit", { method: "POST", body: JSON.stringify(body) });
      if (!res.ok) { toast((await res.json().catch(() => ({}))).error || res.statusText, "bad"); return; }
      const media = {};
      if (row.snap && row.snap.id) media.snap = row.snap.id;
      if (row.video && row.video.id) media.video = row.video.id;
      if (text.value.trim()) media.text_string = text.value.trim().replace(/\n/g, "\\n");
      if (Object.keys(media).length) {
        const r = await api("/api/customgames/media", { method: "POST", body: JSON.stringify(Object.assign({
          group: command ? row.group : game.group, name: command ? row.name.trim() : game.name }, media)) });
        if (!r.ok) toast((await r.json().catch(() => ({}))).error || r.statusText, "bad");
      }
      toast(t("cg_saved").replace("%s", command ? row.name : game.name), "ok");
      dlg.close();
      cgLoad().catch(() => {});
    } finally {
      save.disabled = false;
    }
  });
  dlg.replaceChildren(form);
  dlg.showModal();
}

function cgRowFromGame(game) {
  const mode = game.mode || "640x240@60";
  const known = (cg.info.modes || []).find((m) => m.value === mode);
  return cgNewRow({ group: game.group, name: game.name, platform: game.platform, command: game.command, exe: game.exe,
    folder: game.folder, mode: known ? known.label : "other", modeOther: known ? "" : mode, category: game.category,
    players: game.players, buttons: game.buttons, controls: (game.controls || "").split(",").filter(Boolean) });
}

let cgDialogEl = null;
function cgDialog() {
  if (!cgDialogEl) {
    cgDialogEl = el("dialog", { class: "ask cg-dialog" });
    document.body.append(cgDialogEl);
  }
  return cgDialogEl;
}

function cgField(name, control) {
  return el("label", { class: "cg-field cg-f-" + name }, el("span", {}, t("cg_f_" + name)), control);
}

// ── Adicionar um jogo: a tabela com uma linha, num dialogo ──

function cgAddOne() {
  const row = cgNewRow({ group: cg.defaultGroup });
  const dlg = cgDialog();
  const status = el("div", { class: "cg-status", role: "status" });
  const body = el("div", { class: "cg-one" });
  const draw = () => {
    const ctl = cgControls(row, { dialog: true, redraw: draw });
    body.replaceChildren(...["group", "name", "platform", "folder", "run", "mode", "category", "players", "buttons", "controls", "art"]
      .filter((f) => !(f === "folder" && row.platform === "command")).map((f) => {
        const field = cgField(f, ctl[f]);
        const err = cgFieldError(row, f);
        if (err) {
          field.classList.add("bad");
          field.append(el("small", { class: "cg-err" }, err));
        }
        return field;
      }),
    cgPortProtonNote([row], "cg-pp-one"));
  };
  draw();
  const add = el("button", { type: "submit", class: "btn" }, icon("px-add"), t("cg_add_one"));
  const cancel = el("button", { type: "button", class: "btn ghost" }, t("cg_cancel"));
  cancel.addEventListener("click", () => dlg.close());
  const form = el("form", { class: "cg-form" }, el("h3", {}, t("cg_add")), el("p", { class: "dim" }, t("cg_copy_note")), body, status,
    el("footer", {}, cancel, add));
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    add.disabled = true;
    try {
      if (await cgSave([row], status, $("cg-pp-one"))) dlg.close();
      else {
        draw();
        if (row.error) status.append(el("div", { class: "error" }, row.error));
      }
    } finally {
      add.disabled = false;
    }
  });
  dlg.replaceChildren(form);
  dlg.showModal();
}

// ── Os pacotes novos ──

function cgRenderPending() {
  const rows = (cg.info.pending || []).filter((p) => p.state !== "bad" || p.zip);
  cg.el.pending.hidden = !rows.length;
  if (!rows.length) return;
  const good = rows.filter((p) => p.state !== "bad");
  const all = el("button", { type: "button", class: "btn ghost small" }, icon("px-install"), t("cg_install_all"));
  all.hidden = good.length < 2;
  all.addEventListener("click", async () => {
    for (const p of good) if (!(await cgInstallPending(p, p.group || cg.defaultGroup, true))) break;
  });
  cg.el.pending.replaceChildren(el("h4", {}, icon("px-install"), t("cg_pending"), all), el("div", { class: "nics" }, ...rows.map((p) => {
    if (p.state === "bad") {
      return el("div", { class: "nic-row" }, icon("px-cancel"), el("b", {}, p.zip.split("/").pop()),
        el("span", { class: "tag off" }, t("cg_bad_zip")), el("span", { class: "dim" }, p.why));
    }
    const group = p.group ? el("span", { class: "tag" }, p.group) : cgGroupSelect(cg.defaultGroup, () => {});
    const go = el("button", { type: "button", class: "btn small" }, t("cg_install"));
    go.addEventListener("click", () => cgInstallPending(p, p.group || group.value));
    return el("div", { class: "nic-row" }, icon("px-games"), el("b", {}, p.name), el("span", { class: "dim" }, t("cg_" + p.platform)),
      p.state === "update" ? el("span", { class: "tag off" }, t("cg_update")) : "", group, go);
  })));
}

async function cgInstallPending(p, group, quiet) {
  if (!group) { toast(t("cg_zip_group"), "bad"); return false; }
  let pp = false;
  if (p.platform === "windows" && !cg.info.portproton) {
    pp = await ask({ title: "PortProton", text: t("cg_pp"), yes: t("cg_pp_install"), no: t("cg_cancel") });
  } else if (!quiet && !(await ask({ title: p.name, text: t("cg_install") + ": " + p.name + " → " + group, yes: t("cg_install") }))) {
    return false;
  }
  const task = await cgTask("/api/customgames/install", { zip: p.zip, group, replace: p.state === "update", portproton: pp });
  return !!task && task.rc === 0;
}

// Instalar um pacote (.zip): sobe para ~/roms/custom/GRUPO e instala.
async function cgInstallZip(file) {
  let group = cg.defaultGroup;
  if (!group) group = await cgNewGroup();
  if (!group) return;
  toast(t("cg_uploading").replace("%s", file.name));
  const status = await cgPostFile("/api/upload?root=roms&path=" + encodeURIComponent("custom/" + group) + "&name=" +
    encodeURIComponent(file.name) + "&overwrite=1", file);
  if (status !== 200) return toast(file.name + ": " + (status || "network error"), "bad");
  await cgLoad();
  const pending = (cg.info.pending || []).find((p) => p.zip.endsWith("/custom/" + group + "/" + file.name));
  if (!pending) return toast(file.name + ": " + t("cg_bad_zip"), "bad");
  if (pending.state === "bad") return toast(file.name + ": " + pending.why, "bad");
  toast(t("cg_zip_sent").replace("%s", file.name));
  await cgInstallPending(pending, group, true);
}

// cgPostFile: um arquivo como corpo do pedido (o fetch nao da o progresso:
// XMLHttpRequest). Resolve com o status e, em json, a resposta.
function cgPostFile(url, file, onProgress, json) {
  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.setRequestHeader("X-FliperOS", "1");
    if (onProgress) xhr.upload.onprogress = (ev) => { if (ev.lengthComputable) onProgress(ev.loaded / ev.total); };
    xhr.onload = () => {
      if (xhr.status === 401) showLogin();
      if (!json) return resolve(xhr.status);
      try { resolve({ status: xhr.status, data: JSON.parse(xhr.responseText) }); } catch (e) { resolve({ status: xhr.status, data: {} }); }
    };
    xhr.onerror = () => resolve(json ? { status: 0, data: {} } : 0);
    xhr.send(file);
  });
}

// ── As pastas compactadas ──

function cgRenderPacked() {
  const pack = el("button", { type: "button", class: "btn ghost small" }, icon("px-add"), t("cg_pack"));
  pack.addEventListener("click", async () => {
    const folder = await pickFolder({ title: t("cg_pack"), start: cg.info.games_dir });
    if (!folder || !(await ask({ title: t("cg_pack"), text: t("cg_pack_ask").replace("%s", folder), yes: t("cg_pack") }))) return;
    cgTask("/api/customgames/squash", { folder, action: "pack" });
  });
  cg.el.packed.replaceChildren(el("h4", {}, icon("px-disk"), t("cg_packed"), pack), el("div", { class: "nics" },
    ...(cg.info.squash || []).map((s) => {
      const unpack = el("button", { type: "button", class: "btn ghost small" }, t("cg_unpack"));
      unpack.addEventListener("click", async () => {
        if (await ask({ title: t("cg_unpack"), text: t("cg_unpack_ask").replace("%s", s.folder), yes: t("cg_unpack") })) {
          cgTask("/api/customgames/squash", { folder: s.folder, action: "unpack" });
        }
      });
      return el("div", { class: "nic-row" }, icon("px-dest"), el("code", {}, s.folder), el("span", { class: "dim" }, s.size),
        s.mounted ? "" : el("span", { class: "tag off" }, t("cg_not_mounted")), unpack);
    })));
}

// ── A tabela ──

function cgNewRow(values) {
  return Object.assign({ id: ++cg.seq, group: "", name: "", platform: "windows", folder: "", exe: "", command: "", mode: "240p",
    modeOther: "", category: "", players: "", buttons: "", controls: [], snap: null, video: null, wine: "", exes: [], programs: [],
    errors: {}, state: "", error: "" }, values || {});
}

function cgDraftLoad() {
  try {
    const saved = JSON.parse(localStorage.getItem(CG_DRAFT) || "null");
    if (saved && Array.isArray(saved.rows)) {
      cg.rows = saved.rows.map((r) => cgNewRow(Object.assign({}, r, { id: undefined, state: "", error: "", errors: {} })));
      cg.rows.forEach((r) => { r.id = ++cg.seq; if (r.snap) r.snap.url = ""; });
      cg.defaultGroup = saved.group || "";
    }
  } catch (e) { /* sem armazenamento */ }
}

function cgDraftSave() {
  try {
    const rows = cg.rows.map((r) => {
      const out = Object.assign({}, r);
      delete out.errors; delete out.state; delete out.error;
      if (out.snap) out.snap = { id: out.snap.id, name: out.snap.name };
      return out;
    });
    if (rows.length) localStorage.setItem(CG_DRAFT, JSON.stringify({ rows, group: cg.defaultGroup }));
    else localStorage.removeItem(CG_DRAFT);
  } catch (e) { /* sem armazenamento */ }
}

function cgRenderBulk() {
  const box = cg.el.bulk;
  if (!box.dataset.built) {
    box.dataset.built = "1";
    const addRow = el("button", { type: "button", class: "btn ghost small" }, icon("g-plus"), t("cg_rows"));
    addRow.addEventListener("click", () => { cg.rows.push(cgNewRow({ group: cg.defaultGroup })); cgTableDraw(true); });
    const importBtn = el("button", { type: "button", class: "btn ghost small" }, t("cg_import"));
    importBtn.addEventListener("click", cgImport);
    const pasteBtn = el("button", { type: "button", class: "btn ghost small" }, t("cg_paste"));
    pasteBtn.addEventListener("click", cgPasteDialog);
    const clear = el("button", { type: "button", class: "btn-text quiet" }, t("cg_clear"));
    clear.addEventListener("click", async () => {
      if (cg.rows.length && (await ask({ title: t("cg_clear"), text: t("cg_clear_ask"), yes: t("cg_clear"), danger: true }))) {
        cg.rows = [];
        cgTableDraw();
      }
    });
    const check = el("button", { type: "button", class: "btn ghost small" }, t("cg_check"));
    check.addEventListener("click", () => cgCheck(cg.rows, $("cg-status")).catch(() => {}));
    const save = el("button", { type: "button", class: "btn small" }, t("cg_save_all"));
    save.id = "cg-save";
    save.addEventListener("click", () => cgSaveTable().catch(() => {}));
    box.append(el("h4", {}, icon("px-romlist"), t("cg_bulk")), el("p", { class: "dim" }, t("cg_copy_note")),
      el("div", { class: "cg-toolbar" }, el("label", { class: "cg-default" }, el("span", {}, t("cg_default_group")),
        el("span", { id: "cg-default-group" })), addRow, importBtn, pasteBtn, clear),
      el("div", { class: "cg-table-wrap" }, el("table", { class: "cg-table", id: "cg-table" })),
      el("div", { id: "cg-pp" }), el("div", { class: "cg-status", id: "cg-status", role: "status" }),
      el("div", { class: "cg-foot" }, el("span", { class: "dim" }, t("cg_draft")), el("span", { class: "grow" }), check, save));
    // Colar no meio da tabela: as linhas da planilha a partir dessa.
    box.querySelector("#cg-table").addEventListener("paste", (ev) => {
      const text = (ev.clipboardData || window.clipboardData).getData("text");
      if (!/[\t\n]/.test(text.trim())) return;
      ev.preventDefault();
      cgPaste(text);
    });
  }
  const defaultSelect = cgGroupSelect(cg.defaultGroup, (value) => { cg.defaultGroup = value; cgDraftSave(); });
  $("cg-default-group").replaceChildren(defaultSelect);
  cgTableDraw();
}

// cgGroupSelect: o dropdown dos grupos, com "+ Novo grupo…" no fim.
function cgGroupSelect(value, onChange) {
  const select = el("select", { "aria-label": t("cg_f_group") });
  const fill = (current) => {
    select.replaceChildren(el("option", { value: "" }, t("cg_none")), ...cgGroups().map((g) => el("option", { value: g }, g)),
      el("option", { value: "+new" }, t("cg_new_group_opt")));
    select.value = current || "";
  };
  fill(value);
  select.addEventListener("change", async () => {
    if (select.value !== "+new") return onChange(select.value);
    const name = await ask({ title: t("cg_new_group"), text: t("cg_group_ask"), input: "" });
    if (name && cgValidName(name)) {
      if (!cg.defaultGroup) cg.defaultGroup = name;
      onChange(name);
      fill(name);
    } else fill(value);
  });
  return select;
}

function cgTableDraw(focusLast) {
  const table = $("cg-table");
  if (!table) return;
  const head = el("tr", {}, el("th", { class: "num" }, "#"), ...CG_COLUMNS.map((c) => el("th", { scope: "col" },
    t(c === "run" ? "cg_f_run" : "cg_f_" + c))), el("th", {}));
  const body = cg.rows.length ? cg.rows.map((row, i) => cgTableRow(row, i)) : [el("tr", { class: "cg-none" },
    el("td", { colspan: String(CG_COLUMNS.length + 2), class: "dim" }, t("cg_rows_none")))];
  table.replaceChildren(el("thead", {}, head), el("tbody", {}, ...body));
  $("cg-pp").replaceChildren(cgPortProtonNote(cg.rows));
  $("cg-save").disabled = !cg.rows.length || cg.busy;
  cgDraftSave();
  if (focusLast) {
    const last = table.querySelector("tbody tr:last-child input[type=text]");
    if (last) last.focus();
  }
}

function cgTableRow(row, index) {
  const redraw = () => { cgTableDraw(); };
  const ctl = cgControls(row, { redraw });
  const dup = el("button", { type: "button", class: "icon-btn small", title: t("cg_dup"), "aria-label": t("cg_dup") }, icon("g-copy"));
  dup.addEventListener("click", () => {
    const copy = cgNewRow(Object.assign({}, row, { id: undefined, name: "", folder: row.platform === "command" ? "" : row.folder,
      snap: null, video: null, errors: {}, state: "", error: "", controls: row.controls.slice() }));
    copy.id = ++cg.seq;
    cg.rows.splice(index + 1, 0, copy);
    cgTableDraw();
  });
  const del = el("button", { type: "button", class: "icon-btn small", title: t("cg_remove"), "aria-label": t("cg_remove") }, icon("g-trash"));
  del.addEventListener("click", () => { cg.rows.splice(index, 1); cgTableDraw(); });
  const state = row.state === "ok" ? el("span", { class: "tag on" }, t("cg_row_ok"))
    : row.error ? el("span", { class: "cg-err" }, row.error) : "";
  const tr = el("tr", { class: "cg-row" + (row.state ? " " + row.state : "") + (Object.keys(row.errors).length ? " bad" : "") },
    el("td", { class: "num" }, String(index + 1)),
    ...CG_COLUMNS.map((c) => {
      const td = el("td", { "data-label": t(c === "run" ? "cg_f_run" : "cg_f_" + c), class: "c-" + c });
      if (c === "folder" && row.platform === "command") td.append(el("span", { class: "dim" }, t("cg_any")));
      else td.append(ctl[c]);
      const err = cgFieldError(row, c);
      if (err) {
        td.classList.add("bad");
        td.append(el("small", { class: "cg-err" }, err));
      }
      return td;
    }),
    el("td", { class: "c-act" }, dup, del, state));
  return tr;
}

// O erro do Setup cai na coluna dela (exe e command sao a mesma coluna).
function cgFieldError(row, column) {
  const map = { run: ["exe", "command"], art: ["snap", "video", "text"], group: ["group"], name: ["name"], platform: ["platform"],
    folder: ["folder"], mode: ["mode"], category: ["category"], players: ["players"], buttons: ["buttons"], controls: ["controls"] };
  return (map[column] || []).map((f) => row.errors[f]).filter(Boolean).join(" ");
}

// cgControls: os campos de uma linha (na tabela ou num dialogo). Mudar o tipo
// ou a pasta redesenha (o executavel depende deles).
function cgControls(row, { redraw, editing } = {}) {
  const changed = (structural) => {
    row.state = "";
    row.error = "";
    row.errors = {};
    cgDraftSave();
    if (structural && redraw) redraw();
  };
  const text = (key, placeholder, cls) => {
    const input = el("input", { type: "text", value: row[key] || "", placeholder: placeholder || "",
      "aria-label": t("cg_f_" + (key === "modeOther" ? "mode" : key)),
      spellcheck: "false", class: cls || "" });
    input.addEventListener("input", () => { row[key] = input.value; changed(false); });
    return input;
  };
  const select = (key, options, structural) => {
    const s = el("select", { "aria-label": t("cg_f_" + key) }, ...options.map(([v, label]) => el("option", { value: v }, label)));
    s.value = row[key] || "";
    s.addEventListener("change", () => { row[key] = s.value; changed(structural); });
    return s;
  };
  const out = {};
  out.group = cgGroupSelect(row.group, (value) => { row.group = value; changed(false); });
  out.name = text("name", t("cg_ph_name"));
  out.platform = editing ? el("span", { class: "tag" }, t("cg_" + row.platform))
    : select("platform", CG_PLATFORMS.map((p) => [p, t("cg_" + p)]), true);
  // A pasta: digitada ou escolhida no dialogo; ao mudar, o scan acha os
  // executaveis (e o nome, se ainda nao tem).
  const folder = text("folder", t("cg_ph_folder"), "code-in");
  folder.addEventListener("change", () => cgScanRow(row, redraw));
  const pick = el("button", { type: "button", class: "icon-btn small", title: t("cg_pick"), "aria-label": t("cg_pick") }, icon("px-dest"));
  pick.addEventListener("click", async () => {
    const path = await pickFolder({ title: t("cg_f_folder") + (row.name ? ": " + row.name : ""),
      start: row.folder || (cg.info && cg.info.games_dir) || "" });
    if (!path) return;
    row.folder = path;
    folder.value = path;
    await cgScanRow(row, redraw);
  });
  out.folder = el("div", { class: "cg-pickfield" }, folder, pick);
  // O executavel (Windows): os .exe achados; o comando (Linux e Comando).
  if (row.platform === "windows") {
    const exes = row.exes.length ? row.exes : row.exe ? [row.exe] : [];
    if (exes.length) {
      out.run = select("exe", [["", t("cg_none")], ...exes.map((x) => [x, x])], false);
      if (!row.exe) { row.exe = exes[0]; out.run.value = row.exe; }
    } else {
      out.run = text("exe", row.folder ? t("cg_no_exe") : "game.exe", "code-in");
    }
  } else {
    out.run = text("command", row.platform === "native" ? t("cg_ph_native") : t("cg_ph_command"), "code-in");
    if (row.platform === "native" && row.programs.length) {
      const list = el("datalist", { id: "cg-prog-" + row.id }, ...row.programs.map((p) => el("option", { value: "./" + p.replace(/ /g, "\\ ") })));
      out.run.setAttribute("list", list.id);
      out.run = el("div", {}, out.run, list);
    }
  }
  // O modo: 240p, 480i ou outro (o campo LxA@Hz aparece).
  const modes = ((cg.info && cg.info.modes) || [{ label: "240p" }, { label: "480i" }]).map((m) => [m.label, m.label]);
  const mode = select("mode", [...modes, ["other", t("cg_mode_other")]], true);
  out.mode = row.mode === "other" ? el("div", { class: "cg-mode" }, mode, text("modeOther", t("cg_ph_mode"), "code-in")) : mode;
  // A categoria do catver.ini: o genero e as categorias dele.
  const category = el("select", { "aria-label": t("cg_f_category") }, el("option", { value: "" }, t("cg_none")),
    ...((cg.info && cg.info.genres) || []).map((g) => el("optgroup", { label: g.name }, el("option", { value: g.name }, g.name),
      ...g.subs.map((s) => el("option", { value: s }, s)))));
  if (row.category && !category.querySelector('option[value="' + CSS.escape(row.category) + '"]')) {
    category.append(el("option", { value: row.category }, row.category));
  }
  category.value = row.category || "";
  category.addEventListener("change", () => { row.category = category.value; changed(false); });
  out.category = category;
  out.players = select("players", [["", t("cg_any")], ...[1, 2, 3, 4, 5, 6, 7, 8].map((n) => [String(n), String(n)])], false);
  out.buttons = select("buttons", [["", t("cg_any")], ...[0, 1, 2, 3, 4, 5, 6, 7, 8].map((n) => [String(n), String(n)])], false);
  out.controls = cgControlsButton(row, changed);
  out.art = cgArt(row, changed);
  if (row.platform === "windows" && cg.info && cg.info.wine && cg.info.wine.length && !editing) {
    out.art = el("div", { class: "cg-artwine" }, out.art, select("wine", [["", t("cg_wine_default")], ...cg.info.wine.map((w) => [w.value, w.label])], false));
  }
  return out;
}

// Os controles: um botao com os escolhidos; abre os 13 em botoes.
function cgControlsButton(row, changed) {
  const labels = Object.fromEntries(((cg.info && cg.info.controls) || []).map((c) => [c.value, c.label]));
  const button = el("button", { type: "button", class: "cg-ctl" });
  const show = () => { button.textContent = row.controls.length ? row.controls.join(", ") : t("cg_controls_none"); };
  show();
  button.addEventListener("click", () => {
    const pop = el("dialog", { class: "ask cg-pop" });
    const chips = el("div", { class: "chips" }, ...Object.entries(labels).map(([value, label]) => {
      const b = el("button", { type: "button", "aria-pressed": String(row.controls.includes(value)) }, label);
      b.addEventListener("click", () => {
        row.controls = row.controls.includes(value) ? row.controls.filter((c) => c !== value) : [...row.controls, value];
        b.setAttribute("aria-pressed", String(row.controls.includes(value)));
        show();
        changed(false);
      });
      return b;
    }));
    const done = el("button", { type: "button", class: "btn" }, icon("px-ok"), "OK");
    done.addEventListener("click", () => pop.close());
    pop.append(el("h3", {}, t("cg_controls_title").replace("%s", row.name || "…")), chips, el("footer", {}, done));
    pop.addEventListener("close", () => pop.remove());
    document.body.append(pop);
    pop.showModal();
  });
  return button;
}

// A arte da linha: a imagem e o video sobem na hora para a espera do
// servidor; a linha guarda o id.
function cgArt(row, changed) {
  const box = el("div", { class: "cg-art" });
  const slot = (key, accept, kind, glyph) => {
    const input = el("input", { type: "file", accept, hidden: "" });
    const current = row[key];
    const button = el("button", { type: "button", class: "cg-artbtn" + (current ? " on" : ""), title: t("cg_f_" + (key === "snap" ? "snap" : "video")) });
    if (current && current.url && key === "snap") button.append(el("img", { src: current.url, alt: "" }));
    else button.append(icon(glyph), el("span", {}, current ? current.name : t("cg_f_" + (key === "snap" ? "snap" : "video"))));
    button.addEventListener("click", () => input.click());
    input.addEventListener("change", async () => {
      const file = input.files[0];
      input.value = "";
      if (!file) return;
      button.disabled = true;
      button.replaceChildren(el("span", {}, "0%"));
      const out = await cgPostFile("/api/customgames/stage?kind=" + kind + "&name=" + encodeURIComponent(file.name), file,
        (frac) => { button.firstChild.textContent = Math.round(frac * 100) + "%"; }, true);
      button.disabled = false;
      if (out.status !== 200) {
        toast(t("cg_art_too_big").replace("%s", file.name) + (out.data.error ? " " + out.data.error : ""), "bad");
        row[key] = null;
      } else {
        row[key] = { id: out.data.id, name: file.name, url: key === "snap" ? URL.createObjectURL(file) : "" };
      }
      changed(false);
      const fresh = cgArt(row, changed);
      box.replaceWith(fresh);
    });
    const parts = [button, input];
    if (current) {
      const drop = el("button", { type: "button", class: "icon-btn small", "aria-label": t("cg_remove") }, icon("g-close"));
      drop.addEventListener("click", () => { row[key] = null; changed(false); box.replaceWith(cgArt(row, changed)); });
      parts.push(drop);
    }
    return el("span", { class: "cg-slot" }, ...parts);
  };
  box.append(slot("snap", ".png,.jpg,.jpeg,.webp,.gif", "snap", "g-camera"), slot("video", ".mp4,.mkv,.webm,.avi,.mov,.flv", "video", "g-play"));
  return box;
}

// cgScanRow: os executaveis da pasta (e o tipo e o nome, quando faltam).
async function cgScanRow(row, redraw) {
  if (!row.folder || !row.folder.startsWith("/")) return;
  const res = await api("/api/customgames/scan?one=1&path=" + encodeURIComponent(row.folder));
  if (!res.ok) return;
  const found = await res.json();
  row.exes = found.exes || [];
  row.programs = found.programs || [];
  if (!row.name && found.name) row.name = found.name;
  if (found.platform && row.platform !== "command" && !row.exe && !row.command) row.platform = found.platform;
  if (row.platform === "windows" && !row.exes.includes(row.exe)) row.exe = row.exes[0] || "";
  if (row.platform === "native" && !row.command && found.command) row.command = found.command;
  row.errors = {};
  cgDraftSave();
  if (redraw) redraw();
}

function cgPortProtonNote(rows, id) {
  if (!cg.info || cg.info.portproton || !rows.some((r) => r.platform === "windows")) return el("span");
  const box = el("label", { class: "check cg-ppnote" }, el("input", { type: "checkbox", id: id || "cg-pp-on" }), el("span", {}, t("cg_pp")));
  box.querySelector("input").checked = true;
  return box;
}

// Importar de uma pasta: uma linha por subpasta (ou a propria pasta).
async function cgImport() {
  const folder = await pickFolder({ title: t("cg_import_title"), start: (cg.info && cg.info.games_dir) || "" });
  if (!folder) return;
  const res = await api("/api/customgames/scan?path=" + encodeURIComponent(folder));
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return toast(data.error || res.statusText, "bad");
  let games = (data.games || []).filter((g) => g.platform);
  if (!games.length) {
    if (!(await ask({ title: t("cg_import_title"), text: t("cg_import_none").replace("%s", folder), yes: t("cg_import_one") }))) return;
    const one = await (await api("/api/customgames/scan?one=1&path=" + encodeURIComponent(folder))).json();
    games = [one];
  }
  // A linha vazia do comeco sai.
  cg.rows = cg.rows.filter((r) => r.name || r.folder || r.command);
  for (const g of games) {
    cg.rows.push(cgNewRow({ group: cg.defaultGroup, name: g.name, platform: g.platform || "windows", folder: g.path, exe: g.exe,
      command: g.command, exes: g.exes || [], programs: g.programs || [] }));
  }
  cgTableDraw();
  toast(t("cg_import_found").replace("%n", games.length).replace("%s", folder), "ok");
}

// Colar de uma planilha: as linhas (tabs) viram linhas da tabela; um
// cabecalho com os nomes das colunas escolhe a ordem.
function cgPasteDialog() {
  const dlg = cgDialog();
  const area = el("textarea", { rows: "10", class: "code-in", spellcheck: "false", "aria-label": t("cg_paste_title"),
    placeholder: "Metal Slug X\tPC games\tWindows\t/media/fliperos/USB/Metal Slug X\tMSX.exe\t240p\tPlatform / Shooter Scrolling\t2\t3\tjoy8" });
  const go = el("button", { type: "submit", class: "btn" }, icon("px-add"), t("cg_paste_go"));
  const cancel = el("button", { type: "button", class: "btn ghost" }, t("cg_cancel"));
  cancel.addEventListener("click", () => dlg.close());
  const form = el("form", { class: "cg-form" }, el("h3", {}, t("cg_paste_title")), el("p", { class: "dim" }, t("cg_paste_text")), area,
    el("footer", {}, cancel, go));
  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    if (cgPaste(area.value)) dlg.close();
  });
  dlg.replaceChildren(form);
  dlg.showModal();
  area.focus();
}

function cgPaste(text) {
  const lines = text.replace(/\r/g, "").split("\n").filter((l) => l.trim());
  if (!lines.length) return false;
  let order = CG_PASTE_ORDER;
  const cells = (line) => line.split("\t").map((c) => c.trim().replace(/^"(.*)"$/, "$1"));
  // O cabecalho: os nomes das colunas (em portugues ou em ingles).
  const first = cells(lines[0]).map((c) => c.toLowerCase());
  const named = first.map((c) => Object.keys(CG_PASTE_NAMES).find((k) => CG_PASTE_NAMES[k].includes(c)) || null);
  if (named.filter(Boolean).length >= 2) {
    order = named;
    lines.shift();
  }
  const platformOf = (s) => {
    const v = (s || "").toLowerCase();
    if (/^w|exe/.test(v)) return "windows";
    if (/^l|nat/.test(v)) return "native";
    if (/^c|cmd/.test(v)) return "command";
    return "";
  };
  const controls = Object.keys(Object.fromEntries(((cg.info && cg.info.controls) || []).map((c) => [c.value, 1])));
  const modes = ((cg.info && cg.info.modes) || []).map((m) => m.label);
  cg.rows = cg.rows.filter((r) => r.name || r.folder || r.command);
  let added = 0;
  for (const line of lines) {
    const v = {};
    cells(line).forEach((c, i) => { if (order[i]) v[order[i]] = c; });
    if (!v.name && !v.folder && !v.run) continue;
    let platform = platformOf(v.platform);
    if (!platform) platform = /\.(exe|bat)$/i.test(v.run || "") ? "windows" : v.folder ? "native" : "command";
    const row = cgNewRow({ group: v.group || cg.defaultGroup, name: v.name || "", platform, folder: platform === "command" ? "" : v.folder || "",
      category: v.category || "", players: /^[1-8]$/.test(v.players || "") ? v.players : "",
      buttons: /^[0-8]$/.test(v.buttons || "") ? v.buttons : "",
      controls: (v.controls || "").split(/[,; ]+/).map((c) => c.toLowerCase()).filter((c) => controls.includes(c)) });
    if (platform === "windows") row.exe = v.run || ""; else row.command = v.run || "";
    const m = (v.mode || "").trim();
    if (modes.includes(m)) row.mode = m;
    else if (m) { row.mode = "other"; row.modeOther = m; }
    cg.rows.push(row);
    added++;
  }
  cgTableDraw();
  toast(t("cg_pasted").replace("%n", added), added ? "ok" : "bad");
  // As pastas coladas: os executaveis delas.
  cg.rows.filter((r) => r.folder && !r.exes.length && !r.programs.length).forEach((r) => cgScanRow(r, cgTableDraw).catch(() => {}));
  return added > 0;
}

// ── Conferir e gravar ──

const cgRowMode = (row) => (row.mode === "other" ? row.modeOther.trim() : row.mode);

function cgPayload(row) {
  return { group: row.group, name: row.name.trim(), platform: row.platform, folder: row.platform === "command" ? "" : row.folder.trim(),
    exe: row.platform === "windows" ? row.exe : "", command: row.platform === "windows" ? "" : row.command, mode: cgRowMode(row),
    category: row.category, controls: row.controls.join(","), buttons: row.buttons, players: row.players,
    snap: row.snap ? row.snap.id : "", video: row.video ? row.video.id : "", wine: row.platform === "windows" ? row.wine : "" };
}

// cgCheck: os erros de cada linha pelo Setup (nada e gravado). true: tudo
// certo e cabe no disco.
async function cgCheck(rows, status) {
  if (!rows.length) { status.textContent = t("cg_rows_none"); return false; }
  const res = await api("/api/customgames/check", { method: "POST", body: JSON.stringify({ rows: rows.map(cgPayload) }) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { status.textContent = data.error || res.statusText; return false; }
  rows.forEach((r) => { r.errors = {}; r.state = ""; r.error = ""; });
  for (const e of data.errors || []) if (rows[e.row]) rows[e.row].errors[e.field] = e.error;
  const space = data.bytes ? t(data.bytes + (64 << 20) > data.free ? "cg_space_low" : "cg_space").replace("%s", bytes(data.bytes))
    .replace("%s", bytes(data.free)) : "";
  const ok = !(data.errors || []).length && !(data.bytes && data.bytes + (64 << 20) > data.free);
  status.replaceChildren(el("span", { class: ok ? "ok" : "error" }, ok ? t("cg_check_ok") : (data.errors || []).length ? t("cg_errors") : ""),
    space ? el("span", { class: "dim" }, " " + space) : "");
  if (rows === cg.rows) cgTableDraw();
  return ok;
}

// cgSave: confere e grava as linhas (uma tarefa); cada linha fica com o
// resultado dela. true: todas entraram.
async function cgSave(rows, status, ppBox) {
  if (cg.busy) return false;
  cg.busy = true;
  try {
    if (!(await cgCheck(rows, status))) return false;
    const pp = !!(ppBox && ppBox.checked);
    const res = await api("/api/customgames/bulk", { method: "POST", body: JSON.stringify({ rows: rows.map(cgPayload), portproton: pp }) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) { status.textContent = res.status === 409 ? t("cg_busy") : data.error || res.statusText; return false; }
    taskNext = 0;
    const bar = meter(0);
    const step = el("span", {}, t("cg_saving").replace("%n", rows.length));
    status.replaceChildren(step, bar);
    const task = await waitTask(data.id, (tk) => {
      bar.firstChild.style.width = (tk.pct || 0) + "%";
      if (tk.step) step.textContent = tk.step;
    });
    if (!task) return false;
    for (const r of task.rows || []) {
      if (!rows[r.row]) continue;
      rows[r.row].state = r.ok ? "ok" : "fail";
      rows[r.row].error = r.ok ? "" : r.error;
    }
    const ok = rows.filter((r) => r.state === "ok").length, bad = rows.length - ok;
    status.replaceChildren(el("span", { class: bad ? "error" : "ok" }, (ok ? t("cg_done").replace("%n", ok) + " " : "") +
      (bad ? t("cg_failed").replace("%n", bad) : "")));
    toast(t("cg_done").replace("%n", ok), bad ? "bad" : "ok");
    await cgLoad();
    return bad === 0;
  } finally {
    cg.busy = false;
    if ($("cg-save")) $("cg-save").disabled = !cg.rows.length;
  }
}

async function cgSaveTable() {
  const rows = cg.rows;
  await cgSave(rows, $("cg-status"), $("cg-pp-on"));
  // As que entraram saem da tabela (um instante com o ✓); as outras ficam.
  if (rows.some((r) => r.state === "ok")) {
    cgTableDraw();
    await sleep(1500);
    cg.rows = cg.rows.filter((r) => r.state !== "ok");
    cgTableDraw();
  }
}
