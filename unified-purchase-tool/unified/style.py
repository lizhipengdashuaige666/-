"""Unified design tokens and QSS builder for 采购工作台.

Apple-inspired design system with semantic color tokens, elevation hierarchy,
and unified typography scale.

Usage (new code):
  from unified import style
  bg = style.Surface.Window
  btn_color = style.Fill.Primary
  shadow = style.Elevation.card

Legacy flat names (L_BG, TEXT, BORDER, etc.) remain as aliases — all existing
callers continue to work unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect


# ═══════════════════════════════════════════════════════════════════════════
# Semantic Color Tokens  (preferred for all new code)
# ═══════════════════════════════════════════════════════════════════════════

class Surface:
    Window  = "#F3F6FA"    # calm app canvas, content should lead
    Sidebar = "#EDF2F7"    # subdued navigation rail
    Panel   = "#F7F9FC"    # quiet work area grouping
    Card    = "#FFFFFF"    # 100% — 纯白内容
    Inset   = "#F8FAFC"    # low-emphasis inset controls


class SurfaceDark:
    """Dark-mode surface hierarchy (cool night undertones)."""
    Window  = "#1C1C1E"
    Sidebar = "#222226"
    Panel   = "#28282C"
    Card    = "#2C2C30"
    Inset   = "#323236"


class Text:
    Primary   = "#111827"    # 标题 — 近乎纯黑，contrast 15:1
    Secondary = "#374151"    # 正文 — 深灰，与 Primary 明显拉开跨度
    Tertiary  = "#64748B"    # 辅助 — 中灰
    Disabled  = "#94A3B8"    # Disabled — quiet blue gray


class TextDark:
    Primary   = "#F5F5F7"
    Secondary = "#A0A4AE"
    Tertiary  = "#6B7280"
    Disabled  = "#4B4E55"


class Fill:
    Primary   = "#0057D9"
    Hover     = "#0B66F0"
    Pressed   = "#0046B3"
    Success   = "#2B8A3E"
    Warning   = "#D97706"
    Danger    = "#DC2626"
    Secondary = "#E8ECF2"


class FillDark:
    Primary   = "#0A84FF"
    Hover     = "#409CFF"
    Pressed   = "#006DDF"
    Success   = "#30D158"
    Warning   = "#FF9F0A"
    Danger    = "#FF453A"
    Secondary = "#2A2E34"


class Border:
    Subtle = "#B3BBC9"    # 明确可见的边框
    Strong = "#969FB0"    # 强边框
    Soft   = "#C5CDD9"   # 软边框
    Focus  = "#007AFF"   # 聚焦环


class BorderDark:
    Subtle = "rgba(255,255,255,0.08)"
    Strong = "rgba(255,255,255,0.14)"
    Soft   = "rgba(255,255,255,0.05)"
    Focus  = "#0A84FF"


class Elevation:
    """(offset_y, blur_radius, alpha) for drop shadows.
    blur_radius is used directly (no multiplication)."""
    none  = (0, 0, 0)
    card  = (0, 20, 0.06)
    panel = (0, 30, 0.08)
    popup = (0, 40, 0.12)
    modal = (0, 60, 0.18)


class ElevationLight:
    """Softer shadows for light themes.
    blur_radius is used directly (no multiplication)."""
    none  = (0, 0, 0)
    card  = (0, 20, 0.03)    # card 层：offset 0, blur 20, alpha 3%
    panel = (0, 28, 0.05)    # panel 层：offset 0, blur 28, alpha 5%
    popup = (0, 40, 0.09)    # popup 层：offset 0, blur 40, alpha 9%
    modal = (0, 60, 0.13)    # modal 层：offset 0, blur 60, alpha 13%




class Radius:
    """Unified corner radii system."""
    Control   = 10    # buttons, inputs, list items
    Container = 14    # cards, panels
    Window    = 18    # outer frames
    DropZone  = 20    # large drop areas


class FontSize:
    Display      = 28
    PageTitle    = 24
    SectionTitle = 18
    Body         = 14
    Label        = 13
    Caption      = 12


class FontWeight:
    Regular  = 400
    Medium   = 500
    Semibold = 600
    Bold     = 700


# ═══════════════════════════════════════════════════════════════════════════
# DEPRECATED: Legacy flat token names
# Kept as backward-compatible aliases.  All existing callers (shell.py,
# gui.py, app.py, watermark_app.py) continue to work unchanged.
# ═══════════════════════════════════════════════════════════════════════════

PRIMARY   = FillDark.Primary
SUCCESS   = FillDark.Success
WARNING   = FillDark.Warning
DANGER    = FillDark.Danger

TEXT      = TextDark.Primary
TEXT2     = TextDark.Secondary
TEXT3     = TextDark.Tertiary

BG        = SurfaceDark.Window
CARD      = SurfaceDark.Card
CARD_ALT  = SurfaceDark.Inset
SIDEBAR   = SurfaceDark.Sidebar

INPUT_BG        = "#323236"
INPUT_BG_FOCUS  = "#48484E"
TOOLBAR_BG      = "#2C2C30"

BORDER    = BorderDark.Subtle
BORDER_M  = BorderDark.Strong
BORDER_S  = BorderDark.Soft

SELECTION_BG  = "rgba(10,132,255,0.18)"
HOVER_BG      = "rgba(255,255,255,0.06)"

LOG_BG        = "#1A1A1E"
ERR_BG        = "#3D1C1A"
WARN_BG       = "#3D2E10"

TAG_GREEN  = FillDark.Success
TAG_ORANGE = FillDark.Warning
TAG_BLUE   = FillDark.Primary
TAG_RED    = FillDark.Danger
TAG_GRAY   = "#636368"

# Light-mode legacy aliases
L_PRIMARY   = Fill.Primary
L_SUCCESS   = Fill.Success
L_WARNING   = Fill.Warning
L_DANGER    = Fill.Danger

L_TEXT      = Text.Primary
L_TEXT2     = Text.Secondary
L_TEXT3     = Text.Tertiary

L_BG        = Surface.Window
L_CARD      = Surface.Card
L_CARD_ALT  = Surface.Inset
L_SIDEBAR   = Surface.Sidebar

L_INPUT_BG        = Surface.Inset
L_INPUT_BG_FOCUS  = Surface.Card
L_TOOLBAR_BG      = "rgba(238,242,246,0.82)"

L_BORDER    = Border.Subtle
L_BORDER_M  = Border.Strong
L_BORDER_S  = Border.Soft

L_SELECTION_BG  = "rgba(0,122,255,0.10)"
L_HOVER_BG      = "rgba(0,0,0,0.04)"

L_LOG_BG        = "#F8F9FC"
L_ERR_BG        = "#FEE2E2"
L_WARN_BG       = "#FFF4DE"

L_TAG_GREEN  = "#248A3D"
L_TAG_ORANGE = "#C93400"
L_TAG_BLUE   = "#007AFF"
L_TAG_RED    = "#D42A1F"
L_TAG_GRAY   = Text.Disabled

# Radius legacy aliases
R_SM  = Radius.Control
R_MD  = Radius.Container
R_LG  = Radius.Window
R_XL  = Radius.DropZone

# Font weight legacy aliases
W_REG  = FontWeight.Regular
W_MED  = FontWeight.Medium
W_SB   = FontWeight.Semibold
W_BOLD = FontWeight.Bold

# Font stack
FONT = ('-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", '
        '"PingFang SC", "Microsoft YaHei UI", "Segoe UI", system-ui')
FONT_MONO = ('"SF Mono", "Cascadia Code", Consolas, '
             '"PingFang SC", monospace')

# Elevation presets — use ELEVATION / ELEVATION_LIGHT dicts for semantic access.
# Legacy numeric-index presets kept for apply_shadow() backward compat.
def _elevation_for_level(is_light: bool, level: int):
    dark_levels = {0: Elevation.none, 1: Elevation.card,
                   2: Elevation.panel, 3: Elevation.popup, 4: Elevation.modal}
    light_levels = {0: ElevationLight.none, 1: ElevationLight.card,
                    2: ElevationLight.panel, 3: ElevationLight.popup,
                    4: ElevationLight.modal}
    src = light_levels if is_light else dark_levels
    return src.get(level, ElevationLight.card if is_light else Elevation.card)

_theme_path = Path(__file__).parent / "theme.json"


# ═══════════════════════════════════════════════════════════════════════════
# Color utilities
# ═══════════════════════════════════════════════════════════════════════════

def _lighten(hex_color: str, factor: float = 0.15) -> str:
    """Return a lighter variant (mixes toward white)."""
    c = QColor(hex_color)
    return QColor(
        int(c.red()   + (255 - c.red())   * factor),
        int(c.green() + (255 - c.green()) * factor),
        int(c.blue()  + (255 - c.blue())  * factor),
    ).name()


def _darken(hex_color: str, factor: float = 0.12) -> str:
    """Return a darker variant (mixes toward black)."""
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


def _mix_over(base_hex: str, overlay_hex: str, opacity: float = 1.0) -> str:
    """Simulate a translucent overlay composited over a solid base."""
    base = QColor(base_hex)
    overlay = QColor(overlay_hex)
    a = overlay.alphaF() * opacity
    return QColor(
        int(base.red()   + (overlay.red()   - base.red())   * a),
        int(base.green() + (overlay.green() - base.green()) * a),
        int(base.blue()  + (overlay.blue()  - base.blue())  * a),
    ).name()


# ═══════════════════════════════════════════════════════════════════════════
# Token dict for theme persistence
# ═══════════════════════════════════════════════════════════════════════════

def _make_tokens(mode: str) -> dict:
    """Return a unified token dict from semantic classes for a given mode."""
    surf = Surface if mode == "light" else SurfaceDark
    txt = Text if mode == "light" else TextDark
    fill = Fill if mode == "light" else FillDark
    bdr = Border if mode == "light" else BorderDark
    return {
        "primary": fill.Primary, "hover": fill.Hover, "pressed": fill.Pressed,
        "success": fill.Success,
        "warning": fill.Warning, "danger": fill.Danger,
        "text": txt.Primary, "text2": txt.Secondary, "text3": txt.Tertiary,
        "text_disabled": txt.Disabled,
        "bg": surf.Window, "card": surf.Card, "card_alt": surf.Inset,
        "panel": surf.Panel, "sidebar": surf.Sidebar,
        "border": bdr.Subtle, "border_m": bdr.Strong, "border_s": bdr.Soft,
        "selection_bg": "rgba(0,87,217,0.08)" if mode == "light"
                        else "rgba(10,132,255,0.18)",
        "selection_bg2": "rgba(0,87,217,0.08)" if mode == "light"
                         else "rgba(10,132,255,0.18)",
        "hover_bg": "rgba(0,0,0,0.04)" if mode == "light"
                    else "rgba(255,255,255,0.06)",
        "log_bg": surf.Inset,
        "err_bg": "#FEE2E2" if mode == "light" else "#3D1C1A",
        "warn_bg": "#FFF4DE" if mode == "light" else "#3D2E10",
        "err_text": fill.Danger,
        "toolbar_bg": "#FFFFFF" if mode == "light" else "#2C2C30",
        "input_bg": surf.Inset,
        "input_bg_focus": "#FFFFFF" if mode == "light" else surf.Inset,
        "tag_green": fill.Success, "tag_orange": fill.Warning,
        "tag_blue": fill.Primary, "tag_red": fill.Danger,
        "tag_gray": Text.Disabled if mode == "light" else "#636368",
        "_mode": mode,
    }


# Legacy dicts — derived from semantic tokens, never stale
def _get_legacy_tokens(mode: str) -> dict:
    t = _make_tokens(mode)
    t.pop("_mode", None)
    return t


TOKENS = _get_legacy_tokens("dark")
LIGHT_TOKENS = _get_legacy_tokens("light")


def resolved_tokens(mode: str = "dark", overrides: dict | None = None) -> dict:
    """Return the full effective token set for a saved theme mode."""
    base = _make_tokens(mode)
    if overrides:
        for k, v in overrides.items():
            if k in base and not k.startswith("_"):
                base[k] = v
    base["_mode"] = mode
    return base


def _is_light_theme(t_: dict) -> bool:
    return t_.get("_mode") == "light" or t_.get("bg") == Surface.Window


# ═══════════════════════════════════════════════════════════════════════════
# Surface value builder
# ═══════════════════════════════════════════════════════════════════════════

def _surface_values(t_: dict) -> dict[str, str]:
    """Build the surface hierarchy — canvas → sidebar → card → inset → control."""
    surf = Surface if _is_light_theme(t_) else SurfaceDark
    bdr = Border if _is_light_theme(t_) else BorderDark
    return {
        "canvas": t_.get("bg", surf.Window),
        "sidebar": t_.get("sidebar", surf.Sidebar),
        "panel": t_.get("panel", surf.Panel),
        "card": t_.get("card", surf.Card),
        "card_strong": t_.get("card", surf.Card),
        "inset": t_.get("card_alt", surf.Inset),
        "control": t_.get("input_bg", surf.Inset),
        "control_focus": t_.get("input_bg_focus", "#FFFFFF" if _is_light_theme(t_) else "#48484E"),
        "border": t_.get("border", bdr.Subtle),
        "border_soft": t_.get("border_s", bdr.Soft),
        "divider": t_.get("border", bdr.Subtle),
        "nav_hover": "rgba(0,0,0,0.04)" if _is_light_theme(t_)
                     else "rgba(255,255,255,0.06)",
        "disabled": "#EDF0F6" if _is_light_theme(t_) else "#2A2A30",
        "scroll": "rgba(120,143,170,0.28)" if _is_light_theme(t_)
                  else "rgba(255,255,255,0.10)",
        "scroll_hover": "rgba(92,116,146,0.45)" if _is_light_theme(t_)
                        else "rgba(255,255,255,0.18)",
        "table_header": t_.get("card_alt", surf.Inset),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Drop shadow — elevation-based, backward-compatible
# ═══════════════════════════════════════════════════════════════════════════

_CARD_OBJECT_NAMES = {
    "sideCard", "centerCard", "reviewCard", "statCard",
    "renameCard", "card", "ocrInfoCard", "previewCard",
    "dropPanel", "panel", "sidebar",
}


def apply_shadow(widget: QFrame, blur: int | None = None,
                 offset: tuple | None = None, alpha: float | None = None,
                 elevation: int = 1, is_light: bool = True) -> None:
    """Apply a soft drop shadow to make a card feel lifted off the canvas.

    Supports two calling conventions:
    - Legacy:  apply_shadow(widget, blur=12, offset=(0,3), alpha=0.05)
    - Modern:  apply_shadow(widget, elevation=1, is_light=True)

    Elevation 0 = flat/inset, 1 = card, 2 = panel, 3 = dialog, 4 = modal.
    """
    if blur is not None or offset is not None or alpha is not None:
        b = blur if blur is not None else 12
        ox, oy = offset if offset is not None else (0, 2)
        a = alpha if alpha is not None else 0.05
    else:
        oy, b, a = _elevation_for_level(is_light, elevation)

    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(b)
    shadow.setOffset(0, oy)
    c = QColor(0, 0, 0, int(255 * a))
    shadow.setColor(c)
    widget.setGraphicsEffect(shadow)


def apply_shadows_to_tree(root, skip: set[str] | None = None,
                          is_light: bool = True) -> None:
    """Walk a widget tree and apply drop shadows to card-style frames."""
    if skip is None:
        skip = set()
    for w in root.findChildren(QFrame):
        name = w.objectName()
        if name in _CARD_OBJECT_NAMES and name not in skip:
            apply_shadow(w, elevation=1, is_light=is_light)


# ═══════════════════════════════════════════════════════════════════════════
# QSS Builder
# ═══════════════════════════════════════════════════════════════════════════

def build(theme: dict | None = None) -> str:
    """Build the complete unified QSS stylesheet from tokens."""
    t_ = _make_tokens("light")  # default — overridden by theme
    if theme:
        t_.update(theme)
    p = t_["primary"]
    d = t_["danger"]
    s = t_["success"]
    w = t_["warning"]
    ph = t_["hover"]
    pp = t_["pressed"]
    sv = _surface_values(t_)

    return f"""
