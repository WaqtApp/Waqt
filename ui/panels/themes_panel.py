"""
themes_panel.py — ThemesPanel for Waqt v6.

Extracted from main_window.py (Step 6d of refactor).
"""

from __future__ import annotations

import os
import sys

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel,
    QScrollArea, QVBoxLayout, QWidget,
)

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)

from themes import ThemeCard, THEMES
from ui.app_theme import AppTheme
from ui.widgets import _SaveButton


class ThemesPanel(QWidget):
    """Inline themes panel — same nav as Settings/Overlay/Alerts/Calendar."""

    theme_changed = pyqtSignal(dict)
    _COLS = 2

    def __init__(self, current_theme: str = "Dark Green", parent=None):
        super().__init__(parent)
        self._current = current_theme
        self._cards: dict[str, ThemeCard] = {}
        self.setFixedWidth(290)
        self.setStyleSheet(f"background:{AppTheme.surface};"
                           "border-right:0.5px solid rgba(255,255,255,0.04);")
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        from PyQt6.QtCore import Qt
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")

        content = QWidget(); content.setStyleSheet("background:transparent;")
        v = QVBoxLayout(content)
        v.setContentsMargins(14, 18, 14, 16)
        v.setSpacing(12)

        hdr = QLabel("THEMES")
        hdr.setFont(AppTheme.font(10, QFont.Weight.Bold))
        hdr.setStyleSheet("color:rgba(212,232,216,0.35);letter-spacing:.14em;")
        v.addWidget(hdr)

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0)

        for i, (name, colors) in enumerate(THEMES.items()):
            card = ThemeCard(name, colors, is_active=(name == self._current))
            card.setFixedSize(118, 90)
            card.selected.connect(self._select)
            self._cards[name] = card
            grid.addWidget(card, i // self._COLS, i % self._COLS)

        v.addLayout(grid)
        v.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        # Footer: Apply button
        footer = QWidget()
        footer.setStyleSheet(
            f"background:{AppTheme.surface};"
            "border-top:0.5px solid rgba(255,255,255,0.06);")
        fr = QHBoxLayout(footer)
        fr.setContentsMargins(14, 12, 14, 14)
        self._apply_btn = _SaveButton("Apply Theme")
        self._apply_btn.setFixedHeight(40)
        self._apply_btn.clicked.connect(self._apply)
        fr.addWidget(self._apply_btn)
        outer.addWidget(footer)

    def _select(self, name: str):
        if name == self._current:
            return
        if self._current in self._cards:
            self._cards[self._current].set_active(False)
        self._current = name
        self._cards[name].set_active(True)

    def _apply(self):
        self.theme_changed.emit(THEMES[self._current])

    def set_current(self, name: str):
        if self._current in self._cards:
            self._cards[self._current].set_active(False)
        self._current = name
        if name in self._cards:
            self._cards[name].set_active(True)