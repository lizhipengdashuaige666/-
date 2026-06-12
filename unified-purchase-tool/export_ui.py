#!/usr/bin/env python
# Generate Qt Designer .ui files for the procurement workbench.

from pathlib import Path

OUT = Path(__file__).parent / "ui_exports"
OUT.mkdir(exist_ok=True)

I2 = "  "
I4 = "    "
I6 = "      "


def ui(path, cls_name, wcls, wname, title, body):
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<ui version="4.0">\n'
        f' <class>{cls_name}</class>\n'
        f' <widget class="{wcls}" name="{wname}">\n'
        f'  <property name="windowTitle"><string>{title}</string></property>\n'
        f'{body}'
        f' </widget>\n'
        f' <resources/>\n'
        f'</ui>\n'
    )
    path.write_text(xml, encoding="utf-8")
    print(f"  -> {path.name}")


# Each helper builds a plain string. No deep nesting tricks.

def tag(name, text, indent=I4):
    return f'{indent}<{name}>{text}</{name}>\n'

def prop(name, val_tag, val_text, indent=I4):
    inner = tag(val_tag, val_text, indent + I2)
    return f'{indent}<property name="{name}">\n{inner}{indent}</property>\n'

def string_prop(name, value, indent=I4):
    return prop(name, "string", value, indent)

def bool_prop(name, indent=I4):
    return prop(name, "bool", "true", indent)

def num_prop(name, value, indent=I4):
    return prop(name, "number", str(value), indent)

def enum_prop(name, value, indent=I4):
    return prop(name, "enum", value, indent)

def size_prop(w, h, indent=I4):
    inner = f'{indent+I2}<size>\n{indent+I6}<width>{w}</width>\n{indent+I6}<height>{h}</height>\n{indent+I2}</size>\n'
    return f'{indent}<property name="size">\n{inner}{indent}</property>\n'

def margin_props(l, t, r, b, indent=I4):
    return (
        num_prop("leftMargin", l, indent) +
        num_prop("topMargin", t, indent) +
        num_prop("rightMargin", r, indent) +
        num_prop("bottomMargin", b, indent)
    )

def widget_open(cls, name, indent=I2):
    return f'{indent}<widget class="{cls}" name="{name}">\n'

def widget_close(indent=I2):
    return f'{indent}</widget>\n'

def widget(cls, name, body="", indent=I2):
    return widget_open(cls, name, indent) + body + widget_close(indent)

def layout_open(cls, name, stretch="", indent=I2):
    st = f' stretch="{stretch}"' if stretch else ""
    return f'{indent}<layout class="{cls}" name="{name}"{st}>\n'

def layout_close(indent=I2):
    return f'{indent}</layout>\n'

def layout(cls, name, body, stretch="", indent=I2):
    return layout_open(cls, name, stretch, indent) + body + layout_close(indent)

def item(body, indent=I2):
    return f'{indent}<item>\n{body}{indent}</item>\n'

def spacer(name, w, h, orientation="Horizontal", indent=I2):
    return (
        f'{indent}<spacer name="{name}">\n'
        f'{indent+I2}<property name="orientation"><enum>Qt::{orientation}</enum></property>\n'
        f'{indent+I2}<property name="sizeHint" stdset="0">\n'
        f'{indent+I4}<size>\n'
        f'{indent+I6}<width>{w}</width>\n'
        f'{indent+I6}<height>{h}</height>\n'
        f'{indent+I4}</size>\n'
        f'{indent+I2}</property>\n'
        f'{indent}</spacer>\n'
    )


# =========================================================================
# 1. PurchaseWorkbench
# =========================================================================

