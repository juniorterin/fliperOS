// A area Jogos custom e Sistema > Setup > Jogos > Jogos custom (o Setup >
// Games > Custom games do gabinete), em duas abas: Jogos (os jogos instalados
// em cartoes, por grupo, com o filtro; os pacotes da pasta deles,
// ~/roms/custom-packages, que faltam instalar; o envio de um pacote, que ja
// se instala) e Criar pacote (um pacote, com a previa e o teste no gabinete,
// ou varios de uma vez numa tabela; o pacote feito pergunta se instala).
// Tudo pelo fliperos-setup --customgames (config/fliperos-web,
// /api/customgames).
"use strict";

const cg = { root: null, info: null, packages: [], rows: [], seq: 0, el: null, busy: false, installGroup: "", tab: "games",
  createMode: "one", createRow: null, highlight: "", shown: {}, manyBusy: false };
// A pasta dos pacotes nos textos: onde ela esta de verdade quando e um atalho
// para outro disco (o Setup diz, lib/folders.sh); packages_dir segue sendo o
// caminho para achar os arquivos.
const cgPackagesWhere = () => (cg.info && (cg.info.packages_shown || cg.info.packages_dir)) || "~/roms/custom-packages";
const CG_DRAFT = "fliperos-cg-draft";
const CG_TAB = "fliperos-cg-tab";
const CG_TABS = ["games", "create"];
// Criar pacote: um so (com a previa e o teste) ou varios de uma vez (a tabela).
const CG_CREATE_MODE = "fliperos-cg-create-mode";
const CG_CREATE_MODES = ["one", "many"];
const CG_DELETE_ZIP = "fliperos-cg-delete-zip";
const CG_CAPTURE_SECONDS = 30;
// O nome de todo pacote (config/fliperos-customgame SUFFIX).
const CG_SUFFIX = ".fliperos-customgame.zip";
// As colunas da tabela de varios pacotes: o principal na linha, e o resto (as
// informacoes, o joystick e a arte) nos detalhes dela, abertos por um botao;
// o rotulo de cada uma tambem vai em cada celula (no celular a linha vira um
// cartao).
const CG_COLUMNS = ["name", "platform", "folder", "run", "mode"];
const CG_DETAILS = ["crop", "category", "year", "developer", "players", "buttons", "controls", "joystick", "art"];
const CG_PLATFORMS = ["windows", "native", "command"];
// Colar de uma planilha: os nomes das colunas que o cabecalho pode ter.
const CG_PASTE_NAMES = {
  name: ["name", "nome", "game", "jogo", "title", "titulo", "título"],
  platform: ["type", "tipo", "platform", "plataforma"], folder: ["folder", "pasta", "path", "caminho"],
  run: ["executable", "executavel", "executável", "exe", "command", "comando", "executable or command", "executável ou comando"],
  mode: ["mode", "modo", "video", "vídeo", "resolution", "resolução"], category: ["category", "categoria", "genre", "gênero"],
  players: ["players", "jogadores"], buttons: ["buttons", "botoes", "botões"], controls: ["controls", "controles"],
  year: ["year", "ano"], developer: ["developer", "desenvolvedora", "desenvolvedor", "maker", "fabricante", "studio", "estudio", "estúdio"],
};
const CG_PASTE_ORDER = ["name", "platform", "folder", "run", "mode", "category", "players", "buttons", "controls"];

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
  try {
    if (CG_TABS.includes(localStorage.getItem(CG_TAB))) cg.tab = localStorage.getItem(CG_TAB);
    if (CG_CREATE_MODES.includes(localStorage.getItem(CG_CREATE_MODE))) cg.createMode = localStorage.getItem(CG_CREATE_MODE);
  } catch (e) { /* sem armazenamento */ }
  cg.el = {
    tabs: el("nav", { class: "subtabs", role: "tablist" }),
    games: el("div", { class: "cg-pane" }),
    create: el("div", { class: "cg-pane" }),
  };
  cg.el.panes = { games: cg.el.games, create: cg.el.create };
  box.append(el("div", { class: "cg-head" }, el("h2", {}, t("cg_title")), el("p", { class: "lead" }, t("cg_intro")),
    el("div", { class: "subtabs-bar cg-tabs" }, cg.el.tabs)), cg.el.games, cg.el.create);
  cgDraftLoad();
  cgShowTab(cg.tab);
  await cgLoad();
}

// As abas: Jogos (com quantos pacotes ha para instalar) e Criar pacote. A
// escolhida fica no navegador.
function cgShowTab(tab) {
  cg.tab = CG_TABS.includes(tab) ? tab : "games";
  try { localStorage.setItem(CG_TAB, cg.tab); } catch (e) { /* sem armazenamento */ }
  const waiting = (cg.packages || []).filter((p) => p.state === "new" || p.state === "update").length;
  cg.el.tabs.replaceChildren(...CG_TABS.map((k) => {
    const label = k === "games" && waiting ? t("cg_tab_games") + " (" + waiting + ")" : t("cg_tab_" + k);
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
  ["category", "Fighter / Versus"], ["controls", "joy8"], ["buttons", "6"], ["players", "2"], ["year", "2008"], ["developer", "Capcom"]];
const CG_CFG_KEYS = ["name", "platform", "exe", "command", "mode", "category", "controls", "buttons", "players", "year", "developer"];

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
    cg.el.games.replaceChildren(el("p", { class: "error" }, info.error || res.statusText));
    cg.el.games.dataset.built = "";
    return;
  }
  const pres = await api("/api/customgames/packages");
  cg.packages = pres.ok ? ((await pres.json().catch(() => ({}))).packages || []) : [];
  cg.info = info;
  // O grupo de quem instala: o ultimo usado (o Setup tambem o lembra).
  if (!cg.installGroup || !cgGroups().includes(cg.installGroup)) cg.installGroup = info.last_group || cgGroups()[0] || "";
  cgRenderGames();
  cgRenderCreate();
  cgShowTab(cg.tab);
}

// Os grupos que existem.
function cgGroups() {
  return ((cg.info && cg.info.groups) || []).map((g) => g.name);
}

// Cria o grupo (a pasta dele) e o poe na lista, sem esperar a pagina ler de novo.
// A ficha pede o nome e ja deixa escolher o logotipo (subir uma imagem ou um dos
// que o FliperOS tem); ele so e gravado depois que a pasta existe. Resolve com o
// nome, ou null se a pessoa desistiu. Tem o proprio dialogo: ela tambem abre de
// dentro de outra ficha (o grupo de um jogo), que usa o cgDialog.
function cgNewGroup() {
  return new Promise((resolve) => {
    const dlg = el("dialog", { class: "ask cg-dialog" });
    let answered = false;
    const finish = (name) => {
      if (answered) return;
      answered = true;
      dlg.close();
      dlg.remove();
      resolve(name);
    };
    dlg.addEventListener("close", () => finish(null));
    const name = el("input", { type: "text", value: "", maxlength: "255", autocomplete: "off", spellcheck: "false", "aria-label": t("cg_group_name") });
    const logo = cgLogoField("");
    const make = el("button", { type: "submit", class: "btn" }, icon("g-plus"), t("cg_group_create"));
    const cancel = el("button", { type: "button", class: "btn ghost" }, t("cg_cancel"));
    cancel.addEventListener("click", () => finish(null));
    const form = el("form", { class: "cg-form", method: "dialog" }, el("h3", {}, t("cg_new_group")),
      el("label", { class: "cg-field" }, el("span", {}, t("cg_group_name")), name, el("small", { class: "dim" }, t("cg_group_ask"))),
      logo.node,
      el("footer", {}, cancel, make));
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const fresh = name.value.trim();
      if (!fresh) { name.focus(); return; }
      if (!cgValidName(fresh)) { toast(t("cg_f_group") + ": / | .", "bad"); return; }
      make.disabled = true;
      try {
        const res = await api("/api/customgames/group", { method: "POST", body: JSON.stringify({ name: fresh }) });
        if (!res.ok) { toast((await res.json().catch(() => ({}))).error || res.statusText, "bad"); return; }
        let hasLogo = false;
        if (logo.change) {
          // O grupo ja existe: se a imagem nao serve, ele fica sem logotipo e a pessoa escolhe outro na ficha dele.
          const body = { name: fresh };
          if (logo.change.logo) body.logo = logo.change.logo;
          else if (logo.change.system) body.system = logo.change.system;
          const set = await api("/api/customgames/group-logo", { method: "POST", body: JSON.stringify(body) });
          hasLogo = set.ok;
          if (!set.ok) toast((await set.json().catch(() => ({}))).error || set.statusText, "bad");
          cgLogoStamp = Date.now();
        }
        if (cg.info && !cgGroups().includes(fresh)) cg.info.groups.push({ name: fresh, count: 0, icon: "", logo: hasLogo });
        finish(fresh);
      } finally {
        make.disabled = false;
      }
    });
    dlg.append(form);
    document.body.append(dlg);
    dlg.showModal();
    name.focus();
  });
}

const cgValidName = (s) => !!s && !!s.trim() && !/[/|\n]/.test(s) && !s.startsWith(".");
const cgModeLabel = (mode) => ((cg.info.modes || []).find((m) => m.value === mode) || { label: mode || "?" }).label;

// ── A aba Jogos ──
// Em cima, o envio de um pacote (ele ja se instala no grupo escolhido) e o
// filtro; depois os pacotes que faltam instalar (os novos, os que mudaram e
// os que nao servem) e os grupos, cada um com os cartoes dos jogos
// instalados. Cada cartao abre o jogo, edita (um dialogo), baixa o pacote com
// o que o jogo tem agora e apaga.

const CG_GROUP_PAGE = 12;
const CG_VIEW = "fliperos-cg-games-view";
const CG_SORTS = ["name", "year", "type"];
const CG_STATES = ["installed", "new", "update", "bad"];
const CG_STATE_ORDER = { new: 0, update: 1, bad: 2, installed: 3 };

function cgView() {
  if (!cg.view) {
    cg.view = { query: "", group: "", state: "", platform: "", sort: "name" };
    try { Object.assign(cg.view, JSON.parse(localStorage.getItem(CG_VIEW) || "{}"), { query: "" }); } catch (e) { /* sem armazenamento */ }
    if (!CG_SORTS.includes(cg.view.sort)) cg.view.sort = "name";
  }
  return cg.view;
}

function cgViewSave() {
  const v = cgView();
  try { localStorage.setItem(CG_VIEW, JSON.stringify({ group: v.group, state: v.state, platform: v.platform, sort: v.sort })); } catch (e) { /* sem armazenamento */ }
}

