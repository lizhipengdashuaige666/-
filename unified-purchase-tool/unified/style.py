"""Unified design tokens and QSS builder for 采购工作台.

Two built-in themes: dark (default) and light (clean, layered, high-clarity).
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect

# ═══════════════════════════════════════════════════════════════════════════
# Design Tokens — Dark-mode layered color system
# ═══════════════════════════════════════════════════════════════════════════

PRIMARY   = "#0A84FF"
SUCCESS   = "#30D158"
WARNING   = "#FF9F0A"
DANGER    = "#FF453A"

TEXT      = "#F5F5F7"
TEXT2     = "#98989E"
TEXT3     = "#6C6C72"

# Dark background hierarchy: deepest canvas → lifted card → recessed inset
BG        = "#1A1A1E"   # deep dark canvas
CARD      = "#252528"   # cards float slightly above canvas
CARD_ALT  = "#1E1E22"   # inset areas: logs, OCR info, preview — recessed

# Inputs: slightly recessed on card, focus → brighten + blue edge
INPUT_BG        = "#1E1E22"
INPUT_BG_FOCUS  = "#2C2C30"
TOOLBAR_BG      = "#1A1A1E"   # same as canvas, border separates

# Border hierarchy — subtle but visible on dark
BORDER    = "#3A3A3E"   # card outlines
BORDER_M  = "#48484E"   # input borders, rename card outline
BORDER_S  = "#34343A"   # log/inset borders

# Selection & hover — dark-adapted blue tints
SELECTION_BG  = "#1C3A5C"  # blue tint for nav selection
HOVER_BG      = "#2E2E34"  # list item hover

# Inset panels
LOG_BG        = "#1A1A1E"
ERR_BG        = "#3D1C1A"
WARN_BG       = "#3D2E10"

# Tag colors — bright for dark backgrounds
TAG_GREEN  = "#30D158"
TAG_ORANGE = "#FF9F0A"
TAG_BLUE   = "#0A84FF"
TAG_RED    = "#FF453A"
TAG_GRAY   = "#636368"

# ═══════════════════════════════════════════════════════════════════════════
# Light-mode tokens — clean, airy, high clarity with clear card hierarchy
# ═══════════════════════════════════════════════════════════════════════════

L_PRIMARY   = "#0066CC"
L_SUCCESS   = "#1B8A3D"
L_WARNING   = "#CC7A00"
L_DANGER    = "#D42A1F"

L_TEXT      = "#1D1D1F"
L_TEXT2     = "#6E6E73"
L_TEXT3     = "#A1A1A6"

L_BG        = "#F2F2F7"    # light grey canvas — subtle distinction from cards
L_CARD      = "#FFFFFF"    # white cards float above the canvas
L_CARD_ALT  = "#F9F9FB"    # slightly tinted inset areas

L_INPUT_BG        = "#F5F5FA"
L_INPUT_BG_FOCUS  = "#FFFFFF"
L_TOOLBAR_BG      = "#FFFFFF"

L_BORDER    = "#E5E5EA"    # card outlines — visible but not heavy
L_BORDER_M  = "#D1D1D6"    # input borders
L_BORDER_S  = "#E9E9ED"    # log/inset borders

L_SELECTION_BG  = "#D6E8FF"  # soft blue tint
L_HOVER_BG      = "#F2F2F7"

L_LOG_BG        = "#F9F9FB"
L_ERR_BG        = "#FEE2E2"
L_WARN_BG       = "#FFF4DE"

L_TAG_GREEN  = "#1B8A3D"
L_TAG_ORANGE = "#CC7A00"
L_TAG_BLUE   = "#0066CC"
L_TAG_RED    = "#D42A1F"
L_TAG_GRAY   = "#8E8E93"

# ═══════════════════════════════════════════════════════════════════════════
# Spacing & Shape
# ═══════════════════════════════════════════════════════════════════════════

R_SM  = 6
R_MD  = 8     # buttons, list items
R_LG  = 8     # cards
R_XL  = 10    # drop zones

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

LIGHT_TOKENS = {
    "primary": L_PRIMARY, "success": L_SUCCESS, "warning": L_WARNING, "danger": L_DANGER,
    "text": L_TEXT, "text2": L_TEXT2, "text3": L_TEXT3,
    "bg": L_BG, "card": L_CARD, "card_alt": L_CARD_ALT,
    "border": L_BORDER, "border_m": L_BORDER_M, "border_s": L_BORDER_S,
    "selection_bg": L_SELECTION_BG, "selection_bg2": L_SELECTION_BG, "hover_bg": L_HOVER_BG,
    "log_bg": L_LOG_BG, "err_bg": L_ERR_BG, "warn_bg": L_WARN_BG,
    "err_text": L_DANGER,
    "toolbar_bg": L_TOOLBAR_BG, "input_bg": L_INPUT_BG,
    "input_bg_focus": L_INPUT_BG_FOCUS,
    "tag_green": L_TAG_GREEN, "tag_orange": L_TAG_ORANGE,
    "tag_blue": L_TAG_BLUE, "tag_red": L_TAG_RED, "tag_gray": L_TAG_GRAY,
}

LIGHT_TOKENS.update({
    "primary": "#2775D1", "success": "#1AA36F",
    "warning": "#D98A21", "danger": "#D94A42",
    "text": "#182536", "text2": "#40556D", "text3": "#5F7288",
    "bg": "#F3F7FC", "card": "#FFFFFF", "card_alt": "#F8FBFF",
    "border": "#E4ECF7", "border_m": "#D4E0EE", "border_s": "#EEF3FA",
    "selection_bg": "#E8F2FF", "selection_bg2": "#EAF4FF",
    "hover_bg": "#F4F8FD",
    "log_bg": "#F8FBFF", "warn_bg": "#FFF6E6",
    "toolbar_bg": "#F8FBFF", "input_bg": "#FFFFFF",
    "input_bg_focus": "#FFFFFF",
    "tag_green": "#1AA36F", "tag_orange": "#D98A21",
    "tag_blue": "#2775D1", "tag_red": "#D94A42", "tag_gray": "#93A4BA",
})

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


def resolved_tokens(mode: str = "dark", overrides: dict | None = None) -> dict:
    """Return the full effective token set for a saved theme mode."""
    base = dict(LIGHT_TOKENS if mode == "light" else TOKENS)
    if overrides:
        for k, v in overrides.items():
            if k in base and not k.startswith("_"):
                base[k] = v
    base["_mode"] = mode
    return base


def _is_light_theme(t_: dict) -> bool:
    return t_.get("_mode") == "light" or t_.get("bg") == LIGHT_TOKENS["bg"]


def _surface_values(t_: dict) -> dict[str, str]:
    if not _is_light_theme(t_):
        return {
            "canvas": t_["bg"],
            "sidebar": t_["card"],
            "card": t_["card"],
            "card_strong": t_["card"],
            "inset": t_["card_alt"],
            "control": t_["input_bg"],
            "control_focus": t_["input_bg_focus"],
            "border": t_["border"],
            "border_soft": t_["border_s"],
            "divider": t_["border"],
            "nav_hover": "rgba(255,255,255,0.06)",
            "disabled": "#2A2A30",
            "scroll": "rgba(255,255,255,0.10)",
            "scroll_hover": "rgba(255,255,255,0.18)",
            "table_header": t_["card"],
        }
    return {
        "canvas": "#F3F7FC",
        "sidebar": "#EDF4FD",
        "card": "#FFFFFF",
        "card_strong": "#FFFFFF",
        "inset": "#F8FBFF",
        "control": "#FFFFFF",
        "control_focus": "#FFFFFF",
        "border": "#E1EAF5",
        "border_soft": "#EEF3FA",
        "divider": "#E1EAF5",
        "nav_hover": "#F8FBFF",
        "disabled": "#EDF3FA",
        "scroll": "rgba(120,143,170,0.28)",
        "scroll_hover": "rgba(92,116,146,0.45)",
        "table_header": "#F8FBFF",
    }


# ═══════════════════════════════════════════════════════════════════════════
# Drop shadow — QSS doesn't support box-shadow, so we do it in code
# ═══════════════════════════════════════════════════════════════════════════

_CARD_OBJECT_NAMES = {
    "sideCard", "centerCard", "reviewCard", "statCard",
    "renameCard", "card", "ocrInfoCard", "previewCard",
    "dropPanel", "panel", "sidebar",
}


def apply_shadow(widget: QFrame, blur: int = 18, offset: tuple = (0, 4),
                 alpha: float = 0.10) -> None:
    """Apply a soft drop shadow to make a card feel lifted off the canvas."""
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setOffset(offset[0], offset[1])
    c = QColor(0, 0, 0, int(255 * alpha))
    shadow.setColor(c)
    widget.setGraphicsEffect(shadow)


def apply_shadows_to_tree(root, skip: set[str] | None = None) -> None:
    """Walk a widget tree and apply drop shadows to card-style frames."""
    if skip is None:
        skip = set()
    for w in root.findChildren(QFrame):
        name = w.objectName()
        if name in _CARD_OBJECT_NAMES and name not in skip:
            apply_shadow(w)


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
    sv = _surface_values(t_)

    return f"""
