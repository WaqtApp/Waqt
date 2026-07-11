"""
prayer_panel.py — PrayerPanel + _LocationBanner for Waqt v6.

Extracted from main_window.py (Step 5 of refactor).
"""

from __future__ import annotations

import os
import sys

from PyQt6.QtCore import Qt, QTimer, QTime, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)

from ui.app_theme import AppTheme, ARABIC, _t, _localized_date, _hijri_date
from ui.widgets import HeroCard, PrayerRow


# ═══════════════════════════════════════════════════════════════════════════════
#  LOCATION BANNER
# ═══════════════════════════════════════════════════════════════════════════════

class _LocationBanner(QWidget):
    """
    Non-blocking banner shown when IP location differs from saved settings.
    User can accept (update city) or dismiss.
    """
    accepted  = pyqtSignal(dict)
    dismissed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loc: dict = {}
        self.setStyleSheet(
            "background:rgba(29,80,58,0.92);"
            "border:1px solid rgba(29,158,117,0.45);"
            "border-radius:10px;")

        h = QHBoxLayout(self)
        h.setContentsMargins(14, 10, 10, 10)
        h.setSpacing(10)

        icon = QLabel("📍")
        icon.setStyleSheet("background:transparent;font-size:16px;border:none;")
        icon.setFixedWidth(22)
        h.addWidget(icon)

        self._lbl = QLabel()
        self._lbl.setStyleSheet(
            "color:rgba(212,232,216,0.90);font-size:11px;"
            "background:transparent;border:none;")
        self._lbl.setWordWrap(True)
        h.addWidget(self._lbl, 1)

        self._yes_btn = QPushButton("Update")
        self._yes_btn.setFixedSize(64, 28)
        self._yes_btn.setStyleSheet(
            "QPushButton {"
            "background:rgba(29,158,117,0.85);color:#fff;"
            "border:none;border-radius:6px;font-size:11px;font-weight:600;}"
            "QPushButton:hover {background:rgba(29,158,117,1.0);}")
        self._yes_btn.clicked.connect(self._accept)
        h.addWidget(self._yes_btn)

        self._no_btn = QPushButton("✕")
        self._no_btn.setFixedSize(24, 24)
        self._no_btn.setStyleSheet(
            "QPushButton {background:transparent;color:rgba(212,232,216,0.45);"
            "border:none;font-size:14px;}"
            "QPushButton:hover {color:rgba(212,232,216,0.90);}")
        self._no_btn.clicked.connect(self._dismiss)
        h.addWidget(self._no_btn)

    def show_for(self, loc: dict):
        self._loc = loc
        city       = loc.get("city", "")
        region     = loc.get("region", "")
        country    = loc.get("country", "")
        region_str = region if (region and region.lower() != city.lower()) else country
        location_str = f"{city}, {region_str}" if region_str else city
        self._lbl.setText(
            f"You appear to be in <b>{location_str}</b>. "
            f"Update for accurate prayer times?")
        self.show()
        self.raise_()

    def _accept(self):
        self.hide()
        self.accepted.emit(self._loc)

    def _dismiss(self):
        self.hide()
        self.dismissed.emit()


# ═══════════════════════════════════════════════════════════════════════════════
#  PRAYER PANEL
# ═══════════════════════════════════════════════════════════════════════════════

