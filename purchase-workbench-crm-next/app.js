const DB_NAME = "purchase_workbench_crm_next";
const DB_VERSION = 1;
const STORE_NAME = "tasks";

const PRIORITIES = ["紧急", "高", "中", "低"];
const STATUSES = ["待启动", "进行中", "已搁置", "已完成"];
const priorityWeight = { 紧急: 0, 高: 1, 中: 2, 低: 3 };
const statusClassMap = {
  待启动: "status-pending",
  进行中: "status-progress",
  已搁置: "status-paused",
  已完成: "status-done",
};

let db;
let pendingConfirmResolve = null;
const state = {
  tasks: [],
  selectedTaskId: null,
  tableFilter: "all",
  searchQuery: "",
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

document.addEventListener("DOMContentLoaded", init);

async function init() {
  try {
    db = await openDatabase();
    await seedTasksIfEmpty();
    await refreshTasks();
    bindEvents();
    exposeLocalDiagnostics();
    renderAll();
    showToast("本地任务库已就绪");
  } catch (error) {
    console.error(error);
    $("#workflowBoard").innerHTML = `<div class="empty-state">IndexedDB 初始化失败：${escapeHtml(error.message)}</div>`;
    showToast("本地数据库初始化失败");
  }
}

function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(STORE_NAME)) {
        const store = database.createObjectStore(STORE_NAME, { keyPath: "id" });
        store.createIndex("category", "category", { unique: false });
        store.createIndex("status", "status", { unique: false });
        store.createIndex("priority", "priority", { unique: false });
        store.createIndex("isProblem", "isProblem", { unique: false });
        store.createIndex("createDate", "createDate", { unique: false });
        store.createIndex("updateDate", "updateDate", { unique: false });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function storeRequest(mode, handler) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, mode);
    const store = transaction.objectStore(STORE_NAME);
    const request = handler(store);

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function getAllTasks() {
  return storeRequest("readonly", (store) => store.getAll());
}

function getTask(id) {
  return storeRequest("readonly", (store) => store.get(id));
}

function putTask(task) {
  return storeRequest("readwrite", (store) => store.put(task));
}

function deleteTask(id) {
  return storeRequest("readwrite", (store) => store.delete(id));
}

async function queryTasks({ keyword = "", status = "", category = "", isProblem = null } = {}) {
  const tasks = await getAllTasks();
  const lower = keyword.trim().toLowerCase();
  return tasks.filter((task) => {
    const keywordMatch =
      !lower ||
      task.taskName.toLowerCase().includes(lower) ||
      task.category.toLowerCase().includes(lower);
    const statusMatch = !status || task.status === status;
    const categoryMatch = !category || task.category === category;
    const problemMatch = isProblem === null || task.isProblem === isProblem;
    return keywordMatch && statusMatch && categoryMatch && problemMatch;
  });
}

async function refreshTasks() {
  state.tasks = normalizeTasks(await getAllTasks());
  if (!state.selectedTaskId || !state.tasks.some((task) => task.id === state.selectedTaskId)) {
    state.selectedTaskId = state.tasks[0]?.id || null;
  }
}

async function seedTasksIfEmpty() {
  const existing = await getAllTasks();
  if (existing.length) return;

  const samples = [
    createSeedTask("研发采购 - 结构件打样", "研发采购", "紧急", "进行中", true, "供应商报价偏高，需要重新核价。", 46, 6),
    createSeedTask("行政采购 - 办公耗材补货", "行政采购", "中", "待启动", false, "", 15, 3),
    createSeedTask("生产采购 - 包材年度框架", "生产采购", "高", "进行中", false, "", 68, 12),
    createSeedTask("IT采购 - 设备续保合同", "IT采购", "高", "已搁置", true, "合同条款等待法务确认。", 38, 8),
    createSeedTask("仓储采购 - 托盘供应评估", "仓储采购", "低", "已完成", false, "", 100, 18),
  ];

  await Promise.all(samples.map((task) => putTask(task)));
}

