<div align="center">

<img src="assets/icons/app_icon.png" width="120" alt="Waqt Logo"/>

# 🌙 Waqt — Prayer Times Desktop App

**A beautiful, lightweight desktop app that shows Islamic prayer times in your system tray.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.0+-41CD52?style=flat-square)](https://pypi.org/project/PyQt6/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?style=flat-square&logo=windows)](https://windows.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

[🇬🇧 English](#english) · [🇷🇺 Русский](#русский) · [🇰🇬 Кыргызча](#кыргызча)

</div>

---

## English

### ✨ Features

- 🕌 **Accurate prayer times** — powered by [Aladhan API](https://aladhan.com) with GPS-level coordinates
- 🌍 **Auto location detection** — finds your city automatically via IP
- 🖥️ **System tray integration** — lives quietly in your taskbar, shows prayer name + countdown
- 🪟 **Floating overlay** — draggable pill/card/minimal widget that stays on top
- 🔔 **Prayer notifications** — beautiful popup with illustration when it's time to pray
- 🎨 **8 color themes** — Knowledge, Sunny Town, Arctic Dawn, Iceland, Sunset, Amber & Azure and more
- 🌐 **3 languages** — English, Russian, Kyrgyz
- 🕌 **4 madhabs** — Hanafi, Shafi, Maliki, Hanbali
- ⚡ **Lightweight** — ~100 MB, no background services, minimal CPU usage

### 📸 Screenshots

<table>
<tr>
<td align="center">
<b>Main Window</b><br/>
<img src="docs/screenshots/main_display.png" width="300" alt="Main Window"/>
</td>
<td align="center">
<b>Overlay Widget</b><br/>
<img src="docs/screenshots/overlay.png" width="300" alt="Overlay"/>
</td>
</tr>
<tr>
<td align="center" colspan="2">
<b>System Tray & Notification</b><br/>
<img src="docs/screenshots/image.png" width="500" alt="Tray and Notification"/>
</td>
</tr>
</table>

### 🚀 Quick Start

**Option 1 — Download .exe (recommended)**

```
1. Download Waqt.exe from Releases
2. Double-click to run
3. App appears in system tray (bottom-right near clock)
4. Click the W icon to open settings
```

**Option 2 — Run from source**

```bash
# Install dependencies
pip install PyQt6 requests Pillow

# Run
python main.py
```

### 🔨 Build .exe yourself

```bash
pip install pyinstaller Pillow
python build.py
# Output: dist/Waqt.exe
```

### ⚙️ Settings

| Setting | Options |
|---------|---------|
| City / Country | Any city worldwide |
| Madhab | Hanafi, Shafi, Maliki, Hanbali |
| Calculation Method | MWL, ISNA, Egypt, Karachi |
| Language | EN / RU / KG |
| Overlay Style | Pill / Card / Minimal |
| Theme | 8 themes |
| Notifications | On / Off |

### 📁 Project Structure

```
Waqt/
├── main.py              # Entry point (splash screen, single instance)
├── build.py             # Build script → dist/Waqt.exe
├── core/
│   ├── prayer_times.py  # Aladhan API + coordinate resolution
│   ├── location.py      # IP-based auto location
│   └── settings.py      # JSON settings manager
├── ui/
│   ├── main_window.py   # Main application window
│   ├── overlay.py       # Floating overlay widget (3 styles)
│   ├── tray.py          # System tray icon + popup
│   ├── notification.py  # Prayer time notification popup
│   └── themes.py        # Color themes
└── assets/
    └── icons/           # App icons
```

---

## Русский

### ✨ Возможности

- 🕌 **Точное время намаза** — данные от [Aladhan API](https://aladhan.com) с точными координатами
- 🌍 **Автоопределение локации** — находит ваш город автоматически по IP
- 🖥️ **Интеграция в трей** — живёт в углу экрана, показывает название намаза и обратный отсчёт
- 🪟 **Плавающий виджет** — перетаскиваемый overlay поверх всех окон
- 🔔 **Уведомления о намазе** — красивый popup с иллюстрацией когда приходит время
- 🎨 **8 цветовых тем** — Сила знаний, Солнечный городок, Арктический рассвет и другие
- 🌐 **3 языка** — Английский, Русский, Кыргызский
- 🕌 **4 мазхаба** — Ханафи, Шафии, Малики, Ханбали

### 🚀 Быстрый старт

**Вариант 1 — скачать .exe (рекомендуется)**

```
1. Скачайте Waqt.exe из раздела Releases
2. Дважды кликните для запуска
3. Приложение появится в системном трее (правый нижний угол, рядом с часами)
4. Кликните на иконку W чтобы открыть настройки
```

**Вариант 2 — запуск из исходников**

```bash
pip install PyQt6 requests Pillow
python main.py
```

### ⚙️ Настройки

| Параметр | Варианты |
|----------|---------|
| Город / Страна | Любой город мира |
| Мазхаб | Ханафи, Шафии, Малики, Ханбали |
| Метод расчёта | MWL, ISNA, Egypt, Karachi |
| Язык | EN / RU / KG |
| Стиль Overlay | Pill / Card / Minimal |
| Тема | 8 тем |
| Уведомления | Вкл / Выкл |

### 🕌 Как работает

```
Запуск .exe
    ↓
Splash screen (загрузка)
    ↓
Автоопределение города по IP
    ↓
Загрузка времён намаза с Aladhan API
    ↓
Иконка в трее  →  клик  →  попап со всеми намазами
    +
Overlay виджет поверх всех окон (перетаскивается)
    +
Уведомление когда приходит время намаза
```

---

## Кыргызча

### ✨ Мүмкүнчүлүктөр

- 🕌 **Так намаз убактылары** — [Aladhan API](https://aladhan.com) аркылуу так координаттар менен
- 🌍 **Жайгашууну авто аныктоо** — IP аркылуу шааңызды автоматтык түрдө табат
- 🖥️ **Системалык трей** — экрандын бурчунда жашайт, намаздын атын жана убактыны көрсөтөт
- 🪟 **Калкыма виджет** — бардык терезелердин үстүндө турган виджет
- 🔔 **Намаз эскертмелери** — намаз убактысы келгенде сүрөттүү билдирүү чыгат
- 🎨 **8 түс темасы** — Билим күчү, Арктикалык таң, Күнбатыш жана башкалар
- 🌐 **3 тил** — Англисче, Орусча, Кыргызча
- 🕌 **4 мазхаб** — Ханафи, Шафии, Малики, Ханбали

### 🚀 Тез баштоо

**1-вариант — .exe жүктөө (сунушталат)**

```
1. Waqt.exe файлын Releases бөлүмүнөн жүктөңүз
2. Эки жолу чыкылдатып иштетиңиз
3. Колдонмо системалык трейде пайда болот (оң ылдый бурч)
4. Жөндөөлөрдү ачуу үчүн W сүрөтчөсүнө чыкылдатыңыз
```

**2-вариант — булак кодунан иштетүү**

```bash
pip install PyQt6 requests Pillow
python main.py
```

### ⚙️ Жөндөөлөр

| Параметр | Варианттар |
|----------|-----------|
| Шаар / Өлкө | Дүйнөнүн каалаган шаары |
| Мазхаб | Ханафи, Шафии, Малики, Ханбали |
| Эсептөө ыкмасы | MWL, ISNA, Egypt, Karachi |
| Тил | EN / RU / KG |
| Overlay стили | Pill / Card / Minimal |
| Тема | 8 тема |
| Эскертмелер | Кошулган / Өчүрүлгөн |

---

<div align="center">

### 🛠️ Tech Stack

`Python 3.10+` · `PyQt6` · `Aladhan API` · `OpenStreetMap Nominatim` · `Pillow` · `PyInstaller`

---

Made with ❤️ for the Muslim community in the World

*Пайдалуу болсо, GitHub'да ⭐ коюңуз!*

</div>
