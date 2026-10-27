// Biblioteca: o Downloader e a BIOS, o Scraper e os pacotes de arte, os
// emuladores e os extras, e os arquivos do gabinete.
"use strict";

// ── Downloads e tarefas ──────────────────────────────────────────
// O Downloader do Setup (o filtro do MAME ROM Cleaner escolhe o que baixar
// dos torrents): o andamento, os links e o comecar. O que leva minutos vira
// uma tarefa, com a etapa, a porcentagem e o log.

let dlState = {};

async function loadDownloader() {
  const res = await api("/api/downloader");
  dlState = await res.json();
  const pct = Number(dlState.pct || 0);
  $("dl-text").textContent = dlState.line || "";
  $("dl-pct").textContent = dlState.state === "downloading" ? pct + "%" : "";
  $("dl-bar").style.width = pct + "%";
  $("dl-filter").textContent = dlState.filter || "-";
  if (document.activeElement && document.activeElement.closest(".dl-kind")) return;
  $("dl-kinds").replaceChildren(...["roms", "chds"].map((kind) => {
    const name = dlState[kind + "_name"];
    const box = el("div", { class: "dl-kind" }, el("strong", {}, t("dl_" + kind)),
      el("div", { class: name ? "" : "dim" }, name ? name + " · " + (dlState[kind + "_sets"] || 0) + " sets" : t("dl_none")));
    if (name) {
      const remove = el("button", { type: "button", class: "ghost danger", "data-icon": "🗑" }, t("dl_remove"));
      remove.addEventListener("click", async () => {
        if (!confirm(t("dl_remove_ask"))) return;
        const del = confirm(t("dl_delete_ask"));
        await api("/api/downloader", { method: "POST", body: JSON.stringify({ action: "remove", kind, delete: del }) });
        loadDownloader();
      });
      box.append(remove);
    } else {
      const input = el("input", { type: "text", placeholder: t("dl_paste"), autocomplete: "off" });
      const add = el("button", { type: "button", "data-icon": "🔗" }, t("dl_add"));
      add.addEventListener("click", () => downloaderTask({ action: "add", kind, magnet: input.value.trim() }));
      box.append(el("div", { class: "row" }, input, add));
      if (dlState["default_" + kind]) {
        const def = el("button", { type: "button", class: "ghost", "data-icon": "⭐" }, t("dl_default"));
        def.addEventListener("click", () => downloaderTask({ action: "add", kind }));
        box.append(def);
      }
    }
    return box;
  }));
}

async function downloaderTask(body) {
  const res = await api("/api/downloader", { method: "POST", body: JSON.stringify(body) });
  if (!res.ok) toast((await res.json().catch(() => ({}))).error || res.statusText);
  loadTasks();
  loadDownloader();
}
$("dl-start").addEventListener("click", () => downloaderTask({ action: "start" }));

// ── Download BIOS, Scraper e Instalar ────────────────────────────
// As telas do Setup que tambem ficam aqui: Download BIOS (na pagina
// Downloads), o Scraper e os pacotes de arte, Emulators & Games e Extras.
// O que leva minutos vira uma tarefa; quando ela termina, o cartao dela se
// refaz (taskDone).

