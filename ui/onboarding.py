"""
onboarding.py — First-run wizard for Waqt.

5 steps:
  1. Language selection  — cards in native language
  2. Location           — auto-detect or manual
  3. Madhab + Method    — plain-language descriptions, no jargon
  4. Sound preference   — Off / Azan / Voice / Custom
  5. Done               — summary + launch

Design: full-screen overlay on top of the main window.
Each step slides in from the right.
"""
from __future__ import annotations

import os
import sys

from PyQt6.QtCore import (
    QThread, Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QRect, pyqtSignal, QPoint,
)
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont,
    QLinearGradient, QPainterPath, QPixmap,
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QScrollArea, QApplication,
)

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
from core.settings import save


# ── Translations for onboarding steps ─────────────────────────────────────────

OB = {
    "en": {
        "welcome":     "Welcome to Waqt",
        "welcome_sub": "Prayer times, beautifully simple",
        "choose_lang": "Choose your language",
        "location":    "Where are you?",
        "location_sub":"We need your city for accurate prayer times",
        "auto_detect": "Detect automatically",
        "detecting":   "Detecting…",
        "detected":    "Detected:",
        "city_hint":   "Enter city name",
        "country_hint":"Enter country",
        "madhab":      "Your school of thought",
        "madhab_sub":  "This affects Asr prayer time calculation",
        "sound":       "Notification sound",
        "sound_sub":   "How should we alert you at prayer time?",
        "done":        "You're all set!",
        "done_sub":    "Waqt will now show accurate prayer times for your location.",
        "next":        "Continue",
        "back":        "Back",
        "finish":      "Start Waqt",
        "skip":        "Skip",
        "sound_off":   "Silent",
        "sound_off_d": "Notifications only, no sound",
        "sound_azan":  "Azan",
        "sound_azan_d":"Traditional call to prayer",
        "sound_voice": "Voice reminder",
        "sound_voice_d":"'Time to pray' announcement",
        "sound_custom":"Custom sound",
        "sound_custom_d":"Choose your own audio file",
        "step":        "Step",
        "of":          "of",
    },
    "ru": {
        "welcome":     "Добро пожаловать в Waqt",
        "welcome_sub": "Времена намаза — просто и красиво",
        "choose_lang": "Выберите язык",
        "location":    "Где вы находитесь?",
        "location_sub":"Нам нужен ваш город для точного времени намаза",
        "auto_detect": "Определить автоматически",
        "detecting":   "Определяем…",
        "detected":    "Найдено:",
        "city_hint":   "Введите город",
        "country_hint":"Введите страну",
        "madhab":      "Ваш мазхаб",
        "madhab_sub":  "Влияет на расчёт времени намаза Аср",
        "sound":       "Звук уведомления",
        "sound_sub":   "Как вас оповещать о времени намаза?",
        "done":        "Всё готово!",
        "done_sub":    "Waqt покажет точные времена намаза для вашего местоположения.",
        "next":        "Далее",
        "back":        "Назад",
        "finish":      "Запустить Waqt",
        "skip":        "Пропустить",
        "sound_off":   "Без звука",
        "sound_off_d": "Только уведомления",
        "sound_azan":  "Азан",
        "sound_azan_d":"Традиционный призыв на намаз",
        "sound_voice": "Голосовое напоминание",
        "sound_voice_d":"Объявление «Время намаза»",
        "sound_custom":"Свой звук",
        "sound_custom_d":"Выбрать свой аудиофайл",
        "step":        "Шаг",
        "of":          "из",
    },
    "kg": {
        "welcome":     "Waqt'ка кош келиңиз",
        "welcome_sub": "Намаз убактылары — жөнөкөй жана сонун",
        "choose_lang": "Тилди тандаңыз",
        "location":    "Кайда жайгашасыз?",
        "location_sub":"Так намаз убактысы үчүн шааңызды билишибиз керек",
        "auto_detect": "Автоматтык аныктоо",
        "detecting":   "Аныкталууда…",
        "detected":    "Табылды:",
        "city_hint":   "Шаар атын киргизиңиз",
        "country_hint":"Өлкөнү киргизиңиз",
        "madhab":      "Мазхабыңыз",
        "madhab_sub":  "Аср намазынын убактысын эсептөөгө таасир этет",
        "sound":       "Эскертме үнү",
        "sound_sub":   "Намаз убактысы келгенде кантип эскертели?",
        "done":        "Баары даяр!",
        "done_sub":    "Waqt жайгашкан жериңиз үчүн так намаз убактыларын көрсөтөт.",
        "next":        "Улантуу",
        "back":        "Артка",
        "finish":      "Waqt баштоо",
        "skip":        "Өткөрүп жиберүү",
        "sound_off":   "Үнсүз",
        "sound_off_d": "Билдирүүлөр гана",
        "sound_azan":  "Азан",
        "sound_azan_d":"Салттуу намазга чакыруу",
        "sound_voice": "Үн эскертмеси",
        "sound_voice_d":"«Намаз убактысы» жарыясы",
        "sound_custom":"Өз үнүңүз",
        "sound_custom_d":"Өз аудио файлыңызды тандаңыз",
        "step":        "Кадам",
        "of":          "/",
    },
}

