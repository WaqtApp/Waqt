"""
tray.py — system tray icon + popup for Waqt v6.

Changes vs v5:
  - PrayerPopup: bigger rows (52 px), cleaner typography
  - Tray icon: crisper text at small sizes
  - Delayed hide uses grace period to prevent flicker
  - No global mutation — accent passed as argument
"""

from PyQt6.QtWidgets import (
    QSystemTrayIcon, QMenu, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QApplication,
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QFont, QColor, QBrush, QPen, QPainterPath,
)
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer

# ── Palette (matches AppTheme defaults) ───────────────────────────────────────
ACCENT = "#1D9E75"
BG     = "#06100a"
BORDER = "#0e2016"
TEXT   = "#d4e8d8"
MUTED  = "#4a6a52"

# ── Icon factories ─────────────────────────────────────────────────────────────

def _make_default_icon(accent: str = ACCENT) -> QIcon:
    sz = 64
    px = QPixmap(sz, sz); px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    cx, cy, rm = sz / 2, sz / 2, sz * 0.42
    outer = QPainterPath(); outer.addEllipse(QPointF(cx, cy), rm, rm)
    inner = QPainterPath(); inner.addEllipse(QPointF(cx + rm * 0.46, cy - rm * 0.1), rm * 0.78, rm * 0.78)
    p.setBrush(QBrush(QColor(accent))); p.setPen(Qt.PenStyle.NoPen)
    p.drawPath(outer.subtracted(inner)); p.end()
    return QIcon(px)


def _make_text_icon(name: str, countdown: str, accent: str = ACCENT) -> QIcon:
    """Tray icon showing next prayer name + short countdown."""
    sz = 64
    px = QPixmap(sz, sz); px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    # Background pill
    p.setBrush(QBrush(QColor(10, 15, 30, 255)))
    p.setPen(QPen(QColor(accent), 2))
    p.drawRoundedRect(QRectF(1, 1, sz - 2, sz - 2), 10, 10)

    # Prayer name (top half)
    p.setPen(QColor(accent))
    f1 = QFont("Segoe UI", 16, QFont.Weight.Black)
    p.setFont(f1)
    p.drawText(QRectF(0, 2, sz, sz * 0.52),
               Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
               name[:5])

    # Countdown (bottom half)
    p.setPen(QColor("#ffffff"))
    f2 = QFont("Segoe UI", 13, QFont.Weight.Bold)
    p.setFont(f2)
    p.drawText(QRectF(0, sz * 0.50, sz, sz * 0.46),
               Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
               countdown)
    p.end()
    return QIcon(px)


# ── Prayer popup ───────────────────────────────────────────────────────────────

