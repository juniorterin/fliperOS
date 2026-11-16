// Sistema > Setup: a arvore inteira do Setup do gabinete, na mesma ordem e
// com os mesmos itens (os ui_menu_hints de fliperos-setup/screens). Cada item
// mostra o que da para mudar daqui (os ajustes do --settings, as caixas de
// system.js e as daqui) e, quando o passo precisa do tubo ou do controle na
// mao, "Abrir no gabinete" (fliperos-setup --screen, screens/panel.sh).
// O endereco e #system/setup/GRUPO; Jogos custom e #system/setup/games/custom
// (customgames.js).
"use strict";

// Os grupos e os itens. id: o do menu do Setup (o teste de paridade confere
// os dois lados); also: outros itens do Setup que este cobre; keys: as chaves
// do --settings (exatas, ou o comeco quando terminam em "."); box: uma caixa;
// link: outra pagina do painel; page: uma pagina daqui; cabinet: a tela do
// Setup aberta no gabinete; when: so com esse item no gabinete
// (--setup-items); info: o texto do --setup-items que vai junto; extra: so do
// painel (nao e um item do menu do Setup).
const SETUP_TREE = [
  { id: "video", icon: "px-video", items: [
    { id: "monitor", keys: ["monitor", "video.previous"] },
    { id: "orientation", keys: ["orientation"] },
    { id: "resolution", keys: ["resolution"], cabinet: "resolution" },
    { id: "geometry", box: "geometry", cabinet: "geometry" },
    { id: "geometry_reset", box: "geometryReset" },
    { id: "monitors", keys: ["mm_games"], cabinet: "monitors" },
    { id: "mode480", keys: ["mode480.", "deflicker."] },
    { id: "colour", keys: ["color."], cabinet: "colour" },
    { id: "scanlines", keys: ["scanlines", "scanline."], cabinet: "scanlines", when: "scanlines" },
    { id: "retest", cabinet: "outputs" },
    { id: "driver", cabinet: "driver", when: "driver", info: "driver" },
    { id: "lowdot", cabinet: "lowdot", when: "lowdot", info: "lowdot" },
    { id: "firmware", cabinet: "firmware", when: "firmware" },
    { id: "osd", keys: ["osd"], extra: true },
  ] },
  { id: "audio", icon: "px-audio", items: [
    { id: "card", keys: ["audio_card"] },
    { id: "volume", box: "volume" },
    { id: "mixer", cabinet: "mixer" },
    { id: "latency", label: "mame_latency", keys: ["mame_latency"] },
    { id: "test", keys: ["audio.test"] },
    { id: "sounds", keys: ["menu_sounds"] },
  ] },
  { id: "network", icon: "px-network", items: [
    { id: "wifi", also: ["hidden", "status"], box: "wifi" },
    { id: "live", keys: ["stream_audio", "stream_quality", "marquee_overlay"], extra: true },
  ] },
  { id: "games", icon: "px-games", items: [
    { id: "emulators", link: "#library/install" },
    { id: "frontend", keys: ["launcher"], box: "frontends" },
    { id: "extras", link: "#library/install" },
    { id: "custom", page: "custom" },
    { id: "folders", box: "folders" },
    { id: "downloader", link: "#library/downloads" },
    { id: "cleaner", link: "#library/romfilter" },
    { id: "scraper", link: "#library/art" },
    { id: "romlist", box: "romlist" },
  ] },
  { id: "joysticks", icon: "px-joysticks", items: [
    { id: "buttons", cabinet: "buttons", info: "buttons" },
    { id: "bluetooth", box: "bluetooth", cabinet: "bluetooth", when: "bluetooth" },
    { id: "layout", cabinet: "layout" },
    { id: "guncon", keys: ["gun_flash", "gun.", "gun_offscreen_reload"], cabinet: "guncon" },
    { id: "axes", cabinet: "axes" },
    { id: "padcolor", keys: ["padcolor"] },
    { id: "lpt", cabinet: "lpt", info: "lpt" },
  ] },
  { id: "system", icon: "px-system", items: [
    { id: "latency", keys: ["latency"], cabinet: "latency" },
    { id: "services", keys: ["service."] },
    { id: "quirks", box: "quirks" },
    { id: "password", box: "password" },
    { id: "cabinetname", keys: ["cabinet_name"] },
    { id: "update", box: "update" },
    { id: "version", box: "version" },
    { id: "whatsnew", box: "whatsnew" },
    { id: "debug", keys: ["debug"] },
    { id: "lab", link: "#system/lab" },
    { id: "oscr", cabinet: "oscr" },
    { id: "splash", keys: ["splash"] },
    { id: "power", keys: ["power."], extra: true },
  ] },
  { id: "cloud", icon: "px-cloud", items: [
    { id: "cloud", link: "#system/cloud" },
  ] },
];