/* ==================================================================
   Unified QSS — Dark Mode
   Canvas {t_["bg"]} / Cards {t_["card"]} / Inputs {t_["input_bg"]} / Insets {t_["log_bg"]}
   ================================================================== */

QMainWindow {{ background: {sv["canvas"]}; }}
QMainWindow > QWidget {{
    background: {sv["canvas"]}; color: {t_["text"]};
    font-family: {FONT}; font-size: 13px; font-weight: {W_REG};
}}

/* ---- All labels default to text color (fixes unnamed labels on dark bg) ---- */
QLabel {{ color: {t_["text"]}; }}

/* ---- Shared Sidebar ---- */
QFrame#sharedSidebar {{
    background: {sv["sidebar"]}; border: 0; border-right: 1px solid {sv["divider"]};
}}
QLabel#appTitle {{
    font-size: 15px; font-weight: {W_BOLD}; color: {t_["text"]};
    padding: 10px 6px 10px 6px;
}}
QLabel#navSection {{
    font-size: 11px; font-weight: {W_SB}; color: {t_["text3"]};
    letter-spacing: 0px; padding: 10px 6px 4px 6px; margin-top: 2px;
}}
QPushButton#navItem {{
    background: transparent; color: {t_["text"]}; border: 1px solid transparent; border-radius: {R_MD}px;
    padding: 9px 10px; font-weight: {W_MED}; font-size: 13px; text-align: left;
}}
QPushButton#navItem:hover {{ background: {sv["nav_hover"]}; }}
QPushButton#navItem:checked {{
    background: {t_["selection_bg"]}; color: {p}; font-weight: {W_SB};
    border: 1px solid #D5E7FF;
}}
QLabel#versionLabel {{
    font-size: 11px; color: {t_["text3"]}; padding: 8px 6px;
}}

