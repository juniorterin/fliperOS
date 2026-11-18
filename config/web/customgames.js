// A area Jogos custom e Sistema > Setup > Jogos > Jogos custom (o Setup >
// Games > Custom games do gabinete), em tres abas: Jogos (os grupos e os jogos, a tabela para
// cadastrar muitos de uma vez e as pastas compactadas), Instalar pacotes (os
// JOGO.fliperos-customgame.zip da pasta deles, ~/roms/custom-packages, o
// grupo escolhido ao instalar) e Criar pacote (o zip vai para essa pasta).
// Tudo pelo fliperos-setup --customgames (config/fliperos-web,
// /api/customgames): um jogo so e a tabela com uma linha.
"use strict";

const cg = { root: null, info: null, rows: [], seq: 0, el: null, busy: false, defaultGroup: "", installGroup: "", tab: "games",
  createRow: null, highlight: "" };
const CG_DRAFT = "fliperos-cg-draft";
const CG_TAB = "fliperos-cg-tab";
const CG_TABS = ["games", "install", "create"];
const CG_CAPTURE_SECONDS = 10;
// O nome de todo pacote (config/fliperos-customgame SUFFIX).
const CG_SUFFIX = ".fliperos-customgame.zip";
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

// A pagina e uma so (a tabela e o rascunho ficam nela) e mora na caixa de
// quem a abriu por ultimo: a area Jogos custom (#customgames) ou Sistema >
// Setup > Jogos > Jogos custom. Ja feita, ela so muda de caixa e le de novo.
async function cgMount(box) {
  if (!cg.root) return customGamesPage(box);
  if (cg.root.parentNode !== box) box.append(cg.root);
  return cgLoad();
}

async function customGamesPage(box) {
  if (cg.root) return cgMount(box);
  cg.root = el("div", { class: "cg-root" });
  box.append(cg.root);
  box = cg.root;
  const add = el("button", { type: "button", class: "btn small" }, icon("g-plus"), t("cg_add"));
  add.addEventListener("click", () => cgAddOne());
  const group = el("button", { type: "button", class: "btn ghost small" }, t("cg_new_group"));
  group.addEventListener("click", () => cgNewGroup().then((name) => name && cgLoad()));
  const bulk = el("a", { class: "btn ghost small", href: "#cg-bulk" }, t("cg_bulk"));
  bulk.addEventListener("click", (ev) => { ev.preventDefault(); $("cg-bulk").scrollIntoView({ behavior: "smooth" }); });
  try { if (CG_TABS.includes(localStorage.getItem(CG_TAB))) cg.tab = localStorage.getItem(CG_TAB); } catch (e) { /* sem armazenamento */ }
  cg.el = {
    tabs: el("nav", { class: "subtabs", role: "tablist" }),
    list: el("div", { class: "cg-list" }),
    packed: el("section", { class: "cg-sec" }),
    bulk: el("section", { class: "cg-sec cg-bulk", id: "cg-bulk" }),
    install: el("div", { class: "cg-pane" }),
    create: el("div", { class: "cg-pane" }),
  };
  cg.el.panes = {
    games: el("div", { class: "cg-pane" }, el("div", { class: "cg-bar" }, add, bulk, group), cg.el.list, cg.el.bulk, cg.el.packed),
    install: cg.el.install,
    create: cg.el.create,
  };
  box.append(el("div", { class: "cg-head" }, el("h2", {}, t("cg_title")), el("p", { class: "lead" }, t("cg_intro")),
    el("div", { class: "subtabs-bar cg-tabs" }, cg.el.tabs)),
  ...CG_TABS.map((k) => cg.el.panes[k]));
  cgDraftLoad();
  cgShowTab(cg.tab);
  await cgLoad();
}

// As abas: Jogos, Instalar pacotes (com quantos ha para instalar) e Criar
// pacote. A escolhida fica no navegador.
function cgShowTab(tab) {
  cg.tab = CG_TABS.includes(tab) ? tab : "games";
  try { localStorage.setItem(CG_TAB, cg.tab); } catch (e) { /* sem armazenamento */ }
  const waiting = (cg.packages || []).filter((p) => p.state === "new" || p.state === "update").length;
  cg.el.tabs.replaceChildren(...CG_TABS.map((k) => {
    const label = k === "install" && waiting ? t("cg_tab_install") + " (" + waiting + ")" : t("cg_tab_" + k);
    const a = el("a", { href: "#", role: "tab", class: cg.tab === k ? "on" : "", "aria-selected": String(cg.tab === k) }, label);
    a.addEventListener("click", (ev) => { ev.preventDefault(); cgShowTab(k); });
    return a;
  }));
  for (const k of CG_TABS) cg.el.panes[k].hidden = k !== cg.tab;
}

// A estrutura do pacote, sempre a mesma: JOGO.fliperos-customgame.zip com
// JOGO.cfg, a arte, o .key, o .ppdb e a pasta JOGO/, num exemplo (o Street
// Fighter 4), com o cfg dele e o que cada chave e. A mesma estrutura numa
// pasta (o zip aberto) preenche a arte sozinha ao escolher a pasta.
const CG_EXAMPLE = "Street Fighter 4";
// O cfg do exemplo (as chaves do config/fliperos-customgame check_cfg).
const CG_EXAMPLE_CFG = [["name", CG_EXAMPLE], ["platform", "windows"], ["exe", "StreetFighterIV.exe"], ["mode", "480i"],
  ["category", "Fighter / Versus"], ["controls", "joy8"], ["buttons", "6"], ["players", "2"]];
const CG_CFG_KEYS = ["name", "platform", "exe", "command", "mode", "category", "controls", "buttons", "players"];

// Os arquivos do pacote: [rotulo, classe (a cor), chave do texto, extensao no
// nome, obrigatorio].
const CG_FILES = [[".cfg", "t-cfg", "cfg", "cfg", true], [".jpg", "t-img", "jpg", "jpg"], ["logo", "t-logo", "logo", "logo.png"],
  [".mp4", "t-vid", "mp4", "mp4"], [".txt", "t-txt", "txt", "txt"], [".key", "t-key", "key", "key"], [".ppdb", "t-ppdb", "ppdb", "ppdb"]];

// A estrutura do pacote: o zip aberto, cada arquivo com a cor do seu tipo e
// se e obrigatorio, e o cfg de exemplo ao lado, com o que cada chave faz.
function cgStructure() {
  const game = CG_EXAMPLE;
  const need = (on) => el("span", { class: "cg-need" + (on ? " on" : "") }, t(on ? "cg_required" : "cg_optional"));
  const file = (label, cls, key, ext, required) => el("li", { class: "cg-file " + cls },
    el("span", { class: "cg-ext" }, label),
    el("span", { class: "cg-fname" }, el("code", {}, game + (ext ? "." + ext : "/")), el("small", {}, t("cg_tree_" + key))),
    need(required));
  const cfg = el("pre", { class: "cg-cfg" }, ...CG_EXAMPLE_CFG.flatMap(([k, v]) =>
    [el("span", { class: "cg-k" }, k), el("span", { class: "cg-eq" }, "="), el("span", { class: "cg-v" }, v), "\n"]));
  return el("details", { class: "cg-structure" },
    el("summary", {}, icon("px-install"), el("b", {}, t("cg_structure")), el("code", { class: "cg-zipname" }, t("cg_game_word") + CG_SUFFIX),
      icon("g-chevd")),
    el("div", { class: "cg-anatomy" },
      el("section", { class: "cg-card-files" },
        el("h5", {}, t("cg_example")),
        el("div", { class: "cg-zipbar" }, icon("px-install"), el("code", {}, game + CG_SUFFIX)),
        el("ul", { class: "cg-filelist" }, ...CG_FILES.map((f) => file(...f)), file("/", "t-dir", "folder", "", true))),
      el("section", { class: "cg-card-cfg" },
        el("h5", {}, t("cg_cfg_title")),
        el("div", { class: "cg-cfgfile" }, el("span", { class: "cg-ext" }, ".cfg"), el("code", {}, game + ".cfg"), need(true)),
        cfg,
        el("dl", { class: "cg-cfg-keys" }, ...CG_CFG_KEYS.flatMap((k) => [el("dt", {}, el("code", {}, k)),
          el("dd", {}, t("cg_cfg_" + k).replace("%s", game + "/"))])))),
    el("p", { class: "cg-structure-note" }, icon("g-info"), el("span", {}, t("cg_structure_note"))));
}

