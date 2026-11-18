// Sistema > Setup: a arvore inteira do Setup do gabinete, na mesma ordem e
// com os mesmos itens (os ui_menu_hints de fliperos-setup/screens), como uma
// lista de ajustes: os grupos numa coluna, com a busca, e o grupo aberto em
// secoes, uma linha por ajuste (uiRow e uiSection, de system.js). O passo que
// precisa do tubo ou do controle na mao vira uma linha "no gabinete", que
// abre a tela no tubo (fliperos-setup --screen, screens/panel.sh).
// O endereco e #system/setup/GRUPO; a pagina de um item (Jogos custom, a
// versao, as novidades) e #system/setup/GRUPO/PAGINA. No celular, a lista dos
// grupos e a primeira tela, como nos Ajustes do telefone.
"use strict";

// Os grupos e os itens. id: o do menu do Setup (o teste de paridade confere
// os dois lados); also: outros itens do Setup que este cobre; keys: as chaves
// do --settings (exatas, ou o comeco quando terminam em "."); box: as linhas
// que vem de outro pedido (SETUP_BOXES); link: outra pagina do painel; page:
// uma pagina daqui (SETUP_PAGES); cabinet: a tela do Setup aberta no
// gabinete; when: so com esse item no gabinete (--setup-items); info: o texto
// do --setup-items que vai junto; extra: so do painel (nao e um item do menu
// do Setup). Na lista: title, uma secao com o nome do item; sec, uma secao
// com outros itens (ss_NOME); into, as linhas vao para a secao de outro
// item; top, o item vem primeiro.
const SETUP_TREE = [
  { id: "video", icon: "px-video", items: [
    { id: "monitor", keys: ["monitor", "video.previous"] },
    { id: "orientation", keys: ["orientation"] },
    { id: "resolution", keys: ["resolution"], cabinet: "resolution" },
    { id: "geometry", box: "geometry", cabinet: "geometry", title: true },
    { id: "geometry_reset", box: "geometryReset", into: "geometry" },
    { id: "monitors", keys: ["mm_games"], cabinet: "monitors" },
    { id: "mode480", keys: ["mode480.", "deflicker."], title: true },
    { id: "colour", keys: ["color."], cabinet: "colour", title: true },
    { id: "scanlines", keys: ["scanlines", "scanline."], cabinet: "scanlines", when: "scanlines", title: true },
    { id: "retest", cabinet: "outputs", sec: "outputs" },
    { id: "driver", cabinet: "driver", info: "driver", top: true },
    { id: "lowdot", cabinet: "lowdot", when: "lowdot", info: "lowdot", sec: "outputs" },
    { id: "firmware", cabinet: "firmware", when: "firmware", sec: "outputs" },
    { id: "osd", keys: ["osd"], box: "osd", extra: true, title: true },
  ] },
  { id: "audio", icon: "px-audio", items: [
    { id: "card", keys: ["audio_card"] },
    { id: "volume", box: "volume" },
    { id: "mixer", cabinet: "mixer" },
    { id: "latency", label: "mame_latency", keys: ["mame_latency"] },
    { id: "test", keys: ["audio.test"] },
    { id: "sounds", keys: ["menu_sounds"], box: "sounds", title: true },
  ] },
  { id: "network", icon: "px-network", items: [
    { id: "wifi", also: ["hidden", "status"], box: "wifi", title: true },
    { id: "live", keys: ["stream_audio", "stream_quality", "marquee_overlay"], extra: true, title: true },
  ] },
  { id: "games", icon: "px-games", items: [
    { id: "emulators", link: "#library/install" },
    { id: "frontend", keys: ["launcher"], box: "frontends" },
    { id: "extras", link: "#library/install" },
    { id: "custom", page: "custom" },
    { id: "folders", box: "folders", title: true },
    { id: "downloader", link: "#library/downloads" },
    { id: "cleaner", link: "#library/romfilter" },
    { id: "scraper", link: "#library/art" },
    { id: "romlist", box: "romlist" },
  ] },
  { id: "joysticks", icon: "px-joysticks", items: [
    { id: "buttons", cabinet: "buttons", info: "buttons" },
    { id: "bluetooth", box: "bluetooth", cabinet: "bluetooth", when: "bluetooth", title: true },
    { id: "layout", cabinet: "layout" },
    { id: "guncon", keys: ["gun_flash", "gun.", "gun_offscreen_reload"], cabinet: "guncon", title: true },
    { id: "axes", cabinet: "axes" },
    { id: "padcolor", keys: ["padcolor"] },
    { id: "haptic", keys: ["haptic", "haptic."] },
    { id: "lpt", cabinet: "lpt", info: "lpt" },
  ] },
  { id: "system", icon: "px-system", items: [
    { id: "latency", keys: ["latency"], cabinet: "latency" },
    { id: "services", keys: ["service."], title: true },
    { id: "quirks", box: "quirks", title: true },
    { id: "storage", cabinet: "storage" },
    { id: "password", box: "password" },
    { id: "cabinetname", keys: ["cabinet_name"] },
    { id: "update", box: "update", sec: "updates" },
    { id: "version", page: "version", sec: "updates" },
    { id: "whatsnew", page: "whatsnew", sec: "updates" },
    { id: "debug", keys: ["debug"] },
    { id: "lab", link: "#system/lab" },
    { id: "oscr", cabinet: "oscr" },
    { id: "splash", keys: ["splash"] },
    { id: "power", keys: ["power."], extra: true, title: true },
  ] },
  { id: "cloud", icon: "px-cloud", items: [
    { id: "cloud", link: "#system/cloud" },
  ] },
];

// Os icones dos itens sem um px-ID proprio (os mesmos do carrossel do
// Setup, fliperos-setup/gui/theme.py): ao lado de cada item na busca.
const SETUP_ICON = { monitor: "px-video", geometry_reset: "px-reset", monitors: "px-outputs", driver: "px-chip",
  lowdot: "px-outputs", osd: "px-layout", card: "px-system", volume: "px-audio", test: "px-audio", sounds: "px-audio",
  wifi: "px-network", live: "px-outputs", extras: "px-freeroms", custom: "px-customgames", folders: "px-dest",
  downloader: "px-install", cleaner: "px-filter", update: "px-reset", version: "px-reset", whatsnew: "px-romlist",
  splash: "px-video", storage: "px-disk", other: "px-setup" };
