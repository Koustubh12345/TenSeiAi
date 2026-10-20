"""Fast live-data answers.

The old path sent every weather question through a chain of search engines
and page fetches, which could take 15-30 seconds.  Weather is a small,
well-defined API problem, so answer it directly with a short timeout and a
clear failure message when the network is unavailable.
"""

import json
import re
import urllib.parse
import urllib.request

from . import config

_UA = {"User-Agent": "TenSeiAi/1.0 (local weather lookup)"}
_TIMEOUT = 3.5

# A few common state/city aliases give a useful point instead of the
# geometric centre of a large region.  This is location data, not answers.
_KNOWN = {
    "karnataka": (12.9716, 77.5946, "Bengaluru, Karnataka"),
    "bengaluru": (12.9716, 77.5946, "Bengaluru, Karnataka"),
    "bangalore": (12.9716, 77.5946, "Bengaluru, Karnataka"),
    "mysore": (12.2958, 76.6394, "Mysuru, Karnataka"),
    "mysuru": (12.2958, 76.6394, "Mysuru, Karnataka"),
    "mangalore": (12.9141, 74.8560, "Mangaluru, Karnataka"),
    "mangaluru": (12.9141, 74.8560, "Mangaluru, Karnataka"),
    "hubli": (15.3647, 75.1240, "Hubballi, Karnataka"),
    "hubballi": (15.3647, 75.1240, "Hubballi, Karnataka"),
    "belgaum": (15.8497, 74.4977, "Belagavi, Karnataka"),
    "belagavi": (15.8497, 74.4977, "Belagavi, Karnataka"),
    "india": (28.6139, 77.2090, "New Delhi, India"),
    "delhi": (28.6139, 77.2090, "New Delhi, India"),
    "mumbai": (19.0760, 72.8777, "Mumbai, India"),
    "chennai": (13.0827, 80.2707, "Chennai, India"),
    "hyderabad": (17.3850, 78.4867, "Hyderabad, India"),
    "kolkata": (22.5726, 88.3639, "Kolkata, India"),
    "pune": (18.5204, 73.8567, "Pune, India"),
    "london": (51.5072, -0.1276, "London, UK"),
    "new york": (40.7128, -74.0060, "New York, USA"),
    "tokyo": (35.6762, 139.6503, "Tokyo, Japan"),
    "paris": (48.8566, 2.3522, "Paris, France"),
    "dubai": (25.2048, 55.2708, "Dubai, UAE"),
    "singapore": (1.3521, 103.8198, "Singapore"),
    "sydney": (-33.8688, 151.2093, "Sydney, Australia"),
}

_WMO = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog", 51: "light drizzle", 53: "drizzle",
    55: "heavy drizzle", 56: "freezing drizzle", 57: "freezing drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain",
    67: "freezing rain", 71: "light snow", 73: "snow", 75: "heavy snow",
    77: "snow grains", 80: "light showers", 81: "showers", 82: "heavy showers",
    85: "snow showers", 86: "heavy snow showers", 95: "thunderstorm",
    96: "thunderstorm with hail", 99: "severe thunderstorm with hail",
}


def _get_json(url, timeout=_TIMEOUT):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read(300000).decode("utf-8", "ignore"))


def _location(question):
    """Extract a place name from a weather question, or return a safe default."""
    q = (question or "").strip()
    ql = q.lower()
    m = re.search(
        r"\b(?:weather|temperature|forecast|raining|rain)\b"
        r"(?:\s+(?:like|today|now))?\s+(?:in|for|at|near)\s+"
        r"([a-z][a-z .'\-]{1,45}?)(?:\s+(?:today|now|tomorrow|this week)\b|[?.!]|$)",
        ql)
    if not m:
        m = re.search(
            r"\b(?:in|for|at|near)\s+([a-z][a-z .'\-]{1,45}?)\s+"
            r"(?:weather|temperature|forecast|rain)\b", ql)
    loc = (m.group(1) if m else "").strip(" .,?!")
    if not loc:
        # "weather in Karnataka today" is handled by the first regex.  Avoid
        # treating the whole sentence as a place name.
        m = re.search(r"\b(?:in|for|at|near)\s+([a-z][a-z .'\-]{2,40})", ql)
        loc = (m.group(1) if m else "").strip(" .,?!")
    loc = re.sub(r"\b(?:today|now|currently|right now|this week|tomorrow)\b",
                 " ", loc, flags=re.I)
    loc = re.sub(r"\s+", " ", loc).strip(" .,?!")
    return loc


