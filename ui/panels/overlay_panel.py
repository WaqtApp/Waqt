"""
overlay_panel.py — OverlayPanel for Waqt v6.

Extracted from main_window.py (Step 6b of refactor).
"""

from __future__ import annotations

import os
import sys

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)

from ui.app_theme import AppTheme, _divider
from ui.widgets import ToggleSwitch


class OverlayPanel(QWidget):
    """Controls for the floating overlay widget."""

    style_changed  = pyqtSignal(str)
    toggle_changed = pyqtSignal(bool)

    _STYLES = [
        ("pill",    "Pill",    "Compact horizontal strip"),
        ("card",    "Card",    "Two-line card with accent bar"),
        ("minimal", "Minimal", "Plain text, no background"),
    ]

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._s = settings
        self.setFixedWidth(290)
        self.setStyleSheet(f"background:{AppTheme.surface};"
                           "border-right:0.5px solid rgba(255,255,255,0.04);")
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")

        content = QWidget(); content.setStyleSheet("background:transparent;")
        v = QVBoxLayout(content)
        v.setContentsMargins(16, 18, 16, 16)
        v.setSpacing(14)

        # Header
        hdr = QLabel("OVERLAY")
        hdr.setFont(AppTheme.font(10, QFont.Weight.Bold))
        hdr.setStyleSheet("color:rgba(212,232,216,0.35);letter-spacing:.14em;")
        v.addWidget(hdr)

        # Show / hide toggle
        sh_row = QHBoxLayout()
        sh_lbl = QLabel("Show overlay")
        sh_lbl.setStyleSheet("color:rgba(212,232,216,0.70);font-size:13px;")
        self._show_ts = ToggleSwitch(checked=self._s.get("show_overlay", True))
        self._show_ts.toggled.connect(self.toggle_changed.emit)
        sh_row.addWidget(sh_lbl); sh_row.addStretch(); sh_row.addWidget(self._show_ts)
        v.addLayout(sh_row)

        v.addWidget(_divider())

        # Style picker
        style_hdr = QLabel("STYLE")
        style_hdr.setFont(AppTheme.font(9, QFont.Weight.Bold))
        style_hdr.setStyleSheet("color:rgba(212,232,216,0.28);letter-spacing:.12em;")
        v.addWidget(style_hdr)

        cur = self._s.get("overlay_style", "pill")
        self._style_btns: dict[str, QWidget] = {}
        for key, name, desc in self._STYLES:
            card = self._make_style_card(key, name, desc, active=(key == cur))
            self._style_btns[key] = card
            v.addWidget(card)

        v.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

    def _make_style_card(self, key: str, name: str, desc: str, active: bool) -> QWidget:
        card = QWidget()
        card.setFixedHeight(58)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        ac = AppTheme.accent
        if active:
            card.setStyleSheet(
                "background:rgba(29,158,117,0.10);"
                "border:1px solid rgba(29,158,117,0.40);"
                "border-radius:9px;")
        else:
            card.setStyleSheet(
                "background:rgba(255,255,255,0.03);"
                "border:1px solid rgba(255,255,255,0.06);"
                "border-radius:9px;")

        h = QHBoxLayout(card); h.setContentsMargins(14, 0, 14, 0); h.setSpacing(12)

        dot = QWidget(); dot.setFixedSize(14, 14)
        dot.setStyleSheet(
            f"background:{ac};border-radius:7px;" if active else
            "background:transparent;border:1.5px solid rgba(255,255,255,0.20);border-radius:7px;")
        h.addWidget(dot)

        text_col = QVBoxLayout(); text_col.setSpacing(2)
        fw = "600" if active else "400"
        n_lbl = QLabel(name)
        n_lbl.setStyleSheet(
            f"color:#f0f8f4;font-size:13px;font-weight:{fw};" if active else
            "color:rgba(212,232,216,0.55);font-size:13px;")
        d_lbl = QLabel(desc)
        d_lbl.setStyleSheet("color:rgba(212,232,216,0.28);font-size:10px;")
        text_col.addWidget(n_lbl); text_col.addWidget(d_lbl)
        h.addLayout(text_col, 1)

        card._key = key
        card.mousePressEvent = lambda e, k=key: self._select_style(k)
        return card

    def _select_style(self, key: str):
        cur = self._s.get("overlay_style", "pill")
        if key == cur:
            return
        self._s["overlay_style"] = key
        ac = AppTheme.accent
        for k, card in self._style_btns.items():
            active = (k == key)
            if active:
                card.setStyleSheet(
                    "background:rgba(29,158,117,0.10);"
                    "border:1px solid rgba(29,158,117,0.40);"
                    "border-radius:9px;")
            else:
                card.setStyleSheet(
                    "background:rgba(255,255,255,0.03);"
                    "border:1px solid rgba(255,255,255,0.06);"
                    "border-radius:9px;")
            h = card.layout()
            if h and h.count() >= 1:
                dot = h.itemAt(0).widget()
                if dot:
                    dot.setStyleSheet(
                        f"background:{ac};border-radius:7px;" if active else
                        "background:transparent;border:1.5px solid rgba(255,255,255,0.20);border-radius:7px;")
        self.style_changed.emit(key)

    def sync_toggle(self, enabled: bool):
        self._show_ts.blockSignals(True)
        self._show_ts.setChecked(enabled)
        self._show_ts.blockSignals(False)