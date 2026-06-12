# 采购合同 PDF 自动命名工具

本工具用于 Windows 11 + Python 3.12 环境下批量处理扫描版采购合同 PDF。

## 当前命名规则

```text
供方简称双章合同合同编号.pdf
```

示例：

```text
迈瑞双章合同PO20260525001.pdf
```

## 核心功能

- 扫描 `PDF_DIR` 指定目录下的 PDF。
- 使用 PyMuPDF 渲染 PDF 首页。
- 使用 PaddleOCR 识别首页文本。
- 提取供方名称和合同编号。
- 自动清理非法文件名字符。
- 自动避免重名冲突。
- 写入处理日志 `logs/rename_log.csv`。
- 使用历史缓存 `cache/vendor_cache.json` 记录供方全称、简称和别名。
- 后续命中历史供方时自动匹配简称，减少人工确认。
- 使用 OCR 文本缓存 `cache/ocr_text_cache.json`，重复处理同一未完成文件时不重复 OCR。
- 文件重命名后保留在原采购目录。
- 采购文件自动发送工作台会自动扫描原采购目录，不再要求把文件搬到 C 盘。

## 常用入口

```powershell
python batch_run.py
```

批处理模式会直接扫描并重命名目标目录中的 PDF，适合日常使用。

```powershell
python main.py
```

GUI 模式会显示识别结果。缓存命中的供应商会自动重命名；未命中或字段不完整时才需要人工确认。

## 配置

配置文件：`.env`

```env
PDF_DIR=D:\采购工作\采购订单电子档
RECURSIVE_SCAN=false
RENDER_DPI=180
LOG_DIR=logs
TEMP_DIR=temp
CACHE_DIR=cache
OCR_LANG=ch
WINDOW_TITLE=采购合同 PDF 自动命名工具
SEND_PLATFORM_ENABLED=false
SEND_PLATFORM_DIR=C:\Users\19811\Documents\Codex\2026-05-25\prd-codex-windows-gui-pdf-pdf
SEND_PLATFORM_INBOX_DIR=D:\采购工作\采购订单电子档
```

说明：

- `PDF_DIR`：待处理 PDF 目录。
- `RENDER_DPI`：PDF 首页渲染分辨率，默认 180。值越高识别可能越稳，但速度越慢。
- `CACHE_DIR`：缓存目录，默认 `cache`。
- `SEND_PLATFORM_ENABLED`：是否在命名成功后移动文件。当前为 `false`，表示文件留在原目录。
- `SEND_PLATFORM_INBOX_DIR`：保留配置项；当前指向原采购目录，不再指向 C 盘。

## 与自动发送工作台串联

当前串联路径：

```text
D:\采购工作\采购订单电子档
  -> OCR 命名，文件仍保留在原目录
  -> 采购文件自动发送工作台自动扫描该目录
```

运行 `python batch_run.py` 后，成功处理的 PDF 会在原采购目录内完成重命名。打开自动发送工作台后，会自动读取 `D:\采购工作\采购订单电子档` 里的文件并显示在任务列表中。

## 缓存机制

成功识别或整理过的供应商会写入：

```text
cache/vendor_cache.json
```

缓存内容包括：

- 供方全称
- 供方简称
- 别名
- 出现次数
- 首次出现时间
- 最近出现时间

批处理运行时会先读取历史日志和已有文件名补充缓存，然后再处理新文件。

OCR 文本缓存按 PDF 绝对路径、文件大小、修改时间判断是否命中。命中后仍会使用当前提取规则重新提取供方和合同编号，因此不会降低识别质量；如果要强制重新 OCR，删除 `cache/ocr_text_cache.json` 即可。

## 性能优化

当前默认优化：

- OCR 使用 `PP-OCRv5_mobile_det` 和 `PP-OCRv5_mobile_rec`。
- 关闭 `MKLDNN/oneDNN`，避开当前 Windows CPU 环境下的兼容问题。
- PDF 渲染 DPI 默认从 220 降到 180。
- OCR 检测边长限制为 960。
- GUI 模式改为懒加载 OCR：如果目录内文件都已命名，不再等待 OCR 模型启动。
- 未完成文件重复处理时优先复用 OCR 文本缓存，减少重复识别耗时。

## 界面

GUI 已按工作台风格调整：

- 顶部任务设置区
- 左侧待确认文件和 OCR 内容
- 右侧处理日志
- 浅灰背景、白色卡片、主次按钮分层

如果个别文件识别质量下降，可以把 `.env` 中的 `RENDER_DPI` 调到 200。

## 主要文件

```text
main.py
batch_run.py
app/
  config.py
  extractor.py
  logger_service.py
  ocr_service.py
  ocr_cache.py
  pdf_service.py
  renamer.py
  vendor_cache.py
```
