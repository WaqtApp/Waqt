"""
calendar_panel.py — CalendarPanel + helpers for Waqt v6.

Extracted from main_window.py (Step 6c of refactor).
"""

from __future__ import annotations

import sys
import os
from datetime import date

from PyQt6.QtCore import Qt, QTime, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel,
    QScrollArea, QVBoxLayout, QWidget,
)

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)

from ui.app_theme import AppTheme, _t, _hijri_date, _divider
from ui.widgets import PrayerIconBadge
from ui.workers import FetchWorker


# ═══════════════════════════════════════════════════════════════════════════════
#  DAY CELL
# ═══════════════════════════════════════════════════════════════════════════════

class _DayCell(QWidget):
    clicked = pyqtSignal(date)
    _SIZE = (36, 34)

    def __init__(self, day: int, d: date,
                 is_sel: bool, is_today: bool, is_friday: bool):
        super().__init__()
        self._date     = d
        self._is_sel   = is_sel
        self._is_today = is_today
        self._is_fri   = is_friday
        self._hover    = False
        self.setFixedSize(*self._SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self._lbl = QLabel(str(day))
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = QFont("Segoe UI", 12)
        f.setWeight(QFont.Weight.Bold if (is_sel or is_today) else
                    QFont.Weight.DemiBold if is_friday else
                    QFont.Weight.Normal)
        self._lbl.setFont(f)
        self._lbl.setStyleSheet("background:transparent;border:none;")
        lay.addWidget(self._lbl)
        self._refresh()

    def _refresh(self):
        ac = AppTheme.accent
        if self._is_sel:
            self._lbl.setStyleSheet("color:#ffffff;background:transparent;border:none;")
        elif self._is_today or self._is_fri:
            self._lbl.setStyleSheet(f"color:{ac};background:transparent;border:none;")
        else:
            self._lbl.setStyleSheet("color:#cce0d4;background:transparent;border:none;")
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        ac = QColor(AppTheme.accent)
        if self._is_sel:
            p.setBrush(QBrush(ac)); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 8, 8)
        elif self._is_today:
            p.setBrush(QBrush(QColor(ac.red(), ac.green(), ac.blue(), 40)))
            p.setPen(QPen(QColor(ac.red(), ac.green(), ac.blue(), 150), 1.5))
            p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 8, 8)
        elif self._hover:
            p.setBrush(QBrush(QColor(255, 255, 255, 16))); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 8, 8)

    def enterEvent(self, e): self._hover = True;  self.update(); super().enterEvent(e)
    def leaveEvent(self, e): self._hover = False; self.update(); super().leaveEvent(e)
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._date)

    @classmethod
    def empty(cls) -> QWidget:
        w = QWidget(); w.setFixedSize(*cls._SIZE)
        w.setStyleSheet("background:transparent;")
        return w


# ═══════════════════════════════════════════════════════════════════════════════
#  NAV BUTTON
# ═══════════════════════════════════════════════════════════════════════════════