// A parte que nao muda a cada leitura: o envio do pacote, o filtro (a busca
// nao perde o cursor) e as caixas onde o resto se desenha.
function cgBuildGames() {
  const v = cgView();
  const zipInput = el("input", { type: "file", accept: ".zip", multiple: "", hidden: "" });
  zipInput.addEventListener("change", () => {
    const files = [...zipInput.files];
    zipInput.value = "";
    cgUploadFiles(files).catch(() => {});
  });
  const drop = el("div", { class: "cg-drop", tabindex: "0", role: "button", title: t("cg_zip_name_rule") },
    icon("g-upload"), el("strong", {}, t("cg_drop_title")), el("span", { class: "dim" }, t("cg_drop_sub")));
  drop.addEventListener("click", () => zipInput.click());
  drop.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); zipInput.click(); } });
  let depth = 0;
  drop.addEventListener("dragenter", (ev) => { ev.preventDefault(); depth++; drop.classList.add("over"); });
  drop.addEventListener("dragover", (ev) => { ev.preventDefault(); });
  drop.addEventListener("dragleave", () => { if (--depth <= 0) { depth = 0; drop.classList.remove("over"); } });
  drop.addEventListener("drop", (ev) => {
    ev.preventDefault();
    depth = 0;
    drop.classList.remove("over");
    cgUploadFiles([...(ev.dataTransfer ? ev.dataTransfer.files : [])]).catch(() => {});
  });
  // Onde o pacote enviado se instala, e se o zip sai depois (o gabinete guarda a
  // pasta do jogo; o zip so serve para levar o jogo a outro lugar, e se refaz).
  cg.el.dropGroup = el("span", { class: "cg-dropgroup" });
  const keepBox = el("input", { type: "checkbox", "aria-label": t("cg_delete_zip_after") });
  try { keepBox.checked = localStorage.getItem(CG_DELETE_ZIP) === "1"; } catch (e) { /* sem armazenamento */ }
  keepBox.addEventListener("change", () => { try { localStorage.setItem(CG_DELETE_ZIP, keepBox.checked ? "1" : "0"); } catch (e) { /* sem armazenamento */ } });
  cg.el.deleteZip = keepBox;
  cg.el.progress = el("div", { class: "cg-progress" });
  cg.el.upload = el("div", { class: "cg-upload" }, drop,
    el("div", { class: "cg-uopts" }, el("label", { class: "cg-uopt" }, el("span", {}, t("cg_install_into")), cg.el.dropGroup),
      el("label", { class: "check cg-uopt" }, keepBox, el("span", {}, t("cg_delete_zip_after"))), el("span", { class: "dim cg-uhint" }, t("cg_upload_hint"))),
    zipInput);
  // O filtro e a ordem.
  const search = el("input", { type: "search", placeholder: t("cg_search"), "aria-label": t("cg_search"), value: v.query });
  search.addEventListener("input", () => { v.query = search.value; cgDrawGames(); });
  const select = (key, label) => {
    const s = el("select", { "aria-label": label });
    s.addEventListener("change", () => { v[key] = s.value; cgViewSave(); cgDrawGames(); });
    return s;
  };
  const fill = (s, options, value) => { s.replaceChildren(...options.map(([val, label]) => el("option", { value: val }, label))); s.value = options.some(([val]) => val === value) ? value : ""; };
  cg.el.fGroup = select("group", t("cg_f_group"));
  const fState = select("state", t("cg_pkg_state"));
  fill(fState, [["", t("cg_pkg_all")], ...CG_STATES.map((s) => [s, t("cg_state_" + s)])], v.state);
  const fType = select("platform", t("cg_f_platform"));
  fill(fType, [["", t("cg_pkg_all_types")], ...CG_PLATFORMS.map((p) => [p, t("cg_" + p).replace(/ \(.*/, "")])], v.platform);
  const fSort = select("sort", t("cg_pkg_sort"));
  fill(fSort, CG_SORTS.map((s) => [s, t("cg_sort_" + s)]), v.sort);
  const newGroup = el("button", { type: "button", class: "btn ghost small cg-newgroup" }, icon("g-plus"), t("cg_new_group"));
  newGroup.addEventListener("click", () => cgNewGroup().then((name) => { if (name) { toast(t("cg_group_made").replace("%s", name), "ok"); cgLoad().catch(() => {}); } }));
  cg.el.tools = el("div", { class: "cg-pkgtools cg-filters" }, search, cg.el.fGroup, fState, fType, fSort, newGroup);
  cg.el.incoming = el("section", { class: "cg-sec cg-incoming" });
  cg.el.list = el("div", { class: "cg-list" });
  cg.el.packed = el("section", { class: "cg-sec" });
  cg.el.games.replaceChildren(cg.el.upload, cg.el.progress, cg.el.tools, cg.el.incoming, cg.el.list, cg.el.packed);
  cg.el.games.dataset.built = "1";
}

function cgRenderGames() {
  if (!cg.el.games.dataset.built) cgBuildGames();
  const v = cgView();
  // Os dropdowns que dependem dos grupos que existem.
  const groups = cgGroups();
  if (v.group && !groups.includes(v.group)) { v.group = ""; cgViewSave(); }
  cg.el.fGroup.replaceChildren(el("option", { value: "" }, t("cg_all_groups")), ...groups.map((g) => el("option", { value: g }, g)));
  cg.el.fGroup.value = v.group;
  cg.el.dropGroup.replaceChildren(cgGroupSelect(cg.installGroup, (value) => { cg.installGroup = value; }));
  cgDrawGames();
  cgRenderPacked();
}

// O que o filtro deixa: os jogos instalados e os pacotes que faltam instalar.
function cgFiltered() {
  const v = cgView();
  const q = v.query.trim().toLowerCase();
  const hit = (...fields) => !q || fields.some((s) => (s || "").toLowerCase().includes(q));
  const byName = (a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
  const order = {
    name: byName,
    year: (a, b) => (b.year || "").localeCompare(a.year || "") || byName(a, b),
    type: (a, b) => (a.platform || "").localeCompare(b.platform || "") || byName(a, b),
  }[v.sort] || byName;
  const games = (cg.info.games || []).filter((g) => (!v.state || v.state === "installed") && (!v.group || g.group === v.group) &&
    (!v.platform || g.platform === v.platform) && hit(g.name, g.category, g.developer, g.year, g.group)).sort(order);
  const incoming = (cg.packages || []).filter((p) => p.state !== "installed" && (!v.state || p.state === v.state) &&
    (!v.group || p.group === v.group) && (!v.platform || p.platform === v.platform) &&
    hit(p.name, p.file, p.category, p.developer, p.group)).sort((a, b) => (CG_STATE_ORDER[a.state] - CG_STATE_ORDER[b.state]) || byName(a, b));
  return { games, incoming, filtering: !!(q || v.group || v.state || v.platform) };
}

function cgDrawGames() {
  if (!cg.info || !cg.el.list) return;
  const { games, incoming, filtering } = cgFiltered();
  const groups = cg.info.groups || [];
  cgDrawIncoming(incoming);
  const shown = groups.filter((g) => !filtering || games.some((x) => x.group === g.name));
  let body;
  if (!groups.length && !incoming.length) body = [el("p", { class: "dim cg-empty" }, t("cg_empty"))];
  else if (!shown.length && !incoming.length) body = [el("p", { class: "dim cg-empty" }, t("cg_pkg_none_match"))];
  else body = shown.map((g) => cgGroupSection(g, games.filter((x) => x.group === g.name), filtering));
  cg.el.list.replaceChildren(...body);
  // O jogo ou o pacote que acabou de chegar: o cartao dele pisca e aparece.
  if (cg.highlight) {
    const card = cg.el.games.querySelector('[data-key="' + CSS.escape(cg.highlight) + '"]');
    if (card) { cg.highlight = ""; card.classList.add("flash"); card.scrollIntoView({ behavior: "smooth", block: "center" }); }
  }
}

// Os pacotes que faltam instalar, acima dos grupos: o novo (com o grupo para
// escolher), o que mudou desde a instalacao e o que nao serve.
function cgDrawIncoming(incoming) {
  const box = cg.el.incoming;
  box.hidden = !incoming.length;
  if (!incoming.length) { box.replaceChildren(); return; }
  const fresh = incoming.filter((p) => p.state === "new" || p.state === "update");
  const head = el("h4", {}, t("cg_incoming"), el("span", { class: "dim" }, String(incoming.length)));
  if (fresh.length > 1) {
    const group = cgGroupSelect(cg.installGroup, (value) => { cg.installGroup = value; });
    const all = el("button", { type: "button", class: "btn small" }, icon("px-install"), t("cg_install_all_new").replace("%n", fresh.length));
    all.addEventListener("click", () => cgInstallAll(fresh, group.value).catch(() => {}));
    head.append(el("span", { class: "cg-allgroup" }, el("span", { class: "dim" }, t("cg_in_group")), group, all));
  }
  box.replaceChildren(head, el("p", { class: "dim cg-folder" }, t("cg_incoming_note").replace("%s", cgPackagesWhere())),
    el("div", { class: "cg-cards" }, ...incoming.map(cgPackageCard)));
}

// Um grupo: o nome e o logotipo (a ficha de editar abre os dois), a contagem,
// o apagar, e os cartoes dos jogos; com mais de uma pagina, um botao mostra o resto.
function cgGroupSection(g, mine, filtering) {
  const edit = el("button", { type: "button", class: "icon-btn small", title: t("cg_group_edit"), "aria-label": t("cg_group_edit") + ": " + g.name },
    icon("px-edit"));
  edit.addEventListener("click", () => cgEditGroup(g).catch(() => {}));
  const del = el("button", { type: "button", class: "icon-btn small cg-gdel", title: t("cg_group_delete"),
    "aria-label": t("cg_group_delete") + ": " + g.name }, icon("px-remove"));
  del.addEventListener("click", () => cgDeleteGroup(g.name).catch(() => {}));
  const limit = filtering ? Infinity : cg.shown[g.name] || CG_GROUP_PAGE;
  const more = mine.length > limit ? el("button", { type: "button", class: "btn ghost small cg-more" },
    t("cg_show_more").replace("%n", mine.length - limit)) : "";
  if (more) more.addEventListener("click", () => { cg.shown[g.name] = limit + 24; cgDrawGames(); });
  return el("section", { class: "cg-group" },
    el("h4", {}, g.name, g.logo ? el("img", { class: "cg-glogo", src: cgGroupLogoUrl(g.name), alt: "" }) : "",
      el("span", { class: "dim" }, mine.length === 1 ? t("cg_game_1") : t("cg_games_n").replace("%n", mine.length)),
      el("span", { class: "cg-gtools" }, edit, del)),
    mine.length ? el("div", { class: "cg-cards" }, ...mine.slice(0, limit).map(cgGameCard)) : el("p", { class: "dim cg-empty" }, t("cg_group_empty")),
    more);
}

// O logotipo do grupo (GRUPO/.logo.png): de uma cor so, como o dos sistemas, o
// que o marquee e a tira do frontend mostram. O painel o desenha pelo mesmo
// caminho do marquee (/api/marquee/logo); o numero no fim e para o navegador
// pedir de novo quando a pessoa troca o logotipo.
let cgLogoStamp = Date.now();
const cgGroupLogoUrl = (name) => "/api/marquee/logo?name=" + encodeURIComponent(name) + "&v=" + cgLogoStamp;

// cgLogoField(url): o campo do logotipo de um grupo, o mesmo na ficha de editar e
// na de grupo novo. O logotipo e uma imagem subida (so o desenho dela conta), um
// dos que o FliperOS ja tem, numa lista com a previa, ou nenhum. url e o logotipo
// que o grupo ja tem ("" sem nenhum). Devolve o no e, em .change, o que a pessoa
// pediu: undefined fica como esta, null tira, {logo: id} sobe, {system} escolhe
// da lista.
function cgLogoField(url) {
  const logos = (cg.info && cg.info.logos) || [];
  let change;
  const now = el("div", { class: "cg-logo-now" });
  const remove = el("button", { type: "button", class: "btn ghost small" }, icon("g-trash"), t("cg_logo_remove"));
  const showNow = () => {
    let src = "";
    if (change === undefined) src = url;
    else if (change && change.logo) src = cgStagedUrl(change.logo);
    else if (change && change.system) src = "/api/marquee/logo?system=1&name=" + encodeURIComponent(change.system);
    now.replaceChildren(src ? el("img", { src, alt: "" }) : el("span", { class: "dim" }, t("cg_logo_none")),
      change !== undefined ? el("small", { class: "cg-logo-pending" }, t("cg_logo_changed")) : "");
    remove.hidden = !src;
  };
  const file = el("input", { type: "file", accept: "image/png,image/jpeg,image/webp", hidden: "" });
  const upload = el("button", { type: "button", class: "btn small" }, icon("g-upload"), t("cg_logo_upload"));
  upload.addEventListener("click", () => file.click());
  file.addEventListener("change", async () => {
    const picked = file.files && file.files[0];
    file.value = "";
    if (!picked) return;
    upload.disabled = true;
    const out = await cgPostFile("/api/customgames/stage?kind=logo&name=" + encodeURIComponent(picked.name), picked, null, true);
    upload.disabled = false;
    if (out.status !== 200) { toast(t("cg_art_too_big").replace("%s", picked.name) + (out.data.error ? " " + out.data.error : ""), "bad"); return; }
    change = { logo: out.data.id };
    showNow();
  });
  const select = el("select", { class: "cg-logo-select", "aria-label": t("cg_logo_pick") },
    el("option", { value: "" }, t("cg_logo_pick")), ...logos.map((l) => el("option", { value: l.value }, l.label)));
  const use = el("button", { type: "button", class: "btn small", disabled: "" }, t("cg_logo_use"));
  select.addEventListener("change", () => { use.disabled = !select.value; });
  use.addEventListener("click", () => { change = { system: select.value }; showNow(); });
  remove.addEventListener("click", () => { change = null; showNow(); });
  showNow();
  const node = el("div", { class: "cg-field" }, el("span", {}, t("cg_group_logo")), el("small", { class: "dim" }, t("cg_group_logo_note")), now,
    el("div", { class: "cg-logo-row" }, upload, remove, file),
    el("small", { class: "dim" }, t("cg_logo_or")),
    el("div", { class: "cg-logo-row" }, select, use));
  return { node, get change() { return change; } };
}

// Editar o grupo: o nome e o logotipo numa ficha so; nada e gravado antes de
// Gravar. Renomear leva a pasta, as midias, os jogos instalados e o que vai com
// o nome (o Setup faz tudo e refaz os frontends).
async function cgEditGroup(g) {
  const dlg = cgDialog();
  const name = el("input", { type: "text", value: g.name, maxlength: "255", autocomplete: "off", spellcheck: "false", "aria-label": t("cg_group_name") });
  const logo = cgLogoField(g.logo ? cgGroupLogoUrl(g.name) : "");
  const save = el("button", { type: "submit", class: "btn" }, icon("px-save"), t("cg_save"));
  const cancel = el("button", { type: "button", class: "btn ghost" }, t("cg_cancel"));
  cancel.addEventListener("click", () => dlg.close());
  const form = el("form", { class: "cg-form", method: "dialog" }, el("h3", {}, t("cg_group_edit_title").replace("%s", g.name)),
    el("label", { class: "cg-field" }, el("span", {}, t("cg_group_name")), name, el("small", { class: "dim" }, t("cg_rename_note"))),
    logo.node,
    el("footer", {}, cancel, save));
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const fresh = name.value.trim();
    if (!fresh) { name.focus(); return; }
    if (/[/|]/.test(fresh) || fresh.startsWith(".")) { toast(t("cg_rename_bad"), "bad"); return; }
    save.disabled = true;
    try {
      let target = g.name;
      if (fresh !== g.name) {
        const res = await api("/api/customgames/group-rename", { method: "POST", body: JSON.stringify({ name: g.name, new_name: fresh }) });
        if (!res.ok) { toast((await res.json().catch(() => ({}))).error || res.statusText, "bad"); return; }
        target = fresh;
        if (cg.installGroup === g.name) cg.installGroup = fresh;
        const view = cgView();
        if (view.group === g.name) { view.group = fresh; cgViewSave(); }
        toast(t("cg_renamed").replace("%s", g.name).replace("%s", fresh));
      }
      const change = logo.change;
      if (change !== undefined) {
        const body = { name: target };
        if (change && change.logo) body.logo = change.logo;
        else if (change && change.system) body.system = change.system;
        const res = await api("/api/customgames/group-logo", { method: "POST", body: JSON.stringify(body) });
        if (!res.ok) { toast((await res.json().catch(() => ({}))).error || res.statusText, "bad"); }
        cgLogoStamp = Date.now();
      }
      dlg.close();
      cgLoad().catch(() => {});
    } finally {
      save.disabled = false;
    }
  });
  dlg.replaceChildren(form);
  dlg.showModal();
  name.focus();
  name.select();
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
      text: t("cg_gdel_all_ask").replace("%s", what) + (packages ? " " + t("cg_gdel_pkg_note").replace("%s", cgPackagesWhere()) : ""),
      yes: t("cg_gdel_all"), no: t("cg_gdel_keep"), danger: true });
  }
  const task = await cgTask("/api/customgames/group-delete", { name, all });
  if (task && task.rc === 0) {
    if (cg.installGroup === name) cg.installGroup = "";
    toast(t("cg_deleted").replace("%s", name), "ok");
  }
}

