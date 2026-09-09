"""Spatial/geofence utilities using the Haversine formula."""

from __future__ import annotations

import math


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth in meters.

    Uses the Haversine formula. Accurate enough for geofence checks
    (error < 0.5% over short distances).
    """
    R = 6_371_000  # Earth mean radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def is_within_geofence(
    inspector_lat: float,
    inspector_lon: float,
    project_lat: float,
    project_lon: float,
    radius_m: float,
) -> tuple[bool, float]:
    """
    Check if the inspector's GPS position is within the project geofence.

    Returns (is_within, distance_in_meters).
    """
    distance = haversine_distance(inspector_lat, inspector_lon, project_lat, project_lon)
    return distance <= radius_m, round(distance, 2)
