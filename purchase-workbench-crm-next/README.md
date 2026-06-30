# 采购工作台 CRM Next

这是下一版采购工作台的零依赖前端原型，目标是把现有 PySide 工具逐步迁移到更适合 B 端 CRM 软件长期维护的桌面架构。

## 打开方式

直接打开：

```text
C:\Users\19811\.claude\projects\purchase-workbench-crm-next\index.html
```

或者在本目录启动一个本地静态服务：

```powershell
python -m http.server 4173
```

然后访问 `http://127.0.0.1:4173/`。

## 当前范围

- 已完成 CRM 风格工作台首屏、左侧导航、顶部搜索、指标区、流程看板、业务列表、右侧详情、供应商风险和文件拖拽入口。
- 已实现前端交互：模块切换、状态筛选、搜索、行选择、批量勾选、文件选择、拖拽反馈和 Toast。
- 暂用本地 mock 数据，不读写真实业务文件。
- 图标为零依赖内置 SVG，后续 React 版本建议替换为 `lucide-react`。

## 推荐落地路线

1. `V0`：当前静态原型，用于确认信息架构、Figma 走向和核心页面密度。
2. `V1`：迁移到 React + TypeScript + Vite，拆出 Design Tokens、Layout、Table、Drawer、Uploader 等组件。
3. `V2`：接入 Tauri 桌面壳，保留 Python 作为 sidecar 服务处理 PDF、Excel、水单 OCR、企微发送等能力。
4. `V3`：补齐权限、审计日志、任务队列、异常重试、真实数据库和自动更新。

更完整的迁移说明见 `docs/MIGRATION_PLAN.md`，接口边界见 `docs/API_CONTRACT.md`。
