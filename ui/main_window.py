"""
main_window.py — Waqt v6
Complete rewrite: clean architecture + redesigned UI.

Architecture:
  - AppTheme      : single source of truth for colors/fonts
  - AppState      : settings + prayer data, no UI
  - FetchWorker   : background API thread
  - UI Widgets    : ToggleSwitch, HeroCard, PrayerRow, SidebarBtn  (each ≤ 80 lines)
  - SettingsPanel : builds the settings sidebar, reads/writes AppState
  - PrayerPanel   : builds the main view, reads AppState
  - MainWindow    : composes everything, owns timers

Design changes vs v5:
  - Larger, clearer HeroCard (140 px) with bigger countdown
  - Prayer rows 68 px — more breathing room
  - Arabic names right-aligned, smaller, not competing with English
  - Sidebar labels 9px (was 7px)
  - Settings panel scrolls cleanly, no magic lambdas chained
  - Save button is compact, bottom of settings, not giant green brick
  - Error state shown inline (banner), not QMessageBox blocking
  - All colors via AppTheme.c() — no global mutation
"""

from __future__ import annotations

import math
import requests
import time
import os
import sys
from datetime import date

from PyQt6.QtCore import (
    QPoint, QRectF, QPointF, Qt, QThread, QTime, QTimer, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QIcon, QLinearGradient, QPainter,
    QPainterPath, QPen, QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

# ── Path setup ────────────────────────────────────────────────────────────────
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "ui"))

from core.prayer_times import get_prayer_times
from core.settings import load, save, get_cached_times, save_cached_times, get_nearest_cached_times
from overlay import OverlayWidget, OverlayStyleDialog
from notification import show_prayer_notification, show_pre_prayer_notification


# ── Azan sound player ──────────────────────────────────────────────────────────

class AzanPlayer:
    """
    4 modes (set via settings["azan_mode"]):
      "off"    — silent (default)
      "azan"   — plays assets/sounds/azan.mp3 or azan.wav
      "voice"  — plays assets/sounds/voice.mp3 (TTS-style reminder)
      "custom" — plays settings["azan_custom_path"]

    Volume: settings["azan_volume"] 0–100  (default 80)
    Off by default — user chooses during onboarding.
    """

    # Sound file names per mode (searched in assets/sounds/)
    _MODE_FILES = {
        "azan":  ["azan.mp3",  "azan.wav",  "adhan.mp3", "adhan.wav"],
        "voice": ["voice.mp3", "voice.wav", "reminder.mp3"],
    }

    def __init__(self, settings: dict):
        self._s       = settings
        self._player  = None
        self._audio   = None
        self._current_mode: str = ""
        self._current_path: str = ""
        self._init_qt_player()

    # ── Setup ──────────────────────────────────────────────────────────────────

    def _init_qt_player(self):
        """Try to init QMediaPlayer. Silent fail if Qt Multimedia not installed."""
        try:
            from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
            self._player = QMediaPlayer()
            self._audio  = QAudioOutput()
            self._player.setAudioOutput(self._audio)
            vol = self._s.get("azan_volume", 80) / 100.0
            self._audio.setVolume(vol)
        except Exception:
            self._player = None

    def _find_sound(self, mode: str) -> str | None:
        """Find sound file for the given mode."""
        sounds_dir = os.path.join(_root, "assets", "sounds")
        if mode == "custom":
            path = self._s.get("azan_custom_path", "")
            return path if path and os.path.exists(path) else None
        for fname in self._MODE_FILES.get(mode, []):
            fp = os.path.join(sounds_dir, fname)
            if os.path.exists(fp):
                return fp
        return None

    def _load(self, mode: str) -> bool:
        """Load sound for mode into player. Returns True if ready."""
        path = self._find_sound(mode)
        if not path:
            return False
        if self._player:
            try:
                from PyQt6.QtCore import QUrl
                self._player.setSource(QUrl.fromLocalFile(path))
                self._current_path = path
                self._current_mode = mode
                return True
            except Exception:
                pass
        # Fallback path (winsound)
        self._current_path = path
        self._current_mode = mode
        return path.endswith(".wav")

    # ── Public API ─────────────────────────────────────────────────────────────

    def play(self, prayer_name: str = ""):
        """
        Play sound for prayer.
        Respects: azan_mode (global), azan_sound flag, per-prayer sound_prayers.
        """
        mode = self._s.get("azan_mode", "off")
        if mode == "off" or not self._s.get("azan_sound", False):
            return
        # Per-prayer override
        if prayer_name:
            sound_prayers = self._s.get("sound_prayers", {})
            if not sound_prayers.get(prayer_name, True):
                return

        # Load if mode changed or first play
        if mode != self._current_mode:
            if not self._load(mode):
                self._play_beep()
                return

        if self._player and self._current_path:
            try:
                vol = self._s.get("azan_volume", 80) / 100.0
                if self._audio:
                    self._audio.setVolume(vol)
                self._player.setPosition(0)
                self._player.play()
                return
            except Exception:
                pass

        # Fallback: winsound
        if self._current_path and self._current_path.endswith(".wav"):
            try:
                import winsound
                winsound.PlaySound(
                    self._current_path,
                    winsound.SND_FILENAME | winsound.SND_ASYNC)
                return
            except Exception:
                pass

        self._play_beep()

    def _play_beep(self):
        """Last resort — Windows system sound."""
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

    def stop(self):
        if self._player:
            try: self._player.stop()
            except Exception: pass

    def set_volume(self, v: int):
        """v: 0–100"""
        self._s["azan_volume"] = max(0, min(100, v))
        if self._audio:
            try: self._audio.setVolume(v / 100.0)
            except Exception: pass

    def set_custom_path(self, path: str):
        """Set custom sound file path."""
        self._s["azan_custom_path"] = path
        self._s["azan_mode"]  = "custom"
        self._s["azan_sound"] = True
        self._current_mode = ""  # force reload on next play

    def has_sound_file(self, mode: str) -> bool:
        """Check if a sound file exists for the given mode."""
        return self._find_sound(mode) is not None