class PrayerPanel(QWidget):
    """The main panel showing hero card + prayer list."""

    notif_toggled = pyqtSignal(str, bool)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._s    = settings
        self._lang = settings.get("language", "en")
        self.setStyleSheet(f"background:{AppTheme.bg};")

        self._bg_label = QLabel(self)
        self._bg_label.lower()

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 18, 26, 10)
        root.setSpacing(0)

        # ── Location + date row ──
        loc_row = QHBoxLayout(); loc_row.setSpacing(8)
        self._city_lbl = QLabel()
        self._city_lbl.setFont(AppTheme.display_font(20, QFont.Weight.Medium))
        self._city_lbl.setStyleSheet("color:#f0f8f4;background:transparent;border:none;")
        self._city_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        self._country_lbl = QLabel()
        self._country_lbl.setStyleSheet(
            "color:rgba(212,232,216,0.28);background:transparent;border:none;font-size:13px;")
        self._country_lbl.setAlignment(Qt.AlignmentFlag.AlignBottom)
        self._country_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        self._date_lbl = QLabel()
        self._date_lbl.setStyleSheet(
            "color:rgba(212,232,216,0.22);font-size:11px;background:transparent;border:none;")
        self._date_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._date_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        loc_row.addWidget(self._city_lbl)
        loc_row.addWidget(self._country_lbl)
        loc_row.addStretch()
        loc_row.addWidget(self._date_lbl)
        root.addLayout(loc_row)
        root.addSpacing(16)

        # ── Hero card ──
        self._hero = HeroCard()
        root.addWidget(self._hero)
        root.addSpacing(8)

        # ── Error banner ──
        self._err_banner = QLabel()
        self._err_banner.setStyleSheet(
            "background:rgba(180,60,60,0.12);"
            "color:rgba(220,100,100,0.90);"
            "border:0.5px solid rgba(180,60,60,0.30);"
            "border-radius:8px;padding:6px 12px;font-size:11px;")
        self._err_banner.setWordWrap(True)
        self._err_banner.hide()
        root.addWidget(self._err_banner)

        # ── Location change banner ──
        self._loc_banner = _LocationBanner()
        self._loc_banner.hide()
        root.addWidget(self._loc_banner)

        # ── Prayer rows ──
        self._rows_w = QWidget()
        self._rows_w.setStyleSheet("background:transparent;")
        self._rows_l = QVBoxLayout(self._rows_w)
        self._rows_l.setSpacing(0)
        self._rows_l.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:transparent;border:none;")
        scroll.setWidget(self._rows_w)
        root.addWidget(scroll, 1)

        # ── Footer ──
        foot = QHBoxLayout(); foot.setContentsMargins(4, 8, 4, 0)
        self._info_lbl = QLabel()
        self._info_lbl.setStyleSheet(
            "color:rgba(29,158,117,0.26);font-size:10px;background:transparent;")
        self._hijri_lbl = QLabel()
        self._hijri_lbl.setStyleSheet(
            "color:rgba(29,158,117,0.36);font-size:10px;background:transparent;")
        self._hijri_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._loading_lbl = QLabel()
        self._loading_lbl.setStyleSheet(
            f"color:{AppTheme.accent};font-size:8px;letter-spacing:3px;background:transparent;")
        self._loading_lbl.hide()
        foot.addWidget(self._info_lbl)
        foot.addStretch()
        foot.addWidget(self._loading_lbl)
        foot.addWidget(self._hijri_lbl)
        root.addLayout(foot)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._refresh_bg()

    def set_loading(self, v: bool):
        if v:
            self._loading_lbl.setText("● ● ●")
            self._loading_lbl.show()
            if not hasattr(self, "_load_anim_t"):
                self._load_anim_t = QTimer(self)
                self._load_anim_t.setInterval(500)
                self._load_frames = ["●  ·  ·", "·  ●  ·", "·  ·  ●", "·  ●  ·"]
                self._load_frame_i = 0
                def _step():
                    self._loading_lbl.setText(
                        self._load_frames[self._load_frame_i % len(self._load_frames)])
                    self._load_frame_i += 1
                self._load_anim_t.timeout.connect(_step)
            self._load_anim_t.start()
            self._show_skeleton()
        else:
            if hasattr(self, "_load_anim_t"):
                self._load_anim_t.stop()
            self._loading_lbl.hide()
            self._clear_skeleton()

    def _show_skeleton(self):
        for _ in range(6):
            sk = QWidget()
            sk.setFixedHeight(56)
            sk.setObjectName("skeleton")
            sk.setStyleSheet(
                "QWidget#skeleton{background:rgba(255,255,255,0.03);"
                "border-radius:10px;margin:2px 4px;}")
            self._rows_l.addWidget(sk)

    def _clear_skeleton(self):
        for i in reversed(range(self._rows_l.count())):
            item = self._rows_l.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if w.objectName() == "skeleton":
                    self._rows_l.takeAt(i)
                    w.deleteLater()

    def set_error(self, msg: str | None):
        if msg:
            self._err_banner.setText(msg)
            self._err_banner.show()
        else:
            self._err_banner.hide()

    def set_header(self, city: str, country: str, lang: str,
                   madhab: str, method: str, offline: bool = False):
        self._city_lbl.setText(city)
        self._country_lbl.setText(country)
        self._date_lbl.setText(_localized_date(lang))
        self._hijri_lbl.setText(_hijri_date(lang))
        suffix = "  ·  📵" if offline else ""
        self._info_lbl.setText(f"{madhab}  ·  {method}{suffix}")

    def render_prayers(self, times: dict, next_prayer: str | None,
                       current: str | None, lang: str,
                       prayer_notifs: dict) -> None:
        while self._rows_l.count():
            item = self._rows_l.takeAt(0)
            if w := item.widget(): w.deleteLater()

        dp = current or next_prayer
        if dp:
            self._hero.name_lbl.setText(_t(lang, dp))
            self._hero.time_lbl.setText(times.get(dp, "--:--"))
            self._hero.arabic_lbl.setText(ARABIC.get(dp, ""))
            lk = "current_prayer" if current else "next_prayer"
            self._hero.badge_lbl.setText(_t(lang, lk))
        else:
            self._hero.name_lbl.setText("—")
            self._hero.time_lbl.setText("--:--")
            self._hero.arabic_lbl.setText("")

        if current:
            now = QTime.currentTime()
            pl = [(n, ts) for n, ts in times.items() if n != "Sunrise"]
            for i, (n, ts) in enumerate(pl):
                if n == current and i + 1 < len(pl):
                    t0 = QTime.fromString(ts, "HH:mm")
                    t1 = QTime.fromString(pl[i + 1][1], "HH:mm")
                    total = t0.secsTo(t1)
                    if total > 0:
                        self._hero.set_progress(t0.secsTo(now) / total)
                    break
        else:
            self._hero.set_progress(0)

        now = QTime.currentTime()
        for name, ts in times.items():
            qt = QTime.fromString(ts, "HH:mm")
            if name == current:    state = "active"
            elif qt < now:         state = "done"
            else:                  state = "upcoming"
            notif = prayer_notifs.get(name, True)
            row = PrayerRow(name, ts, state, lang, notif)
            row.notif_toggled.connect(self.notif_toggled)
            self._rows_l.addWidget(row)
        self._rows_l.addStretch()

    def update_countdown(self, countdown: str):
        self._hero.countdown_lbl.setText(countdown)

    def update_progress(self, v: float):
        self._hero.set_progress(v)

    def update_bg(self, enabled: bool, path: str):
        self._s["bg_image_enabled"] = enabled
        self._s["bg_image_path"]    = path
        self._refresh_bg()

    def _refresh_bg(self):
        if not self._s.get("bg_image_enabled", False):
            self._bg_label.setVisible(False); return
        path = self._s.get("bg_image_path", "")
        if not path or not os.path.exists(path):
            for fp in [
                os.path.join(_root, "assets", "background_images", "fatih-yurur.jpg"),
                os.path.join(_root, "assets", "background_images", "fatih-yurur.png"),
            ]:
                if os.path.exists(fp): path = fp; break
        if not path:
            self._bg_label.setVisible(False); return
        pw, ph = self.width(), self.height()
        if pw <= 0 or ph <= 0: return
        src = QPixmap(path)
        if src.isNull(): self._bg_label.setVisible(False); return
        scaled = src.scaled(pw, ph,
                            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                            Qt.TransformationMode.SmoothTransformation)
        xo = (scaled.width() - pw) // 2
        yo = (scaled.height() - ph) // 2
        cropped = scaled.copy(xo, yo, pw, ph)
        pp = QPainter(cropped)
        pp.fillRect(cropped.rect(), QColor(0, 0, 0, 190))
        pp.end()
        self._bg_label.setPixmap(cropped)
        self._bg_label.setGeometry(0, 0, pw, ph)
        self._bg_label.setVisible(True)
        self._bg_label.lower()