class _CalNavBtn(QWidget):
    clicked = pyqtSignal()

    def __init__(self, direction: str = "left", parent=None):
        super().__init__(parent)
        self._dir   = direction
        self._hover = False
        self.setFixedSize(30, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, e): self._hover = True;  self.update()
    def leaveEvent(self, e): self._hover = False; self.update()
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        bg_a     = 50 if self._hover else 20
        border_a = 130 if self._hover else 80
        p.setBrush(QBrush(QColor(29, 158, 117, bg_a)))
        p.setPen(QPen(QColor(29, 158, 117, border_a), 1.0))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 7, 7)
        arrow_color = QColor(29, 158, 117, 230 if self._hover else 170)
        p.setPen(QPen(arrow_color, 2.0, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        cx, cy, s = w / 2, h / 2, 5.5
        if self._dir == "left":
            p.drawLine(QPointF(cx + s * 0.4, cy - s), QPointF(cx - s * 0.6, cy))
            p.drawLine(QPointF(cx - s * 0.6, cy),     QPointF(cx + s * 0.4, cy + s))
        else:
            p.drawLine(QPointF(cx - s * 0.4, cy - s), QPointF(cx + s * 0.6, cy))
            p.drawLine(QPointF(cx + s * 0.6, cy),     QPointF(cx - s * 0.4, cy + s))


# ═══════════════════════════════════════════════════════════════════════════════
#  CALENDAR PANEL
# ═══════════════════════════════════════════════════════════════════════════════

class CalendarPanel(QWidget):
    """Monthly prayer times calendar."""

    MONTHS_EN = ["", "January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]
    DOW       = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._s           = settings
        self._lang        = settings.get("language", "en")
        self._times_cache: dict[str, dict] = {}
        self._workers:    list = []
        self._today       = date.today()
        self._sel         = self._today
        self._cur_month   = self._today.replace(day=1)

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
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")

        content = QWidget(); content.setStyleSheet("background:transparent;")
        root = QVBoxLayout(content)
        root.setContentsMargins(14, 16, 14, 14)
        root.setSpacing(8)

        # Header
        hdr = QLabel("CALENDAR")
        hdr.setFont(AppTheme.font(10, QFont.Weight.Bold))
        hdr.setStyleSheet("color:rgba(212,232,216,0.35);letter-spacing:.14em;")
        root.addWidget(hdr)

        # Month navigation
        nav = QHBoxLayout(); nav.setSpacing(6)
        self._prev_btn = _CalNavBtn("left")
        self._prev_btn.clicked.connect(self._prev_month)
        self._next_btn = _CalNavBtn("right")
        self._next_btn.clicked.connect(self._next_month)
        self._month_lbl = QLabel()
        self._month_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._month_lbl.setStyleSheet(
            "color:rgba(212,232,216,0.85);font-size:13px;font-weight:600;")
        self._update_nav_style()
        nav.addWidget(self._prev_btn)
        nav.addWidget(self._month_lbl, 1)
        nav.addWidget(self._next_btn)
        root.addLayout(nav)

        # Day-of-week headers
        dow_row = QHBoxLayout(); dow_row.setSpacing(0)
        for i, d in enumerate(self.DOW):
            lbl = QLabel(d)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedWidth(36)
            color = "rgba(29,158,117,0.60)" if i == 4 else "rgba(212,232,216,0.22)"
            lbl.setStyleSheet(f"color:{color};font-size:9px;font-weight:500;")
            dow_row.addWidget(lbl)
        dow_row.addStretch()
        root.addLayout(dow_row)

        # Grid container
        self._grid_w = QWidget()
        self._grid_w.setStyleSheet("background:transparent;")
        self._grid_l = QGridLayout(self._grid_w)
        self._grid_l.setSpacing(2)
        self._grid_l.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._grid_w)

        # Hijri date
        self._hijri_lbl = QLabel()
        self._hijri_lbl.setStyleSheet(
            f"color:{AppTheme.accent};font-size:10px;font-style:italic;")
        self._hijri_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._hijri_lbl)

        root.addWidget(_divider())

        # Prayer times section
        pt_hdr = QLabel("PRAYER TIMES")
        pt_hdr.setFont(AppTheme.font(9, QFont.Weight.Bold))
        pt_hdr.setStyleSheet("color:rgba(212,232,216,0.28);letter-spacing:.10em;")
        root.addWidget(pt_hdr)

        self._sel_date_lbl = QLabel()
        self._sel_date_lbl.setStyleSheet("color:rgba(212,232,216,0.45);font-size:11px;")
        root.addWidget(self._sel_date_lbl)

        self._times_w = QWidget()
        self._times_w.setStyleSheet("background:transparent;")
        self._times_layout = QVBoxLayout(self._times_w)
        self._times_layout.setContentsMargins(0, 4, 0, 0)
        self._times_layout.setSpacing(3)
        root.addWidget(self._times_w)

        root.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        self._fill_month()
        self._load_times(self._sel)

    # ── Month grid ─────────────────────────────────────────────────────────────

    def _fill_month(self):
        import calendar as cal
        while self._grid_l.count():
            item = self._grid_l.takeAt(0)
            if w := item.widget():
                w.setParent(None); w.deleteLater()

        self._month_lbl.setText(
            f"{self.MONTHS_EN[self._cur_month.month]} {self._cur_month.year}")
        self._hijri_lbl.setText(_hijri_date(self._lang))

        first_wd = self._cur_month.weekday()
        days_in  = cal.monthrange(self._cur_month.year, self._cur_month.month)[1]
        row, col = 0, first_wd

        for c in range(first_wd):
            self._grid_l.addWidget(_DayCell.empty(), 0, c)

        for day in range(1, days_in + 1):
            d    = date(self._cur_month.year, self._cur_month.month, day)
            cell = _DayCell(day, d,
                            is_sel=(d == self._sel),
                            is_today=(d == self._today),
                            is_friday=(d.weekday() == 4))
            cell.clicked.connect(self._select_day)
            self._grid_l.addWidget(cell, row, col)
            col += 1
            if col == 7:
                col = 0; row += 1

        if col > 0:
            for c in range(col, 7):
                self._grid_l.addWidget(_DayCell.empty(), row, c)

        self._sel_date_lbl.setText(
            f"{self._sel.day} {self.MONTHS_EN[self._sel.month]} {self._sel.year}")

    def _update_nav_style(self):
        self._prev_btn.update()
        self._next_btn.update()

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _prev_month(self):
        y, m = self._cur_month.year, self._cur_month.month
        m -= 1
        if m == 0: m = 12; y -= 1
        self._cur_month = date(y, m, 1)
        try:    self._sel = self._sel.replace(year=y, month=m)
        except: self._sel = self._cur_month
        self._fill_month(); self._load_times(self._sel)

    def _next_month(self):
        y, m = self._cur_month.year, self._cur_month.month
        m += 1
        if m == 13: m = 1; y += 1
        self._cur_month = date(y, m, 1)
        try:    self._sel = self._sel.replace(year=y, month=m)
        except: self._sel = self._cur_month
        self._fill_month(); self._load_times(self._sel)

    def _select_day(self, d: date):
        self._sel = d
        if d.year != self._cur_month.year or d.month != self._cur_month.month:
            self._cur_month = d.replace(day=1)
        self._fill_month(); self._load_times(d)

    # ── Prayer times ───────────────────────────────────────────────────────────

    def _load_times(self, d: date):
        while self._times_layout.count():
            item = self._times_layout.takeAt(0)
            if w := item.widget(): w.deleteLater()

        key = d.isoformat()
        if d == self._today:
            cached = self._s.get("cached_times")
            if cached:
                self._times_cache[key] = cached

        if key in self._times_cache:
            self._render_times(self._times_cache[key], d)
        else:
            loading = QLabel("Loading…")
            loading.setStyleSheet(f"color:{AppTheme.accent};font-size:11px;")
            self._times_layout.addWidget(loading)

            worker = FetchWorker(
                self._s.get("city", "Bishkek"),
                self._s.get("country", "Kyrgyzstan"),
                self._s.get("madhab", "Hanafi"),
                self._s.get("method", "MWL"),
                target_date=d,
            )
            worker.done.connect(lambda t, dk=key, dd=d: self._on_fetched(t, dk, dd))
            worker.failed.connect(self._on_fetch_fail)
            worker.start()
            self._workers.append(worker)
            self._workers = [w for w in self._workers if w.isRunning()]

    def _on_fetched(self, times: dict, key: str, d: date):
        self._times_cache[key] = times
        if self._sel.isoformat() == key:
            while self._times_layout.count():
                item = self._times_layout.takeAt(0)
                if w := item.widget(): w.deleteLater()
            self._render_times(times, d)

    def _on_fetch_fail(self, err: str):
        while self._times_layout.count():
            item = self._times_layout.takeAt(0)
            if w := item.widget(): w.deleteLater()
        lbl = QLabel("Could not load — check connection")
        lbl.setStyleSheet("color:rgba(200,80,80,0.70);font-size:11px;")
        lbl.setWordWrap(True)
        self._times_layout.addWidget(lbl)

    def _render_times(self, times: dict, d: date):
        now      = QTime.currentTime()
        is_today = (d == self._today)
        for name, ts in times.items():
            t_qt   = QTime.fromString(ts, "HH:mm")
            past   = is_today and (t_qt < now)
            active = is_today and not past and name != "Sunrise"

            row_w = QWidget(); row_w.setStyleSheet("background:transparent;")
            row_h = QHBoxLayout(row_w)
            row_h.setContentsMargins(4, 3, 4, 3)
            row_h.setSpacing(10)

            ic = PrayerIconBadge(name, "done" if past else "upcoming")
            ic.setFixedSize(28, 28)
            row_h.addWidget(ic)

            name_lbl = QLabel(_t(self._lang, name))
            if active:
                name_lbl.setStyleSheet(
                    f"color:{AppTheme.accent};font-size:12px;font-weight:600;")
            elif past:
                name_lbl.setStyleSheet("color:rgba(212,232,216,0.25);font-size:12px;")
            else:
                name_lbl.setStyleSheet("color:rgba(212,232,216,0.60);font-size:12px;")
            row_h.addWidget(name_lbl, 1)

            time_lbl = QLabel(ts)
            if active:
                time_lbl.setStyleSheet(
                    f"color:{AppTheme.accent};font-size:12px;font-weight:600;")
            elif past:
                time_lbl.setStyleSheet("color:rgba(212,232,216,0.20);font-size:12px;")
            else:
                time_lbl.setStyleSheet("color:rgba(212,232,216,0.45);font-size:12px;")
            row_h.addWidget(time_lbl)

            self._times_layout.addWidget(row_w)

    # ── External API ───────────────────────────────────────────────────────────

    def set_times_today(self, times: dict):
        key = self._today.isoformat()
        self._times_cache[key] = times
        if self._sel == self._today:
            while self._times_layout.count():
                item = self._times_layout.takeAt(0)
                if w := item.widget(): w.deleteLater()
            self._render_times(times, self._today)

    def retranslate(self, lang: str):
        self._lang = lang
        self._fill_month()
        self._load_times(self._sel)