"""
settings_panel.py — SettingsPanel for Waqt v6.

Extracted from main_window.py (Step 4 of refactor).
"""

from __future__ import annotations

import os
import sys

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)

from core.settings import save, set_autostart, get_autostart
from ui.app_theme import (
    AppTheme, MADHAB_INFO, METHOD_INFO, LANG_NAMES, LANG_CODES,
    _t, _sec_label, _divider,
)
from ui.widgets import (
    ToggleSwitch, _CB, _SaveButton, CitySearchWidget, _LocationDetectWorker,
)


class SettingsPanel(QWidget):
    """Left settings pane. Reads/writes settings dict via callbacks."""

    save_requested  = pyqtSignal()
    lang_changed    = pyqtSignal(str)
    theme_clicked   = pyqtSignal()
    overlay_clicked = pyqtSignal()
    bg_changed      = pyqtSignal(bool, str)
    overlay_toggled = pyqtSignal(bool)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._s    = settings
        self._lang = settings.get("language", "en")
        self.setFixedWidth(290)
        self.setStyleSheet(f"background:{AppTheme.surface};"
                           "border-right:0.5px solid rgba(255,255,255,0.04);")
        self._build()

    # ── build ──────────────────────────────────────────────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")

        content = QWidget()
        content.setStyleSheet("background:transparent;")
        v = QVBoxLayout(content)
        v.setContentsMargins(16, 18, 16, 16)
        v.setSpacing(12)

        # ── Header ──
        self._title_lbl = QLabel(_t(self._lang, "settings").upper())
        self._title_lbl.setFont(AppTheme.font(10, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet("color:rgba(212,232,216,0.35);letter-spacing:.14em;")
        v.addWidget(self._title_lbl)

        # ── City Search ──
        self._city_search = CitySearchWidget(self._s, self._lang)
        self._city_search.city_selected.connect(self._on_city_selected)
        v.addWidget(self._city_search)

        # Hidden fields for compatibility
        self._city_edit    = QLineEdit(self._s.get("city", "Bishkek"))
        self._country_edit = QLineEdit(self._s.get("country", "Kyrgyzstan"))
        self._city_edit.hide(); self._country_edit.hide()
        self._city_edit.textChanged.connect(lambda t: self._s.update({"city": t}))
        self._country_edit.textChanged.connect(lambda t: self._s.update({"country": t}))

        # ── Madhab + Method ──
        two = QHBoxLayout(); two.setSpacing(10)

        lc1 = QVBoxLayout(); lc1.setSpacing(4)
        self._madhab_lbl = _sec_label(_t(self._lang, "madhab").upper())
        lc1.addWidget(self._madhab_lbl)
        self._madhab_cb = _CB()
        self._madhab_cb.addItems(["Hanafi", "Shafi", "Maliki", "Hanbali"])
        self._madhab_cb.setCurrentText(self._s.get("madhab", "Hanafi"))
        self._madhab_cb.setFixedHeight(36)
        self._madhab_cb.setToolTip(MADHAB_INFO.get(self._s.get("madhab", "Hanafi"), ""))
        self._madhab_cb.currentTextChanged.connect(self._on_madhab_change)
        lc1.addWidget(self._madhab_cb)

        lc2 = QVBoxLayout(); lc2.setSpacing(4)
        self._method_lbl = _sec_label("METHOD")
        lc2.addWidget(self._method_lbl)
        self._method_cb = _CB()
        self._method_cb.addItems(["MWL","Karachi","ISNA","Egypt","Makkah","Tehran","Diyanet","Morocco"])
        self._method_cb.setCurrentText(self._s.get("method", "MWL"))
        self._method_cb.setFixedHeight(36)
        self._method_cb.setToolTip(METHOD_INFO.get(self._s.get("method", "MWL"), ""))
        self._method_cb.currentTextChanged.connect(self._on_method_change)
        lc2.addWidget(self._method_cb)

        two.addLayout(lc1); two.addLayout(lc2)
        v.addLayout(two)

        self._hint_lbl = QLabel(self._method_hint(self._s.get("method", "MWL")))
        self._hint_lbl.setStyleSheet(
            f"color:{AppTheme.accent};font-size:10px;font-style:italic;")
        v.addWidget(self._hint_lbl)

        # ── Language ──
        self._lang_lbl = _sec_label(_t(self._lang, "language").upper())
        v.addWidget(self._lang_lbl)
        self._lang_cb = _CB()
        self._lang_cb.addItems([LANG_NAMES.get(k, k) for k in ["en", "ru", "kg"]])
        self._lang_cb.setCurrentText(LANG_NAMES.get(self._lang, self._lang))
        self._lang_cb.setFixedHeight(36)
        self._lang_cb.currentTextChanged.connect(self._on_lang_change)
        v.addWidget(self._lang_cb)

        v.addWidget(_divider())

        # ── Overlay toggle ──
        self._ow_lbl, self._ow_ts = self._toggle_row_v(v, "overlay_widget", "show_overlay")
        self._ow_ts.toggled.connect(self.overlay_toggled.emit)

        # ── Notifications toggle ──
        self._not_lbl, self._not_ts = self._toggle_row_v(v, "notifications", "notifications")

        # ── Alert before ──
        ab_row = QHBoxLayout(); ab_row.setSpacing(10)
        self._ab_lbl = QLabel(_t(self._lang, "alert_before"))
        self._ab_lbl.setStyleSheet("color:rgba(212,232,216,0.42);font-size:12px;")
        self._ab_lbl.setWordWrap(True)
        ab_row.addWidget(self._ab_lbl, 1)
        self._before_cb = _CB()
        _off = _t(self._lang, "off")
        self._before_cb.addItems([_off, "3 min", "5 min", "10 min", "15 min"])
        self._before_cb.setCurrentText(
            {0: _off, 3: "3 min", 5: "5 min", 10: "10 min", 15: "15 min"}.get(
                self._s.get("notif_minutes", 5), "5 min"))
        self._before_cb.setFixedHeight(34)
        self._before_cb.setFixedWidth(100)
        self._before_cb.currentTextChanged.connect(self._on_before_change)
        ab_row.addWidget(self._before_cb)
        v.addLayout(ab_row)

        v.addWidget(_divider())

        # ── Background image ──
        self._bg_lbl, self._bg_ts = self._toggle_row_v(
            v, "background", "bg_image_enabled", on_toggle=self._on_bg_toggle)

        cur_bg = self._s.get("bg_image_path", "")
        self._choose_btn = QPushButton(
            "  📂  " + (os.path.basename(cur_bg) if cur_bg else _t(self._lang, "choose_image")))
        self._choose_btn.setFixedHeight(34)
        self._choose_btn.setStyleSheet(f"""
            QPushButton{{background:transparent;color:{AppTheme.accent};
                border:1px solid rgba(29,158,117,0.20);border-radius:8px;
                font-size:11px;text-align:left;padding-left:10px;}}
            QPushButton:hover{{background:rgba(29,158,117,0.07);
                border-color:rgba(29,158,117,0.40);}}""")
        self._choose_btn.clicked.connect(self._pick_bg)
        v.addWidget(self._choose_btn)

        v.addWidget(_divider())

        # ── Autostart ──
        self._as_lbl, self._as_ts = self._toggle_row_v(
            v, "autostart", "autostart",
            on_toggle=self._on_autostart_toggle)
        actual = get_autostart()
        self._s["autostart"] = actual
        self._as_ts.blockSignals(True)
        self._as_ts.setChecked(actual)
        self._as_ts.blockSignals(False)

        v.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        # ── Footer: Save button ──
        footer = QWidget()
        footer.setStyleSheet(
            f"background:{AppTheme.surface};"
            "border-top:0.5px solid rgba(255,255,255,0.06);")
        fr = QHBoxLayout(footer)
        fr.setContentsMargins(16, 12, 16, 14)
        self._save_btn = _SaveButton(_t(self._lang, "save_apply"))
        self._save_btn.setFixedHeight(40)
        self._save_btn.clicked.connect(self.save_requested.emit)
        fr.addWidget(self._save_btn)
        outer.addWidget(footer)

    # ── helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _section_wrap() -> QWidget:
        w = QWidget(); w.setStyleSheet("background:transparent;"); return w

    def _toggle_row_v(self, parent_layout: QVBoxLayout, label_key: str,
                      settings_key: str, on_toggle=None):
        row = QHBoxLayout(); row.setContentsMargins(0, 4, 0, 4)
        lbl = QLabel(_t(self._lang, label_key))
        lbl.setStyleSheet("color:rgba(212,232,216,0.58);font-size:13px;")
        ts = ToggleSwitch(checked=self._s.get(settings_key, True))
        def _on_toggle(v, k=settings_key, cb=on_toggle):
            self._s.update({k: v})
            if cb: cb(v)
        ts.toggled.connect(_on_toggle)
        row.addWidget(lbl); row.addStretch(); row.addWidget(ts)
        parent_layout.addLayout(row)
        return lbl, ts

    @staticmethod
    def _method_hint(method: str) -> str:
        info = METHOD_INFO.get(method, "")
        return info.split("·")[-1].strip() if "·" in info else ""

    def _update_auto_lock(self):
        pass

    # ── slots ──────────────────────────────────────────────────────────────────

    def _on_city_selected(self, loc: dict):
        city    = loc.get("city", "")
        country = loc.get("country", "")
        self._city_edit.setText(city)
        self._country_edit.setText(country)
        self._s.update({
            "city":     city,
            "country":  country,
            "last_lat": loc.get("lat"),
            "last_lon": loc.get("lon"),
        })
        self.save_requested.emit()

    def _do_auto_detect(self):
        from PyQt6.QtCore import QTimer
        self._auto_btn.setEnabled(False)
        self._detect_dots = 0
        self._detect_timer = QTimer(self)
        self._detect_timer.timeout.connect(self._animate_detect_btn)
        self._detect_timer.start(500)
        self._animate_detect_btn()
        self._detect_worker = _LocationDetectWorker()
        self._detect_worker.done.connect(self._on_detected)
        self._detect_worker.failed.connect(self._on_detect_fail)
        self._detect_worker.finished.connect(self._detect_worker.deleteLater)
        self._detect_worker.start()

    def _animate_detect_btn(self):
        dots = "." * (self._detect_dots % 4)
        self._auto_btn.setText(f"  Detecting{dots}")
        self._detect_dots += 1

    def _on_detected(self, loc: dict):
        if hasattr(self, "_detect_timer"):
            self._detect_timer.stop()
        self._auto_btn.setText(_t(self._lang, "auto_detect"))
        self._auto_btn.setEnabled(True)
        city    = loc.get("city", "")
        country = loc.get("country", "")
        self._s.update({
            "city": city, "country": country,
            "auto_location": True,
            "last_lat": loc.get("lat"),
            "last_lon": loc.get("lon"),
        })
        save(self._s)
        self.save_requested.emit()

    def _on_detect_fail(self, msg: str):
        if hasattr(self, "_detect_timer"):
            self._detect_timer.stop()
        self._auto_btn.setText(_t(self._lang, "auto_detect"))
        self._auto_btn.setEnabled(True)
        if hasattr(self, "_status_lbl"):
            self._status_lbl.setText(f"⚠ {msg}")
            self._status_lbl.show()

    def _on_madhab_change(self, val: str):
        self._s.update({"madhab": val})
        self._madhab_cb.setToolTip(MADHAB_INFO.get(val, ""))

    def _on_method_change(self, val: str):
        self._s.update({"method": val})
        self._method_cb.setToolTip(METHOD_INFO.get(val, ""))
        self._hint_lbl.setText(self._method_hint(val))

    def _on_before_change(self, val: str):
        off = _t(self._lang, "off")
        self._s.update({"notif_minutes": {off: 0, "3 min": 3, "5 min": 5,
                                          "10 min": 10, "15 min": 15}.get(val, 5)})

    def _on_bg_toggle(self, enabled: bool):
        self._s.update({"bg_image_enabled": enabled})
        self.bg_changed.emit(enabled, self._s.get("bg_image_path", ""))

    def _on_autostart_toggle(self, enabled: bool):
        ok = set_autostart(enabled)
        if not ok and enabled:
            self._as_ts.blockSignals(True)
            self._as_ts.setChecked(False)
            self._as_ts.blockSignals(False)
            self._s["autostart"] = False
        else:
            self._s["autostart"] = enabled
        save(self._s)

    def _pick_bg(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose background", "", "Images (*.jpg *.jpeg *.png *.webp *.bmp)")
        if path:
            self._s.update({"bg_image_path": path, "bg_image_enabled": True})
            self._bg_ts.setChecked(True)
            self._choose_btn.setText("  📂  " + os.path.basename(path))
            self.bg_changed.emit(True, path)

    def _on_lang_change(self, display: str):
        code = LANG_CODES.get(display, "en")
        if code == self._lang: return
        self._lang = code
        self._s.update({"language": code})
        save(self._s)
        self.lang_changed.emit(code)

    def retranslate(self, lang: str):
        self._lang = lang
        self._title_lbl.setText(_t(lang, "settings").upper())
        if hasattr(self, "_city_search"):
            self._city_search.retranslate(lang)
        self._madhab_lbl.setText(_t(lang, "madhab").upper())
        self._ow_lbl.setText(_t(lang, "overlay_widget"))
        self._not_lbl.setText(_t(lang, "notifications"))
        self._ab_lbl.setText(_t(lang, "alert_before"))
        self._bg_lbl.setText(_t(lang, "background"))
        self._as_lbl.setText(_t(lang, "autostart"))
        self._lang_lbl.setText(_t(lang, "language").upper())
        self._save_btn.setText(_t(lang, "save_apply"))
        self._choose_btn.setText("  📂  " + _t(lang, "choose_image"))
        self._update_auto_lock()
        cur_m = self._s.get("notif_minutes", 5)
        _off  = _t(lang, "off")
        self._before_cb.blockSignals(True)
        self._before_cb.clear()
        self._before_cb.addItems([_off, "3 min", "5 min", "10 min", "15 min"])
        self._before_cb.setCurrentText(
            {0: _off, 3: "3 min", 5: "5 min", 10: "10 min", 15: "15 min"}.get(cur_m, "5 min"))
        self._before_cb.blockSignals(False)