async function cgLoad() {
  if (!cg.el) return;
  // O describe do Setup (que tambem move os pacotes de antes para a pasta
  // deles) e, depois, os cartoes dos pacotes.
  const res = await api("/api/customgames");
  const info = await res.json().catch(() => ({}));
  if (!res.ok) {
    cg.el.list.replaceChildren(el("p", { class: "error" }, info.error || res.statusText));
    return;
  }
  const pres = await api("/api/customgames/packages");
  cg.packages = pres.ok ? ((await pres.json().catch(() => ({}))).packages || []) : [];
  cg.info = info;
  if (!cg.defaultGroup || !cgGroups().includes(cg.defaultGroup)) cg.defaultGroup = cgGroups()[0] || "";
  // O grupo de quem instala: o ultimo usado (o Setup tambem o lembra).
  if (!cg.installGroup || !cgGroups().includes(cg.installGroup)) cg.installGroup = info.last_group || cg.defaultGroup;
  cgRenderList();
  cgRenderInstall();
  cgRenderCreate();
  cgRenderPacked();
  cgRenderBulk();
  cgShowTab(cg.tab);
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
    const del = el("button", { type: "button", class: "icon-btn small cg-gdel", title: t("cg_group_delete"),
      "aria-label": t("cg_group_delete") + ": " + g.name }, icon("g-trash"));
    del.addEventListener("click", () => cgDeleteGroup(g.name).catch(() => {}));
    return el("section", { class: "cg-group" },
      el("h4", {}, icon("px-games"), g.name, el("span", { class: "dim" }, mine.length === 1 ? t("cg_game_1") : t("cg_games_n").replace("%n", mine.length)), del),
      mine.length ? el("div", { class: "cg-tiles" }, ...mine.map(cgTile)) : el("p", { class: "dim cg-empty" }, t("cg_group_empty")));
  }));
}

// Apagar o grupo inteiro: o Setup diz antes o que vai junto (as pastas dos
// jogos, os pacotes da pasta dele, outros arquivos); as pastas e os pacotes
// so saem se a pessoa disser (os pacotes mantidos voltam a ~/roms/custom).
async function cgDeleteGroup(name) {
  const res = await api("/api/customgames/group-info", { method: "POST", body: JSON.stringify({ name }) });
  const info = await res.json().catch(() => ({}));
  if (!res.ok) { toast(info.error || res.statusText, "bad"); return; }
  const n = (key) => parseInt(info[key] || "0", 10) || 0;
  const games = n("games"), folders = n("folders"), packages = n("packages"), others = n("others");
  let text = t(games === 0 ? "cg_gdel_ask_0" : games === 1 ? "cg_gdel_ask_1" : "cg_gdel_ask").replace("%s", name).replace("%n", games);
  if (others) text += " " + t("cg_gdel_others").replace("%s", (info.other || "") + (others > 5 ? " (+" + (others - 5) + ")" : ""));
  if (!(await ask({ title: t("cg_group_delete") + ": " + name, text, yes: t("cg_delete"), danger: true }))) return;
  let all = false;
  if (folders || packages) {
    const what = [folders ? t("cg_gdel_folders") : "", packages ? t("cg_gdel_packages") : ""].filter(Boolean).join(t("cg_and"));
    all = await ask({ title: t("cg_group_delete") + ": " + name,
      text: t("cg_gdel_all_ask").replace("%s", what) + (packages ? " " + t("cg_gdel_pkg_note") : ""),
      yes: t("cg_gdel_all"), no: t("cg_gdel_keep"), danger: true });
  }
  const task = await cgTask("/api/customgames/group-delete", { name, all });
  if (task && task.rc === 0) {
    if (cg.defaultGroup === name) cg.defaultGroup = "";
    toast(t("cg_deleted").replace("%s", name), "ok");
  }
}

function cgTile(game) {
  const system = "custom/" + game.group;
  const img = el("img", { alt: "", loading: "lazy" });
  img.addEventListener("error", () => { img.replaceWith(el("div", { class: "cg-noimg" }, game.name.slice(0, 2).toUpperCase())); });
  img.src = mediaUrl(system, game.name, "snap");
  fadeIn(img);
  const logo = el("img", { class: "cg-logo", alt: "", loading: "lazy", src: mediaUrl(system, game.name, "logo") });
  logo.addEventListener("error", () => logo.remove());
  const actions = [["g-play", "cg_play", () => cgPlay(game)]];
  if (game.platform !== "script") actions.push(["px-edit", "cg_edit", () => cgEdit(game)]);
  if (game.platform === "windows" || game.platform === "native") actions.push(["px-install", "cg_package", () => cgPack(game)]);
  actions.push(["g-trash", "cg_delete", () => cgDelete(game)]);
  return el("div", { class: "cg-tile", tabindex: "0" }, el("div", { class: "cg-snap" }, img, logo),
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

// O pacote de um jogo instalado: vai para ~/roms/custom-packages (a aba
// Instalar pacotes o mostra).
async function cgPack(game) {
  const task = await cgTask("/api/customgames/pack", { group: game.group, name: game.name });
  if (task && task.rc === 0) toast(t("cg_packaged").replace("%s", game.name), "ok");
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
      if (row.text && row.text.id) media.text = row.text.id;
      if (row.logo && row.logo.id) media.logo = row.logo.id;
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
  const mode = game.mode || "640x480@60";
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
  return el(name === "art" ? "div" : "label", { class: "cg-field cg-f-" + name }, el("span", {}, t("cg_f_" + name)), control);
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

// ── A aba Instalar pacotes ──
// Os pacotes de ~/roms/custom-packages (o compartilhamento \\fliperos\roms):
// os novos com o grupo para escolher (o ultimo usado ja marcado), os que
// mudaram desde a instalacao, os instalados (com o grupo) e os que nao
// servem. Depois de instalar, pergunta se o zip sai.

const cgBaseName = (p) => p.zip.split("/").pop();
// Os cartoes por pagina, e o filtro e a ordem (ficam no navegador).
const CG_PAGE = 10;
const CG_VIEW = "fliperos-cg-packages-view";
const CG_SORTS = ["name", "newest", "size", "state"];
const CG_STATE_ORDER = { new: 0, update: 1, bad: 2, installed: 3 };

function cgView() {
  if (!cg.view) {
    cg.view = { query: "", state: "", platform: "", sort: "name", page: 0 };
    try { Object.assign(cg.view, JSON.parse(localStorage.getItem(CG_VIEW) || "{}"), { query: "", page: 0 }); } catch (e) { /* sem armazenamento */ }
  }
  return cg.view;
}

function cgViewSave() {
  const v = cgView();
  try { localStorage.setItem(CG_VIEW, JSON.stringify({ state: v.state, platform: v.platform, sort: v.sort })); } catch (e) { /* sem armazenamento */ }
}

function cgRenderInstall() {
  const box = cg.el.install;
  const rows = cg.packages || [];
  const folder = cg.info.packages_dir || "~/roms/custom-packages";
  const zipInput = el("input", { type: "file", accept: ".zip", multiple: "", hidden: "" });
  zipInput.addEventListener("change", async () => {
    const files = [...zipInput.files];
    zipInput.value = "";
    for (const f of files) await cgUploadZip(f);
    cgLoad().catch(() => {});
  });
  const send = el("button", { type: "button", class: "btn small", title: t("cg_zip_name_rule") }, icon("g-upload"), t("cg_send_zip"));
  send.addEventListener("click", () => zipInput.click());
  const drop = el("div", { class: "cg-drop", tabindex: "0", role: "button", title: t("cg_zip_name_rule") },
    icon("g-upload"), el("strong", {}, t("cg_drop_title")), el("span", { class: "dim" }, t("cg_drop_sub")));
  drop.addEventListener("click", () => zipInput.click());
  drop.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); zipInput.click(); } });
  let depth = 0;
  drop.addEventListener("dragenter", (ev) => { ev.preventDefault(); depth++; drop.classList.add("over"); });
  drop.addEventListener("dragover", (ev) => { ev.preventDefault(); });
  drop.addEventListener("dragleave", () => { if (--depth <= 0) { depth = 0; drop.classList.remove("over"); } });
  drop.addEventListener("drop", async (ev) => {
    ev.preventDefault();
    depth = 0;
    drop.classList.remove("over");
    const files = [...(ev.dataTransfer ? ev.dataTransfer.files : [])];
    for (const f of files) await cgUploadZip(f);
    cgLoad().catch(() => {});
  });
  if (!cg.el.progress) cg.el.progress = el("div", { class: "cg-progress" });
  const fresh = rows.filter((p) => p.state === "new" || p.state === "update");
  const bar = el("div", { class: "cg-bar" }, send, zipInput);
  if (fresh.length > 1) {
    const allGroup = cgGroupSelect(cg.installGroup, (value) => { cg.installGroup = value; });
    const all = el("button", { type: "button", class: "btn ghost small" }, icon("px-install"),
      t("cg_install_all_new").replace("%n", fresh.length));
    all.addEventListener("click", () => cgInstallAll(fresh, allGroup.value).catch(() => {}));
    bar.append(el("span", { class: "cg-allgroup" }, all, el("span", { class: "dim" }, t("cg_in_group")), allGroup));
  }
  // O filtro e a ordem: feitos uma vez (a busca nao perde o cursor).
  if (!cg.el.pkgTools) {
    const v = cgView();
    const search = el("input", { type: "search", placeholder: t("cg_pkg_search"), "aria-label": t("cg_pkg_search"), value: v.query });
    search.addEventListener("input", () => { v.query = search.value; v.page = 0; cgDrawPackages(); });
    const pick = (key, options) => {
      const s = el("select", { "aria-label": t("cg_pkg_" + key) }, ...options.map(([value, label]) => el("option", { value }, label)));
      s.value = v[key];
      s.addEventListener("change", () => { v[key] = s.value; v.page = 0; cgViewSave(); cgDrawPackages(); });
      return s;
    };
    cg.el.pkgTools = el("div", { class: "cg-pkgtools" }, search,
      pick("state", [["", t("cg_pkg_all")], ...["new", "update", "installed", "bad"].map((s) => [s, t("cg_pkg_state_" + s)])]),
      pick("platform", [["", t("cg_pkg_all_types")], ["windows", t("cg_windows")], ["native", t("cg_native")]]),
      pick("sort", CG_SORTS.map((s) => [s, t("cg_pkg_sort_" + s)])));
    cg.el.pkgGrid = el("div", { class: "cg-cards" });
    cg.el.pkgPager = el("nav", { class: "cg-pager", "aria-label": t("cg_pkg_pages") });
  }
  box.replaceChildren(el("p", { class: "dim cg-folder" }, t("cg_packages_where").replace("%s", folder)), drop, cg.el.progress, bar,
    ...(rows.length ? [cg.el.pkgTools, cg.el.pkgGrid, cg.el.pkgPager] : [el("p", { class: "dim cg-empty" }, t("cg_packages_none"))]));
  // O zip que acabou de chegar (Criar pacote, Enviar): a pagina dele.
  if (cg.highlight) {
    const v = cgView();
    Object.assign(v, { query: "", state: "", platform: "" });
    const list = cgPackagesShown();
    const at = list.findIndex((p) => p.zip === cg.highlight);
    if (at >= 0) v.page = Math.floor(at / CG_PAGE);
  }
  cgDrawPackages();
  if (cg.highlight) {
    const card = box.querySelector('[data-zip="' + CSS.escape(cg.highlight) + '"]');
    cg.highlight = "";
    if (card) { card.classList.add("flash"); card.scrollIntoView({ behavior: "smooth", block: "center" }); }
  }
}

