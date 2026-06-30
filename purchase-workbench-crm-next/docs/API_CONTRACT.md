# 前后端接口边界草案

这份文档用于后续把现有 Python 能力接入 React/Tauri 前端。当前还是草案，先确定边界，避免 UI 层直接读取和修改复杂业务文件。

## 通用响应

```ts
type ApiResponse<T> = {
  ok: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    detail?: unknown;
  };
};
```

## 采购订单

```ts
type PurchaseOrder = {
  id: string;
  supplierName: string;
  category: string;
  amount: number;
  currency: "CNY" | "USD";
  status: "urgent" | "pending" | "progress" | "done";
  owner: string;
  updatedAt: string;
  slaText: string;
};
```

建议接口：

- `GET /api/orders?status=&keyword=&page=`
- `GET /api/orders/:id`
- `POST /api/orders/import`
- `POST /api/orders/:id/confirm`
- `POST /api/orders/:id/send-message`

## 合同中心

```ts
type ContractTask = {
  id: string;
  orderId?: string;
  fileName: string;
  supplierName: string;
  status: "pending_rename" | "pending_archive" | "archived" | "error";
  suggestedName?: string;
  updatedAt: string;
};
```

建议接口：

- `POST /api/contracts/rename-preview`
- `POST /api/contracts/archive`
- `GET /api/contracts/tasks`

## 水单识别

```ts
type WatermarkRecord = {
  id: string;
  fileName: string;
  supplierName?: string;
  amount?: number;
  confidence: number;
  status: "pending" | "review" | "confirmed" | "error";
};
```

建议接口：

- `POST /api/watermarks/recognize`
- `GET /api/watermarks`
- `POST /api/watermarks/:id/confirm`

## 供应商

```ts
type Supplier = {
  id: string;
  name: string;
  responseRate: number;
  riskScore: number;
  tags: string[];
  lastContactAt: string;
};
```

建议接口：

- `GET /api/suppliers?keyword=`
- `GET /api/suppliers/:id`
- `PATCH /api/suppliers/:id`

## 企微/群聊发送

```ts
type MessageJob = {
  id: string;
  targetGroup: string;
  templateName: string;
  status: "draft" | "queued" | "sending" | "sent" | "failed";
  createdAt: string;
};
```

建议接口：

- `POST /api/messages/preview`
- `POST /api/messages/send`
- `GET /api/messages/jobs`

## 本地桌面命令

如果使用 Tauri command，可先保留这些命令名：

- `import_purchase_files(paths: string[])`
- `rename_contracts(paths: string[])`
- `recognize_watermarks(paths: string[])`
- `send_group_message(jobId: string)`
- `open_local_path(path: string)`