// ── O cartao de um jogo instalado ──
// O cartao completo (cgCard: imagem e video ao passar o mouse, logotipo, tipo,
// modo, controles, ano e desenvolvedora, categoria, o texto, .key e .ppdb) e, no rodape, o
// botao Jogar e os icones de editar, baixar o pacote e o menu (instalar de novo,
// apagar o pacote, apagar o jogo).

// O pacote da pasta deles que e deste jogo (o que ele foi instalado, ou o que o
// Baixar fez), ou null.
const cgPackageOf = (game) => (cg.packages || []).find((p) => p.group === game.group && p.name === game.name &&
  (p.state === "installed" || p.state === "update")) || null;

function cgGameCard(game) {
  const system = "custom/" + game.group;
  const media = game.media || [];
  const url = (kind) => mediaUrl(system, game.name, kind);
  const pkg = cgPackageOf(game);
  const tag = pkg && pkg.state === "update" ? { cls: "warn", text: t("cg_newer_pkg") } : null;
  const card = cgCard({ name: game.name, platform: game.platform, mode: game.mode, category: game.category, controls: game.controls,
    year: game.year, developer: game.developer, buttons: game.buttons, players: game.players, snap: url("snap"),
    logo: media.includes("logo") ? url("logo") : "", video: media.includes("preview") ? url("preview") : "",
    text: media.includes("texto") ? url("texto") : "", key: game.key, ppdb: game.ppdb, tag, size: pkg ? pkg.size : 0,
    sizeLabel: "cg_pkg_size" }, cgGameActions(game, pkg));
  card.dataset.key = game.group + "/" + game.name;
  return card;
}

// Um botao so de icone do rodape do cartao (o nome no balao e no aria-label).
function cgIconButton(glyph, label, fn, cls) {
  const b = el("button", { type: "button", class: "icon-btn small cg-ibtn" + (cls ? " " + cls : ""), title: label, "aria-label": label }, icon(glyph));
  b.addEventListener("click", (ev) => { ev.stopPropagation(); fn(); });
  return b;
}

function cgGameActions(game, pkg) {
  const kind = game.platform;
  const packed = kind === "windows" || kind === "native";
  const play = el("button", { type: "button", class: "btn small cg-main" }, icon("g-play"), t("cg_play"));
  play.addEventListener("click", () => cgPlay(game));
  const out = [play];
  if (kind !== "script") out.push(cgIconButton("px-edit", t("cg_edit") + ": " + game.name, () => cgEditGame(game).catch(() => {})));
  if (packed) out.push(cgIconButton("g-download", t("cg_download_pkg") + ": " + game.name, () => cgDownloadGame(game).catch(() => {})));
  const items = [];
  if (packed) items.push(["g-refresh", t("cg_repack"), () => cgDownloadGame(game, true)]);
  if (pkg) {
    items.push(["px-install", t("cg_install_again"), () => cgReinstall(game, pkg)]);
    items.push(["g-trash", t("cg_pkg_delete"), () => cgDeletePackage(pkg)]);
  }
  items.push(["px-remove", t("cg_delete_game"), () => cgDelete(game), true]);
  const more = cgIconButton("g-more", t("cg_more"), () => cgMenu(more, items), "cg-more-btn");
  more.setAttribute("aria-haspopup", "menu");
  out.push(more);
  return out;
}