QWidget#contentArea {{
    background: {sv["canvas"]};
}}
QFrame#topbar {{
    background: #F8FBFF; border: 0; border-bottom: 1px solid {sv["divider"]};
}}
QLabel#topbarTitle {{
    font-size: 16px; font-weight: {W_BOLD}; color: {t_["text"]};
}}
QLabel#topbarSubtitle {{
    font-size: 11px; color: {t_["text2"]};
}}
QPushButton#topNavItem {{
    background: transparent; color: {t_["text"]}; border: 1px solid transparent;
    border-radius: {R_MD}px; padding: 7px 11px; min-height: 28px;
    font-size: 12px; font-weight: {W_SB};
}}
QPushButton#topNavItem:hover {{
    background: #FFFFFF; color: {t_["text"]}; border-color: {sv["border"]};
}}
QPushButton#topNavItem:checked {{
    background: {t_["selection_bg"]}; color: {p}; border-color: #CFE2FF;
}}
QLineEdit#globalSearch {{
    background: #FFFFFF; color: {t_["text2"]}; border: 1px solid {sv["border"]};
    border-radius: {R_MD}px; padding: 7px 12px; font-size: 12px;
    placeholder-text-color: {t_["text3"]};
}}

/* ---- Cards — floating dark surfaces, radius 18px ---- */
QFrame#sideCard {{
    background: {sv["card"]}; border: 1px solid {sv["border"]}; border-radius: {R_LG}px;
}}
QFrame#centerCard {{
    background: {sv["card"]}; border: 1px solid {sv["border"]}; border-radius: {R_LG}px;
}}
QFrame#reviewCard {{
    background: {sv["card"]}; border: 1px solid {sv["border"]}; border-radius: {R_LG}px;
}}
QFrame#statCard {{
    background: {sv["card"]}; border: 1px solid {sv["border"]}; border-radius: {R_LG}px;
}}
QFrame#renameCard {{
    background: {sv["card"]}; border: 1px solid {sv["border"]}; border-radius: {R_LG}px;
}}
QFrame#card {{
    background: {sv["card"]}; border: 1px solid {sv["border"]}; border-radius: {R_LG}px;
}}

