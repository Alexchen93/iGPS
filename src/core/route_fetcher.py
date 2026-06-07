"""OSRM route fetching for iGPS location simulation."""

import requests
from typing import List, Tuple, Optional
from loguru import logger


OSRM_BASE = "https://router.project-osrm.org"


def fetch_road_route(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    transport_mode: str = "driving",
    timeout: int = 8,
) -> Optional[List[Tuple[float, float, float]]]:
    """Fetch a road-snapped route from OSRM and return timestamped waypoints.

    Returns:
        List of (lat, lon, time_offset_seconds) or None on failure.
    """
    try:
        coord_str = f"{start_lon},{start_lat};{end_lon},{end_lat}"
        profile_map = {
            "walking": "foot",
            "cycling": "bike",
            "driving": "car",
            "highway": "car",
        }
        profile = profile_map.get(transport_mode, "car")
        url = f"{OSRM_BASE}/route/v1/{profile}/{coord_str}"
        params = {"overview": "full", "geometries": "geojson", "steps": "true"}
        headers = {"User-Agent": "iGPS/1.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "Ok":
            logger.warning(f"OSRM returned non-OK: {data.get('code')}")
            return None
        routes = data.get("routes", [])
        if not routes:
            return None
        coords = routes[0]["geometry"]["coordinates"]
        total_dist = routes[0]["distance"]
        total_time = routes[0]["duration"]
        if transport_mode == "walking":
            speed_ms = 1.4
        elif transport_mode == "cycling":
            speed_ms = 5.0
        else:
            speed_ms = max(total_dist / max(total_time, 1), 5.0)
        waypoints: List[Tuple[float, float, float]] = []
        cumulative_time = 0.0
        for i in range(1, len(coords)):
            prev_lon, prev_lat = coords[i - 1]
            curr_lon, curr_lat = coords[i]
            from core.coordinate_utils import CoordinateUtils
            seg_dist = CoordinateUtils.calculate_distance(prev_lat, prev_lon, curr_lat, curr_lon)
            seg_time = seg_dist / speed_ms if speed_ms > 0 else 1.0
            cumulative_time += seg_time
            waypoints.append((curr_lat, curr_lon, cumulative_time))
        return waypoints
    except requests.RequestException as e:
        logger.warning(f"OSRM request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching route: {e}")
        return None
