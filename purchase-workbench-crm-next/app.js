const modules = {
  dashboard: {
    eyebrow: "采购运营",
    title: "工作台总览",
    quickTitle: "采购文件处理",
    flowTitle: "采购处理链路",
    tableTitle: "待处理采购单",
    metrics: ["18", "7", "92%", "¥48.6万"],
  },
  orders: {
    eyebrow: "订单协同",
    title: "采购订单",
    quickTitle: "订单导入",
    flowTitle: "订单确认链路",
    tableTitle: "采购订单列表",
    metrics: ["24", "5", "89%", "¥52.1万"],
  },
  contracts: {
    eyebrow: "合同管理",
    title: "合同中心",
    quickTitle: "合同归档",
    flowTitle: "合同处理链路",
    tableTitle: "合同任务列表",
    metrics: ["9", "12", "96%", "¥31.8万"],
  },
  suppliers: {
    eyebrow: "供应链关系",
    title: "供应商",
    quickTitle: "供应商资料",
    flowTitle: "供应商准入链路",
    tableTitle: "供应商跟进列表",
    metrics: ["11", "3", "94%", "¥40.3万"],
  },
  messages: {
    eyebrow: "触达协同",
    title: "群聊发送",
    quickTitle: "发送素材",
    flowTitle: "消息发送链路",
    tableTitle: "待发送清单",
    metrics: ["32", "4", "91%", "¥44.7万"],
  },
  watermark: {
    eyebrow: "票据识别",
    title: "水单识别",
    quickTitle: "水单上传",
    flowTitle: "识别审核链路",
    tableTitle: "水单核验列表",
    metrics: ["14", "2", "88%", "¥22.9万"],
  },
  reports: {
    eyebrow: "经营分析",
    title: "数据报表",
    quickTitle: "报表导入",
    flowTitle: "指标复核链路",
    tableTitle: "报表任务列表",
    metrics: ["6", "1", "97%", "¥63.5万"],
  },
  settings: {
    eyebrow: "后台配置",
    title: "系统设置",
    quickTitle: "配置备份",
    flowTitle: "权限与规则链路",
    tableTitle: "配置变更列表",
    metrics: ["5", "0", "100%", "¥0"],
  },
};

const orders = [
  {
    id: "PO-240630-018",
    supplier: "杭州辰光包装",
    category: "包装材料",
    amount: "¥86,400",
    status: "pending",
    statusText: "待确认",
    owner: "李鹏",
    updated: "09:42",
    sla: "3h 20m",
  },
  {
    id: "PO-240630-017",
    supplier: "深圳华科电子",
    category: "电子元件",
    amount: "¥128,900",
    status: "urgent",
    statusText: "加急",
    owner: "陈婷",
    updated: "09:21",
    sla: "1h 10m",
  },
  {
    id: "CT-240629-066",
    supplier: "宁波远航物流",
    category: "运输服务",
    amount: "¥42,700",
    status: "progress",
    statusText: "处理中",
    owner: "周岩",
    updated: "08:58",
    sla: "6h 40m",
  },
  {
    id: "PO-240629-052",
    supplier: "苏州锐达五金",
    category: "五金耗材",
    amount: "¥19,300",
    status: "done",
    statusText: "已完成",
    owner: "王敏",
    updated: "昨天",
    sla: "已闭环",
  },
  {
    id: "WM-240628-031",
    supplier: "上海蓝桥贸易",
    category: "水单核验",
    amount: "¥63,200",
    status: "pending",
    statusText: "待确认",
    owner: "李鹏",
    updated: "昨天",
    sla: "4h 05m",
  },
];

const workflow = [
  {
    title: "待识别",
    items: [
      { name: "3 份 PDF 合同待命名", meta: "合同中心", status: "处理中", type: "progress" },
      { name: "5 张水单待 OCR", meta: "水单识别", status: "待确认", type: "pending" },
    ],
  },
  {
    title: "待协同",
    items: [
      { name: "华科电子价格需复核", meta: "采购订单", status: "加急", type: "urgent" },
      { name: "供应商群聊发送确认", meta: "群聊发送", status: "处理中", type: "progress" },
    ],
  },
  {
    title: "待归档",
    items: [
      { name: "辰光包装合同归档", meta: "合同中心", status: "待确认", type: "pending" },
      { name: "远航物流回执入库", meta: "采购订单", status: "已完成", type: "done" },
    ],
  },
];

