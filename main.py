"""
main.py — Waqt v6 entry point.

Changes vs v5:
  - Splash screen: slightly larger (340×230), smoother crescent
  - Single-instance check: same socket approach (reliable, cross-platform)
  - App closes cleanly via on_quit (no sys.exit race)
"""

import sys
import os
import socket

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import (
    QPixmap, QPainter, QColor, QBrush, QPen,
    QPainterPath, QFont, QRadialGradient,
)
from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer

# ── Single-instance lock ───────────────────────────────────────────────────────
_LOCK_PORT = 47832


def _is_already_running() -> bool:
    """Returns True if another Waqt instance owns the lock port."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", _LOCK_PORT))
        s.listen(1)
        _is_already_running._lock = s   # keep reference so socket stays open
        return False
    except OSError:
        return True


# ── Splash pixmap ──────────────────────────────────────────────────────────────

def _make_splash(w: int = 340, h: int = 230) -> QPixmap:
    px = QPixmap(w, h); px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px); p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Card background
    p.setBrush(QBrush(QColor("#0f1e2e")))
    p.setPen(QPen(QColor("#1D9E75"), 1.5))
    p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 16, 16)

    # Stars
    p.setPen(Qt.PenStyle.NoPen)
    for sx, sy, sr in [(0.12, 0.14, 2.8), (0.82, 0.11, 2.4),
                       (0.90, 0.34, 1.9), (0.08, 0.46, 1.8), (0.85, 0.64, 2.4)]:
        p.setBrush(QBrush(QColor(255, 255, 255, 130)))
        p.drawEllipse(QPointF(w * sx, h * sy), sr, sr)

    # Crescent moon
    cx, cy, rm = w * 0.5, h * 0.37, min(w, h) * 0.22
    outer = QPainterPath(); outer.addEllipse(QPointF(cx, cy), rm, rm)
    inner = QPainterPath(); inner.addEllipse(QPointF(cx + rm * 0.46, cy - rm * 0.08), rm * 0.78, rm * 0.78)
    p.setBrush(QBrush(QColor("#1D9E75")))
    p.drawPath(outer.subtracted(inner))

    # App name
    p.setPen(QColor("#ffffff"))
    p.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    p.drawText(QRectF(0, h * 0.64, w, 38), Qt.AlignmentFlag.AlignHCenter, "Waqt")

    # Subtitle
    p.setPen(QColor("#6688aa"))
    p.setFont(QFont("Segoe UI", 10))
    p.drawText(QRectF(0, h * 0.81, w, 24), Qt.AlignmentFlag.AlignHCenter,
               "Loading prayer times…")

    p.end()
    return px


# ── Application subclass ───────────────────────────────────────────────────────

class App(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setQuitOnLastWindowClosed(False)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if _is_already_running():
        # Signal existing instance to come to front
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", _LOCK_PORT))
            s.send(b"show"); s.close()
        except Exception:
            pass
        sys.exit(0)

    app = App(sys.argv)

    # Splash
    splash = QSplashScreen(_make_splash(), Qt.WindowType.WindowStaysOnTopHint)
    splash.setWindowFlag(Qt.WindowType.FramelessWindowHint)
    splash.show()
    app.processEvents()

    # Import main window (heavy — PyQt6 widgets, API client, etc.)
    from ui.main_window import MainWindow
    window = MainWindow()

    def on_close(event):
        event.ignore()
        window.hide()

    def on_quit():
        # Stop background threads before exit to prevent QThread: Destroyed
        try:
            if hasattr(window, "_loc_monitor"):
                window._loc_monitor.stop()
                window._loc_monitor.wait(800)
            if hasattr(window, "_worker") and window._worker:
                window._worker.quit()
                window._worker.wait(400)
        except Exception:
            pass
        window._tray.hide()
        splash.close()
        app.quit()
        sys.exit(0)

    window.closeEvent = on_close
    try:
        window._tray.quit_action.triggered.disconnect()
    except Exception:
        pass
    window._tray.quit_action.triggered.connect(on_quit)

    def _finish():
        splash.finish(window)
        window.show()

    QTimer.singleShot(1200, _finish)
    sys.exit(app.exec())