// Game Packages > ROMs e o Create package de ROM (config/fliperos-rompack,
// /api/rompacks): o pacote TITULO.fliperos-EMULADOR.zip leva as ROMs dos
// jogos escolhidos de um emulador ou core e o que vai com elas (BIOS e sets
// pais, arte, nvram, saves, cheats, configuracao por jogo), cada arquivo com o
// caminho da home; instalar o poe de volta nos mesmos lugares. Mora na pagina
// dos jogos custom (customgames.js): a aba ROMs e a escolha "ROM" do Create
// package.
"use strict";

const rp = { packages: [], targets: null, games: null, target: "", picked: new Set(), query: "", shown: 0,
  busy: false, el: null, create: null, highlight: "" };
const RP_KINDS = ["bios", "media", "nvram", "save", "cheats", "config"];
// O que fica de fora fica no navegador (o que nao esta na lista vai: um tipo de
// arte novo ja chega marcado).
const RP_KINDS_KEY = "fliperos-rp-kinds-off";
// Os tipos de arte (as pastas de ~/media), na ordem da tela.
const RP_MEDIA_ORDER = ["snap", "preview", "logo", "box", "marquee", "dmd", "texto"];
const RP_TARGET_KEY = "fliperos-rp-target";
const RP_PAGE = 200;
// O nome de um pacote de ROM (e nao o de um jogo custom).
const RP_NAME_RE = /^(.+)\.fliperos-([a-z0-9][a-z0-9-]*)\.zip$/;
const rpIsPackage = (name) => { const m = RP_NAME_RE.exec(name); return !!m && m[2] !== "customgame"; };
// O titulo vira o nome do arquivo: sai o que o Windows nao aceita num nome.
const rpTitle = (s) => (s || "").replace(/[/\\:*?"<>|\u0000-\u001f]/g, "").trim().replace(/^\.+|\.+$/g, "").slice(0, 120);
const rpZipName = (title, target) => (rpTitle(title) || t("rp_title_word")) + ".fliperos-" + (target || "EMULATOR") + ".zip";

// Os itens do "o que vai junto": as BIOS, cada tipo de arte que os jogos do
// emulador tem (media:snap, media:preview...), a memoria, os saves, os cheats e
// os ajustes.
function rpKindItems() {
  const media = (rp.mediaTypes || []).map((m) => "media:" + m);
  return ["bios", ...media, "nvram", "save", "cheats", "config"];
}

function rpKindsOff() {
  try {
    const saved = JSON.parse(localStorage.getItem(RP_KINDS_KEY) || "[]");
    if (Array.isArray(saved)) return new Set(saved);
  } catch (e) { /* sem armazenamento */ }
  return new Set();
}

// Os marcados, do que a tela mostra agora.
function rpKinds() {
  const off = rpKindsOff();
  return new Set(rpKindItems().filter((k) => !off.has(k)));
}

const rpKindLabel = (k) => (k.startsWith("media:") ? rpMediaLabel(k.slice(6)) : t("rp_kind_" + k));
const rpKindHint = (k) => (k.startsWith("media:") ? t("rp_media_hint").replace("%s", "~/media/" + k.slice(6)) : t("rp_kind_hint_" + k));
const rpMediaLabel = (m) => { const s = t("rp_media_" + m); return s === "rp_media_" + m || !s ? m : s; };

function rpProgress(box, label) {
  const bar = meter(0);
  const text = el("span", { class: "dim" }, "");
  const row = el("div", { class: "cg-prow" }, el("div", { class: "cg-pname" }, label), bar, text);
  box.append(row);
  return {
    set(pct, msg) {
      bar.firstChild.style.width = Math.max(0, Math.min(100, pct || 0)) + "%";
      if (msg != null) text.textContent = msg;
    },
    end(ok, msg) {
      bar.firstChild.style.width = "100%";
      row.classList.add(ok ? "ok" : "bad");
      text.textContent = msg || "";
      setTimeout(() => row.remove(), ok ? 5000 : 15000);
    },
  };
}

// rpTask: uma tarefa (criar, instalar), esperada, com a barra.
async function rpTask(path, body, prog) {
  const res = await api(path, { method: "POST", body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    toast(res.status === 409 ? t("cg_busy") : data.error || res.statusText, "bad");
    prog.end(false, data.error || res.statusText);
    return null;
  }
  taskNext = 0;
  return waitTask(data.id, (tk) => prog.set(tk.pct || 0, (tk.step || "") + (tk.pct ? " · " + Math.round(tk.pct) + "%" : "")));
}

// ── A aba ROMs ──

// rpLoad: os pacotes de ROM da pasta (tambem antes de abrir a aba: o numero
// dela diz quantos faltam instalar).
async function rpLoad() {
  const res = await api("/api/rompacks");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (rp.el) rp.el.list.replaceChildren(el("p", { class: "error" }, data.error || res.statusText));
    return;
  }
  rp.packages = data.packages || [];
  rpDraw();
  if (typeof cgShowTab === "function" && cg.el) cgShowTab(cg.tab);
}

function rpRenderRoms(box) {
  if (rp.el) { rpLoad().catch(() => {}); return; }
  const input = el("input", { type: "file", multiple: "", hidden: "", accept: ".zip" });
  input.addEventListener("change", () => {
    const files = [...input.files];
    input.value = "";
    rpUpload(files).catch(() => {});
  });
  const drop = el("div", { class: "cg-drop", tabindex: "0", role: "button", title: t("rp_name_rule") },
    icon("g-upload"), el("strong", {}, t("rp_drop_title")), el("span", { class: "dim" }, t("rp_drop_sub")));
  drop.addEventListener("click", () => input.click());
  drop.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); input.click(); } });
  let depth = 0;
  drop.addEventListener("dragenter", (ev) => { ev.preventDefault(); depth++; drop.classList.add("over"); });
  drop.addEventListener("dragover", (ev) => ev.preventDefault());
  drop.addEventListener("dragleave", () => { if (--depth <= 0) { depth = 0; drop.classList.remove("over"); } });
  drop.addEventListener("drop", (ev) => {
    ev.preventDefault();
    depth = 0;
    drop.classList.remove("over");
    rpUpload([...(ev.dataTransfer ? ev.dataTransfer.files : [])]).catch(() => {});
  });
  const search = el("input", { type: "search", placeholder: t("rp_search_packages"), "aria-label": t("rp_search_packages") });
  search.addEventListener("input", () => { rp.query = search.value; rpDraw(); });
  rp.el = {
    progress: el("div", { class: "cg-progress" }),
    // Ate a pasta dos pacotes ser lida, o loader.
    list: el("div", { class: "cg-list" }, loader(t("rp_loading_packages"))),
    note: el("p", { class: "dim cg-folder" }),
  };
  box.replaceChildren(cgTelegramNote("rom"), el("div", { class: "cg-upload" }, drop, el("div", { class: "cg-uopts" }, el("span", { class: "dim cg-uhint" }, t("rp_upload_hint"))), input),
    rp.el.progress, el("div", { class: "cg-pkgtools cg-filters" }, search), rp.el.note, rp.el.list);
  rpLoad().catch(() => {});
}