// O menu de um botao: uma lista solta sobre a pagina (o cartao corta o que sai
// dele), fechada ao clicar fora, no Esc ou ao rolar.
function cgMenu(anchor, items) {
  document.querySelectorAll(".cg-menu").forEach((n) => n.remove());
  const close = () => {
    menu.remove();
    document.removeEventListener("pointerdown", outside, true);
    document.removeEventListener("keydown", esc, true);
    window.removeEventListener("scroll", close, true);
    window.removeEventListener("resize", close);
  };
  const outside = (ev) => { if (!menu.contains(ev.target) && !anchor.contains(ev.target)) close(); };
  const esc = (ev) => { if (ev.key === "Escape") { close(); anchor.focus(); } };
  const menu = el("div", { class: "cg-menu", role: "menu" }, ...items.map(([glyph, label, fn, danger]) => {
    const b = el("button", { type: "button", role: "menuitem", class: danger ? "bad" : "" }, icon(glyph), el("span", {}, label));
    b.addEventListener("click", () => { close(); Promise.resolve(fn()).catch(() => {}); });
    return b;
  }));
  document.body.append(menu);
  const r = anchor.getBoundingClientRect();
  const room = window.innerHeight - r.bottom;
  menu.style.right = Math.max(8, window.innerWidth - r.right) + "px";
  if (room >= menu.offsetHeight + 12 || r.top < menu.offsetHeight + 12) menu.style.top = r.bottom + 6 + "px";
  else menu.style.bottom = window.innerHeight - r.top + 6 + "px";
  document.addEventListener("pointerdown", outside, true);
  document.addEventListener("keydown", esc, true);
  window.addEventListener("scroll", close, true);
  window.addEventListener("resize", close);
  const first = menu.querySelector("button");
  if (first) first.focus({ preventScroll: true });
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

// O pacote do jogo instalado, com o que ele tem agora (as configuracoes que a
// pessoa mudou depois de instalar, o .key do menu na tela, a arte): o Setup o
// refaz se mudou algo (senao o zip que ja esta na pasta serve), e o navegador
// o baixa. force: refaz de qualquer jeito.
async function cgDownloadGame(game, force) {
  // Um zip com o nome do pacote que nao e o deste jogo como foi instalado (um mais novo esperando na pasta, ou o de
  // outro jogo): o Setup so o troca com force, e a pessoa decide antes.
  const pkg = cgPackageOf(game);
  const other = (cg.packages || []).find((p) => p.file === cgZipOf(game.name));
  if (!force && other && (!pkg || pkg.file !== other.file || pkg.state === "update")) {
    if (!(await ask({ title: game.name, text: t("cg_pack_replace_ask").replace("%s", other.file), yes: t("cg_create_replace"), danger: true }))) return;
    force = true;
  }
  const prog = cgProgress(t("cg_packing").replace("%s", game.name));
  prog.set(0, "…");
  const task = await cgTask("/api/customgames/pack", { group: game.group, name: game.name, force: !!force },
    (tk) => prog.set(tk.pct || 0, (tk.step || "") + (tk.pct ? " · " + Math.round(tk.pct) + "%" : "")));
  const ok = !!task && task.rc === 0;
  prog.end(ok, ok ? t("cg_pack_done").replace("%s", game.name) : (task && (task.error || task.last)) || t("task_fail"));
  if (!ok) return;
  const zip = cgZipOf(game.name);
  const link = el("a", { href: cgDownloadUrl(zip), download: zip, hidden: "" });
  document.body.append(link);
  link.click();
  link.remove();
  toast(t("cg_pack_downloading").replace("%s", zip), "ok");
}

// Trocar o jogo pelo que esta no pacote dele (o que se mudou depois de
// instalar se perde).
async function cgReinstall(game, pkg) {
  if (!(await ask({ title: game.name, text: t("cg_reinstall_ask").replace("%s", game.name).replace("%s", pkg.file), yes: t("cg_install_again"),
    danger: true }))) return;
  await cgInstallPackage(pkg, game.group, { replace: true, quiet: true });
}

// ── Editar um jogo instalado ──
// Tudo o que o cfg do jogo diz: o modo, as informacoes, o executavel e o que o abre
// (Windows), o comando (Linux e Comando; o de um comando muda tambem de nome e de grupo),
// o mapa do controle e a arte. As mudancas vao no pacote que a pessoa baixa depois.

async function cgEditGame(game) {
  const row = cgRowFromGame(game);
  const kind = game.platform;
  const dlg = cgDialog();
  // Os arquivos da pasta do jogo (ela montada): o executavel escolhido numa lista.
  if (kind !== "command" && game.folder) {
    try {
      const res = await api("/api/customgames/scan?one=1&path=" + encodeURIComponent(game.folder));
      if (res.ok) {
        const found = await res.json();
        row.exes = found.exes || [];
        row.programs = found.programs || [];
      }
    } catch (e) { /* a pasta nao esta montada: o executavel fica como esta */ }
  }
  if (kind === "windows" && row.exe && !row.exes.includes(row.exe)) row.exes.unshift(row.exe);
  // A arte em cartoes, como no Criar pacote: escolher o arquivo ou capturar a tela do jogo aberto no gabinete.
  const ctl = cgControls(row, { dialog: true, editing: game, runner: kind === "windows", cards: true });
  const fields = kind === "command" ? ["name", "group", "run", "mode", "crop", "category", "year", "developer", "players", "buttons", "controls", "art"]
    : ["run", "mode", "crop", "category", "year", "developer", "players", "buttons", "controls", "keys", "art"];
  if (kind === "command") fields.splice(fields.indexOf("controls") + 1, 0, "keys");
  const keys = el("select", { "aria-label": t("cg_f_keys") },
    el("option", { value: "" }, t(game.key ? "cg_keys_keep_set" : "cg_keys_keep_none")),
    el("option", { value: "clear" }, t("cg_keys_clear")), el("option", { value: "joystick" }, t("cg_keys_joystick")));
  ctl.keys = el("div", { class: "cg-keysel" }, keys, el("small", { class: "dim" }, t("cg_keys_hint")));
  const text = el("textarea", { rows: "3", placeholder: t("cg_ph_text"), "aria-label": t("cg_f_text") });
  const save = el("button", { type: "submit", class: "btn" }, icon("px-save"), t("cg_save"));
  const cancel = el("button", { type: "button", class: "btn ghost" }, t("cg_cancel"));
  cancel.addEventListener("click", () => dlg.close());
  const snap = el("img", { class: "cg-editsnap", alt: "", src: mediaUrl("custom/" + game.group, game.name, "snap") });
  snap.addEventListener("error", () => snap.remove());
  // Prévia e Testar no gabinete, como no Criar pacote: o cartao como o frontend mostra o jogo com o que esta no formulario,
  // e o jogo instalado aberto no gabinete (como esta gravado) com a captura da foto e do video dele para a arte.
  const system = "custom/" + game.group;
  const media = game.media || [];
  const before = { snap: mediaUrl(system, game.name, "snap"), logo: media.includes("logo") ? mediaUrl(system, game.name, "logo") : "",
    video: media.includes("preview") ? mediaUrl(system, game.name, "preview") : "",
    text: media.includes("texto") ? mediaUrl(system, game.name, "texto") : "", key: game.key, ppdb: game.ppdb };
  const previewBox = el("div", { class: "cg-preview", hidden: "" });
  const drawPreview = () => {
    if (previewBox.hidden) return;
    previewBox.replaceChildren(el("h5", {}, t("cg_preview_title")), cgPreviewCard(row, before), el("p", { class: "dim" }, t("cg_preview_note")));
  };
  const preview = el("button", { type: "button", class: "btn ghost", "aria-pressed": "false" }, icon("g-grid"), t("cg_preview"));
  preview.addEventListener("click", () => {
    previewBox.hidden = !previewBox.hidden;
    preview.setAttribute("aria-pressed", String(!previewBox.hidden));
    drawPreview();
    if (!previewBox.hidden) previewBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });
  const testStatus = el("div", { class: "cg-create-status", role: "status" });
  const test = el("button", { type: "button", class: "btn ghost" }, icon("g-play"), t("cg_test"));
  const refreshArt = () => {
    const now = form.querySelector(".cg-artcards");
    if (now) now.replaceWith(cgArtCards(row, () => {}));
    drawPreview();
  };
  test.addEventListener("click", () => cgEditTest(game, row, test, testStatus, refreshArt).catch(() => { test.disabled = false; }));
  // Fechar o formulario fecha o jogo que ele abriu (se ainda e o da tela).
  dlg.addEventListener("close", () => { cgEditClose().catch(() => {}); }, { once: true });
  const form = el("form", { class: "cg-form cg-edit" },
    el("header", { class: "cg-edithead" }, snap, el("div", {}, el("h3", {}, t("cg_edit_title").replace("%s", game.name)),
      el("div", { class: "cg-cfacts" }, el("span", { class: "tag" }, t("cg_" + (CG_PLATFORMS.includes(kind) ? kind : "script")).replace(/ \(.*/, "")),
        el("span", { class: "tag" }, game.group)))),
    el("p", { class: "dim cg-editnote" }, t(kind === "command" ? "cg_edit_note_cmd" : "cg_edit_note")),
    el("div", { class: "cg-one" }, ...fields.map((f) => cgField(f, ctl[f])), cgField("text", text)),
    previewBox, testStatus,
    el("footer", {}, preview, test, cancel, save));
  form.addEventListener("change", () => drawPreview());
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    save.disabled = true;
    try {
      const body = { group: game.group, name: game.name, mode: cgRowMode(row), category: row.category, players: row.players,
        buttons: row.buttons, controls: row.controls.join(","), year: row.year.trim(), developer: row.developer.trim(),
        crop169: row.crop ? "1" : "0" };
      if (kind === "command") Object.assign(body, { new_group: row.group, new_name: row.name.trim(), command: row.command });
      if (kind === "native") body.command = row.command;
      if (kind === "windows") Object.assign(body, { exe: row.exe, runner: row.runner === "portproton" ? "" : row.runner });
      if (keys.value) body.keys = keys.value;
      const res = await api("/api/customgames/edit", { method: "POST", body: JSON.stringify(body) });
      if (!res.ok) { toast((await res.json().catch(() => ({}))).error || res.statusText, "bad"); return; }
      const media = {};
      if (row.snap && row.snap.id) media.snap = row.snap.id;
      if (row.video && row.video.id) media.video = row.video.id;
      if (row.text && row.text.id) media.text = row.text.id;
      if (row.logo && row.logo.id) media.logo = row.logo.id;
      if (row.icon && row.icon.id) media.icon = row.icon.id;
      if (text.value.trim()) media.text_string = text.value.trim().replace(/\n/g, "\\n");
      if (Object.keys(media).length) {
        const r = await api("/api/customgames/media", { method: "POST", body: JSON.stringify(Object.assign({
          group: kind === "command" ? row.group : game.group, name: kind === "command" ? row.name.trim() : game.name }, media)) });
        if (!r.ok) toast((await r.json().catch(() => ({}))).error || r.statusText, "bad");
      }
      toast(t("cg_saved").replace("%s", kind === "command" ? row.name : game.name), "ok");
      dlg.close();
      cgLoad().catch(() => {});
    } finally {
      save.disabled = false;
    }
  });
  dlg.replaceChildren(form);
  dlg.showModal();
}

// Editar > Testar no gabinete: o jogo instalado aberto como esta gravado (o mesmo caminho do Jogar). Quando ele aparece na
// tela (o FPS da camada com o app dele), o painel do teste: a foto e os 30 s de video do que o gabinete mostra, que vao para a
// imagem e o video do jogo ao Salvar, e o botao de fechar. Mudancas ainda nao salvas nao valem no teste.
async function cgEditTest(game, row, button, status, redraw) {
  if (!(await ask({ title: t("cg_test"), text: t("cg_edit_test_ask").replace("%s", game.name), yes: t("cg_test") }))) return;
  button.disabled = true;
  try {
    const res = await api("/api/launch", { method: "POST", body: JSON.stringify({ system: "custom/" + game.group, game: game.name }) });
    const out = await res.json().catch(() => ({}));
    if (!res.ok || !out.app) { status.replaceChildren(el("span", { class: "error" }, out.error || res.statusText)); return; }
    cg.editApp = cg.testApp = out.app;
    // Enquanto abre: fechar no gabinete (o jogo pode nao abrir, ou abrir e cair).
    const stopButton = el("button", { type: "button", class: "btn small ghost" }, icon("g-close"), t("cg_test_close"));
    stopButton.addEventListener("click", async () => {
      stopButton.disabled = true;
      await cgEditClose(true);
      status.replaceChildren(el("span", {}, t("cg_test_closed")));
    });
    status.replaceChildren(el("span", {}, t("cg_test_opening").replace("%s", game.name)), " ", stopButton);
    // Ate 2 minutos: um jogo do Windows pode demorar (o PortProton).
    for (let i = 0; i < 60; i++) {
      await sleep(2000);
      if (cg.editApp !== out.app) return;
      const s = await api("/api/status").then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
      if (cg.editApp !== out.app) return;
      if (s.fps && s.fps.program === out.app) {
        status.replaceChildren(cgTestPanel(row, { redraw, close: () => cgEditClose(true), note: "cg_edit_test_note" }));
        return;
      }
    }
    status.replaceChildren(el("span", { class: "error" }, t("cg_test_none").replace("%s", game.name).replace("%s", out.app + ".log")), " ", stopButton);
    stopButton.disabled = false;
  } finally {
    button.disabled = false;
  }
}

// Fecha o jogo que o Editar abriu. Sem force, so se ele ainda e o da tela (quem abriu outro jogo no gabinete nao perde o dele
// ao fechar o formulario).
async function cgEditClose(force) {
  const app = cg.editApp;
  cg.editApp = cg.testApp = "";
  if (!app) return;
  if (!force) {
    const s = await api("/api/status").then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
    if (!s.fps || s.fps.program !== app) return;
  }
  await api("/api/close", { method: "POST", body: "{}" }).catch(() => {});
}

function cgRowFromGame(game) {
  const mode = game.mode || "640x480@60";
  const known = (cg.info.modes || []).find((m) => m.value === mode);
  return cgNewRow({ group: game.group, name: game.name, platform: game.platform, command: game.command, exe: game.exe,
    folder: game.folder, mode: known ? known.label : "other", modeOther: known ? "" : mode, category: game.category,
    players: game.players, buttons: game.buttons, controls: (game.controls || "").split(",").filter(Boolean),
    year: game.year || "", developer: game.developer || "", runner: game.runner || "portproton", crop: !!game.crop });
}