// Os grupos do --settings, para um ajuste novo que nenhum item pega (ele vai
// para "Outros ajustes" do grupo dele: nada some).
const SETUP_ROW_GROUP = { Video: "video", Colour: "video", Scanlines: "video", "Interlaced hacks": "video",
  Audio: "audio", "GunCon 2": "joysticks", Joysticks: "joysticks", "Live screen": "network" };
// As caixas com secao propria (split) e as que levam uma nota embaixo.
const SETUP_BOX_META = {
  frontends: { split: true, title: "fe_custom", note: "fe_boot" },
  folders: { note: "fo_note" }, quirks: { note: "qk_note" }, bluetooth: { note: "bt_howto" },
  osd: { note: "osd_note" }, sounds: { note: "snd_note" },
};

// O caminho dentro do Setup (app.js o poe: #system/setup/GRUPO/PAGINA).
let setupPath = "";
let setupInfo = { items: {}, info: {} };
// O texto da busca e o item a mostrar depois de abrir o grupo (da busca).
let setupQuery = "";
let setupFocus = "";

const setupKeyMatch = (keys, key) => (keys || []).some((k) => key === k || (k.endsWith(".") && key.startsWith(k)));
const setupGroup = () => SETUP_TREE.find((g) => g.id === (setupPath || "").split("/")[0]) || SETUP_TREE[0];
const setupLabel = (item) => (item.id === "other" ? t("setup_other") : t("si_" + (item.label || item.id)));
const setupHint = (item) => (item.id === "other" ? "" : t("sih_" + (item.label || item.id)));
const setupIcon = (item) => SETUP_ICON[item.id] || "px-" + item.id;
const setupNarrow = () => matchMedia("(max-width: 1040px)").matches;
const sleep = (ms) => new Promise((done) => setTimeout(done, ms));

// Os itens de um grupo neste gabinete, cada um com os ajustes dele.
function setupItems(group, rows) {
  const out = [];
  for (const item of group.items) {
    if (item.when && !setupInfo.items[item.when]) continue;
    const mine = rows.filter((r) => setupKeyMatch(item.keys, r.key));
    // Um item so de ajustes que este gabinete nao tem (a tela ao vivo sem o
    // go2rtc ainda tem o marquee; as scanlines a 15 kHz ficam de fora).
    if (item.keys && !mine.length && !item.box && !item.cabinet) continue;
    out.push({ item, rows: mine });
  }
  const known = (r) => SETUP_TREE.some((g) => g.items.some((i) => setupKeyMatch(i.keys, r.key)));
  const other = rows.filter((r) => !known(r) && (SETUP_ROW_GROUP[r.group] || "system") === group.id);
  if (other.length) out.push({ item: { id: "other", title: true }, rows: other });
  return out;
}

// loadSettings: o grupo do endereco (o nome antigo: app.js e as caixas
// chamam esta funcao depois de cada mudanca).
async function loadSettings() {
  const group = setupGroup();
  const pageName = (setupPath || "").split("/")[1] || "";
  const pageItem = !setupQuery && pageName ? group.items.find((i) => i.page === pageName) : null;
  setupNav(group.id);
  $("setup").dataset.mobile = setupPath || setupQuery ? "group" : "list";
  $("settings").hidden = !!pageItem;
  $("setup-page").hidden = !pageItem;
  if (pageItem) return setupPage(group, pageItem);
  delete $("setup-page").dataset.page;
  $("setup-page").replaceChildren();
  // Os ajustes vem do Setup do gabinete (fliperos-setup --settings), que leva
  // alguns segundos. Trocar de grupo desenha na hora com os da ultima leitura
  // (setupRows) e le de novo por tras; sem eles (a primeira vez), o aviso de
  // carregando no lugar da lista. O grupo clicado gira enquanto le.
  const switched = setupShown !== group.id;
  const cached = !!setupRows && switched;
  if (cached) setupDraw(group, setupRows);
  else if (!setupRows) {
    $("settings").replaceChildren(el("p", { class: "dim setup-loading" }, el("span", { class: "spinner" }), t("setup_loading")));
  }
  setupBusy(group.id, true);
  let rows;
  try {
    const [settingsRes, itemsRes] = await Promise.all([api("/api/settings"), api("/api/setup/items")]);
    rows = (await settingsRes.json()).settings || [];
    setupInfo = itemsRes.ok ? await itemsRes.json() : { items: {}, info: {} };
  } catch (e) {
    setupBusy(group.id, false);
    if (e.message !== "login" && !setupRows) {
      $("settings").replaceChildren(el("p", { class: "error" }, t("setup_error").replace("%s", e.message)));
    }
    return;
  }
  setupBusy(group.id, false);
  const changed = JSON.stringify(rows) !== JSON.stringify(setupRows);
  setupRows = rows;
  // Mudou de grupo enquanto o Setup respondia: o outro desenha.
  if (setupGroup() !== group || $("settings").hidden) return;
  setupNav(group.id);
  // Desenhado agora ha pouco com a leitura de antes, e nada mudou: fica (sem
  // piscar). Depois de um ajuste (o mesmo grupo), desenha sempre: as caixas
  // (o volume, a geometria) leem as coisas delas de novo.
  if (cached && !changed && setupShown === group.id) return;
  setupDraw(group, rows);
}

// Os ajustes da ultima leitura e o grupo desenhado com eles.
let setupRows = null;
let setupShown = "";

// setupBusy: o grupo esta lendo os ajustes do gabinete (gira na coluna).
function setupBusy(id, on) {
  const link = $("setup-groups").querySelector('a[href="#system/setup/' + id + '"]');
  if (link) link.classList.toggle("busy", on);
  $("settings").setAttribute("aria-busy", String(on));
}