function rpDraw() {
  if (!rp.el) return;
  rp.el.note.textContent = t("rp_folder_note").replace("%s", cgPackagesWhere());
  const q = rp.query.trim().toLowerCase();
  const rows = rp.packages.filter((p) => !q || [p.title, p.file, p.label, ...(p.games || [])].some((s) => (s || "").toLowerCase().includes(q)));
  if (!rp.packages.length) {
    rp.el.list.replaceChildren(el("p", { class: "dim cg-empty" }, t("rp_empty")));
    return;
  }
  if (!rows.length) {
    rp.el.list.replaceChildren(el("p", { class: "dim cg-empty" }, t("cg_pkg_none_match")));
    return;
  }
  rp.el.list.replaceChildren(el("div", { class: "cg-cards" }, ...rows.map(rpCard)));
  if (rp.highlight) {
    const card = rp.el.list.querySelector('[data-key="' + CSS.escape(rp.highlight) + '"]');
    if (card) { rp.highlight = ""; card.classList.add("flash"); card.scrollIntoView({ behavior: "smooth", block: "center" }); }
  }
}

// O cartao de um pacote de ROM: a imagem e o video do primeiro jogo que tem,
// o emulador, quantos jogos, o que vai junto e o estado no gabinete.
function rpCard(p) {
  const media = (member) => (member ? "/api/customgames/package-media?zip=" + encodeURIComponent(p.zip) + "&member=" + encodeURIComponent(member) : "");
  const actions = [];
  const main = (label, fn, cls) => {
    const b = el("button", { type: "button", class: "btn small cg-main" + (cls ? " " + cls : "") }, ...[].concat(label));
    b.addEventListener("click", () => fn().catch(() => {}));
    return b;
  };
  let tag;
  if (p.state === "bad") {
    tag = { cls: "bad", text: t("cg_problem_1") };
    actions.push(main(t("cg_file_delete"), () => rpDelete(p), "ghost bad"));
  } else {
    tag = p.state === "installed" ? { cls: "ok", text: t("rp_state_installed") }
      : p.state === "partial" ? { cls: "warn", text: t("rp_state_partial") } : { cls: "new", text: t("cg_pkg_state_new") };
    actions.push(main([icon("px-install"), t("cg_install")], () => rpInstall(p)));
    actions.push(el("a", { class: "icon-btn small cg-ibtn", href: cgDownloadUrl(p.file), download: p.file, title: t("cg_download") + ": " + p.file,
      "aria-label": t("cg_download") + ": " + p.file }, icon("g-download")));
    actions.push(cgIconButton("px-remove", t("cg_pkg_delete") + ": " + p.file, () => rpDelete(p).catch(() => {})));
  }
  const card = cgCard({ name: p.title || p.file, file: p.file, snap: media(p.snap), logo: media(p.logo), video: media(p.video),
    size: p.bytes || p.size, tag, problems: p.state === "bad" ? [p.why || ""] : [] }, actions);
  const facts = card.querySelector(".cg-cfacts");
  if (facts && p.state !== "bad") {
    facts.append(el("span", { class: "tag" }, p.label || p.target));
    if (p.group) facts.append(el("span", { class: "tag on", title: t("rp_f_group") }, t("rp_group_tag").replace("%s", p.group)));
    const n = (p.games || []).length;
    facts.append(el("span", { class: "tag on" }, n === 1 ? t("cg_game_1") : t("cg_games_n").replace("%n", n)));
    for (const k of ["bios", "media", "nvram", "save", "cheats", "config"]) {
      if (p.kinds && p.kinds[k]) facts.append(el("span", { class: "tag", title: t("rp_kind_" + k) }, t("rp_kind_short_" + k)));
    }
  }
  if (p.state !== "bad" && (p.games || []).length) {
    const body = card.querySelector(".cg-cbody");
    const list = p.games.slice(0, 12).join(", ") + (p.games.length > 12 ? " " + t("rp_and_more").replace("%n", p.games.length - 12) : "");
    if (body) body.append(el("div", { class: "cg-ccat rp-games" }, list));
  }
  card.dataset.key = p.zip;
  return card;
}

