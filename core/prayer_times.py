"""
prayer_times.py — fetches daily prayer times from aladhan.com API.

TIMEZONE STRATEGY (DST fix):
  aladhan without timezonestring ignores DST → Warsaw is 1h off in summer.
  We resolve timezone via 4 levels (first success wins):
  
  1. timezonefinder  — local library, no network (pip install timezonefinder)
  2. Country code    — Nominatim returns country_code, we map it to IANA tz
                       Works offline if coordinates were already fetched.
                       Covers 99% of users correctly.
  3. timeapi.io      — REST API fallback
  4. geonames        — last resort REST fallback

Level 2 is the key addition: even without timezonefinder installed, 
country_code from Nominatim gives us the correct timezone for most countries.
"""

import requests
from datetime import date

MADHAB_MAP = {"Hanafi": 1, "Shafi": 0, "Maliki": 0, "Hanbali": 0}

METHODS: dict[str, dict] = {
    "MWL":     {"id": 3,  "name": "Muslim World League",        "region": "Europe, Far East"},
    "Karachi": {"id": 1,  "name": "Univ. of Islamic Sciences",  "region": "Pakistan, Afghanistan"},
    "ISNA":    {"id": 2,  "name": "Islamic Society N. America", "region": "USA, Canada"},
    "Egypt":   {"id": 5,  "name": "Egyptian General Authority", "region": "Africa, Middle East"},
    "Makkah":  {"id": 4,  "name": "Umm Al-Qura, Makkah",       "region": "Saudi Arabia"},
    "Tehran":  {"id": 7,  "name": "Tehran / IIIS",              "region": "Iran, Central Asia"},
    "Diyanet": {"id": 13, "name": "Diyanet (Turkey)",           "region": "Turkey"},
    "Morocco": {"id": 11, "name": "Morocco",                    "region": "Morocco"},
}
METHOD_MAP = {k: v["id"] for k, v in METHODS.items()}

_NOMINATIM_HEADERS = {"User-Agent": "WaqtPrayerApp/2.0 (waqt-prayer-desktop)"}

