import json
import urllib.parse
import urllib.request


OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"


class WeatherError(RuntimeError):
    pass


def _get_json(url, timeout=12):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise WeatherError(f"Неуспешно вземане на данни: {exc}") from exc


def fetch_weather(lat, lon):
    params = {
        "latitude": f"{lat:.7f}",
        "longitude": f"{lon:.7f}",
        "current": "wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "wind_speed_unit": "ms",
        "timezone": "auto",
    }
    url = OPEN_METEO_FORECAST_URL + "?" + urllib.parse.urlencode(params)
    data = _get_json(url)
    current = data.get("current") or {}
    if "wind_speed_10m" not in current or "wind_direction_10m" not in current:
        raise WeatherError("Open-Meteo не върна текущ вятър за тези координати.")

    return {
        "wind_speed_ms": float(current["wind_speed_10m"]),
        "wind_from_deg": float(current["wind_direction_10m"]),
        "wind_gust_ms": float(current.get("wind_gusts_10m") or current["wind_speed_10m"]),
        "time": current.get("time", "неизвестно"),
    }


def fetch_elevation(lat, lon):
    params = {
        "latitude": f"{lat:.7f}",
        "longitude": f"{lon:.7f}",
    }
    url = OPEN_METEO_ELEVATION_URL + "?" + urllib.parse.urlencode(params)
    data = _get_json(url)
    elevation = data.get("elevation")
    if not elevation:
        raise WeatherError("Open-Meteo не върна надморска височина.")
    return float(elevation[0])
