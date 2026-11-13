// As tarefas (o que leva minutos: downloads, scraper, BIOS, instalacoes, a
// limpeza de romsets, o modo lab): uma gaveta so, aberta pelo botao do topo,
// com um selo de quantas estao rodando. Quando uma termina, um toast e o
// cartao de quem a comecou se refaz (taskDone). No alto da gaveta, o que roda
// sozinho no gabinete (com jogo aberto ou nao): o scrape automatico e o
// Downloader dos torrents de ROM e CHD, com o pausar dele.

let openLogs = new Set(), taskNext = 0, tasksCount = 0;
const taskRunning = new Map();

// O que se refaz quando uma tarefa termina.
function taskDone(kind) {
  if (kind === "bios" && page === "downloads") loadBios().catch(() => {});
  if ((kind === "scraper" || kind === "mediapacks") && page === "scraper") loadScraper().catch(() => {});
  if (kind === "extras" && page === "install") loadInstall().catch(() => {});
  if (kind === "settings" && page === "settings") loadSettings().catch(() => {});
}

// Uma linha do que roda sozinho (background do /api/tasks).
function backgroundRow(b) {
  const isDl = b.kind === "download", isPaused = isDl && b.state === "paused";
  const goOn = isDl && b.state !== "downloading";
  let name, state, detail;
  if (isDl) {
    name = t("bg_download");
    state = isPaused ? t("dl_paused") : b.state === "downloading" ? b.pct + "%" : t("bg_stopped");
    detail = b.line;
  } else {
    name = t("bg_scrape");
    state = b.scanned && b.total ? b.pct + "%" : "…";
    const parts = [autoScrapeLine(b)];
    if (b.current) parts.push(t("scr_auto_now").replace("%s", b.current));
    if (b.packs_pct != null) parts.push(t("scr_auto_packs").replace("%n", b.packs_pct));
    detail = parts.join(" · ");
  }
  const item = el("li", { class: "task" + (goOn ? "" : " running") },
    el("div", { class: "task-head" }, icon(goOn ? "g-warn" : "g-refresh", "task-icon"),
      el("strong", {}, name), el("span", { class: "task-state" }, state)));
  item.append(meter(b.pct || 0));
  if (detail) item.append(el("div", { class: "dim task-detail" }, detail));
  if (isDl) {
    const go = el("button", { type: "button", class: "btn small" + (goOn ? "" : " ghost") },
      t(goOn ? "dl_resume" : "dl_pause"));
    go.addEventListener("click", async () => {
      go.disabled = true;
      await api("/api/downloader", { method: "POST", body: JSON.stringify({ action: goOn ? "resume" : "pause" }) });
      taskNext = 0;
      loadTasks().catch(() => {});
      if (page === "downloads") loadDownloader().catch(() => {});
    });
    item.append(el("div", { class: "task-actions" }, go));
  }
  return item;
}

async function loadTasks() {
  const res = await api("/api/tasks");
  const data = await res.json();
  const tasks = data.tasks || [], bg = data.background || [];
  for (const task of tasks) {
    if (taskRunning.get(task.id) && !task.running) {
      taskDone(task.kind);
      toast(t(task.rc === 0 ? "task_done_toast" : "task_failed_toast").replace("%s", task.name), task.rc === 0 ? "ok" : "bad");
    }
    taskRunning.set(task.id, task.running);
  }
  // O selo conta tambem o que roda sozinho (o download pausado nao).
  tasksCount = tasks.filter((x) => x.running).length
    + bg.filter((b) => b.kind !== "download" || b.state === "downloading").length;
  $("tasks-badge").hidden = !tasksCount;
  $("tasks-badge").textContent = tasksCount;
  $("tasks-btn").classList.toggle("busy", tasksCount > 0);
  if ($("drawer").hidden) return;
  const list = $("tasks");
  if (!tasks.length && !bg.length) {
    list.replaceChildren(el("li", { class: "empty-task" }, icon("px-ok"), el("span", {}, t("no_tasks"))));
    return;
  }
  const rows = bg.map(backgroundRow);
  for (const task of tasks) {
    const done = !task.running, ok = done && task.rc === 0;
    const state = task.running ? (task.pct != null ? task.pct + "%" : "…") : ok ? t("task_ok") : t("task_fail") + " (" + task.rc + ")";
    const item = el("li", { class: "task" + (task.running ? " running" : ok ? " ok" : " fail") },
      el("div", { class: "task-head" }, icon(task.running ? "g-refresh" : ok ? "g-check" : "g-warn", "task-icon"),
        el("strong", {}, task.name), el("span", { class: "task-state" }, state)));
    if (task.running) item.append(meter(task.pct || 0));
    const detail = task.error || task.step || task.last;
    if (detail) item.append(el("div", { class: "dim task-detail" }, detail));
    const actions = el("div", { class: "task-actions" });
    const logButton = el("button", { type: "button", class: "btn ghost small" }, icon("g-list"), t("show_log"));
    logButton.addEventListener("click", () => {
      openLogs.has(task.id) ? openLogs.delete(task.id) : openLogs.add(task.id);
      loadTasks();
    });
    actions.append(logButton);
    if (task.running) {
      const cancel = el("button", { type: "button", class: "btn red small" }, icon("g-close"), t("cancel"));
      cancel.addEventListener("click", async () => {
        await api("/api/task/cancel", { method: "POST", body: JSON.stringify({ id: task.id }) });
        loadTasks();
      });
      actions.append(cancel);
    }
    item.append(actions);
    if (openLogs.has(task.id)) {
      const r = await api("/api/task?id=" + task.id);
      const pre = el("pre", { class: "log" }, (await r.json()).log || "");
      item.append(pre);
      requestAnimationFrame(() => { pre.scrollTop = pre.scrollHeight; });
    }
    rows.push(item);
  }
  list.replaceChildren(...rows);
}

// Com algo rodando ou a gaveta aberta, a cada 3 s; parado, a cada 15 s.
function tasksTick(now) {
  if (now < taskNext) return;
  taskNext = now + (tasksCount || !$("drawer").hidden ? 3000 : 15000);
  loadTasks().catch(() => {});
}

function drawer(open) {
  $("drawer").hidden = !open;
  $("drawer-back").hidden = !open;
  if (open) { taskNext = 0; loadTasks().catch(() => {}); }
}
$("tasks-btn").addEventListener("click", () => drawer($("drawer").hidden));
$("drawer-close").addEventListener("click", () => drawer(false));
$("drawer-back").addEventListener("click", () => drawer(false));