// Instalar: o que o pacote traz contra o que ja esta no gabinete. Um arquivo
// com o mesmo nome e outro conteudo (o save, a nvram de quem instala, uma ROM
// de outra versao) so e trocado se a pessoa disser.
async function rpInstall(p) {
  const res = await api("/api/rompacks/inspect", { method: "POST", body: JSON.stringify({ zip: p.zip }) });
  const info = await res.json().catch(() => ({}));
  if (!res.ok) { toast(info.error || res.statusText, "bad"); return false; }
  const n = (info.games || []).length;
  const fresh = Number(info.new || 0), differ = Number(info.differ || 0);
  if (!fresh && !differ && !info.group) {
    toast(t("rp_already").replace("%s", p.title), "ok");
    return true;
  }
  const what = t("rp_install_ask").replace("%s", p.title).replace("%n", n).replace("%l", p.label || p.target)
    .replace("%f", fresh).replace("%b", bytes(p.bytes || 0));
  let replace = false;
  if (differ) {
    if (!(await ask({ title: p.title, text: what, yes: t("cg_install") }))) return false;
    replace = await ask({ title: p.title, text: t("rp_replace_ask").replace("%n", differ), yes: t("rp_replace"), no: t("rp_keep"), danger: true });
  } else if (!(await ask({ title: p.title, text: what, yes: t("cg_install") }))) return false;
  const prog = rpProgress(rp.el.progress, t("cg_installing").replace("%s", p.title));
  prog.set(0, "…");
  const task = await rpTask("/api/rompacks/install", { zip: p.zip, replace }, prog);
  const ok = !!task && task.rc === 0;
  prog.end(ok, ok ? t("rp_installed").replace("%s", p.title) : (task && (task.error || task.last)) || t("task_fail"));
  if (ok) rp.highlight = p.zip;
  rpLoad().catch(() => {});
  return ok;
}

async function rpDelete(p) {
  if (!(await ask({ title: p.file, text: t("rp_delete_ask").replace("%s", p.file), yes: t("cg_pkg_delete"), danger: true }))) return;
  const res = await api("/api/rompacks/delete", { method: "POST", body: JSON.stringify({ zip: p.zip }) });
  toast(res.ok ? t("cg_deleted").replace("%s", p.file) : (await res.json().catch(() => ({}))).error || res.statusText, res.ok ? "ok" : "bad");
  rpLoad().catch(() => {});
}

// Enviar: cada TITULO.fliperos-EMULADOR.zip sobe para a pasta dos pacotes e ja
// pergunta se instala. Um pacote de jogo de PC vai para a aba dele.
async function rpUpload(files) {
  for (const file of files) {
    if (/\.fliperos-customgame\.zip(\.\d{3})?$/i.test(file.name)) {
      toast(t("rp_is_pc").replace("%s", file.name), "bad");
      continue;
    }
    if (!rpIsPackage(file.name)) {
      toast(t("rp_name_bad").replace("%s", file.name), "bad");
      continue;
    }
    const prog = rpProgress(rp.el.progress, t("cg_uploading").replace("%s", file.name));
    prog.set(0, "0%");
    const status = await cgPostFile("/api/upload?root=roms&path=custom-packages&name=" + encodeURIComponent(file.name) + "&overwrite=1",
      file, (frac) => prog.set(frac * 100, Math.round(frac * 100) + "%"));
    if (status !== 200) {
      prog.end(false, String(status || "network error"));
      continue;
    }
    prog.end(true, t("cg_zip_sent").replace("%s", file.name));
    await rpLoad();
    const p = rp.packages.find((x) => x.file === file.name);
    if (!p) continue;
    if (p.state === "bad") { toast(file.name + ": " + (p.why || ""), "bad"); continue; }
    await rpInstall(p);
  }
}

// ── Create package > ROM ──
// Em cima, o titulo e o emulador. Embaixo, duas colunas: a esquerda o seletor
// (a busca, os filtros do frontend, os do MAME e a lista, tudo somando: cada
// criterio ligado tira mais jogos), a direita os jogos escolhidos. Depois, o que
// vai junto (cada tipo de conteudo, cada tipo de arte separado) e o grupo
// proprio com o logotipo de sistema.