from tray import TrayIcon
from themes import ThemesDialog, ThemeCard, THEMES
from onboarding import OnboardingWizard
from ui.app_theme import (
    AppTheme,
    ARABIC, PRAYER_COLORS, MADHAB_INFO, METHOD_INFO,
    LANG_NAMES, LANG_CODES, T,
    _t, _hijri_date, _localized_date, _sec_label, _divider,
)


from ui.workers import FetchWorker, LocationMonitor


from ui.widgets import (
    ToggleSwitch, _CB, PrayerIconBadge, BellToggle, PrayerProgressBar,
    PrayerRow, HeroCard, SidebarBtn, _Logo, _AutoDetectBtn, _SaveButton,
    CitySearchWidget, _LocationDetectWorker,
)


# NOTE: get_autostart()/set_autostart() removed — duplicated core.settings'
# implementation. settings_panel.py already imports the real one from there.

# ═══════════════════════════════════════════════════════════════════════════════
#  SETTINGS PANEL
# ═══════════════════════════════════════════════════════════════════════════════

from ui.panels.settings_panel import SettingsPanel

from ui.panels.prayer_panel import PrayerPanel, _LocationBanner


from ui.panels.alerts_panel   import AlertsPanel
from ui.panels.overlay_panel  import OverlayPanel
from ui.panels.calendar_panel import CalendarPanel
from ui.panels.themes_panel   import ThemesPanel

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ═══════════════════════════════════════════════════════════════════════════════