/* ---- Inset panels (log, OCR info, preview) ---- */
QFrame#ocrInfoCard {{
    background: {sv["inset"]}; border: 1px solid {sv["border_soft"]}; border-radius: 12px;
}}
QFrame#previewCard {{
    background: {sv["inset"]}; border: 1px dashed {bm}; border-radius: {R_LG}px;
}}
QFrame#previewCard:hover {{ border-color: {p}; background: {_lighten(t_["card_alt"], 0.06)}; }}

/* ---- Workbench: drop panel ---- */
QFrame#dropPanel {{
    background: {sv["card"]}; border: 1px dashed {bm}; border-radius: {R_XL}px;
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
    background: {sv["card"]}; border: 1px solid {sv["border"]}; border-radius: {R_LG}px;
}}

/* ---- Buttons — min-height 34px, radius 12px ---- */
QPushButton {{
    min-height: 30px; border-radius: {R_MD}px; padding: 5px 13px;
    font-size: 12px; font-weight: {W_SB};
}}
QPushButton#primaryBtn {{
    background: {p}; color: #FFFFFF; border: 1px solid {p};
}}
QPushButton#primaryBtn:hover {{ background: {prim_dark}; border-color: {prim_dark}; }}
QPushButton#primaryBtn:pressed {{ background: {prim_darker}; border-color: {prim_darker}; }}
QPushButton#primaryBtn:disabled {{
    background: {sv["disabled"]}; color: {t_["text2"]}; border: 1px solid {bm};
}}
QPushButton#secondaryBtn {{
    background: {sv["control"]}; color: {p}; border: 1px solid {sv["border"]};
}}
QPushButton#secondaryBtn:hover {{ background: {prim_light}; border-color: {p}; }}
QPushButton#secondaryBtn:pressed {{ background: {prim_lighter}; }}
QPushButton#secondaryBtn:disabled {{
    background: {sv["disabled"]}; color: {t_["text2"]}; border: 1px solid {sv["border_soft"]};
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
    background: {sv["control"]}; color: {d}; border: 1px solid {_alpha(d, 0.25)};
}}

/* ---- Ghost / icon / danger outline buttons ---- */
QPushButton#ghostButton {{
    background: {sv["control"]}; color: {t_["text"]}; border: 1px solid transparent;
    border-radius: {R_MD}px; padding: 6px 14px; font-weight: {W_MED}; font-size: 12px;
}}
QPushButton#ghostButton:hover {{ background: {sv["nav_hover"]}; border-color: {sv["border_soft"]}; }}
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
QPushButton#dangerButton:hover {{ background: {d}; color: #FFFFFF; }}

/* ---- Filter / chip buttons ---- */
QPushButton#filterBtn {{
    background: {sv["control"]}; border: 1px solid transparent; border-radius: {R_SM}px;
    padding: 5px 12px; font-size: 11px; font-weight: {W_SB}; color: {t_["text2"]};
}}
QPushButton#filterBtn:hover {{ background: {sv["nav_hover"]}; color: {t_["text"]}; }}
QPushButton#filterBtn:checked {{
    background: {t_["selection_bg"]}; color: {p};
}}