// ── Os pacotes que faltam instalar ──
// Os de ~/roms/custom-packages (o compartilhamento \\fliperos\roms) que ainda
// nao sao um jogo (novos, com o grupo para escolher; o ultimo usado ja
// marcado), os que mudaram desde a instalacao e os que nao servem (com os
// problemas). Um pacote instalado nao aparece aqui: o jogo dele e o cartao,
// que baixa o pacote.

const cgBaseName = (p) => p.zip.split("/").pop();

// O cartao de um pacote por instalar: o do jogo (como no frontend) com o estado,
// os problemas e, no rodape, instalar, baixar o zip e apagar o zip.
function cgPackageCard(p) {
  const media = (kind) => (p.media && p.media[kind] ? "/api/customgames/package-media?zip=" + encodeURIComponent(p.zip) +
    "&member=" + encodeURIComponent(p.media[kind]) : "");
  const actions = [];
  let tag;
  const main = (label, fn, cls) => {
    const b = el("button", { type: "button", class: "btn small cg-main" + (cls ? " " + cls : "") }, ...[].concat(label));
    b.addEventListener("click", () => fn().catch(() => {}));
    return b;
  };
  if (p.state === "bad") {
    const n = (p.problems || []).length;
    tag = { cls: "bad", text: n === 1 ? t("cg_problem_1") : t("cg_problems_n").replace("%n", n) };
    actions.push(main(t("cg_file_delete"), () => cgDeletePackage(p), "ghost bad"));
  } else if (p.state === "update") {
    tag = { cls: "warn", text: t("cg_newer_than").replace("%s", p.group) };
    actions.push(main([icon("px-install"), t("cg_update_in").replace("%s", p.group)], () => cgInstallPackage(p, p.group, { replace: true })));
  } else {
    tag = { cls: "new", text: t("cg_pkg_state_new") };
    const group = cgGroupSelect(cg.installGroup, (value) => { cg.installGroup = value; });
    actions.push(group, main([icon("px-install"), t("cg_install")], () => cgInstallPackage(p, group.value)));
  }
  if (p.state !== "bad") {
    // O zip de um pacote que serve se baixa daqui, para levar a outro FliperOS.
    const zip = el("a", { class: "icon-btn small cg-ibtn", href: cgDownloadUrl(p.file), download: p.file, title: t("cg_download") + ": " + p.file,
      "aria-label": t("cg_download") + ": " + p.file }, icon("g-download"));
    actions.push(zip, cgIconButton("px-remove", t("cg_pkg_delete") + ": " + p.file, () => cgDeletePackage(p).catch(() => {})));
  }
  const card = cgCard({ name: p.name, file: p.file, platform: p.platform, mode: p.mode, category: p.category, controls: p.controls,
    year: p.year, developer: p.developer, buttons: p.buttons, players: p.players, snap: media("snap"), logo: media("logo"), video: media("preview"), text: media("texto"),
    size: p.bytes || p.size, key: p.key, ppdb: p.ppdb, tag, problems: p.state === "bad" ? cgProblems(p) : [] }, actions);
  card.dataset.key = p.zip;
  return card;
}

// cgCard: um jogo como o frontend o mostra: a imagem e, com o cursor (ou um
// toque), o video; o nome correndo quando nao cabe; o tipo, o modo, os
// jogadores, o controle e os botoes em icones; a categoria; o texto rolando
// devagar quando e maior que o espaco. info.text: o endereco do .txt, ou o
// proprio texto em info.textValue. Serve os jogos instalados, os pacotes por
// instalar e a previa do Criar pacote. O rodape (actions) tem o botao
// principal, que cresce, e os botoes de icone (cg-main, cg-ibtn).
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
  const made = [info.year, info.developer].filter(Boolean).join(" ");
  if (made) body.append(el("div", { class: "cg-cmade" }, made));
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
  if (info.size) body.append(el("div", { class: "cg-csize dim" }, info.sizeLabel ? t(info.sizeLabel).replace("%s", bytes(info.size)) : bytes(info.size)));
  card.append(art, body);
  if (actions.length) card.append(el("div", { class: "cg-cact" }, ...actions));
  return card;
}

// Os problemas de um pacote que nao serve, um por linha, traduzidos pelos
// codigos (config/fliperos-customgame); um codigo sem texto aqui mostra o
// motivo em ingles do verificador.
const CG_PROBLEM_CODES = ["not_zip", "unsafe", "encrypted", "misnamed", "cfg_missing", "cfg_many", "cfg_text", "folder_missing",
  "stranger", "strangers_more", "two_files", "name_missing", "name_bad", "platform_missing", "platform_bad", "exe_missing",
  "exe_not_found", "command_missing", "mode_bad", "category_long", "controls_bad", "buttons_bad", "players_bad", "runner_bad",
  "crop169_bad", "year_bad", "developer_long"];

