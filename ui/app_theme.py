"""
app_theme.py — AppTheme + static data for Waqt v6.

Extracted from main_window.py (Step 1 of refactor).
Contains:
  - AppTheme      : colors, fonts, global stylesheet
  - ARABIC        : Arabic prayer name strings
  - PRAYER_COLORS : per-prayer stroke/bg colors
  - MADHAB_INFO   : madhab descriptions
  - METHOD_INFO   : calculation method descriptions
  - LANG_NAMES / LANG_CODES
  - T             : all UI translations (en, ru, kg)
  - _t()          : translation helper
  - _hijri_date() : Hijri calendar calculation
  - _localized_date() : locale-aware Gregorian date string
  - _sec_label()  : section label factory
  - _divider()    : horizontal divider factory
"""

from __future__ import annotations

from datetime import date

from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QLabel, QWidget


# ═══════════════════════════════════════════════════════════════════════════════
#  THEME
# ═══════════════════════════════════════════════════════════════════════════════

class AppTheme:
    """Single source of truth for the current color palette + fonts."""

    bg       = "#263445"
    surface  = "#0d1117"
    sidebar  = "#060809"
    accent   = "#1D9E75"
    text     = "#ffffff"
    muted    = "#4a6a52"
    border   = "#141e18"
    row_bg   = "#0b1410"
    name     = "Dark Green"

    # ── Style profile: SHAPE, independent of color ──────────────────────────
    # Color themes (THEMES dict) answer "what hue". Style answers "how round,
    # how thick, how loud". Two axes, so any color theme can pair with either
    # style without a combinatorial explosion of presets.
    style = "minimal"   # "minimal" (Apple-ish) | "playful" (One UI-ish)

    STYLE_PROFILES = {
        "minimal": {
            "card_radius":     16,
            "progress_h":      2,
            "progress_radius": 1,
            "badge_pill":      False,   # small dot + uppercase label
            "row_radius":      10,
            "border_alpha":    55,      # thin hairline border on cards
        },
        "playful": {
            "card_radius":     26,
            "progress_h":      8,
            "progress_radius": 4,
            "badge_pill":      True,    # filled rounded badge
            "row_radius":      18,
            "border_alpha":    0,       # no hairline — flat filled shapes instead
        },
    }

    @classmethod
    def shape(cls, key: str):
        return cls.STYLE_PROFILES.get(cls.style, cls.STYLE_PROFILES["minimal"])[key]

    @classmethod
    def apply_style(cls, style_name: str) -> None:
        if style_name in cls.STYLE_PROFILES:
            cls.style = style_name

    @classmethod
    def apply(cls, colors: dict, name: str = "") -> None:
        cls.bg      = colors.get("bg",      cls.bg)
        cls.surface = colors.get("surface", cls.surface)
        cls.accent  = colors.get("accent",  cls.accent)
        cls.text    = colors.get("text",    cls.text)
        cls.border  = colors.get("border",  cls.border)
        cls.name    = name

    @staticmethod
    def c(hex_: str, alpha: int = 255) -> QColor:
        col = QColor(hex_)
        col.setAlpha(alpha)
        return col

    @staticmethod
    def font(size: int, weight=QFont.Weight.Normal, family: str = "Segoe UI") -> QFont:
        if size <= 0:
            size = 11   # safe default
        f = QFont(family, size)
        f.setWeight(weight)
        return f

    @staticmethod
    def display_font(size: int, weight=QFont.Weight.Normal) -> QFont:
        """Serif font for prayer names / times."""
        if size <= 0:
            size = 11
        f = QFont()
        f.setFamilies(["Cinzel", "Palatino Linotype", "Book Antiqua", "Segoe UI"])
        f.setPointSize(size)
        f.setWeight(weight)
        return f

    @classmethod
    def app_stylesheet(cls) -> str:
        return f"""
QWidget {{
    background: {cls.bg};
    color: {cls.text};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}
QLineEdit {{
    background: rgba(255,255,255,0.04);
    color: {cls.text};
    border: 0.5px solid rgba(255,255,255,0.09);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
}}
QLineEdit:focus {{
    border: 0.5px solid rgba(29,158,117,0.50);
    background: rgba(29,158,117,0.05);
}}
QLineEdit:read-only {{
    background: rgba(255,255,255,0.02);
    color: rgba(212,232,216,0.22);
    border: 0.5px solid rgba(255,255,255,0.04);
}}
QComboBox {{
    background: rgba(255,255,255,0.04);
    color: {cls.text};
    border: 0.5px solid rgba(255,255,255,0.09);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    min-height: 16px;
}}
QComboBox:hover {{ border: 0.5px solid rgba(29,158,117,0.36); }}
QComboBox::drop-down {{ border: none; width: 20px; background: transparent; }}
QComboBox::down-arrow {{
    image: none; width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {cls.accent};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: #0d1a10;
    color: {cls.text};
    border: 0.5px solid {cls.border};
    padding: 4px;
    selection-background-color: {cls.accent};
    selection-color: #fff;
    outline: none;
    border-radius: 8px;
}}
QComboBox QAbstractItemView::item {{ padding: 6px 12px; min-height: 26px; }}
QPushButton {{
    background: {cls.accent};
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton:hover {{ background: #17b882; }}
QPushButton:pressed {{ background: #0d6b50; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: transparent; width: 3px; border-radius: 2px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(29,158,117,0.20);
    border-radius: 2px; min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QLabel {{ background: transparent; border: none; }}
QToolTip {{
    background: #141e1a;
    color: {cls.text};
    border: 0.5px solid rgba(29,158,117,0.22);
    border-radius: 6px;
    padding: 5px 9px;
    font-size: 11px;
}}
"""


