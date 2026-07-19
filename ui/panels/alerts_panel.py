"""
alerts_panel.py — AlertsPanel + _SoundCard for Waqt v6.

Extracted from main_window.py (Step 6a of refactor).
"""

from __future__ import annotations

import os
import sys

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)

from core.settings import save, save_debounced
from ui.app_theme import AppTheme, _t, _divider
from ui.widgets import ToggleSwitch, _CB, PrayerIconBadge


# ═══════════════════════════════════════════════════════════════════════════════
#  SOUND CARD
# ═══════════════════════════════════════════════════════════════════════════════

class _SoundCard(QWidget):
    """Compact selectable card for sound mode in AlertsPanel."""
    selected = pyqtSignal(str)

    def __init__(self, key: str, icon: str, title: str, desc: str, active: bool = False):
        super().__init__()
        self._key    = key
        self._active = active
        self._hover  = False
        self.setFixedHeight(50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lo = QHBoxLayout(self); lo.setContentsMargins(12, 0, 12, 0); lo.setSpacing(10)

        ic = QLabel(icon)
        ic.setFixedSize(28, 28)
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic.setStyleSheet("background:transparent;font-size:15px;")
        lo.addWidget(ic)

        tw = QWidget(); tw.setStyleSheet("background:transparent;")
        tv = QVBoxLayout(tw); tv.setContentsMargins(0, 0, 0, 0); tv.setSpacing(1)
        tl = QLabel(title)
        tl.setStyleSheet("color:#f0f8f4;font-size:12px;font-weight:500;background:transparent;")
        dl = QLabel(desc)
        dl.setStyleSheet("color:rgba(212,232,216,0.38);font-size:10px;background:transparent;")
        tv.addWidget(tl); tv.addWidget(dl)
        lo.addWidget(tw, 1)

        self._dot = QWidget(); self._dot.setFixedSize(14, 14)
        self._dot.setStyleSheet(
            "background:#1D9E75;border-radius:7px;" if active else
            "background:transparent;border:1.5px solid rgba(255,255,255,0.2);border-radius:7px;")
        lo.addWidget(self._dot)

    def setActive(self, v: bool):
        self._active = v
        self._dot.setStyleSheet(
            "background:#1D9E75;border-radius:7px;" if v else
            "background:transparent;border:1.5px solid rgba(255,255,255,0.2);border-radius:7px;")
        self.update()

    def enterEvent(self, e): self._hover = True;  self.update()
    def leaveEvent(self, e): self._hover = False; self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self._key)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        if self._active:
            p.setBrush(QBrush(AppTheme.accent_qcolor(22)))
            p.setPen(QPen(AppTheme.accent_qcolor(100), 0.8))
        elif self._hover:
            p.setBrush(QBrush(QColor(255, 255, 255, 8)))
            p.setPen(QPen(QColor(255, 255, 255, 20), 0.5))
        else:
            p.setBrush(QBrush(QColor(255, 255, 255, 4)))
            p.setPen(QPen(QColor(255, 255, 255, 10), 0.5))
        r = AppTheme.shape("row_radius")
        p.drawRoundedRect(0, 0, w, h, r, r)


# ═══════════════════════════════════════════════════════════════════════════════
#  ALERTS PANEL
# ═══════════════════════════════════════════════════════════════════════════════