MADHAB_CARDS = [
    ("Hanafi",  "Hanafi",  "Central Asia, Turkey, South Asia\nHanafi, Ханафи, حنفي"),
    ("Shafi",   "Shafi'i", "Southeast Asia, East Africa\nШафии, شافعي"),
    ("Maliki",  "Maliki",  "North & West Africa\nМалики, مالكي"),
    ("Hanbali", "Hanbali", "Gulf countries\nХанбали, حنبلي"),
]

LANGUAGE_CARDS = [
    ("en", "English",   "English"),
    ("ru", "Русский",   "Russian"),
    ("kg", "Кыргызча", "Kyrgyz"),
]


# ── Helper widgets ─────────────────────────────────────────────────────────────

def _btn(text: str, accent: bool = True, w: int = 160, h: int = 42) -> QPushButton:
    b = QPushButton(text)
    b.setFixedSize(w, h)
    if accent:
        b.setStyleSheet("""
            QPushButton{background:#1D9E75;color:#fff;border:none;
                border-radius:10px;font-size:13px;font-weight:600;}
            QPushButton:hover{background:#1cb882;}
            QPushButton:pressed{background:#148a5e;}
        """)
    else:
        b.setStyleSheet("""
            QPushButton{background:rgba(255,255,255,0.07);
                color:rgba(212,232,216,0.6);
                border:0.5px solid rgba(255,255,255,0.1);
                border-radius:10px;font-size:13px;}
            QPushButton:hover{background:rgba(255,255,255,0.12);
                color:rgba(212,232,216,0.9);}
        """)
    return b


class SelectCard(QWidget):
    """Selectable option card used for language, madhab, sound."""
    selected = pyqtSignal(str)   # emits the key

    def __init__(self, key: str, title: str, subtitle: str = "",
                 icon: str = "", active: bool = False):
        super().__init__()
        self._key    = key
        self._active = active
        self._hover  = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(66)

        lo = QHBoxLayout(self)
        lo.setContentsMargins(16, 0, 16, 0)
        lo.setSpacing(14)

        # Icon circle
        if icon:
            ic = QLabel(icon)
            ic.setFixedSize(36, 36)
            ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ic.setStyleSheet(
                "background:rgba(29,158,117,0.12);"
                "border-radius:18px;font-size:18px;")
            lo.addWidget(ic)

        # Text
        tw = QWidget(); tw.setStyleSheet("background:transparent;")
        tv = QVBoxLayout(tw); tv.setContentsMargins(0,0,0,0); tv.setSpacing(2)

        tl = QLabel(title)
        tl.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
        tl.setStyleSheet("color:#f0f8f4;background:transparent;")
        tv.addWidget(tl)

        if subtitle:
            sl = QLabel(subtitle)
            sl.setStyleSheet(
                "color:rgba(212,232,216,0.45);font-size:10px;background:transparent;")
            tv.addWidget(sl)

        lo.addWidget(tw, 1)

        # Active dot
        self._dot = QWidget()
        self._dot.setFixedSize(18, 18)
        self._dot.setStyleSheet(
            "background:#1D9E75;border-radius:9px;" if active else
            "background:transparent;border:1.5px solid rgba(255,255,255,0.2);"
            "border-radius:9px;")
        lo.addWidget(self._dot)

    def setActive(self, v: bool):
        self._active = v
        self._dot.setStyleSheet(
            "background:#1D9E75;border-radius:9px;" if v else
            "background:transparent;border:1.5px solid rgba(255,255,255,0.2);"
            "border-radius:9px;")
        self.update()

    def enterEvent(self, e): self._hover = True;  self.update()
    def leaveEvent(self, e): self._hover = False; self.update()
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self._key)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        if self._active:
            p.setBrush(QBrush(QColor(29, 158, 117, 28)))
            p.setPen(QPen(QColor(29, 158, 117, 140), 1.0))
        elif self._hover:
            p.setBrush(QBrush(QColor(255, 255, 255, 10)))
            p.setPen(QPen(QColor(255, 255, 255, 30), 0.5))
        else:
            p.setBrush(QBrush(QColor(255, 255, 255, 5)))
            p.setPen(QPen(QColor(255, 255, 255, 14), 0.5))
        p.drawRoundedRect(QRect(0, 0, w, h), 12, 12)