class PrayerPopup(QWidget):
    """Frameless popup near the tray showing all prayer times."""

    _GRACE_MS = 280  # hide delay to prevent flicker

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        # Close when clicking anywhere outside
        self.setWindowFlags(
            self.windowFlags() |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(self._GRACE_MS)
        self._hide_timer.timeout.connect(self._do_hide)

        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)

        self._card = QWidget(); self._card.setObjectName("card")
        self._card.setStyleSheet(f"""
            QWidget#card {{
                background: {BG};
                border: 1px solid {ACCENT};
                border-radius: 14px;
            }}
            QWidget#card QLabel {{
                background: transparent;
                border: none;
            }}
        """)

        inner = QVBoxLayout(self._card)
        inner.setContentsMargins(18, 14, 18, 14)
        inner.setSpacing(0)

        header = QLabel("Prayer times")
        header.setStyleSheet(f"color:{MUTED};font-size:10px;letter-spacing:.09em;font-weight:500;")
        inner.addWidget(header)
        inner.addSpacing(10)

        self._rows_layout = QVBoxLayout()
        self._rows_layout.setSpacing(0)
        inner.addLayout(self._rows_layout)

        outer.addWidget(self._card)

    def update_times(self, times: dict, next_prayer: str,
                     lang_names: dict, countdown: str) -> None:
        items = list(times.items())

        # ── Build rows only ONCE (first call or when prayer set changes) ──────
        need_rebuild = (
            not hasattr(self, "_row_labels")
            or list(self._row_labels.keys()) != [n for n, _ in items]
            or getattr(self, "_built_lang", {}) != lang_names
        )
        if need_rebuild:
            self._build_rows(items, lang_names)
            self._built_lang = dict(lang_names)

        # ── Every second: just update text + styles, NO widget rebuild ────────
        for name, time_str in items:
            if name not in self._row_labels:
                continue
            nl, vl = self._row_labels[name]
            is_next = (name == next_prayer)

            # Name label
            nl.setFont(QFont("Segoe UI", 11,
                             QFont.Weight.DemiBold if is_next else QFont.Weight.Normal))
            nl.setStyleSheet(f"color:{'#5DCAA5' if is_next else TEXT};")

            # Value label — countdown for next, fixed time for others
            vl.setText(countdown if is_next else time_str)
            vl.setStyleSheet(
                f"color:{ACCENT if is_next else MUTED};font-size:11px;"
                + ("font-weight:600;" if is_next else ""))

    def _build_rows(self, items: list, lang_names: dict = None) -> None:
        """Build all row widgets from scratch — called only when needed."""
        if lang_names is None: lang_names = {}
        # Clear existing
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._row_labels: dict[str, tuple] = {}  # name → (name_lbl, value_lbl)

        for i, (name, time_str) in enumerate(items):
            row = QWidget(); row.setStyleSheet("background:transparent;")
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 7, 0, 7)

            nl = QLabel(lang_names.get(name, name))
            nl.setFont(QFont("Segoe UI", 11, QFont.Weight.Normal))
            nl.setStyleSheet(f"color:{TEXT};")
            nl.setFixedWidth(110)   # enough for longest kg name

            vl = QLabel(time_str)
            vl.setStyleSheet(f"color:{MUTED};font-size:11px;")
            vl.setAlignment(Qt.AlignmentFlag.AlignRight)
            # Fixed width — prevents popup from resizing every second
            vl.setFixedWidth(80)

            h.addWidget(nl); h.addStretch(); h.addWidget(vl)

            self._row_labels[name] = (nl, vl)

            wrap = QWidget(); wrap.setStyleSheet("background:transparent;")
            wv = QVBoxLayout(wrap)
            wv.setContentsMargins(0, 0, 0, 0); wv.setSpacing(0)
            wv.addWidget(row)

            if i < len(items) - 1:
                sep = QWidget(); sep.setFixedHeight(1)
                sep.setStyleSheet(f"background:{BORDER};")
                wv.addWidget(sep)

            self._rows_layout.addWidget(wrap)

        # Size fixed after first build — no more adjustSize on tick
        self._card.setFixedWidth(240)
        self._card.adjustSize()
        self.setFixedWidth(240)
        self.adjustSize()

    def show_near_tray(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        # Don't call adjustSize — width is fixed, height set after _build_rows
        self.move(screen.right() - self.width() - 14,
                  screen.bottom() - self.height() - 10)
        self.show(); self.raise_()
        # Install app-level filter to catch clicks outside popup
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        """Close popup when user clicks anywhere outside it."""
        from PyQt6.QtCore import QEvent
        if (self.isVisible() and
                event.type() == QEvent.Type.MouseButtonPress):
            # Check if click is outside our widget
            try:
                gpos = event.globalPosition().toPoint()
            except AttributeError:
                gpos = event.globalPos()
            if not self.geometry().contains(gpos):
                self._hide_timer.stop()
                self.hide()
                QApplication.instance().removeEventFilter(self)
        return False   # don't consume the event

    def _do_hide(self):
        self.hide()
        try:
            QApplication.instance().removeEventFilter(self)
        except Exception:
            pass

    def enterEvent(self, event):
        self._hide_timer.stop(); super().enterEvent(event)

    def leaveEvent(self, event):
        self._hide_timer.start(); super().leaveEvent(event)


    def mousePressEvent(self, event):
        """Close popup on any mouse click."""
        self._hide_timer.stop()
        self.hide()
        super().mousePressEvent(event)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # transparent — card handles its own bg
        p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(Qt.PenStyle.NoPen)


# ── Tray icon ──────────────────────────────────────────────────────────────────

class TrayIcon(QSystemTrayIcon):

    def __init__(self, parent=None):
        super().__init__(_make_default_icon(), parent)
        self.setToolTip("Waqt")

        self._popup      = PrayerPopup()
        self._times:      dict = {}
        self._next:       str  = ""
        self._lang_names: dict = {}
        self._countdown:  str  = "--:--"

        # ── Context menu ──
        self._menu = QMenu()
        self._menu.setStyleSheet(f"""
            QMenu {{
                background: {BG};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 4px;
                font-family: 'Segoe UI';
                font-size: 13px;
            }}
            QMenu::item {{
                padding: 8px 22px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background: {ACCENT};
                color: #fff;
            }}
            QMenu::separator {{
                height: 1px;
                background: {BORDER};
                margin: 4px 8px;
            }}
        """)

        self._info_action    = self._menu.addAction("Waqt")
        self._info_action.setEnabled(False)
        self._menu.addSeparator()
        self._show_action    = self._menu.addAction("Open Waqt")
        self._times_action   = self._menu.addAction("Prayer times")
        self._overlay_action = self._menu.addAction("Show overlay")
        self._menu.addSeparator()
        self._quit_action    = self._menu.addAction("Quit")

        self.setContextMenu(self._menu)
        self.activated.connect(self._on_activated)
        self.show()

    # ── Public API ─────────────────────────────────────────────────────────────

    def update_prayer(self, name: str, countdown: str) -> None:
        """Called every second with localised name + HH:MM countdown."""
        self._countdown = countdown
        self._next      = name

        # Shorten countdown for icon: drop hours if 0
        short = countdown.replace("in ", "")
        parts = short.split(":")
        if len(parts) == 3:
            h = int(parts[0])
            short = f"{h}:{parts[1]}" if h > 0 else f"0:{parts[1]}"

        self.setIcon(_make_text_icon(name, short))
        self.setToolTip(f"Waqt  ·  {name}  {countdown}")
        self._info_action.setText(f"{name}  ·  {countdown}")

        if self._popup.isVisible() and self._times:
            self._popup.update_times(
                self._times, self._next, self._lang_names, countdown)

    def set_times(self, times: dict, next_prayer: str, lang_names: dict) -> None:
        self._times      = times
        self._next       = next_prayer
        self._lang_names = lang_names

    def update_language(self, lang: str, t: dict) -> None:
        self._show_action.setText(t.get("open_waqt",        "Open Waqt"))
        self._times_action.setText(t.get("prayer_times_menu", "Prayer times"))
        self._overlay_action.setText(t.get("show_overlay",  "Show overlay"))
        self._quit_action.setText(t.get("quit",             "Quit"))

    # ── Internals ──────────────────────────────────────────────────────────────

    def _on_activated(self, reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.MiddleClick,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._toggle_popup()

    def _toggle_popup(self) -> None:
        if self._popup.isVisible():
            self._popup.hide()
        else:
            if self._times:
                self._popup.update_times(
                    self._times, self._next, self._lang_names, self._countdown)
            self._popup.show_near_tray()

    # ── Properties (used by MainWindow) ───────────────────────────────────────

    @property
    def show_action(self):    return self._show_action
    @property
    def overlay_action(self): return self._overlay_action
    @property
    def times_action(self):   return self._times_action
    @property
    def quit_action(self):    return self._quit_action