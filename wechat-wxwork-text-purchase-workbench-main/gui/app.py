from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QPlainTextEdit,
    QRadioButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from adapters import WeChatMessenger, WXWorkMessenger
from core.config import DEFAULT_OPEN_DIR, LOG_FILE, SUPPLIERS_FILE, load_suppliers, upsert_supplier
from core.confirm_history import needs_confirmation, record_confirmation
from core.parser import parse_document
from core.templates import ensure_default_templates, render_message
from unified import style as _style

_PRIMARY = "#0A84FF"

def _status_colors(shell: object | None = None) -> dict[str, str]:
    """Return status→color map from current theme tokens."""
    t = dict(_style.TOKENS)
    if shell is not None and hasattr(shell, '_theme_overrides'):
        t.update(shell._theme_overrides or {})
    return {
        "已发送": t.get("success", "#30D158"),
        "发送失败": t.get("danger", "#FF453A"),
        "待配置": t.get("warning", "#FF9F0A"),
        "请确认群聊": t.get("primary", "#0A84FF"),
        "已跳过": t.get("text3", "#6C6C72"),
    }

ADAPTERS = {
    "wechat": WeChatMessenger,
    "wxwork": WXWorkMessenger,
}

PLATFORM_TEXT = {
    "wechat": "微信",
    "wxwork": "企业微信",
}


def _position_top_right(dialog: QMessageBox) -> None:
    """将弹窗定位到最右边屏幕的右上角。"""
    screens = QApplication.screens()
    if not screens:
        return
    rightmost = max(screens, key=lambda s: s.geometry().right())
    geo = rightmost.availableGeometry()
    dialog.show()
    dialog.hide()
    x = geo.right() - dialog.width() - 20
    y = geo.top() + 40
    dialog.move(x, y)


@dataclass
class TaskItem:
    path: Path
    supplier: str
    business_type: str
    number: str
    source: str
    platform: str
    chat_name: str
    delivery_type: str = "instrument"
    status: str = "待发送"
    detail: str = ""
    checked: bool = False

    @property
    def group_key(self) -> tuple[str, str, str, str]:
        return (self.supplier, self.platform, self.chat_name, self.business_type)