class ProgressDots(QWidget):
    """Step indicator dots at the bottom of wizard."""
    def __init__(self, total: int, current: int = 0):
        super().__init__()
        self._total   = total
        self._current = current
        self.setFixedHeight(16)

    def set_current(self, n: int): self._current = n; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        dot_r = 4; gap = 14
        total_w = self._total * (dot_r * 2) + (self._total - 1) * gap
        sx = (w - total_w) // 2
        for i in range(self._total):
            x = sx + i * (dot_r * 2 + gap)
            if i == self._current:
                p.setBrush(QBrush(QColor("#1D9E75")))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(x - 2, 4, dot_r * 2 + 4, dot_r * 2 + 4)
            else:
                p.setBrush(QBrush(QColor(255, 255, 255, 40)))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(x, 5, dot_r * 2, dot_r * 2)


# ── Individual step pages ──────────────────────────────────────────────────────

class _BasePage(QWidget):
    """Common layout: title area + content + nav buttons."""

    next_clicked = pyqtSignal()
    back_clicked = pyqtSignal()

    def __init__(self, lang: str = "en", show_back: bool = True,
                 next_label_key: str = "next"):
        super().__init__()
        self._lang = lang
        self.setStyleSheet("background:transparent;")

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(40, 32, 40, 24)
        self._root.setSpacing(0)

        # Content area (subclasses fill this)
        self._content = QVBoxLayout()
        self._content.setSpacing(0)
        self._root.addLayout(self._content, 1)

        # Nav row
        nav = QHBoxLayout(); nav.setSpacing(12)
        if show_back:
            self._back_btn = _btn(OB[lang].get("back", "Back"), accent=False, w=100)
            self._back_btn.clicked.connect(self.back_clicked)
            nav.addWidget(self._back_btn)
        nav.addStretch()
        self._next_btn = _btn(OB[lang].get(next_label_key, "Continue"), w=160)
        self._next_btn.clicked.connect(self.next_clicked)
        nav.addWidget(self._next_btn)
        self._root.addLayout(nav)

    def _t(self, key: str) -> str:
        return OB.get(self._lang, OB["en"]).get(key, key)

    def _section_title(self, title_key: str, sub_key: str = "") -> QVBoxLayout:
        lv = QVBoxLayout(); lv.setSpacing(6)
        tl = QLabel(self._t(title_key))
        tl.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        tl.setStyleSheet("color:#f0f8f4;")
        lv.addWidget(tl)
        if sub_key:
            sl = QLabel(self._t(sub_key))
            sl.setStyleSheet("color:rgba(212,232,216,0.45);font-size:12px;")
            sl.setWordWrap(True)
            lv.addWidget(sl)
        lv.addSpacing(20)
        return lv


