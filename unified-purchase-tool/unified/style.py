"""Unified design tokens and QSS builder for 采购工作台.

iOS-native style: deep card-lift background, white floating cards,
clear input-card-log hierarchy, high-contrast text.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtGui import QColor

# ═══════════════════════════════════════════════════════════════════════════
# Design Tokens — iOS-style layered color system
# ═══════════════════════════════════════════════════════════════════════════

PRIMARY   = "#007AFF"
SUCCESS   = "#2C6E2F"
WARNING   = "#E67C00"
DANGER    = "#D33C2C"

TEXT      = "#1C1C1E"
TEXT2     = "#6C6C70"
TEXT3     = "#AEAEB2"

# Background hierarchy: deep canvas → white card → tinted inset areas
BG        = "#B0B0BD"   # medium-gray canvas, white cards float above it
CARD      = "#FFFFFF"   # white floating surfaces
CARD_ALT  = "#E4E4EC"   # inset areas: logs, OCR info, preview — clearly not white

# Inputs: tinted, focus → white + blue glow
INPUT_BG        = "#EAEAF0"
INPUT_BG_FOCUS  = "#FFFFFF"
TOOLBAR_BG      = "#C0C0CA"   # lighter than canvas, distinct from card

# Border hierarchy — stronger so cards stand out against canvas
BORDER    = "#A0A0B0"   # card outlines, visible against canvas
BORDER_M  = "#9898A8"   # input borders, rename card outline
BORDER_S  = "#BEBECD"   # log/inset borders (lighter, against card_alt)

# Selection & hover — adjusted for darker canvas
SELECTION_BG  = "#D6E4FF"  # blue tint for nav selection
HOVER_BG      = "#E8E8F0"  # list item hover

# Inset panels
LOG_BG        = "#ECECF2"
ERR_BG        = "#FFECEA"
WARN_BG       = "#FFEAD2"

# Tag colors
TAG_GREEN  = "#2C6E2F"
TAG_ORANGE = "#E67C00"
TAG_BLUE   = "#007AFF"
TAG_RED    = "#D33C2C"
TAG_GRAY   = "#8E8E93"

# ═══════════════════════════════════════════════════════════════════════════
# Spacing & Shape
# ═══════════════════════════════════════════════════════════════════════════

R_SM  = 7
R_MD  = 12    # buttons, list items
R_LG  = 18    # cards
R_XL  = 20    # drop zones

# ═══════════════════════════════════════════════════════════════════════════
# Typography
# ═══════════════════════════════════════════════════════════════════════════

W_REG  = 400
W_MED  = 500
W_SB   = 590
W_BOLD = 700

FONT = ('-apple-system, BlinkMacSystemFont, "SF Pro Text", '
        '"PingFang SC", "Microsoft YaHei UI", "Segoe UI", system-ui')
FONT_MONO = ('"SF Mono", "Cascadia Code", Consolas, '
             '"PingFang SC", monospace')

# ═══════════════════════════════════════════════════════════════════════════
# Token dict for theme persistence
# ═══════════════════════════════════════════════════════════════════════════

TOKENS = {
    "primary": PRIMARY, "success": SUCCESS, "warning": WARNING, "danger": DANGER,
    "text": TEXT, "text2": TEXT2, "text3": TEXT3,
    "bg": BG, "card": CARD, "card_alt": CARD_ALT,
    "border": BORDER, "border_m": BORDER_M, "border_s": BORDER_S,
    "selection_bg": SELECTION_BG, "selection_bg2": SELECTION_BG, "hover_bg": HOVER_BG,
    "log_bg": LOG_BG, "err_bg": ERR_BG, "warn_bg": WARN_BG,
    "err_text": DANGER,
    "toolbar_bg": TOOLBAR_BG, "input_bg": INPUT_BG,
    "input_bg_focus": INPUT_BG_FOCUS,
    "tag_green": TAG_GREEN, "tag_orange": TAG_ORANGE,
    "tag_blue": TAG_BLUE, "tag_red": TAG_RED, "tag_gray": TAG_GRAY,
}

_theme_path = Path(__file__).parent / "theme.json"


# ═══════════════════════════════════════════════════════════════════════════
# Color utilities for derived hover/pressed states
# ═══════════════════════════════════════════════════════════════════════════

def _lighten(hex_color: str, factor: float = 0.15) -> str:
    """Return a lighter variant (for hover backgrounds). factor=0 mixes toward white."""
    c = QColor(hex_color)
    return QColor(
        int(c.red()   + (255 - c.red())   * factor),
        int(c.green() + (255 - c.green()) * factor),
        int(c.blue()  + (255 - c.blue())  * factor),
    ).name()


def _darken(hex_color: str, factor: float = 0.12) -> str:
    """Return a darker variant (for pressed states). factor=0 keeps original."""
    c = QColor(hex_color)
    return QColor(
        int(c.red()   * (1 - factor)),
        int(c.green() * (1 - factor)),
        int(c.blue()  * (1 - factor)),
    ).name()


def _alpha(hex_color: str, a: float) -> str:
    """Return the color with a given alpha as rgba()."""
    c = QColor(hex_color)
    return f"rgba({c.red()},{c.green()},{c.blue()},{a})"


# ═══════════════════════════════════════════════════════════════════════════
# QSS Builder
# ═══════════════════════════════════════════════════════════════════════════

def build(theme: dict | None = None) -> str:
    """Build the complete unified QSS stylesheet from tokens."""
    t_ = dict(TOKENS)
    if theme:
        t_.update(theme)
    p = t_["primary"]
    d = t_["danger"]
    s = t_["success"]
    w = t_["warning"]
    bm = t_["border_m"]
    bs = t_["border_s"]

    # Derived colors (hover/pressed)
    prim_dark     = _darken(p)
    prim_darker   = _darken(p, 0.20)
    prim_light    = _lighten(p, 0.82)
    prim_lighter  = _lighten(p, 0.88)
    danger_dark   = _darken(d)
    danger_darker = _darken(d, 0.20)

    return f"""