/* ==================================================================
   Unified QSS — Apple-Inspired Design System
   Canvas {sv["canvas"]} / Cards {sv["card"]} / Sidebar {sv["sidebar"]}
   Semantic Tokens + Elevation Hierarchy + Refined Typography
   Dual selectors [role=card] + #objectName for migration
   ================================================================== */

QMainWindow {{ background: {sv["canvas"]}; }}
QMainWindow > QWidget {{
    background: {sv["canvas"]}; color: {t_["text"]};
    font-family: {FONT}; font-size: {FontSize.Body}px; font-weight: {W_REG};
}}

QLabel {{ color: {t_["text"]}; }}

/* ── Sidebar ── */
QFrame#sharedSidebar {{
    background: {sv["sidebar"]};
    border: 0;
    border-right: 1px solid {sv["border_soft"]};
}}
QLabel#appTitle {{
    font-size: {FontSize.SectionTitle}px; font-weight: {W_SB}; color: {t_["text2"]};
    padding: 12px 8px 10px 8px;
}}
QLabel#navSection {{
    font-size: {FontSize.Caption}px; font-weight: {W_MED}; color: {t_["text3"]};
    letter-spacing: 0.2px; text-transform: uppercase;
    padding: 10px 8px 6px 8px; margin-top: 2px;
}}
QPushButton#navItem,
QPushButton[role="nav"] {{
    background: transparent; color: {t_["text3"]};
    border: 0;
    border-left: 3px solid transparent;
    border-radius: 0;
    padding: 11px 10px 11px 13px;
    font-weight: {W_MED}; font-size: {FontSize.Body}px; text-align: left;
}}
QPushButton#navItem:hover,
QPushButton[role="nav"]:hover {{ background: {sv["nav_hover"]}; }}
QPushButton#navItem:checked,
QPushButton[role="nav"]:checked {{
    background: transparent; color: {p}; font-weight: {W_BOLD};
    border-left: 3px solid {p};
    margin-left: 0; margin-right: 0;
}}
QLabel#versionLabel {{
    font-size: {FontSize.Caption}px; color: {t_["text3"]}; padding: 10px 8px;
}}

