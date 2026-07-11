"""
workers.py — Background threads for Waqt v6.

Extracted from main_window.py (Step 2 of refactor).
Contains:
  - FetchWorker     : QThread that fetches prayer times from aladhan API
  - LocationMonitor : QThread that monitors IP-based location changes
"""

from __future__ import annotations

import time

from PyQt6.QtCore import QThread, pyqtSignal

import os
import sys
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

from core.prayer_times import get_prayer_times


# ═══════════════════════════════════════════════════════════════════════════════
#  FETCH WORKER
# ═══════════════════════════════════════════════════════════════════════════════

class FetchWorker(QThread):
    done   = pyqtSignal(dict)
    failed = pyqtSignal(str)

    MAX_RETRIES  = 3
    RETRY_DELAYS = [2, 5, 12]   # seconds: 2s → 5s → 12s (exponential backoff)

    def __init__(self, city: str, country: str, madhab: str, method: str,
                 target_date=None, lat: float = None, lon: float = None,
                 country_code: str = ""):
        super().__init__()
        self.setObjectName("FetchWorker")
        self.city         = city
        self.country      = country
        self.madhab       = madhab
        self.method       = method
        self.target_date  = target_date
        self.lat          = lat
        self.lon          = lon
        self.country_code = country_code

    def run(self):
        last_err = "Unknown error"
        for attempt in range(self.MAX_RETRIES):
            if attempt > 0:
                time.sleep(self.RETRY_DELAYS[attempt - 1])
            try:
                result = self._fetch_once()
                if result:
                    self.done.emit(result)
                    return
            except Exception as e:
                last_err = str(e)
        self.failed.emit(last_err)

    def _fetch_once(self) -> dict | None:
        if self.lat and self.lon:
            from core.prayer_times import (
                _aladhan_get, _extract_times, MADHAB_MAP, METHOD_MAP,
                _tz_from_timezonefinder, _tz_from_country_code,
            )
            from datetime import date as _date
            td = self.target_date or _date.today()
            ds = td.strftime("%d-%m-%Y")
            tz = _tz_from_timezonefinder(self.lat, self.lon)
            if not tz and self.country_code:
                tz = _tz_from_country_code(self.country_code.lower())
            params = {
                "latitude":  self.lat,
                "longitude": self.lon,
                "method":    METHOD_MAP.get(self.method, 3),
                "school":    MADHAB_MAP.get(self.madhab, 1),
            }
            if tz:
                params["timezonestring"] = tz
            data = _aladhan_get(f"timings/{ds}", params)
            if data:
                return _extract_times(data)
        return get_prayer_times(
            self.city, self.country, self.madhab, self.method,
            target_date=self.target_date)


# ═══════════════════════════════════════════════════════════════════════════════
#  LOCATION MONITOR
# ═══════════════════════════════════════════════════════════════════════════════

class LocationMonitor(QThread):
    """
    Background location monitor.

    DESIGN:
    - Does NOT run at startup — first check triggered via QTimer from MainWindow
      so the app is fully loaded before any network call.
    - Runs every CHECK_INTERVAL_MIN minutes after that.
    - stop() sets _running=False; since get_location_by_ip() can take ~8s,
      we check _running before and after each network call.
    - Thread name set so Qt warning shows "LocationMonitor" not empty string.
    """
    location_changed = pyqtSignal(dict)
    detected         = pyqtSignal(dict)

    CHECK_INTERVAL_SEC = 15 * 60
    SLEEP_STEP         = 0.25

    def __init__(self, saved: dict, parent=None):
        super().__init__(parent)
        self._saved   = dict(saved)
        self._running = True
        self._first   = True
        self.setObjectName("LocationMonitor")

    def run(self):
        while self._running:
            self._interruptible_sleep(self.CHECK_INTERVAL_SEC)
            if self._running:
                self._check()

    def _interruptible_sleep(self, total_secs: float):
        elapsed = 0.0
        while self._running and elapsed < total_secs:
            time.sleep(self.SLEEP_STEP)
            elapsed += self.SLEEP_STEP

    def do_check_now(self):
        """
        Called once from MainWindow via QTimer after app loads.
        Runs the check directly in caller's thread context — don't call from GUI thread.
        Instead, use a one-shot QTimer pointing here via a wrapper.
        """
        self._check()

    def _check(self):
        if not self._running:
            return
        try:
            from core.location import get_location_by_ip, locations_differ
            loc = get_location_by_ip()

            if not self._running or not loc.get("city"):
                return

            if self._first:
                self._first = False
                self.detected.emit(loc)

            saved_loc = {
                "city":    self._saved.get("city", ""),
                "country": self._saved.get("country", ""),
                "lat":     self._saved.get("lat"),
                "lon":     self._saved.get("lon"),
            }
            if locations_differ(saved_loc, loc, km_threshold=40.0):
                self.location_changed.emit(loc)
        except Exception:
            pass

    def update_saved(self, city: str, country: str, lat=None, lon=None):
        self._saved = {"city": city, "country": country, "lat": lat, "lon": lon}

    def stop(self):
        self._running = False