// Os sete grupos na coluna, como o menu do Setup, com quantos itens cada um
// tem neste gabinete. No celular, sem grupo no endereco, nenhum fica aceso
// (a lista e a tela).
function setupNav(current) {
  const none = setupQuery || (setupNarrow() && !setupPath);
  $("setup-groups").replaceChildren(...SETUP_TREE.map((g) => {
    const on = !none && g.id === current;
    return el("a", { href: "#system/setup/" + g.id, class: on ? "on" : "", "aria-current": on ? "page" : "false" },
      icon(g.icon), el("span", { class: "gname" }, t("sg_" + g.id)),
      el("span", { class: "count" }, setupRows ? String(setupItems(g, setupRows).length) : ""));
  }));
}

function setupBack(href, label) {
  const back = el("a", { class: "back", href }, icon("g-back"), label);
  back.addEventListener("click", () => {
    setupClearSearch();
    if (location.hash === href) loadSettings().catch(() => {});
  });
  return back;
}

function setupDraw(group, rows) {
  setupShown = group.id;
  if (setupQuery) return setupSearch();
  // Os pedidos das caixas, uma vez por desenho (a geometria serve a duas).
  const cache = new Map();
  const ctx = { json: (path) => {
    if (!cache.has(path)) cache.set(path, api(path).then((r) => r.json()));
    return cache.get(path);
  } };
  const blocks = [];
  for (const { item, rows: mine } of setupItems(group, rows)) blocks.push(...setupBlocks(group, item, mine, ctx));
  $("settings").replaceChildren(setupBack("#system/setup", t("sub_setup")), el("h2", {}, t("sg_" + group.id)),
    el("p", { class: "lead" }, t("sgh_" + group.id)), ...setupSections(blocks));
  if (setupFocus) {
    const target = $(setupFocus) || $("settings").querySelector('[data-item="' + setupFocus + '"]');
    setupFocus = "";
    if (target) {
      target.scrollIntoView({ block: "center" });
      target.classList.add("flash");
    }
  }
}

// Os blocos de um item: as linhas dele, com o titulo, a nota e onde vao.
function setupBlocks(group, item, rows, ctx) {
  const label = setupLabel(item);
  const id = "si-" + group.id + "-" + item.id;
  // Outra pagina (do painel ou daqui): o item e um link.
  if (item.link || item.page) {
    const href = item.page ? "#system/setup/" + group.id + "/" + item.page : item.link;
    return [{ id, sec: item.sec, rows: [uiRow({ label, sub: setupHint(item), href, control: icon("g-chev"), cls: "go-row" })] }];
  }
  if (item.id === "driver") return [{ id, top: true, title: t("si_gpu"), rows: [gpuRow(item)] }];
  const own = item.id === "mode480" ? mode480Rows(rows) : rows.map(settingRow);
  const blocks = [];
  const meta = SETUP_BOX_META[item.box] || {};
  if (item.box) {
    const part = setupBoxPart(item, label, ctx);
    if (meta.split) blocks.push({ id: id + "-box", title: t(meta.title), note: t(meta.note), rows: [part] });
    else own.push(part);
  }
  if (item.cabinet) own.push(cabinetRow(item, label, own.length > 0));
  const note = !meta.split && meta.note ? t(meta.note) : item.id === "mode480" ? setupHint(item) : "";
  blocks.unshift({ id, title: item.title ? label : "", note, sec: item.sec, into: item.into, rows: own });
  return blocks.filter((b) => b.rows.length);
}

// As secoes: o item com titulo (ou com 3 linhas ou mais) na dele; os de uma
// linha ou duas juntos, sem titulo; os de um mesmo sec juntos.
function setupSections(blocks) {
  const sections = [], byItem = new Map();
  let last = null;
  for (const b of [...blocks.filter((x) => x.top), ...blocks.filter((x) => !x.top)]) {
    let sec = b.into ? byItem.get("si-" + b.id.split("-")[1] + "-" + b.into) : null;
    if (!sec && b.sec) {
      sec = last && last.key === "sec:" + b.sec ? last : null;
      if (!sec) sections.push(sec = { key: "sec:" + b.sec, title: t("ss_" + b.sec), rows: [], notes: [] });
    } else if (!sec && (b.title || b.rows.length >= 3)) {
      sections.push(sec = { key: b.id, title: b.title, rows: [], notes: [] });
    } else if (!sec) {
      sec = last && last.key === "run" ? last : null;
      if (!sec) sections.push(sec = { key: "run", title: "", rows: [], notes: [] });
    }
    // O id do item: na secao que ele abre, ou na primeira linha dele.
    if (!sec.id) sec.id = b.id;
    else if (b.rows[0]) b.rows[0].dataset.item = b.id;
    byItem.set(b.id, sec);
    sec.rows.push(...b.rows);
    if (b.note) sec.notes.push(b.note);
    last = b.into ? last : sec;
  }
  return sections.map((s) => uiSection(s.title, s.rows, s.notes.join(" "), { id: s.id }));
}

// Uma caixa: a linha de carregando, e as linhas dela quando o pedido volta.
function setupBoxPart(item, label, ctx) {
  const part = el("div", { class: "part" }, uiRow({ label, control: el("span", { class: "spinner sm" }), cls: "dim-row" }));
  SETUP_BOXES[item.box](item, label, ctx).then((rows) => part.replaceChildren(...rows)).catch((e) => {
    if (e.message !== "login") part.replaceChildren(uiRow({ label, sub: e.message, cls: "error-row" }));
  });
  return part;
}

// ── A busca ──
// Os ajustes que batem viram as linhas de verdade (mudam dali mesmo); os
// itens sem ajuste (as telas do tubo, as caixas, as paginas) levam ao grupo.