/* ==================================================================
   Unified QSS — iOS Native Style
   Canvas {t_["bg"]} / Cards {t_["card"]} / Inputs {t_["input_bg"]} / Insets {t_["log_bg"]}
   ================================================================== */

QMainWindow {{ background: {t_["bg"]}; }}
QMainWindow > QWidget {{
    background: {t_["bg"]}; color: {t_["text"]};
    font-family: {FONT}; font-size: 13px; font-weight: {W_REG};
}}

/* ---- Shared Sidebar ---- */
QFrame#sharedSidebar {{
    background: {t_["card"]}; border: 0; border-right: 1px solid {t_["border"]};
}}
QLabel#appTitle {{
    font-size: 21px; font-weight: {W_BOLD}; color: {t_["text"]};
    padding: 20px 18px 8px 18px;
}}
QLabel#navSection {{
    font-size: 11px; font-weight: {W_SB}; color: {t_["text2"]};
    letter-spacing: 0.3px; padding: 6px 18px 2px 18px; margin-top: 10px;
}}
QPushButton#navItem {{
    background: transparent; color: {t_["text"]}; border: 0; border-radius: {R_MD}px;
    padding: 10px 18px; font-weight: {W_MED}; font-size: 14px; text-align: left;
}}
QPushButton#navItem:hover {{ background: rgba(0,0,0,0.04); }}
QPushButton#navItem:checked {{
    background: {t_["selection_bg"]}; color: {p}; font-weight: {W_SB};
}}
QLabel#versionLabel {{
    font-size: 11px; color: {t_["text3"]}; padding: 8px 18px;
}}

/* ---- Cards — white floating surfaces, radius 18px ---- */
QFrame#sideCard {{
    background: {t_["card"]}; border: 2px solid {t_["border"]}; border-radius: {R_LG}px;
}}
QFrame#centerCard {{
    background: {t_["card"]}; border: 2px solid {t_["border"]}; border-radius: {R_LG}px;
}}
QFrame#reviewCard {{
    background: {t_["card"]}; border: 2px solid {t_["border"]}; border-radius: {R_LG}px;
}}
QFrame#statCard {{
    background: {t_["card"]}; border: 2px solid {t_["border"]}; border-radius: {R_LG}px;
}}
QFrame#renameCard {{
    background: {t_["card"]}; border: 2px solid {bm}; border-radius: {R_LG}px;
}}
QFrame#renameCardActive {{
    background: {t_["card"]}; border: 3px solid {p}; border-radius: {R_LG}px;
}}
QFrame#card {{
    background: {t_["card"]}; border: 2px solid {t_["border"]}; border-radius: {R_LG}px;
}}