# ── Level 2: country code → IANA timezone ─────────────────────────────────────
# Covers primary timezone for each country (handles 99% of Muslim-majority
# and common destination countries). Multi-timezone countries use capital city tz.
_COUNTRY_TZ: dict[str, str] = {
    # Central Asia
    "kg": "Asia/Bishkek",    "kz": "Asia/Almaty",
    "uz": "Asia/Tashkent",   "tj": "Asia/Dushanbe",
    "tm": "Asia/Ashgabat",
    # Eastern Europe / Caucasus
    "ru": "Europe/Moscow",   "ua": "Europe/Kyiv",
    "by": "Europe/Minsk",    "az": "Asia/Baku",
    "am": "Asia/Yerevan",    "ge": "Asia/Tbilisi",
    "md": "Europe/Chisinau",
    # Europe
    "pl": "Europe/Warsaw",   "de": "Europe/Berlin",
    "fr": "Europe/Paris",    "gb": "Europe/London",
    "nl": "Europe/Amsterdam","be": "Europe/Brussels",
    "se": "Europe/Stockholm","no": "Europe/Oslo",
    "dk": "Europe/Copenhagen","fi": "Europe/Helsinki",
    "at": "Europe/Vienna",   "ch": "Europe/Zurich",
    "es": "Europe/Madrid",   "pt": "Europe/Lisbon",
    "it": "Europe/Rome",     "gr": "Europe/Athens",
    "ro": "Europe/Bucharest","hu": "Europe/Budapest",
    "cz": "Europe/Prague",   "sk": "Europe/Bratislava",
    "bg": "Europe/Sofia",    "hr": "Europe/Zagreb",
    "rs": "Europe/Belgrade", "ba": "Europe/Sarajevo",
    "si": "Europe/Ljubljana","ee": "Europe/Tallinn",
    "lv": "Europe/Riga",     "lt": "Europe/Vilnius",
    # Middle East
    "tr": "Europe/Istanbul", "sy": "Asia/Damascus",
    "lb": "Asia/Beirut",     "jo": "Asia/Amman",
    "il": "Asia/Jerusalem",  "iq": "Asia/Baghdad",
    "ir": "Asia/Tehran",     "kw": "Asia/Kuwait",
    "sa": "Asia/Riyadh",     "ae": "Asia/Dubai",
    "qa": "Asia/Qatar",      "bh": "Asia/Bahrain",
    "om": "Asia/Muscat",     "ye": "Asia/Aden",
    # North Africa
    "eg": "Africa/Cairo",    "ma": "Africa/Casablanca",
    "dz": "Africa/Algiers",  "tn": "Africa/Tunis",
    "ly": "Africa/Tripoli",  "sd": "Africa/Khartoum",
    # Sub-Saharan Africa
    "ng": "Africa/Lagos",    "gh": "Africa/Accra",
    "sn": "Africa/Dakar",    "et": "Africa/Addis_Ababa",
    "so": "Africa/Mogadishu","ke": "Africa/Nairobi",
    "tz": "Africa/Dar_es_Salaam","ug": "Africa/Kampala",
    "cm": "Africa/Douala",   "ml": "Africa/Bamako",
    "bf": "Africa/Ouagadougou","ne": "Africa/Niamey",
    "mr": "Africa/Nouakchott","gm": "Africa/Banjul",
    "gn": "Africa/Conakry",  "sl": "Africa/Freetown",
    "ci": "Africa/Abidjan",  "td": "Africa/Ndjamena",
    # South / Southeast Asia
    "pk": "Asia/Karachi",    "in": "Asia/Kolkata",
    "bd": "Asia/Dhaka",      "af": "Asia/Kabul",
    "np": "Asia/Kathmandu",  "lk": "Asia/Colombo",
    "mv": "Indian/Maldives", "id": "Asia/Jakarta",
    "my": "Asia/Kuala_Lumpur","bn": "Asia/Brunei",
    "ph": "Asia/Manila",     "sg": "Asia/Singapore",
    "th": "Asia/Bangkok",    "mm": "Asia/Rangoon",
    # East Asia
    "cn": "Asia/Shanghai",   "jp": "Asia/Tokyo",
    "kr": "Asia/Seoul",      "mn": "Asia/Ulaanbaatar",
    # Americas
    "us": "America/New_York","ca": "America/Toronto",
    "mx": "America/Mexico_City","br": "America/Sao_Paulo",
    "ar": "America/Argentina/Buenos_Aires",
    # Australia / Oceania
    "au": "Australia/Sydney","nz": "Pacific/Auckland",
}


def _tz_from_timezonefinder(lat: float, lon: float) -> str | None:
    """Level 1: local library, no network. pip install timezonefinder"""
    try:
        from timezonefinder import TimezoneFinder
        return TimezoneFinder().timezone_at(lat=lat, lng=lon)
    except Exception:
        return None


def _tz_from_country_code(country_code: str | None) -> str | None:
    """
    Level 2: map ISO 3166-1 alpha-2 country code to IANA timezone.
    No network needed — uses the embedded table above.
    Handles DST correctly via Python's zoneinfo (built-in since Python 3.9).
    """
    if not country_code:
        return None
    return _COUNTRY_TZ.get(country_code.lower())


def _tz_from_timeapi(lat: float, lon: float) -> str | None:
    """Level 3: timeapi.io REST API."""
    try:
        r = requests.get(
            "https://timeapi.io/api/TimeZone/coordinate",
            params={"latitude": lat, "longitude": lon},
            timeout=4,
        )
        return r.json().get("timeZone") or None
    except Exception:
        return None


def _tz_from_geonames(lat: float, lon: float) -> str | None:
    """Level 4: GeoNames public endpoint."""
    try:
        r = requests.get(
            "http://api.geonames.org/timezoneJSON",
            params={"lat": lat, "lng": lon, "username": "demo"},
            timeout=4,
        )
        return r.json().get("timezoneId") or None
    except Exception:
        return None