function setupSearch() {
  const q = setupQuery.toLowerCase();
  const hit = (...texts) => texts.some((x) => x && String(x).toLowerCase().includes(q));
  const sections = [];
  let count = 0;
  for (const group of SETUP_TREE) {
    const rows = [];
    for (const { item, rows: mine } of setupItems(group, setupRows || [])) {
      const found = mine.filter((r) => !r.key.startsWith("deflicker.") &&
        hit(settingLabel(r), r.label, ...(r.options || []).map((o) => o.label)));
      if (found.length) {
        rows.push(...(item.id === "mode480" ? mode480Rows(mine.filter((r) => r.key.startsWith("deflicker.") || found.includes(r)))
          : found.map(settingRow)));
        count += found.length;
      } else if (hit(setupLabel(item), setupHint(item))) {
        const href = item.page ? "#system/setup/" + group.id + "/" + item.page : item.link || "#system/setup/" + group.id;
        const link = uiRow({ label: setupLabel(item), sub: setupHint(item), before: [icon(setupIcon(item))], href, control: icon("g-chev"),
          cls: "go-row" });
        link.addEventListener("click", () => {
          setupFocus = "si-" + group.id + "-" + item.id;
          setupClearSearch();
          if (location.hash === href) loadSettings().catch(() => {});
        });
        rows.push(link);
        count++;
      }
    }
    if (rows.length) sections.push(uiSection(t("sg_" + group.id), rows));
  }
  const found = !count ? t("setup_found_none") : count === 1 ? t("setup_found_1") : t("setup_found").replace("%n", count);
  $("settings").replaceChildren(setupBack("#system/setup", t("sub_setup")), el("h2", {}, t("setup_search_title")),
    el("p", { class: "lead" }, found.replace("%s", setupQuery)), ...sections);
}

function setupClearSearch() {
  if (!setupQuery) return;
  setupQuery = "";
  $("setup-q").value = "";
}

$("setup-q").addEventListener("input", () => {
  setupQuery = $("setup-q").value.trim();
  if (setupQuery) {
    $("settings").hidden = false;
    $("setup-page").hidden = true;
    $("setup").dataset.mobile = "group";
    setupNav(setupGroup().id);
    if (setupRows) setupSearch();
  } else {
    loadSettings().catch(() => {});
  }
});
// Um grupo clicado durante a busca: a busca sai (o mesmo grupo do endereco
// nao muda o endereco, entao desenha aqui).
$("setup-groups").addEventListener("click", (ev) => {
  const link = ev.target.closest("a"), searching = !!setupQuery;
  setupClearSearch();
  if (searching && link && link.getAttribute("href") === location.hash) loadSettings().catch(() => {});
});

// ── As paginas de um item ──

const SETUP_PAGES = { custom: (box) => customGamesPage(box), version: versionPage, whatsnew: whatsnewPage };

async function setupPage(group, item) {
  const box = $("setup-page");
  // Os jogos custom guardam a tabela: voltar a pagina so le a lista de novo.
  // A mesma pagina da area Jogos custom: a ultima que a abriu fica com ela.
  if (item.page === "custom" && box.dataset.page === "custom") return cgMount(box);
  box.dataset.page = item.page;
  box.replaceChildren(el("a", { class: "back show", href: "#system/setup/" + group.id }, icon("g-back"), t("sg_" + group.id)));
  return SETUP_PAGES[item.page](box);
}

// ── As linhas especiais ──

// A placa de video em uso (do /api/status) e o driver dela, em destaque; a
// troca do driver e no tubo (uma confirmacao na tela: sem imagem, o driver
// de antes volta sozinho).
function gpuRow(item) {
  const gpu = lastStatus ? statusGpu(lastStatus) : null;
  const can = !!setupInfo.items.driver;
  const hint = setupInfo.info.driver || "";
  const row = uiRow({ label: gpu ? gpuName(gpu.name) || gpu.slot : t("gpu_none"),
    before: gpu && gpu.driver ? [el("span", { class: "drvpill", title: t("gpu_driver") }, gpu.driver)] : [],
    sub: hint ? t("gpu_takes").replace("%s", (lang === "pt" && DRIVER_HINT_PT[hint]) || hint) : "",
    help: can ? t("sic_driver") : "", control: can ? uiCabGo(t("setup_swap_cab")) : "", cls: "drv wrap-ctl" });
  return can ? uiClickable(row, () => openOnCabinet(item.cabinet, t("si_driver"))) : row;
}

// Abrir no gabinete: a linha inteira, com a etiqueta "no gabinete". Num item
// com outras linhas, o nome do que abre (Grade de teste); sozinha, o do item.
function cabinetRow(item, label, others) {
  const name = others && TEXT.en["sicl_" + item.id] ? t("sicl_" + item.id) : label;
  let sub = TEXT[lang]["sic_" + item.id] || TEXT.en["sic_" + item.id] || setupHint(item);
  if (item.info === "buttons" && setupInfo.info.buttons) sub = setupInfo.info.buttons;
  if (item.info === "lpt") sub = t("now_is").replace("%s", setupInfo.info.lpt || t("ra_off"));
  if (item.info === "lowdot" && setupInfo.info.lowdot && lang !== "pt") sub = setupInfo.info.lowdot;
  return uiClickable(uiRow({ label: name, sub, control: uiCabGo(t("setup_on_cab")), cls: "cab-row" }),
    () => openOnCabinet(item.cabinet, name));
}

async function openOnCabinet(screen, label) {
  if (!(await ask({ title: label, text: t("cab_ask").replace("%s", label), yes: t("cab_open"),
    extra: { label: t("cab_watch"), href: "#live" } }))) return;
  const res = await api("/api/setup/open", { method: "POST", body: JSON.stringify({ screen }) });
  const data = await res.json().catch(() => ({}));
  // Um update trocou o tty1 com algo na tela: so depois de reiniciar.
  if (res.status === 409 && data.code === "restart") {
    if (await ask({ title: label, text: t("cab_restart"), yes: t("set_restart_now"), no: t("set_later") })) {
      const r = await api("/api/settings", { method: "POST", body: JSON.stringify({ key: "power.reboot", value: "1" }) });
      toast(r.ok ? t("set_restarting") : r.statusText, r.ok ? "ok" : "bad");
    }
    return;
  }
  toast(res.ok ? t("cab_done").replace("%s", label) : data.error || res.statusText, res.ok ? "ok" : "bad");
}
$("setup-whole").addEventListener("click", () => openOnCabinet("setup", t("setup_title")));