class WelcomePage(_BasePage):
    def __init__(self, lang: str = "en"):
        super().__init__(lang, show_back=False, next_label_key="next")
        t = OB.get(lang, OB["en"])

        # Crescent logo
        logo = _CrescentLogo(); logo.setFixedSize(80, 80)
        self._content.addStretch(1)
        logo_row = QHBoxLayout(); logo_row.addStretch(); logo_row.addWidget(logo); logo_row.addStretch()
        self._content.addLayout(logo_row)
        self._content.addSpacing(24)

        title = QLabel(t["welcome"])
        title.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        title.setStyleSheet("color:#f0f8f4;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content.addWidget(title)
        self._content.addSpacing(8)

        sub = QLabel(t["welcome_sub"])
        sub.setStyleSheet("color:rgba(212,232,216,0.45);font-size:14px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content.addWidget(sub)
        self._content.addStretch(2)

        # Override nav: centered single button
        self._root.itemAt(1).layout().itemAt(0).widget().hide()  # hide back placeholder
        self._next_btn.setFixedWidth(200)


class LanguagePage(_BasePage):
    lang_selected = pyqtSignal(str)

    def __init__(self, lang: str = "en", current: str = "en"):
        super().__init__(lang, show_back=False)
        self._chosen = current
        self._cards: dict[str, SelectCard] = {}

        for lv in self._section_title("choose_lang").children():
            if isinstance(lv, QLabel): self._content.addWidget(lv)
        lv = self._section_title("choose_lang")
        cnt = lv.count()
        for i in range(cnt):
            item = lv.itemAt(i)
            if item and item.widget():
                self._content.addWidget(item.widget())

        # Language cards in a 3-column row
        cards_row = QHBoxLayout(); cards_row.setSpacing(10)
        for code, native, english in LANGUAGE_CARDS:
            card = _LangCard(code, native, english, active=(code == current))
            card.selected.connect(self._on_select)
            self._cards[code] = card
            cards_row.addWidget(card)
        self._content.addLayout(cards_row)
        self._content.addStretch()

    def _on_select(self, code: str):
        for k, c in self._cards.items():
            c.setActive(k == code)
        self._chosen = code
        self.lang_selected.emit(code)

    def chosen(self) -> str: return self._chosen


class _LangCard(QWidget):
    selected = pyqtSignal(str)

    def __init__(self, code: str, native: str, english: str, active: bool = False):
        super().__init__()
        self._code   = code
        self._active = active
        self._hover  = False
        self.setFixedSize(100, 100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lo = QVBoxLayout(self); lo.setContentsMargins(8, 12, 8, 12); lo.setSpacing(4)
        lo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        nl = QLabel(native)
        nl.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        nl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nl.setStyleSheet("color:#f0f8f4;background:transparent;")

        el = QLabel(english)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.setStyleSheet("color:rgba(212,232,216,0.45);font-size:10px;background:transparent;")

        lo.addStretch(); lo.addWidget(nl); lo.addWidget(el); lo.addStretch()

    def setActive(self, v: bool): self._active = v; self.update()
    def enterEvent(self, e): self._hover = True;  self.update()
    def leaveEvent(self, e): self._hover = False; self.update()
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self._code)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        if self._active:
            p.setBrush(QBrush(QColor(29, 158, 117, 35)))
            p.setPen(QPen(QColor(29, 158, 117, 200), 1.5))
        elif self._hover:
            p.setBrush(QBrush(QColor(255, 255, 255, 12)))
            p.setPen(QPen(QColor(255, 255, 255, 40), 0.5))
        else:
            p.setBrush(QBrush(QColor(255, 255, 255, 6)))
            p.setPen(QPen(QColor(255, 255, 255, 20), 0.5))
        p.drawRoundedRect(0, 0, w, h, 14, 14)


class LocationPage(_BasePage):
    def __init__(self, lang: str = "en", city: str = "", country: str = ""):
        super().__init__(lang)
        self._worker = None

        hdr = self._section_title("location", "location_sub")
        for i in range(hdr.count()):
            item = hdr.itemAt(i)
            if item and item.widget(): self._content.addWidget(item.widget())

        # Auto-detect button
        self._auto_btn = _btn("  ⊙  " + self._t("auto_detect"), accent=False, w=240, h=40)
        self._auto_btn.setStyleSheet("""
            QPushButton{background:rgba(29,158,117,0.12);color:#1D9E75;
                border:1px solid rgba(29,158,117,0.35);border-radius:10px;
                font-size:13px;text-align:left;padding-left:16px;}
            QPushButton:hover{background:rgba(29,158,117,0.2);
                border-color:rgba(29,158,117,0.6);}
        """)
        self._auto_btn.clicked.connect(self._do_detect)
        self._content.addWidget(self._auto_btn)
        self._content.addSpacing(10)

        # Status label
        self._status = QLabel("")
        self._status.setStyleSheet("color:#1D9E75;font-size:11px;")
        self._content.addWidget(self._status)
        self._content.addSpacing(10)

        # Manual fields
        self._city_edit = QLineEdit(city)
        self._city_edit.setPlaceholderText(self._t("city_hint"))
        self._city_edit.setFixedHeight(40)
        self._city_edit.setStyleSheet("""
            QLineEdit{background:rgba(255,255,255,0.06);color:#f0f8f4;
                border:0.5px solid rgba(255,255,255,0.12);border-radius:10px;
                padding:0 14px;font-size:13px;}
            QLineEdit:focus{border:0.5px solid rgba(29,158,117,0.5);}
        """)
        self._content.addWidget(self._city_edit)
        self._content.addSpacing(8)

        self._country_edit = QLineEdit(country)
        self._country_edit.setPlaceholderText(self._t("country_hint"))
        self._country_edit.setFixedHeight(40)
        self._country_edit.setStyleSheet(self._city_edit.styleSheet())
        self._content.addWidget(self._country_edit)
        self._content.addStretch()

    def _do_detect(self):
        self._auto_btn.setText("  ⟳  " + self._t("detecting"))
        self._auto_btn.setEnabled(False)

        class _W(QThread):
            done   = pyqtSignal(dict)
            failed = pyqtSignal()
            def run(self_):
                try:
                    from core.location import get_location_by_ip
                    loc = get_location_by_ip()
                    if loc.get("city"): self_.done.emit(loc)
                    else: self_.failed.emit()
                except Exception: self_.failed.emit()

        self._worker = _W()
        self._worker.done.connect(self._on_detected)
        self._worker.failed.connect(self._on_fail)
        self._worker.start()

    def _on_detected(self, loc: dict):
        city    = loc.get("city", "")
        country = loc.get("country", "")
        self._city_edit.setText(city)
        self._country_edit.setText(country)
        self._status.setText(
            f"✓  {self._t('detected')} {city}, {country}")
        self._auto_btn.setText("  ✓  " + city)
        self._auto_btn.setEnabled(True)

    def _on_fail(self):
        self._auto_btn.setText("  ⊙  " + self._t("auto_detect"))
        self._auto_btn.setEnabled(True)
        self._status.setText("⚠  Could not detect. Enter manually.")
        self._status.setStyleSheet("color:rgba(220,100,80,0.8);font-size:11px;")

    def get_city(self)    -> str: return self._city_edit.text().strip()
    def get_country(self) -> str: return self._country_edit.text().strip()


class MadhabPage(_BasePage):
    def __init__(self, lang: str = "en", current: str = "Hanafi"):
        super().__init__(lang)
        self._chosen = current
        self._cards: dict[str, SelectCard] = {}

        hdr = self._section_title("madhab", "madhab_sub")
        for i in range(hdr.count()):
            item = hdr.itemAt(i)
            if item and item.widget(): self._content.addWidget(item.widget())

        for key, title, subtitle in MADHAB_CARDS:
            card = SelectCard(key, title, subtitle, active=(key == current))
            card.selected.connect(self._on_select)
            self._cards[key] = card
            self._content.addWidget(card)
            self._content.addSpacing(6)
        self._content.addStretch()

    def _on_select(self, key: str):
        for k, c in self._cards.items(): c.setActive(k == key)
        self._chosen = key

    def chosen(self) -> str: return self._chosen


class SoundPage(_BasePage):
    """Sound preference: Off / Azan / Voice / Custom."""

    def __init__(self, lang: str = "en", current: str = "off"):
        super().__init__(lang)
        self._chosen = current
        self._cards: dict[str, SelectCard] = {}

        hdr = self._section_title("sound", "sound_sub")
        for i in range(hdr.count()):
            item = hdr.itemAt(i)
            if item and item.widget(): self._content.addWidget(item.widget())

        options = [
            ("off",    "🔕", self._t("sound_off"),    self._t("sound_off_d")),
            ("azan",   "🕌", self._t("sound_azan"),   self._t("sound_azan_d")),
            ("voice",  "🗣", self._t("sound_voice"),  self._t("sound_voice_d")),
            ("custom", "📁", self._t("sound_custom"), self._t("sound_custom_d")),
        ]
        for key, icon, title, subtitle in options:
            card = SelectCard(key, title, subtitle, icon=icon,
                              active=(key == current))
            card.selected.connect(self._on_select)
            self._cards[key] = card
            self._content.addWidget(card)
            self._content.addSpacing(6)
        self._content.addStretch()

    def _on_select(self, key: str):
        for k, c in self._cards.items(): c.setActive(k == key)
        self._chosen = key

    def chosen(self) -> str: return self._chosen


class DonePage(_BasePage):
    def __init__(self, lang: str = "en", city: str = "", madhab: str = ""):
        super().__init__(lang, show_back=False, next_label_key="finish")
        t = OB.get(lang, OB["en"])

        self._content.addStretch(1)

        check = _CheckMark(); check.setFixedSize(72, 72)
        row = QHBoxLayout(); row.addStretch(); row.addWidget(check); row.addStretch()
        self._content.addLayout(row)
        self._content.addSpacing(20)

        tl = QLabel(t["done"])
        tl.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        tl.setStyleSheet("color:#f0f8f4;")
        tl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content.addWidget(tl)
        self._content.addSpacing(8)

        sl = QLabel(t["done_sub"])
        sl.setStyleSheet("color:rgba(212,232,216,0.45);font-size:12px;")
        sl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.setWordWrap(True)
        self._content.addWidget(sl)
        self._content.addSpacing(16)

        if city:
            info = QLabel(f"📍 {city}   ·   🕌 {madhab}")
            info.setStyleSheet(
                "color:#1D9E75;font-size:12px;letter-spacing:.03em;")
            info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._content.addWidget(info)

        self._content.addStretch(2)
        self._next_btn.setFixedWidth(200)


class _CrescentLogo(QWidget):
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height(); cx, cy = w/2, h/2
        outer = QPainterPath(); outer.addEllipse(QPoint(int(cx), int(cy)), int(w*.44), int(h*.44))
        inner = QPainterPath(); inner.addEllipse(QPoint(int(cx+w*.18), int(cy-h*.04)), int(w*.33), int(h*.33))
        p.setBrush(QBrush(QColor("#1D9E75"))); p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(outer.subtracted(inner))


class _CheckMark(QWidget):
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height(); cx, cy = w/2, h/2; r = min(w,h)/2 - 2
        p.setBrush(QBrush(QColor(29, 158, 117, 40))); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPoint(int(cx), int(cy)), int(r), int(r))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor("#1D9E75"), 3.0, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawLine(int(cx - r*.35), int(cy), int(cx - r*.02), int(cy + r*.38))
        p.drawLine(int(cx - r*.02), int(cy + r*.38), int(cx + r*.42), int(cy - r*.3))


# ── Main Wizard ────────────────────────────────────────────────────────────────

class OnboardingWizard(QWidget):
    """
    Full-screen overlay wizard. Parent should be MainWindow.
    Emits finished(settings_dict) when user completes all steps.
    """
    finished = pyqtSignal(dict)

    STEPS = 6   # Welcome, Language, Location, Madhab, Sound, Done

    def __init__(self, settings: dict, parent: QWidget = None):
        super().__init__(parent)
        self._s    = settings
        self._lang = settings.get("language", "en")
        self._step = 0
        self._pages: list[QWidget] = []

        # Cover the parent window completely
        if parent:
            self.setGeometry(parent.rect())
        self.setStyleSheet("background:transparent;")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)

        # Card container
        self._card = QWidget()
        self._card.setStyleSheet("")
        self._card_layout = QVBoxLayout(self._card)
        self._card_layout.setContentsMargins(0, 0, 0, 0)

        card_row = QHBoxLayout()
        card_row.addStretch()
        card_row.addWidget(self._card)
        card_row.addStretch()

        self._root.addStretch()
        self._root.addLayout(card_row)

        # Progress dots
        self._dots = ProgressDots(self.STEPS, 0)
        dot_row = QHBoxLayout(); dot_row.addStretch()
        dot_row.addWidget(self._dots); dot_row.addStretch()
        self._root.addLayout(dot_row)
        self._root.addSpacing(16)
        self._root.addStretch()

        self._build_pages()
        self._show_step(0)

    def resizeEvent(self, e):
        if self.parent():
            self.setGeometry(self.parent().rect())
        super().resizeEvent(e)

    def _build_pages(self):
        self._pages = [
            WelcomePage(self._lang),
            LanguagePage(self._lang, self._lang),
            LocationPage(self._lang,
                         self._s.get("city", ""),
                         self._s.get("country", "")),
            MadhabPage(self._lang, self._s.get("madhab", "Hanafi")),
            SoundPage(self._lang, self._s.get("azan_mode", "off")),
            DonePage(self._lang,
                     self._s.get("city", ""),
                     self._s.get("madhab", "Hanafi")),
        ]
        # Connect language page
        self._pages[1].lang_selected.connect(self._on_lang_change)
        # Wire next/back
        for i, page in enumerate(self._pages):
            if hasattr(page, "next_clicked"):
                page.next_clicked.connect(lambda _=None, n=i: self._advance(n))
            if hasattr(page, "back_clicked"):
                page.back_clicked.connect(lambda _=None, n=i: self._go_back(n))

    def _show_step(self, idx: int):
        # Remove old page
        while self._card_layout.count():
            item = self._card_layout.takeAt(0)
            if item.widget(): item.widget().hide()

        self._step = idx
        self._dots.set_current(idx)
        page = self._pages[idx]
        self._card.setFixedSize(460, 480)
        self._card_layout.addWidget(page)
        page.show()

    def _advance(self, from_step: int):
        # Save data from each step before advancing
        step = self._pages[from_step]
        if isinstance(step, LanguagePage):
            self._lang = step.chosen()
            self._s["language"] = self._lang
        elif isinstance(step, LocationPage):
            city    = step.get_city()
            country = step.get_country()
            if city:    self._s["city"]    = city
            if country: self._s["country"] = country
        elif isinstance(step, MadhabPage):
            self._s["madhab"] = step.chosen()
        elif isinstance(step, SoundPage):
            mode = step.chosen()
            self._s["azan_mode"]  = mode
            self._s["azan_sound"] = (mode != "off")

        next_idx = from_step + 1
        if next_idx >= self.STEPS:
            # Done
            self._s["first_run_shown"] = True
            save(self._s)
            self.finished.emit(self._s)
            self.hide()
        else:
            # Rebuild Done page with updated city/madhab
            if next_idx == self.STEPS - 1:
                self._pages[-1] = DonePage(
                    self._lang,
                    self._s.get("city", ""),
                    self._s.get("madhab", "Hanafi"))
                if hasattr(self._pages[-1], "next_clicked"):
                    self._pages[-1].next_clicked.connect(
                        lambda _=None, n=self.STEPS-1: self._advance(n))
            self._show_step(next_idx)

    def _go_back(self, from_step: int):
        if from_step > 0:
            self._show_step(from_step - 1)

    def _on_lang_change(self, code: str):
        self._lang = code

    def paintEvent(self, _):
        """Dark semi-transparent backdrop."""
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(0, 0, 0, 180))

        # Card shadow + background
        if self._card:
            cr = self._card.geometry()
            shadow_r = cr.adjusted(-8, -8, 8, 8)
            p.setBrush(QBrush(QColor(0, 0, 0, 60)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(shadow_r, 18, 18)
            p.setBrush(QBrush(QColor(13, 17, 23)))
            p.setPen(QPen(QColor(29, 158, 117, 55), 0.8))
            p.drawRoundedRect(cr, 16, 16)