def export_workbench():
    DropBody = (
        margin_props(18, 14, 18, 14, I6)
        + item(layout("QVBoxLayout", "dropTextLayout",
            item(widget("QLabel", "dropTitle", string_prop("text", "Drag PDF files or a folder here", I6), I4))
            + item(widget("QLabel", "dragHint", string_prop("text", "Supports: PO, contract, reconciliation, statement", I6), I4))
        , stretch="", indent=I4))
        + item(widget("QPushButton", "addPdfBtn", string_prop("text", "Add PDF(s)", I4), I4))
        + item(widget("QPushButton", "addFolderBtn", string_prop("text", "Add Folder", I4), I4))
    )
    Drop = widget("QFrame", "dropPanel",
        layout("QHBoxLayout", "dropLayout", DropBody, stretch="1,0,0"))

    FltrBody = (
        margin_props(14, 12, 14, 12, I6)
        + num_prop("horizontalSpacing", 10, I6)
        + num_prop("verticalSpacing", 8, I6)
        + item(widget("QLineEdit", "supplierFilter", string_prop("placeholderText", "Filter supplier", I4)))
        + item(widget("QComboBox", "typeFilter", "", I4))
        + item(widget("QComboBox", "platformFilter", "", I4))
        + item(widget("QComboBox", "statusFilter", "", I4))
        + item(widget("QPushButton", "clearFilterBtn", string_prop("text", "Clear Filters", I4), I4))
        + item(widget("QComboBox", "fillPlatformCombo", "", I4))
        + item(widget("QLineEdit", "fillChat", string_prop("placeholderText", "Fill chat name", I4), I4))
        + item(widget("QComboBox", "fillStatusCombo", "", I4))
        + item(widget("QPushButton", "fillApplyBtn", string_prop("text", "Apply to Selected", I4), I4))
    )
    Fltr = widget("QFrame", "filterPanel",
        layout("QGridLayout", "filterLayout", FltrBody))

    TableProp = (
        num_prop("rowCount", 0, I2) +
        num_prop("columnCount", 7, I2) +
        bool_prop("alternatingRowColors", I2) +
        enum_prop("selectionBehavior", "QAbstractItemView::SelectRows", I2) +
        enum_prop("selectionMode", "QAbstractItemView::ExtendedSelection", I2)
    )
    Table = widget("QTableWidget", "taskTable", TableProp)

    ActBody = (
        item(widget("QPushButton", "searchSendBtn", string_prop("text", "Search && Confirm Send", I4), I4))
        + item(widget("QPushButton", "directSendBtn", string_prop("text", "Send to Current Chat", I4), I4))
        + item(widget("QPushButton", "selectAllBtn", string_prop("text", "Select All", I4), I4))
        + item(widget("QPushButton", "skipSelectedBtn", string_prop("text", "Skip Selected", I4), I4))
        + item(spacer("actionSpacer", 40, 20, "Horizontal", I4))
        + item(widget("QPushButton", "clearListBtn", string_prop("text", "Clear All", I4), I4))
    )
    Act = widget("QFrame", "actionPanel",
        layout("QHBoxLayout", "actionLayout", ActBody))

    Left = layout("QVBoxLayout", "leftLayout",
        body=item(Drop) + item(Fltr) + item(Table) + item(Act),
        stretch="0,0,1,0")

    Side = widget("QFrame", "sidePanel",
        layout("QVBoxLayout", "sidebarLayout", stretch="0,0,0,0,0,0,0,0,1",
            num_prop("spacing", 12, I4)
            + item(widget("QLabel", "sidebarHeader", string_prop("text", "Details", I4), I4))
            + item(widget("QLabel", "detailContent", string_prop("text", "No task selected", I4) + bool_prop("wordWrap", I4), I4))
            + item(widget("QPushButton", "openSuppliersBtn", string_prop("text", "Open Supplier Config", I4), I4))
            + item(widget("QPushButton", "openLogBtn", string_prop("text", "Open Log", I4), I4))
            + item(widget("QLabel", "messageLabel", string_prop("text", "Message to Send", I4), I4))
            + item(layout("QGridLayout", "messageTabs",
                num_prop("spacing", 8, I4)
                + item(widget("QRadioButton", "msgTabInstr", string_prop("text", "Instrument", I4) + bool_prop("checked", I4), I4))
                + item(widget("QRadioButton", "msgTabReagent", string_prop("text", "Reagent", I4), I4))
                + item(widget("QRadioButton", "msgTabContract", string_prop("text", "Contract", I4), I4))
                + item(widget("QRadioButton", "msgTabRecon", string_prop("text", "Reconciliation", I4), I4))))
            + item(widget("QPlainTextEdit", "messagePreviewBox", bool_prop("readOnly", I4), I4))
            + item(widget("QLabel", "logLabel", string_prop("text", "Log", I4), I4))
            + item(widget("QPlainTextEdit", "logBox", bool_prop("readOnly", I4), I4))
        ))

    Body = layout("QHBoxLayout", "mainLayout", stretch="1,0",
        Left + item(Side))

    ui(OUT / "purchase_workbench.ui", "PurchaseWorkbench", "QWidget",
       "PurchaseWorkbench", "Purchase Workbench - Send", Body)


# =========================================================================
# 2. UnifiedApp
# =========================================================================

