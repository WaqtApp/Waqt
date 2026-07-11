"""
settings.py — load/save app settings.

Fix: store settings.json in %APPDATA%/Waqt/ instead of cwd.
This prevents permission errors when running from Program Files,
and keeps data when the exe is moved.
"""

import json
import os
from pathlib import Path


def _settings_path() -> Path:
    """
    Returns platform-appropriate path for settings.json.
    Windows: %APPDATA%/Waqt/settings.json
    Linux/Mac: ~/.config/waqt/settings.json
    """
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home() / ".config"

    folder = base / "Waqt"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "settings.json"


SETTINGS_FILE = _settings_path()

DEFAULT = {
    "city":             "Bishkek",
    "country":          "Kyrgyzstan",
    "madhab":           "Hanafi",
    "method":           "MWL",
    "theme_name":       "Dark Green",
    "overlay_style":    "pill",
    "display_mode":     "overlay",
    "notifications":    True,
    "notif_minutes":    5,        # NEW: notify N minutes before prayer
    "language":         "en",
    "auto_location":    True,
    "first_run_shown":  False,
    "cached_times":     None,
    "cached_date":      None,
}


def load() -> dict:
    """Load settings, merging with defaults so new keys always exist."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                on_disk = json.load(f)
            # Merge: disk values override defaults, but new default keys are added
            data = {**DEFAULT, **on_disk}
        except (json.JSONDecodeError, OSError):
            data = DEFAULT.copy()
    else:
        data = DEFAULT.copy()
        # First run: try to auto-detect location
        try:
            from core.location import get_location_by_ip
            loc = get_location_by_ip()
            data["city"]    = loc["city"]
            data["country"] = loc["country"]
            save(data)
        except Exception:
            pass

    return data


def save(data: dict) -> None:
    """Save settings to disk immediately (blocking file write)."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print(f"[Waqt] Could not save settings: {e}")


# ── Debounced save ─────────────────────────────────────────────────────────
# Every ToggleSwitch/combo callback in the panels used to call save() directly.
# Flip 3 toggles in AlertsPanel in a row (global sound, per-prayer x2) and
# that's 3 synchronous JSON writes on the UI thread in ~1 second — each one
# a real syscall (open/write/close). It's not what makes the app feel slow
# on its own, but it's needless I/O on every click and it's the wrong pattern
# to keep copying into new panels. Use save_debounced() from UI callbacks;
# it coalesces N rapid changes into a single write ~500ms after the last one.
import threading

_debounce_lock  = threading.Lock()
_debounce_timer: threading.Timer | None = None
_DEBOUNCE_SECONDS = 0.5


def save_debounced(data: dict) -> None:
    """Schedule a save ~0.5s from now; cancels/reschedules on repeated calls."""
    global _debounce_timer
    with _debounce_lock:
        if _debounce_timer is not None:
            _debounce_timer.cancel()
        _debounce_timer = threading.Timer(_DEBOUNCE_SECONDS, save, args=(data,))
        _debounce_timer.daemon = True
        _debounce_timer.start()


def flush(data: dict) -> None:
    """Force an immediate write and cancel any pending debounced save.
    Call this on app quit / window close so a pending change is never lost."""
    global _debounce_timer
    with _debounce_lock:
        if _debounce_timer is not None:
            _debounce_timer.cancel()
            _debounce_timer = None
    save(data)


def save_cached_times(data: dict, times: dict) -> None:
    """Cache today's prayer times for offline use."""
    from datetime import date
    data["cached_times"] = times
    data["cached_date"]  = date.today().isoformat()
    save(data)


def get_cached_times(data: dict) -> dict | None:
    """Return cached times if they are from today, else None."""
    from datetime import date
    cached      = data.get("cached_times")
    cached_date = data.get("cached_date")
    if cached and cached_date == date.today().isoformat():
        return cached
    return None

# ── Autostart (Windows registry) ──────────────────────────────────────────────

def set_autostart(enabled: bool) -> bool:
    """Enable/disable Windows autostart via registry. Returns True on success."""
    try:
        import sys
        if sys.platform != "win32":
            return False
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "Waqt"
        exe_path = sys.executable  # path to python or frozen exe
        
        # If running as frozen exe (PyInstaller)
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            exe_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
        
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                            winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"[Waqt] Autostart error: {e}")
        return False


def get_autostart() -> bool:
    """Check if Waqt is set to autostart on Windows."""
    try:
        import sys
        if sys.platform != "win32":
            return False
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.QueryValueEx(key, "Waqt")
            return True
    except Exception:
        return False


def get_offline_fallback(data: dict) -> dict | None:
    """
    Return cached prayer times for today if available.
    Same as get_cached_times but with a more descriptive name.
    """
    return get_cached_times(data)