async function postJson(path, body) {
  const res = await api(path, { method: "POST", body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) toast(data.error || res.statusText);
  return res.ok ? data : null;
}

async function startTask(path, body) {
  if (await postJson(path, body)) toast(t("inst_started"));
  loadTasks().catch(() => {});
}

const BIOS_FIELDS = ["downloaded", "present", "missing", "failed", "when"];
const BIOS_GROUPS = ["failed", "missing", "downloaded", "big", "present"];

async function loadBios() {
  const data = await (await api("/api/bios")).json();
  const last = data.last || {};
  $("bios-auto").checked = !!data.auto;
  $("bios-last").replaceChildren(...(Object.keys(last).length ? BIOS_FIELDS.map((key) => {
    let value = last[key] || "-";
    if (key === "downloaded" && last.bytes) value += " (" + bytes(Number(last.bytes)) + ")";
    return el("div", {}, el("dt", {}, t("bios_" + key)), el("dd", {}, value));
  }) : [el("div", {}, el("dd", { class: "dim" }, t("bios_none")))]));
  // Uma lista por estado; as que pedem algo da pessoa ja abertas.
  $("bios-list").replaceChildren(...BIOS_GROUPS.flatMap((status) => {
    const rows = (data.items || []).filter((r) => r.status === status);
    if (!rows.length) return [];
    const box = el("details", {}, el("summary", {}, t("bios_s_" + status) + " (" + rows.length + ")"),
      el("ul", { class: "small-list" }, ...rows.map((r) => el("li", {}, el("span", { class: "dim" }, r.folder + "  "), r.dest))));
    if (status === "failed" || status === "missing") box.open = true;
    return [box];
  }));
}
$("bios-check").addEventListener("click", () => startTask("/api/bios", { action: "check" }));
$("bios-refresh").addEventListener("click", () => startTask("/api/bios", { action: "check", refresh: true }));
$("bios-auto").addEventListener("change", async (event) => {
  await postJson("/api/bios", { action: "auto", on: event.target.checked });
  loadBios().catch(() => {});
});

const MEDIA = ["snap", "logo", "box", "marquee", "texto", "preview"];
let scr = null, scrPicked = new Set();

function chip(label, pressed, onClick) {
  const button = el("button", { type: "button", "aria-pressed": pressed ? "true" : "false" }, label);
  button.addEventListener("click", onClick);
  return button;
}

async function loadScraper() {
  scr = await (await api("/api/scraper")).json();
  const notes = [];
  if (scr.running) notes.push(t("scr_running"));
  if (scr.pending.length) notes.push(t("scr_pending").replace("%s", scr.pending.join(", ")));
  $("scr-state").textContent = notes.join(" ");
  $("scr-state").hidden = !notes.length;
  $("scr-resume").hidden = !scr.pending.length;
  renderScraperSystems();
  $("scr-source").replaceChildren(...scr.sources.map((s) => {
    const scope = SOURCE_SCOPE[s.key] || "all";
    const option = el("option", { value: s.key }, s.name + " · " + t(scope === "arcade" ? "tag_arcade_only" : "tag_" + scope));
    option.selected = s.key === scr.source;
    return option;
  }));
  showSourceScope(scr.source);
  // O rotulo da conta vem do Setup (scraper_account_label), em ingles.
  const account = { "no account needed": t("scr_acc_none"), "no account": t("scr_acc_no"),
    "key saved": t("scr_acc_key"), "key missing": t("scr_acc_nokey") }[scr.account]
    || (scr.user ? t("scr_acc_user").replace("%s", scr.user) : scr.account);
  $("scr-source-note").textContent = t("scr_account").replace("%s", account);
  renderScraperAccount();
  $("scr-media").replaceChildren(...MEDIA.map((m) => chip(t("media_" + m), scr.media.includes(m), async () => {
    const media = scr.media.includes(m) ? scr.media.filter((x) => x !== m) : scr.media.concat(m);
    if (await postJson("/api/scraper", { action: "media", media })) {
      scr.media = media;
      loadScraper().catch(() => {});
    }
  })));
  // O progetto-SNAPS so tem as capturas: os tipos nao valem para ele.
  $("scr-media").hidden = scr.source === "progettosnaps";
  $("scr-clones-box").hidden = !scr.systems.some((s) => s.key === "mame");
  const site = $("scr-site");
  site.textContent = t("scr_site_run").replace("%s", scr.name);
  const noSky = !scr.skyscraper && scr.source !== "progettosnaps";
  site.disabled = noSky || !scr.systems.length;
  site.title = noSky ? t("scr_no_sky") : "";
  showPacks(scr.packs);
}

function renderScraperSystems() {
  const keys = new Set(scr.systems.map((s) => s.key));
  scrPicked = new Set([...scrPicked].filter((k) => keys.has(k)));
  const box = $("scr-systems");
  if (!scr.systems.length) {
    box.replaceChildren(el("span", { class: "dim" }, t("scr_none")));
    $("scr-run").disabled = true;
    return;
  }
  $("scr-run").disabled = false;
  const pick = (s) => chip(s.key + " · " + s.count, scrPicked.has(s.key), () => {
    scrPicked.has(s.key) ? scrPicked.delete(s.key) : scrPicked.add(s.key);
    renderScraperSystems();
  });
  // As pastas de arcade e as de console separadas: cada uma ganha arte
  // diferente. Nenhuma marcada vale como todas, como o "All systems" da tela.
  const groups = [["arcade", true], ["console", false]].flatMap(([kind, arcade]) => {
    const list = scr.systems.filter((s) => !!s.arcade === arcade);
    return list.length ? [el("div", { class: "chips" }, el("span", { class: "tag " + kind }, t("tag_" + kind)),
      ...list.map(pick))] : [];
  });
  box.replaceChildren(el("div", { class: "chips" },
    chip(t("scr_all"), !scrPicked.size, () => { scrPicked.clear(); renderScraperSystems(); })), ...groups);
}

// O que cada site cobre: todos os sistemas, so arcade ou so consoles.
const SOURCE_SCOPE = { screenscraper: "all", mobygames: "all", thegamesdb: "console", igdb: "console",
  openretro: "console", arcadedb: "arcade", progettosnaps: "arcade" };

function showSourceScope(key) {
  const scope = SOURCE_SCOPE[key] || "all";
  const tag = $("scr-source-tag");
  tag.className = "tag " + scope;
  tag.textContent = t(scope === "arcade" ? "tag_arcade_only" : "tag_" + scope);
  $("scr-source-what").textContent = t("scr_src_" + key);
}

// A conta do site escolhido: usuario e senha, a chave de API ou o client ID
// e o secret. A senha guardada nunca volta para ca.
function renderScraperAccount() {
  const form = $("scr-account");
  const source = scr.sources.find((s) => s.key === $("scr-source").value) || {};
  const fields = { login: [["user", "text"], ["password", "password"]], key: [["key", "password"]],
    idsecret: [["id", "text"], ["secret", "password"]] }[source.kind];
  form.hidden = !fields;
  if (!fields) return;
  const inputs = fields.map(([name, type]) => {
    const input = el("input", { type, name, autocomplete: type === "password" ? "new-password" : "off" });
    if (name === "user" && scr.user) input.value = scr.user;
    return el("label", { class: "row" }, el("small", {}, t("scr_" + name)), input);
  });
  const save = el("button", { type: "submit", "data-icon": "💾" }, t("scr_save"));
  const remove = el("button", { type: "button", class: "ghost danger", "data-icon": "🗑" }, t("scr_remove"));
  remove.addEventListener("click", async () => {
    if (await postJson("/api/scraper", { action: "account", source: source.key, remove: true })) loadScraper().catch(() => {});
  });
  form.replaceChildren(...inputs, el("div", { class: "row" }, save, remove));
  form.onsubmit = async (event) => {
    event.preventDefault();
    const body = { action: "account", source: source.key };
    for (const [name] of fields) body[name] = form.elements[name].value.trim();
    if (await postJson("/api/scraper", body)) {
      toast(t("scr_saved"));
      loadScraper().catch(() => {});
    }
  };
}

$("scr-source").addEventListener("change", async (event) => {
  showSourceScope(event.target.value);
  await postJson("/api/scraper", { action: "source", source: event.target.value });
  loadScraper().catch(() => {});
});
$("scr-run").addEventListener("click", () => startTask("/api/scraper", { action: "scrape", systems: [...scrPicked] }));
$("scr-site").addEventListener("click", () => startTask("/api/scraper",
  { action: "site", systems: [...scrPicked], clones: $("scr-clones").checked }));
$("scr-resume").addEventListener("click", () => startTask("/api/scraper", { action: "resume" }));
$("packs-start").addEventListener("click", () => startTask("/api/scraper", { action: "packs" }));

function showPacks(packs) {
  const pct = Number(packs.pct || 0);
  const downloading = packs.state === "downloading";
  $("packs-text").textContent = packs.line && packs.state !== "none" ? packs.line : t("packs_idle");
  $("packs-pct").textContent = downloading ? pct + "%" : "";
  $("packs-bar").style.width = (downloading ? pct : 0) + "%";
}

async function loadPacks() {
  showPacks((await (await api("/api/scraper?packs=1")).json()).packs || {});
}

async function loadInstall() {
  const data = await (await api("/api/install")).json();
  $("emu-list").replaceChildren(...data.emulators.map((e) => installBox("emulators", e)));
  $("extras-list").replaceChildren(...data.extras.map((e) => installBox("extras", e)));
}

function installBox(group, item) {
  const state = item.installed ? t("inst_installed") + (item.version ? " · " + item.version : "") : t("inst_not");
  const box = el("div", { class: "dl-kind" }, el("div", { class: "row" }, el("strong", {}, item.label),
    el("span", { class: "dim" }, state)));
  if (item.kind === "image") {
    box.append(el("div", { class: "dim" }, t(item.installed ? "inst_image" : "inst_image_missing")));
    return box;
  }
  const go = el("button", { type: "button", "data-icon": item.installed ? "↻" : "⬇" },
    t(item.installed ? "inst_update" : "inst_install"));
  go.addEventListener("click", () => {
    const ask = item.installed ? "inst_again" : item.kind === "build" ? "inst_build" : "inst_ask";
    if (confirm(t(ask).replace("%s", item.label))) startTask("/api/install", { group, name: item.name });
  });
  const actions = el("div", { class: "row start" }, go);
  if (group === "emulators" && item.installed) {
    const note = el("span", { class: "dim" });
    const check = el("button", { type: "button", class: "ghost", "data-icon": "🔎" }, t("inst_check"));
    check.addEventListener("click", async () => {
      note.textContent = t("inst_checking");
      const r = await (await api("/api/install/latest?name=" + encodeURIComponent(item.name))).json();
      note.textContent = r.state === "same" ? t("inst_same").replace("%s", r.want)
        : r.state === "new" ? t("inst_new").replace("%s", r.want) : t("inst_unknown");
    });
    actions.append(check, note);
  }
  box.append(actions);
  if (item.kind === "source") box.append(el("div", { class: "dim" }, t("inst_kof")));
  // O ZeDMD so conecta com o firmware 5.1 ou mais novo (docs/wiki/Frontends.md).
  if (group === "extras" && item.name === "zedmd") {
    box.append(el("div", { class: "dim" }, t("inst_zedmd") + " ",
      el("a", { href: "https://github.com/juniorterin/fliperOS/wiki/Frontends#zedmd-firmware-version",
        target: "_blank", rel: "noopener" }, t("inst_zedmd_link"))));
  }
  // O Pixelcade instalado: o codigo do pacote de arte pago.
  if (group === "extras" && item.name === "pixelcade" && item.installed) {
    const code = el("input", { type: "text", placeholder: t("inst_artpack"), autocomplete: "off" });
    const art = el("button", { type: "button", class: "ghost", "data-icon": "🎨" }, t("inst_artpack_go"));
    art.addEventListener("click", () => {
      if (code.value.trim()) startTask("/api/install", { group, name: item.name, artpack: code.value.trim() });
    });
    box.append(el("div", { class: "row" }, code, art));
  }
  return box;
}

// ── Arquivos: as pastas do gabinete ──────────────────────────────
// roms, bios, media e splashscreen de ~: entrar nas pastas, baixar,
// enviar (um de cada vez, com o progresso; tambem soltando na lista), criar
// pasta e apagar.

let fileRoot = "roms", filePath = "";

function filesQuery(path) {
  return "root=" + encodeURIComponent(fileRoot) + "&path=" + encodeURIComponent(path);
}
const joinPath = (...parts) => parts.filter(Boolean).join("/");

function stamp(seconds) {
  const d = new Date(seconds * 1000);
  return d.toLocaleDateString(lang === "pt" ? "pt-BR" : "en") + " " +
    d.toLocaleTimeString(lang === "pt" ? "pt-BR" : "en", { hour: "2-digit", minute: "2-digit" });
}

async function loadFiles(path) {
  const res = await api("/api/files?" + filesQuery(path == null ? filePath : path));
  if (!res.ok) { filePath = ""; return; }
  const data = await res.json();
  fileRoot = data.root;
  filePath = data.path;
  const select = $("file-root");
  if (select.options.length !== data.roots.length) {
    select.replaceChildren(...data.roots.map((r) => el("option", { value: r }, r === "home" ? "~/ (" + t("home_all") + ")" : "~/" + r)));
  }
  select.value = fileRoot;
  // O caminho: cada pedaco leva de volta a ele.
  const parts = filePath ? filePath.split("/") : [];
  const crumbs = [el("button", { type: "button" }, icon("g-home"), fileRoot === "home" ? "~" : "~/" + fileRoot)];
  crumbs[0].addEventListener("click", () => loadFiles(""));
  parts.forEach((part, i) => {
    const b = el("button", { type: "button" }, part);
    b.addEventListener("click", () => loadFiles(parts.slice(0, i + 1).join("/")));
    crumbs.push(el("span", {}, "/"), b);
  });
  $("crumbs").replaceChildren(...crumbs);

  const table = $("files");
  const head = el("tr", {}, el("th", {}, t("name")), el("th", { class: "num" }, t("size")),
    el("th", { class: "fdate" }, t("modified")), el("th", {}, ""));
  const rows = data.entries.map((e) => {
    const target = joinPath(filePath, e.name);
    let link;
    if (e.dir) {
      link = el("button", { type: "button", title: e.name }, "📁 " + e.name);
      link.addEventListener("click", () => loadFiles(target));
    } else {
      link = el("a", { href: "/api/download?" + filesQuery(target), title: e.name, download: e.name }, "📄 " + e.name);
    }
    const del = el("button", { type: "button", class: "del icon-only", "data-icon": "🗑",
      "aria-label": t("delete") + " " + e.name, title: t("delete") });
    del.addEventListener("click", async () => {
      if (!confirm(t("confirm_delete").replace("%s", e.name))) return;
      const r = await api("/api/delete", { method: "POST", body: JSON.stringify({ root: fileRoot, path: target }) });
      if (!r.ok) toast((await r.json().catch(() => ({}))).error || r.statusText);
      loadFiles();
    });
    // Os arquivos tambem com o botao de baixar (o nome ja baixa).
    const actions = el("td", { class: "fact" });
    if (!e.dir) {
      actions.append(el("a", { href: "/api/download?" + filesQuery(target), download: e.name, class: "dl icon-only",
        "data-icon": "⬇", "aria-label": t("download") + " " + e.name, title: t("download") }));
    }
    actions.append(del);
    return el("tr", {}, el("td", { class: "fname" }, link), el("td", { class: "num" }, e.dir ? "" : bytes(e.size)),
      el("td", { class: "fdate" }, stamp(e.mtime)), actions);
  });
  if (!rows.length) rows.push(el("tr", {}, el("td", { colspan: "4", class: "dim" }, t("empty_folder"))));
  // Dentro de uma pasta, ".." no topo volta para a de cima.
  if (filePath) {
    const up = el("button", { type: "button", title: t("up_folder") }, "📁 ..");
    up.addEventListener("click", () => loadFiles(filePath.split("/").slice(0, -1).join("/")));
    rows.unshift(el("tr", {}, el("td", { class: "fname" }, up), el("td"), el("td", { class: "fdate" }), el("td")));
  }
  table.replaceChildren(el("colgroup", {}, el("col"), el("col", { class: "c-size" }), el("col", { class: "c-date" }),
    el("col", { class: "c-del" })), el("thead", {}, head), el("tbody", {}, ...rows));
}

// sendFile: um arquivo pelo XMLHttpRequest (o fetch nao da o progresso do
// envio). Resolve com o status.
function sendFile(file, overwrite) {
  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/upload?" + filesQuery(filePath) + "&name=" + encodeURIComponent(file.name) +
      (overwrite ? "&overwrite=1" : ""));
    xhr.setRequestHeader("X-FliperOS", "1");
    xhr.upload.onprogress = (ev) => {
      if (ev.lengthComputable) {
        $("upload-status").textContent = t("uploading").replace("%s", file.name)
          .replace("%p", Math.round((100 * ev.loaded) / ev.total));
      }
    };
    xhr.onload = () => resolve(xhr.status);
    xhr.onerror = () => resolve(0);
    xhr.send(file);
  });
}