def export_unified_shell():
    Central = widget("QWidget", "centralBody",
        layout("QHBoxLayout", "bodyLayout", stretch="0,1",
            num_prop("spacing", 0, I4)
            + item(widget("QFrame", "sharedSidebar",
                layout("QVBoxLayout", "sidebarNavLayout", stretch="0,0,0,0,1,0",
                    num_prop("spacing", 0, I6)
                    + margin_props(16, 16, 16, 16, I6)
                    + item(widget("QLabel", "appTitle", string_prop("text", "Procurement Workbench", I6), I4), I4)
                    + item(widget("QLabel", "navSection", string_prop("text", "Modules", I6), I4), I4)
                    + item(widget("QPushButton", "navItem0", string_prop("text", "Contract Naming", I6) + bool_prop("checkable", I6), I4), I4)
                    + item(widget("QPushButton", "navItem1", string_prop("text", "Send Contracts", I6) + bool_prop("checkable", I6), I4), I4)
                    + item(spacer("sidebarSpacer", 20, 40, "Vertical", I6))
                    + item(widget("QLabel", "versionLabel", string_prop("text", "v2.0", I6), I4), I4))))
            + item(widget("QStackedWidget", "contentStack",
                layout("QStackedLayout", "stackLayout",
                    item(widget("QWidget", "renamePage", "", I4))
                    + item(widget("QWidget", "workbenchPage", "", I4)))))
        )
    )

    ui(OUT / "unified_shell.ui", "UnifiedApp", "QMainWindow",
       "UnifiedApp", "Procurement Workbench", Central)


# =========================================================================
# 3. SupplierDialog
# =========================================================================

def export_supplier_dialog():
    FormBody = (
        num_prop("spacing", 6, I4) +
        item(widget("QLabel", "supplierLabel", string_prop("text", "Supplier", I4), I4)) +
        item(widget("QLineEdit", "supplierEdit", "", I4)) +
        item(widget("QLabel", "platformLabel", string_prop("text", "Platform", I4), I4)) +
        item(widget("QComboBox", "platformCombo", "", I4)) +
        item(widget("QLabel", "chatLabel", string_prop("text", "Chat Name", I4), I4)) +
        item(widget("QLineEdit", "chatEdit", string_prop("placeholderText", "e.g. ABC-Purchasing Group", I4), I4)) +
        item(widget("QLabel", "deliveryLabel", string_prop("text", "Delivery Type", I4), I4)) +
        item(widget("QComboBox", "deliveryCombo", "", I4))
    )
    Body = layout("QVBoxLayout", "mainLayout",
        item(layout("QFormLayout", "formLayout", FormBody)) +
        item(widget("QDialogButtonBox", "buttonBox", string_prop("standardButtons", "Ok|Cancel", I2)))
    )

    ui(OUT / "supplier_dialog.ui", "SupplierDialog", "QDialog",
       "SupplierDialog", "Add Supplier", Body)


# =========================================================================
# 4. ThemeSettingsDialog
# =========================================================================

def export_theme_dialog():
    color_keys = [
        ("Background", "bg_main"), ("Card BG", "bg_card"),
        ("Primary Text", "text_main"), ("Secondary Text", "text_secondary"),
        ("Border", "border"), ("Primary Blue", "primary"),
        ("Success Green", "green"), ("Warning Orange", "orange"),
        ("Error Red", "red"),
    ]
    rows = []
    for label, key in color_keys:
        row = item(
            layout("QHBoxLayout", f"row_{key}",
                margin_props(0, 2, 0, 2, I6)
                + item(widget("QLabel", f"lbl_{key}", string_prop("text", label, I6), I4), I4)
                + item(widget("QPushButton", f"color_{key}", "", I4), I4)
                + item(spacer(f"hsp_{key}", 40, 20, "Horizontal", I6)))
        )
        rows.append(row)

    Scroll = widget("QScrollArea", "colorScroll",
        bool_prop("widgetResizable")
        + widget("QWidget", "colorInner",
            layout("QVBoxLayout", "formLayout",
                num_prop("spacing", 4, I6)
                + "".join(rows)
            , indent=I4)
        )
    )

    Body = layout("QVBoxLayout", "mainLayout", stretch="1,0",
        num_prop("spacing", 6, I4)
        + item(Scroll)
        + item(layout("QHBoxLayout", "buttonRow",
            num_prop("spacing", 8, I6)
            + item(widget("QPushButton", "previewBtn", string_prop("text", "Preview", I6), I4), I4)
            + item(widget("QPushButton", "saveBtn", string_prop("text", "Save && Apply", I6), I4), I4)
            + item(widget("QPushButton", "cancelBtn", string_prop("text", "Cancel", I6), I4), I4)))
    )

    ui(OUT / "theme_settings_dialog.ui", "ThemeSettingsDialog", "QDialog",
       "ThemeSettingsDialog", "Theme Settings", Body)


# =========================================================================
if __name__ == "__main__":
    export_workbench()
    export_unified_shell()
    export_supplier_dialog()
    export_theme_dialog()
    print(f"\nDone -> {OUT}")