function cgProblems(p) {
  const base = p.name || cgBaseName(p).replace(/\.fliperos-customgame\.zip$|\.zip$/i, "");
  return (p.problems || []).map(({ code, arg, text }) =>
    (CG_PROBLEM_CODES.includes(code) ? t("cg_pb_" + code).split("%s").join(arg).split("%g").join(base) : text || code));
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

// Instala um pacote no grupo; o jogo que ja esta nele pergunta se troca. quiet:
// o "instalar todos" e o instalar de novo ja perguntaram. deleteZip: o zip sai
// depois (sem dizer, vale a caixa do envio).
async function cgInstallPackage(p, group, { replace = false, quiet = false, deleteZip } = {}) {
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
  }
  const prog = cgProgress(t("cg_installing").replace("%s", p.name));
  prog.set(0, "…");
  // O cartao do jogo, quando ele aparecer na lista, pisca.
  cg.highlight = group + "/" + p.name;
  const task = await cgTask("/api/customgames/install", { zip: p.zip, group, replace, portproton: pp },
    (tk) => prog.set(tk.pct || 0, (tk.step || "") + (tk.pct ? " · " + Math.round(tk.pct) + "%" : "")));
  const ok = !!task && task.rc === 0;
  prog.end(ok, ok ? t("cg_installed_ok").replace("%s", p.name) : (task && (task.error || task.last)) || t("task_fail"));
  if (!ok) cg.highlight = "";
  if (ok) {
    cg.installGroup = group;
    if (deleteZip === undefined ? !quiet && !!(cg.el.deleteZip && cg.el.deleteZip.checked) : deleteZip) await cgDeletePackage(p, true);
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
  if (done.length && cg.el.deleteZip && cg.el.deleteZip.checked) for (const p of done) await cgDeletePackage(p, true);
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

// Enviar pacotes (o botao, ou soltar na area): cada zip sobe para a pasta dos
// pacotes e, em seguida, se instala no grupo escolhido (um jogo que ja esta
// instalado com esse pacote se atualiza no grupo dele). Um pacote que nao serve
// fica na lista com os problemas.
async function cgUploadFiles(files) {
  if (!files.length) return;
  if (!cg.installGroup) {
    // Sem nenhum grupo ainda: o primeiro nasce aqui.
    const name = await cgNewGroup();
    if (!name) return;
    cg.installGroup = name;
    cgRenderGames();
  }
  for (const file of files) {
    if (!(await cgUploadZip(file))) continue;
    const res = await api("/api/customgames/packages");
    cg.packages = res.ok ? ((await res.json().catch(() => ({}))).packages || []) : cg.packages;
    const p = cg.packages.find((x) => x.file === file.name);
    if (!p) continue;
    if (p.state === "bad") {
      toast(file.name + ": " + cgProblems(p).join(" "), "bad");
      continue;
    }
    // O mesmo pacote ja instalado (o zip trocado): o jogo e atualizado onde ele esta.
    await cgInstallPackage(p, p.group || cg.installGroup);
  }
  cgLoad().catch(() => {});
}

// Enviar um pacote: so JOGO.fliperos-customgame.zip, para a pasta dos
// pacotes. Outro nome volta com a regra.
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
  cg.highlight = (cg.info.packages_dir || "") + "/" + file.name;
  return true;
}

// O nome do zip de um jogo na pasta dos pacotes (lib/customgames.sh
// customgames_package_out: o que o disco do Windows recusa vira "_").
const cgZipOf = (name) => name.replace(/[^A-Za-z0-9 ._()&+,-]+/g, "_") + CG_SUFFIX;
// O endereco para baixar um pacote da pasta ~/roms/custom-packages (o
// /api/download com a raiz roms).
const cgDownloadUrl = (zip) => "/api/download?root=roms&path=" + encodeURIComponent("custom-packages/" + zip);

// cgDownloadButton: o botao Baixar de um pacote feito, para levar o zip a
// outro FliperOS (a pasta dele, ~/roms/custom-packages).
function cgDownloadButton(zip) {
  return el("a", { class: "btn small", href: cgDownloadUrl(zip), download: zip }, icon("px-install"), t("cg_download"));
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

// ── A aba Criar pacote ──
// Um jogo do Windows ou do Linux numa pasta: o zip vai para
// ~/roms/custom-packages e, feito, pergunta se instala. Um pacote de cada vez
// (com a previa e o teste no gabinete) ou varios de uma vez (a tabela, mais
// abaixo). A pasta com a estrutura do pacote preenche o resto.

const CG_CREATE_FIELDS = ["name", "platform", "folder", "run", "mode", "crop", "category", "year", "developer", "players", "buttons", "controls", "joystick", "art"];

// Um pacote ou varios de uma vez: o seletor em duas pilulas; a escolha fica no navegador.
function cgCreateMode(mode) {
  cg.createMode = CG_CREATE_MODES.includes(mode) ? mode : "one";
  try { localStorage.setItem(CG_CREATE_MODE, cg.createMode); } catch (e) { /* sem armazenamento */ }
  const draft = cg.rows.length;
  cg.el.modeBar.replaceChildren(...CG_CREATE_MODES.map((m) => {
    const label = m === "many" && draft ? t("cg_mode_many") + " (" + draft + ")" : t("cg_mode_" + m);
    const b = el("button", { type: "button", role: "tab", class: "cg-mode-btn" + (cg.createMode === m ? " on" : ""), "aria-selected": String(cg.createMode === m) },
      icon(m === "one" ? "px-install" : "g-list"), label);
    b.addEventListener("click", () => cgCreateMode(m));
    return b;
  }));
  cg.el.one.hidden = cg.createMode !== "one";
  cg.el.many.hidden = cg.createMode !== "many";
}

function cgRenderCreate() {
  const box = cg.el.create;
  if (!cg.createRow) cg.createRow = cgNewRow({ platform: "windows" });
  if (!box.dataset.built) {
    box.dataset.built = "1";
    cg.el.structure = cgStructure();
    cg.el.createForm = el("div", { class: "cg-one cg-create" });
    cg.el.createStatus = el("div", { class: "cg-status", role: "status" });
    cg.el.createIntro = el("p", { class: "dim cg-folder" });
    cg.el.modeBar = el("div", { class: "cg-modebar", role: "tablist" });
    cg.el.one = el("div", { class: "cg-create-one" });
    cg.el.many = el("div", { class: "cg-create-many" });
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
    cg.el.one.append(el("div", { class: "cg-create-wrap" }, cg.el.createForm, cg.el.createPreview),
      cg.el.createStatus, el("div", { class: "cg-create-foot" }, clear, preview, test, go));
    box.append(cg.el.createIntro, cg.el.structure, cg.el.modeBar, cg.el.one, cg.el.many);
    // Sem jogo nem pacote nenhum, a estrutura ja aberta.
    cg.el.structure.open = !(cg.info.games || []).length && !(cg.info.pending || []).length;
  }
  cg.el.createIntro.textContent = t("cg_create_intro").replace("%s", cgPackagesWhere());
  cgCreateMode(cg.createMode);
  cgCreateDraw();
  cgRenderMany();
}

function cgCreateDraw() {
  const row = cg.createRow;
  if (row.platform === "command") row.platform = "windows";
  const ctl = cgControls(row, { redraw: cgCreateDraw, package: true, cards: true });
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
  box.replaceChildren(el("h5", {}, t("cg_preview_title")), cgPreviewCard(cg.createRow), el("p", { class: "dim" }, t("cg_preview_note")));
}

// O cartao da previa de uma linha: o que ela tem agora (a arte nova, ou a de antes em fallback, que o Editar passa), como o
// frontend mostraria. fallback: {snap, logo, video, text} do jogo instalado; key: o jogo tem .key.
function cgPreviewCard(row, fallback = {}) {
  const modeLabel = row.mode === "other" ? row.modeOther : row.mode;
  const mode = (((cg.info && cg.info.modes) || []).find((m) => m.label === modeLabel) || { value: modeLabel }).value;
  return cgCard({ name: row.name.trim() || t("cg_ph_name"), platform: row.platform, mode, category: row.category,
    year: row.year.trim(), developer: row.developer.trim(), controls: row.controls.join(","), buttons: row.buttons, players: row.players,
    snap: row.snap ? row.snap.url || "" : fallback.snap || "", logo: row.logo ? row.logo.url || "" : fallback.logo || "",
    video: row.video ? row.video.url || "" : fallback.video || "",
    text: row.text && !row.text.value ? row.text.url || "" : row.text ? "" : fallback.text || "", textValue: row.text ? row.text.value || "" : "",
    key: !!row.key || !!row.joystick || !!fallback.key, ppdb: !!row.ppdb && row.platform === "windows" || !!fallback.ppdb,
    tag: { cls: "new", text: t("cg_preview") } });
}

// Fechar no gabinete: o jogo do teste (abrindo ou aberto) e o X dele fecham.
async function cgTestClose() {
  cg.testApp = "";
  await api("/api/customgames/test-close", { method: "POST", body: "{}" }).catch(() => {});
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
    // Enquanto abre: o botao de fechar no gabinete (o jogo pode nao abrir, ou abrir e cair).
    const stopButton = el("button", { type: "button", class: "btn small ghost" }, icon("g-close"), t("cg_test_close"));
    let cancelled = false;
    stopButton.addEventListener("click", async () => {
      cancelled = true;
      stopButton.disabled = true;
      await cgTestClose();
      status.replaceChildren(el("span", {}, t("cg_test_closed")));
    });
    status.replaceChildren(el("span", {}, t("cg_test_opening").replace("%s", row.name)), " ", stopButton);
    cg.testApp = out.app;
    // Ate 2 minutos: um jogo do Windows pode demorar (o PortProton). Para antes se o jogo abriu e
    // fechou (o fim do log dele vai na tela), e mostra o painel do teste se ele roda ha um tempo
    // sem aparecer no FPS (um programa sem OpenGL).
    let running = 0;
    for (let i = 0; i < 60; i++) {
      await sleep(2000);
      if (cancelled) return;
      const s = await api("/api/status").then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
      const st = await api("/api/customgames/test-state?app=" + encodeURIComponent(out.app)).then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
      if (cancelled) return;
      if ((s.fps && s.fps.program === out.app) || (st.state === "running" && ++running >= 8)) {
        status.replaceChildren(cgTestPanel(row));
        return;
      }
      if (st.state === "ended") {
        cg.testApp = "";
        status.replaceChildren(el("span", { class: "error" }, t("cg_test_ended").replace("%s", row.name).replace("%s", st.log || out.app + ".log")),
          (st.tail || []).length ? el("pre", { class: "cg-testlog" }, st.tail.join("\n")) : "");
        return;
      }
    }
    status.replaceChildren(el("span", { class: "error" }, t("cg_test_none").replace("%s", row.name).replace("%s", out.app)), " ", stopButton);
    stopButton.disabled = false;
  } finally {
    cg.busy = false;
    button.disabled = false;
  }
}

// Captura a tela do gabinete (a foto, ou 30 segundos de video a 60 quadros e com som) para a imagem
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
    say(t(kind === "snap" ? "cg_cap_photo_ok" : data.sound ? "cg_cap_video_ok" : "cg_cap_video_nosound"));
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
    card("logo", ".png,.jpg,.jpeg,.webp", "logo", "g-star", false), card("icon", ".png,.jpg,.jpeg,.webp,.ico", "icon", "g-home", false),
    card("text", ".txt", "text", "g-list", false));
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
// a foto e 30 segundos de video, que vao para a imagem e o video do pacote.
// opts (o Editar de um jogo instalado): redraw() desenha a arte de novo depois de uma captura, close() fecha o
// jogo, note e a chave do texto no lugar do aviso das teclas do Criar pacote.
function cgTestPanel(row, opts = {}) {
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
      (opts.redraw || cgCreateDraw)();
    } finally {
      busy(false);
    }
  };
  photo.addEventListener("click", () => capture("snap").catch(() => busy(false)));
  video.addEventListener("click", () => capture("video").catch(() => busy(false)));
  close.addEventListener("click", async () => {
    await (opts.close || cgTestClose)();
    msg.textContent = "";
  });
  return el("div", { class: "cg-testbar" },
    el("div", { class: "cg-testhead" }, icon("g-check"), el("b", {}, t("cg_test_open").replace("%s", row.name))),
    el("p", { class: "cg-testnote" }, t(opts.note || "cg_test_keys")),
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
    const task = await cgTask("/api/customgames/create", { row: payload, replace }, (tk) => {
      bar.firstChild.style.width = (tk.pct || 0) + "%";
      if (tk.step) step.textContent = tk.step;
    });
    if (task && task.rc === 0) {
      // O pacote pronto: o link para baixar o zip, e a pergunta se instala agora;
      // a tela de criar volta limpa.
      const made = { name: row.name.trim(), platform: row.platform, file: zip };
      cg.createRow = cgNewRow({ platform: "windows" });
      cgCreateDraw();
      status.replaceChildren(el("span", { class: "ok" }, t("cg_created_dl").replace("%s", zip)), " ", cgDownloadButton(zip));
      toast(t("cg_created").replace("%s", zip), "ok");
      await cgLoad();
      await cgOfferInstall([made]);
    } else {
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

// ── Criar varios pacotes de uma vez ──
// A tabela: uma linha por jogo (o nome, o tipo, a pasta, o executavel ou
// comando e o modo), e os detalhes de cada uma (a categoria, o ano, a
// desenvolvedora, jogadores, botoes, controles, o joystick e a arte) abertos por
// um botao. Importar de uma pasta (uma linha por subpasta, com a arte, o .key
// e o .ppdb que vieram com ela), colar de uma planilha, duplicar e aplicar um
// campo a todas as linhas. Conferir mostra o que falta em cada linha; criar
// faz um zip por linha em ~/roms/custom-packages, com o resultado de cada uma,
// e pergunta se instala.

function cgBuildMany() {
  const box = cg.el.many;
  const add = el("button", { type: "button", class: "btn ghost small" }, icon("g-plus"), t("cg_rows"));
  add.addEventListener("click", () => { cg.rows.push(cgNewRow({ open: true })); cgTableDraw(true); });
  const importBtn = el("button", { type: "button", class: "btn ghost small" }, icon("px-addfolder"), t("cg_import"));
  importBtn.addEventListener("click", () => cgImport().catch(() => {}));
  const pasteBtn = el("button", { type: "button", class: "btn ghost small" }, icon("g-list"), t("cg_paste"));
  pasteBtn.addEventListener("click", cgPasteDialog);
  const applyBtn = el("button", { type: "button", class: "btn ghost small" }, icon("g-copy"), t("cg_apply_all"));
  applyBtn.addEventListener("click", cgApplyAll);
  const clear = el("button", { type: "button", class: "btn-text quiet" }, t("cg_clear"));
  clear.addEventListener("click", async () => {
    if (cg.rows.length && (await ask({ title: t("cg_clear"), text: t("cg_clear_ask"), yes: t("cg_clear"), danger: true }))) {
      cg.rows = [];
      cgTableDraw();
    }
  });
  const open = el("button", { type: "button", class: "btn-text quiet" }, t("cg_open_all"));
  open.addEventListener("click", () => {
    const all = cg.rows.some((r) => !r.open);
    cg.rows.forEach((r) => { r.open = all; });
    cgTableDraw();
  });
  cg.el.manyCheck = el("button", { type: "button", class: "btn ghost" }, t("cg_check"));
  cg.el.manyCheck.addEventListener("click", () => cgCheckMany().catch(() => {}));
  cg.el.manyGo = el("button", { type: "button", class: "btn" }, icon("px-add"), t("cg_create_many"));
  cg.el.manyGo.addEventListener("click", () => cgCreateMany().catch(() => {}));
  cg.el.table = el("table", { class: "cg-table cg-many" });
  cg.el.manyStatus = el("div", { class: "cg-status", role: "status" });
  box.replaceChildren(el("p", { class: "dim cg-folder" }, t("cg_many_note").replace("%s", cgPackagesWhere())),
    el("div", { class: "cg-toolbar" }, add, importBtn, pasteBtn, applyBtn, el("span", { class: "cg-tbend" }, open, clear)),
    el("div", { class: "cg-many-box" }, el("div", { class: "cg-table-wrap" }, cg.el.table)), cg.el.manyStatus,
    el("div", { class: "cg-foot" }, el("span", { class: "dim" }, t("cg_draft")), el("span", { class: "grow" }), cg.el.manyCheck, cg.el.manyGo));
  // Colar no meio da tabela: as linhas da planilha a partir dessa.
  cg.el.table.addEventListener("paste", (ev) => {
    const text = (ev.clipboardData || window.clipboardData).getData("text");
    if (!/[\t\n]/.test(text.trim())) return;
    ev.preventDefault();
    cgPaste(text);
  });
  box.dataset.built = "1";
}

function cgRenderMany() {
  if (!cg.el.many.dataset.built) cgBuildMany();
  cgTableDraw();
}

// A conta de linhas e o botao de criar.
function cgManyButtons() {
  const n = cg.rows.length;
  cg.el.manyGo.replaceChildren(icon("px-add"), t(n === 1 ? "cg_create_many_1" : "cg_create_many").replace("%n", n));
  cg.el.manyGo.disabled = !n || cg.manyBusy;
  cg.el.manyCheck.disabled = !n || cg.manyBusy;
  cgCreateMode(cg.createMode);
}

function cgTableDraw(focusLast) {
  const table = cg.el.table;
  if (!table) return;
  const head = el("tr", {}, el("th", { class: "num" }, "#"), ...CG_COLUMNS.map((c) => el("th", { scope: "col" }, t(c === "run" ? "cg_f_run" : "cg_f_" + c))), el("th", {}));
  const body = cg.rows.length ? cg.rows.flatMap((row, i) => cgTableRow(row, i)) : [el("tr", { class: "cg-none" },
    el("td", { colspan: String(CG_COLUMNS.length + 2), class: "dim" }, t("cg_rows_none")))];
  table.replaceChildren(el("thead", {}, head), el("tbody", {}, ...body));
  cgManyButtons();
  cgDraftSave();
  if (focusLast) {
    const last = [...table.querySelectorAll("tbody tr.cg-row")].pop();
    const input = last && last.querySelector("input[type=text]");
    if (input) input.focus();
  }
}

// Quantos campos dos detalhes a linha tem preenchidos (o numero no botao).
function cgDetailsFilled(row) {
  return [row.crop ? "x" : "", row.category, row.year.trim(), row.developer.trim(), row.players, row.buttons, row.controls.length ? "x" : "",
    row.joystick ? "x" : "", row.snap, row.video, row.text, row.logo, row.icon].filter(Boolean).length;
}

// A linha da tabela, e logo abaixo os detalhes dela quando abertos.
function cgTableRow(row, index) {
  const redraw = () => { cgTableDraw(); };
  const ctl = cgControls(row, { redraw, package: true });
  const toggle = el("button", { type: "button", class: "icon-btn small cg-detbtn" + (row.open ? " on" : ""), "aria-expanded": String(!!row.open),
    title: t("cg_details"), "aria-label": t("cg_details") + ": " + (row.name || index + 1) }, icon("g-chevd"));
  const filled = cgDetailsFilled(row);
  if (filled) toggle.append(el("i", { class: "cg-detcount" }, String(filled)));
  toggle.addEventListener("click", () => { row.open = !row.open; cgTableDraw(); });
  const dup = el("button", { type: "button", class: "icon-btn small", title: t("cg_dup"), "aria-label": t("cg_dup") }, icon("g-copy"));
  dup.addEventListener("click", () => {
    const copy = cgNewRow(Object.assign({}, row, { id: undefined, name: "", snap: null, video: null, text: null, logo: null, icon: null, errors: {}, state: "",
      error: "", controls: row.controls.slice(), exes: row.exes.slice(), programs: row.programs.slice() }));
    copy.id = ++cg.seq;
    cg.rows.splice(index + 1, 0, copy);
    cgTableDraw();
  });
  const del = el("button", { type: "button", class: "icon-btn small", title: t("cg_remove"), "aria-label": t("cg_remove") }, icon("g-trash"));
  del.addEventListener("click", () => { cg.rows.splice(index, 1); cgTableDraw(); });
  const detailErrors = CG_DETAILS.some((c) => cgFieldError(row, c));
  const state = row.state === "ok" ? el("span", { class: "tag on" }, t("cg_row_ok"))
    : row.state === "working" ? el("span", { class: "tag" }, t("cg_row_working"))
      : row.error ? el("span", { class: "cg-err" }, row.error) : detailErrors && !row.open ? el("span", { class: "cg-err" }, t("cg_row_details_bad")) : "";
  const main = el("tr", { class: "cg-row" + (row.state ? " " + row.state : "") + (Object.keys(row.errors).length ? " bad" : "") },
    el("td", { class: "num" }, String(index + 1)),
    ...CG_COLUMNS.map((c) => {
      const td = el("td", { "data-label": t(c === "run" ? "cg_f_run" : "cg_f_" + c), class: "c-" + c });
      td.append(ctl[c]);
      const err = cgFieldError(row, c);
      if (err) {
        td.classList.add("bad");
        td.append(el("small", { class: "cg-err" }, err));
      }
      return td;
    }),
    el("td", { class: "c-act" }, toggle, dup, del, state));
  const rows = [main];
  if (row.open) {
    rows.push(el("tr", { class: "cg-detail" }, el("td", {}), el("td", { colspan: String(CG_COLUMNS.length + 1) },
      el("div", { class: "cg-one cg-detailgrid" }, ...CG_DETAILS.map((f) => {
        const field = cgField(f, ctl[f]);
        const err = cgFieldError(row, f);
        if (err) {
          field.classList.add("bad");
          field.append(el("small", { class: "cg-err" }, err));
        }
        return field;
      })))));
  }
  return rows;
}

// O erro do Setup cai na coluna dela (exe e command sao a mesma coluna).
function cgFieldError(row, column) {
  const map = { run: ["exe", "command"], art: ["snap", "logo", "icon", "video", "text", "key", "ppdb"], name: ["name"], platform: ["platform"],
    folder: ["folder"], mode: ["mode"], category: ["category"], year: ["year"], developer: ["developer"], players: ["players"],
    buttons: ["buttons"], controls: ["controls"] };
  return (map[column] || []).map((f) => row.errors[f]).filter(Boolean).join(" ");
}

// Aplicar a todas as linhas: um campo com o valor escolhido aqui (o modo, o
// runner, a categoria, o ano, a desenvolvedora, jogadores, botoes, controles, o
// joystick).
function cgApplyAll() {
  if (!cg.rows.length) { toast(t("cg_rows_none"), "bad"); return; }
  const dlg = cgDialog();
  const fields = ["mode", "crop", "runner", "category", "year", "developer", "players", "buttons", "controls", "joystick"];
  const tmp = cgNewRow({ platform: "windows" });
  const pick = el("select", { "aria-label": t("cg_apply_field") }, ...fields.map((f) => el("option", { value: f }, t("cg_f_" + f))));
  const holder = el("div", { class: "cg-apply-value" });
  const draw = () => {
    const ctl = cgControls(tmp, { redraw: draw, package: true });
    if (pick.value === "runner") {
      const runner = el("select", { "aria-label": t("cg_f_runner") }, ...[["portproton", t("cg_runner_portproton")], ["wine", t("cg_runner_wine")],
        ["wine-staging", t("cg_runner_staging")]].map(([v, label]) => el("option", { value: v }, label)));
      runner.value = tmp.runner;
      runner.addEventListener("change", () => { tmp.runner = runner.value; });
      holder.replaceChildren(runner, el("small", { class: "dim" }, t("cg_apply_runner_note")));
    } else holder.replaceChildren(ctl[pick.value]);
  };
  pick.addEventListener("change", draw);
  draw();
  const go = el("button", { type: "submit", class: "btn" }, icon("px-ok"), t("cg_apply_go").replace("%n", cg.rows.length));
  const cancel = el("button", { type: "button", class: "btn ghost" }, t("cg_cancel"));
  cancel.addEventListener("click", () => dlg.close());
  const form = el("form", { class: "cg-form", method: "dialog" }, el("h3", {}, t("cg_apply_all")), el("p", { class: "dim" }, t("cg_apply_note")),
    el("label", { class: "cg-field" }, el("span", {}, t("cg_apply_field")), pick), el("div", { class: "cg-field" }, el("span", {}, t("cg_apply_value")), holder),
    el("footer", {}, cancel, go));
  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const f = pick.value;
    for (const r of cg.rows) {
      r.errors = {}; r.state = ""; r.error = "";
      if (f === "mode") { r.mode = tmp.mode; r.modeOther = tmp.modeOther; }
      else if (f === "controls") r.controls = tmp.controls.slice();
      else if (f === "runner") { if (r.platform === "windows") r.runner = tmp.runner; }
      else if (f === "year" || f === "developer") r[f] = tmp[f];
      else r[f] = tmp[f];
    }
    dlg.close();
    cgTableDraw();
    toast(t("cg_applied").replace("%n", cg.rows.length), "ok");
  });
  dlg.replaceChildren(form);
  dlg.showModal();
}