/* ── Content area ── */
QWidget#contentArea {{ background: {sv["canvas"]}; }}

/* ── Topbar ── */
QFrame#topbar {{
    background: {t_.get("toolbar_bg", TOOLBAR_BG)};
    border: 0;
    border-bottom: 1px solid {sv["border"]};
}}
QLabel#topbarTitle {{
    font-size: 30px; font-weight: {W_BOLD}; color: {t_["text"]};
    letter-spacing: 0;
    padding: 0;
}}
QLabel#topbarSubtitle {{
    font-size: {FontSize.Label}px; color: {t_["text3"]};
    padding: 0;
}}
QPushButton#topNavItem {{
    background: transparent; color: {t_["text"]};
    border: 1px solid transparent;
    border-radius: {R_SM}px; padding: 7px 12px; min-height: 30px;
    font-size: {FontSize.Caption}px; font-weight: {W_MED};
}}
QPushButton#topNavItem:hover {{
    background: {sv["nav_hover"]};
}}
QPushButton#topNavItem:checked {{
    background: {t_["selection_bg"]}; color: {p};
}}
QLineEdit#globalSearch {{
    background: {sv["control"]}; color: {t_["text2"]};
    border: 1px solid {sv["border"]};
    border-radius: {Radius.Container}px; padding: 8px 14px; font-size: {FontSize.Caption}px;
    placeholder-text-color: {t_["text3"]};
}}