async function uploadFiles(files) {
  let sent = 0;
  for (const file of files) {
    let status = await sendFile(file, false);
    if (status === 409 && confirm(t("exists_overwrite").replace("%s", file.name))) status = await sendFile(file, true);
    if (status === 401) { showLogin(); return; }
    if (status === 200) sent++;
    else if (status !== 409) toast(file.name + ": " + (status || "network error"));
  }
  $("upload-status").textContent = t("uploaded").replace("%n", sent);
  loadFiles();
}

$("file-root").addEventListener("change", () => { fileRoot = $("file-root").value; loadFiles(""); });
$("file-input").addEventListener("change", () => {
  const files = Array.from($("file-input").files);
  $("file-input").value = "";
  if (files.length) uploadFiles(files);
});
$("file-mkdir").addEventListener("click", async () => {
  const name = prompt(t("folder_name"));
  if (!name) return;
  const r = await api("/api/mkdir", { method: "POST", body: JSON.stringify({ root: fileRoot, path: filePath, name }) });
  if (!r.ok) toast((await r.json().catch(() => ({}))).error || r.statusText);
  loadFiles();
});
const drop = $("file-drop");
drop.addEventListener("dragover", (ev) => { ev.preventDefault(); drop.classList.add("over"); });
drop.addEventListener("dragleave", () => drop.classList.remove("over"));
drop.addEventListener("drop", (ev) => {
  ev.preventDefault();
  drop.classList.remove("over");
  const files = Array.from(ev.dataTransfer.files || []);
  if (files.length) uploadFiles(files);
});
