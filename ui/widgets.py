"""
widgets.py — Reusable UI widgets for Waqt v6.

Extracted from main_window.py (Step 3 of refactor).
Contains:
  - ToggleSwitch         : animated on/off toggle
  - _CB                  : QComboBox without scroll-wheel
  - PrayerIconBadge      : per-prayer drawn icon
  - BellToggle           : per-prayer notification bell
  - PrayerProgressBar    : thin progress bar
  - PrayerRow            : one row in the prayer list
  - HeroCard             : large "next prayer" card
  - SidebarBtn           : sidebar navigation button
  - _Logo                : crescent logo widget
  - _AutoDetectBtn       : GPS-style auto-detect button
  - _SaveButton          : frosted-glass save button
  - _SearchWorker        : QThread for Nominatim city search
  - _LocationDetectWorker: QThread for IP-based location
  - CitySearchWidget     : full city search + auto-detect UI
"""

from __future__ import annotations

import math
import os
import sys

import requests

from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter,
    QPainterPath, QPen, QPixmap,
)
from PyQt6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QWidget,
)

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

from ui.app_theme import AppTheme, ARABIC, PRAYER_COLORS, _t


# ═══════════════════════════════════════════════════════════════════════════════
#  TOGGLE SWITCH
# ═══════════════════════════════════════════════════════════════════════════════