QPushButton#modeChip {{
    background: transparent; color: {t_["text2"]};
    border: 1px solid {sv["border"]};
    border-radius: {R_SM}px;
    padding: 0 14px;
    min-height: 34px;
    font-size: {FontSize.Caption}px;
    font-weight: {W_MED};
}}
QPushButton#modeChip:hover {{
    background: {sv["control"]}; color: {t_["text"]};
}}
QPushButton#modeChip:checked {{
    background: {t_["selection_bg"]};
    color: {p};
    border-color: {p};
    font-weight: {W_BOLD};
}}

/* ── Cards — single surface, shadow for depth, border on hover only ── */
QFrame#sideCard, QFrame#centerCard, QFrame#reviewCard,
QFrame#statCard, QFrame#renameCard, QFrame#card,
QFrame[role="card"] {{
    background: {sv["card"]};
    border: 1px solid {sv["border_soft"]};
    border-radius: {Radius.Control}px;
}}
QFrame#centerCard {{
    background: transparent;
    border: 0;
    border-radius: 0;
}}
QFrame#statCard {{
    background: transparent;
    border: 0;
    border-radius: 0;
}}

/* ── Inset panels ── */
QFrame#ocrInfoCard,
QFrame[role="inset"] {{
    background: transparent;
    border: 0;
    border-radius: 0;
}}
QFrame#previewCard {{
    background: {sv["inset"]};
    border: 1px dashed {t_["border_m"]};
    border-radius: {Radius.Container}px;
}}
QFrame#previewCard:hover {{
    border-color: {p};
}}