// Os icones dos itens sem um px-ID proprio: os mesmos do carrossel do Setup
// (fliperos-setup/gui/theme.py).
const SETUP_ICON = { monitor: "px-video", geometry_reset: "px-reset", monitors: "px-outputs", driver: "px-chip",
  lowdot: "px-outputs", osd: "px-layout", card: "px-system", volume: "px-audio", test: "px-audio", sounds: "px-audio",
  wifi: "px-network", live: "px-outputs", extras: "px-freeroms", custom: "px-games", folders: "px-dest",
  downloader: "px-install", cleaner: "px-filter", update: "px-reset", version: "px-reset", whatsnew: "px-romlist",
  splash: "px-video", other: "px-setup" };
// Os grupos do --settings, para um ajuste novo que nenhum item pega (ele vai
// para "Outros ajustes" do grupo dele: nada some).
const SETUP_ROW_GROUP = { Video: "video", Colour: "video", Scanlines: "video", "Interlaced hacks": "video",
  Audio: "audio", "GunCon 2": "joysticks", Joysticks: "joysticks", "Live screen": "network" };

// O caminho dentro do Setup (app.js o poe: #system/setup/GRUPO/PAGINA).
let setupPath = "";
let setupInfo = { items: {}, info: {} };
// Os itens abertos ficam abertos ao voltar (um ajuste recarrega o grupo).
const setupOpenItems = new Set();

const setupKeyMatch = (keys, key) => (keys || []).some((k) => key === k || (k.endsWith(".") && key.startsWith(k)));
const setupGroup = () => SETUP_TREE.find((g) => g.id === (setupPath || "").split("/")[0]) || SETUP_TREE[0];
const setupLabel = (item) => (item.id === "other" ? t("setup_other") : t("si_" + (item.label || item.id)));
const sleep = (ms) => new Promise((done) => setTimeout(done, ms));

function setupHint(item) {
  if (item.info && setupInfo.info[item.info] && (item.id === "driver" || item.id === "lowdot")) return setupInfo.info[item.info];
  return item.id === "other" ? "" : t("sih_" + (item.label || item.id));
}

function setupIcon(item) {
  return SETUP_ICON[item.id] || "px-" + item.id;
}