/* ---- Inset panels (log, OCR info, preview) ---- */
QFrame#ocrInfoCard {{
    background: {t_["card_alt"]}; border: 2px solid {bs}; border-radius: 16px;
}}
QFrame#previewCard {{
    background: {t_["card_alt"]}; border: 2px dashed {bm}; border-radius: {R_LG}px;
}}
QFrame#previewCard:hover {{ border-color: {p}; background: {_darken(t_["card_alt"], 0.03)}; }}

/* ---- Workbench: drop panel ---- */
QFrame#dropPanel {{
    background: {t_["card"]}; border: 3px dashed {bm}; border-radius: {R_XL}px;
}}
QFrame#dropPanel:hover {{ border-color: {p}; }}
QLabel#dropTitle {{
    font-size: 15px; font-weight: {W_MED}; color: {t_["text2"]};
}}
QLabel#hint {{
    font-size: 12px; color: {t_["text3"]};
}}

/* ---- Workbench: panel / sidebar ---- */
QFrame#panel, QFrame#sidebar {{
    background: {t_["card"]}; border: 2px solid {t_["border"]}; border-radius: {R_LG}px;
}}

/* ---- Buttons — min-height 34px, radius 12px ---- */
QPushButton {{
    min-height: 34px; border-radius: {R_MD}px; padding: 6px 16px;
    font-size: 13px; font-weight: {W_SB};
}}
QPushButton#primaryBtn {{
    background: {p}; color: #FFFFFF; border: 1px solid {p};
}}
QPushButton#primaryBtn:hover {{ background: {prim_dark}; border-color: {prim_dark}; }}
QPushButton#primaryBtn:pressed {{ background: {prim_darker}; border-color: {prim_darker}; }}
QPushButton#primaryBtn:disabled {{
    background: {t_["border"]}; color: {t_["text3"]}; border: 1px solid {bm};
}}
QPushButton#secondaryBtn {{
    background: {t_["card"]}; color: {p}; border: 1px solid {bm};
}}
QPushButton#secondaryBtn:hover {{ background: {prim_light}; border-color: {p}; }}
QPushButton#secondaryBtn:pressed {{ background: {prim_lighter}; }}
QPushButton#secondaryBtn:disabled {{
    background: transparent; color: {t_["text3"]}; border: 1px solid transparent;
}}
QPushButton#stopBtn {{
    background: {t_["err_bg"]}; color: {d};
    border: 1px solid {_alpha(d, 0.25)};
}}
QPushButton#stopBtn:hover {{ background: {d}; color: #FFFFFF; border-color: {d}; }}
QPushButton#stopBtn:pressed {{ background: {danger_darker}; color: #FFFFFF; }}
QPushButton#startBtn {{
    background: {p}; color: #FFFFFF; border: 1px solid {p};
}}
QPushButton#startBtn:hover {{ background: {prim_dark}; border-color: {prim_dark}; }}
QPushButton#dangerBtn {{
    background: {d}; color: #FFFFFF; border: 1px solid {d};
    border-radius: {R_MD}px; padding: 11px 22px; font-size: 14px; font-weight: {W_BOLD};
}}
QPushButton#dangerBtn:hover {{ background: {danger_dark}; border-color: {danger_dark}; }}
QPushButton#dangerBtn:disabled {{
    background: {t_["card"]}; color: {d}; border: 1px solid {_alpha(d, 0.25)};
}}

/* ---- Ghost / icon / danger outline buttons ---- */
QPushButton#ghostButton {{
    background: {t_["input_bg"]}; color: {t_["text"]}; border: 0;
    border-radius: {R_MD}px; padding: 6px 14px; font-weight: {W_MED}; font-size: 12px;
}}
QPushButton#ghostButton:hover {{ background: {t_["border"]}; }}
QPushButton#iconButton {{
    background: transparent; color: {p}; border: 0;
    border-radius: {R_MD}px; padding: 4px 10px; font-weight: {W_MED}; font-size: 12px;
}}
QPushButton#iconButton:hover {{ background: {_alpha(p, 0.06)}; }}
QPushButton#dangerButton {{
    background: transparent; color: {d};
    border: 1px solid {_alpha(d, 0.25)}; border-radius: {R_MD}px;
    padding: 6px 14px; font-weight: {W_MED}; font-size: 12px;
}}
QPushButton#dangerButton:hover {{ background: {d}; color: white; }}