class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._on = checked
        self.setFixedSize(40, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self) -> bool: return self._on
    def setChecked(self, v: bool): self._on = v; self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._on = not self._on
            self.update()
            self.toggled.emit(self._on)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        track = AppTheme.c(AppTheme.accent) if self._on else QColor(28, 40, 33)
        p.setBrush(QBrush(track)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, h // 2, h // 2)
        if not self._on:
            p.setPen(QPen(QColor(255, 255, 255, 14), 0.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(0, 0, w, h, h // 2, h // 2)
        p.setPen(Qt.PenStyle.NoPen)
        tx = w - h + 3 if self._on else 3
        p.setBrush(QBrush(QColor("#fff")))
        p.drawEllipse(tx, 3, h - 6, h - 6)


# ═══════════════════════════════════════════════════════════════════════════════
#  NO-SCROLL COMBO
# ═══════════════════════════════════════════════════════════════════════════════

class _CB(QComboBox):
    def wheelEvent(self, e): e.ignore()


# ═══════════════════════════════════════════════════════════════════════════════
#  PRAYER ICON BADGE
# ═══════════════════════════════════════════════════════════════════════════════

class PrayerIconBadge(QWidget):
    def __init__(self, name: str, state: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self._name = name; self._state = state

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cfg = PRAYER_COLORS.get(self._name, {"stroke": AppTheme.accent, "bg": "#0a1e14"})
        if self._state == "done":
            bg = QColor(255, 255, 255, 5)
            ic = QColor(255, 255, 255, 16)
        else:
            bg = QColor(cfg["bg"])
            ic = QColor(cfg["stroke"])

        p.setBrush(QBrush(bg)); p.setPen(Qt.PenStyle.NoPen)
        r = AppTheme.shape("row_radius")
        p.drawRoundedRect(0, 0, 40, 40, r, r)

        p.setPen(QPen(ic, 1.6, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.GlobalColor.transparent)
        cx, cy, r = 20.0, 20.0, 9.0

        if self._name == "Fajr":
            outer = QPainterPath(); outer.addEllipse(QPointF(cx, cy), r * .75, r * .75)
            inner = QPainterPath(); inner.addEllipse(QPointF(cx + r * .32, cy - r * .08), r * .56, r * .56)
            p.setBrush(QBrush(ic)); p.setPen(Qt.PenStyle.NoPen)
            p.drawPath(outer.subtracted(inner))
            for ox, oy, sr in [(-r * .9, -r * .85, 1.2), (r * .85, -r * .55, 1.0)]:
                p.drawEllipse(QPointF(cx + ox, cy + oy), sr, sr)

        elif self._name == "Sunrise":
            p.setPen(QPen(ic, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(int(cx - r), int(cy + 3), int(cx + r), int(cy + 3))
            p.drawArc(int(cx - r * .55), int(cy + 3 - r * .55), int(r * 1.1), int(r * 1.1), 0, 180 * 16)
            for deg in [0, 45, 90, 135, 180]:
                a = math.radians(deg)
                p.drawLine(int(cx + (r * .72) * math.cos(a)), int((cy + 3) - (r * .72) * math.sin(a)),
                           int(cx + r * math.cos(a)), int((cy + 3) - r * math.sin(a)))

        elif self._name == "Dhuhr":
            p.setPen(QPen(ic, 1.6))
            p.drawEllipse(QPointF(cx, cy), r * .42, r * .42)
            for i in range(8):
                a = math.radians(i * 45)
                p.drawLine(int(cx + (r * .62) * math.cos(a)), int(cy + (r * .62) * math.sin(a)),
                           int(cx + r * math.cos(a)), int(cy + r * math.sin(a)))

        elif self._name == "Asr":
            p.setPen(QPen(ic, 1.6))
            p.drawEllipse(QPointF(cx, cy + 2), r * .38, r * .38)
            for i in range(6):
                a = math.radians(i * 60)
                p.drawLine(int(cx + (r * .58) * math.cos(a)), int((cy + 2) + (r * .58) * math.sin(a)),
                           int(cx + (r * .84) * math.cos(a)), int((cy + 2) + (r * .84) * math.sin(a)))

        elif self._name == "Maghrib":
            p.setPen(QPen(ic, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(int(cx - r), int(cy + 3), int(cx + r), int(cy + 3))
            p.drawArc(int(cx - r * .5), int(cy + 3 - r * .5), int(r), int(r), 0, 180 * 16)

        elif self._name == "Isha":
            outer = QPainterPath(); outer.addEllipse(QPointF(cx - 1, cy), r * .72, r * .72)
            inner = QPainterPath(); inner.addEllipse(QPointF(cx + r * .28, cy - r * .06), r * .53, r * .53)
            p.setBrush(QBrush(ic)); p.setPen(Qt.PenStyle.NoPen)
            p.drawPath(outer.subtracted(inner))
            for ox, oy, sr in [(r * .7, -r * .7, 1.3), (r * .95, 0., 1.0), (r * .6, r * .65, .9)]:
                p.drawEllipse(QPointF(cx + ox, cy + oy), sr, sr)


# ═══════════════════════════════════════════════════════════════════════════════
#  BELL TOGGLE
# ═══════════════════════════════════════════════════════════════════════════════

class BellToggle(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, enabled: bool = True, parent=None):
        super().__init__(parent)
        self._on = enabled
        self.setFixedSize(26, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Toggle notification for this prayer")

    def isOn(self) -> bool: return self._on
    def setOn(self, v: bool): self._on = v; self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._on = not self._on; self.update(); self.toggled.emit(self._on)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        col = QColor(AppTheme.accent) if self._on else QColor(255, 255, 255, 24)
        if self._on:
            p.setBrush(QBrush(AppTheme.accent_qcolor(16))); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(1, 1, w - 2, h - 2, 6, 6)
        p.setPen(QPen(col, 1.3, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.GlobalColor.transparent)
        path = QPainterPath()
        path.moveTo(cx, cy - 5.5)
        path.cubicTo(cx - 3.5, cy - 5.5, cx - 4.5, cy - 2.5, cx - 4.5, cy)
        path.lineTo(cx - 4.5, cy + 2.5); path.lineTo(cx - 6, cy + 4)
        path.lineTo(cx + 6, cy + 4);     path.lineTo(cx + 4.5, cy + 2.5)
        path.lineTo(cx + 4.5, cy)
        path.cubicTo(cx + 4.5, cy - 2.5, cx + 3.5, cy - 5.5, cx, cy - 5.5)
        p.drawPath(path)
        p.drawArc(int(cx - 1.5), int(cy + 4), 3, 3, 0, -180 * 16)
        if not self._on:
            p.setPen(QPen(QColor(180, 60, 60, 120), 1.2))
            p.drawLine(int(cx - 5), int(cy + 5), int(cx + 5), int(cy - 5))


# ═══════════════════════════════════════════════════════════════════════════════
#  PROGRESS BAR
# ═══════════════════════════════════════════════════════════════════════════════

class PrayerProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(AppTheme.shape("progress_h"))
        self._v = 0.0

    def set_progress(self, v: float):
        self._v = max(0.0, min(1.0, v)); self.update()

    def refresh_shape(self):
        """Call after AppTheme.apply_style() changes — updates fixed height."""
        self.setFixedHeight(AppTheme.shape("progress_h"))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = AppTheme.shape("progress_radius")
        p.setBrush(QBrush(QColor(255, 255, 255, 8))); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, r, r)
        if self._v > 0:
            fw = int(w * self._v)
            g = QLinearGradient(0, 0, fw, 0)
            g.setColorAt(0, AppTheme.c(AppTheme.accent))
            g.setColorAt(1, QColor("#5DCAA5"))
            p.setBrush(QBrush(g)); p.drawRoundedRect(0, 0, fw, h, r, r)


# ═══════════════════════════════════════════════════════════════════════════════
#  PRAYER ROW
# ═══════════════════════════════════════════════════════════════════════════════

class PrayerRow(QWidget):
    notif_toggled = pyqtSignal(str, bool)

    def __init__(self, name: str, time_str: str, state: str = "upcoming",
                 lang: str = "en", notif_on: bool = True, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self._name  = name
        self._state = state
        self._hover = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 16, 0)
        layout.setSpacing(0)

        # Active indicator bar
        bar = QWidget(); bar.setFixedWidth(14); bar.setStyleSheet("background:transparent;")
        if state == "active":
            ib = QWidget(bar); ib.setFixedSize(3, 20)
            ib.move(0, (56 - 20) // 2)
            ib.setStyleSheet(f"background:{AppTheme.accent};border-radius:2px;")
        layout.addWidget(bar)

        # Icon
        layout.addWidget(PrayerIconBadge(name, state))
        layout.addSpacing(14)

        # Name + Arabic
        if state == "done":
            name_color = "rgba(212,232,216,0.20)"
            arabic_color = f"{AppTheme.accent_rgba(0.12)}"
            time_color = "rgba(212,232,216,0.15)"
            fw = QFont.Weight.Normal
        elif state == "active":
            name_color = "#f0f8f4"
            arabic_color = f"{AppTheme.accent_rgba(0.55)}"
            time_color = AppTheme.accent
            fw = QFont.Weight.Medium
        else:
            name_color = "rgba(212,232,216,0.60)"
            arabic_color = f"{AppTheme.accent_rgba(0.28)}"
            time_color = "rgba(212,232,216,0.36)"
            fw = QFont.Weight.Normal

        name_lbl = QLabel(_t(lang, name))
        name_lbl.setFont(AppTheme.display_font(12, fw))
        name_lbl.setStyleSheet(f"color:{name_color};")
        name_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(name_lbl)

        layout.addSpacing(8)

        arabic_lbl = QLabel(ARABIC.get(name, ""))
        af = QFont()
        af.setFamilies(["Arabic Typesetting", "Amiri", "Scheherazade New", "Noto Naskh Arabic", "Tahoma"])
        af.setPointSize(10)
        arabic_lbl.setFont(af)
        arabic_lbl.setStyleSheet(f"color:{arabic_color};")
        arabic_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(arabic_lbl)

        layout.addStretch(1)

        time_lbl = QLabel(time_str)
        time_lbl.setFont(AppTheme.display_font(14, fw))
        time_lbl.setStyleSheet(f"color:{time_color};")
        time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(time_lbl)
        layout.addSpacing(12)

        if name != "Sunrise":
            bell = BellToggle(enabled=notif_on)
            bell.toggled.connect(lambda v, n=name: self.notif_toggled.emit(n, v))
            layout.addWidget(bell)
        else:
            layout.addSpacing(26)

    def enterEvent(self, e): self._hover = True;  self.update()
    def leaveEvent(self, e): self._hover = False; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        mx, my = 4, 3

        if self._state == "active":
            p.setBrush(QBrush(QColor(10, 32, 20, 235)))
            p.setPen(QPen(AppTheme.accent_qcolor(55), 0.7))
        elif self._state == "done":
            p.setBrush(QBrush(QColor(8, 10, 9, 160)))
            p.setPen(QPen(QColor(255, 255, 255, 5), 0.5))
        else:
            a = 220 if self._hover else 195
            ba = 16 if self._hover else 9
            p.setBrush(QBrush(QColor(11, 18, 14, a)))
            p.setPen(QPen(QColor(255, 255, 255, ba), 0.5))

        r = AppTheme.shape("row_radius")
        p.drawRoundedRect(QRectF(mx, my, w - mx * 2, h - my * 2), r, r)


# ═══════════════════════════════════════════════════════════════════════════════
#  HERO CARD
# ═══════════════════════════════════════════════════════════════════════════════

class HeroCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("hc")
        self.setFixedHeight(140)
        self.setStyleSheet(
            "QFrame#hc { background: transparent; border-radius: 16px; }"
            "QFrame#hc QLabel { background: transparent; border: none; }"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 16, 22, 12)
        root.setSpacing(0)

        self._badge_row = QHBoxLayout()
        self._badge_row.setSpacing(7)
        root.addLayout(self._badge_row)
        self.badge_lbl = None   # created by _build_badge()
        self._badge_text = "Next prayer"
        self._build_badge()
        root.addSpacing(6)

        main_row = QHBoxLayout()
        main_row.setSpacing(0)

        left = QVBoxLayout()
        left.setSpacing(4)
        left.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.name_lbl = QLabel("—")
        self.name_lbl.setFont(AppTheme.display_font(26, QFont.Weight.Medium))
        self.name_lbl.setStyleSheet("color:#f0f8f4;")
        self.name_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        self.arabic_lbl = QLabel("")
        af = QFont()
        af.setFamilies(["Arabic Typesetting", "Amiri", "Scheherazade New", "Noto Naskh Arabic", "Tahoma"])
        af.setPointSize(12)
        self.arabic_lbl.setFont(af)
        self.arabic_lbl.setStyleSheet(f"color:{AppTheme.accent_rgba(0.38)};")
        self.arabic_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        left.addWidget(self.name_lbl)
        left.addWidget(self.arabic_lbl)

        right = QVBoxLayout()
        right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        right.setSpacing(4)

        self.time_lbl = QLabel("--:--")
        self.time_lbl.setFont(AppTheme.display_font(32, QFont.Weight.Normal))
        self.time_lbl.setStyleSheet(f"color:{AppTheme.accent};")
        self.time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.time_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        self.countdown_lbl = QLabel("--:--:--")
        self.countdown_lbl.setFont(AppTheme.font(11))
        self.countdown_lbl.setStyleSheet("color:rgba(255,255,255,0.24);")
        self.countdown_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.countdown_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        right.addWidget(self.time_lbl)
        right.addWidget(self.countdown_lbl)

        main_row.addLayout(left)
        main_row.addStretch()
        main_row.addLayout(right)

        root.addLayout(main_row)
        root.addStretch()

        self._bar = PrayerProgressBar()
        root.addWidget(self._bar)

    def _build_badge(self):
        """(Re)builds the badge row for the current AppTheme.style."""
        while self._badge_row.count():
            item = self._badge_row.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        if AppTheme.shape("badge_pill"):
            # Playful: filled rounded pill, dark text on accent bg
            self.badge_lbl = QLabel(self._badge_text)
            self.badge_lbl.setStyleSheet(
                f"background:{AppTheme.accent};color:#04342c;"
                "font-size:11px;font-weight:500;"
                "padding:4px 12px;border-radius:10px;")
            self._badge_row.addWidget(self.badge_lbl)
        else:
            # Minimal: small dot + uppercase muted label
            dot = QWidget(); dot.setFixedSize(7, 7)
            dot.setStyleSheet(f"background:{AppTheme.accent};border-radius:4px;")
            self.badge_lbl = QLabel(self._badge_text)
            self.badge_lbl.setStyleSheet(
                f"color:{AppTheme.accent_rgba(0.60)};font-size:10px;"
                "letter-spacing:.07em;font-weight:500;")
            self._badge_row.addWidget(dot)
            self._badge_row.addWidget(self.badge_lbl)
        self._badge_row.addStretch()

    def refresh_shape(self):
        """Call after AppTheme.apply_style() changes to re-skin badge/bar."""
        self._badge_text = self.badge_lbl.text() if self.badge_lbl else self._badge_text
        self._build_badge()
        self._bar.refresh_shape()
        self.update()

    def set_progress(self, v: float):
        self._bar.set_progress(v)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        rad = AppTheme.shape("card_radius")
        b_alpha = AppTheme.shape("border_alpha")

        p.setBrush(QBrush(QColor(5, 20, 13, 240)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), rad, rad)

        g = QLinearGradient(0, 0, w * .7, h * .7)
        g.setColorAt(0, AppTheme.accent_qcolor(20))
        g.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(g))
        p.drawRoundedRect(QRectF(0, 0, w, h), rad, rad)

        if b_alpha > 0:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(29, 158, 117, b_alpha), 0.8))
            p.drawRoundedRect(QRectF(.4, .4, w - .8, h - .8), rad, rad)


# ═══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR BUTTON
# ═══════════════════════════════════════════════════════════════════════════════

class SidebarBtn(QWidget):
    clicked = pyqtSignal()

    _W = 72; _H = 62; _ICON_SZ = 20; _TOP_H = 42

    def __init__(self, icon_path: str, label: str = "", active: bool = False, tooltip: str = ""):
        super().__init__()
        self._path   = icon_path
        self._label  = label
        self._active = active
        self._hover  = False
        self._px: QPixmap | None = None
        self.setFixedSize(self._W, self._H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip: self.setToolTip(tooltip)
        if os.path.exists(icon_path):
            self._px = QPixmap(icon_path)

    def setActive(self, v: bool): self._active = v; self.update()
    def enterEvent(self, e): self._hover = True;  self.update()
    def leaveEvent(self, e): self._hover = False; self.update()
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton: self.clicked.emit()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, top_h = self._W, self._TOP_H

        if self._active:
            p.setBrush(QBrush(AppTheme.c(AppTheme.accent)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(0, (top_h - 20) // 2 + 4, 3, 20, 1, 1)

        bg_a = 52 if self._active else (20 if self._hover else 0)
        if bg_a:
            p.setBrush(QBrush(QColor(29, 158, 117, bg_a)))
            p.setPen(Qt.PenStyle.NoPen)
            r = AppTheme.shape("row_radius")
            p.drawRoundedRect(8, 4, w - 16, top_h - 4, r, r)

        sz = self._ICON_SZ; iy = (top_h - sz) // 2; ox = (w - sz) // 2
        if self._px and not self._px.isNull():
            tinted = QPixmap(self._px.size())
            tinted.fill(Qt.GlobalColor.transparent)
            tp = QPainter(tinted)
            tp.setRenderHint(QPainter.RenderHint.Antialiasing)
            icon_c = (AppTheme.c(AppTheme.accent) if self._active else
                      QColor(255, 255, 255, 175 if self._hover else 70))
            tp.fillRect(tinted.rect(), icon_c)
            tp.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            tp.drawPixmap(0, 0, self._px); tp.end()
            scaled = tinted.scaled(sz, sz, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap(ox, iy, scaled)
        else:
            fc = AppTheme.c(AppTheme.accent) if self._active else QColor(255, 255, 255, 70)
            p.setBrush(QBrush(fc)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(ox + 5, iy + 5, 10, 10)

        if self._label:
            lc = (QColor(AppTheme.accent) if self._active else
                  QColor(255, 255, 255, 155 if self._hover else 50))
            p.setPen(lc)
            p.setFont(AppTheme.font(8))
            p.drawText(QRectF(0, top_h + 1, w, 14),
                       Qt.AlignmentFlag.AlignHCenter, self._label)


# ═══════════════════════════════════════════════════════════════════════════════
#  LOGO WIDGET
# ═══════════════════════════════════════════════════════════════════════════════

class _Logo(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(72, 54)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Home")

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h * .42

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(AppTheme.accent_qcolor(7)))
        p.drawEllipse(QPointF(cx, cy), 18, 18)
        p.setPen(QPen(AppTheme.accent_qcolor(20), 0.5))
        p.setBrush(Qt.GlobalColor.transparent)
        p.drawEllipse(QPointF(cx, cy), 14, 14)

        outer = QPainterPath(); outer.addEllipse(QPointF(cx, cy), 10, 10)
        inner = QPainterPath(); inner.addEllipse(QPointF(cx + 4.5, cy - 1), 7.6, 7.6)
        p.setBrush(QBrush(AppTheme.c(AppTheme.accent))); p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(outer.subtracted(inner))

        p.setPen(QColor(255, 255, 255, 55))
        p.setFont(AppTheme.font(7, QFont.Weight.Medium))
        p.drawText(QRectF(0, h * .76, w, 12), Qt.AlignmentFlag.AlignHCenter, "WAQT")


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTO-DETECT BUTTON
# ═══════════════════════════════════════════════════════════════════════════════

class _AutoDetectBtn(QPushButton):
    def paintEvent(self, ev):
        super().paintEvent(ev)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy, r = 20.0, self.height() / 2, 7.0
        p.setPen(QPen(QColor(AppTheme.accent), 1.5))
        p.setBrush(Qt.GlobalColor.transparent)
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(AppTheme.accent)))
        p.drawEllipse(QPointF(cx, cy), 2.5, 2.5)
        p.setPen(QPen(QColor(AppTheme.accent), 1.2))
        p.drawLine(int(cx - r - 3), int(cy), int(cx - r + 2), int(cy))
        p.drawLine(int(cx + r - 2), int(cy), int(cx + r + 3), int(cy))
        p.drawLine(int(cx), int(cy - r - 3), int(cx), int(cy - r + 2))
        p.drawLine(int(cx), int(cy + r - 2), int(cx), int(cy + r + 3))


# ═══════════════════════════════════════════════════════════════════════════════
#  SAVE BUTTON
# ═══════════════════════════════════════════════════════════════════════════════

class _SaveButton(QPushButton):
    """Frosted-glass save button — looks good with any accent color."""
    def __init__(self, text: str = "Save & Apply", parent=None):
        super().__init__(text, parent)
        self._hover   = False
        self._pressed = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background:transparent;border:none;color:transparent;")

    def enterEvent(self, e):  self._hover = True;   self.update(); super().enterEvent(e)
    def leaveEvent(self, e):  self._hover = False;  self.update(); super().leaveEvent(e)
    def mousePressEvent(self, e):
        self._pressed = True;  self.update(); super().mousePressEvent(e)
    def mouseReleaseEvent(self, e):
        self._pressed = False; self.update(); super().mouseReleaseEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        ac = QColor(AppTheme.accent)

        if self._pressed:
            fill = QColor(ac.red(), ac.green(), ac.blue(), 28)
        elif self._hover:
            fill = QColor(ac.red(), ac.green(), ac.blue(), 18)
        else:
            fill = QColor(ac.red(), ac.green(), ac.blue(), 10)
        p.setBrush(QBrush(fill))
        p.setPen(Qt.PenStyle.NoPen)
        r = AppTheme.shape("row_radius")
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)

        border_a = 110 if self._hover else 65
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(ac.red(), ac.green(), ac.blue(), border_a), 1.0))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), r, r)

        text_a = 240 if self._hover else 180
        p.setPen(QColor(255, 255, 255, text_a))
        f = QFont("Segoe UI", 12, QFont.Weight.Medium)
        p.setFont(f)
        p.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, self.text())


# ═══════════════════════════════════════════════════════════════════════════════
#  CITY SEARCH — workers
# ═══════════════════════════════════════════════════════════════════════════════

class _SearchWorker(QThread):
    results_ready = pyqtSignal(list)

    def __init__(self, query: str):
        super().__init__()
        self.setObjectName("SearchWorker")
        self._query = query

    def run(self):
        try:
            r = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": self._query, "format": "json", "limit": 8,
                        "addressdetails": 1, "featuretype": "settlement"},
                headers={"User-Agent": "WaqtPrayerApp/2.0 (waqt-prayer-desktop)",
                         "Accept-Language": "en"},
                timeout=6,
            )
            r.raise_for_status()
            results = []
            seen = set()
            for item in r.json():
                addr         = item.get("address", {})
                city         = (addr.get("city") or addr.get("town") or
                                addr.get("village") or addr.get("hamlet") or
                                addr.get("municipality") or addr.get("county") or
                                item.get("name", ""))
                country      = addr.get("country", "")
                country_code = addr.get("country_code", "").upper()
                state        = addr.get("state") or addr.get("state_district") or ""
                lat          = float(item.get("lat", 0))
                lon          = float(item.get("lon", 0))
                key          = f"{city.lower()}|{country.lower()}"
                if city and country and key not in seen:
                    seen.add(key)
                    results.append({
                        "city": city, "state": state, "country": country,
                        "country_code": country_code, "lat": lat, "lon": lon,
                        "display": (f"{city}, {state}, {country}"
                                    if state else f"{city}, {country}"),
                    })
            self.results_ready.emit(results)
        except Exception:
            self.results_ready.emit([])


class _LocationDetectWorker(QThread):
    done   = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("LocationDetectWorker")

    def run(self):
        try:
            from core.location import get_location_by_ip
            loc = get_location_by_ip()
            if loc.get("city"):
                self.done.emit(loc)
            else:
                self.failed.emit("Could not determine location")
        except Exception as e:
            self.failed.emit(str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  CITY SEARCH WIDGET
# ═══════════════════════════════════════════════════════════════════════════════

class CitySearchWidget(QWidget):
    """
    Smart city search — works for the entire world.
    Features real-time Nominatim autocomplete + IP auto-detect.
    """
    city_selected = pyqtSignal(dict)
    _DEBOUNCE_MS  = 450

    def __init__(self, settings: dict, lang: str, parent=None):
        super().__init__(parent)
        self._s       = settings
        self._lang    = lang
        self._results: list[dict] = []
        self._worker:  _SearchWorker | None = None
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._do_search)
        self.setStyleSheet("background:transparent;")
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        search_wrap = QWidget()
        search_wrap.setStyleSheet(
            "background:rgba(255,255,255,0.05);"
            "border:1px solid rgba(255,255,255,0.10);"
            "border-radius:10px;")
        sw = QHBoxLayout(search_wrap)
        sw.setContentsMargins(12, 0, 8, 0)
        sw.setSpacing(6)

        ic = QLabel("🔍")
        ic.setStyleSheet("background:transparent;border:none;font-size:13px;")
        ic.setFixedWidth(20)
        sw.addWidget(ic)

        self._search_edit = QLineEdit()
        self._search_edit.setFixedHeight(42)
        self._search_edit.setFrame(False)
        self._search_edit.setFont(AppTheme.font(13))
        self._search_edit.setPlaceholderText(self._placeholder())
        self._search_edit.setStyleSheet(
            "QLineEdit {"
            "background:transparent;border:none;"
            "color:#e8f5ee;"
            "font-family:'Segoe UI',Arial,sans-serif;font-size:13px;}")
        self._search_edit.textChanged.connect(self._on_text_changed)
        self._search_edit.returnPressed.connect(self._do_search)
        sw.addWidget(self._search_edit, 1)

        self._clear_btn = QPushButton("✕")
        self._clear_btn.setFixedSize(28, 28)
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.setStyleSheet(
            "QPushButton {background:transparent;color:rgba(212,232,216,0.30);"
            "border:none;font-size:13px;border-radius:6px;}"
            "QPushButton:hover {color:rgba(212,232,216,0.80);"
            "background:rgba(255,255,255,0.08);}")
        self._clear_btn.clicked.connect(self._clear)
        self._clear_btn.hide()
        sw.addWidget(self._clear_btn)
        v.addWidget(search_wrap)

        self._status_lbl = QLabel()
        self._status_lbl.setStyleSheet("color:rgba(212,232,216,0.45);font-size:11px;")
        self._status_lbl.hide()
        v.addWidget(self._status_lbl)

        self._dropdown = QFrame()
        self._dropdown.setStyleSheet(
            "QFrame {"
            "background:rgba(8,18,12,0.98);"
            f"border:1px solid {AppTheme.accent_rgba(0.35)};"
            "border-radius:10px;}")
        self._drop_v = QVBoxLayout(self._dropdown)
        self._drop_v.setContentsMargins(5, 5, 5, 5)
        self._drop_v.setSpacing(2)
        self._dropdown.hide()
        v.addWidget(self._dropdown)

        self._cur_pill = QWidget()
        self._cur_pill.setStyleSheet(
            f"background:{AppTheme.accent_rgba(0.08)};"
            f"border:1px solid {AppTheme.accent_rgba(0.20)};"
            "border-radius:8px;")
        cp = QHBoxLayout(self._cur_pill)
        cp.setContentsMargins(10, 6, 10, 6)
        cp.setSpacing(6)
        pin = QLabel("📍")
        pin.setStyleSheet("background:transparent;border:none;font-size:12px;")
        cp.addWidget(pin)
        self._cur_lbl = QLabel(self._current_text())
        self._cur_lbl.setStyleSheet(
            f"color:{AppTheme.accent};font-size:11px;"
            "background:transparent;border:none;")
        cp.addWidget(self._cur_lbl, 1)
        v.addWidget(self._cur_pill)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        self._auto_btn = _AutoDetectBtn(_t(self._lang, "auto_detect"))
        self._auto_btn.setFixedHeight(36)
        self._auto_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_btn(self._auto_btn)
        self._auto_btn.clicked.connect(self._do_auto_detect)
        btn_row.addWidget(self._auto_btn, 1)
        v.addLayout(btn_row)

    def _placeholder(self) -> str:
        return {"ru": "Поиск города или страны…",
                "kg": "Шаар же өлкө издөө…"}.get(self._lang, "Search city or country…")

    def _current_text(self) -> str:
        city    = self._s.get("city", "")
        country = self._s.get("country", "")
        return f"{city}, {country}" if city and country else city or "—"

    def _style_btn(self, btn: QPushButton, secondary: bool = False):
        ac = AppTheme.accent
        if secondary:
            btn.setStyleSheet(
                "QPushButton {"
                "background:rgba(255,255,255,0.04);"
                f"color:{ac};"
                f"border:1px solid {AppTheme.accent_rgba(0.30)};"
                "border-radius:8px;font-size:11px;font-weight:600;}"
                "QPushButton:hover {"
                f"background:{AppTheme.accent_rgba(0.12)};"
                f"border-color:{AppTheme.accent_rgba(0.55)};}}")
        else:
            btn.setStyleSheet(
                "QPushButton {"
                f"background:{AppTheme.accent_rgba(0.09)};color:{ac};"
                f"border:1px solid {AppTheme.accent_rgba(0.25)};"
                "border-radius:8px;font-size:11px;font-weight:500;"
                "padding-left:32px;text-align:left;}"
                "QPushButton:hover {"
                f"background:{AppTheme.accent_rgba(0.16)};"
                f"border-color:{AppTheme.accent_rgba(0.50)};}}")

    def _on_text_changed(self, text: str):
        self._clear_btn.setVisible(bool(text))
        q = text.strip()
        if len(q) < 2:
            self._dropdown.hide()
            self._status_lbl.hide()
            return
        self._status_lbl.setText("Searching…")
        self._status_lbl.show()
        self._debounce.start(self._DEBOUNCE_MS)

    def _do_search(self):
        q = self._search_edit.text().strip()
        if len(q) < 2:
            return
        if self._worker and self._worker.isRunning():
            self._worker.quit()
        self._worker = _SearchWorker(q)
        self._worker.results_ready.connect(self._on_results)
        self._worker.start()

    def _on_results(self, results: list):
        self._results = results
        while self._drop_v.count():
            item = self._drop_v.takeAt(0)
            if w := item.widget(): w.deleteLater()

        if not results:
            self._status_lbl.setText("No cities found — try different spelling")
            self._status_lbl.show()
            self._dropdown.hide()
            return

        self._status_lbl.hide()
        for r in results:
            self._drop_v.addWidget(self._make_row(r))
        self._dropdown.show()
        self._dropdown.adjustSize()

    def _make_row(self, r: dict) -> QWidget:
        w = QWidget()
        w.setFixedHeight(48)
        w.setCursor(Qt.CursorShape.PointingHandCursor)
        w.setStyleSheet(
            "QWidget {background:transparent;border-radius:7px;}"
            f"QWidget:hover {{background:{AppTheme.accent_rgba(0.10)};}}")
        h = QHBoxLayout(w)
        h.setContentsMargins(10, 0, 12, 0)
        h.setSpacing(10)

        pin = QLabel("📍")
        pin.setFixedWidth(18)
        pin.setStyleSheet("background:transparent;border:none;font-size:12px;")
        h.addWidget(pin)

        tc = QVBoxLayout(); tc.setSpacing(1)
        city_l = QLabel(r["city"])
        city_l.setFont(AppTheme.font(12, QFont.Weight.Medium))
        city_l.setStyleSheet("color:#e8f5ee;background:transparent;border:none;")

        parts = [p for p in [r.get("state",""), r.get("country","")] if p]
        sub   = ", ".join(parts)
        sub_l = QLabel(sub)
        sub_l.setStyleSheet(
            "color:rgba(212,232,216,0.40);font-size:10px;"
            "background:transparent;border:none;")
        tc.addWidget(city_l); tc.addWidget(sub_l)
        h.addLayout(tc, 1)

        lat_s = f"{r['lat']:.3f}"
        lon_s = f"{r['lon']:.3f}"
        coord = QLabel(lat_s + "\n" + lon_s)
        coord.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        coord.setStyleSheet(
            f"color:{AppTheme.accent};font-size:9px;opacity:0.5;"
            "background:transparent;border:none;")
        h.addWidget(coord)

        w.mousePressEvent = lambda e, res=r: self._select(res)
        return w

    def _select(self, r: dict):
        display = r.get("display") or f"{r['city']}, {r.get('country','')}"
        self._search_edit.setText(display)
        self._search_edit.setCursorPosition(0)
        self._dropdown.hide()
        self._status_lbl.hide()
        self._cur_lbl.setText(f"{r['city']}, {r.get('country','')}")
        self.city_selected.emit(r)

    def _clear(self):
        self._search_edit.clear()
        self._dropdown.hide()
        self._status_lbl.hide()
        self._clear_btn.hide()

    def _do_auto_detect(self):
        self._auto_btn.setEnabled(False)
        self._dots = 0
        if not hasattr(self, "_dot_t"):
            self._dot_t = QTimer(self)
            self._dot_t.timeout.connect(self._anim)
        self._dot_t.start(400)
        self._anim()

        self._aw = _LocationDetectWorker()
        self._aw.done.connect(self._auto_done)
        self._aw.failed.connect(self._auto_fail)
        self._aw.finished.connect(self._aw.deleteLater)
        self._aw.start()

    def _anim(self):
        dots = "·" * (self._dots % 4)
        self._auto_btn.setText(f"  Detecting{dots}")
        self._dots += 1

    def _auto_done(self, loc: dict):
        self._dot_t.stop()
        self._auto_btn.setText(_t(self._lang, "auto_detect"))
        self._auto_btn.setEnabled(True)
        loc["display"] = f"{loc['city']}, {loc.get('country','')}"
        self._select(loc)

    def _auto_fail(self, msg: str):
        self._dot_t.stop()
        self._auto_btn.setText(_t(self._lang, "auto_detect"))
        self._auto_btn.setEnabled(True)
        self._status_lbl.setText(
            "⚠ IP detection failed — enter city name manually")
        self._status_lbl.show()

    def retranslate(self, lang: str):
        self._lang = lang
        self._auto_btn.setText(_t(lang, "auto_detect"))
        self._search_edit.setPlaceholderText(self._placeholder())
        self._cur_lbl.setText(self._current_text())

    def _update_current_lbl(self, loc: dict | None = None):
        if loc:
            self._cur_lbl.setText(f"{loc.get('city','')}, {loc.get('country','')}")
        else:
            self._cur_lbl.setText(self._current_text())