// Os pacotes que o filtro deixa, na ordem escolhida.
function cgPackagesShown() {
  const v = cgView();
  const q = v.query.trim().toLowerCase();
  const list = (cg.packages || []).filter((p) => (!v.state || p.state === v.state) && (!v.platform || p.platform === v.platform) &&
    (!q || [p.name, p.file, p.category, p.group].some((s) => (s || "").toLowerCase().includes(q))));
  const by = {
    name: (a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }),
    newest: (a, b) => b.mtime - a.mtime,
    size: (a, b) => (b.bytes || b.size) - (a.bytes || a.size),
    state: (a, b) => (CG_STATE_ORDER[a.state] - CG_STATE_ORDER[b.state]) || a.name.localeCompare(b.name),
  }[v.sort] || (() => 0);
  return list.sort(by);
}

function cgDrawPackages() {
  const v = cgView();
  const list = cgPackagesShown();
  const pages = Math.max(1, Math.ceil(list.length / CG_PAGE));
  v.page = Math.min(v.page, pages - 1);
  const shown = list.slice(v.page * CG_PAGE, (v.page + 1) * CG_PAGE);
  cg.el.pkgGrid.replaceChildren(...(shown.length ? shown.map(cgPackageCard) : [el("p", { class: "dim cg-empty" }, t("cg_pkg_none_match"))]));
  const go = (page) => { v.page = page; cgDrawPackages(); cg.el.pkgTools.scrollIntoView({ behavior: "smooth", block: "nearest" }); };
  const button = (label, page, on, aria) => {
    const b = el("button", { type: "button", class: "cg-page" + (on ? " on" : ""), "aria-label": aria || label }, label);
    if (page < 0 || page >= pages || on) b.disabled = true;
    else b.addEventListener("click", () => go(page));
    return b;
  };
  cg.el.pkgPager.hidden = pages < 2 && list.length <= CG_PAGE;
  cg.el.pkgPager.replaceChildren(button("‹", v.page - 1, false, t("cg_pkg_prev")),
    ...Array.from({ length: pages }, (_, i) => button(String(i + 1), i, i === v.page)),
    button("›", v.page + 1, false, t("cg_pkg_next")),
    el("span", { class: "dim" }, list.length ? t("cg_pkg_range").replace("%a", v.page * CG_PAGE + 1)
      .replace("%b", v.page * CG_PAGE + shown.length).replace("%n", list.length) : ""));
}

// O cartao de um pacote: o cartao do jogo (como no frontend) com o estado,
// os problemas e as acoes.
function cgPackageCard(p) {
  const media = (kind) => (p.media && p.media[kind] ? "/api/customgames/package-media?zip=" + encodeURIComponent(p.zip) +
    "&member=" + encodeURIComponent(p.media[kind]) : "");
  const actions = [];
  let tag;
  if (p.state === "bad") {
    const n = (p.problems || []).length;
    tag = { cls: "bad", text: n === 1 ? t("cg_problem_1") : t("cg_problems_n").replace("%n", n) };
    actions.push(cgPkgButton("cg_file_delete", () => cgDeletePackage(p), "ghost"));
  } else if (p.state === "installed") {
    tag = { cls: "on", text: t("cg_installed_in").replace("%s", p.group) };
    actions.push(cgPkgButton("cg_install_again", () => cgInstallPackage(p, p.group, { replace: true })),
      cgPkgButton("cg_pkg_delete", () => cgDeletePackage(p), "ghost"));
  } else if (p.state === "update") {
    tag = { cls: "warn", text: t("cg_newer_than").replace("%s", p.group) };
    actions.push(cgPkgButton("cg_install", () => cgInstallPackage(p, p.group, { replace: true }), "small"));
  } else {
    tag = { cls: "new", text: t("cg_pkg_state_new") };
    const group = cgGroupSelect(cg.installGroup, (value) => { cg.installGroup = value; });
    actions.push(group, cgPkgButton("cg_install", () => cgInstallPackage(p, group.value), "small"));
  }
  const card = cgCard({ name: p.name, file: p.file, platform: p.platform, mode: p.mode, category: p.category, controls: p.controls,
    buttons: p.buttons, players: p.players, snap: media("snap"), logo: media("logo"), video: media("preview"), text: media("texto"),
    size: p.bytes || p.size, key: p.key, ppdb: p.ppdb, tag, problems: p.state === "bad" ? cgProblems(p) : [] }, actions);
  card.dataset.zip = p.zip;
  return card;
}