class AlertsPanel(QWidget):
    """Per-prayer notification settings + global alert controls."""

    changed = pyqtSignal()

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._s    = settings
        self._lang = settings.get("language", "en")
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
        v = QVBoxLayout(content)
        v.setContentsMargins(16, 18, 16, 16)
        v.setSpacing(14)

        # Header
        self._hdr_lbl = QLabel(_t(self._lang, "panel_alerts"))
        self._hdr_lbl.setFont(AppTheme.font(10, QFont.Weight.Bold))
        self._hdr_lbl.setStyleSheet("color:rgba(212,232,216,0.35);letter-spacing:.14em;")
        v.addWidget(self._hdr_lbl)

        # Global notifications toggle
        gl_row = QHBoxLayout()
        self._notif_main_lbl = QLabel(_t(self._lang, "notif_lbl"))
        self._notif_main_lbl.setStyleSheet("color:rgba(212,232,216,0.70);font-size:13px;")
        self._global_ts = ToggleSwitch(checked=self._s.get("notifications", True))
        self._global_ts.toggled.connect(self._on_global_toggle)
        gl_row.addWidget(self._notif_main_lbl); gl_row.addStretch(); gl_row.addWidget(self._global_ts)
        v.addLayout(gl_row)

        # Alert before combo
        ab_row = QHBoxLayout(); ab_row.setSpacing(10)
        ab_lbl = QLabel(_t(self._lang, "alert_before"))
        ab_lbl.setStyleSheet("color:rgba(212,232,216,0.42);font-size:12px;")
        ab_row.addWidget(ab_lbl, 1)
        self._before_cb = _CB()
        _off = _t(self._lang, "off")
        self._before_cb.addItems([_off, "3 min", "5 min", "10 min", "15 min"])
        self._before_cb.setCurrentText(
            {0: _off, 3: "3 min", 5: "5 min", 10: "10 min", 15: "15 min"}.get(
                self._s.get("notif_minutes", 5), "5 min"))
        self._before_cb.setFixedHeight(34); self._before_cb.setFixedWidth(100)
        self._before_cb.currentTextChanged.connect(self._on_before_change)
        ab_row.addWidget(self._before_cb)
        v.addLayout(ab_row)

        v.addWidget(_divider())

        # Azan sound header
        self._azan_hdr_lbl = QLabel(_t(self._lang, "panel_azan_sound"))
        self._azan_hdr_lbl.setFont(AppTheme.font(9, QFont.Weight.Bold))
        self._azan_hdr_lbl.setStyleSheet("color:rgba(212,232,216,0.28);letter-spacing:.12em;")
        v.addWidget(self._azan_hdr_lbl)
        v.addSpacing(8)

        # Global sound toggle
        snd_row = QHBoxLayout(); snd_row.setContentsMargins(0, 0, 0, 6)
        self._snd_lbl = QLabel(_t(self._lang, "azan_play_lbl"))
        self._snd_lbl.setStyleSheet("color:rgba(212,232,216,0.65);font-size:13px;")
        self._snd_ts = ToggleSwitch(checked=self._s.get("azan_sound", False))
        self._snd_ts.toggled.connect(self._on_sound_toggle)
        snd_row.addWidget(self._snd_lbl); snd_row.addStretch(); snd_row.addWidget(self._snd_ts)
        v.addLayout(snd_row)

        # Sound mode cards
        _cur_mode = self._s.get("azan_mode", "off")
        self._sound_cards: dict[str, _SoundCard] = {}
        _modes = [
            ("off",    "🔕", "Silent",         "Notifications only, no sound"),
            ("azan",   "🕌", "Azan",            "Traditional call to prayer"),
            ("voice",  "🗣", "Voice reminder", "«Time to pray» announcement"),
            ("custom", "📁", "Custom sound",   "Choose your own audio file"),
        ]
        for key, icon, title, desc in _modes:
            card = _SoundCard(key, icon, title, desc, active=(key == _cur_mode))
            card.selected.connect(self._on_mode_select)
            self._sound_cards[key] = card
            v.addWidget(card)
            v.addSpacing(4)

        # Custom file picker
        self._custom_row = QWidget()
        self._custom_row.setStyleSheet("background:transparent;")
        cr = QHBoxLayout(self._custom_row); cr.setContentsMargins(4, 0, 0, 0); cr.setSpacing(8)
        _cur_custom = self._s.get("azan_custom_path", "")
        self._custom_btn = QPushButton(
            "📂  " + (os.path.basename(_cur_custom) if _cur_custom else "Choose file…"))
        self._custom_btn.setFixedHeight(30)
        self._custom_btn.setStyleSheet(f"""
            QPushButton{{background:transparent;color:{AppTheme.accent};
                border:1px solid {AppTheme.accent_rgba(0.3)};border-radius:{AppTheme.shape('row_radius')}px;
                font-size:11px;text-align:left;padding-left:10px;}}
            QPushButton:hover{{background:{AppTheme.accent_rgba(0.08)};}}""")
        self._custom_btn.clicked.connect(self._pick_custom_sound)
        cr.addWidget(self._custom_btn)
        v.addWidget(self._custom_row)
        self._custom_row.setVisible(_cur_mode == "custom")

        # Volume
        v.addSpacing(6)
        vol_row = QHBoxLayout(); vol_row.setContentsMargins(0, 0, 0, 4)
        self._vol_lbl = QLabel(_t(self._lang, "azan_volume_lbl"))
        self._vol_lbl.setStyleSheet("color:rgba(212,232,216,0.42);font-size:12px;")
        self._vol_cb = _CB()
        self._vol_cb.addItems(["25%", "50%", "75%", "100%"])
        _v = self._s.get("azan_volume", 80)
        self._vol_cb.setCurrentText(
            "25%" if _v <= 30 else "50%" if _v <= 55 else "75%" if _v <= 80 else "100%")
        self._vol_cb.setFixedHeight(30); self._vol_cb.setFixedWidth(82)
        self._vol_cb.currentTextChanged.connect(lambda val: (
            self._s.update({"azan_volume":
                {"25%": 25, "50%": 50, "75%": 75, "100%": 100}.get(val, 80)}),
            save_debounced(self._s)))
        vol_row.addWidget(self._vol_lbl); vol_row.addStretch(); vol_row.addWidget(self._vol_cb)
        v.addLayout(vol_row)

        v.addWidget(_divider())

        # Per-prayer toggles
        self._per_prayer_hdr = QLabel(_t(self._lang, "panel_per_prayer"))
        self._per_prayer_hdr.setFont(AppTheme.font(9, QFont.Weight.Bold))
        self._per_prayer_hdr.setStyleSheet("color:rgba(212,232,216,0.28);letter-spacing:.12em;")
        v.addWidget(self._per_prayer_hdr)

        self._prayer_rows: dict[str, ToggleSwitch] = {}
        prayer_notifs = self._s.get("prayer_notifs", {})
        for name in ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"]:
            row = QHBoxLayout(); row.setContentsMargins(0, 4, 0, 4)
            ic = PrayerIconBadge(name, "upcoming")
            ic.setFixedSize(32, 32)
            row.addWidget(ic)
            row.addSpacing(10)
            lbl = QLabel(_t(self._lang, name))
            lbl.setStyleSheet("color:rgba(212,232,216,0.65);font-size:13px;")
            row.addWidget(lbl, 1)
            ts = ToggleSwitch(checked=prayer_notifs.get(name, name != "Sunrise"))
            ts.toggled.connect(lambda v, n=name: self._on_prayer_toggle(n, v))
            self._prayer_rows[name] = ts
            row.addWidget(ts)
            v.addLayout(row)

        v.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

    # ── slots ──────────────────────────────────────────────────────────────────

    def _on_sound_toggle(self, enabled: bool):
        self._s["azan_sound"] = enabled
        save_debounced(self._s)

    def _on_mode_select(self, key: str):
        for k, c in self._sound_cards.items():
            c.setActive(k == key)
        self._s["azan_mode"]  = key
        self._s["azan_sound"] = (key != "off")
        self._snd_ts.blockSignals(True)
        self._snd_ts.setChecked(key != "off")
        self._snd_ts.blockSignals(False)
        self._custom_row.setVisible(key == "custom")
        save_debounced(self._s)

    def _pick_custom_sound(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose sound file", "",
            "Audio (*.mp3 *.wav *.ogg *.m4a *.aac)")
        if path:
            self._s["azan_custom_path"] = path
            self._s["azan_mode"]  = "custom"
            self._s["azan_sound"] = True
            self._custom_btn.setText("📂  " + os.path.basename(path))
            save_debounced(self._s)

    def _on_global_toggle(self, enabled: bool):
        self._s["notifications"] = enabled
        save_debounced(self._s)
        self.changed.emit()

    def _on_before_change(self, val: str):
        _off = _t(self._lang, "off")
        self._s["notif_minutes"] = {_off: 0, "3 min": 3, "5 min": 5,
                                    "10 min": 10, "15 min": 15}.get(val, 5)
        save_debounced(self._s)

    def _on_prayer_toggle(self, name: str, enabled: bool):
        notifs = self._s.get("prayer_notifs", {})
        notifs[name] = enabled
        self._s["prayer_notifs"] = notifs
        save_debounced(self._s)
        self.changed.emit()

    def retranslate(self, lang: str):
        self._lang = lang
        self._hdr_lbl.setText(_t(lang, "panel_alerts"))
        self._notif_main_lbl.setText(_t(lang, "notif_lbl"))
        self._azan_hdr_lbl.setText(_t(lang, "panel_azan_sound"))
        self._snd_lbl.setText(_t(lang, "azan_play_lbl"))
        self._vol_lbl.setText(_t(lang, "azan_volume_lbl"))
        self._per_prayer_hdr.setText(_t(lang, "panel_per_prayer"))
        cur_m = self._s.get("notif_minutes", 5)
        _off  = _t(lang, "off")
        self._before_cb.blockSignals(True)
        self._before_cb.clear()
        self._before_cb.addItems([_off, "3 min", "5 min", "10 min", "15 min"])
        self._before_cb.setCurrentText(
            {0: _off, 3: "3 min", 5: "5 min", 10: "10 min", 15: "15 min"}.get(cur_m, "5 min"))
        self._before_cb.blockSignals(False)