/* ---- Filter / chip buttons ---- */
QPushButton#filterBtn {{
    background: {t_["input_bg"]}; border: 1px solid transparent; border-radius: {R_SM}px;
    padding: 5px 12px; font-size: 11px; font-weight: {W_SB}; color: {t_["text2"]};
}}
QPushButton#filterBtn:hover {{ background: {t_["border"]}; color: {t_["text"]}; }}
QPushButton#filterBtn:checked {{
    background: {t_["selection_bg"]}; color: {p};
}}

/* ---- File List — radius 12px, min-height 44px ---- */
QListWidget {{
    background: {t_["card"]}; border: 0; border-radius: {R_MD}px;
    padding: 2px 0; outline: none;
}}
QListWidget::item {{
    border-radius: {R_MD}px; padding: 12px 16px; margin: 2px 4px;
    color: {t_["text"]}; font-size: 12px; font-weight: {W_MED}; min-height: 44px;
    background: {t_["card"]};
}}
QListWidget::item:hover:!selected {{
    background: {t_["hover_bg"]};
}}
QListWidget::item:selected {{
    background: {t_["selection_bg"]}; color: {t_["text"]}; font-weight: {W_SB};
    border-left: 3px solid {p}; padding-left: 13px;
}}

/* ---- Typography scale ---- */
QLabel#toolbarTitle     {{ font-size: 21px; font-weight: {W_BOLD}; color: {t_["text"]}; }}
QLabel#toolbarSubtitle  {{ font-size: 11px; color: {t_["text2"]}; }}
QLabel#sectionLabel     {{ font-size: 11px; font-weight: {W_SB}; color: {t_["text2"]}; letter-spacing: 0.2px; }}
QLabel#cardTitle        {{ font-size: 15px; font-weight: 620; color: {t_["text"]}; }}
QLabel#sideTitle        {{ font-size: 15px; font-weight: 620; color: {t_["text"]}; }}
QLabel#sideSubtitle     {{ font-size: 11px; color: {t_["text2"]}; }}
QLabel#statValue        {{ font-size: 42px; font-weight: 720; letter-spacing: -0.5px; }}
QLabel#statValue[statColor="#1C1C1E"] {{ color: {t_["text"]}; }}
QLabel#statValue[statColor="#2C6E2F"] {{ color: {s}; }}
QLabel#statValue[statColor="#D33C2C"] {{ color: {d}; }}
QLabel#statValue[statColor="#007AFF"] {{ color: {p}; }}
QLabel#statLabel        {{ font-size: 13px; font-weight: {W_MED}; color: {t_["text2"]}; }}
QLabel#infoValue        {{ font-size: 14px; font-weight: {W_BOLD}; color: {t_["text"]}; }}
QLabel#sectionTitle     {{ font-size: 11px; font-weight: {W_SB}; color: {t_["text2"]}; letter-spacing: -0.1px; margin-bottom: 2px; }}
QLabel#groupLabel       {{ font-size: 11px; font-weight: 650; color: {t_["text"]}; letter-spacing: 0.3px; padding: 2px 0; }}

/* ---- Status property colors ---- */
QLabel[status_pending="true"]  {{ color: {t_["text2"]}; }}
QLabel[status_progress="true"] {{ color: {w}; }}
QLabel[status_success="true"]  {{ color: {s}; }}
QLabel[status_error="true"]    {{ color: {d}; }}

/* ---- Tags (pill-shaped) ---- */
QLabel#tagGreen  {{ background: {t_["tag_green"]};  color: #FFFFFF; border-radius: 999px; padding: 2px 10px; font-weight: 560; font-size: 11px; }}
QLabel#tagOrange {{ background: {t_["tag_orange"]}; color: #FFFFFF; border-radius: 999px; padding: 2px 10px; font-weight: 560; font-size: 11px; }}
QLabel#tagBlue   {{ background: {t_["tag_blue"]};   color: #FFFFFF; border-radius: 999px; padding: 2px 10px; font-weight: 560; font-size: 11px; }}
QLabel#tagRed    {{ background: {t_["tag_red"]};    color: #FFFFFF; border-radius: 999px; padding: 2px 10px; font-weight: 560; font-size: 11px; }}
QLabel#tagGray   {{ background: {t_["tag_gray"]};   color: #FFFFFF; border-radius: 999px; padding: 2px 10px; font-weight: 560; font-size: 11px; }}
QLabel#tagWarn   {{ background: {t_["warn_bg"]};    color: {w}; border-radius: 999px; padding: 2px 10px; font-weight: 560; font-size: 11px; }}