function createSeedTask(taskName, category, priority, status, isProblem, problemDesc, progress, daysBack) {
  const createDate = offsetDate(-daysBack);
  const midDate = offsetDate(-Math.max(Math.floor(daysBack / 2), 1));
  const today = todayKey();
  const startProgress = Math.max(0, progress - 24);
  const midProgress = Math.max(startProgress, progress - 10);

  return {
    id: generateId(),
    taskName,
    category,
    priority,
    status,
    isProblem,
    problemDesc,
    progress,
    createDate,
    updateDate: today,
    historyLog: [
      { date: createDate, progress: startProgress, status: "待启动" },
      { date: midDate, progress: midProgress, status: status === "已完成" ? "进行中" : status },
      { date: today, progress, status },
    ],
  };
}

function bindEvents() {
  $("#globalSearch").addEventListener("input", (event) => {
    state.searchQuery = event.target.value.trim();
    renderBoard();
    renderTable();
  });

  $$(".nav-item, .tab-button").forEach((button) => {
    button.addEventListener("click", () => setActiveView(button.dataset.view));
  });

  $$(".segmented button").forEach((button) => {
    button.addEventListener("click", () => {
      state.tableFilter = button.dataset.filter;
      $$(".segmented button").forEach((item) => item.classList.remove("is-active"));
      button.classList.add("is-active");
      renderTable();
    });
  });

  $("#addTaskButton").addEventListener("click", () => openTaskModal());
  $("#generateReportButton").addEventListener("click", generateMonthlyReport);
  $("#taskForm").addEventListener("submit", saveTaskFromForm);
  $("#cancelModalButton").addEventListener("click", closeTaskModal);
  $("#closeModalButton").addEventListener("click", closeTaskModal);
  $("#taskModal").addEventListener("click", (event) => {
    if (event.target.id === "taskModal") closeTaskModal();
  });
  $("#confirmCancelButton").addEventListener("click", () => resolveConfirm(false));
  $("#confirmOkButton").addEventListener("click", () => resolveConfirm(true));
  $("#confirmModal").addEventListener("click", (event) => {
    if (event.target.id === "confirmModal") resolveConfirm(false);
  });

  $("#progress").addEventListener("input", (event) => {
    $("#progressValue").textContent = `${event.target.value}%`;
  });

  $("#isProblem").addEventListener("change", syncProblemFieldState);

  $("#openDetailButton").addEventListener("click", () => {
    if (!state.selectedTaskId) {
      showToast("当前没有可编辑任务");
      return;
    }
    openTaskModal(state.selectedTaskId);
  });

  $("#notifyButton").addEventListener("click", () => {
    const count = state.tasks.filter((task) => task.isProblem).length;
    showToast(count ? `当前有 ${count} 个问题任务` : "当前没有问题任务");
  });

  $("#filterButton").addEventListener("click", () => {
    showToast("表格筛选只影响列表，看板保持全局板块视图");
  });

  $("#orderTableBody").addEventListener("click", handleTableClick);
  $("#workflowBoard").addEventListener("click", handleBoardClick);
}

function setActiveView(view) {
  const titles = {
    dashboard: ["本地采购任务", "任务工作台"],
    tasks: ["任务全生命周期", "任务管理"],
    categories: ["动态板块", "板块看板"],
    report: ["月底复盘", "月度报告"],
    automation: ["每日快照", "自动记录"],
    settings: ["本地运行", "系统设置"],
  };
  const [eyebrow, title] = titles[view] || titles.dashboard;
  $("#moduleEyebrow").textContent = eyebrow;
  $("#moduleTitle").textContent = title;
  $$(".nav-item, .tab-button").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === view);
  });
}

function renderAll() {
  renderKpis();
  renderBoard();
  renderTable();
  renderDetail();
  renderCategorySummary();
  renderStorageSummary();
  renderCategoryOptions();
}

function renderKpis() {
  const total = state.tasks.length;
  const pending = state.tasks.filter((task) => task.status !== "已完成").length;
  const problems = state.tasks.filter((task) => task.isProblem).length;
  const average = total ? Math.round(sum(state.tasks.map((task) => task.progress)) / total) : 0;

  $("#metricTotal").textContent = total;
  $("#metricPending").textContent = pending;
  $("#metricProblem").textContent = problems;
  $("#metricAverage").textContent = `${average}%`;
  $("#problemBadge").textContent = problems;
}

