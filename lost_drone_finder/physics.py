import math

from geo import bearing_distance_to_vector, destination_point, vector_to_bearing_distance


GRAVITY = 9.80665


def wind_to_vector(wind_from_deg, wind_speed_ms):
    blowing_to = (wind_from_deg + 180) % 360
    return bearing_distance_to_vector(blowing_to, wind_speed_ms)


def estimate_drag_sensitivity(weight_kg):
    weight_kg = max(weight_kg, 0.05)
    return min(1.4, max(0.18, 0.55 / math.sqrt(weight_kg)))


def estimate_terminal_velocity(weight_kg):
    weight_kg = max(weight_kg, 0.05)
    return min(32.0, max(7.0, 11.5 * math.sqrt(weight_kg / 0.25)))


def calculate_zone(
    lat,
    lon,
    speed_ms,
    drone_direction_deg,
    remaining_battery_min,
    weight_kg,
    height_agl_m,
    wind_from_deg,
    wind_speed_ms,
    wind_gust_ms=None,
    loss_mode="signal",
    drone_type="fpv",
    fpv_mode="fall",
    elapsed_since_loss_min=0.0,
    elapsed_since_loss_s=None,
    normal_wind_limit_ms=8.0,
):
    if speed_ms < 0:
        raise ValueError("Скоростта не може да е отрицателна.")
    if remaining_battery_min < 0:
        raise ValueError("Оставащата батерия не може да е отрицателна.")
    if elapsed_since_loss_s is not None:
        elapsed_since_loss_min = elapsed_since_loss_s / 60
    if elapsed_since_loss_min < 0:
        raise ValueError("Миналото време след загуба на сигнал не може да е отрицателно.")
    if weight_kg <= 0:
        raise ValueError("Теглото трябва да е положително.")
    if height_agl_m < 0:
        raise ValueError("Височината не може да е отрицателна.")

    wind_north_ms, wind_east_ms = wind_to_vector(wind_from_deg, wind_speed_ms)
    weight_factor = estimate_drag_sensitivity(weight_kg)
    remaining_s = remaining_battery_min * 60
    elapsed_s = elapsed_since_loss_min * 60
    observed_s = elapsed_s if elapsed_s > 0 else remaining_s

    if loss_mode == "crash":
        powered_s = min(observed_s, remaining_s, 8.0)
        post_power_s = 0.0
    else:
        powered_s = min(observed_s, remaining_s)
        post_power_s = max(0.0, observed_s - remaining_s)

    terminal_velocity = estimate_terminal_velocity(weight_kg)
    fall_time_s = math.sqrt(2 * height_agl_m / GRAVITY) if height_agl_m else 0.0
    if terminal_velocity and height_agl_m:
        fall_time_s = min(fall_time_s, height_agl_m / terminal_velocity)
        fall_time_s = max(fall_time_s, math.sqrt(2 * height_agl_m / GRAVITY) * 0.65)

    if drone_type == "normal":
        excess_wind = max(0.0, wind_speed_ms - normal_wind_limit_ms)
        drift_factor = min(0.60, excess_wind / 12.0)
        if loss_mode == "crash":
            drone_north_ms, drone_east_ms = bearing_distance_to_vector(drone_direction_deg, speed_ms * 0.30)
            ground_north_ms = drone_north_ms + wind_north_ms * 0.14
            ground_east_ms = drone_east_ms + wind_east_ms * 0.14
            powered_s = min(powered_s, 8.0)
        else:
            ground_north_ms = wind_north_ms * drift_factor
            ground_east_ms = wind_east_ms * drift_factor
            powered_s = min(powered_s, 240.0)
        fall_wind_factor = 0.18 if wind_speed_ms > normal_wind_limit_ms else 0.04
        model_note = "Нормален дрон: очаква се да е много близо до мястото на изгубения сигнал, освен при силен вятър."
    else:
        if fpv_mode == "landing" and loss_mode != "crash":
            cruise_speed = speed_ms * 0.25
            wind_factor = 0.75 * weight_factor
            ground_north_ms, ground_east_ms = bearing_distance_to_vector(drone_direction_deg, cruise_speed)
            ground_north_ms += wind_north_ms * wind_factor
            ground_east_ms += wind_east_ms * wind_factor
            fall_time_s = fall_time_s if post_power_s > 0 else 0.0
            fall_wind_factor = min(1.25, weight_factor) if post_power_s > 0 else 0.0
            model_note = "FPV бавно кацане: дронът каца плавно и вятърът леко го носи по време на кацането."
        else:
            cruise_speed = speed_ms if loss_mode != "crash" else speed_ms * 0.35
            powered_s = min(powered_s, 18.0 if loss_mode != "crash" else 8.0)
            wind_factor = 0.22 * weight_factor
            ground_north_ms, ground_east_ms = bearing_distance_to_vector(drone_direction_deg, cruise_speed)
            ground_north_ms += wind_north_ms * wind_factor
            ground_east_ms += wind_east_ms * wind_factor
            fall_wind_factor = min(1.25, weight_factor)
            model_note = "FPV падане: търси се най-близката вероятна точка според последната посока, височина и вятър."

    flight_north_m = ground_north_ms * powered_s
    flight_east_m = ground_east_ms * powered_s
    fall_north_m = wind_north_ms * fall_wind_factor * fall_time_s
    fall_east_m = wind_east_ms * fall_wind_factor * fall_time_s

    if post_power_s > 0 and not (drone_type == "normal" and loss_mode != "crash"):
        fall_north_m += wind_north_ms * min(1.0, weight_factor) * min(post_power_s, 120.0)
        fall_east_m += wind_east_ms * min(1.0, weight_factor) * min(post_power_s, 120.0)

    total_north_m = flight_north_m + fall_north_m
    total_east_m = flight_east_m + fall_east_m
    bearing, distance = vector_to_bearing_distance(total_north_m, total_east_m)
    impact_lat, impact_lon = destination_point(lat, lon, bearing, distance)

    gust = wind_gust_ms if wind_gust_ms is not None else wind_speed_ms
    wind_uncertainty = abs(gust - wind_speed_ms) * (powered_s * 0.10 + fall_time_s)
    model_uncertainty = distance * 0.12 + height_agl_m * 0.25
    weight_uncertainty = 30.0 / math.sqrt(max(weight_kg, 0.05))
    timing_uncertainty = max(15.0, speed_ms * 8.0)

    if drone_type == "normal":
        model_uncertainty += 25.0 if wind_speed_ms <= normal_wind_limit_ms else 55.0
        timing_uncertainty *= 0.45
    if loss_mode == "crash":
        model_uncertainty += 55.0
    if drone_type == "fpv" and fpv_mode == "landing":
        model_uncertainty += 45.0

    radius_m = max(25.0, wind_uncertainty + model_uncertainty + weight_uncertainty + timing_uncertainty)

    return {
        "impact_lat": impact_lat,
        "impact_lon": impact_lon,
        "bearing_deg": bearing,
        "distance_m": distance,
        "radius_m": radius_m,
        "flight_time_s": powered_s,
        "post_power_s": post_power_s,
        "fall_time_s": fall_time_s,
        "terminal_velocity_ms": terminal_velocity,
        "wind_blowing_to_deg": (wind_from_deg + 180) % 360,
        "ground_speed_ms": math.hypot(ground_north_ms, ground_east_ms),
        "input_speed_ms": speed_ms,
        "loss_mode": loss_mode,
        "drone_type": drone_type,
        "fpv_mode": fpv_mode,
        "model_note": model_note,
        "remaining_battery_min": remaining_battery_min,
        "elapsed_since_loss_min": elapsed_since_loss_min,
        "elapsed_since_loss_s": elapsed_since_loss_min * 60,
    }