// ── A tabela ──

function cgNewRow(values) {
  return Object.assign({ id: ++cg.seq, group: "", name: "", platform: "windows", folder: "", exe: "", command: "", mode: "480i",
    modeOther: "", crop: false, category: "", year: "", developer: "", players: "", buttons: "", controls: [], joystick: false, snap: null, video: null, text: null, logo: null, icon: null, key: null, ppdb: null,
    wine: "", runner: "portproton", exes: [], programs: [], errors: {}, state: "", error: "", open: false }, values || {});
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
  for (const key of ["snap", "video", "text", "logo", "icon"]) {
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
  if (cfg.crop169 === "1") row.crop = true;
  if (cfg.category && !row.category) row.category = cfg.category;
  if (cfg.year && !row.year) row.year = cfg.year;
  if (cfg.developer && !row.developer) row.developer = cfg.developer;
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
  return [["snap", "cg_f_snap"], ["logo", "cg_f_logo"], ["icon", "cg_f_icon"], ["video", "cg_f_video"], ["text", "cg_f_text"], ["key", "cg_f_key"], ["ppdb", "cg_f_ppdb"]]
    .filter(([k]) => row[k] && row[k].path).map(([, label]) => t(label).toLowerCase());
}

function cgDraftLoad() {
  try {
    const saved = JSON.parse(localStorage.getItem(CG_DRAFT) || "null");
    if (saved && Array.isArray(saved.rows)) {
      // Um pacote e do Windows ou do Linux: as linhas de um rascunho de antes, de um comando, ficam de fora.
      cg.rows = saved.rows.filter((r) => r.platform !== "command")
        .map((r) => cgNewRow(Object.assign({}, r, { id: undefined, group: "", state: "", error: "", errors: {} })));
      cg.rows.forEach((r) => {
        r.id = ++cg.seq;
        // Os enderecos do navegador (blob:) nao voltam: a arte da pasta, sim.
        for (const k of ["snap", "video", "text", "logo", "icon"]) {
          if (r[k]) r[k].url = r[k].path ? cgArtUrl(r[k].path, k === "snap" ? "" : k) : r[k].id && k !== "text" ? cgStagedUrl(r[k].id) : "";
        }
      });
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
    if (rows.length) localStorage.setItem(CG_DRAFT, JSON.stringify({ rows }));
    else localStorage.removeItem(CG_DRAFT);
  } catch (e) { /* sem armazenamento */ }
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
    // O grupo novo nasce na hora (a pasta dele) e entra na escolha.
    const name = await cgNewGroup();
    if (name) {
      onChange(name);
      fill(name);
    } else fill(value);
  });
  return select;
}