function renderBoard() {
  const board = $("#workflowBoard");
  const tasks = state.tasks.filter(matchesSearch);
  const categories = [...new Set(tasks.map((task) => task.category))].sort((a, b) => a.localeCompare(b, "zh-CN"));

  if (!categories.length) {
    board.innerHTML = `<div class="empty-state">没有匹配的任务</div>`;
    return;
  }

  board.innerHTML = categories
    .map((category) => {
      const categoryTasks = tasks
        .filter((task) => task.category === category)
        .sort((a, b) => priorityWeight[a.priority] - priorityWeight[b.priority] || b.progress - a.progress);

      return `
        <article class="workflow-column">
          <header>
            <h3>${escapeHtml(category)}</h3>
            <span class="count-pill">${categoryTasks.length}</span>
          </header>
          ${categoryTasks.map(renderTaskCard).join("")}
        </article>
      `;
    })
    .join("");
}

function renderTaskCard(task) {
  return `
    <button class="task-card ${task.isProblem ? "is-problem" : ""}" type="button" data-task-id="${escapeHtml(task.id)}">
      <span class="task-card-top">
        <strong>${escapeHtml(task.taskName)}</strong>
        ${task.isProblem ? `<span class="warning-mark" title="有问题">⚠</span>` : ""}
      </span>
      <span class="task-progress-line">
        <span class="progress"><i style="width: ${task.progress}%"></i></span>
        <span>${task.progress}%</span>
      </span>
      <span class="task-meta">
        <span class="status-pill ${statusClass(task.status)}">${escapeHtml(task.status)}</span>
        <span class="priority-chip priority-${priorityKey(task.priority)}">${escapeHtml(task.priority)}</span>
      </span>
    </button>
  `;
}

