FPV_PROFILES = [
    (3.0, 6.5, 120),
    (3.5, 6.0, 180),
    (5.0, 5.0, 249),
    (6.0, 6.0, 550),
    (7.0, 7.5, 750),
    (10.0, 9.0, 950),
]


NORMAL_DRONES = [
    ("DJI Mini 2", ("mini 2", "mini2"), 249, 31, 8.5),
    ("DJI Mini 3", ("mini 3", "mini3"), 249, 38, 10.0),
    ("DJI Mini 4 Pro", ("mini 4", "mini4", "mini 4 pro"), 249, 34, 10.7),
    ("DJI Air 2S", ("air 2s", "air2s"), 595, 31, 12.0),
    ("DJI Air 3", ("air 3", "air3"), 720, 46, 12.0),
    ("DJI Mavic 2", ("mavic 2", "mavic2"), 907, 31, 10.5),
    ("DJI Mavic 3", ("mavic 3", "mavic3"), 895, 46, 12.0),
    ("DJI Avata", ("avata",), 410, 18, 10.7),
    ("DJI Neo", ("neo",), 135, 18, 8.0),
]


def clamp(value, low, high):
    return max(low, min(high, value))


def estimate_fpv_from_voltage(voltage, inches, cells):
    if voltage <= 0:
        raise ValueError("Волтажът на батерията трябва да е положителен.")
    if inches <= 0:
        raise ValueError("Размерът на FPV дрона в инчове трябва да е положителен.")
    if cells <= 0:
        raise ValueError("Броят клетки на батерията трябва да е положителен.")

    per_cell = voltage / cells
    percent = clamp((per_cell - 3.45) / (4.20 - 3.45), 0.0, 1.0)

    max_minutes = FPV_PROFILES[-1][1]
    estimated_weight_g = FPV_PROFILES[-1][2]
    for max_inches, profile_minutes, profile_weight in FPV_PROFILES:
        if inches <= max_inches:
            max_minutes = profile_minutes
            estimated_weight_g = profile_weight
            break

    remaining_minutes = max_minutes * percent
    return {
        "cells": cells,
        "per_cell": per_cell,
        "percent": percent * 100,
        "remaining_minutes": max(0.2, remaining_minutes),
        "estimated_weight_g": estimated_weight_g,
        "label": f"{cells}S FPV, {inches:g} inch",
    }


def find_normal_drone(text):
    cleaned = text.strip().lower()
    if not cleaned:
        return None

    best = None
    best_score = 0
    for name, aliases, weight_g, max_minutes, wind_limit in NORMAL_DRONES:
        candidates = (name.lower(),) + aliases
        for candidate in candidates:
            score = 0
            for part in cleaned.replace("-", " ").split():
                if part and part in candidate:
                    score += len(part)
            if cleaned in candidate:
                score += len(cleaned) + 5
            if score > best_score:
                best_score = score
                best = {
                    "name": name,
                    "weight_g": weight_g,
                    "max_minutes": max_minutes,
                    "wind_limit_ms": wind_limit,
                }

    return best if best_score >= 3 else None