// Os filtros do MAME: o campo das listas do FliperOS (as do frontend, com o XML
// do MAME, o catver e o nplayers) e como tirar o valor de cada jogo.
const RP_MAME_FIELDS = [
  ["genre", (m) => (m.Category || "").split(" / ")[0].replace(/\s*\*.*$/, "").trim()],
  ["players", (m) => (m.Players || "").trim()],
  ["buttons", (m) => (m.Buttons || "").trim()],
  ["control", (m) => (m.Control || "").trim()],
  ["decade", (m) => (/^\d{4}/.test(m.Year || "") ? m.Year.slice(0, 3) + "0s" : "")],
  ["maker", (m) => (m.Manufacturer || "").replace(/\s*\(.*$/, "").trim()],
];

function rpRenderCreate(box) {
  if (rp.create) { if (!rp.targets) rpLoadTargets().catch(() => {}); return; }
  const c = rp.create = { chips: new Set(), mame: {}, clones: "" };
  c.title = el("input", { type: "text", maxlength: "120", placeholder: t("rp_title_ph"), autocomplete: "off" });
  c.title.addEventListener("input", () => { if (!c.groupName.dataset.touched) c.groupName.value = rpTitle(c.title.value); rpCreateSummary(); });
  c.target = el("select", { "aria-label": t("rp_f_target") });
  c.target.addEventListener("change", () => {
    rp.target = c.target.value;
    try { localStorage.setItem(RP_TARGET_KEY, rp.target); } catch (e) { /* sem armazenamento */ }
    rp.picked = new Set();
    rpLoadGames().catch(() => {});
  });
  c.zip = el("code", { class: "rp-zipname" });
  // O seletor: busca, filtros e a lista.
  c.search = el("input", { type: "search", placeholder: t("rp_search_games"), "aria-label": t("rp_search_games") });
  c.search.addEventListener("input", () => { rp.query = c.search.value; rp.shown = RP_PAGE; rpDrawGames(); });
  c.chipsBox = el("div", { class: "rp-chips" });
  c.mameBox = el("div", { class: "rp-mame" });
  const clear = el("button", { type: "button", class: "btn ghost small" }, icon("g-trash"), t("rp_filters_clear"));
  clear.addEventListener("click", () => {
    c.chips.clear(); c.mame = {}; c.clones = ""; rp.query = ""; c.search.value = "";
    rpDrawFilters(); rp.shown = RP_PAGE; rpDrawGames();
  });
  const all = el("button", { type: "button", class: "btn small" }, icon("g-plus"), t("rp_pick_all"));
  all.addEventListener("click", () => { for (const g of rpFilteredGames()) rp.picked.add(g.name); rpDrawGames(); });
  const none = el("button", { type: "button", class: "btn ghost small" }, t("rp_pick_none"));
  none.addEventListener("click", () => { for (const g of rpFilteredGames()) rp.picked.delete(g.name); rpDrawGames(); });
  c.count = el("span", { class: "dim rp-count" });
  c.games = el("div", { class: "rp-games-list", role: "list" });
  c.more = el("div", {});
  // A coluna dos escolhidos.
  c.pickedHead = el("h5", { class: "rp-h rp-picked-h" });
  c.pickedList = el("div", { class: "rp-picked-list", role: "list" });
  const unpick = el("button", { type: "button", class: "btn ghost small" }, t("rp_unpick_all"));
  unpick.addEventListener("click", () => { rp.picked.clear(); rpDrawGames(); });
  c.kinds = el("div", { class: "rp-kinds" });
  // O grupo proprio: nos frontends, um sistema com estes jogos e o logotipo.
  c.groupOn = el("input", { type: "checkbox" });
  c.groupName = el("input", { type: "text", maxlength: "80", autocomplete: "off", placeholder: t("rp_group_ph") });
  c.groupName.addEventListener("input", () => { c.groupName.dataset.touched = "1"; rpCreateSummary(); });
  c.logo = cgLogoField("");
  c.groupBody = el("div", { class: "rp-group-body" },
    el("label", { class: "cg-field" }, el("span", {}, t("rp_group_name")), c.groupName), c.logo.node);
  c.groupOn.addEventListener("change", () => { c.groupBody.hidden = !c.groupOn.checked; rpCreateSummary(); });
  c.groupBody.hidden = true;
  c.groupNote = el("small", { class: "dim" });
  c.summary = el("div", { class: "rp-summary", role: "status" });
  c.status = el("div", { class: "cg-progress" });
  c.go = el("button", { type: "button", class: "btn" }, icon("px-add"), t("cg_create_go"));
  c.go.addEventListener("click", () => rpCreate().catch(() => {}));
  box.replaceChildren(
    el("p", { class: "dim cg-folder" }, t("rp_create_intro").replace("%s", cgPackagesWhere())),
    el("div", { class: "rp-form" },
      el("label", { class: "cg-field" }, el("span", {}, t("rp_f_title")), c.title),
      el("label", { class: "cg-field" }, el("span", {}, t("rp_f_target")), c.target),
      el("div", { class: "rp-zipline" }, icon("px-install"), c.zip)),
    el("div", { class: "rp-cols" },
      el("section", { class: "rp-pick" },
        el("h5", { class: "rp-h" }, t("rp_f_games")),
        // Os filtros num bloco so: a busca, os do frontend, os do MAME e, separada
        // embaixo, a linha do que fazer com os mostrados.
        el("div", { class: "rp-filters" },
          el("div", { class: "rp-frow" }, c.search, clear),
          el("div", { class: "rp-fsec" }, el("div", { class: "rp-flabel" }, t("rp_f_frontend")), c.chipsBox),
          el("div", { class: "rp-fsec" }, el("div", { class: "rp-flabel" }, t("rp_f_mame")), c.mameBox),
          el("div", { class: "rp-frow rp-factions" }, c.count, el("span", { class: "rp-fbtns" }, none, all))),
        c.games, c.more),
      el("aside", { class: "rp-picked" }, el("div", { class: "rp-picked-top" }, c.pickedHead, unpick), c.pickedList)),
    el("h5", { class: "rp-h" }, t("rp_f_kinds")), c.kinds,
    el("h5", { class: "rp-h" }, t("rp_f_group")),
    el("label", { class: "check rp-kind rp-group-on" }, c.groupOn,
      el("span", {}, el("b", {}, t("rp_group_on")), el("small", { class: "dim" }, t("rp_group_hint")), c.groupNote)),
    c.groupBody,
    c.summary, c.status, el("div", { class: "cg-create-foot" }, c.go));
  rpLoadTargets().catch(() => {});
}

async function rpLoadTargets() {
  const c = rp.create;
  // Os emuladores com jogos: o loader na lista ate eles chegarem.
  c.target.disabled = true;
  c.games.replaceChildren(loader(t("rp_loading_targets")));
  const res = await api("/api/rompacks/targets").catch(() => null);
  c.target.disabled = false;
  if (!res) { c.games.replaceChildren(el("p", { class: "error" }, "network error")); return; }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { c.games.replaceChildren(el("p", { class: "error" }, data.error || res.statusText)); return; }
  rp.targets = data.targets || [];
  if (!rp.targets.length) {
    c.target.replaceChildren();
    c.games.replaceChildren(el("p", { class: "dim cg-empty" }, t("rp_no_targets")));
    rpCreateSummary();
    return;
  }
  let saved = rp.target;
  try { saved = saved || localStorage.getItem(RP_TARGET_KEY) || ""; } catch (e) { /* sem armazenamento */ }
  c.target.replaceChildren(...rp.targets.map((tg) => el("option", { value: tg.id },
    tg.label + " · " + (tg.games === 1 ? t("cg_game_1") : t("cg_games_n").replace("%n", tg.games)))));
  rp.target = rp.targets.some((tg) => tg.id === saved) ? saved : rp.targets[0].id;
  c.target.value = rp.target;
  await rpLoadGames();
}

// Os jogos do emulador e, de cada pasta dele, o que o frontend sabe de cada um
// (o titulo, o ano, o fabricante, a categoria, os jogadores, os botoes, o
// controle, o clone, o favorito) e os filtros do frontend (/api/games).
async function rpLoadGames() {
  const c = rp.create;
  rp.games = null;
  // A barra de carregamento: a lista do emulador (ate 60%, andando sozinha
  // enquanto o gabinete le as pastas) e depois os dados do frontend de cada pasta.
  const bar = meter(0);
  const say = el("span", { class: "dim" }, t("rp_reading"));
  c.games.replaceChildren(el("div", { class: "rp-loading" }, say, bar));
  const set = (pct) => { bar.firstChild.style.width = Math.max(0, Math.min(100, pct)) + "%"; };
  let pct = 2;
  set(pct);
  const tick = setInterval(() => { pct += (60 - pct) * 0.06; set(pct); }, 250);
  rpCreateSummary();
  const target = rp.target;
  const res = await api("/api/rompacks/games?target=" + encodeURIComponent(target)).catch(() => null);
  clearInterval(tick);
  if (rp.target !== target) return;
  const data = res ? await res.json().catch(() => ({})) : {};
  if (!res || !res.ok) { c.games.replaceChildren(el("p", { class: "error" }, data.error || (res ? res.statusText : "network error"))); return; }
  const games = data.games || [];
  rp.mediaTypes = data.media_types || [];
  rp.frontendFilters = [];
  const keys = [...new Set(games.map((g) => g.key))];
  let done = 0;
  set(60);
  say.textContent = t("rp_reading_meta").replace("%n", games.length);
  await Promise.all(keys.map(async (key) => {
    try {
      const r = await api("/api/games?system=" + encodeURIComponent(key)).catch(() => null);
      if (!r || !r.ok) return;
      const d = await r.json().catch(() => ({}));
      const rows = new Map((d.games || []).map((row) => [row.Name, row]));
      for (const g of games) if (g.key === key) g.meta = rows.get(g.stem) || {};
      if (!rp.frontendFilters.length && Array.isArray(d.filters)) rp.frontendFilters = d.filters;
    } finally {
      set(60 + (++done / Math.max(1, keys.length)) * 40);
    }
  }));
  if (rp.target !== target) return;
  for (const g of games) g.meta = g.meta || {};
  rp.games = games;
  for (const n of [...rp.picked]) if (!rp.games.some((g) => g.name === n)) rp.picked.delete(n);
  c.chips.clear(); c.mame = {}; c.clones = "";
  rp.shown = RP_PAGE;
  rpDrawFilters();
  rpDrawKinds();
  rpDrawGames();
}

const rpGameTitle = (g) => (g.meta && g.meta.Title) || g.name;

// Os filtros: os chips do frontend (os do Setup e os favoritos; varios ligados
// ao mesmo tempo somam) e os do MAME (cada um um seletor com os valores que os
// jogos daqui tem; os escolhidos somam).
function rpDrawFilters() {
  const c = rp.create;
  const chips = [...rp.frontendFilters.map((f) => ({ value: f.name, label: f.name, filter: f }))];
  if (!chips.some((r) => (r.filter.rules || []).some((x) => x.field === "Favourite"))) {
    chips.unshift({ value: "__fav", label: t("favourites"), filter: FAV_FILTER, star: true });
  }
  c.chipFilters = new Map(chips.map((r) => [r.value, r.filter]));
  c.chipsBox.replaceChildren(...chips.map((r) => {
    const on = c.chips.has(r.value);
    const chip = el("button", { type: "button", class: "chip" + (on ? " on" : ""), "aria-pressed": String(on) },
      r.star ? icon("g-star", "yellow") : "", r.label);
    chip.addEventListener("click", () => {
      if (c.chips.has(r.value)) c.chips.delete(r.value); else c.chips.add(r.value);
      rpDrawFilters(); rp.shown = RP_PAGE; rpDrawGames();
    });
    return chip;
  }));
  const games = rp.games || [];
  const selects = RP_MAME_FIELDS.map(([key, get]) => {
    const counts = new Map();
    for (const g of games) { const v = get(g.meta || {}); if (v) counts.set(v, (counts.get(v) || 0) + 1); }
    if (!counts.size) return null;
    const values = [...counts.keys()].sort((a, b) => compareValues(a, b));
    const s = el("select", { "aria-label": t("rp_mf_" + key), class: c.mame[key] ? "on" : "" },
      el("option", { value: "" }, t("rp_mf_" + key)), ...values.map((v) => el("option", { value: v }, v + " (" + counts.get(v) + ")")));
    s.value = c.mame[key] || "";
    s.addEventListener("change", () => {
      if (s.value) c.mame[key] = s.value; else delete c.mame[key];
      s.className = s.value ? "on" : "";
      rp.shown = RP_PAGE; rpDrawGames();
    });
    return s;
  }).filter(Boolean);
  if (games.some((g) => g.meta && g.meta.CloneOf)) {
    const s = el("select", { "aria-label": t("rp_mf_clones"), class: c.clones ? "on" : "" },
      ...["", "no", "only"].map((v) => el("option", { value: v }, t("rp_clones_" + (v || "all")))));
    s.value = c.clones;
    s.addEventListener("change", () => { c.clones = s.value; s.className = s.value ? "on" : ""; rp.shown = RP_PAGE; rpDrawGames(); });
    selects.push(s);
  }
  c.mameBox.replaceChildren(...(selects.length ? selects : [el("span", { class: "dim" }, t("rp_mf_none"))]));
}

function rpFilteredGames() {
  const c = rp.create;
  const q = rp.query.trim().toLowerCase();
  let rows = (rp.games || []).filter((g) => !q || g.name.toLowerCase().includes(q) || rpGameTitle(g).toLowerCase().includes(q) ||
    g.files.some((f) => f.toLowerCase().includes(q)));
  if (!c) return rows;
  // Os chips do frontend: cada um ligado tira mais (as regras do Attract-Mode, games.js).
  for (const value of c.chips) {
    const filter = c.chipFilters && c.chipFilters.get(value);
    if (!filter) continue;
    const pass = new Set(applyFilter(rows.map((g) => Object.assign({}, g.meta, { __g: g })), Object.assign({}, filter, { limit: 0, sort_by: "" }))
      .map((m) => m.__g));
    rows = rows.filter((g) => pass.has(g));
  }
  for (const [key, get] of RP_MAME_FIELDS) {
    if (c.mame[key]) rows = rows.filter((g) => get(g.meta || {}) === c.mame[key]);
  }
  if (c.clones === "no") rows = rows.filter((g) => !(g.meta && g.meta.CloneOf));
  if (c.clones === "only") rows = rows.filter((g) => g.meta && g.meta.CloneOf);
  return rows;
}

// O que vai junto das ROMs: um item por tipo de conteudo que os jogos do
// emulador tem (cada tipo de arte separado), com quantos jogos tem cada um.
function rpDrawKinds() {
  const c = rp.create;
  if (!c) return;
  const off = rpKindsOff();
  const games = rp.games || [];
  const count = (k) => {
    if (k.startsWith("media:")) return games.filter((g) => ((g.has || {}).media || []).includes(k.slice(6))).length;
    if (k === "bios") return null;
    return games.filter((g) => (g.has || {})[k]).length;
  };
  c.kinds.replaceChildren(...rpKindItems().map((k) => {
    const box = el("input", { type: "checkbox", value: k });
    box.checked = !off.has(k);
    box.addEventListener("change", () => {
      const set = rpKindsOff();
      if (box.checked) set.delete(k); else set.add(k);
      try { localStorage.setItem(RP_KINDS_KEY, JSON.stringify([...set])); } catch (e) { /* sem armazenamento */ }
      rpCreateSummary();
    });
    const n = count(k);
    const head = el("b", {}, rpKindLabel(k));
    if (n != null) head.append(el("span", { class: "dim rp-kcount" }, " · " + (n === 1 ? t("cg_game_1") : t("cg_games_n").replace("%n", n))));
    return el("label", { class: "check rp-kind" + (n === 0 ? " rp-none" : "") }, box, el("span", {}, head, el("small", { class: "dim" }, rpKindHint(k))));
  }));
}

// O que um jogo tem alem da ROM, em etiquetas pequenas.
function rpHas(g) {
  const h = g.has || {};
  const out = [];
  for (const m of h.media || []) out.push(el("span", { class: "tag", title: rpMediaLabel(m) }, m));
  for (const k of ["nvram", "save", "cheats", "config"]) if (h[k]) out.push(el("span", { class: "tag on", title: t("rp_kind_" + k) }, t("rp_kind_short_" + k)));
  return out;
}

function rpGameName(g) {
  const title = rpGameTitle(g);
  return el("span", { class: "rp-gname", title: g.files.join(", ") }, title,
    title !== g.name ? el("small", { class: "dim" }, " " + g.name) : "");
}

function rpDrawGames() {
  const c = rp.create;
  if (!c || !rp.games) return;
  const rows = rpFilteredGames();
  c.count.textContent = t("rp_shown").replace("%n", rows.length).replace("%t", rp.games.length);
  if (!rp.games.length) {
    c.games.replaceChildren(el("p", { class: "dim cg-empty" }, t("rp_no_games")));
    c.more.replaceChildren();
  } else {
    const shown = rows.slice(0, rp.shown || RP_PAGE);
    c.games.replaceChildren(...(shown.length ? shown.map((g) => {
      const box = el("input", { type: "checkbox" });
      box.checked = rp.picked.has(g.name);
      // O "+": abre embaixo a ficha do jogo (os metadados e a arte).
      const open = rp.metaOpen === g.name;
      const plus = el("button", { type: "button", class: "rp-plus" + (open ? " on" : ""), "aria-expanded": String(open),
        title: t("rp_meta_open"), "aria-label": t("rp_meta_open") + ": " + rpGameTitle(g) }, icon(open ? "g-minus" : "g-plus"));
      plus.addEventListener("click", () => { rp.metaOpen = open ? "" : g.name; rpDrawGames(); });
      const label = el("label", { class: "rp-game" }, box, rpGameName(g),
        el("span", { class: "rp-ghas" }, ...rpHas(g)), el("span", { class: "dim rp-gsize" }, bytes(g.bytes || 0)));
      const line = el("div", { class: "rp-row" + (box.checked ? " on" : "") + (open ? " open" : ""), role: "listitem" }, plus, label);
      box.addEventListener("change", () => {
        if (box.checked) rp.picked.add(g.name); else rp.picked.delete(g.name);
        line.classList.toggle("on", box.checked);
        rpDrawPicked();
      });
      if (!open) return line;
      return el("div", { class: "rp-rowwrap" }, line, rpMetaPanel(g));
    }) : [el("p", { class: "dim cg-empty" }, t("cg_pkg_none_match"))]));
    if (rows.length > shown.length) {
      // O numero e o de jogos que o clique poe na lista; o que ainda falta vai entre parenteses.
      const left = rows.length - shown.length, step = Math.min(RP_PAGE, left);
      const more = el("button", { type: "button", class: "btn ghost small cg-more" }, t("cg_show_more_of").replace("%n", step).replace("%r", left));
      more.addEventListener("click", () => { rp.shown = (rp.shown || RP_PAGE) + step; rpDrawGames(); });
      c.more.replaceChildren(more);
    } else c.more.replaceChildren();
  }
  rpDrawPicked();
}

// A ficha de um jogo (o "+"): os metadados que os filtros usam, para mudar ou
// pôr o que falta, e a arte dele, lida so agora (uma ficha aberta por vez).
// Salvar grava na copia do FliperOS (config/fliperos-gamemeta), que vale nas
// listas do frontend e vai no pacote.
const RP_META_FIELDS = ["Title", "Year", "Manufacturer", "Category", "Players", "Buttons", "Control", "Rotation", "CloneOf",
  "Series", "Language", "Region", "Rating", "Status"];
const RP_MEDIA_SHOW = ["snap", "preview", "box", "logo", "marquee", "dmd", "texto"];

// Os campos de texto livre; os outros sao listas com os valores que ja existem.
const RP_META_TEXT = ["Title", "Year"];
// Os valores fixos de cada lista (o Control como as listas do Attract-Mode o escrevem,
// os 13 tipos de controle do FliperOS, config/fliperos-web CUSTOM_CONTROLS).
const RP_META_FIXED = {
  Players: ["1", "2", "3", "4", "5", "6", "8"],
  Buttons: ["0", "1", "2", "3", "4", "5", "6", "7", "8", "10"],
  Control: ["joystick (8-way)", "joystick (4-way)", "joystick (2-way)", "double joystick (8-way)", "trackball", "dial",
    "paddle", "positional", "analog stick", "pedal", "lightgun", "keyboard", "mahjong"],
  Rotation: ["0", "90", "180", "270"],
  Status: ["good", "imperfect", "preliminary"],
};

// rpMetaControl: o controle de um campo. Uma lista (os valores fixos, os dos jogos
// deste emulador e, na categoria, as do catver em genero > subgenero) com "Outro…",
// que troca por um campo de texto; o valor de agora sempre entra. Devolve
// {node, value}.
function rpMetaControl(f, value, g) {
  if (RP_META_TEXT.includes(f)) {
    const input = el("input", { type: "text", value, maxlength: "200", autocomplete: "off",
      inputmode: f === "Year" ? "numeric" : "text" });
    return { node: input, get value() { return input.value; } };
  }
  const have = new Set((rp.games || []).map((x) => (x.meta || {})[f]).filter(Boolean));
  if (f === "CloneOf") for (const x of rp.games || []) if (x.stem !== g.stem && !(x.meta || {}).CloneOf) have.add(x.stem);
  const fixed = RP_META_FIXED[f] || [];
  const numeric = (a, b) => (/^\d+$/.test(a) && /^\d+$/.test(b) ? Number(a) - Number(b) : a.localeCompare(b, undefined, { sensitivity: "base" }));
  const select = el("select", {}, el("option", { value: "" }, t("rp_meta_none")));
  const seen = new Set();
  const opt = (v) => { seen.add(v); return el("option", { value: v }, v); };
  if (f === "Category") {
    // As do catver.ini (o genero e as categorias dele) e, antes, as que os jogos ja usam.
    const mine = [...have].sort(numeric);
    if (mine.length) select.append(el("optgroup", { label: t("rp_meta_in_use") }, ...mine.map(opt)));
    for (const gen of (cg.info && cg.info.genres) || []) {
      const subs = [gen.name, ...(gen.subs || [])].filter((v) => !seen.has(v));
      if (subs.length) select.append(el("optgroup", { label: gen.name }, ...subs.map(opt)));
    }
  } else {
    const all = [...new Set([...fixed, ...have])].sort(fixed.length && f !== "Status" && f !== "Control" ? numeric : (a, b) => {
      const ia = fixed.indexOf(a), ib = fixed.indexOf(b);
      return ia >= 0 && ib >= 0 ? ia - ib : ia >= 0 ? -1 : ib >= 0 ? 1 : numeric(a, b);
    });
    select.append(...all.slice(0, 2500).map(opt));
  }
  if (value && !seen.has(value)) select.append(opt(value));
  select.append(el("option", { value: "__other" }, t("rp_meta_other")));
  select.value = value;
  const text = el("input", { type: "text", maxlength: "200", autocomplete: "off", hidden: "", placeholder: t("rp_meta_other_ph") });
  const back = el("button", { type: "button", class: "icon-btn small", hidden: "", title: t("rp_meta_back"), "aria-label": t("rp_meta_back") },
    icon("g-close"));
  select.addEventListener("change", () => {
    if (select.value !== "__other") return;
    select.hidden = true; text.hidden = false; back.hidden = false;
    text.value = ""; text.focus();
  });
  back.addEventListener("click", (ev) => {
    ev.preventDefault();
    select.hidden = false; text.hidden = true; back.hidden = true;
    select.value = value;
  });
  const node = el("span", { class: "rp-mctl" }, select, text, back);
  return { node, get value() { return select.hidden ? text.value : select.value === "__other" ? "" : select.value; } };
}

function rpMetaPanel(g) {
  const box = el("div", { class: "rp-meta" }, el("p", { class: "dim" }, t("rp_reading")));
  rpMetaLoad(g, box).catch((e) => box.replaceChildren(el("p", { class: "error" }, String(e))));
  return box;
}

async function rpMetaLoad(g, box) {
  const res = await api("/api/gamemeta?system=" + encodeURIComponent(g.key) + "&game=" + encodeURIComponent(g.stem));
  const data = await res.json().catch(() => ({}));
  if (rp.metaOpen !== g.name) return;
  if (!res.ok) { box.replaceChildren(el("p", { class: "error" }, data.error || res.statusText)); return; }
  const edited = new Set(data.edited || []);
  const inputs = {};
  const grid = el("div", { class: "rp-meta-fields" }, ...RP_META_FIELDS.map((f) => {
    const field = rpMetaControl(f, (data.fields || {})[f] || "", g);
    inputs[f] = field;
    return el("label", { class: "cg-field rp-mf" + (edited.has(f) ? " edited" : "") }, el("span", {}, t("rp_mfl_" + f)), field.node);
  }));
  const lists = {};
  const status = el("span", { class: "dim rp-meta-status", role: "status" });
  const save = el("button", { type: "button", class: "btn small" }, icon("px-save"), t("cg_save"));
  save.addEventListener("click", async () => {
    const fields = {};
    for (const f of RP_META_FIELDS) fields[f] = inputs[f].value.trim();
    save.disabled = true;
    status.textContent = t("rp_meta_saving");
    const r = await api("/api/gamemeta", { method: "POST", body: JSON.stringify({ system: g.key, game: g.stem, fields }) });
    save.disabled = false;
    if (!r.ok) { status.textContent = (await r.json().catch(() => ({}))).error || r.statusText; return; }
    // A lista do jogo ja tem os valores novos: os filtros e o titulo acompanham.
    g.meta = Object.assign({}, g.meta);
    for (const f of RP_META_FIELDS) if (fields[f]) g.meta[f] = fields[f]; else delete g.meta[f];
    status.textContent = t("rp_meta_saved");
    toast(t("rp_meta_saved"), "ok");
    rpDrawFilters();
    rpDrawGames();
  });
  const close = el("button", { type: "button", class: "btn ghost small" }, t("cg_cancel"));
  close.addEventListener("click", () => { rp.metaOpen = ""; rpDrawGames(); });
  // A arte: so a que o jogo tem, pedida agora.
  const media = (data.media || []).filter((k) => RP_MEDIA_SHOW.includes(k));
  const url = (kind) => "/api/media?system=" + encodeURIComponent(g.key) + "&kind=" + kind + "&game=" + encodeURIComponent(g.stem);
  const art = el("div", { class: "rp-meta-art" }, ...(media.length ? media.map((kind) => {
    let node;
    if (kind === "preview") node = el("video", { src: url(kind), controls: "", muted: "", loop: "", playsinline: "", preload: "metadata" });
    else if (kind === "texto") {
      node = el("div", { class: "rp-meta-text" });
      fetch(url(kind), { headers: { "X-FliperOS": "1" } }).then((r) => (r.ok ? r.text() : "")).then((s) => { node.textContent = s.trim(); }).catch(() => {});
    } else node = el("img", { src: url(kind), alt: "", loading: "lazy" });
    return el("figure", { class: "rp-meta-media " + kind }, node, el("figcaption", {}, rpMediaLabel(kind)));
  }) : [el("p", { class: "dim" }, t("rp_meta_noart"))]));
  box.replaceChildren(el("div", { class: "rp-meta-head" }, el("b", {}, rpGameTitle(g)), el("code", { class: "dim" }, g.stem),
    el("small", { class: "dim" }, t("rp_meta_note"))),
    grid, ...Object.values(lists), art, el("div", { class: "rp-meta-foot" }, status, close, save));
  // A ficha inteira a vista dentro da lista (que rola).
  requestAnimationFrame(() => box.scrollIntoView({ behavior: "smooth", block: "nearest" }));
}

// A coluna da direita: os jogos escolhidos, em ordem, cada um com o tirar.
function rpDrawPicked() {
  const c = rp.create;
  if (!c) return;
  const picked = (rp.games || []).filter((g) => rp.picked.has(g.name))
    .sort((a, b) => rpGameTitle(a).localeCompare(rpGameTitle(b), undefined, { sensitivity: "base" }));
  const size = picked.reduce((s, g) => s + (g.bytes || 0), 0);
  c.pickedHead.textContent = t("rp_picked").replace("%n", picked.length).replace("%s", bytes(size));
  c.pickedList.replaceChildren(...(picked.length ? picked.map((g) => {
    const out = el("button", { type: "button", class: "icon-btn small", title: t("rp_unpick"), "aria-label": t("rp_unpick") + ": " + rpGameTitle(g) },
      icon("g-close"));
    out.addEventListener("click", () => { rp.picked.delete(g.name); rpDrawGames(); });
    return el("div", { class: "rp-pgame", role: "listitem" }, rpGameName(g), el("span", { class: "dim rp-gsize" }, bytes(g.bytes || 0)), out);
  }) : [el("p", { class: "dim rp-picked-empty" }, t("rp_pick_some"))]));
  rpCreateSummary();
}

function rpCreateSummary() {
  const c = rp.create;
  if (!c) return;
  c.zip.textContent = rpZipName(c.title.value, rp.target);
  const picked = (rp.games || []).filter((g) => rp.picked.has(g.name));
  const size = picked.reduce((s, g) => s + (g.bytes || 0), 0);
  const kinds = rpKinds();
  const noGroup = picked.filter((g) => !g.group_ok).length;
  c.groupNote.textContent = c.groupOn.checked && noGroup ? " " + t("rp_group_skip").replace("%n", noGroup) : "";
  const group = c.groupOn.checked ? c.groupName.value.trim() : "";
  c.summary.textContent = picked.length
    ? t("rp_summary").replace("%n", picked.length).replace("%s", bytes(size)) +
      (kinds.size ? " " + t("rp_summary_plus").replace("%s", [...kinds].map((k) => rpKindLabel(k).toLowerCase()).join(", ")) : "") +
      (group ? " " + t("rp_summary_group").replace("%s", group) : "")
    : t("rp_pick_some");
  c.go.disabled = rp.busy || !picked.length || !rpTitle(c.title.value) || !rp.target ||
    (c.groupOn.checked && (!group || /[/\\|]/.test(group) || group.startsWith(".")));
}

async function rpCreate(replace = false) {
  const c = rp.create;
  const title = rpTitle(c.title.value);
  const games = (rp.games || []).filter((g) => rp.picked.has(g.name)).map((g) => g.name);
  if (!title || !games.length) return;
  const body = { target: rp.target, title, games, kinds: [...rpKinds()], replace };
  if (c.groupOn.checked) {
    body.group = c.groupName.value.trim();
    const change = c.logo.change;
    if (change && change.logo) body.logo = change.logo;
    else if (change && change.system) body.system = change.system;
  }
  rp.busy = true;
  rpCreateSummary();
  const zip = rpZipName(title, rp.target);
  const prog = rpProgress(c.status, t("rp_making").replace("%s", zip));
  prog.set(0, "…");
  const task = await rpTask("/api/rompacks/create", body, prog);
  rp.busy = false;
  rpCreateSummary();
  if (task && task.rc === 3 && !replace) {
    prog.end(false, t("cg_cancel"));
    if (await ask({ title: zip, text: t("cg_create_exists").replace("%s", zip), yes: t("cg_create_replace"), danger: true })) return rpCreate(true);
    return;
  }
  const ok = !!task && task.rc === 0;
  prog.end(ok, ok ? t("rp_made").replace("%s", zip) : (task && (task.error || task.last)) || t("task_fail"));
  if (!ok) return;
  c.status.append(el("div", { class: "cg-status ok" }, el("span", {}, t("rp_made_note").replace("%s", zip).replace("%s", cgPackagesWhere()) +
    (body.group ? " " + t("rp_made_group").replace("%s", body.group) : "")),
    " ", el("a", { class: "btn small", href: cgDownloadUrl(zip), download: zip }, icon("px-install"), t("cg_download"))));
  rp.highlight = (cg.info && cg.info.packages_dir ? cg.info.packages_dir + "/" : "") + zip;
  if (rp.el) rpLoad().catch(() => {});
  if (body.group) cgLoad().catch(() => {});
}