// cgCard: um jogo como o frontend o mostra: a imagem e, com o cursor (ou um
// toque), o video; o nome correndo quando nao cabe; o tipo, o modo, os
// jogadores, o controle e os botoes em icones; a categoria; o texto rolando
// devagar quando e maior que o espaco. info.text: o endereco do .txt, ou o
// proprio texto em info.textValue. Serve a lista de pacotes e a previa do
// Criar pacote.
function cgCard(info, actions = []) {
  const name = info.name || info.file || "?";
  const art = el("div", { class: "cg-cmedia" });
  const initials = () => el("div", { class: "cg-noimg" }, name.slice(0, 2).toUpperCase());
  if (info.snap) {
    const img = el("img", { alt: "", loading: "lazy", src: info.snap });
    img.addEventListener("error", () => img.replaceWith(initials()));
    art.append(img);
  } else art.append(initials());
  // O logotipo (a wheel) por cima da imagem, embaixo, como o frontend o poe.
  if (info.logo) {
    const logo = el("img", { class: "cg-logo", alt: name, loading: "lazy", src: info.logo });
    logo.addEventListener("error", () => logo.remove());
    art.append(logo);
  }
  const card = el("article", { class: "cg-card", tabindex: "-1" });
  if (info.video) {
    const video = el("video", { loop: "", playsinline: "", preload: "none", src: info.video, "aria-hidden": "true" });
    video.muted = true;
    const play = () => { video.muted = true; video.play().then(() => art.classList.add("playing")).catch(() => {}); };
    const stop = () => { video.pause(); art.classList.remove("playing"); };
    card.addEventListener("mouseenter", play);
    card.addEventListener("mouseleave", stop);
    card.addEventListener("focusin", play);
    card.addEventListener("focusout", (ev) => { if (!card.contains(ev.relatedTarget)) stop(); });
    art.addEventListener("click", () => (art.classList.contains("playing") ? stop() : play()));
    art.append(video, el("span", { class: "cg-cplay", title: t("cg_f_video") }, icon("g-play")));
    art.classList.add("has-video");
  }
  if (info.tag) art.append(el("span", { class: "cg-ctag " + info.tag.cls }, info.tag.text));
  // O nome: corre de um lado a outro quando nao cabe (como no frontend).
  const title = el("span", {}, name);
  const head = el("h5", { class: "cg-cname", title: info.file ? name + " · " + info.file : name }, title);
  requestAnimationFrame(() => {
    const extra = title.scrollWidth - head.clientWidth;
    if (extra > 4) { head.classList.add("run"); head.style.setProperty("--run", -extra + "px"); head.style.setProperty("--run-s", Math.max(4, extra / 25) + "s"); }
  });
  const facts = el("div", { class: "cg-cfacts" });
  if (info.platform) facts.append(el("span", { class: "tag" }, t("cg_" + info.platform)));
  if (info.mode) facts.append(el("span", { class: "tag" }, cgModeLabel(info.mode)));
  const ctrl = controlIcons({ control: info.controls || "", players: info.players || "", buttons: info.buttons || "" });
  if (ctrl) facts.append(ctrl);
  if (info.key) facts.append(el("span", { class: "tag on", title: t("cg_tree_key") }, ".key"));
  if (info.ppdb) facts.append(el("span", { class: "tag on", title: t("cg_tree_ppdb") }, ".ppdb"));
  const body = el("div", { class: "cg-cbody" }, head, facts);
  if (info.category) body.append(el("div", { class: "cg-ccat" }, info.category));
  // O texto: rola de cima a baixo, devagar, quando nao cabe.
  if (info.text || info.textValue) {
    const inner = el("div", {});
    const box = el("div", { class: "cg-ctext" }, inner);
    const show = (text) => {
      inner.textContent = text.trim();
      requestAnimationFrame(() => {
        const extra = inner.scrollHeight - box.clientHeight;
        box.classList.toggle("roll", extra > 4);
        if (extra > 4) { box.style.setProperty("--roll", -extra + "px"); box.style.setProperty("--roll-s", Math.max(6, extra / 8) + "s"); }
      });
    };
    if (info.textValue) show(info.textValue);
    else fetch(info.text, { headers: { "X-FliperOS": "1" } }).then((r) => (r.ok ? r.text() : "")).then(show).catch(() => {});
    body.append(box);
  }
  if (info.problems && info.problems.length) body.append(el("ul", { class: "cg-problems" }, ...info.problems.map((text) => el("li", {}, text))));
  if (info.size) body.append(el("div", { class: "cg-csize dim" }, bytes(info.size)));
  card.append(art, body);
  if (actions.length) card.append(el("div", { class: "cg-cact" }, ...actions));
  return card;
}

// Os problemas de um pacote que nao serve, um por linha, traduzidos pelos
// codigos (config/fliperos-customgame); um codigo sem texto aqui mostra o
// motivo em ingles do verificador.
const CG_PROBLEM_CODES = ["not_zip", "unsafe", "encrypted", "misnamed", "cfg_missing", "cfg_many", "cfg_text", "folder_missing",
  "stranger", "strangers_more", "two_files", "name_missing", "name_bad", "platform_missing", "platform_bad", "exe_missing",
  "exe_not_found", "command_missing", "mode_bad", "category_long", "controls_bad", "buttons_bad", "players_bad", "runner_bad"];

function cgProblems(p) {
  const base = p.name || cgBaseName(p).replace(/\.fliperos-customgame\.zip$|\.zip$/i, "");
  return (p.problems || []).map(({ code, arg, text }) =>
    (CG_PROBLEM_CODES.includes(code) ? t("cg_pb_" + code).split("%s").join(arg).split("%g").join(base) : text || code));
}

function cgPkgButton(label, fn, kind) {
  const b = el("button", { type: "button", class: "btn " + (kind === "small" ? "small" : "ghost small") }, t(label));
  b.addEventListener("click", () => fn().catch(() => {}));
  return b;
}

// Uma linha de progresso (envio ou instalacao, PortProton incluido) no painel
// da aba Instalar pacotes: barra + texto; end() deixa o resultado e some.
function cgProgress(label) {
  const bar = meter(0);
  const text = el("span", { class: "dim" }, "");
  const row = el("div", { class: "cg-prow" }, el("div", { class: "cg-pname" }, label), bar, text);
  if (!cg.el.progress) cg.el.progress = el("div", { class: "cg-progress" });
  cg.el.progress.append(row);
  return {
    set(pct, msg) {
      bar.firstChild.style.width = Math.max(0, Math.min(100, pct || 0)) + "%";
      if (msg != null) text.textContent = msg;
    },
    end(ok, msg) {
      bar.firstChild.style.width = "100%";
      row.classList.add(ok ? "ok" : "bad");
      text.textContent = msg || "";
      setTimeout(() => row.remove(), ok ? 4000 : 12000);
    },
  };
}

// Instala um pacote no grupo; o que ja esta nele pergunta se troca. quiet:
// sem perguntar antes nem depois (o "instalar todos" pergunta no fim).
async function cgInstallPackage(p, group, { replace = false, quiet = false } = {}) {
  if (!group || group === "+new") { toast(t("cg_zip_group"), "bad"); return false; }
  const there = (cg.info.games || []).some((g) => g.group === group && g.name === p.name);
  if (there && !replace) {
    if (!(await ask({ title: p.name, text: t("cg_replace_ask").replace("%s", p.name).replace("%s", group), yes: t("cg_install"), danger: true }))) {
      return false;
    }
    replace = true;
  }
  let pp = false;
  if (p.platform === "windows" && !cg.info.portproton) {
    pp = await ask({ title: "PortProton", text: t("cg_pp"), yes: t("cg_pp_install"), no: t("cg_cancel") });
  } else if (!quiet && !there && !(await ask({ title: p.name, text: t("cg_install") + ": " + p.name + " → " + group, yes: t("cg_install") }))) {
    return false;
  }
  const prog = cgProgress(t("cg_installing").replace("%s", p.name));
  prog.set(0, "…");
  const task = await cgTask("/api/customgames/install", { zip: p.zip, group, replace, portproton: pp },
    (tk) => prog.set(tk.pct || 0, (tk.step || "") + (tk.pct ? " · " + Math.round(tk.pct) + "%" : "")));
  const ok = !!task && task.rc === 0;
  prog.end(ok, ok ? t("cg_installed_ok").replace("%s", p.name) : (task && (task.error || task.last)) || t("task_fail"));
  if (ok) cg.installGroup = group;
  if (ok && !quiet && (await ask({ title: p.name, text: t("cg_pkg_delete_ask").replace("%s", cgBaseName(p)).replace("%s", group),
    yes: t("cg_pkg_delete"), no: t("cg_pkg_keep") }))) {
    await cgDeletePackage(p, true);
  }
  return ok;
}

