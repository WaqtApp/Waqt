"""
overlay.py — floating overlay widget for Waqt v6.

Changes vs v5:
  - No `global ACCENT` mutation — color read from AppTheme at paint time
  - Style rebuild is cleaner (no dangling QWidget().setLayout() hack)
  - CrescentWidget unchanged (correct)
  - StyleCard / OverlayStyleDialog: minor polish
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QApplication, QDialog, QGridLayout, QPushButton, QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QPoint, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QBrush, QPen, QCursor, QPainterPath,
)

# ── Theme pulled lazily so overlay always reflects the live AppTheme ─────────
# (module-level fallback keeps this file loadable/testable outside the app)
class _FallbackTheme:
    accent  = "#1D9E75"
    bg      = "#1a1a2e"
    surface = "#16213e"
    text    = "#e0e0e0"
    border  = "#2a2a4a"


def _theme():
    try:
        from ui.app_theme import AppTheme
        return AppTheme
    except Exception:
        return _FallbackTheme


def _accent() -> str:
    return _theme().accent


def _rgba(hex_: str, alpha: float) -> str:
    """CSS 'rgba(r,g,b,a)' string for any theme color — same idea as
    AppTheme.accent_rgba() but works for bg/surface/border too."""
    c = QColor(hex_)
    return f"rgba({c.red()},{c.green()},{c.blue()},{alpha})"


# ── Crescent moon widget ───────────────────────────────────────────────────────

class CrescentWidget(QWidget):
    def __init__(self, size: int = 14, color: str | None = None, parent=None):
        super().__init__(parent)
        self._size  = size
        self._color = color
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = self._color or _accent()
        p.setBrush(QBrush(QColor(color)))
        p.setPen(Qt.PenStyle.NoPen)
        sz = self._size
        outer = QPainterPath()
        outer.addEllipse(QPointF(sz / 2, sz / 2), sz / 2 - 1, sz / 2 - 1)
        inner = QPainterPath()
        inner.addEllipse(
            QPointF(sz / 2 + sz * 0.19, sz / 2 - sz * 0.04),
            sz * 0.36, sz * 0.36,
        )
        p.drawPath(outer.subtracted(inner))


# ── Style metadata ─────────────────────────────────────────────────────────────

OVERLAY_STYLES: dict[str, dict] = {
    "pill": {
        "name": "Pill",
        "desc": "Compact horizontal pill",
        "w": 220, "h": 36,
    },
    "card": {
        "name": "Card",
        "desc": "Two-line card with accent bar",
        "w": 210, "h": 62,
    },
    "minimal": {
        "name": "Minimal",
        "desc": "Just text, no background",
        "w": 190, "h": 40,
    },
}


# ── Style picker dialog ────────────────────────────────────────────────────────

class StyleCard(QFrame):
    selected = pyqtSignal(str)

    def __init__(self, key: str, info: dict, is_active: bool):
        super().__init__()
        self._key    = key
        self._active = is_active
        self.setFixedSize(154, 72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_style()

        v = QVBoxLayout(self); v.setContentsMargins(12, 9, 12, 9); v.setSpacing(3)

        t = _theme()
        self._name_lbl = QLabel(info["name"])
        self._name_lbl.setStyleSheet(
            f"color:{t.accent if is_active else t.text};"
            f"font-size:12px;font-weight:{'600' if is_active else '400'};"
            "background:transparent;")
        desc_lbl = QLabel(info["desc"])
        desc_lbl.setStyleSheet(f"color:{_rgba(t.text, 0.45)};font-size:10px;background:transparent;")
        desc_lbl.setWordWrap(True)

        v.addWidget(self._name_lbl)
        v.addWidget(desc_lbl)
        v.addStretch()

    def _refresh_style(self):
        t = _theme()
        border = f"1.5px solid {t.accent}" if self._active else f"1px solid {t.border}"
        bg = _rgba(t.accent, 0.10) if self._active else t.surface
        self.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border: {border};
                border-radius: 9px;
            }}
        """)

    def set_active(self, active: bool):
        self._active = active
        self._refresh_style()
        t = _theme()
        self._name_lbl.setStyleSheet(
            f"color:{t.accent if active else t.text};"
            f"font-size:12px;font-weight:{'600' if active else '400'};"
            "background:transparent;")

    def mousePressEvent(self, _):
        self.selected.emit(self._key)