/* ── Drop panel ── */
QFrame#dropPanel,
QFrame[role="drop"] {{
    background: {sv["card"]};
    border: 2px dashed {_alpha(p, 0.30)};
    border-radius: {Radius.DropZone}px;
}}
QFrame#dropPanel:hover,
QFrame[role="drop"]:hover {{ border-color: {p}; }}
QLabel#dropTitle {{
    font-size: {FontSize.Body}px; font-weight: {W_MED}; color: {t_["text2"]};
}}
QLabel#hint {{
    font-size: {FontSize.Caption}px; color: {t_["text3"]};
}}

/* ── Panel / sidebar frames ── */
QFrame#panel, QFrame#sidebar,
QFrame[role="panel"] {{
    background: {sv["panel"]};
    border: none;
    border-radius: {Radius.Container}px;
}}

/* ── Buttons — dual selectors for migration ── */
QPushButton {{
    min-height: 34px; border-radius: {Radius.Control}px;
    padding: 8px 16px;
    font-size: {FontSize.Body}px; font-weight: {W_SB};
}}
QPushButton#primaryBtn,
QPushButton[role="primary"] {{
    background-color: {p}; color: #FFFFFF; border: 1px solid {p};
    padding: 11px 24px; min-height: 40px;
    font-weight: {W_BOLD};
}}
QPushButton#primaryBtn:enabled,
QPushButton[role="primary"]:enabled {{
    background-color: {p}; color: #FFFFFF; border: 1px solid {p};
}}
QPushButton#primaryBtn:hover,
QPushButton[role="primary"]:hover {{ background-color: {ph}; border-color: {ph}; }}
QPushButton#primaryBtn:pressed,
QPushButton[role="primary"]:pressed {{ background-color: {pp}; border-color: {pp}; }}
QPushButton#primaryBtn:disabled,
QPushButton[role="primary"]:disabled {{
    background-color: transparent; color: {t_["text_disabled"]};
    border: 1px solid {sv["border_soft"]};
}}
QPushButton#secondaryBtn,
QPushButton[role="secondary"] {{
    background: transparent; color: {t_["text2"]};
    border: 1px solid {sv["border"]};
    padding: 10px 22px; min-height: 36px;
}}
QPushButton#secondaryBtn:hover,
QPushButton[role="secondary"]:hover {{
    background: {sv["control"]}; color: {t_["text"]}; border-color: {sv["border"]};
}}
QPushButton#secondaryBtn:pressed,
QPushButton[role="secondary"]:pressed {{ background: {t_["selection_bg"]}; }}
QPushButton#secondaryBtn:disabled,
QPushButton[role="secondary"]:disabled {{
    background: transparent; color: {t_["text_disabled"]};
    border: 1px solid {sv["border_soft"]};
}}
QPushButton#filledSecondaryBtn {{
    background: #D9ECFF;
    color: {p};
    border: 1px solid #A8D1FF;
    border-radius: {Radius.Control}px;
    padding: 0 24px;
    min-height: 42px;
    font-size: {FontSize.Body}px;
    font-weight: {W_BOLD};
}}
QPushButton#filledSecondaryBtn:hover {{
    background: #CBE5FF;
    border-color: #83BCFF;
}}
QPushButton#filledSecondaryBtn:pressed {{
    background: #B8D9FF;
}}
QPushButton#filledSecondaryBtn:disabled {{
    background: transparent;
    color: {t_["text_disabled"]};
    border: 1px solid {sv["border_soft"]};
}}
QPushButton#stopBtn {{
    background: {t_["err_bg"]}; color: {d};
    border: 1px solid #FF9E9A;
    padding: 10px 22px; min-height: 36px;
}}
QPushButton#stopBtn:hover {{
    background: {d}; color: #FFFFFF; border-color: {d};
}}
QPushButton#stopBtn:pressed {{ background: #B3241A; color: #FFFFFF; }}
QPushButton#startBtn {{
    background: {p}; color: #FFFFFF; border: none;
    padding: 10px 22px; min-height: 36px;
}}
QPushButton#startBtn:hover {{ background: {ph}; }}
QPushButton[role="danger"] {{
    background: {d}; color: #FFFFFF; border: none;
    border-radius: {Radius.Control}px; padding: 12px 24px;
    font-size: {FontSize.Label}px; font-weight: {W_BOLD}; min-height: 40px;
}}
QPushButton[role="danger"]:hover {{ background: #B3241A; }}
QPushButton[role="danger"]:disabled {{
    background: {sv["control"]}; color: {d};
    border: 1px solid #FF9E9A;
}}

/* ── Ghost / icon ── */
QPushButton#ghostButton,
QPushButton[role="ghost"] {{
    background: transparent; color: {t_["text"]};
    border: none;
    border-radius: {Radius.Control}px; padding: 7px 16px;
    font-weight: {W_MED}; font-size: {FontSize.Caption}px;
}}
QPushButton#ghostButton:hover,
QPushButton[role="ghost"]:hover {{
    background: {sv["nav_hover"]};
}}
QPushButton#iconButton {{
    background: transparent; color: {p}; border: 0;
    border-radius: {R_SM}px; padding: 5px 12px;
    font-weight: {W_MED}; font-size: {FontSize.Caption}px;
}}
QPushButton#iconButton:hover {{ background: #E5F0FF; }}
QPushButton#dangerButton {{
    background: transparent; color: {d};
    border: 1px solid #FF9E9A;
    border-radius: {Radius.Control}px; padding: 7px 16px;
    font-weight: {W_MED}; font-size: {FontSize.Caption}px;
}}
QPushButton#dangerButton:hover {{ background: {d}; color: #FFFFFF; }}