// ── As caixas: as linhas que vem de outro pedido ──

const SETUP_BOXES = {
  geometry: (item, label, ctx) => geometryRows(ctx),
  geometryReset: async (item, label, ctx) => {
    const g = await ctx.json("/api/geometry");
    const go = uiButton(settingActionLabel({ key: "color.reset" }), async () => {
      if (!(await ask({ title: t("geo_reset"), text: t("geo_reset_text"), yes: t("geo_reset") }))) return;
      const r = await api("/api/geometry", { method: "POST", body: JSON.stringify({ action: "reset" }) });
      toast(r.ok ? t("geo_was_reset") : r.statusText, r.ok ? "ok" : "bad");
      loadSettings().catch(() => {});
    });
    go.disabled = !g.range;
    return [uiRow({ label, sub: t("sih_geometry_reset"), control: go })];
  },
  volume: async () => [volumeRow(await (await api("/api/volume")).json())],
  wifi: () => wifiRows(),
  password: async () => [passwordRow()],
  frontends: () => frontendsRows(),
  folders: () => folderRows(""),
  quirks: () => quirksRows(),
  bluetooth: () => bluetoothRows(),
  osd: () => osdProfileRows(),
  sounds: () => menuSoundRows(),
  romlist: async (item, label) => {
    if (!setupInfo.items.romlist) return [uiRow({ label, sub: t("rl_missing") })];
    return [uiRow({ label, sub: setupHint(item), help: t("rl_note"),
      control: uiButton(t("rl_go"), (b) => setupTask("attract-romlist", label, b)) })];
  },
  update: async (item, label) => [uiRow({ label, sub: setupHint(item), help: t("up_note"), control: uiButton(t("up_go"), async (b) => {
    if (await ask({ title: label, text: t("up_ask"), yes: t("up_run") })) await setupTask("system-update", label, b, t("up_done"));
  }) })],
};

// ── As tarefas ──

// waitTask: espera a tarefa terminar (onTick a cada volta); null se ela
// sumiu.
async function waitTask(id, onTick) {
  let task = { running: true };
  while (task.running) {
    await sleep(1500);
    const res = await api("/api/task?id=" + id);
    if (!res.ok) return null;
    task = await res.json();
    if (onTick) onTick(task);
  }
  return task;
}