def _geocode(loc):
    key = re.sub(r"[^a-z ]", "", loc.lower()).strip()
    if key in _KNOWN:
        lat, lon, label = _KNOWN[key]
        return lat, lon, label
    url = ("https://geocoding-api.open-meteo.com/v1/search?name="
           + urllib.parse.quote_plus(loc)
           + "&count=1&language=en&format=json")
    data = _get_json(url)
    rows = data.get("results") or []
    if not rows:
        return None
    r = rows[0]
    label = r.get("name") or loc
    admin = r.get("admin1") or ""
    country = r.get("country") or ""
    parts = [label]
    if admin and admin.lower() != label.lower():
        parts.append(admin)
    if country:
        parts.append(country)
    return float(r["latitude"]), float(r["longitude"]), ", ".join(parts)


def weather(question):
    """Return a direct weather answer dict, or None when this is not a weather ask."""
    ql = (question or "").lower()
    if not re.search(r"\b(?:weather|temperature|forecast|rain|raining)\b", ql):
        return None
    # "weather vs climate" / "what is weather" are concepts, not live data.
    if re.search(r"\b(?:vs|versus|difference between)\b", ql):
        return None
    if re.search(r"^what (?:is|are) (?:the )?(?:weather|climate)\b", ql) \
            and not re.search(r"\b(?:today|now|current|currently|this week|tomorrow)\b", ql):
        return None
    if not config.online():
        return {
            "answer": "I'm running offline, so I can't fetch live weather right now. "
                      "Turn on web research (`/web on` in the terminal) and ask again.",
            "mode": "live", "confidence": 0.9, "sources": [],
            "took_s": 0.0, "kind": "weather",
        }
    loc = _location(question)
    if not loc:
        return {
            "answer": "Tell me the city or region and I'll check the current weather, "
                      "for example: **weather in Bengaluru today**.",
            "mode": "live", "confidence": 0.9, "sources": [],
            "took_s": 0.0, "kind": "weather",
        }
    try:
        geo = _geocode(loc)
        if not geo:
            return {
                "answer": "I couldn't find a place called **%s**. Try a nearby city or district." % loc,
                "mode": "live", "confidence": 0.75, "sources": [],
                "took_s": 0.0, "kind": "weather",
            }
        lat, lon, label = geo
        url = ("https://api.open-meteo.com/v1/forecast?latitude=%.4f&longitude=%.4f"
               "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
               "weather_code,wind_speed_10m&timezone=auto" % (lat, lon))
        data = _get_json(url)
        cur = data.get("current") or {}
        temp = cur.get("temperature_2m")
        feels = cur.get("apparent_temperature")
        hum = cur.get("relative_humidity_2m")
        wind = cur.get("wind_speed_10m")
        code = int(cur.get("weather_code") or 0)
        desc = _WMO.get(code, "current conditions")
        if temp is None:
            raise RuntimeError("no temperature in response")
        bits = ["Right now in **%s**: **%s°C**" % (label, _num(temp))]
        if feels is not None:
            bits.append("feels like **%s°C**" % _num(feels))
        bits.append("**%s**" % desc)
        if hum is not None:
            bits.append("humidity **%s%%**" % _num(hum))
        if wind is not None:
            bits.append("wind **%s km/h**" % _num(wind))
        return {
            "answer": ", ".join(bits) + ".",
            "mode": "live", "confidence": 0.95, "sources": [],
            "took_s": 0.0, "kind": "weather",
        }
    except Exception:
        return {
            "answer": "I couldn't reach a live weather service just now. "
                      "Please check a local weather app for **%s**; I don't want to guess." % loc,
            "mode": "live", "confidence": 0.8, "sources": [],
            "took_s": 0.0, "kind": "weather",
        }


def _num(value):
    try:
        f = float(value)
        return ("%.1f" % f).rstrip("0").rstrip(".")
    except Exception:
        return str(value)


def try_answer(question):
    """Only handle questions that genuinely need live weather data."""
    ql = (question or "").lower()
    if "weather" not in ql and "temperature" not in ql and "forecast" not in ql:
        return None
    return weather(question)