/* ── Filter / chip ── */
QPushButton#filterBtn,
QPushButton[role="filter"] {{
    background: {sv["control"]};
    border: none;
    border-radius: {R_SM}px; padding: 6px 14px;
    font-size: {FontSize.Label}px; font-weight: {W_SB}; color: {t_["text2"]};
}}
QPushButton#filterBtn:hover,
QPushButton[role="filter"]:hover {{ background: {sv["nav_hover"]}; color: {t_["text"]}; }}
QPushButton#filterBtn:checked,
QPushButton[role="filter"]:checked {{
    background: {t_["selection_bg"]}; color: {p};
}}

/* ── File List ── */
QListWidget {{
    background: transparent; border: 0; border-radius: {Radius.Container}px;
    padding: 4px 0; outline: none;
}}
QListWidget::item {{
    border-radius: {R_SM}px; padding: 10px 14px; margin: 2px 6px;
    color: {t_["text"]}; font-size: {FontSize.Body}px; font-weight: {W_MED};
    min-height: 46px; background: transparent;
}}
QListWidget::item:hover:!selected {{ background: {t_["hover_bg"]}; }}
QListWidget::item:selected {{
    background: {t_["selection_bg"]}; color: {t_["text"]};
    font-weight: {W_SB};
}}

/* ── Typography — Content-First Scale ── */
QLabel#toolbarTitle,
QLabel[typography="headline"] {{ font-size: {FontSize.PageTitle}px; font-weight: {W_BOLD}; color: {t_["text"]}; letter-spacing: -0.5px; }}
QLabel#toolbarSubtitle {{ font-size: {FontSize.Caption}px; color: {t_["text2"]}; }}
QLabel#sectionLabel,
QLabel[typography="caption"] {{ font-size: {FontSize.Caption}px; font-weight: {W_MED}; color: {t_["text3"]}; letter-spacing: 0.1px; }}
QLabel#cardTitle,
QLabel[typography="title"] {{ font-size: {FontSize.SectionTitle}px; font-weight: {W_BOLD}; color: {t_["text"]}; letter-spacing: 0; }}
QLabel#sideTitle,
QLabel[typography="side"] {{ font-size: {FontSize.Label}px; font-weight: {W_SB}; color: {t_["text2"]}; letter-spacing: 0; }}
QLabel#sideSubtitle {{ font-size: {FontSize.Caption}px; color: {t_["text3"]}; }}
QLabel#statValue        {{ font-size: {FontSize.PageTitle}px; font-weight: {W_BOLD}; letter-spacing: 0; }}
QLabel#statValue[statRole="pending"] {{ color: {t_["text2"]}; }}
QLabel#statValue[statRole="done"]    {{ color: {s}; }}
QLabel#statValue[statRole="failed"]  {{ color: {d}; }}
QLabel#statValue[statRole="review"]  {{ color: {p}; }}
QLabel#statLabel        {{ font-size: {FontSize.Caption}px; font-weight: {W_MED}; color: {t_["text3"]}; }}
QLabel#infoValue        {{ font-size: {FontSize.Body}px; font-weight: {W_BOLD}; color: {t_["text"]}; }}
QLabel#ocrValue         {{ font-size: {FontSize.Body}px; font-weight: {W_BOLD}; color: {t_["text"]}; background: transparent; }}
QLabel#ocrSummaryValue  {{ font-size: {FontSize.Body}px; font-weight: {W_BOLD}; color: {t_["text"]}; background: transparent; }}
QLabel#ocrPlaceholder,
QLabel[role="placeholder"] {{ font-size: {FontSize.Body}px; font-weight: {W_MED}; color: {t_["text3"]}; background: transparent; }}
QLabel#sectionTitle     {{ font-size: {FontSize.Label}px; font-weight: {W_SB}; color: {t_["text2"]}; letter-spacing: 0.4px; margin-bottom: 2px; }}
QLabel#groupLabel       {{ font-size: {FontSize.Label}px; font-weight: {W_SB}; color: {t_["text"]}; letter-spacing: 0.3px; padding: 4px 0; }}

/* ── Status property colors ── */
QLabel[status_pending="true"]  {{ color: {t_["text2"]}; }}
QLabel[status_progress="true"] {{ color: {w}; }}
QLabel[status_success="true"]  {{ color: {s}; }}
QLabel[status_error="true"]    {{ color: {d}; }}

