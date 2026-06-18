import math


EARTH_RADIUS_M = 6371008.8


def parse_float(value, name):
    try:
        return float(str(value).strip().replace(",", "."))
    except ValueError as exc:
        raise ValueError(f"Невалидна стойност за {name}.") from exc


def parse_decimal_degrees(lat_text, lon_text):
    lat = parse_float(lat_text, "ширина")
    lon = parse_float(lon_text, "дължина")
    validate_lat_lon(lat, lon)
    return lat, lon


def parse_dms(deg_text, min_text, sec_text, hemi, name):
    deg = abs(parse_float(deg_text, f"{name} градуси"))
    minutes = parse_float(min_text, f"{name} минути")
    seconds = parse_float(sec_text, f"{name} секунди")
    if minutes < 0 or minutes >= 60 or seconds < 0 or seconds >= 60:
        raise ValueError(f"Минутите и секундите за {name} трябва да са между 0 и 59.999.")

    value = deg + minutes / 60 + seconds / 3600
    if hemi.upper() in ("S", "W", "Ю", "З"):
        value *= -1
    return value


def validate_lat_lon(lat, lon):
    if not -90 <= lat <= 90:
        raise ValueError("Географската ширина трябва да е между -90 и 90.")
    if not -180 <= lon <= 180:
        raise ValueError("Географската дължина трябва да е между -180 и 180.")


def format_decimal(value):
    return f"{value:.7f}"


def destination_point(lat, lon, bearing_deg, distance_m):
    bearing = math.radians(bearing_deg)
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    angular_distance = distance_m / EARTH_RADIUS_M

    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular_distance)
        + math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(lat1),
        math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2),
    )

    lon2 = (math.degrees(lon2) + 540) % 360 - 180
    return math.degrees(lat2), lon2


def vector_to_bearing_distance(north_m, east_m):
    distance = math.hypot(north_m, east_m)
    if distance == 0:
        return 0.0, 0.0
    bearing = (math.degrees(math.atan2(east_m, north_m)) + 360) % 360
    return bearing, distance


def bearing_distance_to_vector(bearing_deg, distance_m):
    bearing = math.radians(bearing_deg)
    north = math.cos(bearing) * distance_m
    east = math.sin(bearing) * distance_m
    return north, east