/* ---- QLineEdit#suggestName ---- */
QLineEdit#suggestName {{
    font-size: 19px; font-weight: 600; color: {t_["text"]};
    background: {t_["input_bg"]}; border: 1px solid {bm};
    border-radius: {R_LG}px; padding: 14px 18px;
}}
QLineEdit#suggestName:focus {{
    border-color: {p}; background: {t_["input_bg_focus"]};
}}

/* ---- Generic inputs — #F5F5F7, focus → white + blue glow ---- */
QLineEdit, QComboBox {{
    background: {t_["input_bg"]}; color: {t_["text"]}; border: 1px solid {bm};
    border-radius: {R_MD}px; padding: 8px 12px; font-size: 12px;
    selection-background-color: {p};
}}
QLineEdit:focus, QComboBox:focus {{
    background: {t_["input_bg_focus"]}; border: 1px solid {p};
}}
QComboBox::drop-down {{ border: 0; width: 20px; }}
QComboBox QAbstractItemView {{
    background: white; color: {t_["text"]}; border: 1px solid {t_["border"]};
    border-radius: {R_MD}px; padding: 4px;
    selection-background-color: {t_["selection_bg"]};
}}
QLineEdit#searchBox {{
    background: {t_["input_bg"]}; color: {t_["text"]}; border: 1px solid {bm};
    border-radius: {R_MD}px; padding: 8px 12px; font-size: 12px;
}}
QLineEdit#searchBox:focus {{
    background: {t_["input_bg_focus"]}; border: 1px solid {p};
}}

/* ---- Filter ComboBox (naming tool) ---- */
QComboBox {{
    background: {t_["input_bg"]}; color: {t_["text"]}; border: 1px solid {bm};
    border-radius: {R_MD}px; padding: 8px 12px; font-size: 12px; font-weight: {W_MED};
}}
QComboBox:hover {{ background: {t_["border"]}; }}
QComboBox::drop-down {{ border: 0; width: 18px; }}
QComboBox QAbstractItemView {{
    background: white; color: {t_["text"]}; border: 1px solid {t_["border"]};
    border-radius: 8px; selection-background-color: {t_["selection_bg"]}; padding: 3px;
}}

/* ---- Log / OCR / Message Preview ---- */
#logBox, #ocrBox {{
    background: {t_["card_alt"]}; border: 1px solid {bs}; border-radius: {R_MD}px;
    padding: 12px; font-size: 12px; color: {t_["text"]};
    font-family: {FONT_MONO};
}}
QPlainTextEdit#messagePreview {{
    background: {t_["input_bg"]}; color: {t_["text2"]}; border: 0; border-radius: {R_MD}px;
    padding: 10px 11px;
    font-family: {FONT_MONO}; font-size: 12px; min-height: 76px; max-height: 100px;
}}
QPlainTextEdit#wbLogBox {{
    background: {t_["card_alt"]}; color: {t_["text"]};
    border: 1px solid {bs}; border-radius: {R_MD}px;
    padding: 12px; font-family: {FONT_MONO}; font-size: 12px;
}}

/* ---- ProgressBar — 5px height ---- */
QProgressBar {{
    background: {t_["border"]}; border: none; border-radius: 3px; height: 5px; font-size: 0;
}}
QProgressBar::chunk {{ background: {p}; border-radius: 3px; }}

/* ---- Radio Buttons (segmented control) ---- */
QRadioButton {{
    font-size: 12px; font-weight: 580; color: {t_["text"]};
    background: {t_["input_bg"]}; border: 1px solid {bm}; padding: 7px 14px; spacing: 0;
}}
QRadioButton:first-child {{ border-top-left-radius: 8px; border-bottom-left-radius: 8px; }}
QRadioButton:last-child  {{ border-top-right-radius: 8px; border-bottom-right-radius: 8px; }}
QRadioButton::indicator {{ width: 0; height: 0; }}
QRadioButton:checked {{ background: {p}; color: #FFFFFF; border-color: {p}; font-weight: {W_SB}; }}

/* ---- Message tab radio (workbench sidebar) ---- */
QRadioButton#messageTab {{
    background: {t_["input_bg"]}; color: {t_["text2"]}; border: 0; border-radius: {R_MD}px;
    padding: 7px 12px; font-weight: 560; font-size: 12px;
}}
QRadioButton#messageTab::indicator {{ width: 0; height: 0; }}
QRadioButton#messageTab:checked {{ background: {p}; color: white; }}
QRadioButton#messageTab:hover:!checked {{ background: {bm}; }}