/* ── Tags (pill-shaped) ── */
QLabel#tagGreen  {{ background: #E0F5E4; color: {s}; border: 1px solid #B2E6BA; border-radius: 8px; padding: 2px 8px; font-weight: {W_SB}; font-size: {FontSize.Caption}px; }}
QLabel#tagOrange {{ background: #FFEAD2; color: {w}; border: 1px solid #FFCD9E; border-radius: 8px; padding: 2px 8px; font-weight: {W_SB}; font-size: {FontSize.Caption}px; }}
QLabel#tagBlue   {{ background: #D9ECFF; color: {p}; border: 1px solid #A8D1FF; border-radius: 8px; padding: 2px 8px; font-weight: {W_SB}; font-size: {FontSize.Caption}px; }}
QLabel#tagRed    {{ background: #FFD6D4; color: {d}; border: 1px solid #FFA39E; border-radius: 8px; padding: 2px 8px; font-weight: {W_SB}; font-size: {FontSize.Caption}px; }}
QLabel#tagGray   {{ background: {sv["control"]}; color: {t_["text2"]}; border: 1px solid {sv["border_soft"]}; border-radius: 8px; padding: 2px 8px; font-weight: {W_MED}; font-size: {FontSize.Caption}px; }}
QLabel#tagWarn   {{ background: #FFF4DE; color: {w}; border: 1px solid #FFCD9E; border-radius: 8px; padding: 2px 8px; font-weight: {W_SB}; font-size: {FontSize.Caption}px; }}

QPushButton#smallBtn,
QPushButton[role="small"] {{
    min-height: 30px; background: transparent; color: {p};
    border: 1px solid {sv["border"]}; border-radius: {R_SM}px;
    padding: 5px 12px; font-size: {FontSize.Caption}px; font-weight: {W_SB};
}}
QPushButton#smallBtn:hover,
QPushButton[role="small"]:hover {{
    background: #E5F0FF; border-color: {p};
}}

/* ── QLineEdit#suggestName ── */
QLineEdit#suggestName {{
    font-size: {FontSize.SectionTitle}px; font-weight: {W_BOLD}; color: {t_["text"]};
    background: #FFFFFF; border: 1px solid {sv["border_soft"]};
    border-radius: {Radius.Control}px; padding: 14px 18px;
}}
QLineEdit#suggestName:focus {{
    border-color: {p}; background: {sv["control_focus"]};
}}
QLineEdit#suggestName[renameState="active"] {{
    border-color: {p}; border-width: 2px;
}}

/* ── Generic inputs ── */
QLineEdit, QComboBox {{
    background: {sv["control"]}; color: {t_["text"]};
    border: 1px solid {sv["border_soft"]};
    border-radius: {Radius.Control}px; padding: 8px 12px; font-size: {FontSize.Body}px;
    selection-background-color: {p};
    placeholder-text-color: {t_["text3"]};
    min-height: 20px;
}}
QLineEdit:focus, QComboBox:focus {{
    background: {sv["control_focus"]}; border: 1px solid {p};
}}
QComboBox::drop-down {{ border: 0; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {sv["card"]}; color: {t_["text"]};
    border: 1px solid {sv["border"]};
    border-radius: {Radius.Control}px; padding: 4px;
    selection-background-color: {t_["selection_bg"]};
}}
QLineEdit#searchBox {{
    background: {sv["control"]}; color: {t_["text"]};
    border: 1px solid {sv["border_soft"]};
    border-radius: {Radius.Control}px; padding: 8px 12px; font-size: {FontSize.Body}px;
    placeholder-text-color: {t_["text3"]};
}}
QLineEdit#searchBox:focus {{
    background: {sv["control_focus"]}; border: 1px solid {p};
}}

/* ── Log / OCR / Message Preview ── */
#logBox, #ocrBox {{
    background: {sv["inset"]}; border: 1px solid {sv["border_soft"]};
    border-radius: {Radius.Control}px; padding: 14px; font-size: {FontSize.Caption}px;
    color: {t_["text"]}; font-family: {FONT_MONO};
}}
QPlainTextEdit#messagePreview {{
    background: {sv["inset"]}; color: {t_["text2"]};
    border: 0; border-radius: {Radius.Control}px; padding: 12px 14px;
    font-family: {FONT_MONO}; font-size: {FontSize.Caption}px;
    min-height: 80px; max-height: 110px;
}}
QPlainTextEdit#wbLogBox {{
    background: {sv["inset"]}; color: {t_["text"]};
    border: 1px solid {sv["border_soft"]};
    border-radius: {Radius.Control}px; padding: 14px;
    font-family: {FONT_MONO}; font-size: {FontSize.Caption}px;
}}

/* ── ProgressBar ── */
QProgressBar {{
    background: {sv["border_soft"]}; border: none;
    border-radius: 4px; height: 6px; font-size: 0;
}}
QProgressBar::chunk {{ background: {p}; border-radius: 4px; }}

/* ── Radio Buttons (segmented control) ── */
QRadioButton {{
    font-size: {FontSize.Caption}px; font-weight: {W_MED}; color: {t_["text2"]};
    background: transparent; border: 1px solid {sv["border_soft"]};
    padding: 8px 16px; spacing: 0;
}}
QRadioButton:first-child {{
    border-top-left-radius: {Radius.Control}px; border-bottom-left-radius: {Radius.Control}px;
}}
QRadioButton:last-child {{
    border-top-right-radius: {Radius.Control}px; border-bottom-right-radius: {Radius.Control}px;
}}
QRadioButton::indicator {{ width: 0; height: 0; }}
QRadioButton:checked {{ background: {t_["selection_bg"]}; color: {p}; border-color: {p}; font-weight: {W_BOLD}; }}

