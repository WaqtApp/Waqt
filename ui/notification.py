"""
notification.py — prayer time notification widget for Waqt v6.

Changes vs v5:
  - Removed per-pixel tinting loop (was already fixed in v5 with CompositionMode)
  - Notification width increased to 260 px — more readable
  - Subtitle typography improved
  - Stack tracking is module-level (unchanged — correct approach)
"""

import os

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QApplication
from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QPixmap

_root       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOWER_ICON = os.path.join(_root, "assets", "icons", "azan_tower.png")

ACCENT = "#1D9E75"

# Track active notifications for stacking
_active: list = []


def _tint_icon(path: str, size: int = 28) -> QPixmap | None:
    """
    Tint a black-on-white icon to ACCENT using QPainter composition.
    O(1) GPU ops instead of O(w*h) pixel loop.
    """
    if not os.path.exists(path):
        return None
    try:
        src = QPixmap(path).scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        result = QPixmap(src.size())
        result.fill(Qt.GlobalColor.transparent)
        p = QPainter(result)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(result.rect(), QColor(ACCENT))
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        p.drawPixmap(0, 0, src)
        p.end()
        return result
    except Exception:
        return None


class PrayerNotification(QWidget):
    dismissed = pyqtSignal()

    # Dimensions
    _W = 260; _H = 58

    def __init__(self, name: str, time_str: str,
                 subtitle: str = "Time to pray", stack_offset: int = 0):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(self._W, self._H)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 10, 0)
        layout.setSpacing(0)

        # Left accent bar
        bar = QWidget(); bar.setFixedWidth(3)
        bar.setStyleSheet(f"background:{ACCENT};border-radius:2px;")
        layout.addWidget(bar)

        # Icon
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(50, self._H)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background:transparent;")
        px = _tint_icon(_TOWER_ICON, 28)
        if px:
            icon_lbl.setPixmap(px)
        else:
            icon_lbl.setText("🕌")
            icon_lbl.setStyleSheet(f"color:{ACCENT};font-size:20px;background:transparent;")
        layout.addWidget(icon_lbl)

        # Text block
        tw = QWidget(); tw.setStyleSheet("background:transparent;")
        tv = QVBoxLayout(tw)
        tv.setContentsMargins(2, 0, 0, 0)
        tv.setSpacing(3)
        tv.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        name_lbl = QLabel(name)
        name_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        name_lbl.setStyleSheet("color:#ffffff;background:transparent;")
        tv.addWidget(name_lbl)

        sub_lbl = QLabel(f"{time_str}  ·  {subtitle}")
        sub_lbl.setFont(QFont("Segoe UI", 9))
        sub_lbl.setStyleSheet(f"color:{ACCENT};background:transparent;")
        tv.addWidget(sub_lbl)
        layout.addWidget(tw, 1)

        # Close button
        close = QLabel("×")
        close.setFixedSize(22, 22)
        close.setAlignment(Qt.AlignmentFlag.AlignCenter)
        close.setStyleSheet("color:rgba(255,255,255,0.35);font-size:16px;background:transparent;")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.mousePressEvent = lambda e: self._dismiss()
        layout.addWidget(close)

        # Position: bottom-right, stacked upward
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.right() - self._W - 18,
            screen.bottom() - self._H - 18 - stack_offset,
        )

        # Auto-dismiss after 12 s
        QTimer.singleShot(12_000, self._dismiss)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setBrush(QBrush(QColor(4, 14, 8, 245)))
        p.setPen(QPen(QColor(ACCENT), 0.8))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 11, 11)

    def _dismiss(self):
        if self in _active:
            _active.remove(self)
        self.hide()
        self.dismissed.emit()
        self.deleteLater()


# ── Public helpers ─────────────────────────────────────────────────────────────

def show_prayer_notification(name: str, time_str: str,
                              subtitle: str = "Time to pray") -> PrayerNotification:
    """Show a prayer notification, stacked above any existing ones."""
    stack_offset = len(_active) * (PrayerNotification._H + 8)
    n = PrayerNotification(name, time_str, subtitle, stack_offset=stack_offset)
    _active.append(n)
    n.show()
    return n


def show_pre_prayer_notification(name: str, time_str: str,
                                  minutes: int) -> PrayerNotification:
    """Show a 'X minutes until prayer' notification."""
    return show_prayer_notification(name, time_str, f"in {minutes} min")