/* ---- File List — radius 12px, min-height 44px ---- */
QListWidget {{
    background: transparent; border: 0; border-radius: {R_MD}px;
    padding: 2px 0; outline: none;
}}
QListWidget::item {{
    border-radius: {R_MD}px; padding: 8px 12px; margin: 2px 4px;
    color: {t_["text"]}; font-size: 12px; font-weight: {W_MED}; min-height: 42px;
    background: transparent;
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
QLabel#statValue        {{ font-size: 28px; font-weight: 720; letter-spacing: 0px; }}
QLabel#statValue[statRole="pending"] {{ color: {t_["text"]}; }}
QLabel#statValue[statRole="done"]    {{ color: {s}; }}
QLabel#statValue[statRole="failed"]  {{ color: {d}; }}
QLabel#statValue[statRole="review"]  {{ color: {p}; }}
QLabel#statLabel        {{ font-size: 13px; font-weight: {W_MED}; color: {t_["text2"]}; }}
QLabel#infoValue        {{ font-size: 14px; font-weight: {W_BOLD}; color: {t_["text"]}; }}
QLabel#ocrValue         {{ font-size: 13px; font-weight: 650; color: {t_["text"]}; background: transparent; }}
QLabel#sectionTitle     {{ font-size: 11px; font-weight: {W_SB}; color: {t_["text2"]}; letter-spacing: -0.1px; margin-bottom: 2px; }}
QLabel#groupLabel       {{ font-size: 11px; font-weight: 650; color: {t_["text"]}; letter-spacing: 0.3px; padding: 2px 0; }}

/* ---- Status property colors ---- */
QLabel[status_pending="true"]  {{ color: {t_["text2"]}; }}
QLabel[status_progress="true"] {{ color: {w}; }}
QLabel[status_success="true"]  {{ color: {s}; }}
QLabel[status_error="true"]    {{ color: {d}; }}

/* ---- Tags (pill-shaped) ---- */
QLabel#tagGreen  {{ background: {_alpha(s, 0.14)}; color: {s}; border: 1px solid {_alpha(s, 0.24)}; border-radius: 999px; padding: 3px 10px; font-weight: 650; font-size: 11px; }}
QLabel#tagOrange {{ background: {_alpha(w, 0.14)}; color: {w}; border: 1px solid {_alpha(w, 0.24)}; border-radius: 999px; padding: 3px 10px; font-weight: 650; font-size: 11px; }}
QLabel#tagBlue   {{ background: {_alpha(p, 0.13)}; color: {p}; border: 1px solid {_alpha(p, 0.24)}; border-radius: 999px; padding: 3px 10px; font-weight: 650; font-size: 11px; }}
QLabel#tagRed    {{ background: {_alpha(d, 0.13)}; color: {d}; border: 1px solid {_alpha(d, 0.24)}; border-radius: 999px; padding: 3px 10px; font-weight: 650; font-size: 11px; }}
QLabel#tagGray   {{ background: {sv["control"]}; color: {t_["text2"]}; border: 1px solid {sv["border"]}; border-radius: 999px; padding: 3px 10px; font-weight: 650; font-size: 11px; }}
QLabel#tagWarn   {{ background: {t_["warn_bg"]}; color: {w}; border: 1px solid {_alpha(w, 0.24)}; border-radius: 999px; padding: 3px 10px; font-weight: 650; font-size: 11px; }}

QPushButton#smallBtn {{
    min-height: 28px; background: transparent; color: {p};
    border: 1px solid {sv["border"]}; border-radius: {R_SM}px;
    padding: 4px 10px; font-size: 12px; font-weight: {W_SB};
}}
QPushButton#smallBtn:hover {{
    background: {_alpha(p, 0.08)}; border-color: {_alpha(p, 0.36)};
}}

/* ---- QLineEdit#suggestName ---- */
QLineEdit#suggestName {{
    font-size: 19px; font-weight: 600; color: {t_["text"]};
    background: {sv["control"]}; border: 1px solid {sv["border"]};
    border-radius: {R_LG}px; padding: 14px 18px;
}}
QLineEdit#suggestName:focus {{
    border-color: {p}; background: {sv["control_focus"]};
}}