// loadSettings: o grupo do endereco (o nome antigo: app.js e as caixas de
// system.js chamam esta funcao depois de cada mudanca).
async function loadSettings() {
  const group = setupGroup();
  const page = (setupPath || "").split("/")[1] === "custom" && group.id === "games";
  setupNav(group.id);
  $("settings").hidden = page;
  $("setup-page").hidden = !page;
  if (page) {
    const back = el("a", { class: "btn ghost small setup-back", href: "#system/setup/games" }, icon("g-back"),
      t("setup_back").replace("%s", t("sg_games")));
    if (!$("setup-page").dataset.page) {
      $("setup-page").dataset.page = "custom";
      $("setup-page").replaceChildren(back);
      return customGamesPage($("setup-page"));
    }
    return cgLoad();
  }
  delete $("setup-page").dataset.page;
  $("setup-page").replaceChildren();
  if (!$("settings").children.length) $("settings").replaceChildren(el("p", { class: "dim" }, t("setup_loading")));
  let rows;
  try {
    const [settingsRes, itemsRes] = await Promise.all([api("/api/settings"), api("/api/setup/items")]);
    rows = (await settingsRes.json()).settings || [];
    setupInfo = itemsRes.ok ? await itemsRes.json() : { items: {}, info: {} };
  } catch (e) {
    if (e.message !== "login") $("settings").replaceChildren(el("p", { class: "error" }, t("setup_error").replace("%s", e.message)));
    return;
  }
  // Mudou de grupo enquanto o Setup respondia: o outro desenha.
  if (setupGroup() !== group || $("settings").hidden) return;
  const items = [];
  for (const item of group.items) {
    if (item.when && !setupInfo.items[item.when]) continue;
    const mine = rows.filter((r) => setupKeyMatch(item.keys, r.key));
    // Um item so de ajustes que este gabinete nao tem (a tela ao vivo sem o
    // go2rtc ainda tem o marquee; as scanlines a 15 kHz ficam de fora).
    if (item.keys && !mine.length && !item.box && !item.cabinet) continue;
    items.push(setupItem(group, item, mine));
  }
  const known = (r) => SETUP_TREE.some((g) => g.items.some((i) => setupKeyMatch(i.keys, r.key)));
  const other = rows.filter((r) => !known(r) && (SETUP_ROW_GROUP[r.group] || "system") === group.id);
  if (other.length) items.push(setupItem(group, { id: "other" }, other));
  $("settings").replaceChildren(...items);
}

// Os sete grupos no alto, como o menu do Setup.
function setupNav(current) {
  $("setup-groups").replaceChildren(...SETUP_TREE.map((g) => el("a", {
    href: "#system/setup/" + g.id, class: "sg" + (g.id === current ? " on" : ""),
    "aria-current": g.id === current ? "page" : "false",
  }, icon(g.icon), el("span", {}, el("b", {}, t("sg_" + g.id)), el("small", {}, t("sgh_" + g.id))))));
}

function setupItem(group, item, rows) {
  const label = setupLabel(item);
  const head = [icon(setupIcon(item)), el("span", { class: "si-text" }, el("b", {}, label),
    el("small", {}, setupHint(item)))];
  // Outra pagina (do painel ou daqui): o item e um link.
  if (item.link || item.page) {
    const href = item.page ? "#system/setup/" + group.id + "/" + item.page : item.link;
    return el("a", { class: "setup-item setup-link", href, id: "si-" + group.id + "-" + item.id }, ...head,
      icon("g-chev"));
  }
  const key = group.id + "/" + item.id;
  const details = el("details", { class: "setup-item", id: "si-" + group.id + "-" + item.id },
    el("summary", {}, ...head, item.cabinet && !rows.length && !item.box ? el("span", { class: "tag cab-tag" }, icon("px-arcade"))
      : ""));
  const body = el("div", { class: "si-body si-" + item.id });
  details.append(body);
  let built = false;
  const build = async () => {
    if (built) return;
    built = true;
    body.replaceChildren(el("div", { class: "setting dim" }, "…"));
    try {
      body.replaceChildren(...(await setupBody(item, rows, label)));
    } catch (e) {
      built = false;
      if (e.message !== "login") body.replaceChildren(el("div", { class: "setting error" }, e.message));
    }
  };
  details.addEventListener("toggle", () => {
    if (details.open) {
      setupOpenItems.add(key);
      build();
    } else setupOpenItems.delete(key);
  });
  if (setupOpenItems.has(key)) {
    details.open = true;
    build();
  }
  return details;
}