class SupplierDialog(QDialog):
    def __init__(self, supplier: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新增供应商")
        self.setModal(True)
        self.resize(420, 240)

        self.supplier_edit = QLineEdit(supplier)
        self.platform_combo = QComboBox()
        self.platform_combo.addItem("微信", "wechat")
        self.platform_combo.addItem("企业微信", "wxwork")
        self.chat_edit = QLineEdit()
        self.chat_edit.setPlaceholderText("例如：安侣-某某采购沟通群")
        self.delivery_combo = QComboBox()
        self.delivery_combo.addItems(["仪器生产", "试剂生产"])

        form = QFormLayout()
        form.addRow("供应商", self.supplier_edit)
        form.addRow("平台", self.platform_combo)
        form.addRow("群聊名称", self.chat_edit)
        form.addRow("收货类型", self.delivery_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        if not self.supplier or not self.chat_name:
            QMessageBox.warning(self, "信息不完整", "供应商和群聊名称都要填写。")
            return
        self.accept()

    @property
    def supplier(self) -> str:
        return self.supplier_edit.text().strip()

    @property
    def platform(self) -> str:
        return str(self.platform_combo.currentData())

    @property
    def chat_name(self) -> str:
        return self.chat_edit.text().strip()

    @property
    def delivery_type(self) -> str:
        return "reagent" if self.delivery_combo.currentIndex() == 1 else "instrument"


class PurchaseWorkbench(QWidget):
    def __init__(self, parent: QWidget | None = None,
                 shell: object | None = None) -> None:
        super().__init__(parent)
        self._shell = shell
        ensure_default_templates()
        self.tasks: list[TaskItem] = []
        self._build_ui()
        # Stylesheet is managed by the unified shell
        self._log("工作台已启动，可以拖入 PDF 或文件夹。")

    def _build_ui(self) -> None:
        main = QHBoxLayout(self)
        main.setContentsMargins(24, 24, 24, 24)
        main.setSpacing(20)

        left = QVBoxLayout()
        left.setSpacing(12)
        left.addWidget(self._build_drop_panel())
        left.addWidget(self._build_filter_panel())

        # Table + empty-state placeholder, stacked
        self._table_stack = QStackedWidget()
        self._table_stack.addWidget(self._build_table())
        self._table_stack.addWidget(self._build_empty_state())
        self._table_stack.setCurrentIndex(1)  # start with empty state
        left.addWidget(self._table_stack, 1)

        left.addWidget(self._build_actions())

        sidebar = self._build_sidebar()
        main.addLayout(left, 1)
        main.addWidget(sidebar)

    def _build_panel_frame(self, name: str) -> QFrame:
        """Create a QFrame that respects QSS background colors."""
        f = QFrame()
        f.setObjectName(name)
        f.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        return f

    def _build_drop_panel(self) -> QWidget:
        panel = self._build_panel_frame("dropPanel")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(18, 14, 18, 14)

        text = QVBoxLayout()
        label = QLabel("📎 拖入 PDF 或采购订单文件夹")
        label.setObjectName("dropTitle")
        hint = QLabel("📄 支持：PO、双章合同、对账单、供应商往来对账单")
        hint.setObjectName("hint")
        text.addWidget(label)
        text.addWidget(hint)

        add_pdf = QPushButton("📄 选择 PDF")
        add_pdf.setObjectName("primaryBtn")
        add_pdf.clicked.connect(self.choose_pdf)
        add_folder = QPushButton("📁 选择文件夹")
        add_folder.setObjectName("secondaryBtn")
        add_folder.clicked.connect(self.choose_folder)

        layout.addLayout(text, 1)
        layout.addWidget(add_pdf)
        layout.addWidget(add_folder)
        return panel

    def _build_filter_panel(self) -> QWidget:
        panel = self._build_panel_frame("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 10)
        layout.setSpacing(8)

        # Row 0: filters
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        self.supplier_filter = QLineEdit()
        self.supplier_filter.setPlaceholderText("筛选供应商...")
        self.supplier_filter.textChanged.connect(self._refresh_table)

        self.type_filter = QComboBox()
        self.type_filter.addItem("全部类型", "")
        self.type_filter.currentIndexChanged.connect(self._refresh_table)

        self.platform_filter = QComboBox()
        self.platform_filter.addItem("全部平台", "")
        self.platform_filter.addItem("微信", "wechat")
        self.platform_filter.addItem("企业微信", "wxwork")
        self.platform_filter.currentIndexChanged.connect(self._refresh_table)

        self.status_filter = QComboBox()
        self.status_filter.addItem("全部状态", "")
        self.status_filter.currentIndexChanged.connect(self._refresh_table)

        reset_button = QPushButton("清除筛选")
        reset_button.setObjectName("secondaryBtn")
        reset_button.clicked.connect(self.clear_filters)

        filter_row.addWidget(self.supplier_filter)
        filter_row.addWidget(self.type_filter)
        filter_row.addWidget(self.platform_filter)
        filter_row.addWidget(self.status_filter)
        filter_row.addWidget(reset_button)
        layout.addLayout(filter_row)

        # Divider
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #3A3A3E;")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # Row 1: batch operations
        batch_label = QLabel("批量操作")
        batch_label.setObjectName("sectionLabel")
        layout.addWidget(batch_label)

        batch_row = QHBoxLayout()
        batch_row.setSpacing(10)

        self.fill_platform = QComboBox()
        self.fill_platform.addItem("批量设置平台", "")
        self.fill_platform.addItem("微信", "wechat")
        self.fill_platform.addItem("企业微信", "wxwork")

        self.fill_chat = QLineEdit()
        self.fill_chat.setPlaceholderText("批量设置群聊名称")

        self.fill_status = QComboBox()
        self.fill_status.addItem("批量设置状态", "")
        for status in ("待发送", "请确认群聊", "已发送", "已跳过"):
            self.fill_status.addItem(status, status)

        fill_button = QPushButton("应用到勾选")
        fill_button.setObjectName("primaryBtn")
        fill_button.clicked.connect(self.fill_checked_tasks)

        batch_row.addWidget(self.fill_platform)
        batch_row.addWidget(self.fill_chat, 1)
        batch_row.addWidget(self.fill_status)
        batch_row.addWidget(fill_button)
        layout.addLayout(batch_row)

        return panel

    def _build_table(self) -> QWidget:
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["", "文件", "供应商", "类型", "平台", "群聊", "状态"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 34)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.itemChanged.connect(self._sync_selection_from_check)
        self.table.itemSelectionChanged.connect(self._update_detail)
        self.table.setAlternatingRowColors(True)
        return self.table

    def _build_empty_state(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = QLabel("拖拽 PDF 文件到此处开始")
        icon.setObjectName("dropTitle")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint = QLabel("支持 PO、双章合同、对账单")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        layout.addWidget(icon)
        layout.addWidget(hint)
        layout.addStretch()
        return w

    def _build_actions(self) -> QWidget:
        panel = self._build_panel_frame("panel")
        layout = QHBoxLayout(panel)
        self.send_button = QPushButton("直接发送当前群聊")
        self.send_button.setObjectName("primaryBtn")
        self.send_button.clicked.connect(self.send_selected)
        self.search_button = QPushButton("搜索并确认发送")
        self.search_button.setObjectName("secondaryBtn")
        self.search_button.clicked.connect(self.search_selected)
        self.select_all_button = QPushButton("全选")
        self.select_all_button.setObjectName("secondaryBtn")
        self.select_all_button.clicked.connect(self.toggle_all_checked)
        skip_button = QPushButton("跳过选中")
        skip_button.setObjectName("secondaryBtn")
        skip_button.clicked.connect(self.skip_selected)
        clear_button = QPushButton("清空列表")
        clear_button.setObjectName("dangerButton")
        clear_button.clicked.connect(self.clear_tasks)
        layout.addWidget(self.send_button)
        layout.addWidget(self.search_button)
        layout.addWidget(self.select_all_button)
        layout.addWidget(skip_button)
        layout.addStretch(1)
        layout.addWidget(clear_button)
        return panel

    def _build_sidebar(self) -> QWidget:
        panel = self._build_panel_frame("sidebar")
        panel.setFixedWidth(330)
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        title = QLabel("任务详情")
        title.setObjectName("sectionTitle")
        self.detail_label = QLabel("未选择任务")
        self.detail_label.setObjectName("detailText")
        self.detail_label.setWordWrap(True)

        # Progress bar
        self._send_progress = QProgressBar()
        self._send_progress.setTextVisible(True)
        self._send_progress.setFormat("就绪")
        self._send_progress.setRange(0, 1)
        self._send_progress.setValue(0)
        self._send_progress.setVisible(False)

        config_button = QPushButton("打开供应商配置")
        config_button.setObjectName("secondaryBtn")
        config_button.clicked.connect(lambda: os.startfile(SUPPLIERS_FILE))
        log_button = QPushButton("打开日志")
        log_button.setObjectName("secondaryBtn")
        log_button.clicked.connect(lambda: os.startfile(LOG_FILE))

        message_title = QLabel("将发送的文字")
        message_title.setObjectName("sectionTitle")
        self.message_group = QButtonGroup(self)
        message_tabs = QGridLayout()
        message_tabs.setSpacing(8)
        self.message_preview = QPlainTextEdit()
        self.message_preview.setReadOnly(True)
        self.message_preview.setObjectName("messagePreview")
        for index, (label, key) in enumerate(
            (
                ("仪器生产", "instrument"),
                ("试剂生产", "reagent"),
                ("双章合同", "contract"),
                ("对账信息", "reconciliation"),
            )
        ):
            radio = QRadioButton(label)
            radio.setObjectName("messageTab")
            radio.setProperty("templateKey", key)
            self.message_group.addButton(radio)
            message_tabs.addWidget(radio, index // 2, index % 2)
            if index == 0:
                radio.setChecked(True)
        self.message_group.buttonClicked.connect(self._update_message_preview)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setObjectName("logBox")

        layout.addWidget(title)
        layout.addWidget(self.detail_label)
        layout.addWidget(self._send_progress)
        layout.addWidget(config_button)
        layout.addWidget(log_button)
        layout.addWidget(message_title)
        layout.addLayout(message_tabs)
        layout.addWidget(self.message_preview)
        layout.addWidget(QLabel("🗒️ 运行记录"))
        layout.addWidget(self.log_box, 1)
        self._update_message_preview()
        return panel

    def choose_pdf(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择 PDF",
            str(DEFAULT_OPEN_DIR if DEFAULT_OPEN_DIR.exists() else Path.home()),
            "PDF 文件 (*.pdf)",
        )
        self.add_paths([Path(file) for file in files])

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择文件夹",
            str(DEFAULT_OPEN_DIR if DEFAULT_OPEN_DIR.exists() else Path.home()),
        )
        if folder:
            self.add_paths([Path(folder)])

    def add_paths(self, paths: list[Path]) -> None:
        pdfs: list[Path] = []
        for path in paths:
            if path.is_dir():
                pdfs.extend(sorted(child for child in path.iterdir() if child.suffix.lower() == ".pdf"))
            elif path.suffix.lower() == ".pdf":
                pdfs.append(path)
            else:
                self._log(f"已忽略非 PDF：{path.name}")

        if not pdfs:
            self._log("没有找到 PDF 文件。")
            return

        existing = {task.path.resolve() for task in self.tasks}
        added = 0
        for pdf in pdfs:
            if pdf.resolve() in existing:
                continue
            task = self._create_task(pdf)
            self.tasks.append(task)
            added += 1

        self._refresh_table()
        self._log(f"已载入 {added} 个 PDF。")

    def _create_task(self, path: Path) -> TaskItem:
        parsed = parse_document(path)
        supplier = parsed.supplier or path.stem
        suppliers = load_suppliers()
        config = suppliers.get(supplier)
        if not config:
            dialog = SupplierDialog(supplier, self)
            if dialog.exec() == QDialog.Accepted:
                config = upsert_supplier(dialog.supplier, dialog.platform, dialog.chat_name, dialog.delivery_type)
                supplier = dialog.supplier
                status = "待发送"
                detail = "已新增供应商配置"
                delivery_type = dialog.delivery_type
            else:
                config = {"platform": "", "chat_name": "", "delivery_type": "instrument"}
                status = "待配置"
                detail = "供应商没有配置，禁止发送"
                delivery_type = "instrument"
        else:
            status = "待发送"
            detail = ""
            delivery_type = config.get("delivery_type", "instrument")

        return TaskItem(
            path=path.resolve(),
            supplier=supplier,
            business_type=parsed.business_type or "文件",
            number=parsed.number or path.stem,
            source=parsed.source,
            platform=str(config.get("platform", "")),
            chat_name=str(config.get("chat_name", "")),
            delivery_type=str(config.get("delivery_type", delivery_type)),
            status=status,
            detail=detail,
        )

    def _refresh_table(self) -> None:
        visible_tasks = self._visible_tasks()

        # Toggle between table and empty state
        if not self.tasks:
            self._table_stack.setCurrentIndex(1)
            return
        self._table_stack.setCurrentIndex(0)

        self._refresh_filter_options()
        self.table.setRowCount(len(visible_tasks))
        self.table.blockSignals(True)
        for row, task in enumerate(visible_tasks):
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            check.setCheckState(Qt.Checked if task.checked else Qt.Unchecked)
            task_index = self.tasks.index(task)
            check.setData(Qt.UserRole, task_index)
            self.table.setItem(row, 0, check)
            values = [
                task.path.name,
                task.supplier,
                task.business_type,
                PLATFORM_TEXT.get(task.platform, task.platform),
                task.chat_name,
                task.status,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, task_index)
                if col == 5:
                    self._style_status_item(item, task.status)
                self.table.setItem(row, col + 1, item)
        self.table.blockSignals(False)
        self.table.resizeRowsToContents()
        self._update_select_all_button()
        self._update_detail()

    def _style_status_item(self, item: QTableWidgetItem, status: str) -> None:
        colors = _status_colors(getattr(self, '_shell', None))
        item.setForeground(QColor(colors.get(status, _PRIMARY)))
        font = QFont()
        font.setBold(True)
        item.setFont(font)

    def _selected_tasks(self) -> list[TaskItem]:
        checked_indexes = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                task_index = item.data(Qt.UserRole)
                if isinstance(task_index, int):
                    checked_indexes.append(task_index)
        if checked_indexes:
            return [self.tasks[index] for index in checked_indexes if 0 <= index < len(self.tasks)]
        indexes = []
        for row_index in self.table.selectionModel().selectedRows():
            item = self.table.item(row_index.row(), 0)
            task_index = item.data(Qt.UserRole) if item else None
            if isinstance(task_index, int):
                indexes.append(task_index)
        return [self.tasks[index] for index in sorted(set(indexes)) if 0 <= index < len(self.tasks)]

    def _sync_selection_from_check(self, item: QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        task_index = item.data(Qt.UserRole)
        row = item.row()
        if isinstance(task_index, int) and 0 <= task_index < len(self.tasks):
            self.tasks[task_index].checked = item.checkState() == Qt.Checked
        self._update_select_all_button()
        self.table.blockSignals(True)
        try:
            self.table.selectRow(row)
        finally:
            self.table.blockSignals(False)
        self._update_detail()

    def _update_select_all_button(self) -> None:
        visible_tasks = self._visible_tasks()
        if visible_tasks and all(task.checked for task in visible_tasks):
            self.select_all_button.setText("取消全选")
        else:
            self.select_all_button.setText("全选")

    def _visible_tasks(self) -> list[TaskItem]:
        supplier_text = self.supplier_filter.text().strip() if hasattr(self, "supplier_filter") else ""
        type_value = self.type_filter.currentData() if hasattr(self, "type_filter") else ""
        platform_value = self.platform_filter.currentData() if hasattr(self, "platform_filter") else ""
        status_value = self.status_filter.currentData() if hasattr(self, "status_filter") else ""

        result = []
        for task in self.tasks:
            if supplier_text and supplier_text not in task.supplier:
                continue
            if type_value and task.business_type != type_value:
                continue
            if platform_value and task.platform != platform_value:
                continue
            if status_value and task.status != status_value:
                continue
            result.append(task)
        return result

    def _refresh_filter_options(self) -> None:
        if not hasattr(self, "type_filter"):
            return
        self._sync_combo_options(self.type_filter, "全部类型", sorted({task.business_type for task in self.tasks if task.business_type}))
        self._sync_combo_options(self.status_filter, "全部状态", sorted({task.status for task in self.tasks if task.status}))

    def _sync_combo_options(self, combo: QComboBox, all_label: str, values: list[str]) -> None:
        current = combo.currentData() or ""
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(all_label, "")
        for value in values:
            combo.addItem(value, value)
        index = combo.findData(current)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def clear_filters(self) -> None:
        self.supplier_filter.clear()
        self.type_filter.setCurrentIndex(0)
        self.platform_filter.setCurrentIndex(0)
        self.status_filter.setCurrentIndex(0)
        self._refresh_table()

    def fill_checked_tasks(self) -> None:
        selected = self._selected_tasks()
        if not selected:
            QMessageBox.information(self, "请选择任务", "请先勾选或选中要填充的任务。")
            return
        platform = self.fill_platform.currentData()
        chat_name = self.fill_chat.text().strip()
        status = self.fill_status.currentData()
        if not platform and not chat_name and not status:
            QMessageBox.information(self, "没有填充内容", "请先选择平台、输入群聊名称，或选择状态。")
            return
        for task in selected:
            if platform:
                task.platform = platform
            if chat_name:
                task.chat_name = chat_name
            if status:
                task.status = status
        self._refresh_table()
        self._log(f"已填充 {len(selected)} 个任务。")

    def _single_group_tasks(self) -> list[TaskItem] | None:
        selected = self._selected_tasks()
        if not selected:
            QMessageBox.information(self, "请选择任务", "请先选中要处理的 PDF。")
            return None
        bad = [task for task in selected if not task.platform or not task.chat_name]
        if bad:
            QMessageBox.warning(self, "配置不完整", "选中的任务缺少平台或群聊名称，不能发送。")
            return None
        return selected

    def _task_groups(self, tasks: list[TaskItem]) -> list[list[TaskItem]]:
        groups: dict[tuple[str, str, str, str], list[TaskItem]] = {}
        for task in tasks:
            groups.setdefault(task.group_key, []).append(task)
        return list(groups.values())

    def search_selected(self) -> None:
        selected = self._single_group_tasks()
        if not selected:
            return
        for group in self._task_groups(selected):
            if not self._search_and_send_group(group):
                break

    def _search_and_send_group(self, selected: list[TaskItem]) -> bool:
        task = selected[0]
        adapter_cls = ADAPTERS.get(task.platform)
        if not adapter_cls:
            QMessageBox.warning(self, "平台错误", f"不支持的平台：{task.platform}")
            return False
        adapter = adapter_cls()
        self._log(f"开始搜索群聊：{task.chat_name}")
        self._hide_for_desktop_action()
        try:
            ok = adapter.activate() and adapter.open_chat_for_manual_confirmation(task.chat_name)
            # 保持最小化，让用户看到微信搜索结果
            self._log("搜索关键词已输入，1.5s 后弹窗确认。")
            QApplication.processEvents()
            time.sleep(1.5)
            if ok:
                self._set_status(selected, "请确认群聊", "自动搜索已执行，请人工确认当前群聊。")
                result = self._confirm_current_chat_and_send(selected, "程序已尝试打开群聊。")
            else:
                self._set_status(selected, "请确认群聊", "自动搜索失败，请手动打开群聊后再确认发送。")
                result = self._confirm_current_chat_and_send(selected, "程序没有可靠进入群聊。请你先手动打开目标群聊，再回到这个弹窗点击「是」。")
        finally:
            self._restore_after_desktop_action()
        return result

    def send_selected(self) -> None:
        selected = self._single_group_tasks()
        if not selected:
            return
        for group in self._task_groups(selected):
            if not self._confirm_and_send_group(group):
                break

    def _confirm_and_send_group(self, selected: list[TaskItem]) -> bool:
        task = selected[0]
        confirm_text = (
            f"请确认当前 {PLATFORM_TEXT.get(task.platform, task.platform)} 窗口打开的是：\n\n"
            f"{task.chat_name}\n\n"
            f"确认后将发送 1 条文字通知和 {len(selected)} 个 PDF。"
        )
        if needs_confirmation(task.supplier, task.platform, task.chat_name):
            msg = QMessageBox(QMessageBox.Question, "发送前确认", confirm_text,
                              QMessageBox.Yes | QMessageBox.No, self)
            msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
            _position_top_right(msg)
            result = msg.exec()
            if result != QMessageBox.Yes:
                self._log("用户取消发送。")
                return False
            count = record_confirmation(task.supplier, task.platform, task.chat_name)
            self._log(f"已记录人工确认：{task.supplier} 第 {count}/3 次。")

        return self._send_tasks(selected)

    def _confirm_current_chat_and_send(self, selected: list[TaskItem], prefix: str) -> bool:
        task = selected[0]
        msg = QMessageBox(QMessageBox.Question, "确认并发送",
            f"{prefix}\n\n目标群聊：\n{task.chat_name}\n\n请确认当前打开的就是这个群聊。\n点击「是」后会立刻发送文字和 PDF。",
            QMessageBox.Yes | QMessageBox.No, self)
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
        _position_top_right(msg)
        result = msg.exec()
        if result != QMessageBox.Yes:
            self._log("用户取消发送。")
            return False
        if needs_confirmation(task.supplier, task.platform, task.chat_name):
            count = record_confirmation(task.supplier, task.platform, task.chat_name)
            self._log(f"已记录人工确认：{task.supplier} 第 {count}/3 次。")
        return self._send_tasks(selected)

    def _send_tasks(self, selected: list[TaskItem]) -> bool:
        task = selected[0]
        adapter_cls = ADAPTERS.get(task.platform)
        adapter = adapter_cls()
        self._log(f"开始发送：{task.supplier} / {task.chat_name}")

        # Show progress bar
        total = len(selected)
        self._send_progress.setVisible(True)
        self._send_progress.setRange(0, total)
        self._send_progress.setValue(0)
        self._send_progress.setFormat(f"发送中 0/{total}")

        self._hide_for_desktop_action()
        try:
            if not adapter.activate():
                self._restore_after_desktop_action()
                self._send_progress.setVisible(False)
                self._set_status(selected, "发送失败", "无法激活微信/企业微信窗口。")
                QMessageBox.critical(self, "发送失败", "无法激活微信/企业微信窗口。")
                return False

            message = self._message_for_task(task)
            if not adapter.send_text(message):
                self._restore_after_desktop_action()
                self._send_progress.setVisible(False)
                self._set_status(selected, "发送失败", "文字通知发送失败。")
                QMessageBox.critical(self, "发送失败", "文字通知发送失败。")
                return False

            for i, item in enumerate(selected):
                item.status = "发送中"
                self._refresh_table()
                self._send_progress.setValue(i)
                self._send_progress.setFormat(f"发送中 {i}/{total}")
                adapter._set_foreground(adapter.hwnd)
                adapter.send_file(item.path)
                time.sleep(2)
                item.status = "已发送"
                item.checked = False
                item.detail = "发送成功"
                self._refresh_table()
                self._send_progress.setValue(i + 1)
        finally:
            self._restore_after_desktop_action()
            self._send_progress.setVisible(False)

        # 再等一下确保所有文件都上传完成，然后才归档
        time.sleep(1)
        for item in selected:
            self._archive(item)
        self._refresh_table()
        self._set_status(selected, "已发送", "文字和 PDF 已发送完成。")
        self._log(f"发送完成：{task.supplier}，PDF 数量 {len(selected)}。")
        return True

    def _archive(self, item: TaskItem) -> None:
        """发送完成后归档文件到已发子目录，仅双章合同记录台账。"""
        try:
            bt = (item.business_type or "").lower()
            if "双章" in bt:
                sub = "已发/双章合同"
            elif "对账" in bt:
                sub = "已发/对账单"
            else:
                sub = "已发/电子档已发"
            d = item.path.parent / sub
            d.mkdir(parents=True, exist_ok=True)
            np = d / item.path.name
            if np.exists():
                np = d / f"{item.path.stem}_{datetime.now().strftime('%H%M%S')}.pdf"
            item.path.rename(np)
            item.path = np
            item.detail = f"→ {sub}"
            self._log(f"归档: {sub}/{item.path.name}")
            if "双章" in bt:
                self._record_to_excel(item)
        except OSError as e:
            self._log(f"归档失败: {item.path.name} — {e}")

    def _record_to_excel(self, item: TaskItem) -> None:
        """发送后记录到台账Excel。"""
        supplier_full = self._get_supplier_full_name(item.supplier)
        from unified.ledger import append_row
        ok = append_row(supplier_full, item.number, item.path.name, item.business_type)
        if ok:
            self._log(f"台账已记录: {supplier_full} | {item.number} | {datetime.now().strftime('%Y-%m-%d')}")
        else:
            self._log("台账写入失败: 文件被其他程序占用，请关闭Excel后重试")

    def _get_supplier_full_name(self, short_name: str) -> str:
        """查找供应商全称：优先 suppliers.json 的 full_name 字段，其次命名工具的 VendorCache。"""
        try:
            suppliers = load_suppliers()
            # 1. 精确匹配 suppliers.json 的 key
            if short_name in suppliers:
                entry = suppliers[short_name]
                if entry.get("full_name"):
                    return str(entry["full_name"])
            # 2. 遍历查找 full_name 匹配
            for key, entry in suppliers.items():
                if entry.get("full_name") and short_name in (key, entry.get("full_name", "")):
                    return str(entry["full_name"])
            # 3. 尝试命名工具的 VendorCache
            import json
            vendor_cache_path = Path(r"C:\Users\19811\.claude\projects\pdf-windows-11-python-3-12\cache\vendor_cache.json")
            if vendor_cache_path.exists():
                data = json.loads(vendor_cache_path.read_text(encoding="utf-8"))
                for vendor in data.get("vendors", []):
                    vn = str(vendor.get("vendor_name", ""))
                    vs = str(vendor.get("vendor_short_name", ""))
                    aliases = [str(a) for a in vendor.get("aliases", [])]
                    if short_name in (vn, vs, *aliases):
                        return vn
        except Exception:
            pass
        # 4. 都找不到就返回原名
        return short_name

    def skip_selected(self) -> None:
        selected = self._selected_tasks()
        if not selected:
            return
        for task in selected:
            task.checked = False
        self._set_status(selected, "已跳过", "用户跳过。")

    def toggle_all_checked(self) -> None:
        visible_tasks = self._visible_tasks()
        if not visible_tasks:
            return
        checked = not all(task.checked for task in visible_tasks)
        for task in visible_tasks:
            task.checked = checked
        self._refresh_table()
        self._update_select_all_button()

    def clear_tasks(self) -> None:
        self.tasks.clear()
        self._refresh_table()
        self._log("任务列表已清空。")

    def _set_status(self, tasks: list[TaskItem], status: str, detail: str) -> None:
        for task in tasks:
            task.status = status
            task.detail = detail
        self._refresh_table()

    def _update_detail(self) -> None:
        selected = self._selected_tasks()
        if not selected:
            self.detail_label.setText("未选择任务")
            return
        task = selected[0]
        self.detail_label.setText(
            "\n".join(
                (
                    f"文件：{task.path.name}",
                    f"供应商：{task.supplier}",
                    f"业务类型：{task.business_type}",
                    f"编号：{task.number}",
                    f"识别来源：{task.source}",
                    f"平台：{PLATFORM_TEXT.get(task.platform, task.platform)}",
                    f"群聊：{task.chat_name}",
                    f"状态：{task.status}",
                    f"说明：{task.detail or '无'}",
                )
            )
        )

    def _log(self, text: str) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        t = dict(_style.TOKENS)
        if getattr(self, '_shell', None) is not None and hasattr(self._shell, '_theme_overrides'):
            t.update(self._shell._theme_overrides or {})
        primary = t.get("primary", _PRIMARY)
        text_c = t.get("text", "#F5F5F7")
        self.log_box.appendHtml(
            f'<div style="color:{text_c}; padding:2px 0; border-left:3px solid {primary};'
            f'padding-left:6px; margin:1px 0;">{now}  {text}</div>'
        )

    def _selected_message_key(self) -> str:
        button = self.message_group.checkedButton()
        return str(button.property("templateKey")) if button else "instrument"

    def _message_for_task(self, task: TaskItem) -> str:
        """按原版流程：用task的业务类型判定模板，用task/radio的收货类型填充地址。"""
        bt = (task.business_type or "").lower()
        dv = getattr(task, 'delivery_type', None) or self._selected_message_key()
        if "合同" in bt:
            return render_message("双章合同")
        if "对账" in bt:
            return render_message("对账单")
        return render_message("PO", dv)

    def _update_message_preview(self) -> None:
        key = self._selected_message_key()
        if key == "reagent":
            message = render_message("PO", "reagent")
        elif key == "contract":
            message = render_message("双章合同")
        elif key == "reconciliation":
            message = render_message("对账单")
        else:
            message = render_message("PO", "instrument")
        self.message_preview.setPlainText(message)

    def _hide_for_desktop_action(self) -> None:
        self.window().showMinimized()
        QApplication.processEvents()
        time.sleep(0.5)

    def _restore_after_desktop_action(self) -> None:
        self.window().showNormal()
        self.window().raise_()
        self.window().activateWindow()
        QApplication.processEvents()


def run() -> int:
    app = QApplication.instance() or QApplication([])
    window = PurchaseWorkbench()
    window.show()
    return app.exec()