async function setupTask(name, label, button, done) {
  if (button) button.disabled = true;
  try {
    const res = await api("/api/setup/task", { method: "POST", body: JSON.stringify({ name }) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return toast(data.error || res.statusText, "bad");
    toast(t("task_started").replace("%s", label));
    taskNext = 0;
    const task = await waitTask(data.id);
    if (task && task.rc === 0) toast(done || task.step || label, "ok");
    else if (task) toast(t("task_failed").replace("%s", label).replace("%s", task.error || task.last || task.rc), "bad");
  } finally {
    if (button) button.disabled = false;
  }
}

// ── Audio > Volume ──

function volumeRow(vol) {
  if (vol.percent == null) return uiRow({ label: t("volume"), sub: t("not_installed") });
  const range = el("input", { type: "range", min: "0", max: "100", step: "5", value: String(vol.percent || 0),
    "aria-label": t("volume") });
  const shown = el("output", { class: "val" }, (vol.percent || 0) + "%");
  const mute = uiIconButton(vol.muted ? "g-mute" : "g-volume", t("mute"), () => send({ action: "mute" }));
  mute.setAttribute("aria-pressed", String(!!vol.muted));
  const send = async (body) => {
    const res = await api("/api/volume", { method: "POST", body: JSON.stringify(body) });
    const now = await res.json().catch(() => ({}));
    if (now.percent != null) {
      range.value = now.percent;
      shown.textContent = now.percent + "%";
    }
    mute.setAttribute("aria-pressed", String(!!now.muted));
    mute.replaceChildren(icon(now.muted ? "g-mute" : "g-volume"));
  };
  range.addEventListener("input", () => { shown.textContent = range.value + "%"; });
  range.addEventListener("change", () => send({ set: Number(range.value) }).catch(() => {}));
  return uiRow({ label: t("volume"), control: el("div", { class: "slider" }, mute, range, shown), cls: "has-slider" });
}

// ── Audio > Menu sounds: os dois .wav ──
// O arquivo enviado (ouvir, trocar, tirar) ou o vazio; um .wav arrastado
// para a linha tambem vale.

async function menuSoundRows() {
  const data = await (await api("/api/sounds")).json();
  return ["move", "select"].map((which) => menuSoundRow(which, (data.sounds || {})[which]));
}

function menuSoundRow(which, have) {
  const file = which + ".wav";
  const input = el("input", { type: "file", accept: ".wav,audio/wav,audio/x-wav", hidden: "" });
  let row = null;
  const redraw = (sounds) => row.replaceWith(menuSoundRow(which, (sounds || {})[which]));
  const send = async (f) => {
    if (!f) return;
    if (!/\.wav$/i.test(f.name) || f.size > 2 << 20) return toast(t("snd_only_wav"), "bad");
    const res = await cgPostFile("/api/sounds/upload?which=" + which, f, null, true);
    if (res.status !== 200) return toast((res.data && res.data.error) || t("snd_only_wav"), "bad");
    toast(t("snd_sent").replace("%s", file), "ok");
    redraw(res.data.sounds);
  };
  input.addEventListener("change", () => {
    const f = input.files[0];
    input.value = "";
    send(f).catch(() => {});
  });
  const controls = [input];
  if (have) {
    controls.push(uiIconButton("g-play", t("snd_play").replace("%s", file), async () => {
      await new Audio("/api/sounds/file?which=" + which + "&t=" + have.mtime).play().catch(() => {});
    }));
  }
  controls.push(uiButton(t(have ? "snd_swap" : "snd_send"), () => input.click()));
  if (have) {
    controls.push(uiIconButton("g-close", t("snd_remove").replace("%s", file), async () => {
      if (!(await ask({ title: file, text: t("snd_remove_ask").replace("%s", file), yes: t("fe_delete"), danger: true }))) return;
      const r = await api("/api/sounds", { method: "POST", body: JSON.stringify({ action: "delete", which }) });
      const out = await r.json().catch(() => ({}));
      if (!r.ok) return toast(out.error || r.statusText, "bad");
      toast(t("snd_removed").replace("%s", file), "ok");
      redraw(out.sounds);
    }));
  }
  const sub = have ? el("span", {}, el("span", { class: "wav" }, "WAV"), " " + file + " · " + bytes(have.size)) : t("snd_none");
  row = uiRow({ label: t("snd_" + which), sub, control: controls, cls: "snd" });
  row.addEventListener("dragover", (ev) => { ev.preventDefault(); row.classList.add("drop-on"); });
  row.addEventListener("dragleave", () => row.classList.remove("drop-on"));
  row.addEventListener("drop", (ev) => {
    ev.preventDefault();
    row.classList.remove("drop-on");
    send(ev.dataTransfer.files[0]).catch(() => {});
  });
  return row;
}

// ── Video > On-screen menu: os perfis gravados na OSD ──
// O tipo numa etiqueta (jogo, core, emulador, resolucao, padrao), o que
// muda numa linha; a seta abre os ajustes, o x apaga (o que ele mudava volta
// ao perfil de baixo). O padrao nao se apaga.

async function osdProfileRows() {
  const data = await (await api("/api/osd/profiles")).json();
  const profiles = data.profiles || [];
  return profiles.length ? profiles.map(osdProfileRow) : [uiRow({ label: t("osd_none"), cls: "dim-row" })];
}

function osdKeyLabel(key) {
  if (key.startsWith("level.")) return t("osd_level").replace("%s", key.slice(6));
  const row = (setupRows || []).find((r) => r.key === key);
  return row ? settingLabel(row) : (lang === "pt" && SETTING_NAMES_PT[key]) || key;
}

function osdValue(key, value) {
  if (key.startsWith("level.")) return TEXT.en["m480_" + value] ? t("m480_" + value) : value;
  const row = (setupRows || []).find((r) => r.key === key);
  if (row && row.options) {
    const o = settingOptions(row).find((x) => x.value === value);
    if (o) return o.label;
  }
  if ((row && row.type === "number") || /^(color|scanline|gun)\./.test(key)) return /^-?\d+(\.\d+)?$/.test(value) ? prettyNumber(key, value) : value;
  return value;
}

function osdProfileRow(p) {
  const name = p.kind === "default" ? t("osd_all") : p.name;
  const values = Object.entries(p.values);
  const where = { game: p.where + "/" + p.name, core: t("osd_core_sub").replace("%s", p.name),
    emulator: t("osd_emu_sub").replace("%s", p.name), resolution: t("osd_res_sub").replace("%s", p.name),
    default: t("osd_default_sub") }[p.kind];
  const list = el("div", { class: "kv-list", hidden: "" }, ...values.map(([k, v]) =>
    el("div", {}, el("span", {}, osdKeyLabel(k)), el("b", { class: "val" }, osdValue(k, v)))));
  const open = uiIconButton("g-chevd", t("osd_open").replace("%s", name), (b) => {
    list.hidden = !list.hidden;
    b.classList.toggle("up", !list.hidden);
  });
  const controls = [open];
  let row = null;
  if (p.kind !== "default") {
    controls.push(uiIconButton("g-close", t("osd_delete").replace("%s", name), async () => {
      const below = t(p.kind === "game" ? "osd_below_game" : "osd_below_other");
      if (!(await ask({ title: t("osd_delete_title").replace("%s", name), text: t("osd_delete_ask").replace("%s", below),
        yes: t("fe_delete"), danger: true }))) return;
      const r = await api("/api/osd/profiles", { method: "POST", body: JSON.stringify({ action: "delete", scope: p.scope }) });
      const out = await r.json().catch(() => ({}));
      toast(r.ok ? t("osd_deleted").replace("%s", name) : out.error || r.statusText, r.ok ? "ok" : "bad");
      if (r.ok) row.remove();
    }));
  }
  row = uiRow({ label: name, before: [el("span", { class: "kind k-" + p.kind }, t("osd_k_" + p.kind))],
    sub: where + " · " + values.map(([k, v]) => osdKeyLabel(k) + " " + osdValue(k, v)).join(", "),
    control: controls, after: [list], cls: "prof" });
  return row;
}

// ── Games > Frontend: os frontends da pessoa ──

async function frontendsRows() {
  const data = await (await api("/api/frontends")).json();
  const form = (fe) => {
    const label = uiField({ type: "text", value: fe ? fe.label : "", placeholder: t("fe_label"), "aria-label": t("fe_label"),
      maxlength: "80" });
    const command = uiField({ type: "text", class: "fld code-txt", value: fe ? fe.command : "", placeholder: t("fe_cmd"),
      "aria-label": t("fe_cmd"), spellcheck: "false" });
    const save = el("button", { type: "submit", class: "btn small" }, t("fe_save"));
    const box = el("form", { class: "srow-form", hidden: "" }, label, command, el("div", { class: "srow-form-foot" }, save));
    box.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      save.disabled = true;
      try {
        const res = await api("/api/frontends", { method: "POST", body: JSON.stringify({ action: "save",
          name: fe ? fe.name : "", label: label.value.trim(), command: command.value.trim() }) });
        const out = await res.json().catch(() => ({}));
        toast(res.ok ? t("fe_saved").replace("%s", label.value.trim()) : out.error || res.statusText, res.ok ? "ok" : "bad");
        if (res.ok) loadSettings().catch(() => {});
      } finally {
        save.disabled = false;
      }
    });
    return box;
  };
  const rows = (data.frontends || []).map((fe) => {
    const edit = form(fe);
    return uiRow({ label: fe.label, sub: fe.command + (fe.installed ? "" : " · " + t("fe_missing")), mono: true, after: [edit], control: [
      uiIconButton("✎", t("fe_edit") + ": " + fe.label, () => { edit.hidden = !edit.hidden; }),
      uiIconButton("g-trash", t("fe_delete") + ": " + fe.label, async () => {
        if (!(await ask({ title: fe.label, text: t("fe_delete_ask").replace("%s", fe.label), yes: t("fe_delete"), danger: true }))) return;
        const res = await api("/api/frontends", { method: "POST", body: JSON.stringify({ action: "delete", name: fe.name }) });
        if (!res.ok) toast((await res.json().catch(() => ({}))).error || res.statusText, "bad");
        loadSettings().catch(() => {});
      })] });
  });
  const add = form(null);
  rows.push(uiRow({ label: t("fe_add"), sub: rows.length ? "" : t("fe_none"), after: [add],
    control: uiButton(t("fe_add_go"), () => { add.hidden = !add.hidden; }) }));
  return rows;
}

