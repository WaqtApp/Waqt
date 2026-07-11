"""
themes.py — color themes for Waqt v6.

Changes vs v5:
  - ThemeCard uses paintEvent only (no mixed StyleSheet + paint hack)
  - Active indicator is a cleaner checkmark
  - ThemesDialog: 4 per row for 8 themes (unchanged layout, cleaner code)
  - THEMES dict unchanged — same 8 themes
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QPushButton, QLabel, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen

# ── Theme palette definitions ─────────────────────────────────────────────────

THEMES: dict[str, dict] = {
    "Knowledge": {
        "bg": "#1a1f3a", "surface": "#252b4a",
        "accent": "#e8b84b", "text": "#f0ead6", "border": "#333860",
    },
    "Sunny Town": {
        "bg": "#1a1210", "surface": "#2a1e1a",
        "accent": "#e8693a", "text": "#faf0e8", "border": "#3d2820",
    },
    "Arctic Dawn": {
        "bg": "#0d1b2e", "surface": "#142338",
        "accent": "#5bc8e8", "text": "#ddf0f8", "border": "#1a3050",
    },
    "Iceland": {
        "bg": "#111820", "surface": "#192230",
        "accent": "#38d9a9", "text": "#e0f5ef", "border": "#1e3040",
    },
    "Sunset": {
        "bg": "#1a0f1e", "surface": "#26162e",
        "accent": "#c868e8", "text": "#f0ddf8", "border": "#3a1e4a",
    },
    "Amber & Azure": {
        "bg": "#0f1a1a", "surface": "#162828",
        "accent": "#e8a030", "text": "#faf5e8", "border": "#1e3838",
    },
    "Dark Green": {
        "bg": "#1a1a2e", "surface": "#16213e",
        "accent": "#1D9E75", "text": "#e0e0e0", "border": "#2a2a4a",
    },
    "Midnight": {
        "bg": "#0d1b2a", "surface": "#1b2838",
        "accent": "#4a9eff", "text": "#dce8f5", "border": "#1e3a5f",
    },
}


# ── Theme card widget ──────────────────────────────────────────────────────────

class ThemeCard(QFrame):
    selected = pyqtSignal(str)

    def __init__(self, name: str, colors: dict, is_active: bool = False):
        super().__init__()
        self._name   = name
        self._colors = colors
        self._active = is_active
        self.setFixedSize(142, 98)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_border()

    def _refresh_border(self):
        border = (f"2px solid {self._colors['accent']}" if self._active
                  else f"1px solid {self._colors['border']}")
        self.setStyleSheet(f"""
            QFrame {{
                background: {self._colors['bg']};
                border: {border};
                border-radius: 10px;
            }}
        """)

    def set_active(self, active: bool):
        self._active = active
        self._refresh_border()
        self.update()

    def mousePressEvent(self, _):
        self.selected.emit(self._name)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        c = self._colors

        # Surface preview rect
        p.setBrush(QBrush(QColor(c["surface"]))); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(10, 10, w - 20, 44, 6, 6)

        # Mini card inside preview
        p.setBrush(QBrush(QColor(c["bg"])))
        p.drawRoundedRect(14, 14, 42, 30, 4, 4)

        # Accent bar inside mini card
        p.setBrush(QBrush(QColor(c["accent"])))
        p.drawRoundedRect(16, 36, 26, 4, 2, 2)

        # Accent pill (bottom of preview)
        p.drawRoundedRect(10, 60, 58, 8, 4, 4)

        # Text strip (muted)
        p.setBrush(QBrush(QColor(c["text"]))); p.setOpacity(0.28)
        p.drawRoundedRect(74, 60, w - 84, 8, 4, 4)
        p.setOpacity(1.0)

        # Theme name label
        p.setPen(QColor(c["text"]))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(10, h - 7, self._name)

        # Active checkmark circle
        if self._active:
            p.setBrush(QBrush(QColor(c["accent"]))); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(w - 22, 8, 14, 14)
            p.setPen(QPen(QColor("#ffffff"), 1.8))
            p.drawLine(w - 18, 15, w - 15, 18)
            p.drawLine(w - 15, 18, w - 10, 12)


# ── Themes dialog ──────────────────────────────────────────────────────────────

class ThemesDialog(QDialog):
    theme_changed = pyqtSignal(dict)

    def __init__(self, current_theme: str = "Dark Green", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Themes")
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setFixedSize(500, 390)
        self._current = current_theme
        self._cards: dict[str, ThemeCard] = {}

        self.setStyleSheet("""
            QDialog  { background: #1a1a2e; }
            QLabel   { color: #e0e0e0; background: transparent; }
            QPushButton {
                background: #1D9E75; color: #ffffff; border: none;
                border-radius: 7px; padding: 9px 22px; font-size: 13px;
            }
            QPushButton:hover { background: #17b882; }
        """)

        v = QVBoxLayout(self); v.setContentsMargins(22, 22, 22, 22); v.setSpacing(14)

        title = QLabel("Choose theme")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Medium))
        v.addWidget(title)

        grid = QGridLayout(); grid.setSpacing(10)
        for i, (name, colors) in enumerate(THEMES.items()):
            card = ThemeCard(name, colors, is_active=(name == self._current))
            card.selected.connect(self._select)
            self._cards[name] = card
            grid.addWidget(card, i // 4, i % 4)

        v.addLayout(grid)
        v.addStretch()

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply)
        v.addWidget(apply_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _select(self, name: str):
        if self._current in self._cards:
            self._cards[self._current].set_active(False)
        self._current = name
        self._cards[name].set_active(True)

    def _apply(self):
        self.theme_changed.emit(THEMES[self._current])
        self.accept()