const supplierRisks = [
  { name: "深圳华科电子", note: "报价波动", score: 82 },
  { name: "杭州辰光包装", note: "响应延迟", score: 54 },
  { name: "宁波远航物流", note: "稳定", score: 28 },
];

const timelines = {
  "PO-240630-018": [
    ["采购单生成", "09:12 从 Excel 导入，已完成字段校验"],
    ["供应商确认", "09:42 已推送至企微群，等待报价确认"],
    ["下一步", "超过 12:00 未确认将自动提醒负责人"],
  ],
  "PO-240630-017": [
    ["价格异常", "09:21 单价高于近 30 日均值 8.4%"],
    ["已标记加急", "需要主管在 1 小时内复核"],
    ["下一步", "通过后进入合同生成队列"],
  ],
};

let currentView = "dashboard";
let currentFilter = "all";
let selectedOrderId = orders[0].id;

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function statusClass(status) {
  const map = {
    urgent: "status-urgent",
    pending: "status-pending",
    progress: "status-progress",
    done: "status-done",
  };
  return map[status] || "status-progress";
}

function setActiveView(view) {
  currentView = view;
  const config = modules[view] || modules.dashboard;

  $("#moduleEyebrow").textContent = config.eyebrow;
  $("#moduleTitle").textContent = config.title;
  $("#quickTitle").textContent = config.quickTitle;
  $("#flowTitle").textContent = config.flowTitle;
  $("#tableTitle").textContent = config.tableTitle;

  const [pending, contracts, rate, amount] = config.metrics;
  $("#metricPending").textContent = pending;
  $("#metricContracts").textContent = contracts;
  $("#metricRate").textContent = rate;
  $("#metricAmount").textContent = amount;

  $$(".nav-item, .tab-button").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === view);
  });

  renderWorkflow();
  renderOrders();
  showToast(`已切换到：${config.title}`);
}

function renderWorkflow() {
  const board = $("#workflowBoard");
  board.innerHTML = workflow
    .map(
      (column) => `
        <article class="workflow-column">
          <header>
            <h3>${column.title}</h3>
            <span class="count-pill">${column.items.length}</span>
          </header>
          ${column.items
            .map(
              (item) => `
                <div class="task-row">
                  <strong>${item.name}</strong>
                  <div class="task-meta">
                    <span>${item.meta}</span>
                    <span class="status-pill ${statusClass(item.type)}">${item.status}</span>
                  </div>
                </div>
              `
            )
            .join("")}
        </article>
      `
    )
    .join("");
}

function orderMatches(order, query) {
  if (!query) return true;
  const haystack = `${order.id} ${order.supplier} ${order.category} ${order.owner}`.toLowerCase();
  return haystack.includes(query.toLowerCase());
}

function filteredOrders() {
  const query = $("#globalSearch").value.trim();
  return orders.filter((order) => {
    const filterMatch = currentFilter === "all" || order.status === currentFilter;
    return filterMatch && orderMatches(order, query);
  });
}

function renderOrders() {
  const rows = filteredOrders();
  const body = $("#orderTableBody");

  if (!rows.length) {
    body.innerHTML = `
      <tr>
        <td colspan="8" class="empty-row">没有匹配的业务记录</td>
      </tr>
    `;
    return;
  }

  body.innerHTML = rows
    .map(
      (order) => `
        <tr data-id="${order.id}" class="${order.id === selectedOrderId ? "is-selected" : ""}">
          <td><input type="checkbox" aria-label="选择 ${order.id}" /></td>
          <td><strong>${order.id}</strong></td>
          <td>${order.supplier}</td>
          <td>${order.category}</td>
          <td>${order.amount}</td>
          <td><span class="status-pill ${statusClass(order.status)}">${order.statusText}</span></td>
          <td>${order.owner}</td>
          <td>${order.updated}</td>
        </tr>
      `
    )
    .join("");

  body.querySelectorAll("tr[data-id]").forEach((row) => {
    row.addEventListener("click", (event) => {
      if (event.target.type === "checkbox") return;
      selectedOrderId = row.dataset.id;
      renderOrders();
      renderDetail();
    });
  });
}