// O corpo de um item: o texto do gabinete, os ajustes, a caixa e o Abrir no
// gabinete, nessa ordem.
async function setupBody(item, rows, label) {
  const out = [];
  const info = item.info ? setupInfo.info[item.info] : null;
  if (item.info === "buttons" && info) out.push(el("div", { class: "setting" }, el("div", { class: "dim" }, info)));
  if (item.info === "lpt") {
    out.push(el("div", { class: "setting" }, el("div", { class: "dim" }, t("now_is").replace("%s", info || t("ra_off")))));
  }
  if (item.id === "mode480") out.push(...mode480Rows(rows));
  else out.push(...rows.map(settingRow));
  if (item.box) out.push(...(await SETUP_BOXES[item.box](item, label)));
  if (item.cabinet) out.push(cabinetRow(item, label));
  return out;
}

// unwrap: as caixas de system.js vem num <details> (o Setup de antes, um
// grupo por caixa); aqui o item ja e o grupo.
function unwrap(details) {
  details.open = true;
  return [...details.childNodes].filter((n) => n.nodeName !== "SUMMARY");
}

const SETUP_BOXES = {
  geometry: async () => unwrap(await geometryBox()),
  geometryReset: async () => {
    const g = await (await api("/api/geometry")).json();
    const button = el("button", { type: "button", class: "btn ghost" }, icon("px-reset"), t("geo_reset"));
    button.disabled = !g.range;
    button.addEventListener("click", async () => {
      if (!(await ask({ title: t("geo_reset"), text: t("geo_reset_text"), yes: t("geo_reset") }))) return;
      const r = await api("/api/geometry", { method: "POST", body: JSON.stringify({ action: "reset" }) });
      toast(r.ok ? t("geo_was_reset") : r.statusText, r.ok ? "ok" : "bad");
      loadSettings().catch(() => {});
    });
    return [el("div", { class: "setting" }, button, el("div", { class: "dim" }, t(g.range ? "geo_custom" : "geo_preset") +
      " · " + (g.label || g.monitor || "")))];
  },
  volume: async () => [volumeSetting(await (await api("/api/volume")).json())],
  wifi: async () => unwrap(await wifiBox()),
  password: async () => unwrap(passwordBox()),
  version: async () => { openGroups.add("Version"); return unwrap(versionBox()); },
  whatsnew: async () => { openGroups.add("Whatsnew"); return unwrap(whatsnewBox()); },
  frontends: frontendsBox,
  folders: async () => [await foldersBox("")],
  quirks: quirksBox,
  bluetooth: bluetoothBox,
  romlist: async (item, label) => {
    if (!setupInfo.items.romlist) return [el("div", { class: "setting" }, el("div", { class: "dim" }, t("rl_missing")))];
    const run = el("button", { type: "button", class: "btn" }, icon("px-romlist"), t("rl_run"));
    run.addEventListener("click", () => setupTask("attract-romlist", label, run));
    return [el("div", { class: "setting" }, el("div", { class: "row start" }, run), el("div", { class: "dim" }, t("rl_note")))];
  },
  update: async (item, label) => {
    const run = el("button", { type: "button", class: "btn" }, icon("px-install"), t("up_run"));
    run.addEventListener("click", async () => {
      if (await ask({ title: label, text: t("up_ask"), yes: t("up_run") })) setupTask("system-update", label, run, t("up_done"));
    });
    return [el("div", { class: "setting" }, el("div", { class: "row start" }, run), el("div", { class: "dim" }, t("up_note")))];
  },
};

// ── Abrir no gabinete ──

function cabinetRow(item, label) {
  const open = el("button", { type: "button", class: "btn ghost" }, icon("px-arcade"), t("cab_open"));
  open.addEventListener("click", () => openOnCabinet(item.cabinet, label));
  const hint = TEXT[lang]["sic_" + item.id] || TEXT.en["sic_" + item.id] || "";
  return el("div", { class: "setting cab-row" },
    el("div", { class: "row start" }, open, el("a", { class: "btn ghost small", href: "#live" }, icon("g-camera"), t("cab_watch"))),
    hint ? el("div", { class: "dim" }, hint) : "");
}