class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        # ── State ──
        self._s: dict         = load()
        self._lang: str       = self._s.get("language", "en")
        self._times: dict     = {}
        self._next: str | None  = None
        self._current: str | None = None
        self._worker: FetchWorker | None = None
        self._notified:  set[str] = set()
        self._pre_noted: set[str] = set()
        self._last_date: str      = ""
        self._prayer_notifs: dict = self._s.get("prayer_notifs", {})

        # ── Window ──
        self.setWindowTitle("Waqt")
        self.setMinimumSize(580, 580)
        self.resize(800, 640)
        self.setStyleSheet(AppTheme.app_stylesheet())
        ip = os.path.join(_root, "assets", "icons", "app_icon.png")
        if os.path.exists(ip): self.setWindowIcon(QIcon(ip))

        # Apply saved theme
        saved_theme = self._s.get("theme_name", "Dark Green")
        if saved_theme in THEMES:
            AppTheme.apply(THEMES[saved_theme], saved_theme)
            self.setStyleSheet(AppTheme.app_stylesheet())

        # Apply saved shape style (minimal/playful — independent of color)
        AppTheme.apply_style(self._s.get("design_style", "minimal"))

        # ── Layout ──
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._sidebar  = self._build_sidebar()
        self._settings = SettingsPanel(self._s)
        self._alerts   = AlertsPanel(self._s)
        self._overlay_panel = OverlayPanel(self._s)
        self._calendar = CalendarPanel(self._s)
        self._themes_panel = ThemesPanel(
            current_theme=self._s.get("theme_name", "Dark Green"))
        self._prayer   = PrayerPanel(self._s)

        # Panel stack — only one visible at a time
        self._panels: dict[str, QWidget] = {
            "settings":    self._settings,
            "bell":        self._alerts,
            "layout_grid": self._overlay_panel,
            "calendar":    self._calendar,
            "palette":     self._themes_panel,
        }
        self._active_panel: str = "settings"

        root.addWidget(self._sidebar)
        for p in self._panels.values():
            root.addWidget(p)
            p.setVisible(False)
        self._settings.setVisible(True)   # default panel
        root.addWidget(self._prayer, 1)

        # ── Connect settings panel signals ──
        self._settings.save_requested.connect(self._save_and_apply)
        self._settings.lang_changed.connect(self._on_lang_changed)
        self._settings.overlay_clicked.connect(self._open_overlay_style)
        self._settings.bg_changed.connect(
            lambda enabled, path: self._prayer.update_bg(enabled, path))
        self._settings.overlay_toggled.connect(self._on_overlay_toggle)
        self._prayer.notif_toggled.connect(self._on_notif_toggle)
        self._themes_panel.theme_changed.connect(self._apply_theme)
        self._themes_panel.style_changed.connect(self._apply_style)
        self._settings._city_search.city_selected.connect(self._on_city_selected_mw)
        # Alerts panel
        self._alerts.changed.connect(lambda: self._prayer_notifs.update(
            self._s.get("prayer_notifs", {})))
        # Overlay panel
        self._overlay_panel.toggle_changed.connect(self._on_overlay_toggle)
        self._overlay_panel.style_changed.connect(self._apply_overlay_style)
        # Calendar: feed today's times when ready
        # (connected after times arrive in _on_times_ready)

        # ── Overlay ──
        self._overlay = OverlayWidget(style=self._s.get("overlay_style", "pill"))
        # Azan sound player
        self._azan = AzanPlayer(self._s)
        # Restore saved position
        ox = self._s.get("overlay_x")
        oy = self._s.get("overlay_y")
        if ox is not None and oy is not None:
            # Clamp to screen bounds so it doesn't end up off-screen
            screen = QApplication.primaryScreen().availableGeometry()
            ox = max(0, min(int(ox), screen.width()  - 100))
            oy = max(0, min(int(oy), screen.height() - 40))
            self._overlay.move(ox, oy)
        if self._s.get("show_overlay", True):
            self._overlay.show()
        # Save position when overlay is moved
        self._overlay_save_timer = QTimer(self)
        self._overlay_save_timer.setSingleShot(True)
        self._overlay_save_timer.setInterval(800)   # debounce — save 0.8s after drag
        self._overlay_save_timer.timeout.connect(self._save_overlay_pos)
        # Override moveEvent on the overlay widget to trigger save
        _orig_move = self._overlay.moveEvent if hasattr(self._overlay, 'moveEvent') else None
        def _on_overlay_move(event, _orig=_orig_move):
            if _orig: _orig(event)
            self._overlay_save_timer.start()
        self._overlay.moveEvent = _on_overlay_move

        # ── Tray ──
        self._tray = TrayIcon(self)
        self._tray.show_action.triggered.connect(self._open_window)
        self._tray.times_action.triggered.connect(self._tray._toggle_popup)
        self._tray.overlay_action.triggered.connect(self._toggle_overlay)
        self._tray.quit_action.triggered.connect(QApplication.quit)

        # ── Onboarding wizard (first run only) ──
        self._wizard: OnboardingWizard | None = None
        if not self._s.get("first_run_shown", False):
            QTimer.singleShot(400, self._show_onboarding)
        else:
            QTimer.singleShot(120, self.refresh_times)

        # ── Timers ──
        self._tick_t = QTimer(self); self._tick_t.timeout.connect(self._tick)
        self._tick_t.start(1000)
        self._refresh_t = QTimer(self); self._refresh_t.timeout.connect(self._auto_refresh)
        self._refresh_t.start(30 * 60 * 1000)

        # Midnight timer — fires exactly at 00:00:10 to refresh for new day
        self._schedule_midnight_refresh()

        # ── Cleanup on app quit ──
        QApplication.instance().aboutToQuit.connect(self._cleanup)

        # ── Location monitor ──
        # monitor only does periodic checks every 15 min — no first-run check here
        self._loc_monitor = LocationMonitor(saved={
            "city":         self._s.get("city", "Bishkek"),
            "country":      self._s.get("country", "Kyrgyzstan"),
            "last_lat":     self._s.get("last_lat"),
            "last_lon":     self._s.get("last_lon"),
            "country_code": self._s.get("country_code", ""),
        })
        self._loc_monitor.location_changed.connect(self._on_location_changed)
        self._loc_monitor.detected.connect(self._on_location_detected)
        self._loc_monitor.start()

        # First-run location check: one-shot worker 15s after startup
        # Uses _LocationDetectWorker so it can be properly stopped/waited
        self._startup_loc_worker: _LocationDetectWorker | None = None
        QTimer.singleShot(15_000, self._startup_location_check)

        # Connect banner signals
        self._prayer._loc_banner.accepted.connect(self._accept_location)
        self._prayer._loc_banner.dismissed.connect(
            lambda: self._s.update({"loc_banner_dismissed": True}))

    # ── Sidebar ────────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> QWidget:
        sb = QWidget(); sb.setFixedWidth(72)
        sb.setStyleSheet(
            f"background:{AppTheme.sidebar};"
            "border-right:1px solid rgba(34,201,138,0.14);")
        v = QVBoxLayout(sb); v.setContentsMargins(0, 16, 0, 16); v.setSpacing(4)
        #v.addWidget(_Logo())
        self._logo = _Logo()
        self._logo.clicked.connect(self._go_home)
        v.addWidget(self._logo)


        def _sdiv():
            dw = QWidget(); dh = QHBoxLayout(dw); dh.setContentsMargins(12, 4, 12, 4)
            d = QWidget(); d.setFixedHeight(1)
            d.setStyleSheet("background:rgba(34,201,138,0.18);")
            dh.addWidget(d); return dw

        v.addWidget(_sdiv())

        idir = os.path.join(_root, "assets", "icons")

        def _ip(name: str) -> str:
            for ext in [".svg", ".png"]:
                fp = os.path.join(idir, name + ext)
                if os.path.exists(fp): return fp
            return ""

        self._sb_btns: dict[str, SidebarBtn] = {}
        nav = [
            ("settings",    _t(self._lang, "sidebar_settings")),
            ("layout_grid", _t(self._lang, "sidebar_overlay")),
            ("bell",        _t(self._lang, "sidebar_alerts")),
            ("calendar",    _t(self._lang, "sidebar_calendar")),
        ]
        for iname, label in nav:
            btn = SidebarBtn(_ip(iname), label=label,
                             active=(iname == "settings"), tooltip=label)
            btn.clicked.connect(lambda _=None, n=iname: self._on_nav(n))
            self._sb_btns[iname] = btn
            v.addWidget(btn)

        v.addWidget(_sdiv())
        _themes_lbl = _t(self._lang, "sidebar_themes")
        pb = SidebarBtn(_ip("palette"), label=_themes_lbl, tooltip=_themes_lbl)
        pb.clicked.connect(lambda: self._on_nav("palette"))
        self._sb_btns["palette"] = pb
        v.addWidget(pb)
        v.addStretch()
        return sb

    def _go_home(self):
        """Close all side panels - show main prayer view."""
        if self._active_panel and self._active_panel in self._panels:
            self._panels[self._active_panel].setVisible(False)
            if btn := self._sb_btns.get(self._active_panel):
                btn.setActive(False)
        self._active_panel = ""

    def _on_nav(self, name: str):
        """Switch the active side panel. Same button again = close panel."""
        panel_keys = list(self._panels.keys())
        if name not in panel_keys:
            return

        if self._active_panel == name:
            # Toggle: click active button → close panel
            panel = self._panels[name]
            panel.setVisible(False)
            if btn := self._sb_btns.get(name): btn.setActive(False)
            self._active_panel = ""
            return

        # Hide previous panel
        if self._active_panel and self._active_panel in self._panels:
            self._panels[self._active_panel].setVisible(False)
            if btn := self._sb_btns.get(self._active_panel):
                btn.setActive(False)

        # Show new panel
        self._panels[name].setVisible(True)
        if btn := self._sb_btns.get(name): btn.setActive(True)
        self._active_panel = name

    # ── Fetch ──────────────────────────────────────────────────────────────────

    def refresh_times(self):
        cached = get_cached_times(self._s)
        if cached:
            self._on_times_ready(cached); return
        self._prayer.set_loading(True)
        self._prayer.set_error(None)
        if self._worker and self._worker.isRunning():
            try:
                self._worker.done.disconnect()
                self._worker.failed.disconnect()
            except Exception:
                pass
            self._worker.quit()
            self._worker.wait(600)
        self._worker = FetchWorker(
            self._s.get("city", "Bishkek"), self._s.get("country", "Kyrgyzstan"),
            self._s.get("madhab", "Hanafi"), self._s.get("method", "MWL"),
            lat=self._s.get("last_lat"), lon=self._s.get("last_lon"),
            country_code=self._s.get("country_code", ""))
        self._worker.done.connect(self._on_times_ready)
        self._worker.failed.connect(self._on_fetch_err)
        self._worker.start()

    def _on_times_ready(self, times: dict):
        self._prayer.set_loading(False)
        self._prayer.set_error(None)
        self._times = times
        save_cached_times(self._s, times)
        self._update_header(offline=False)
        self._render()
        self._tray.set_times(times, self._next or "",
                             T.get(self._lang, T["en"]))
        # Feed calendar today times
        if hasattr(self, "_calendar"):
            self._calendar.set_times_today(times)

    def _on_fetch_err(self, msg: str):
        self._prayer.set_loading(False)

        # 1) Any cached day within the last week — degrades gracefully,
        #    works for any city (prayer times drift ~1-2 min/day).
        cached, age_days = get_nearest_cached_times(self._s, max_age_days=7)
        if cached is not None:
            self._times = cached
            lang = self._lang
            if age_days == 0:
                warn = {
                    "en": "⚠  No internet — showing today's cached times",
                    "ru": "⚠  Нет интернета — время из сегодняшнего кэша",
                    "kg": "⚠  Интернет жок — бүгүнкү кэштелген убакыт",
                }.get(lang, "⚠  No internet — showing cached times")
            else:
                warn = {
                    "en": f"⚠  No internet — times from {age_days}d ago (approx.)",
                    "ru": f"⚠  Нет интернета — время {age_days} дн. назад (примерно)",
                    "kg": f"⚠  Интернет жок — {age_days} күн мурунку убакыт (болжол)",
                }.get(lang, f"⚠  No internet — {age_days}d-old cached times")
            self._prayer.set_error(warn)
            self._update_header(offline=True)
            self._render()
            return

        # 2) No cache, but we know where the user is — compute locally
        #    from sun position. No network, no per-city table.
        lat = self._s.get("last_lat")
        lon = self._s.get("last_lon")
        if lat is not None and lon is not None:
            from core.prayer_times import calculate_local, utc_offset_hours, resolve_timezone_offline
            tz_name = resolve_timezone_offline(lat, lon, self._s.get("country_code", ""))
            tz_offset = utc_offset_hours(tz_name, date.today())
            self._times = calculate_local(
                lat, lon, tz_offset, date.today(),
                self._s.get("method", "MWL"), self._s.get("madhab", "Hanafi"))
            lang = self._lang
            warn = {
                "en": "⚠  No internet, no cache — locally computed (~±2 min)",
                "ru": "⚠  Нет интернета и кэша — расчёт на месте (~±2 мин)",
                "kg": "⚠  Интернет жана кэш жок — жергиликтүү эсептөө (~±2 мүн)",
            }.get(lang, "⚠  Offline — locally computed times")
            self._prayer.set_error(warn)
            self._update_header(offline=True)
            self._render()
            return

        # 3) Never connected at all — nothing honest to show. A hardcoded
        #    city would be wrong, not approximate, so say so plainly.
        self._times = {}
        lang = self._lang
        warn = {
            "en": "⚠  Connect to the internet once to set up your location",
            "ru": "⚠  Подключитесь к интернету хотя бы раз, чтобы задать локацию",
            "kg": "⚠  Локацияны коюу үчүн бир жолу интернетке кошулуңуз",
        }.get(lang, "⚠  Internet required for first-time setup")
        self._prayer.set_error(warn)
        self._update_header(offline=True)
        self._render()

    def _update_header(self, offline: bool = False):
        self._prayer.set_header(
            self._s.get("city", ""),
            self._s.get("country", ""),
            self._lang,
            self._s.get("madhab", ""),
            self._s.get("method", ""),
            offline=offline,
        )

    # ── Render ─────────────────────────────────────────────────────────────────

    def _compute_next_current(self):
        if not self._times: return
        now = QTime.currentTime()
        self._current  = self._calc_current(now)
        self._next     = self._calc_next(now)

    def _render(self):
        self._compute_next_current()
        self._prayer.render_prayers(
            self._times, self._next, self._current,
            self._lang, self._prayer_notifs)

    def _calc_current(self, now: QTime) -> str | None:
        if not self._times: return None
        fajr    = QTime.fromString(self._times.get("Fajr", "00:00"), "HH:mm")
        sunrise = QTime.fromString(self._times.get("Sunrise", "00:00"), "HH:mm")
        if now < fajr: return None
        if fajr <= now < sunrise: return "Fajr"
        skip = {"Sunrise", "Fajr"}
        pl = [(n, t) for n, t in self._times.items() if n not in skip]
        for i in range(len(pl) - 1):
            n, ts = pl[i]; _, tn = pl[i + 1]
            if QTime.fromString(ts, "HH:mm") <= now < QTime.fromString(tn, "HH:mm"):
                return n
        if pl:
            ln, lt = pl[-1]
            if now >= QTime.fromString(lt, "HH:mm"): return ln
        return None

    def _calc_next(self, now: QTime) -> str:
        for name, ts in self._times.items():
            if name == "Sunrise": continue
            if QTime.fromString(ts, "HH:mm") > now: return name
        return "Fajr"

    # ── Tick ───────────────────────────────────────────────────────────────────

    def _tick(self):
        if not self._next or self._next not in self._times: return
        now = QTime.currentTime()

        # ── Sleep/Wake-up detection ───────────────────────────────────────────────
        # >65s gap between ticks = laptop woke from sleep.
        # Immediately recalculate which prayer is next/current.
        if hasattr(self, '_last_tick_time'):
            elapsed = self._last_tick_time.secsTo(now)
            if elapsed < 0: elapsed += 86400   # midnight wrap
            if elapsed > 65:
                print(f'[Waqt] Wake-up detected — {elapsed}s gap. Recalculating.')
                self._last_tick_time = now
                self._render()   # instantly fixes next/current prayer
                from datetime import date as _date
                if self._s.get('cached_date', '') != _date.today().isoformat():
                    print('[Waqt] New day on wake-up — refreshing prayer times.')
                    self.refresh_times()
                return
        self._last_tick_time = now
        # ──────────────────────────────────────────────────────────────────────

        qt  = QTime.fromString(self._times[self._next], "HH:mm")
        secs = now.secsTo(qt)
        if secs < -60: secs += 86400

        # Pre-prayer notification
        nm = self._s.get("notif_minutes", 5)
        pk = f"pre_{self._next}"
        if (self._s.get("notifications", True) and nm > 0
                and 0 < secs <= nm * 60 and pk not in self._pre_noted
                and self._prayer_notifs.get(self._next, True)):
            self._pre_noted.add(pk)
            show_pre_prayer_notification(
                _t(self._lang, self._next), self._times[self._next], nm)

        # At prayer time
        if -2 <= secs <= 0:
            if (self._s.get("notifications", True)
                    and self._next not in self._notified
                    and self._prayer_notifs.get(self._next, True)):
                self._notified.add(self._next)
                show_prayer_notification(
                    _t(self._lang, self._next), self._times[self._next])
                # Play azan sound
                if hasattr(self, "_azan"):
                    self._azan.play(self._next)
            self._render(); return

        h, rem = divmod(secs, 3600); m2, s = divmod(rem, 60)
        countdown = f"in {h:02d}:{m2:02d}:{s:02d}"
        self._prayer.update_countdown(countdown)

        # Progress
        cur = self._calc_current(now)
        if cur:
            pl = [(n, ts) for n, ts in self._times.items() if n != "Sunrise"]
            for i, (n, ts) in enumerate(pl):
                if n == cur and i + 1 < len(pl):
                    t0 = QTime.fromString(ts, "HH:mm")
                    t1 = QTime.fromString(pl[i + 1][1], "HH:mm")
                    total = t0.secsTo(t1)
                    if total > 0:
                        self._prayer.update_progress(t0.secsTo(now) / total)
                    break

        name = _t(self._lang, cur or self._next)
        if hasattr(self, "_overlay"):
            self._overlay.update_info(
                name, self._times.get(cur or self._next, ""), countdown)
        if hasattr(self, "_tray"):
            self._tray.update_prayer(name, f"{h:02d}:{m2:02d}")
            # Keep popup countdown live if it's currently visible
            if (hasattr(self._tray, "_popup")
                    and self._tray._popup.isVisible()
                    and self._times):
                self._tray._popup.update_times(
                    self._times,
                    self._next or "",
                    T.get(self._lang, T["en"]),
                    countdown)

    # ── Actions ────────────────────────────────────────────────────────────────

    def _startup_location_check(self):
        """
        One-shot location check 15s after startup.
        Uses _LocationDetectWorker (same as manual auto-detect button).
        Shows banner if detected location differs from saved.
        """
        w = _LocationDetectWorker()
        w.done.connect(self._on_location_detected)
        # Don't show error on startup check — silent fail is fine
        w.finished.connect(w.deleteLater)
        self._startup_loc_worker = w
        w.start()

    def _cleanup(self):
        """Stop all background threads before app exits."""
        try:
            if hasattr(self, "_azan"):
                self._azan.stop()
        except Exception:
            pass
        try:
            # Stop startup location check if still running
            if hasattr(self, "_startup_loc_worker") and self._startup_loc_worker:
                if self._startup_loc_worker.isRunning():
                    self._startup_loc_worker.quit()
                    self._startup_loc_worker.wait(500)

            # Stop periodic monitor — wait long enough for any active network call
            if hasattr(self, "_loc_monitor"):
                self._loc_monitor.stop()
                # We give 10s because get_location_by_ip can take ~8s
                # If it doesn't stop in time, terminate it
                if not self._loc_monitor.wait(10_000):
                    self._loc_monitor.terminate()
                    self._loc_monitor.wait(500)

            if hasattr(self, "_worker") and self._worker and self._worker.isRunning():
                self._worker.quit()
                self._worker.wait(500)

            for attr in ["_detect_worker", "_aw"]:
                w = getattr(self, attr, None)
                if w and hasattr(w, "isRunning") and w.isRunning():
                    w.quit()
                    w.wait(300)
        except Exception:
            pass

    def _on_city_selected_mw(self, loc: dict):
        """User selected a city from the search widget."""
        city    = loc.get("city", "")
        country = loc.get("country", "")
        self._s.update({
            "city": city, "country": country,
            "last_lat": loc.get("lat"), "last_lon": loc.get("lon"),
            "auto_location": False,
        })
        save(self._s)
        self._update_header()
        if hasattr(self, "_loc_monitor"):
            self._loc_monitor.update_saved(city, country, loc.get("lat"), loc.get("lon"))
        self._s.pop("cached_times", None)
        self._s.pop("cached_date",  None)
        self.refresh_times()

    def _save_and_apply(self):
        save(self._s)
        self._s.pop("cached_times", None)
        self._s.pop("cached_date",  None)
        self.refresh_times()

    def _on_location_detected(self, loc: dict):
        """First detection after startup — show banner if location differs."""
        from core.location import locations_differ
        saved_loc = {
            "city":    self._s.get("city", ""),
            "country": self._s.get("country", ""),
            "lat":     self._s.get("last_lat"),
            "lon":     self._s.get("last_lon"),
        }
        if not loc.get("city"):
            return
        # Always show if coordinates differ significantly (ignores cached dismiss)
        if locations_differ(saved_loc, loc, km_threshold=40.0):
            self._s.pop("loc_banner_dismissed", None)
            self._prayer._loc_banner.show_for(loc)

    def _on_location_changed(self, loc: dict):
        """Periodic check found a significantly different location."""
        self._s.pop("loc_banner_dismissed", None)   # reset dismiss flag
        self._prayer._loc_banner.show_for(loc)

    def _accept_location(self, loc: dict):
        """User clicked Update in the location banner."""
        city    = loc.get("city", "")
        country = loc.get("country", "")
        self._s.update({
            "city":    city,
            "country": country,
            "last_lat":  loc.get("lat"),
            "last_lon":  loc.get("lon"),
            "loc_banner_dismissed": False,
        })
        save(self._s)
        # Sync settings panel fields
        if hasattr(self._settings, "_city_edit"):
            self._settings._city_edit.setText(city)
        if hasattr(self._settings, "_country_edit"):
            self._settings._country_edit.setText(country)
        # Update monitor
        if hasattr(self, "_loc_monitor"):
            self._loc_monitor.update_saved(city, country, loc.get("lat"), loc.get("lon"))
        # Refresh prayer times for new city
        self._s.pop("cached_times", None)
        self._s.pop("cached_date",  None)
        self.refresh_times()

    def _on_notif_toggle(self, name: str, enabled: bool):
        self._prayer_notifs[name] = enabled
        self._s["prayer_notifs"] = self._prayer_notifs
        save(self._s)

    def _on_lang_changed(self, code: str):
        self._lang = code
        self._settings.retranslate(code)
        if hasattr(self, "_alerts"):
            self._alerts.retranslate(code)
        if hasattr(self, "_calendar"):
            self._calendar.retranslate(code)
        if hasattr(self, "_tray"):
            self._tray.update_language(code, T.get(code, T["en"]))

        # ── Retranslate sidebar button labels ─────────────────────────────
        _key_map = {
            "settings":    "sidebar_settings",
            "layout_grid": "sidebar_overlay",
            "bell":        "sidebar_alerts",
            "calendar":    "sidebar_calendar",
            "palette":     "sidebar_themes",
        }
        for btn_key, t_key in _key_map.items():
            if btn := self._sb_btns.get(btn_key):
                new_label = _t(code, t_key)
                btn._label = new_label
                btn.setToolTip(new_label)
                btn.update()

        self._update_header()
        if self._times: self._render()

    def _schedule_midnight_refresh(self):
        """
        Schedule a one-shot timer to fire 10 seconds after midnight.
        After firing, it reschedules itself for the next midnight.
        This ensures prayer times always refresh at the start of a new day,
        even if the app has been running for days.
        """
        from datetime import datetime, timedelta
        now = datetime.now()
        # Next midnight = tomorrow 00:00:00
        tomorrow = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=10, microsecond=0)
        ms_until_midnight = int((tomorrow - now).total_seconds() * 1000)
        # Clamp to reasonable range (shouldn't be needed but defensive)
        ms_until_midnight = max(1000, min(ms_until_midnight, 24 * 60 * 60 * 1000))
        QTimer.singleShot(ms_until_midnight, self._on_midnight)

    def _on_midnight(self):
        """Called at 00:00:10 — clears day state and fetches fresh times."""
        today = date.today().isoformat()
        self._last_date = today
        self._notified  = set()
        self._pre_noted = set()
        self._s.pop("cached_times", None)
        self._s.pop("cached_date",  None)
        self.refresh_times()
        self._schedule_midnight_refresh()

    def _auto_refresh(self):
        """Called every 30 minutes — handles midnight boundary."""
        today = date.today().isoformat()
        if today != self._last_date:
            self._last_date = today
            self._notified  = set()
            self._pre_noted = set()
            self._s.pop("cached_times", None)
            self._s.pop("cached_date",  None)
        elif self._s.get("cached_date", "") != today:
            self._s.pop("cached_times", None)
            self._s.pop("cached_date",  None)
        self.refresh_times()

    def _save_overlay_pos(self):
        """Save overlay position to settings (debounced)."""
        if hasattr(self, "_overlay") and self._overlay.isVisible():
            pos = self._overlay.pos()
            self._s["overlay_x"] = pos.x()
            self._s["overlay_y"] = pos.y()
            save(self._s)

    def _open_window(self):
        self.show(); self.raise_(); self.activateWindow()
        if self.isMinimized(): self.showNormal()

    def _first_run_tip(self):
        """Kept for compatibility — wizard handles first run now."""
        pass

    def _show_onboarding(self):
        """Launch first-run wizard as overlay on top of main window."""
        from onboarding import OnboardingWizard
        self._wizard = OnboardingWizard(self._s, parent=self)
        self._wizard.finished.connect(self._on_onboarding_done)
        self._wizard.show()
        self._wizard.raise_()

    def _on_onboarding_done(self, settings: dict):
        """Called when user completes onboarding wizard."""
        self._s.update(settings)
        self._lang = self._s.get("language", "en")
        save(self._s)

        # Re-init azan player with chosen mode
        if hasattr(self, "_azan"):
            self._azan.stop()
        self._azan = AzanPlayer(self._s)

        # Apply language to all panels
        lang = self._lang
        if hasattr(self, "_settings"):
            self._settings.retranslate(lang)
        if hasattr(self, "_alerts"):
            self._alerts.retranslate(lang)
        if hasattr(self, "_calendar"):
            self._calendar.retranslate(lang)
        if hasattr(self, "_tray"):
            self._tray.update_language(lang, T.get(lang, T["en"]))

        # Update panels background styles
        if hasattr(self, "_settings"):
            self._settings.setStyleSheet(
                f"background:{AppTheme.surface};"
                "border-right:0.5px solid rgba(255,255,255,0.04);")

        self._wizard = None

        # Now fetch prayer times for chosen location
        self._s.pop("cached_times", None)
        self._s.pop("cached_date",  None)
        self.refresh_times()

    def _on_overlay_toggle(self, enabled: bool):
        """Called when user flips the Overlay widget toggle (Settings or OverlayPanel)."""
        self._s["show_overlay"] = enabled
        save(self._s)
        if not hasattr(self, "_overlay"):
            return
        if enabled:
            self._overlay.show()
        else:
            self._overlay.hide()
        # Sync both toggles
        if hasattr(self, "_settings") and hasattr(self._settings, "_ow_ts"):
            self._settings._ow_ts.blockSignals(True)
            self._settings._ow_ts.setChecked(enabled)
            self._settings._ow_ts.blockSignals(False)
        if hasattr(self, "_overlay_panel") and hasattr(self._overlay_panel, "_show_ts"):
            self._overlay_panel.sync_toggle(enabled)

    def _toggle_overlay(self):
        """Toggle called from tray menu."""
        if not hasattr(self, "_overlay"):
            return
        enabled = not self._overlay.isVisible()
        self._overlay.show() if enabled else self._overlay.hide()
        # Sync the settings toggle if panel exists
        self._s["show_overlay"] = enabled
        if hasattr(self, "_settings") and hasattr(self._settings, "_ow_ts"):
            self._settings._ow_ts.setChecked(enabled)

    def _open_overlay_style(self):
        dlg = OverlayStyleDialog(
            current_style=self._s.get("overlay_style", "pill"), parent=self)
        dlg.style_chosen.connect(self._apply_overlay_style); dlg.exec()

    def _apply_overlay_style(self, style: str):
        self._s["overlay_style"] = style; save(self._s)
        if hasattr(self, "_overlay"):
            was = self._overlay.isVisible()
            self._overlay.set_style(style)
            if was: self._overlay.show()

    def _apply_theme(self, colors: dict):
        name = next((n for n, c in THEMES.items() if c == colors), "Dark Green")
        self._s["theme_name"] = name; save(self._s)
        AppTheme.apply(colors, name)
        self.setStyleSheet(AppTheme.app_stylesheet())
        # Update all panel backgrounds
        for panel in self._panels.values():
            panel.setStyleSheet(f"background:{AppTheme.surface};"
                                "border-right:0.5px solid rgba(255,255,255,0.04);")
        self._prayer.setStyleSheet(f"background:{AppTheme.bg};")
        self._prayer._refresh_bg()
        # Sync themes panel active card
        if hasattr(self, "_themes_panel"):
            self._themes_panel.set_current(name)
        if self._times: self._render()

    def _apply_style(self, style_name: str):
        """Shape axis (minimal/playful) — separate from color, see AppTheme.style."""
        self._s["design_style"] = style_name
        save(self._s)
        # HeroCard reads AppTheme.shape() at paint time; refresh_shape() also
        # rebuilds the badge (dot+label vs filled pill) and progress bar height.
        if hasattr(self._prayer, "_hero"):
            self._prayer._hero.refresh_shape()