/* ── Message tab radio ── */
QRadioButton#messageTab {{
    background: {sv["control"]}; color: {t_["text2"]};
    border: 0; border-radius: {Radius.Control}px; padding: 8px 14px;
    font-weight: {W_SB}; font-size: {FontSize.Caption}px;
}}
QRadioButton#messageTab::indicator {{ width: 0; height: 0; }}
QRadioButton#messageTab:checked {{ background: {p}; color: #FFFFFF; }}
QRadioButton#messageTab:hover:!checked {{ background: {sv["nav_hover"]}; }}

/* ── Collapse button ── */
QPushButton#collapseBtn {{
    background: transparent; border: none; color: {t_["text"]};
    font-size: {FontSize.Label}px; font-weight: {W_SB}; padding: 5px 0; text-align: left;
}}
QPushButton#collapseBtn:hover {{ color: {p}; }}

/* ── Table ── */
QTableWidget {{
    background: transparent;
    alternate-background-color: {sv["inset"]};
    border: 0; border-radius: {Radius.Container}px;
    gridline-color: transparent;
    selection-background-color: {t_["selection_bg"]};
    selection-color: {t_["text"]};
}}
QTableWidget::item {{ padding: 10px 8px; color: {t_["text"]}; }}
QTableWidget::item:selected {{ color: {t_["text"]}; }}
QHeaderView::section {{
    background: {sv["table_header"]}; color: {t_["text2"]};
    border: 0; border-bottom: 1px solid {sv["border"]}; border-radius: 0;
    padding: 10px 8px; font-weight: {W_SB}; font-size: {FontSize.Label}px;
    letter-spacing: 0.2px;
}}

/* ── Tabs ── */
QTabWidget::pane {{ background: transparent; border: 0; }}
QTabBar::tab {{
    background: transparent; color: {t_["text2"]}; border: 0;
    padding: 10px 18px; font-weight: {W_MED}; font-size: {FontSize.Body}px;
    min-width: 60px;
}}
QTabBar::tab:selected {{
    color: {p}; border-bottom: 2px solid {p}; font-weight: {W_SB};
}}
QTabBar::tab:hover:!selected {{ color: {t_["text"]}; }}

/* ── Toolbar ── */
QWidget#toolbar {{
    background: transparent; border: 0;
}}

/* ── StatusBar ── */
QStatusBar {{
    background: {sv["card"]}; border-top: 1px solid {sv["border"]};
    color: {t_["text2"]}; font-size: {FontSize.Caption}px; min-height: 30px;
}}

/* ── Splitter ── */
QSplitter::handle {{ background: {sv["border"]}; }}

/* ── ScrollArea ── */
QScrollArea#previewScroll {{
    background: {sv["card"]}; border: 1px solid {sv["border_soft"]};
    border-radius: {Radius.Control}px;
}}

/* ── Timeline ── */
QFrame#timelineLine {{
    background: {sv["border_soft"]};
    border: none;
    min-width: 2px; max-width: 2px;
}}

/* ── Scrollbars ── */
QScrollBar:vertical {{ background: transparent; width: 5px; border-radius: 3px; }}
QScrollBar::handle:vertical {{ background: {sv["scroll"]}; border-radius: 3px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {sv["scroll_hover"]}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 5px; }}
QScrollBar::handle:horizontal {{ background: {sv["scroll"]}; border-radius: 3px; min-width: 24px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Dialogs ── */
QDialog, QMessageBox {{
    background-color: {sv["card"]}; color: {t_["text"]};
}}
QDialog QLabel, QMessageBox QLabel {{
    color: {t_["text"]}; background: transparent;
}}
QDialog QPushButton, QMessageBox QPushButton {{
    color: {t_["text"]}; background: {sv["control"]};
    border: 1px solid {sv["border"]};
    border-radius: {Radius.Control}px; padding: 8px 18px; min-width: 80px;
}}
QDialog QPushButton:hover, QMessageBox QPushButton:hover {{
    background: {sv["nav_hover"]};
}}
QDialog QLineEdit {{
    background: {sv["control_focus"]}; color: {t_["text"]};
    border: 1px solid {p}; border-radius: {Radius.Control}px; padding: 8px 12px;
}}

/* ── Disabled fallback ── */
QPushButton:disabled {{ background: transparent; color: {t_["text_disabled"]}; border: 1px solid {sv["border_soft"]}; }}
"""


# ═══════════════════════════════════════════════════════════════════════════
# Theme Persistence
# ═══════════════════════════════════════════════════════════════════════════


def load_theme() -> dict:
    try:
        if _theme_path.exists():
            data = json.loads(_theme_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                mode = data.get("_mode", "light")
                overrides = {k: v for k, v in data.items() if k != "_mode" and k in _make_tokens("light")}
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
    t = load_theme()
    return t.get("_mode", "light")


def build_for_mode(mode: str = "dark", overrides: dict | None = None) -> str:
    return build(resolved_tokens(mode, overrides))