/* ---- Generic inputs ---- */
QLineEdit, QComboBox {{
    background: {sv["control"]}; color: {t_["text"]}; border: 1px solid {sv["border"]};
    border-radius: {R_MD}px; padding: 7px 10px; font-size: 12px;
    selection-background-color: {p};
    placeholder-text-color: {t_["text3"]};
}}
QLineEdit:focus, QComboBox:focus {{
    background: {sv["control_focus"]}; border: 1px solid {p};
}}
QComboBox::drop-down {{ border: 0; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {sv["card_strong"]}; color: {t_["text"]}; border: 1px solid {sv["border"]};
    border-radius: {R_MD}px; padding: 4px;
    selection-background-color: {t_["selection_bg"]};
}}
QLineEdit#searchBox {{
    background: {sv["control"]}; color: {t_["text"]}; border: 1px solid {sv["border"]};
    border-radius: {R_MD}px; padding: 7px 10px; font-size: 12px;
    placeholder-text-color: {t_["text3"]};
}}
QLineEdit#searchBox:focus {{
    background: {sv["control_focus"]}; border: 1px solid {p};
}}

/* ---- Filter ComboBox (naming tool) ---- */
QComboBox {{
    background: {sv["control"]}; color: {t_["text"]}; border: 1px solid {sv["border"]};
    border-radius: {R_MD}px; padding: 7px 10px; font-size: 12px; font-weight: {W_MED};
}}
QComboBox:hover {{ background: {sv["nav_hover"]}; }}
QComboBox::drop-down {{ border: 0; width: 18px; }}
QComboBox QAbstractItemView {{
    background: {sv["card_strong"]}; color: {t_["text"]}; border: 1px solid {sv["border"]};
    border-radius: 8px; selection-background-color: {t_["selection_bg"]}; padding: 3px;
}}

/* ---- Log / OCR / Message Preview ---- */
#logBox, #ocrBox {{
    background: {sv["inset"]}; border: 1px solid {sv["border_soft"]}; border-radius: {R_MD}px;
    padding: 12px; font-size: 12px; color: {t_["text"]};
    font-family: {FONT_MONO};
}}
QPlainTextEdit#messagePreview {{
    background: {sv["inset"]}; color: {t_["text2"]}; border: 0; border-radius: {R_MD}px;
    padding: 10px 11px;
    font-family: {FONT_MONO}; font-size: 12px; min-height: 76px; max-height: 100px;
}}
QPlainTextEdit#wbLogBox {{
    background: {sv["inset"]}; color: {t_["text"]};
    border: 1px solid {sv["border_soft"]}; border-radius: {R_MD}px;
    padding: 12px; font-family: {FONT_MONO}; font-size: 12px;
}}

/* ---- ProgressBar — 5px height ---- */
QProgressBar {{
    background: {sv["border_soft"]}; border: none; border-radius: 3px; height: 5px; font-size: 0;
}}
QProgressBar::chunk {{ background: {p}; border-radius: 3px; }}

/* ---- Radio Buttons (segmented control) ---- */
QRadioButton {{
    font-size: 12px; font-weight: 580; color: {t_["text"]};
    background: {sv["control"]}; border: 1px solid {sv["border"]}; padding: 7px 14px; spacing: 0;
}}
QRadioButton:first-child {{ border-top-left-radius: 8px; border-bottom-left-radius: 8px; }}
QRadioButton:last-child  {{ border-top-right-radius: 8px; border-bottom-right-radius: 8px; }}
QRadioButton::indicator {{ width: 0; height: 0; }}
QRadioButton:checked {{ background: {p}; color: #FFFFFF; border-color: {p}; font-weight: {W_SB}; }}

/* ---- Message tab radio (workbench sidebar) ---- */
QRadioButton#messageTab {{
    background: {sv["control"]}; color: {t_["text2"]}; border: 0; border-radius: {R_MD}px;
    padding: 7px 12px; font-weight: 560; font-size: 12px;
}}
QRadioButton#messageTab::indicator {{ width: 0; height: 0; }}
QRadioButton#messageTab:checked {{ background: {p}; color: #FFFFFF; }}
QRadioButton#messageTab:hover:!checked {{ background: {sv["nav_hover"]}; }}