async function openOnCabinet(screen, label) {
  if (!(await ask({ title: label, text: t("cab_ask").replace("%s", label), yes: t("cab_open") }))) return;
  const res = await api("/api/setup/open", { method: "POST", body: JSON.stringify({ screen }) });
  const data = await res.json().catch(() => ({}));
  toast(res.ok ? t("cab_done").replace("%s", label) : data.error || res.statusText, res.ok ? "ok" : "bad");
}
$("setup-whole").addEventListener("click", () => openOnCabinet("setup", t("setup_title")));

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

function volumeSetting(vol) {
  const range = el("input", { type: "range", min: "0", max: "100", step: "5", value: String(vol.percent || 0),
    "aria-label": t("volume") });
  const shown = el("output", { class: "slider-value" }, (vol.percent || 0) + "%");
  const mute = el("button", { type: "button", class: "btn ghost small", "aria-pressed": String(!!vol.muted) }, icon("g-mute"), t("mute"));
  const send = async (body) => {
    const res = await api("/api/volume", { method: "POST", body: JSON.stringify(body) });
    const now = await res.json().catch(() => ({}));
    if (now.percent != null) { range.value = now.percent; shown.textContent = now.percent + "%"; }
    mute.setAttribute("aria-pressed", String(!!now.muted));
  };
  range.addEventListener("input", () => { shown.textContent = range.value + "%"; });
  range.addEventListener("change", () => send({ set: Number(range.value) }).catch(() => {}));
  mute.addEventListener("click", () => send({ action: "mute" }).catch(() => {}));
  if (vol.percent == null) return el("div", { class: "setting" }, el("div", { class: "dim" }, t("not_installed")));
  return el("div", { class: "setting" }, el("label", {}, icon("px-audio"), t("volume")),
    el("div", { class: "slider" }, range, shown), el("div", { class: "row start" }, mute));
}

// ── Games > Frontend: os frontends da pessoa ──