// ── Games > Folders ──
// Cada pasta de ~ numa linha: trocar por uma de outro disco, desfazer, e as
// pastas de dentro (abertas embaixo, um pouco para dentro).

async function folderRows(path) {
  const data = await (await api("/api/folders?path=" + encodeURIComponent(path))).json();
  return (data.folders || []).map((f) => {
    const state = { default: "fo_default", custom: "fo_custom", offline: "fo_offline", missing: "fo_missing" }[f.state] || "fo_default";
    const controls = [];
    let row = null, inner = null;
    if (f.inner) {
      controls.push(uiIconButton("g-chevd", t("fo_inner") + ": ~/" + f.path, async (b) => {
        if (inner) {
          const show = inner[0].hidden;
          inner.forEach((r) => { r.hidden = !show; });
          b.classList.toggle("up", show);
          return;
        }
        inner = await folderRows(f.path);
        inner.forEach((r) => r.classList.add("inner"));
        if (inner.length) row.after(...inner);
        b.classList.add("up");
      }));
    }
    controls.push(uiButton(t("fo_link_go"), () => folderLink(f.path, data.start)));
    if (f.state === "custom" || f.state === "offline") controls.push(uiButton(t("fo_unlink_go"), () => folderUnlink(f.path), "quiet"));
    row = uiRow({ label: "~/" + f.path, sub: [t(state), f.target].filter(Boolean).join(" · "), help: f.about, control: controls,
      cls: f.state === "offline" ? "warn-row" : "" });
    return row;
  });
}