# ═══════════════════════════════════════════════════════════════════════════════
#  STATIC DATA
# ═══════════════════════════════════════════════════════════════════════════════

ARABIC: dict[str, str] = {
    "Fajr": "الفجر", "Sunrise": "الشروق",
    "Dhuhr": "الظهر", "Asr": "العصر",
    "Maghrib": "المغرب", "Isha": "العشاء",
}

PRAYER_COLORS: dict[str, dict] = {
    "Fajr":    {"stroke": "#7aabdb", "bg": "#0d1a26"},
    "Sunrise": {"stroke": "#d4a54a", "bg": "#1e1406"},
    "Dhuhr":   {"stroke": "#1D9E75", "bg": "#071a10"},
    "Asr":     {"stroke": "#c88040", "bg": "#1a0e06"},
    "Maghrib": {"stroke": "#cc6868", "bg": "#1a0808"},
    "Isha":    {"stroke": "#9878cc", "bg": "#0e0818"},
}

MADHAB_INFO: dict[str, str] = {
    "Hanafi":  "Central Asia, Turkey, South Asia",
    "Shafi":   "Southeast Asia, East Africa",
    "Maliki":  "North & West Africa",
    "Hanbali": "Gulf countries",
}

METHOD_INFO: dict[str, str] = {
    "MWL":     "Muslim World League · Europe & Far East",
    "Karachi": "Univ. of Islamic Sciences · South Asia",
    "ISNA":    "Islamic Society of North America",
    "Egypt":   "Egyptian General Authority",
    "Makkah":  "Umm Al-Qura · Saudi Arabia",
    "Tehran":  "Tehran / IIIS · Central Asia",
    "Diyanet": "Diyanet (Turkey)",
    "Morocco": "Morocco",
}

LANG_NAMES: dict[str, str] = {"en": "English", "ru": "Русский", "kg": "Кыргызча"}
LANG_CODES: dict[str, str] = {v: k for k, v in LANG_NAMES.items()}

