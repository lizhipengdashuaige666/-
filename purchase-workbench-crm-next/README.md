# 采购工作台 CRM Next

这是下一版采购工作台的单页本地应用版本。它保持 HTML/CSS/JS 零依赖形态，但业务数据已经从静态 mock 改为浏览器 IndexedDB 的 `tasks` 对象仓库。

## 打开方式

直接打开：

```text
C:\Users\19811\.claude\projects\purchase-workbench-crm-next\index.html
```

更推荐在本目录启动本地静态服务：

```powershell
python -m http.server 4173 --bind 127.0.0.1
```

然后访问：

```text
http://127.0.0.1:4173/
```

`127.0.0.1` 只绑定本机，业务逻辑不依赖网络。

## 当前能力

- IndexedDB 本地持久化：对象仓库 `tasks`。
- 首次启动自动初始化 5 条示例任务。
- 支持任务新增、编辑、删除和二次确认。
- 保存任务时自动维护每日进度快照，同一天只保留一条记录。
- 看板按 `category` 动态生成列，新增/删除/改分类会立即重绘。
- 看板卡片按优先级排序，问题任务红色边框并显示警示标记。
- KPI 实时联动：总任务、待处理、有问题、平均完成率。
- 右侧详情展示任务字段和最近 7 天历史时间线。
- 顶栏搜索联动看板和表格。
- 表格分段筛选只影响表格，不改变全局看板。
- 月度报告生成静态 HTML，可打印或另存 PDF。

## 数据模型

`tasks` 仓库字段：

- `id`
- `taskName`
- `category`
- `priority`
- `status`
- `isProblem`
- `problemDesc`
- `progress`
- `createDate`
- `updateDate`
- `historyLog`

其中 `historyLog` 元素结构为：

```js
{ date: "YYYY-MM-DD", progress: 60, status: "进行中" }
```

## 后续路线

当前版本继续保留单页 HTML 本地运行形态。后续如需接入 API，可以先保留 IndexedDB 作为离线缓存，再增加同步层。

更完整的迁移说明见 `docs/MIGRATION_PLAN.md`，接口边界见 `docs/API_CONTRACT.md`。