async function folderLink(rel, start) {
  const target = await pickFolder({ title: t("fo_pick").replace("%s", rel), start });
  if (!target) return;
  if (!(await ask({ title: "~/" + rel, text: t("fo_link_ask").replace("%s", target).replace(/%s/g, rel), yes: t("fo_link") }))) return;
  const res = await api("/api/folders", { method: "POST", body: JSON.stringify({ action: "link", path: rel, target }) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return toast(data.error || res.statusText, "bad");
  toast(t("fo_linked").replace("%s", rel).replace("%s", target) + (data.kept ? " " + t("fo_kept").replace("%s", data.kept) : ""), "ok");
  loadSettings().catch(() => {});
}

async function folderUnlink(rel) {
  if (!(await ask({ title: "~/" + rel, text: t("fo_unlink_ask").replace("%s", rel), yes: t("fo_unlink") }))) return;
  const res = await api("/api/folders", { method: "POST", body: JSON.stringify({ action: "unlink", path: rel }) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return toast(data.error || res.statusText, "bad");
  toast(t(data.new ? "fo_new" : "fo_back").replace("%s", rel), "ok");
  loadSettings().catch(() => {});
}

// ── System > Quirks ──

const QUIRK_KINDS = [["hid40", ":0x40"], ["hid8", ":0x8"], ["hid400", ":0x400"], ["uas", "u"], ["custom", ""]];

async function quirksRows() {
  const data = await (await api("/api/quirks")).json();
  const rows = (data.quirks || []).map((q) => uiRow({ label: q.name, sub: q.code, mono: true,
    control: uiIconButton("g-trash", t("fe_delete") + ": " + q.name, async () => {
      if (!(await ask({ title: q.name, text: t("qk_delete_ask").replace("%s", q.name + " (" + q.code + ")"), yes: t("fe_delete"),
        danger: true }))) return;
      const res = await api("/api/quirks", { method: "POST", body: JSON.stringify({ action: "delete", code: q.code }) });
      const out = await res.json().catch(() => ({}));
      toast(res.ok ? t("qk_deleted") : out.error || res.statusText, res.ok ? "ok" : "bad");
      loadSettings().catch(() => {});
    }) }));
  const name = uiField({ type: "text", placeholder: t("qk_name"), "aria-label": t("qk_name"), maxlength: "80" });
  const device = el("select", { class: "fld", "aria-label": t("qk_device") }, el("option", { value: "" }, t("qk_device_none")),
    ...(data.devices || []).map((d) => el("option", { value: d.id }, d.id + "  " + d.name)));
  const kind = el("select", { class: "fld", "aria-label": t("qk_kind") }, ...QUIRK_KINDS.map(([k]) => el("option", { value: k }, t("qk_" + k))));
  const code = uiField({ type: "text", class: "fld code-txt", placeholder: "0x16c0:0x05e1:0x40", "aria-label": t("qk_code"), spellcheck: "false" });
  // O codigo sai do aparelho e da correcao (o do disco sem 0x).
  const fill = () => {
    const id = device.value, k = QUIRK_KINDS.find(([x]) => x === kind.value);
    if (!id || kind.value === "custom") return;
    code.value = kind.value === "uas" ? id.replace(/0x/g, "") + ":u" : id + k[1];
    if (!name.value) name.value = (device.selectedOptions[0].textContent.split("  ")[1] || "").slice(0, 60);
  };
  device.addEventListener("change", fill);
  kind.addEventListener("change", fill);
  const add = el("button", { type: "submit", class: "btn small" }, t("qk_add"));
  const form = el("form", { class: "srow-form", hidden: "" }, name, device, kind, code, el("div", { class: "srow-form-foot" }, add));
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    add.disabled = true;
    try {
      const res = await api("/api/quirks", { method: "POST", body: JSON.stringify({ action: "add", name: name.value.trim(),
        code: code.value.trim() }) });
      const out = await res.json().catch(() => ({}));
      toast(res.ok ? t("qk_saved") : out.error || res.statusText, res.ok ? "ok" : "bad");
      if (res.ok) loadSettings().catch(() => {});
    } finally {
      add.disabled = false;
    }
  });
  rows.push(uiRow({ label: t("qk_add"), sub: rows.length ? "" : t("qk_none"), after: [form],
    control: uiButton(t("qk_add_go"), () => { form.hidden = !form.hidden; }) }));
  return rows;
}

// ── Joysticks > Bluetooth ──

async function bluetoothRows() {
  const data = await (await api("/api/bluetooth")).json();
  const act = async (action, d) => {
    if (action === "remove" && !(await ask({ title: d.name, text: t("bt_forget_ask").replace("%s", d.name), yes: t("bt_forget"),
      danger: true }))) return;
    if (action === "pair") toast(t("bt_pairing").replace("%s", d.name));
    const res = await api("/api/bluetooth", { method: "POST", body: JSON.stringify({ action, mac: d.mac }) });
    const out = await res.json().catch(() => ({}));
    if (!res.ok) return toast(out.error || res.statusText, "bad");
    if (action === "pair") toast(t("bt_paired_ok").replace("%s", d.name), "ok");
    loadSettings().catch(() => {});
  };
  const device = (d, actions) => uiRow({ label: d.name,
    sub: [d.mac, d.connected ? t("bt_connected") : d.paired ? t("bt_paired") : ""].filter(Boolean).join(" · "),
    control: actions.map(([action, label]) => (action === "remove" ? uiIconButton("g-trash", t(label) + ": " + d.name, () => act(action, d))
      : uiButton(t(label), () => act(action, d)))) });
  const power = uiRow({ label: t("bt_power"), sub: data.adapter || "", control: uiSwitch(!!data.powered, t("bt_power"), async (on) => {
    const r = await api("/api/bluetooth", { method: "POST", body: JSON.stringify({ action: "power", on }) });
    loadSettings().catch(() => {});
    return r.ok;
  }) });
  const paired = (data.devices || []).map((d) => device(d, [d.connected ? ["disconnect", "bt_disconnect"] : ["connect", "bt_connect"],
    ["remove", "bt_forget"]]));
  let found = [];
  const go = uiButton(t("bt_scan_go"), async () => {
    found.forEach((n) => n.remove());
    found = [uiRow({ label: t("bt_scanning"), cls: "dim-row" })];
    scan.after(...found);
    const res = await api("/api/bluetooth?scan=1");
    const out = await res.json().catch(() => ({}));
    const fresh = (out.found || []).filter((d) => !d.paired);
    found.forEach((n) => n.remove());
    found = fresh.length ? fresh.map((d) => device(d, [["pair", "bt_pair"]])) : [uiRow({ label: t("bt_found_none"), cls: "dim-row" })];
    scan.after(...found);
  });
  go.disabled = !data.powered;
  const scan = uiRow({ label: t("bt_scan"), sub: paired.length ? "" : t("bt_none"), control: go });
  return [power, ...paired, scan];
}

// ── Escolher uma pasta (Folders, Importar de uma pasta, Pastas compactadas) ──
// O dialogo do painel com as pastas do gabinete (/api/dirs): os lugares de
// sempre (start, os discos montados, ~/roms), depois a arvore. Resolve com o
// caminho, ou null.

let pickDialog = null;
function pickFolder({ title, start = "", extra = [] }) {
  if (!pickDialog) {
    pickDialog = el("dialog", { class: "ask pick" });
    document.body.append(pickDialog);
  }
  const dlg = pickDialog;
  return new Promise((resolve) => {
    let chosen = null;
    const show = async (path) => {
      const res = await api("/api/dirs?path=" + encodeURIComponent(path || ""));
      // A pasta de comeco que nao existe (um gabinete sem ~/games): os lugares.
      if (!res.ok && path && path === start) return show("");
      const data = await res.json().catch(() => ({}));
      const list = el("div", { class: "pick-list" });
      const go = (label, to) => {
        const b = el("button", { type: "button", class: "pick-dir", title: to }, label);
        b.addEventListener("click", () => show(to).catch(() => {}));
        list.append(b);
      };
      if (!res.ok) list.append(el("p", { class: "error" }, data.error || res.statusText));
      else if (!data.path) {
        for (const place of [start, ...extra, ...(data.places || [])].filter((p, i, all) => p && all.indexOf(p) === i)) {
          go("💾 " + place, place);
        }
        go("📁 /", "/");
      } else {
        go("⬆ " + t("cg_up"), data.parent || "");
        (data.dirs || []).forEach((name) => go("📁 " + name, (data.path === "/" ? "" : data.path) + "/" + name));
      }
      const places = el("button", { type: "button", class: "btn ghost small" }, icon("px-disk"), t("cg_places"));
      places.addEventListener("click", () => show("").catch(() => {}));
      const use = el("button", { type: "button", class: "btn" }, icon("px-ok"), t("cg_use_folder"));
      use.disabled = !data.path;
      use.addEventListener("click", () => { chosen = data.path; dlg.close(); });
      const cancel = el("button", { type: "button", class: "btn ghost" }, t("cancel"));
      cancel.addEventListener("click", () => dlg.close());
      dlg.replaceChildren(el("h3", {}, title || t("cg_folder_title")), data.path ? el("p", { class: "pick-path" }, data.path) : "",
        list, el("footer", {}, places, el("span", { class: "grow" }), cancel, use));
    };
    dlg.onclose = () => resolve(chosen);
    show(start).then(() => { if (!dlg.open) dlg.showModal(); }).catch(() => resolve(null));
  });
}
