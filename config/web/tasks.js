// As tarefas (o que leva minutos: downloads, scraper, BIOS, instalacoes, a
// limpeza de romsets, o modo lab): uma gaveta so, aberta pelo botao do topo,
// com um selo de quantas estao rodando. Quando uma termina, um toast e o
// cartao de quem a comecou se refaz (taskDone).

let openLogs = new Set(), taskNext = 0, tasksCount = 0;
const taskRunning = new Map();

// O que se refaz quando uma tarefa termina.
function taskDone(kind) {
  if (kind === "bios" && page === "downloads") loadBios().catch(() => {});
  if ((kind === "scraper" || kind === "mediapacks") && page === "scraper") loadScraper().catch(() => {});
  if (kind === "extras" && page === "install") loadInstall().catch(() => {});
  if (kind === "settings" && page === "settings") loadSettings().catch(() => {});
}

async function loadTasks() {
  const res = await api("/api/tasks");
  const tasks = (await res.json()).tasks || [];
  for (const task of tasks) {
    if (taskRunning.get(task.id) && !task.running) {
      taskDone(task.kind);
      toast(t(task.rc === 0 ? "task_done_toast" : "task_failed_toast").replace("%s", task.name), task.rc === 0 ? "ok" : "bad");
    }
    taskRunning.set(task.id, task.running);
  }
  tasksCount = tasks.filter((x) => x.running).length;
  $("tasks-badge").hidden = !tasksCount;
  $("tasks-badge").textContent = tasksCount;
  $("tasks-btn").classList.toggle("busy", tasksCount > 0);
  if ($("drawer").hidden) return;
  const list = $("tasks");
  if (!tasks.length) {
    list.replaceChildren(el("li", { class: "empty-task" }, icon("px-ok"), el("span", {}, t("no_tasks"))));
    return;
  }
  const rows = [];
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