class OverlayStyleDialog(QDialog):
    style_chosen = pyqtSignal(str)

    def __init__(self, current_style: str = "card", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Overlay style")
        self.setModal(True)
        self.setFixedSize(400, 210)
        self._current = current_style
        self._cards: dict[str, StyleCard] = {}

        t = _theme()
        self.setStyleSheet(f"""
            QDialog  {{ background: {t.bg}; }}
            QLabel   {{ color: {t.text}; background: transparent; }}
            QPushButton {{
                background: {t.accent}; color: #fff; border: none;
                border-radius: 7px; padding: 7px 22px; font-size: 13px;
            }}
            QPushButton:hover {{ background: {_rgba(t.accent, 0.85)}; }}
        """)

        v = QVBoxLayout(self); v.setContentsMargins(20, 18, 20, 18); v.setSpacing(14)

        title = QLabel("Choose overlay style")
        title.setStyleSheet(f"font-size:13px;font-weight:600;color:{t.text};")
        v.addWidget(title)

        grid = QGridLayout(); grid.setSpacing(10)
        for i, (key, info) in enumerate(OVERLAY_STYLES.items()):
            card = StyleCard(key, info, is_active=(key == current_style))
            card.selected.connect(self._select)
            self._cards[key] = card
            grid.addWidget(card, 0, i)
        v.addLayout(grid)
        v.addStretch()

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply)
        v.addWidget(apply_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _select(self, key: str):
        if self._current in self._cards:
            self._cards[self._current].set_active(False)
        self._current = key
        self._cards[key].set_active(True)

    def _apply(self):
        self.style_chosen.emit(self._current)
        self.accept()


# ── Overlay widget ─────────────────────────────────────────────────────────────

class OverlayWidget(QWidget):
    """Draggable floating widget showing next prayer + countdown."""

    def __init__(self, style: str = "card"):
        super().__init__()
        self._style     = style
        self._name      = "—"
        self._time_str  = "--:--"
        self._countdown = "--:--:--"
        self._drag_pos  = QPoint()
        self._dragging  = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))

        self._build()
        self._snap_default()

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self):
        """
        Safe rebuild: we keep a permanent QHBoxLayout on self that holds
        one child container (_inner). Rebuilding just replaces _inner —
        no layout is ever set twice on self.
        """
        ac = _accent()
        s  = self._style

        # ── Create the new inner container ────────────────────────────────────
        new_inner = QWidget()
        new_inner.setStyleSheet("background:transparent;")

        if s == "pill":
            self.setFixedHeight(36)
            layout = QHBoxLayout(new_inner)
            layout.setContentsMargins(12, 0, 10, 0)
            layout.setSpacing(6)

            layout.addWidget(CrescentWidget(12, ac))

            self._name_lbl = QLabel(self._name)
            self._name_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
            self._name_lbl.setStyleSheet("color:#ffffff;background:transparent;")
            self._name_lbl.setMinimumWidth(42)
            layout.addWidget(self._name_lbl)

            layout.addWidget(self._sep_dot())

            self._time_lbl = QLabel(self._time_str)
            self._time_lbl.setFont(QFont("Segoe UI", 10))
            self._time_lbl.setStyleSheet("color:rgba(255,255,255,0.55);background:transparent;")
            self._time_lbl.setFixedWidth(38)
            layout.addWidget(self._time_lbl)

            layout.addWidget(self._sep_dot())

            self._countdown_lbl = QLabel(self._countdown)
            self._countdown_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
            self._countdown_lbl.setStyleSheet(f"color:{ac};background:transparent;")
            self._countdown_lbl.setFixedWidth(76)
            layout.addWidget(self._countdown_lbl)

            self._add_close(layout)

        elif s == "card":
            self.setFixedHeight(62)
            root = QVBoxLayout(new_inner)
            root.setContentsMargins(14, 8, 10, 8)
            root.setSpacing(4)

            row1 = QHBoxLayout(); row1.setSpacing(7)
            row1.addWidget(CrescentWidget(14, ac))

            self._name_lbl = QLabel(self._name)
            self._name_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            self._name_lbl.setStyleSheet("color:#ffffff;background:transparent;")
            row1.addWidget(self._name_lbl)
            row1.addStretch()

            self._time_lbl = QLabel(self._time_str)
            self._time_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
            self._time_lbl.setStyleSheet(f"color:{ac};background:transparent;")
            row1.addWidget(self._time_lbl)

            self._add_close(row1)

            row2 = QHBoxLayout(); row2.setSpacing(5)
            next_lbl = QLabel("next")
            next_lbl.setStyleSheet("color:rgba(255,255,255,0.30);font-size:9px;background:transparent;")
            row2.addWidget(next_lbl)

            self._countdown_lbl = QLabel(self._countdown)
            self._countdown_lbl.setFont(QFont("Segoe UI", 9))
            self._countdown_lbl.setStyleSheet("color:rgba(255,255,255,0.65);background:transparent;")
            row2.addWidget(self._countdown_lbl)
            row2.addStretch()

            root.addLayout(row1)
            root.addLayout(row2)

        else:  # minimal
            self.setFixedHeight(40)
            layout = QHBoxLayout(new_inner)
            layout.setContentsMargins(10, 0, 10, 0)
            layout.setSpacing(6)

            self._name_lbl = QLabel(self._name)
            self._name_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            self._name_lbl.setStyleSheet(f"color:{ac};background:transparent;")
            layout.addWidget(self._name_lbl)

            self._time_lbl = QLabel(self._time_str)
            self._time_lbl.setFont(QFont("Segoe UI", 11))
            self._time_lbl.setStyleSheet("color:#ffffff;background:transparent;")
            layout.addWidget(self._time_lbl)

            layout.addWidget(self._sep_dot())

            self._countdown_lbl = QLabel(self._countdown)
            self._countdown_lbl.setFont(QFont("Segoe UI", 10))
            self._countdown_lbl.setStyleSheet("color:rgba(255,255,255,0.60);background:transparent;")
            layout.addWidget(self._countdown_lbl)

            layout.addStretch()
            self._add_close(layout)

        # ── Swap inner container safely ────────────────────────────────────────
        if not self.layout():
            # First call: create the permanent outer layout
            outer = QHBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(0)
        else:
            outer = self.layout()

        # Remove and delete old inner (if any)
        if hasattr(self, "_inner") and self._inner is not None:
            outer.removeWidget(self._inner)
            self._inner.hide()
            self._inner.deleteLater()

        self._inner = new_inner
        outer.addWidget(self._inner)
        self.adjustSize()
        self.update()

    @staticmethod
    def _sep_dot() -> QLabel:
        lbl = QLabel("·")
        lbl.setStyleSheet("color:rgba(255,255,255,0.28);font-size:11px;")
        return lbl

    def _add_close(self, layout):
        close = QLabel("×")
        close.setFixedSize(16, 16)
        close.setAlignment(Qt.AlignmentFlag.AlignCenter)
        close.setStyleSheet("color:rgba(255,255,255,0.30);font-size:14px;")
        close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close.mousePressEvent = lambda e: self.hide()
        layout.addWidget(close)

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_style(self, style: str):
        if style == self._style: return
        self._style = style
        was = self.isVisible()
        self.hide()
        self._build()
        if was:
            self._clamp(); self.show()

    def refresh_theme(self):
        """Re-pull colors from AppTheme after a theme switch.

        _build() bakes the current accent into the label stylesheets once;
        paintEvent() re-reads _theme() every paint, but nothing schedules a
        repaint on its own after AppTheme.apply() runs. Call this from
        MainWindow's theme-change handler so the overlay doesn't stay on
        the old theme's colors until the next unrelated repaint.
        """
        was = self.isVisible()
        self.hide()
        self._build()
        if was:
            self._clamp(); self.show()
        else:
            self.update()

    def update_info(self, name: str, time_str: str, countdown: str):
        self._name      = name
        self._time_str  = time_str
        self._countdown = countdown
        if hasattr(self, "_name_lbl"):     self._name_lbl.setText(name)
        if hasattr(self, "_time_lbl"):     self._time_lbl.setText(time_str)
        if hasattr(self, "_countdown_lbl"): self._countdown_lbl.setText(countdown)
        self.adjustSize(); self._clamp()

    # ── Geometry helpers ───────────────────────────────────────────────────────

    def _available(self):
        return QApplication.primaryScreen().availableGeometry()

    def _snap_default(self):
        avail = self._available()
        self.move(avail.right() - self.width() - 18,
                  avail.bottom() - self.height() - 10)

    def _clamp(self):
        avail = self._available()
        x = max(avail.left(), min(self.x(), avail.right()  - self.width()))
        y = max(avail.top(),  min(self.y(), avail.bottom() - self.height()))
        self.move(x, y)

    # ── Paint ──────────────────────────────────────────────────────────────────

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        ac = _accent()

        if self._style == "pill":
            p.setBrush(QBrush(QColor(10, 12, 26, 218)))
            p.setPen(QPen(QColor(ac), 0.8))
            p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 18, 18)

        elif self._style == "card":
            p.setBrush(QBrush(QColor(10, 12, 26, 224)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(0, 0, w, h), 11, 11)
            # Left accent bar
            p.setBrush(QBrush(QColor(ac)))
            p.drawRoundedRect(QRectF(0, 0, 3, h), 2, 2)
            # Border
            p.setPen(QPen(QColor(ac), 0.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 11, 11)
            # Divider
            p.setPen(QPen(QColor(255, 255, 255, 16), 0.5))
            p.drawLine(12, h // 2 + 2, w - 10, h // 2 + 2)

        elif self._style == "minimal":
            p.setBrush(QBrush(QColor(0, 0, 0, 115)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(0, 0, w, h), 7, 7)

    # ── Drag ───────────────────────────────────────────────────────────────────

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._dragging = True

    def mouseMoveEvent(self, e):
        if self._dragging and e.buttons() == Qt.MouseButton.LeftButton:
            new   = e.globalPosition().toPoint() - self._drag_pos
            avail = self._available()
            x = max(avail.left(), min(new.x(), avail.right()  - self.width()))
            y = max(avail.top(),  min(new.y(), avail.bottom() - self.height()))
            self.move(x, y)

    def mouseReleaseEvent(self, _):
        self._dragging = False

    def contextMenuEvent(self, _):
        self.hide()