async function frontendsBox() {
  const data = await (await api("/api/frontends")).json();
  const list = el("div", { class: "nics" });
  const form = (fe) => {
    const label = el("input", { type: "text", value: fe ? fe.label : "", placeholder: t("fe_label"), "aria-label": t("fe_label"),
      maxlength: "80" });
    const command = el("input", { type: "text", class: "code-in", value: fe ? fe.command : "", placeholder: t("fe_cmd"),
      "aria-label": t("fe_cmd"), spellcheck: "false" });
    const save = el("button", { type: "submit", class: "btn" }, icon("px-save"), t("fe_save"));
    const box = el("form", { class: "fe-form" }, label, command, el("div", { class: "row start" }, save));
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
  for (const fe of data.frontends || []) {
    const edit = el("button", { type: "button", class: "btn ghost small" }, icon("px-edit"), t("fe_edit"));
    const del = el("button", { type: "button", class: "btn red small" }, icon("px-remove"), t("fe_delete"));
    const row = el("div", { class: "fe-row" }, el("div", { class: "nic-row" }, icon("px-frontend"), el("b", {}, fe.label),
      el("code", { class: "dim" }, fe.command), fe.installed ? "" : el("span", { class: "tag off" }, t("fe_missing")), edit, del));
    edit.addEventListener("click", () => { edit.disabled = true; row.append(form(fe)); });
    del.addEventListener("click", async () => {
      if (!(await ask({ title: fe.label, text: t("fe_delete_ask").replace("%s", fe.label), yes: t("fe_delete"), danger: true }))) return;
      const res = await api("/api/frontends", { method: "POST", body: JSON.stringify({ action: "delete", name: fe.name }) });
      if (!res.ok) toast((await res.json().catch(() => ({}))).error || res.statusText, "bad");
      loadSettings().catch(() => {});
    });
    list.append(row);
  }
  return [el("div", { class: "setting one" }, el("h4", {}, t("fe_custom")),
    data.frontends && data.frontends.length ? list : el("div", { class: "dim" }, t("fe_none")),
    el("details", { class: "fe-add" }, el("summary", {}, icon("px-add"), t("fe_add")), form(null)),
    el("div", { class: "dim" }, t("fe_boot")))];
}

// ── Games > Folders ──

async function foldersBox(path) {
  const data = await (await api("/api/folders?path=" + encodeURIComponent(path))).json();
  const list = el("div", { class: "folders" + (path ? " inner" : "") });
  for (const f of data.folders || []) {
    const state = { default: "fo_default", custom: "fo_custom", offline: "fo_offline", missing: "fo_missing" }[f.state] || "fo_default";
    const link = el("button", { type: "button", class: "btn ghost small" }, icon("px-link"), t("fo_link"));
    link.addEventListener("click", () => folderLink(f.path, data.start));
    const actions = [link];
    if (f.state === "custom" || f.state === "offline") {
      const undo = el("button", { type: "button", class: "btn ghost small" }, icon("px-unlink"), t("fo_unlink"));
      undo.addEventListener("click", () => folderUnlink(f.path));
      actions.push(undo);
    }
    const row = el("div", { class: "folder" }, el("div", { class: "nic-row" }, icon("px-dest"), el("b", {}, "~/" + f.path),
      el("span", { class: "tag " + (f.state === "custom" ? "on" : f.state === "offline" ? "off" : "") }, t(state)),
      f.target ? el("code", { class: "dim" }, f.target) : ""), f.about ? el("div", { class: "dim" }, f.about) : "",
    el("div", { class: "row start" }, ...actions));
    if (f.inner) {
      const inner = el("details", { class: "folder-inner" }, el("summary", {}, t("fo_inner")));
      inner.addEventListener("toggle", async () => {
        if (!inner.open || inner.dataset.loaded) return;
        inner.dataset.loaded = "1";
        inner.append(await foldersBox(f.path));
      });
      row.append(inner);
    }
    list.append(row);
  }
  return path ? list : el("div", { class: "setting one" }, list, el("div", { class: "dim" }, t("fo_note")));
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

async function quirksBox() {
  const data = await (await api("/api/quirks")).json();
  const list = el("div", { class: "nics" }, ...(data.quirks || []).map((q) => {
    const del = el("button", { type: "button", class: "btn red small" }, icon("px-remove"), t("fe_delete"));
    del.addEventListener("click", async () => {
      if (!(await ask({ title: q.name, text: t("qk_delete_ask").replace("%s", q.name + " (" + q.code + ")"), yes: t("fe_delete"),
        danger: true }))) return;
      const res = await api("/api/quirks", { method: "POST", body: JSON.stringify({ action: "delete", code: q.code }) });
      const out = await res.json().catch(() => ({}));
      toast(res.ok ? t("qk_deleted") : out.error || res.statusText, res.ok ? "ok" : "bad");
      loadSettings().catch(() => {});
    });
    return el("div", { class: "nic-row" }, icon("px-quirks"), el("b", {}, q.name), el("code", { class: "dim" }, q.code), del);
  }));
  const name = el("input", { type: "text", placeholder: t("qk_name"), "aria-label": t("qk_name"), maxlength: "80" });
  const device = el("select", { "aria-label": t("qk_device") }, el("option", { value: "" }, t("qk_device_none")),
    ...(data.devices || []).map((d) => el("option", { value: d.id }, d.id + "  " + d.name)));
  const kind = el("select", { "aria-label": t("qk_kind") }, ...QUIRK_KINDS.map(([k]) => el("option", { value: k }, t("qk_" + k))));
  const code = el("input", { type: "text", class: "code-in", placeholder: "0x16c0:0x05e1:0x40", "aria-label": t("qk_code"),
    spellcheck: "false" });
  // O codigo sai do aparelho e da correcao (o do disco sem 0x).
  const fill = () => {
    const id = device.value, k = QUIRK_KINDS.find(([x]) => x === kind.value);
    if (!id || kind.value === "custom") return;
    code.value = kind.value === "uas" ? id.replace(/0x/g, "") + ":u" : id + k[1];
    if (!name.value) name.value = (device.selectedOptions[0].textContent.split("  ")[1] || "").slice(0, 60);
  };
  device.addEventListener("change", fill);
  kind.addEventListener("change", fill);
  const add = el("button", { type: "submit", class: "btn" }, icon("px-add"), t("qk_add"));
  const form = el("form", { class: "fe-form" }, name, device, kind, code, el("div", { class: "row start" }, add));
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
  return [el("div", { class: "setting one" }, data.quirks && data.quirks.length ? list : el("div", { class: "dim" }, t("qk_none")),
    el("details", { class: "fe-add" }, el("summary", {}, icon("px-add"), t("qk_add")), form),
    el("div", { class: "dim" }, t("qk_note")))];
}

// ── Joysticks > Bluetooth ──

async function bluetoothBox() {
  const data = await (await api("/api/bluetooth")).json();
  const power = el("input", { type: "checkbox" });
  power.checked = !!data.powered;
  power.addEventListener("change", async () => {
    await api("/api/bluetooth", { method: "POST", body: JSON.stringify({ action: "power", on: power.checked }) });
    loadSettings().catch(() => {});
  });
  const act = async (action, d, button) => {
    if (action === "remove" && !(await ask({ title: d.name, text: t("bt_forget_ask").replace("%s", d.name), yes: t("bt_forget"),
      danger: true }))) return;
    button.disabled = true;
    if (action === "pair") toast(t("bt_pairing").replace("%s", d.name));
    const res = await api("/api/bluetooth", { method: "POST", body: JSON.stringify({ action, mac: d.mac }) });
    const out = await res.json().catch(() => ({}));
    button.disabled = false;
    if (!res.ok) return toast(out.error || res.statusText, "bad");
    if (action === "pair") toast(t("bt_paired_ok").replace("%s", d.name), "ok");
    loadSettings().catch(() => {});
  };
  const row = (d, actions) => el("div", { class: "nic-row" }, icon("px-bluetooth"), el("b", {}, d.name), el("code", { class: "dim" }, d.mac),
    d.connected ? el("span", { class: "tag on" }, t("bt_connected")) : d.paired ? el("span", { class: "tag" }, t("bt_paired")) : "",
    ...actions.map(([action, label]) => {
      const b = el("button", { type: "button", class: "btn small " + (action === "remove" ? "red" : "ghost") }, t(label));
      b.addEventListener("click", () => act(action, d, b));
      return b;
    }));
  const paired = (data.devices || []).map((d) => row(d, [d.connected ? ["disconnect", "bt_disconnect"] : ["connect", "bt_connect"],
    ["remove", "bt_forget"]]));
  const found = el("div", { class: "nics" });
  const scan = el("button", { type: "button", class: "btn" }, icon("px-scan"), t("bt_scan"));
  scan.disabled = !data.powered;
  scan.addEventListener("click", async () => {
    scan.disabled = true;
    found.replaceChildren(el("div", { class: "dim" }, t("bt_scanning")));
    try {
      const res = await api("/api/bluetooth?scan=1");
      const out = await res.json().catch(() => ({}));
      const fresh = (out.found || []).filter((d) => !d.paired);
      found.replaceChildren(...(fresh.length ? fresh.map((d) => row(d, [["pair", "bt_pair"]]))
        : [el("div", { class: "dim" }, t("bt_found_none"))]));
    } finally {
      scan.disabled = false;
    }
  });
  return [el("div", { class: "setting one" },
    el("label", { class: "switch" }, power, el("i"), el("span", {}, t("bt_power") + (data.adapter ? " (" + data.adapter + ")" : ""))),
    paired.length ? el("div", { class: "nics" }, ...paired) : el("div", { class: "dim" }, t("bt_none")),
    el("div", { class: "row start" }, scan), found, el("div", { class: "dim" }, t("bt_howto")))];
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
