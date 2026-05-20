"""Geo utilities for in-car location-aware recommendation."""

from __future__ import annotations

import numpy as np
import pandas as pd

EARTH_RADIUS_KM = 6371.0088


def haversine_km(
    lat1: float | np.ndarray,
    lon1: float | np.ndarray,
    lat2: float | np.ndarray,
    lon2: float | np.ndarray,
) -> float | np.ndarray:
    """Great-circle distance between two points (or arrays of points) in km."""
    lat1 = np.radians(lat1)
    lat2 = np.radians(lat2)
    dlat = lat2 - lat1
    dlon = np.radians(lon2) - np.radians(lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def add_distance_column(
    businesses: pd.DataFrame,
    user_lat: float,
    user_lon: float,
    out_col: str = "distance_km",
) -> pd.DataFrame:
    """Return businesses with a distance column to (user_lat, user_lon)."""
    df = businesses.copy()
    df[out_col] = haversine_km(
        df["latitude"].to_numpy(), df["longitude"].to_numpy(), user_lat, user_lon
    )
    return df


def filter_radius(
    businesses: pd.DataFrame, user_lat: float, user_lon: float, radius_km: float
) -> pd.DataFrame:
    """Restrict to restaurants within ``radius_km`` of the user."""
    df = add_distance_column(businesses, user_lat, user_lon)
    return df[df["distance_km"] <= radius_km].reset_index(drop=True)


def distance_score(
    distances_km: np.ndarray | pd.Series, decay_km: float = 5.0
) -> np.ndarray:
    """Score 1.0 at the user's location, decaying smoothly with distance.

    Uses an exponential decay: score = exp(-d / decay_km). At ``decay_km`` km the
    score is ~0.37; at 2 * decay_km it's ~0.14. Symmetric, monotonic, bounded.
    """
    distances = np.asarray(distances_km, dtype=np.float64)
    return np.exp(-distances / max(decay_km, 1e-6))


# ---------------------------------------------------------------------------
# City centroids — used as fall-back when the browser blocks geolocation
# ---------------------------------------------------------------------------
CITY_CENTROIDS: dict[str, tuple[float, float]] = {
    "Philadelphia": (39.9526, -75.1652),
    "Tampa": (27.9506, -82.4572),
    "New Orleans": (29.9511, -90.0715),
    "Tucson": (32.2226, -110.9747),
    "Indianapolis": (39.7684, -86.1581),
    "Nashville": (36.1627, -86.7816),
    "Reno": (39.5296, -119.8138),
    "Saint Louis": (38.6270, -90.1994),
    "Santa Barbara": (34.4208, -119.6982),
    "Boise": (43.6150, -116.2023),
    "Edmonton": (53.5461, -113.4938),
}


def lookup_city_centroid(city: str) -> tuple[float, float] | None:
    """Best-effort centroid for a Yelp dataset city."""
    return CITY_CENTROIDS.get(city)