T: dict[str, dict] = {
    "en": {
        "Fajr": "Fajr", "Sunrise": "Sunrise", "Dhuhr": "Dhuhr",
        "Asr": "Asr", "Maghrib": "Maghrib", "Isha": "Isha",
        "settings": "Settings", "location": "Location",
        "auto_detect": "Auto-detect my location",
        "city": "City", "country": "Country",
        "madhab": "Madhab", "method": "Calculation method",
        "save_apply": "Save & Apply", "language": "Language",
        "next_prayer": "Next prayer", "current_prayer": "Currently",
        "open_waqt": "Open Waqt", "prayer_times_menu": "Prayer times",
        "show_overlay": "Show overlay", "quit": "Quit",
        "overlay_widget": "Overlay widget", "notifications": "Notifications",
        "alert_before": "Alert before prayer", "background": "Background image",
        "choose_image": "Choose image…", "overlay_style": "Overlay style",
        "themes": "Themes", "auto_active": "Auto-detect ON — fields locked",
        "off": "Off", "refresh": "Refresh",
        "no_data": "Could not load prayer times.",
        # Sidebar labels
        "sidebar_settings": "Settings",
        "sidebar_overlay":  "Overlay",
        "sidebar_alerts":   "Alerts",
        "sidebar_calendar": "Calendar",
        "sidebar_themes":   "Themes",
        # Panel headers
        "panel_alerts":    "ALERTS",
        "panel_overlay":   "OVERLAY",
        "panel_style":     "STYLE",
        "panel_calendar":  "CALENDAR",
        "panel_themes":    "THEMES",
        "panel_per_prayer":"PER PRAYER",
        "panel_azan_sound":"AZAN SOUND",
        "show_overlay_lbl":"Show overlay",
        "azan_play_lbl":   "Play sound at prayer time",
        "azan_volume_lbl": "Volume",
        "notif_lbl":       "Notifications",
        "autostart": "Launch at startup",
        "hijri_months": ["", "Muharram", "Safar", "Rabi al-Awwal", "Rabi al-Thani",
            "Jumada al-Awwal", "Jumada al-Thani", "Rajab", "Shaban",
            "Ramadan", "Shawwal", "Dhu al-Qidah", "Dhu al-Hijjah"],
    },
    "ru": {
        "Fajr": "Фаджр", "Sunrise": "Восход", "Dhuhr": "Зухр",
        "Asr": "Аср", "Maghrib": "Магриб", "Isha": "Иша",
        "settings": "Настройки", "location": "Местоположение",
        "auto_detect": "Определить автоматически",
        "city": "Город", "country": "Страна",
        "madhab": "Мазхаб", "method": "Метод расчёта",
        "save_apply": "Сохранить и применить", "language": "Язык",
        "next_prayer": "Следующий намаз", "current_prayer": "Сейчас",
        "open_waqt": "Открыть Waqt", "prayer_times_menu": "Времена намаза",
        "show_overlay": "Показать виджет", "quit": "Выйти",
        "overlay_widget": "Overlay виджет", "notifications": "Уведомления",
        "alert_before": "Оповестить за", "background": "Фоновое изображение",
        "choose_image": "Выбрать изображение…", "overlay_style": "Стиль overlay",
        "themes": "Темы", "auto_active": "Авто-определение ВКЛ",
        "off": "Выкл", "refresh": "Обновить",
        "no_data": "Не удалось загрузить времена намаза.",
        # Sidebar labels
        "sidebar_settings": "Настройки",
        "sidebar_overlay":  "Оверлей",
        "sidebar_alerts":   "Алерты",
        "sidebar_calendar": "Календарь",
        "sidebar_themes":   "Темы",
        # Panel headers
        "panel_alerts":    "АЛЕРТЫ",
        "panel_overlay":   "ОВЕРЛЕЙ",
        "panel_style":     "СТИЛЬ",
        "panel_calendar":  "КАЛЕНДАРЬ",
        "panel_themes":    "ТЕМЫ",
        "panel_per_prayer":"ПО НАМАЗУ",
        "panel_azan_sound":"ЗВУК АЗАНА",
        "show_overlay_lbl":"Показать виджет",
        "azan_play_lbl":   "Играть звук при намазе",
        "azan_volume_lbl": "Громкость",
        "notif_lbl":       "Уведомления",
        "autostart": "Запускать при старте Windows",
        "hijri_months": ["", "Мухаррам", "Сафар", "Раби аль-Авваль", "Раби ас-Сани",
            "Джумада аль-Уля", "Джумада ас-Сания", "Раджаб", "Шаабан",
            "Рамадан", "Шавваль", "Зуль-Каада", "Зуль-Хиджа"],
    },
    "kg": {
        "Fajr": "Багымдат", "Sunrise": "Күн чыгуу", "Dhuhr": "Бешим",
        "Asr": "Аср", "Maghrib": "Шам", "Isha": "Куптан",
        "settings": "Жөндөөлөр", "location": "Жайгашуу",
        "auto_detect": "Автоматтык аныктоо",
        "city": "Шаар", "country": "Өлкө",
        "madhab": "Мазхаб", "method": "Эсептөө ыкмасы",
        "save_apply": "Сактоо жана колдонуу", "language": "Тил",
        "next_prayer": "Кийинки намаз", "current_prayer": "Учурда",
        "open_waqt": "Waqt ачуу", "prayer_times_menu": "Намаз убактылары",
        "show_overlay": "Виджетти көрсөтүү", "quit": "Чыгуу",
        "overlay_widget": "Overlay виджет", "notifications": "Эскертмелер",
        "alert_before": "Мурун эскертүү", "background": "Фон сүрөт",
        "choose_image": "Сүрөт тандоо…", "overlay_style": "Overlay стили",
        "themes": "Темалар", "auto_active": "Авто аныктоо ИШТЕП жатат",
        "off": "Өчүр", "refresh": "Жаңыртуу",
        "no_data": "Намаз убактыларын жүктөй алган жок.",
        # Sidebar labels
        "sidebar_settings": "Жөндөө",
        "sidebar_overlay":  "Виджет",
        "sidebar_alerts":   "Эскертме",
        "sidebar_calendar": "Күнтизме",
        "sidebar_themes":   "Темалар",
        # Panel headers
        "panel_alerts":    "ЭСКЕРТМЕЛЕР",
        "panel_overlay":   "ВИДЖЕТ",
        "panel_style":     "СТИЛЬ",
        "panel_calendar":  "КҮНТИЗМЕ",
        "panel_themes":    "ТЕМАЛАР",
        "panel_per_prayer":"НАМАЗ БОЮНЧА",
        "panel_azan_sound":"АЗАН УНУ",
        "show_overlay_lbl":"Виджетти көрсөтүү",
        "azan_play_lbl":   "Намазда үн чыгаруу",
        "azan_volume_lbl": "Үн күчү",
        "notif_lbl":       "Эскертмелер",
        "autostart": "Windows менен кошо иштетүү",
        "hijri_months": ["", "Мухаррам", "Сафар", "Раби аль-Авваль", "Раби ас-Сани",
            "Джумада аль-Уля", "Джумада ас-Сания", "Раджаб", "Шаабан",
            "Рамадан", "Шавваль", "Зул-Каада", "Зул-Хиджа"],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
#  TRANSLATION HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def _t(lang: str, key: str) -> str:
    return T.get(lang, T["en"]).get(key, T["en"].get(key, key))


# ═══════════════════════════════════════════════════════════════════════════════
#  DATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _hijri_date(lang: str = "en") -> str:
    g = date.today()
    y, m, d = g.year, g.month, g.day
    if m < 3:
        y -= 1; m += 12
    a = y // 100; b = 2 - a + a // 4
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5
    l2 = jd - 1948438.5 + 0.5
    n  = int(l2 / 29.53058)
    hy = n // 12 + 1
    hm = n % 12 + 1
    hd = max(1, min(30, int(l2 - (29.53058 * n + 1948438.5)) + 1))
    months = T.get(lang, T["en"])["hijri_months"]
    mn = months[hm] if 1 <= hm <= 12 else ""
    return f"{hd} {mn} {hy}"


def _localized_date(lang: str) -> str:
    today = date.today()
    d, m, yr = today.day, today.month, today.year
    wd = today.weekday()
    if lang == "ru":
        days = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
        mo   = ["","янв","фев","мар","апр","май","июн","июл","авг","сен","окт","ноя","дек"]
        return f"{days[wd]}, {d} {mo[m]} {yr}"
    if lang == "kg":
        days = ["Дүйшөмбү","Шейшемби","Шаршемби","Бейшемби","Жума","Ишемби","Жекшемби"]
        mo   = ["","янв","фев","мар","апр","май","июн","июл","авг","сен","окт","ноя","дек"]
        return f"{days[wd]}, {d} {mo[m]} {yr}"
    return today.strftime("%A, %d %B %Y")


# ═══════════════════════════════════════════════════════════════════════════════
#  UI FACTORIES
# ═══════════════════════════════════════════════════════════════════════════════

def _sec_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "color: rgba(212,232,216,0.30);"
        "font-size: 10px;"
        "letter-spacing: .08em;"
        "font-weight: 500;"
    )
    return lbl


def _divider() -> QWidget:
    d = QWidget()
    d.setFixedHeight(1)
    d.setStyleSheet("background: rgba(255,255,255,0.05);")
    return d