async function cgInstallAll(rows, group) {
  if (!group || group === "+new") { toast(t("cg_zip_group"), "bad"); return; }
  if (!(await ask({ title: t("cg_install_all_new").replace("%n", rows.length),
    text: t("cg_install_all_ask").replace("%n", rows.length).replace("%s", group), yes: t("cg_install") }))) return;
  const done = [];
  for (const p of rows) {
    if (await cgInstallPackage(p, p.state === "update" ? p.group : group, { replace: p.state === "update", quiet: true })) done.push(p);
  }
  if (done.length && (await ask({ title: t("cg_install_all_new").replace("%n", rows.length),
    text: t("cg_pkg_delete_all_ask").replace("%n", done.length), yes: t("cg_pkg_delete"), no: t("cg_pkg_keep") }))) {
    for (const p of done) await cgDeletePackage(p, true);
  }
  cgLoad().catch(() => {});
}

// Apaga o zip da pasta dos pacotes (o jogo instalado dele fica). sure: sem
// perguntar (a pergunta ja foi feita).
async function cgDeletePackage(p, sure) {
  if (!sure && !(await ask({ title: cgBaseName(p), text: t("cg_pkg_delete_one").replace("%s", cgBaseName(p)),
    yes: t("cg_pkg_delete"), danger: true }))) return;
  const res = await api("/api/customgames/package-delete", { method: "POST", body: JSON.stringify({ zip: p.zip }) });
  toast(res.ok ? t("cg_deleted").replace("%s", cgBaseName(p)) : (await res.json().catch(() => ({}))).error || res.statusText,
    res.ok ? "ok" : "bad");
  cgLoad().catch(() => {});
}

// Enviar um pacote: so JOGO.fliperos-customgame.zip, para a pasta dos
// pacotes; ele aparece na lista para instalar. Outro nome volta com a regra.
async function cgUploadZip(file) {
  if (!file.name.toLowerCase().endsWith(CG_SUFFIX)) {
    const stem = file.name.replace(/\.zip$/i, "").replace(/\.fliperos-customgame$/i, "") || t("cg_game_word");
    toast(t("cg_zip_name").replace("%s", file.name).replace("%s", stem + CG_SUFFIX), "bad");
    return false;
  }
  const prog = cgProgress(t("cg_uploading").replace("%s", file.name));
  prog.set(0, "0%");
  const status = await cgPostFile("/api/upload?root=roms&path=custom-packages&name=" + encodeURIComponent(file.name) +
    "&overwrite=1", file, (frac) => prog.set(frac * 100, Math.round(frac * 100) + "%"));
  if (status !== 200) {
    prog.end(false, String(status || "network error"));
    toast(file.name + ": " + (status || "network error"), "bad");
    return false;
  }
  prog.end(true, t("cg_zip_sent").replace("%s", file.name));
  toast(t("cg_zip_sent").replace("%s", file.name), "ok");
  cg.highlight = (cg.info.packages_dir || "") + "/" + file.name;
  return true;
}

// ── A aba Criar pacote ──
// Um jogo do Windows ou do Linux numa pasta (a mesma linha de Adicionar um
// jogo, sem grupo): o zip vai para ~/roms/custom-packages e aparece na aba
// Instalar pacotes. A pasta com a estrutura do pacote preenche o resto.

const CG_CREATE_FIELDS = ["name", "platform", "folder", "run", "mode", "category", "players", "buttons", "controls", "art"];