/* ---- Collapse button ---- */
QPushButton#collapseBtn {{
    background: transparent; border: none; color: {t_["text"]};
    font-size: 13px; font-weight: {W_SB}; padding: 4px 0; text-align: left;
}}
QPushButton#collapseBtn:hover {{ color: {p}; }}

/* ---- Workbench Table ---- */
QTableWidget {{
    background: transparent; alternate-background-color: {sv["inset"]};
    border: 0; border-radius: {R_LG}px;
    gridline-color: transparent;
    selection-background-color: {t_["selection_bg"]}; selection-color: {t_["text"]};
}}
QTableWidget::item {{ padding: 8px 6px; color: {t_["text"]}; }}
QTableWidget::item:selected {{ color: {t_["text"]}; }}
QHeaderView::section {{
    background: {sv["table_header"]}; color: {t_["text2"]}; border: 0;
    border-bottom: 1px solid {sv["divider"]}; border-radius: 0;
    padding: 8px 6px; font-weight: 560; font-size: 11px; letter-spacing: 0px;
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
    background: {sv["card"]}; border-bottom: 1px solid {sv["divider"]};
}}

/* ---- StatusBar ---- */
QStatusBar {{
    background: {sv["card"]}; border-top: 1px solid {sv["divider"]};
    color: {t_["text2"]}; font-size: 12px; min-height: 28px;
}}

/* ---- Splitter handle ---- */
QSplitter::handle {{ background: {sv["divider"]}; }}

/* ---- ScrollArea (preview) ---- */
QScrollArea#previewScroll {{
    background: {sv["inset"]}; border: 1px solid {sv["border_soft"]}; border-radius: {R_MD}px;
}}

/* ---- Scrollbars — 5px wide, rounded ---- */
QScrollBar:vertical {{ background: transparent; width: 5px; border-radius: 3px; }}
QScrollBar::handle:vertical {{ background: {sv["scroll"]}; border-radius: 3px; min-height: 20px; }}
QScrollBar::handle:vertical:hover {{ background: {sv["scroll_hover"]}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 5px; }}
QScrollBar::handle:horizontal {{ background: {sv["scroll"]}; border-radius: 3px; min-width: 20px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ---- Dialogs ---- */
QDialog, QMessageBox {{
    background-color: {sv["card_strong"]}; color: {t_["text"]};
}}
QDialog QLabel, QMessageBox QLabel {{
    color: {t_["text"]}; background: transparent;
}}
QDialog QPushButton, QMessageBox QPushButton {{
    color: {t_["text"]}; background: {sv["control"]}; border: 1px solid {sv["border"]};
    border-radius: {R_MD}px; padding: 6px 14px; min-width: 72px;
}}
QDialog QPushButton:hover, QMessageBox QPushButton:hover {{
    background: {sv["nav_hover"]};
}}
QDialog QLineEdit {{
    background: {sv["control_focus"]}; color: {t_["text"]}; border: 1px solid {p}; border-radius: 8px; padding: 7px 9px;
}}

/* ---- Disabled fallback ---- */
QPushButton:disabled {{ background: {sv["disabled"]}; color: {t_["text2"]}; border: 1px solid {bm}; }}
"""


# ═══════════════════════════════════════════════════════════════════════════
# Theme Persistence


def load_theme() -> dict:
    try:
        if _theme_path.exists():
            data = json.loads(_theme_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                mode = data.get("_mode", "dark")
                overrides = {k: v for k, v in data.items() if k != "_mode" and k in TOKENS}
                overrides["_mode"] = mode
                return overrides
    except Exception:
        pass
    return {"_mode": "light"}


def save_theme(theme: dict) -> None:
    _theme_path.parent.mkdir(parents=True, exist_ok=True)
    _theme_path.write_text(json.dumps(theme, indent=2, ensure_ascii=False),
                           encoding="utf-8")


def get_current_mode() -> str:
    """Returns 'dark' or 'light' based on saved preference."""
    t = load_theme()
    return t.get("_mode", "dark")


def build_for_mode(mode: str = "dark", overrides: dict | None = None) -> str:
    """Build QSS for the given mode ('dark' or 'light')."""
    return build(resolved_tokens(mode, overrides))