function renderTable() {
  const body = $("#orderTableBody");
  const rows = state.tasks.filter(matchesSearch).filter(matchesTableFilter);

  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="8" class="empty-row">没有匹配的任务记录</td></tr>`;
    return;
  }

  body.innerHTML = rows
    .sort((a, b) => b.updateDate.localeCompare(a.updateDate) || priorityWeight[a.priority] - priorityWeight[b.priority])
    .map(
      (task) => `
        <tr data-task-id="${escapeHtml(task.id)}" class="${task.id === state.selectedTaskId ? "is-selected" : ""}">
          <td><strong>${escapeHtml(task.taskName)}</strong></td>
          <td>${escapeHtml(task.category)}</td>
          <td><span class="priority-chip priority-${priorityKey(task.priority)}">${escapeHtml(task.priority)}</span></td>
          <td><span class="status-pill ${statusClass(task.status)}">${escapeHtml(task.status)}</span></td>
          <td>
            <div class="table-progress">
              <span class="progress"><i style="width: ${task.progress}%"></i></span>
              <strong>${task.progress}%</strong>
            </div>
          </td>
          <td>${task.isProblem ? `<span class="problem-inline">⚠ 有问题</span>` : "正常"}</td>
          <td>${escapeHtml(task.updateDate)}</td>
          <td>
            <button class="danger-button" type="button" data-action="delete" data-task-id="${escapeHtml(task.id)}">
              <svg><use href="#icon-trash"></use></svg>
              删除
            </button>
          </td>
        </tr>
      `
    )
    .join("");
}

function renderDetail() {
  const task = state.tasks.find((item) => item.id === state.selectedTaskId);
  const editButton = $("#openDetailButton");

  if (!task) {
    $("#detailTitle").textContent = "暂无任务";
    $("#detailStatus").textContent = "暂无";
    $("#detailCategory").textContent = "-";
    $("#detailPriority").textContent = "-";
    $("#detailProgress").textContent = "0%";
    $("#detailUpdateDate").textContent = "-";
    $("#detailProblem").textContent = "无问题描述";
    $("#timeline").innerHTML = `<div class="empty-state compact">暂无历史记录</div>`;
    editButton.disabled = true;
    return;
  }

  editButton.disabled = false;
  $("#detailTitle").textContent = task.taskName;
  $("#detailStatus").textContent = task.status;
  $("#detailCategory").textContent = task.category;
  $("#detailPriority").textContent = task.priority;
  $("#detailProgress").textContent = `${task.progress}%`;
  $("#detailUpdateDate").textContent = task.updateDate;
  $("#detailProblem").textContent = task.isProblem ? task.problemDesc : "无问题描述";
  $("#detailProblem").classList.toggle("is-problem", task.isProblem);

  const minHistoryDate = offsetDate(-6);
  const logs = [...task.historyLog]
    .filter((log) => log.date >= minHistoryDate && log.date <= todayKey())
    .sort((a, b) => b.date.localeCompare(a.date))
    .slice(0, 7);

  $("#timeline").innerHTML = logs.length
    ? logs
        .map(
          (log) => `
            <div class="timeline-item">
              <span class="timeline-dot"></span>
              <div>
                <strong>📅 ${escapeHtml(log.date)} → 进度 ${log.progress}% (${escapeHtml(log.status)})</strong>
              </div>
            </div>
          `
        )
        .join("")
    : `<div class="empty-state compact">暂无历史记录</div>`;
}

function renderCategorySummary() {
  const list = $("#supplierList");
  const groups = groupByCategory(state.tasks)
    .map(([category, tasks]) => ({
      category,
      count: tasks.length,
      average: Math.round(sum(tasks.map((task) => task.progress)) / tasks.length),
    }))
    .sort((a, b) => b.average - a.average);

  if (!groups.length) {
    list.innerHTML = `<div class="empty-state compact">暂无板块数据</div>`;
    return;
  }

  list.innerHTML = groups
    .map(
      (item) => `
        <div class="supplier-item">
          <div class="supplier-main">
            <strong>${escapeHtml(item.category)}</strong>
            <span>${item.count} 个任务</span>
          </div>
          <div class="risk-meter"><i style="width: ${item.average}%"></i></div>
          <small>${item.average}% 平均完成率</small>
        </div>
      `
    )
    .join("");
}

function renderStorageSummary() {
  const latestDate = state.tasks
    .map((task) => task.updateDate)
    .sort()
    .at(-1);
  const historyCount = sum(state.tasks.map((task) => task.historyLog.length));

  $("#storageSummary").innerHTML = `
    <div class="storage-row">
      <span>任务仓库</span>
      <strong>tasks</strong>
    </div>
    <div class="storage-row">
      <span>历史快照</span>
      <strong>${historyCount} 条</strong>
    </div>
    <div class="storage-row">
      <span>最后更新</span>
      <strong>${latestDate || "-"}</strong>
    </div>
  `;
}

function renderCategoryOptions() {
  const options = [...new Set(state.tasks.map((task) => task.category))]
    .sort((a, b) => a.localeCompare(b, "zh-CN"))
    .map((category) => `<option value="${escapeHtml(category)}"></option>`)
    .join("");
  $("#categoryOptions").innerHTML = options;
}

function handleBoardClick(event) {
  const card = event.target.closest("[data-task-id]");
  if (!card) return;
  const id = card.dataset.taskId;
  selectTask(id);
  openTaskModal(id);
}

async function handleTableClick(event) {
  const deleteButton = event.target.closest("[data-action='delete']");
  if (deleteButton) {
    event.stopPropagation();
    await confirmAndDeleteTask(deleteButton.dataset.taskId);
    return;
  }

  const row = event.target.closest("tr[data-task-id]");
  if (!row) return;
  selectTask(row.dataset.taskId);
  openTaskModal(row.dataset.taskId);
}

function selectTask(id) {
  state.selectedTaskId = id;
  renderTable();
  renderDetail();
}

function openTaskModal(id = "") {
  const modal = $("#taskModal");
  const form = $("#taskForm");
  const task = id ? state.tasks.find((item) => item.id === id) : null;

  form.reset();
  $("#formError").textContent = "";
  $("#taskId").value = task?.id || "";
  $("#taskModalTitle").textContent = task ? "编辑任务" : "新建任务";
  $("#taskName").value = task?.taskName || "";
  $("#category").value = task?.category || "";
  $("#priority").value = task?.priority || "中";
  $("#status").value = task?.status || "待启动";
  $("#progress").value = task?.progress ?? 0;
  $("#progressValue").textContent = `${task?.progress ?? 0}%`;
  $("#isProblem").checked = Boolean(task?.isProblem);
  $("#problemDesc").value = task?.problemDesc || "";
  syncProblemFieldState();

  modal.classList.add("is-visible");
  modal.setAttribute("aria-hidden", "false");
  $("#taskName").focus();
}

function closeTaskModal() {
  $("#taskModal").classList.remove("is-visible");
  $("#taskModal").setAttribute("aria-hidden", "true");
}

function syncProblemFieldState() {
  const isProblem = $("#isProblem").checked;
  $("#problemDesc").required = isProblem;
  $("#problemDesc").classList.toggle("is-required", isProblem);
}

async function saveTaskFromForm(event) {
  event.preventDefault();
  const id = $("#taskId").value;
  const today = todayKey();
  const existing = id ? await getTask(id) : null;
  const isProblem = $("#isProblem").checked;
  const taskName = $("#taskName").value.trim();
  const category = $("#category").value.trim();
  const priority = $("#priority").value;
  const status = $("#status").value;
  const progress = Number.parseInt($("#progress").value, 10);
  const problemDesc = $("#problemDesc").value.trim();

  const error = validateTaskForm({ taskName, category, priority, status, progress, isProblem, problemDesc });
  if (error) {
    $("#formError").textContent = error;
    return;
  }

  const task = normalizeTask({
    ...(existing || {}),
    id: existing?.id || generateId(),
    taskName,
    category,
    priority,
    status,
    isProblem,
    problemDesc: isProblem ? problemDesc : "",
    progress,
    createDate: existing?.createDate || today,
    updateDate: today,
    historyLog: existing?.historyLog || [],
  });

  task.historyLog = upsertDailySnapshot(task);
  await putTask(task);
  await refreshTasks();
  state.selectedTaskId = task.id;
  renderAll();
  closeTaskModal();
  showToast(existing ? "任务已更新，今日快照已同步" : "任务已新建，今日快照已记录");
}

function validateTaskForm(task) {
  if (!task.taskName) return "请填写任务名称。";
  if (!task.category) return "请填写板块分类。";
  if (!PRIORITIES.includes(task.priority)) return "请选择正确的优先级。";
  if (!STATUSES.includes(task.status)) return "请选择正确的状态。";
  if (!Number.isInteger(task.progress) || task.progress < 0 || task.progress > 100) return "完成度必须是 0 到 100 的整数。";
  if (task.isProblem && !task.problemDesc) return "标记为有问题时，必须填写问题描述。";
  return "";
}

async function confirmAndDeleteTask(id) {
  const task = state.tasks.find((item) => item.id === id);
  if (!task) return;
  const ok = await askConfirm(`确认删除「${task.taskName}」？删除后无法恢复。`);
  if (!ok) return;

  await deleteTask(id);
  await refreshTasks();
  renderAll();
  showToast("任务已删除");
}

function askConfirm(message) {
  $("#confirmMessage").textContent = message;
  $("#confirmModal").classList.add("is-visible");
  $("#confirmModal").setAttribute("aria-hidden", "false");
  $("#confirmOkButton").focus();
  return new Promise((resolve) => {
    pendingConfirmResolve = resolve;
  });
}

function resolveConfirm(value) {
  $("#confirmModal").classList.remove("is-visible");
  $("#confirmModal").setAttribute("aria-hidden", "true");
  $("#confirmMessage").textContent = "确认删除这条任务？";
  if (pendingConfirmResolve) {
    pendingConfirmResolve(value);
    pendingConfirmResolve = null;
  }
}

async function generateMonthlyReport() {
  const tasks = normalizeTasks(await queryTasks());
  const html = buildMonthlyReportHtml(tasks);
  window.purchaseWorkbenchLastReportHtml = html;
  const reportWindow = window.open("", "_blank");
  if (!reportWindow) {
    showToast("浏览器拦截了报告窗口，请允许弹窗后重试");
    return;
  }

  reportWindow.document.open();
  reportWindow.document.write(html);
  reportWindow.document.close();
  showToast("本月报告已生成");
}

function buildMonthlyReportHtml(tasks) {
  const monthLabel = todayKey().slice(0, 7);
  const total = tasks.length;
  const done = tasks.filter((task) => task.status === "已完成").length;
  const average = total ? Math.round(sum(tasks.map((task) => task.progress)) / total) : 0;
  const startValues = tasks.map((task) => sortedHistory(task)[0]?.progress ?? task.progress);
  const endValues = tasks.map((task) => sortedHistory(task).at(-1)?.progress ?? task.progress);
  const startAverage = startValues.length ? Math.round(sum(startValues) / startValues.length) : 0;
  const endAverage = endValues.length ? Math.round(sum(endValues) / endValues.length) : 0;
  const diff = endAverage - startAverage;
  const problems = tasks.filter((task) => task.isProblem);
  const topCategories = groupByCategory(tasks)
    .map(([category, groupTasks]) => ({
      category,
      average: Math.round(sum(groupTasks.map((task) => task.progress)) / groupTasks.length),
      count: groupTasks.length,
    }))
    .sort((a, b) => b.average - a.average)
    .slice(0, 3);

  return `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <title>${monthLabel} 采购任务月度报告</title>
    <style>
      :root { font-family: "Microsoft YaHei UI", "Segoe UI", Arial, sans-serif; color: #182536; background: #f3f6fb; }
      body { margin: 0; padding: 32px; background: #f3f6fb; }
      main { max-width: 1040px; margin: 0 auto; }
      header { display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; margin-bottom: 20px; }
      h1, h2, p { margin: 0; }
      h1 { font-size: 28px; }
      h2 { font-size: 18px; margin-bottom: 12px; }
      .sub { margin-top: 8px; color: #64788d; }
      .print { border: 1px solid #2563eb; background: #2563eb; color: #fff; border-radius: 8px; min-height: 38px; padding: 0 14px; font-weight: 700; cursor: pointer; }
      .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 20px 0; }
      .card, section { background: #fff; border: 1px solid #dce5f1; border-radius: 8px; padding: 16px; }
      .card span { color: #64788d; font-size: 12px; }
      .card strong { display: block; margin-top: 8px; font-size: 28px; }
      section { margin-top: 14px; }
      table { width: 100%; border-collapse: collapse; }
      th, td { border-bottom: 1px solid #dce5f1; padding: 10px; text-align: left; font-size: 13px; }
      th { background: #f8fbff; color: #40556d; }
      .problem { color: #b42318; font-weight: 700; }
      .rank { display: grid; gap: 10px; }
      .rank-row { display: grid; grid-template-columns: 160px 1fr 60px; gap: 12px; align-items: center; }
      .bar { height: 8px; background: #edf2f8; border-radius: 6px; overflow: hidden; }
      .bar i { display: block; height: 100%; background: #2563eb; }
      @media print { body { background: #fff; padding: 0; } .print { display: none; } .card, section { break-inside: avoid; } }
    </style>
  </head>
  <body>
    <main>
      <header>
        <div>
          <h1>${monthLabel} 采购任务月度报告</h1>
          <p class="sub">基于本地 IndexedDB 的 tasks 仓库生成，时间：${todayKey()}</p>
        </div>
        <button class="print" onclick="window.print()">打印 / 另存 PDF</button>
      </header>
      <div class="grid">
        <article class="card"><span>本月总任务数</span><strong>${total}</strong></article>
        <article class="card"><span>本月已完成数</span><strong>${done}</strong></article>
        <article class="card"><span>平均完成率</span><strong>${average}%</strong></article>
        <article class="card"><span>月初 vs 月末</span><strong>${formatSigned(diff)}%</strong></article>
      </div>
      <section>
        <h2>月初 / 月末进度对比</h2>
        <table>
          <thead><tr><th>月初平均</th><th>月末平均</th><th>变化</th></tr></thead>
          <tbody><tr><td>${startAverage}%</td><td>${endAverage}%</td><td>${formatSigned(diff)}%</td></tr></tbody>
        </table>
      </section>
      <section>
        <h2>问题任务清单</h2>
        ${
          problems.length
            ? `<table>
                <thead><tr><th>任务</th><th>板块</th><th>问题描述</th></tr></thead>
                <tbody>${problems
                  .map(
                    (task) =>
                      `<tr><td>${escapeHtml(task.taskName)}</td><td>${escapeHtml(task.category)}</td><td class="problem">${escapeHtml(task.problemDesc || "未填写")}</td></tr>`
                  )
                  .join("")}</tbody>
              </table>`
            : `<p class="sub">本月暂无问题任务。</p>`
        }
      </section>
      <section>
        <h2>完成度最高 Top 3 板块</h2>
        <div class="rank">
          ${
            topCategories.length
              ? topCategories
                  .map(
                    (item) => `
                      <div class="rank-row">
                        <strong>${escapeHtml(item.category)}</strong>
                        <span class="bar"><i style="width: ${item.average}%"></i></span>
                        <span>${item.average}%</span>
                      </div>
                    `
                  )
                  .join("")
              : `<p class="sub">暂无板块数据。</p>`
          }
        </div>
      </section>
    </main>
  </body>
</html>`;
}

function matchesSearch(task) {
  const query = state.searchQuery.toLowerCase();
  if (!query) return true;
  return task.taskName.toLowerCase().includes(query) || task.category.toLowerCase().includes(query);
}

function matchesTableFilter(task) {
  if (state.tableFilter === "urgent") return task.priority === "紧急";
  if (state.tableFilter === "pending") return task.status !== "已完成";
  if (state.tableFilter === "done") return task.status === "已完成";
  return true;
}

function normalizeTasks(tasks) {
  return tasks.map(normalizeTask).sort((a, b) => b.updateDate.localeCompare(a.updateDate));
}

function normalizeTask(task) {
  return {
    id: String(task.id || generateId()),
    taskName: String(task.taskName || "").trim(),
    category: String(task.category || "未分类").trim(),
    priority: PRIORITIES.includes(task.priority) ? task.priority : "中",
    status: STATUSES.includes(task.status) ? task.status : "待启动",
    isProblem: Boolean(task.isProblem),
    problemDesc: String(task.problemDesc || "").trim(),
    progress: clampInt(task.progress, 0, 100),
    createDate: isDateKey(task.createDate) ? task.createDate : todayKey(),
    updateDate: isDateKey(task.updateDate) ? task.updateDate : todayKey(),
    historyLog: Array.isArray(task.historyLog) ? task.historyLog.map(normalizeLog).filter(Boolean) : [],
  };
}

function normalizeLog(log) {
  if (!log || !isDateKey(log.date)) return null;
  return {
    date: log.date,
    progress: clampInt(log.progress, 0, 100),
    status: STATUSES.includes(log.status) ? log.status : "待启动",
  };
}

function upsertDailySnapshot(task) {
  const today = todayKey();
  const nextLog = sortedHistory(task);
  const snapshot = { date: today, progress: task.progress, status: task.status };
  const last = nextLog[nextLog.length - 1];

  if (last?.date === today) {
    nextLog[nextLog.length - 1] = snapshot;
  } else {
    nextLog.push(snapshot);
  }

  return nextLog;
}

function sortedHistory(task) {
  return [...(task.historyLog || [])].sort((a, b) => a.date.localeCompare(b.date));
}

function exposeLocalDiagnostics() {
  window.purchaseWorkbench = {
    getTasks: () => structuredClone(state.tasks),
    getKpis: () => ({
      total: state.tasks.length,
      pending: state.tasks.filter((task) => task.status !== "已完成").length,
      problem: state.tasks.filter((task) => task.isProblem).length,
      average: state.tasks.length ? Math.round(sum(state.tasks.map((task) => task.progress)) / state.tasks.length) : 0,
    }),
    buildMonthlyReportHtml: () => buildMonthlyReportHtml(state.tasks),
  };
}

function groupByCategory(tasks) {
  const map = new Map();
  tasks.forEach((task) => {
    if (!map.has(task.category)) map.set(task.category, []);
    map.get(task.category).push(task);
  });
  return [...map.entries()];
}

function statusClass(status) {
  return statusClassMap[status] || "status-progress";
}

function priorityKey(priority) {
  return { 紧急: "urgent", 高: "high", 中: "medium", 低: "low" }[priority] || "medium";
}

function generateId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function todayKey() {
  const date = new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function offsetDate(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function isDateKey(value) {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value);
}

function clampInt(value, min, max) {
  const number = Number.parseInt(value, 10);
  if (Number.isNaN(number)) return min;
  return Math.min(max, Math.max(min, number));
}

function sum(values) {
  return values.reduce((total, value) => total + value, 0);
}

function formatSigned(value) {
  if (value > 0) return `+${value}`;
  return String(value);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

let toastTimer;
function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("is-visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("is-visible"), 2500);
}