/* ---- Collapse button ---- */
QPushButton#collapseBtn {{
    background: transparent; border: none; color: {t_["text"]};
    font-size: 13px; font-weight: {W_SB}; padding: 4px 0; text-align: left;
}}
QPushButton#collapseBtn:hover {{ color: {p}; }}

/* ---- Workbench Table ---- */
QTableWidget {{
    background: {t_["card"]}; alternate-background-color: {t_["card_alt"]};
    border: 0; border-radius: {R_LG}px;
    gridline-color: transparent;
    selection-background-color: {t_["selection_bg"]}; selection-color: {t_["text"]};
}}
QTableWidget::item {{ padding: 8px 6px; }}
QHeaderView::section {{
    background: {t_["card"]}; color: {t_["text2"]}; border: 0;
    border-bottom: 1px solid {t_["border"]}; border-radius: 0;
    padding: 10px 6px; font-weight: 560; font-size: 11px; letter-spacing: -0.1px;
}}

/* ---- Tabs ---- */
QTabWidget::pane {{ background: transparent; border: 0; }}
QTabBar::tab {{
    background: transparent; color: {t_["text2"]}; border: 0;
    padding: 8px 16px; font-weight: {W_MED}; font-size: 12px; min-width: 56px;
}}
QTabBar::tab:selected {{
    color: {p}; border-bottom: 2px solid {p}; font-weight: {W_SB};
}}
QTabBar::tab:hover:!selected {{ color: {t_["text"]}; }}

/* ---- Toolbar — segmented control style ---- */
QWidget#toolbar {{
    background: {t_["toolbar_bg"]}; border-bottom: 1px solid {t_["border"]};
}}

/* ---- StatusBar ---- */
QStatusBar {{
    background: {t_["card"]}; border-top: 1px solid {t_["border"]};
    color: {t_["text2"]}; font-size: 12px; min-height: 28px;
}}

/* ---- Splitter handle ---- */
QSplitter::handle {{ background: {t_["border"]}; }}

/* ---- ScrollArea (preview) ---- */
QScrollArea#previewScroll {{
    background: {t_["card_alt"]}; border: 1px solid {bs}; border-radius: {R_MD}px;
}}

/* ---- Scrollbars — 5px wide, rounded ---- */
QScrollBar:vertical {{ background: transparent; width: 5px; border-radius: 3px; }}
QScrollBar::handle:vertical {{ background: rgba(0,0,0,0.12); border-radius: 3px; min-height: 20px; }}
QScrollBar::handle:vertical:hover {{ background: rgba(0,0,0,0.22); }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 5px; }}
QScrollBar::handle:horizontal {{ background: rgba(0,0,0,0.12); border-radius: 3px; min-width: 20px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ---- Dialogs ---- */
QDialog, QMessageBox {{ background-color: {t_["bg"]}; color: {t_["text"]}; }}
QDialog QLabel, QMessageBox QLabel {{ color: {t_["text"]}; }}
QDialog QLineEdit {{
    background: {t_["card"]}; color: {t_["text"]}; border: 1px solid {p}; border-radius: 8px; padding: 7px 9px;
}}

/* ---- Disabled fallback ---- */
QPushButton:disabled {{ background: #FAFAFC; color: {t_["text3"]}; border: 1px solid {bm}; }}
"""


# ═══════════════════════════════════════════════════════════════════════════
# Theme Persistence
# ═══════════════════════════════════════════════════════════════════════════

def load_theme() -> dict:
    try:
        if _theme_path.exists():
            data = json.loads(_theme_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {k: v for k, v in data.items() if k in TOKENS}
    except Exception:
        pass
    return {}


def save_theme(theme: dict) -> None:
    _theme_path.parent.mkdir(parents=True, exist_ok=True)
    _theme_path.write_text(json.dumps(theme, indent=2, ensure_ascii=False),
                           encoding="utf-8")