// cgControls: os campos de uma linha (na tabela, na ficha de um jogo ou no Criar
// pacote). Mudar o tipo ou a pasta redesenha (o executavel depende deles).
// package: a linha e de um pacote (so Windows ou Linux, com o joystick); cards:
// a arte em cartoes com a bandeja de captura (o Criar pacote de um jogo e o Editar);
// editing: um jogo instalado (o tipo nao muda); runner: o que o abre aparece
// mesmo editando.
function cgControls(row, { redraw, editing, package: pkg, cards, runner } = {}) {
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
    // Staging; o executavel e o runner de um jogo instalado tambem se editam.
    if (!editing || runner) {
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
  // O ano e a desenvolvedora: o frontend os mostra ao lado do nome do jogo.
  out.year = text("year", "1993", "cg-year");
  out.year.setAttribute("inputmode", "numeric");
  out.year.setAttribute("maxlength", "4");
  out.developer = text("developer", t("cg_ph_developer"));
  out.developer.setAttribute("maxlength", "80");
  out.players = select("players", [["", t("cg_any")], ...[1, 2, 3, 4, 5, 6, 7, 8].map((n) => [String(n), String(n)])], false);
  out.buttons = select("buttons", [["", t("cg_any")], ...[0, 1, 2, 3, 4, 5, 6, 7, 8].map((n) => [String(n), String(n)])], false);
  out.controls = cgControlsButton(row, changed);
  // O 16:9 crop (crop169=1 no cfg): o jogo ve uma tela 16:9 e o tubo mostra o meio dela em 4:3. A caixa traz a
  // explicacao; vale ao criar o pacote, ao editar um jogo instalado e pela OSD (Video configuration).
  {
    const box = el("input", { type: "checkbox", "aria-label": t("cg_f_crop") });
    box.checked = !!row.crop;
    box.addEventListener("change", () => { row.crop = box.checked; changed(false); });
    out.crop = el("div", { class: "cg-joystick cg-crop" }, box, el("small", { class: "dim" }, t("cg_crop_hint")));
  }
  // O jogo ja aceita o joystick (um pacote a criar): o pacote leva um .key vazio, sem mapa do controle para o
  // teclado, e o menu na tela nao abre pedindo um (vale no lugar do .key que veio com a pasta).
  if (pkg) {
    const box = el("input", { type: "checkbox", "aria-label": t("cg_f_joystick") });
    box.checked = !!row.joystick;
    box.addEventListener("change", () => { row.joystick = box.checked; changed(false); });
    out.joystick = el("div", { class: "cg-joystick" }, box, el("small", { class: "dim" }, t("cg_joystick_hint")));
  }
  out.art = cards ? cgArtCards(row, changed) : cgArt(row, changed);
  return out;
}

// O icone de cada tipo de controle, os mesmos do cartao e do frontend: o direcional em setas
// (8, 4 ou 2 direcoes; o duplo, dois), a mira da pistola, o teclado e os eixos (trackball, dial,
// pedal...). Sem um proprio, os eixos.
const CG_CONTROL_GLYPH = { lightgun: "px-guncon", keyboard: "px-keyboard", mahjong: "px-buttons", analog: "px-joysticks" };
const CG_CONTROL_WAYS = { joy8: 8, joy4: 4, joy2: 2 };

function cgControlGlyph(value) {
  const ways = CG_CONTROL_WAYS[value];
  if (ways) return arrowPad(ways);
  if (value === "twin") return el("span", { class: "cg-twin" }, arrowPad(8), arrowPad(8));
  return icon(CG_CONTROL_GLYPH[value] || "px-axes", "cg-ctlglyph");
}

// Os controles: um botao com os escolhidos (o icone e o nome de cada um); abre os 13 em botoes
// com o icone de cada um.
function cgControlsButton(row, changed) {
  const labels = Object.fromEntries(((cg.info && cg.info.controls) || []).map((c) => [c.value, c.label]));
  const button = el("button", { type: "button", class: "cg-ctl" });
  const show = () => {
    if (!row.controls.length) { button.replaceChildren(t("cg_controls_none")); return; }
    button.replaceChildren(el("span", { class: "cg-ctlicons" }, ...row.controls.map((c) => cgControlGlyph(c))),
      el("span", { class: "cg-ctltext" }, row.controls.join(", ")));
  };
  show();
  button.addEventListener("click", () => {
    const pop = el("dialog", { class: "ask cg-pop" });
    const chips = el("div", { class: "chips cg-ctlchips" }, ...Object.entries(labels).map(([value, label]) => {
      const b = el("button", { type: "button", "aria-pressed": String(row.controls.includes(value)) }, cgControlGlyph(value), label);
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
    slot("icon", ".png,.jpg,.jpeg,.webp,.ico", "icon", "g-home"),
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
    const row = cgNewRow({ name: g.name, platform: g.platform || "windows", folder: g.path, exe: g.exe,
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
    placeholder: "Metal Slug X\tWindows\t/media/fliperos/USB/Metal Slug X\tMSX.exe\t240p\tPlatform / Shooter Scrolling\t2\t3\tjoy8" });
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
  // Um pacote e do Windows ou do Linux.
  const platformOf = (s) => {
    const v = (s || "").toLowerCase();
    if (/^w|exe/.test(v)) return "windows";
    if (/^l|nat/.test(v)) return "native";
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
    if (!platform) platform = /\.(exe|bat)$/i.test(v.run || "") ? "windows" : v.folder && !(v.run || "").startsWith("./") ? "windows" : "native";
    const row = cgNewRow({ name: v.name || "", platform, folder: v.folder || "",
      category: v.category || "", year: /^(19|20)\d\d$/.test((v.year || "").trim()) ? v.year.trim() : "",
      developer: (v.developer || "").trim().slice(0, 80), players: /^[1-8]$/.test(v.players || "") ? v.players : "",
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

// ── Conferir e criar ──

const cgRowMode = (row) => (row.mode === "other" ? row.modeOther.trim() : row.mode);

function cgPayload(row) {
  return { group: row.group, name: row.name.trim(), platform: row.platform, folder: row.platform === "command" ? "" : row.folder.trim(),
    exe: row.platform === "windows" ? row.exe : "", command: row.platform === "windows" ? "" : row.command, mode: cgRowMode(row),
    category: row.category, controls: row.controls.join(","), buttons: row.buttons, players: row.players,
    year: row.year.trim(), developer: row.developer.trim(),
    snap: cgArtRef(row.snap), video: cgArtRef(row.video), text: cgArtRef(row.text), logo: cgArtRef(row.logo), icon: cgArtRef(row.icon), wine: row.platform === "windows" ? row.wine : "",
    key: row.platform !== "command" && row.key ? row.key.path : "", ppdb: row.platform === "windows" && row.ppdb ? row.ppdb.path : "",
    joystick: row.platform !== "command" && row.joystick ? "1" : "", crop: row.crop ? "1" : "",
    runner: row.platform === "windows" ? row.runner || "portproton" : "" };
}

// O id da arte subida, ou o caminho da que veio com a pasta.
const cgArtRef = (art) => (art ? art.id || art.path || "" : "");

// cgCheckMany: os erros de cada linha pelo Setup (nada e gravado), os zips que
// ja existem e se cabe no disco. Devolve null se algo esta errado, ou
// {exists: [linhas]} (os zips que a criacao troca).
async function cgCheckMany(quiet) {
  const status = cg.el.manyStatus;
  if (!cg.rows.length) { status.textContent = t("cg_rows_none"); return null; }
  const res = await api("/api/customgames/check-packages", { method: "POST", body: JSON.stringify({ rows: cg.rows.map(cgPayload) }) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { status.textContent = data.error || res.statusText; return null; }
  cg.rows.forEach((r) => { r.errors = {}; r.state = ""; r.error = ""; });
  for (const e of data.errors || []) {
    const row = cg.rows[e.row];
    if (!row) continue;
    row.errors[e.field] = e.error;
    // Um erro num campo dos detalhes abre os detalhes da linha.
    if (CG_DETAILS.some((c) => cgFieldError(row, c))) row.open = true;
  }
  const lowSpace = data.bytes && data.bytes + (64 << 20) > data.free;
  const space = data.bytes ? t(lowSpace ? "cg_space_low" : "cg_space").replace("%s", bytes(data.bytes)).replace("%s", bytes(data.free)) : "";
  const ok = !(data.errors || []).length && !lowSpace;
  status.replaceChildren(el("span", { class: ok ? "ok" : "error" }, ok ? (quiet ? "" : t("cg_check_ok")) : (data.errors || []).length ? t("cg_errors") : ""),
    space ? el("span", { class: "dim" }, " " + space) : "");
  cgTableDraw();
  return ok ? { exists: data.exists || [] } : null;
}

// Criar: confere, pergunta o que ja existe e roda a tarefa; cada linha fica com
// o resultado dela (as que sairam deixam a tabela) e a pergunta de instalar.
async function cgCreateMany() {
  if (cg.manyBusy) return;
  cg.manyBusy = true;
  cgManyButtons();
  try {
    const checked = await cgCheckMany(true);
    if (!checked) return;
    let replace = false;
    if (checked.exists.length) {
      const names = checked.exists.map((e) => e.zip.replace(/\.fliperos-customgame\.zip$/, "")).slice(0, 6).join(", ") + (checked.exists.length > 6 ? "…" : "");
      if (!(await ask({ title: t("cg_create_many").replace("%n", cg.rows.length), text: t("cg_many_exist").replace("%n", checked.exists.length).replace("%s", names),
        yes: t("cg_create_replace"), danger: true }))) return;
      replace = true;
    }
    const rows = cg.rows.slice();
    const res = await api("/api/customgames/create-packages", { method: "POST", body: JSON.stringify({ rows: rows.map(cgPayload), replace }) });
    const data = await res.json().catch(() => ({}));
    const status = cg.el.manyStatus;
    if (!res.ok) { status.replaceChildren(el("span", { class: "error" }, res.status === 409 ? t("cg_busy") : data.error || res.statusText)); return; }
    rows.forEach((r) => { r.state = "working"; });
    cgTableDraw();
    taskNext = 0;
    const bar = meter(0);
    const step = el("span", {}, t("cg_creating_many").replace("%n", rows.length));
    status.replaceChildren(step, bar);
    const task = await waitTask(data.id, (tk) => {
      bar.firstChild.style.width = (tk.pct || 0) + "%";
      if (tk.step) step.textContent = tk.step;
    });
    if (!task) { rows.forEach((r) => { r.state = ""; }); cgTableDraw(); return; }
    for (const r of task.rows || []) {
      if (!rows[r.row]) continue;
      rows[r.row].state = r.ok ? "ok" : "fail";
      rows[r.row].error = r.ok ? "" : r.error;
    }
    rows.forEach((r) => { if (r.state === "working") r.state = ""; });
    const made = rows.filter((r) => r.state === "ok"), bad = rows.length - made.length;
    status.replaceChildren(el("span", { class: bad ? "error" : "ok" }, (made.length ? t("cg_created_n").replace("%n", made.length) + " " : "") +
      (bad ? t("cg_failed_n").replace("%n", bad) : "")));
    toast(t("cg_created_n").replace("%n", made.length), bad ? "bad" : "ok");
    cgTableDraw();
    // As que sairam deixam a tabela depois de um instante com o ✓; as outras ficam com o erro.
    if (made.length) {
      await sleep(1200);
      cg.rows = cg.rows.filter((r) => r.state !== "ok");
      cgTableDraw();
      await cgLoad();
      await cgOfferInstall(made.map((r) => ({ name: r.name.trim(), platform: r.platform, file: cgZipOf(r.name.trim()) })));
    }
  } finally {
    cg.manyBusy = false;
    cgManyButtons();
  }
}

// Depois de criar: instalar agora? O dialogo lista os pacotes feitos e deixa
// escolher o grupo (o ultimo usado ja marcado); "Agora nao" deixa os pacotes
// na lista de Jogos para instalar depois. Os que ja estao no grupo escolhido
// perguntam se trocam, como ao instalar um pacote.
async function cgOfferInstall(made) {
  if (!made.length) return;
  const wanted = await new Promise((resolve) => {
    const dlg = cgDialog();
    const group = cgGroupSelect(cg.installGroup, (value) => { cg.installGroup = value; });
    const yes = el("button", { type: "submit", class: "btn" }, icon("px-install"), t("cg_offer_yes"));
    const no = el("button", { type: "button", class: "btn ghost" }, t("cg_offer_no"));
    let answer = null;
    no.addEventListener("click", () => dlg.close());
    const form = el("form", { class: "cg-form", method: "dialog" },
      el("h3", {}, t(made.length === 1 ? "cg_offer_title_1" : "cg_offer_title").replace("%n", made.length)),
      el("ul", { class: "cg-offer-list" }, ...made.slice(0, 8).map((m) => el("li", {}, m.name)),
        made.length > 8 ? el("li", { class: "dim" }, "+" + (made.length - 8)) : ""),
      el("p", { class: "dim" }, t("cg_offer_text")),
      el("label", { class: "cg-field" }, el("span", {}, t("cg_install_into")), group),
      el("footer", {}, no, yes));
    form.addEventListener("submit", (ev) => { ev.preventDefault(); answer = group.value; dlg.close(); });
    dlg.addEventListener("close", () => resolve(answer), { once: true });
    dlg.replaceChildren(form);
    dlg.showModal();
  });
  if (!wanted || wanted === "+new") return;
  await cgLoad();
  cgShowTab("games");
  for (const m of made) {
    const p = (cg.packages || []).find((x) => x.file === m.file);
    if (!p || p.state === "bad") continue;
    await cgInstallPackage(p, wanted, { quiet: true, deleteZip: false });
  }
  cgLoad().catch(() => {});
}