function renderDetail() {
  const order = orders.find((item) => item.id === selectedOrderId) || orders[0];
  $("#detailTitle").textContent = order.id;
  $("#detailStatus").textContent = order.statusText;
  $("#detailSupplier").textContent = order.supplier;
  $("#detailAmount").textContent = order.amount;
  $("#detailOwner").textContent = order.owner;
  $("#detailSla").textContent = order.sla;

  const events = timelines[order.id] || [
    ["资料同步", "已从本地业务模块读取基础字段"],
    ["规则校验", "状态、金额、供应商名称均通过前端校验"],
    ["下一步", "等待后端服务返回真实执行结果"],
  ];

  $("#timeline").innerHTML = events
    .map(
      ([title, text]) => `
        <div class="timeline-item">
          <span class="timeline-dot"></span>
          <div>
            <strong>${title}</strong>
            <span>${text}</span>
          </div>
        </div>
      `
    )
    .join("");
}

function renderSupplierRisk() {
  $("#supplierList").innerHTML = supplierRisks
    .map(
      (supplier) => `
        <div class="supplier-item">
          <div class="supplier-main">
            <strong>${supplier.name}</strong>
            <span>${supplier.note}</span>
          </div>
          <div class="risk-meter"><i style="width: ${supplier.score}%"></i></div>
        </div>
      `
    )
    .join("");
}

let toastTimer;
function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("is-visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("is-visible"), 2200);
}

function bindEvents() {
  $$(".nav-item, .tab-button").forEach((button) => {
    button.addEventListener("click", () => setActiveView(button.dataset.view));
  });

  $$(".segmented button").forEach((button) => {
    button.addEventListener("click", () => {
      currentFilter = button.dataset.filter;
      $$(".segmented button").forEach((item) => item.classList.remove("is-active"));
      button.classList.add("is-active");
      renderOrders();
    });
  });

  $("#globalSearch").addEventListener("input", renderOrders);

  $("#selectAll").addEventListener("change", (event) => {
    $$("#orderTableBody input[type='checkbox']").forEach((checkbox) => {
      checkbox.checked = event.target.checked;
    });
    showToast(event.target.checked ? "已选择当前列表记录" : "已取消选择");
  });

  $("#pickFileButton").addEventListener("click", () => $("#fileInput").click());
  $("#fileInput").addEventListener("change", (event) => {
    const count = event.target.files.length;
    if (count) showToast(`已加入 ${count} 个文件到处理队列`);
  });

  const uploadZone = $("#uploadZone");
  ["dragenter", "dragover"].forEach((name) => {
    uploadZone.addEventListener(name, (event) => {
      event.preventDefault();
      uploadZone.classList.add("is-dragover");
    });
  });
  ["dragleave", "drop"].forEach((name) => {
    uploadZone.addEventListener(name, (event) => {
      event.preventDefault();
      uploadZone.classList.remove("is-dragover");
    });
  });
  uploadZone.addEventListener("drop", (event) => {
    const count = event.dataTransfer.files.length;
    if (count) showToast(`已接收 ${count} 个拖拽文件`);
  });

  $("#notifyButton").addEventListener("click", () => showToast("3 条提醒：价格复核、合同归档、供应商确认"));
  $("#filterButton").addEventListener("click", () => showToast("筛选面板将在后端接入后启用"));
  $("#addTaskButton").addEventListener("click", () => showToast("已创建一条本地演示任务"));
  $("#openDetailButton").addEventListener("click", () => showToast(`打开 ${selectedOrderId} 的详情抽屉`));
}

bindEvents();
renderWorkflow();
renderOrders();
renderDetail();
renderSupplierRisk();