function cgRenderCreate() {
  const box = cg.el.create;
  if (!cg.createRow) cg.createRow = cgNewRow({ platform: "windows" });
  if (!box.dataset.built) {
    box.dataset.built = "1";
    cg.el.structure = cgStructure();
    cg.el.createForm = el("div", { class: "cg-one cg-create" });
    cg.el.createStatus = el("div", { class: "cg-status", role: "status" });
    cg.el.createIntro = el("p", { class: "dim cg-folder" });
    const go = el("button", { type: "button", class: "btn" }, icon("px-add"), t("cg_create_go"));
    go.addEventListener("click", () => cgCreate(go).catch(() => {}));
    const clear = el("button", { type: "button", class: "btn ghost" }, t("cg_create_clear"));
    clear.addEventListener("click", () => {
      cg.createRow = cgNewRow({ platform: "windows" });
      cg.el.createStatus.replaceChildren();
      cgCreateDraw();
    });
    // Previa: o cartao como o frontend vai mostrar o jogo; Testar: o jogo
    // aberto no gabinete, da pasta dele, antes de empacotar.
    const preview = el("button", { type: "button", class: "btn ghost", "aria-pressed": "false" }, icon("g-grid"), t("cg_preview"));
    preview.addEventListener("click", () => {
      cg.el.createPreview.hidden = !cg.el.createPreview.hidden;
      preview.setAttribute("aria-pressed", String(!cg.el.createPreview.hidden));
      cgCreatePreview();
      if (!cg.el.createPreview.hidden) cg.el.createPreview.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
    const test = el("button", { type: "button", class: "btn ghost" }, icon("g-play"), t("cg_test"));
    test.addEventListener("click", () => cgTest(test).catch(() => {}));
    cg.el.createPreview = el("div", { class: "cg-preview", hidden: "" });
    box.append(cg.el.createIntro, cg.el.structure, el("div", { class: "cg-create-wrap" }, cg.el.createForm, cg.el.createPreview),
      cg.el.createStatus, el("div", { class: "cg-create-foot" }, clear, preview, test, go));
    // Sem jogo nem pacote nenhum, a estrutura ja aberta.
    cg.el.structure.open = !(cg.info.games || []).length && !(cg.info.pending || []).length;
  }
  cg.el.createIntro.textContent = t("cg_create_intro").replace("%s", cg.info.packages_dir || "~/roms/custom-packages");
  cgCreateDraw();
}

function cgCreateDraw() {
  const row = cg.createRow;
  if (row.platform === "command") row.platform = "windows";
  const ctl = cgControls(row, { redraw: cgCreateDraw, package: true });
  cg.el.createForm.replaceChildren(...CG_CREATE_FIELDS.map((f) => {
    const field = cgField(f, ctl[f]);
    const err = cgFieldError(row, f);
    if (err) {
      field.classList.add("bad");
      field.append(el("small", { class: "cg-err" }, err));
    }
    return field;
  }));
  // A previa acompanha o que muda no formulario (um campo de texto, ao sair dele).
  if (!cg.el.createForm.dataset.watch) {
    cg.el.createForm.dataset.watch = "1";
    cg.el.createForm.addEventListener("change", () => cgCreatePreview());
  }
  cgCreatePreview();
}

// O cartao da previa: o que a linha tem agora, como o frontend mostraria.
function cgCreatePreview() {
  const box = cg.el.createPreview;
  if (!box || box.hidden) return;
  const row = cg.createRow;
  const modeLabel = row.mode === "other" ? row.modeOther : row.mode;
  const mode = (((cg.info && cg.info.modes) || []).find((m) => m.label === modeLabel) || { value: modeLabel }).value;
  const card = cgCard({ name: row.name.trim() || t("cg_ph_name"), platform: row.platform, mode, category: row.category,
    controls: row.controls.join(","), buttons: row.buttons, players: row.players,
    snap: row.snap ? row.snap.url || "" : "", logo: row.logo ? row.logo.url || "" : "", video: row.video ? row.video.url || "" : "",
    text: row.text && !row.text.value ? row.text.url || "" : "", textValue: row.text ? row.text.value || "" : "",
    key: !!row.key, ppdb: !!row.ppdb && row.platform === "windows", tag: { cls: "new", text: t("cg_preview") } });
  box.replaceChildren(el("h5", {}, t("cg_preview_title")), card, el("p", { class: "dim" }, t("cg_preview_note")));
}

// Testar: o jogo aberto no gabinete da pasta dele, sem instalar. Quando ele
// aparece na tela (o FPS da camada com o nome dele), o aviso das teclas: um
// jogo que nao aceita o controle ganha o mapa pelo menu na tela, que abre
// sozinho, e o mapa vai no pacote.
async function cgTest(button) {
  const row = cg.createRow;
  const status = cg.el.createStatus;
  if (cg.busy) return;
  cg.busy = true;
  button.disabled = true;
  try {
    const payload = cgPayload(row);
    const check = await api("/api/customgames/check-create", { method: "POST", body: JSON.stringify({ row: payload }) });
    const data = await check.json().catch(() => ({}));
    row.errors = {};
    for (const e of data.errors || []) row.errors[e.field] = e.error;
    cgCreateDraw();
    if ((data.errors || []).length) { status.replaceChildren(el("span", { class: "error" }, t("cg_errors"))); return; }
    if (!(await ask({ title: t("cg_test"), text: t("cg_test_ask").replace("%s", row.name), yes: t("cg_test") }))) return;
    const res = await api("/api/customgames/test", { method: "POST", body: JSON.stringify({ row: payload }) });
    const out = await res.json().catch(() => ({}));
    if (!res.ok) { status.replaceChildren(el("span", { class: "error" }, out.error || res.statusText)); return; }
    status.replaceChildren(el("span", {}, t("cg_test_opening").replace("%s", row.name)));
    cg.testApp = out.app;
    // Ate 2 minutos: um jogo do Windows pode demorar (o PortProton).
    for (let i = 0; i < 60; i++) {
      await sleep(2000);
      const s = await api("/api/status").then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
      if (s.fps && s.fps.program === out.app) {
        status.replaceChildren(cgTestPanel(row));
        return;
      }
    }
    status.replaceChildren(el("span", { class: "error" }, t("cg_test_none").replace("%s", row.name).replace("%s", out.app)));
  } finally {
    cg.busy = false;
    button.disabled = false;
  }
}

// Captura a tela do gabinete (a foto, ou 10 segundos de video) para a imagem
// ou o video do pacote: o servidor guarda na espera e devolve o id. say(texto)
// conta o andamento; say(null, erro), a falha. A arte nova, ou null.
async function cgCaptureArt(row, kind, say) {
  let timer = 0;
  if (kind === "video") {
    let left = CG_CAPTURE_SECONDS;
    say(t("cg_cap_recording").replace("%n", left));
    timer = setInterval(() => {
      left = Math.max(0, left - 1);
      say(left ? t("cg_cap_recording").replace("%n", left) : t("cg_cap_encoding"));
    }, 1000);
  } else say(t("cg_cap_taking"));
  try {
    const res = await api("/api/customgames/capture?kind=" + kind, { method: "POST", body: "{}" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) { say(null, data.error || res.statusText); return null; }
    const key = kind === "snap" ? "snap" : "video";
    row[key] = { id: data.id, name: data.name, url: cgStagedUrl(data.id) };
    say(t(kind === "snap" ? "cg_cap_photo_ok" : "cg_cap_video_ok"));
    return row[key];
  } finally {
    clearInterval(timer);
  }
}

// Sobe um arquivo para a espera do servidor e o poe na arte da linha (a
// previa pelo navegador; o texto, lido aqui). false: nao subiu.
async function cgStage(row, key, kind, file, onProgress) {
  const out = await cgPostFile("/api/customgames/stage?kind=" + kind + "&name=" + encodeURIComponent(file.name), file, onProgress, true);
  if (out.status !== 200) {
    toast(t("cg_art_too_big").replace("%s", file.name) + (out.data.error ? " " + out.data.error : ""), "bad");
    row[key] = null;
    return false;
  }
  row[key] = { id: out.data.id, name: file.name, url: key === "text" ? "" : URL.createObjectURL(file) };
  if (key === "text") row[key].value = await file.text().catch(() => "");
  return true;
}

// Criar pacote: a arte em cartoes. A imagem e o video, lado a lado, abrem uma
// bandeja (escolher um arquivo, ou capturar a tela do jogo em teste no
// gabinete); o logotipo e o texto escolhem o arquivo direto.
function cgArtCards(row, changed) {
  const box = el("div", { class: "cg-artcards" });
  const redraw = () => { changed(false); box.replaceWith(cgArtCards(row, changed)); cgCreatePreview(); };
  const card = (key, accept, kind, glyph, tray) => {
    const current = row[key];
    const input = el("input", { type: "file", accept, hidden: "" });
    const preview = el("div", { class: "cg-apreview" });
    if (current && current.url && key === "video") {
      const video = el("video", { src: current.url, muted: "", loop: "", playsinline: "", preload: "metadata", "aria-hidden": "true" });
      video.muted = true;
      preview.addEventListener("mouseenter", () => video.play().catch(() => {}));
      preview.addEventListener("mouseleave", () => video.pause());
      preview.append(video);
    } else if (current && current.url && key !== "text") preview.append(el("img", { src: current.url, alt: "" }));
    else preview.append(icon(current ? "g-check" : glyph));
    const name = el("small", { title: current && current.path ? t("cg_from_folder") + ": " + current.path : "" },
      current ? current.name : t("cg_art_empty_" + key));
    const open = el("button", { type: "button", class: "cg-abtn", "aria-haspopup": tray ? "menu" : "false" }, preview,
      el("span", { class: "cg-ainfo" }, el("b", {}, t("cg_f_" + key)), name));
    const wrap = el("div", { class: "cg-acard " + key + (current ? " on" : "") + (current && current.path ? " found" : "") }, open, input);
    if (current) {
      const drop = el("button", { type: "button", class: "cg-adrop", title: t("cg_remove"), "aria-label": t("cg_remove") + ": " + t("cg_f_" + key) },
        icon("g-close"));
      drop.addEventListener("click", () => { row[key] = null; redraw(); });
      wrap.append(drop);
    }
    const progress = (text) => preview.replaceChildren(el("span", { class: "cg-aprog" }, text));
    input.addEventListener("change", async () => {
      const file = input.files[0];
      input.value = "";
      if (!file) return;
      progress("0%");
      await cgStage(row, key, kind, file, (frac) => progress(Math.round(frac * 100) + "%"));
      redraw();
    });
    if (!tray) { open.addEventListener("click", () => input.click()); return wrap; }
    open.addEventListener("click", () => {
      const was = wrap.querySelector(".cg-tray");
      document.querySelectorAll(".cg-tray").forEach((n) => n.remove());
      if (was) return;
      const capKind = key === "snap" ? "snap" : "video";
      const item = (glyph2, title, hint) => el("button", { type: "button", role: "menuitem", class: "cg-tray-item" }, icon(glyph2),
        el("span", {}, el("b", {}, title), el("small", {}, hint)));
      const file = item("g-upload", t("cg_art_pick"), t("cg_art_pick_" + key));
      const cap = item(key === "snap" ? "g-camera" : "g-play", t("cg_art_capture"), t("cg_art_checking"));
      cap.disabled = true;
      const menu = el("div", { class: "cg-tray", role: "menu" }, file, cap);
      wrap.append(menu);
      const close = () => {
        menu.remove();
        document.removeEventListener("pointerdown", outside, true);
        document.removeEventListener("keydown", esc, true);
      };
      const outside = (ev) => { if (!wrap.contains(ev.target)) close(); };
      const esc = (ev) => { if (ev.key === "Escape") close(); };
      document.addEventListener("pointerdown", outside, true);
      document.addEventListener("keydown", esc, true);
      // Capturar so com o jogo do teste na tela (o /api/status diz qual programa roda).
      api("/api/status").then((r) => (r.ok ? r.json() : {})).catch(() => ({})).then((st) => {
        const live = !!cg.testApp && !!st.fps && st.fps.program === cg.testApp;
        cap.disabled = !live;
        cap.querySelector("small").textContent = live ? t("cg_art_cap_" + key) : t("cg_art_need_test");
      });
      file.addEventListener("click", () => { close(); input.click(); });
      cap.addEventListener("click", async () => {
        close();
        progress("…");
        await cgCaptureArt(row, capKind, (text, error) => { if (error) toast(error, "bad"); else if (text) progress(text); });
        redraw();
      });
      file.focus();
    });
    return wrap;
  };
  box.append(card("snap", ".png,.jpg,.jpeg,.webp,.gif", "snap", "g-camera", true),
    card("video", ".mp4,.mkv,.webm,.avi,.mov,.flv", "video", "g-play", true),
    card("logo", ".png,.jpg,.jpeg,.webp", "logo", "g-star", false), card("text", ".txt", "text", "g-list", false));
  // O JOGO.key e o JOGO.ppdb que vieram com a pasta: so a marca (e tirar).
  for (const key of ["key", "ppdb"].filter((k) => row[k])) {
    const drop = el("button", { type: "button", class: "icon-btn small", "aria-label": t("cg_remove") + ": " + row[key].name }, icon("g-close"));
    drop.addEventListener("click", () => { row[key] = null; redraw(); });
    box.append(el("span", { class: "cg-slot cg-artfile" }, el("span", { class: "tag on cg-chip", title: t("cg_from_folder") + ": " + row[key].path },
      t("cg_f_" + key)), drop));
  }
  return box;
}

// O jogo aberto no teste: o aviso das teclas e a captura da tela do gabinete,
// a foto e 10 segundos de video, que vao para a imagem e o video do pacote.
function cgTestPanel(row) {
  const msg = el("span", { class: "cg-capmsg", role: "status" });
  const shots = el("div", { class: "cg-capshots" });
  const photo = el("button", { type: "button", class: "btn small" }, icon("g-camera"), t("cg_cap_photo"));
  const video = el("button", { type: "button", class: "btn small ghost" }, icon("g-play"), t("cg_cap_video"));
  const close = el("button", { type: "button", class: "btn small ghost" }, icon("g-close"), t("cg_test_close"));
  const busy = (on) => { photo.disabled = on; video.disabled = on; };
  const capture = async (kind) => {
    busy(true);
    const say = (text, error) => msg.replaceChildren(el("span", { class: error ? "error" : "" }, error || text || ""));
    try {
      const got = await cgCaptureArt(row, kind, say);
      if (!got) return;
      const thumb = kind === "snap" ? el("img", { src: got.url, alt: "" })
        : el("video", { src: got.url, controls: "", loop: "", muted: "", playsinline: "", preload: "metadata" });
      shots.append(el("figure", { class: "cg-capshot " + kind }, thumb));
      cgCreateDraw();
    } finally {
      busy(false);
    }
  };
  photo.addEventListener("click", () => capture("snap").catch(() => busy(false)));
  video.addEventListener("click", () => capture("video").catch(() => busy(false)));
  close.addEventListener("click", async () => {
    cg.testApp = "";
    await api("/api/close", { method: "POST", body: "{}" });
    msg.textContent = "";
  });
  return el("div", { class: "cg-testbar" },
    el("div", { class: "cg-testhead" }, icon("g-check"), el("b", {}, t("cg_test_open").replace("%s", row.name))),
    el("p", { class: "cg-testnote" }, t("cg_test_keys")),
    el("p", { class: "cg-capnote dim" }, t("cg_cap_note")),
    el("div", { class: "cg-testact" }, photo, video, close, msg), shots);
}

async function cgCreate(button) {
  const row = cg.createRow;
  const status = cg.el.createStatus;
  if (cg.busy) return;
  cg.busy = true;
  button.disabled = true;
  try {
    const payload = cgPayload(row);
    const res = await api("/api/customgames/check-create", { method: "POST", body: JSON.stringify({ row: payload }) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) { status.textContent = data.error || res.statusText; return; }
    row.errors = {};
    for (const e of data.errors || []) row.errors[e.field] = e.error;
    cgCreateDraw();
    if ((data.errors || []).length) { status.replaceChildren(el("span", { class: "error" }, t("cg_errors"))); return; }
    if (data.bytes + (64 << 20) > data.free) {
      status.replaceChildren(el("span", { class: "error" }, t("cg_space_low").replace("%s", bytes(data.bytes)).replace("%s", bytes(data.free))));
      return;
    }
    const zip = data.out.split("/").pop();
    let replace = false;
    if (data.exists) {
      if (!(await ask({ title: row.name, text: t("cg_create_exists").replace("%s", zip), yes: t("cg_create_replace"), danger: true }))) return;
      replace = true;
    }
    const bar = meter(0);
    const step = el("span", {}, t("cg_creating").replace("%s", zip));
    status.replaceChildren(step, bar);
    cg.highlight = data.out;
    const task = await cgTask("/api/customgames/create", { row: payload, replace }, (tk) => {
      bar.firstChild.style.width = (tk.pct || 0) + "%";
      if (tk.step) step.textContent = tk.step;
    });
    if (task && task.rc === 0) {
      status.replaceChildren(el("span", { class: "ok" }, t("cg_created").replace("%s", zip)));
      toast(t("cg_created").replace("%s", zip), "ok");
      cg.createRow = cgNewRow({ platform: "windows" });
      cgShowTab("install");
    } else {
      cg.highlight = "";
      status.replaceChildren(el("span", { class: "error" }, (task && (task.error || task.last)) || t("task_fail")));
    }
  } finally {
    cg.busy = false;
    button.disabled = false;
  }
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
  return Object.assign({ id: ++cg.seq, group: "", name: "", platform: "windows", folder: "", exe: "", command: "", mode: "480i",
    modeOther: "", category: "", players: "", buttons: "", controls: [], snap: null, video: null, text: null, logo: null, key: null, ppdb: null,
    wine: "", runner: "portproton", exes: [], programs: [], errors: {}, state: "", error: "" }, values || {});
}

// A arte de uma linha: {id} subida pela pessoa, ou {path} a que veio com a
// pasta do jogo (fica no gabinete; a miniatura vem dele).
const cgArtUrl = (path, kind) => "/api/customgames/art?path=" + encodeURIComponent(path) + (kind ? "&kind=" + kind : "");
const cgBase = (path) => path.split("/").pop();
// A arte guardada na espera do servidor (a que subiu ou a capturada no teste).
const cgStagedUrl = (id) => "/api/customgames/staged?id=" + encodeURIComponent(id);

// cgFound: o que veio com a pasta (a estrutura do pacote: JOGO.jpg, .mp4,
// .txt, .key, .ppdb e o JOGO.cfg) na linha. O que a pessoa subiu fica; o que
// veio de outra pasta antes sai.
function cgFound(row, found) {
  if (found.path) row.folder = found.path;
  for (const key of ["snap", "video", "text", "logo"]) {
    if (row[key] && row[key].id) continue;
    const path = found[key] || "";
    row[key] = path ? { path, name: cgBase(path), url: cgArtUrl(path, key === "snap" ? "" : key) } : null;
  }
  for (const key of ["key", "ppdb"]) row[key] = found[key] ? { path: found[key], name: cgBase(found[key]) } : null;
  const cfg = found.cfg || {};
  if (cfg.mode) {
    const known = ((cg.info && cg.info.modes) || []).find((m) => m.value === cfg.mode);
    if (known) { row.mode = known.label; row.modeOther = ""; } else { row.mode = "other"; row.modeOther = cfg.mode; }
  }
  if (cfg.runner) row.runner = cfg.runner;
  if (cfg.category && !row.category) row.category = cfg.category;
  if (cfg.players && !row.players) row.players = cfg.players;
  if (cfg.buttons && !row.buttons) row.buttons = cfg.buttons;
  if (cfg.controls && !row.controls.length) row.controls = cfg.controls.split(",");
  // O exe= (ou command=) do JOGO.cfg vence o que o scan adivinhou.
  if (found.cfg_run && row.platform !== "command") {
    row.platform = found.platform;
    if (found.platform === "windows") row.exe = found.exe; else row.command = found.command;
  }
}

// O que veio com a pasta, para a mensagem: "imagem, video, .key".
function cgFoundList(row) {
  return [["snap", "cg_f_snap"], ["logo", "cg_f_logo"], ["video", "cg_f_video"], ["text", "cg_f_text"], ["key", "cg_f_key"], ["ppdb", "cg_f_ppdb"]]
    .filter(([k]) => row[k] && row[k].path).map(([, label]) => t(label).toLowerCase());
}

function cgDraftLoad() {
  try {
    const saved = JSON.parse(localStorage.getItem(CG_DRAFT) || "null");
    if (saved && Array.isArray(saved.rows)) {
      cg.rows = saved.rows.map((r) => cgNewRow(Object.assign({}, r, { id: undefined, state: "", error: "", errors: {} })));
      cg.rows.forEach((r) => {
        r.id = ++cg.seq;
        // Os enderecos do navegador (blob:) nao voltam: a arte da pasta, sim.
        for (const k of ["snap", "video", "text", "logo"]) {
          if (r[k]) r[k].url = r[k].path ? cgArtUrl(r[k].path, k === "snap" ? "" : k) : r[k].id && k !== "text" ? cgStagedUrl(r[k].id) : "";
        }
      });
      cg.defaultGroup = saved.group || "";
    }
  } catch (e) { /* sem armazenamento */ }
}

function cgDraftSave() {
  try {
    const rows = cg.rows.map((r) => {
      const out = Object.assign({}, r);
      delete out.errors; delete out.state; delete out.error;
      if (out.snap) out.snap = { id: out.snap.id, path: out.snap.path, name: out.snap.name };
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
      snap: null, video: null, text: null, logo: null, errors: {}, state: "", error: "", controls: row.controls.slice() }));
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
  const map = { run: ["exe", "command"], art: ["snap", "logo", "video", "text", "key", "ppdb"], group: ["group"], name: ["name"], platform: ["platform"],
    folder: ["folder"], mode: ["mode"], category: ["category"], players: ["players"], buttons: ["buttons"], controls: ["controls"] };
  return (map[column] || []).map((f) => row.errors[f]).filter(Boolean).join(" ");
}

// cgControls: os campos de uma linha (na tabela ou num dialogo). Mudar o tipo
// ou a pasta redesenha (o executavel depende deles).
function cgControls(row, { redraw, editing, package: pkg } = {}) {
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
  // Um pacote (Criar pacote) e so do Windows ou do Linux.
  out.platform = editing ? el("span", { class: "tag" }, t("cg_" + row.platform))
    : select("platform", CG_PLATFORMS.filter((p) => !pkg || p !== "command").map((p) => [p, t("cg_" + p)]), true);
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
    // O que roda o jogo (runner= no cfg): PortProton (o padrao), Wine ou Wine
    // Staging. Um jogo instalado troca pelo Setup.
    if (!editing) {
      out.run = el("div", { class: "cg-runner" }, out.run, select("runner", [["portproton", t("cg_runner_portproton")],
        ["wine", t("cg_runner_wine")], ["wine-staging", t("cg_runner_staging")]], true));
    }
  } else {
    out.run = text("command", row.platform === "native" ? t("cg_ph_native") : t("cg_ph_command"), "code-in");
    if (row.platform === "native" && row.programs.length) {
      const list = el("datalist", { id: "cg-prog-" + row.id }, ...row.programs.map((p) => el("option", { value: "./" + p.replace(/ /g, "\\ ") })));
      out.run.setAttribute("list", list.id);
      out.run = el("div", {}, out.run, list);
    }
  }
  // O modo: 240p, 240p hack (Mugen), 480i ou outro (o campo LxA@Hz aparece).
  const modes = ((cg.info && cg.info.modes) || [{ label: "240p" }, { label: "480i" }])
    .map((m) => [m.label, m.label === "240p-hack" ? t("cg_mode_hack") : m.label]);
  // O campo LxA@Hz existe sempre e so aparece com "outro": quem nao redesenha
  // (o Editar) mostra o campo do mesmo jeito.
  const mode = select("mode", [...modes, ["other", t("cg_mode_other")]], true);
  const modeOther = text("modeOther", t("cg_ph_mode"), "code-in");
  modeOther.hidden = row.mode !== "other";
  mode.addEventListener("change", () => {
    modeOther.hidden = mode.value !== "other";
    if (!modeOther.hidden && modeOther.isConnected) modeOther.focus();
  });
  out.mode = el("div", { class: "cg-mode" }, mode, modeOther);
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
  out.art = pkg ? cgArtCards(row, changed) : cgArt(row, changed);
  if (row.platform === "windows" && (row.runner || "portproton") === "portproton" && cg.info && cg.info.wine &&
      cg.info.wine.length && !editing && !pkg) {
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

// A arte da linha: a imagem, o video e o texto sobem na hora para a espera
// do servidor (a linha guarda o id), ou vieram com a pasta do jogo (o
// caminho; marcados "da pasta"). O .key e o .ppdb so vem da pasta.
function cgArt(row, changed) {
  const box = el("div", { class: "cg-art" });
  const slot = (key, accept, kind, glyph) => {
    const input = el("input", { type: "file", accept, hidden: "" });
    const current = row[key];
    const label = t("cg_f_" + key);
    const button = el("button", { type: "button", class: "cg-artbtn" + (current ? " on" : "") + (current && current.path ? " found" : ""),
      title: current && current.path ? t("cg_from_folder") + ": " + current.path : label });
    if (current && current.url && (key === "snap" || key === "logo")) button.append(el("img", { src: current.url, alt: "", class: key }));
    else button.append(icon(glyph), el("span", {}, current ? current.name : label));
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
        // A previa (Criar pacote) mostra a imagem e o video pelo navegador, e
        // o texto lido aqui mesmo.
        row[key] = { id: out.data.id, name: file.name, url: key === "text" ? "" : URL.createObjectURL(file) };
        if (key === "text") row[key].value = await file.text().catch(() => "");
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
  // O JOGO.key e o JOGO.ppdb que vieram com a pasta: so a marca (e tirar).
  const chip = (key) => {
    const drop = el("button", { type: "button", class: "icon-btn small", "aria-label": t("cg_remove") + ": " + row[key].name }, icon("g-close"));
    drop.addEventListener("click", () => { row[key] = null; changed(false); box.replaceWith(cgArt(row, changed)); });
    return el("span", { class: "cg-slot" }, el("span", { class: "tag on cg-chip", title: t("cg_from_folder") + ": " + row[key].path },
      t("cg_f_" + key)), drop);
  };
  box.append(slot("snap", ".png,.jpg,.jpeg,.webp,.gif", "snap", "g-camera"), slot("logo", ".png,.jpg,.jpeg,.webp", "logo", "g-star"),
    slot("video", ".mp4,.mkv,.webm,.avi,.mov,.flv", "video", "g-play"),
    slot("text", ".txt", "text", "g-list"), ...["key", "ppdb"].filter((k) => row[k]).map(chip));
  return box;
}

// cgScanRow: os executaveis da pasta (e o tipo e o nome, quando faltam), e o
// que veio com ela na estrutura do pacote (a arte, o .key, o .ppdb, o cfg).
async function cgScanRow(row, redraw, quiet) {
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
  cgFound(row, found);
  row.errors = {};
  cgDraftSave();
  if (redraw) redraw();
  const got = cgFoundList(row);
  if (got.length && !quiet) toast(t("cg_found").replace("%s", got.join(", ")), "ok");
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
  let art = 0;
  for (const g of games) {
    const row = cgNewRow({ group: cg.defaultGroup, name: g.name, platform: g.platform || "windows", folder: g.path, exe: g.exe,
      command: g.command, exes: g.exes || [], programs: g.programs || [] });
    cgFound(row, g);
    if (cgFoundList(row).length) art++;
    cg.rows.push(row);
  }
  cgTableDraw();
  toast(t("cg_import_found").replace("%n", games.length).replace("%s", folder) +
    (art ? " " + t("cg_import_art").replace("%n", art) : ""), "ok");
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
  cg.rows.filter((r) => r.folder && !r.exes.length && !r.programs.length).forEach((r) => cgScanRow(r, cgTableDraw, true).catch(() => {}));
  return added > 0;
}

// ── Conferir e gravar ──

const cgRowMode = (row) => (row.mode === "other" ? row.modeOther.trim() : row.mode);

function cgPayload(row) {
  return { group: row.group, name: row.name.trim(), platform: row.platform, folder: row.platform === "command" ? "" : row.folder.trim(),
    exe: row.platform === "windows" ? row.exe : "", command: row.platform === "windows" ? "" : row.command, mode: cgRowMode(row),
    category: row.category, controls: row.controls.join(","), buttons: row.buttons, players: row.players,
    snap: cgArtRef(row.snap), video: cgArtRef(row.video), text: cgArtRef(row.text), logo: cgArtRef(row.logo), wine: row.platform === "windows" ? row.wine : "",
    key: row.platform !== "command" && row.key ? row.key.path : "", ppdb: row.platform === "windows" && row.ppdb ? row.ppdb.path : "",
    runner: row.platform === "windows" ? row.runner || "portproton" : "" };
}

// O id da arte subida, ou o caminho da que veio com a pasta.
const cgArtRef = (art) => (art ? art.id || art.path || "" : "");

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