def get_coordinates(
    city: str, country: str
) -> tuple[float | None, float | None, str | None]:
    """
    Returns (lat, lon, tz_string).
    Nominatim response includes country_code which we use for Level 2 tz lookup.
    """
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q":              f"{city}, {country}",
                "format":         "json",
                "limit":          1,
                "addressdetails": 1,   # needed to get country_code
            },
            headers=_NOMINATIM_HEADERS,
            timeout=6,
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            return None, None, None

        item = data[0]
        lat  = float(item["lat"])
        lon  = float(item["lon"])

        # Extract country_code from response (e.g. "pl" for Poland)
        country_code = item.get("address", {}).get("country_code") or \
                       item.get("country_code")

        # Resolve timezone: try all 4 levels
        tz = (
            _tz_from_timezonefinder(lat, lon)
            or _tz_from_country_code(country_code)
            or _tz_from_timeapi(lat, lon)
            or _tz_from_geonames(lat, lon)
        )
        return lat, lon, tz

    except Exception:
        return None, None, None


def get_prayer_times(
    city: str,
    country: str,
    madhab: str,
    method: str,
    target_date: date | None = None,
    lat: float | None = None,
    lon: float | None = None,
    country_code: str = "",
) -> dict:
    """
    Fetch prayer times. Returns {Fajr, Sunrise, Dhuhr, Asr, Maghrib, Isha}.
    Times in HH:MM local time, DST-correct.

    If lat/lon are provided they are used directly — skipping Nominatim geocoding.
    This ensures village-level accuracy (Кок-Жар ≠ Bishkek).
    """
    if target_date is None:
        target_date = date.today()

    date_str  = target_date.strftime("%d-%m-%Y")
    school    = MADHAB_MAP.get(madhab, 1)
    method_id = METHOD_MAP.get(method, 3)

    # Use saved coordinates if available — skip Nominatim geocoding entirely
    if lat is not None and lon is not None:
        tz = (_tz_from_timezonefinder(lat, lon)
              or _tz_from_country_code(country_code.lower() if country_code else None))
        params: dict = {
            "latitude":  lat,
            "longitude": lon,
            "method":    method_id,
            "school":    school,
        }
        if tz:
            params["timezonestring"] = tz
        try:
            data = _aladhan_get(f"timings/{date_str}", params)
            if data:
                return _extract_times(data)
        except Exception:
            pass
        # If API call failed with coords — fall through to city-based geocoding

    # No coords — geocode via Nominatim then call Aladhan
    lat_g, lon_g, tz = get_coordinates(city, country)

    # Strategy 1: coords + explicit timezone → correct DST
    if lat_g is not None and lon_g is not None and tz is not None:
        try:
            data = _aladhan_get(f"timings/{date_str}", {
                "latitude":       lat_g,
                "longitude":      lon_g,
                "method":         method_id,
                "school":         school,
                "timezonestring": tz,
            })
            if data:
                return _extract_times(data)
        except Exception:
            pass

    # Strategy 2: coords without timezone (may be off in DST zones)
    if lat_g is not None and lon_g is not None:
        try:
            data = _aladhan_get(f"timings/{date_str}", {
                "latitude":  lat_g,
                "longitude": lon_g,
                "method":    method_id,
                "school":    school,
            })
            if data:
                return _extract_times(data)
        except Exception:
            pass

    # Strategy 3: city/country name (aladhan own geocoder)
    try:
        data = _aladhan_get(f"timingsByCity/{date_str}", {
            "city": city, "country": country,
            "method": method_id, "school": school,
        })
        if data:
            return _extract_times(data)
        raise RuntimeError("aladhan returned no data")
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to fetch prayer times for {city}, {country}: {e}")


def _aladhan_get(endpoint: str, params: dict) -> dict | None:
    url = f"https://api.aladhan.com/v1/{endpoint}"
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    return data if data.get("code") == 200 else None


def _extract_times(data: dict) -> dict:
    """Strip seconds and timezone suffix from aladhan response."""
    timings = data["data"]["timings"]
    return {
        key: timings.get(key, "00:00").split(" ")[0][:5]
        for key in ("Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha")
    }