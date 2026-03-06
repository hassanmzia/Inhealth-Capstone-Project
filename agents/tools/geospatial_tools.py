"""
Hospital routing and geospatial tools.

Re-exports the core find_nearest_hospital tool from base.tools and adds
route planning and multi-hospital search helpers.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from langchain_core.tools import tool

from agents.base.tools import find_nearest_hospital  # noqa: F401 – re-export

logger = logging.getLogger("inhealth.tools.geospatial")


@tool
def plan_route_to_hospital(
    patient_location: dict, hospital_location: dict, transport_mode: str = "driving"
) -> dict:
    """
    Plan a route from the patient's location to a hospital using the
    configured routing service (OSRM / Mapbox).

    Args:
        patient_location: Dict with 'lat' and 'lon' keys for the origin
        hospital_location: Dict with 'lat' and 'lon' keys for the destination
        transport_mode: Travel mode - 'driving' (default), 'walking', or
                        'ambulance'

    Returns:
        Dict with 'distance_km', 'duration_minutes', 'route_geometry', and
        'instructions'.
    """
    try:
        import httpx

        osrm_url = os.getenv(
            "OSRM_SERVICE_URL", "http://router.project-osrm.org"
        )
        profile = "car" if transport_mode in ("driving", "ambulance") else "foot"

        origin = f"{patient_location['lon']},{patient_location['lat']}"
        dest = f"{hospital_location['lon']},{hospital_location['lat']}"

        resp = httpx.get(
            f"{osrm_url}/route/v1/{profile}/{origin};{dest}",
            params={
                "overview": "full",
                "steps": "true",
                "geometries": "geojson",
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            return {"error": "No route found", "raw_code": data.get("code")}

        route = data["routes"][0]
        return {
            "distance_km": round(route["distance"] / 1000.0, 2),
            "duration_minutes": round(route["duration"] / 60.0, 1),
            "route_geometry": route.get("geometry"),
            "instructions": [
                step.get("maneuver", {}).get("instruction", "")
                for leg in route.get("legs", [])
                for step in leg.get("steps", [])
            ],
            "transport_mode": transport_mode,
        }

    except Exception as exc:
        logger.error("plan_route_to_hospital failed: %s", exc)
        return {"error": str(exc)}


@tool
def find_hospitals_in_radius(
    patient_location: dict, radius_km: float = 25.0, capabilities_needed: list = None
) -> list:
    """
    Find all hospitals within a given radius of the patient, optionally
    filtered by required capabilities.  Results are sorted by distance.

    Args:
        patient_location: Dict with 'lat' and 'lon' keys
        radius_km: Search radius in kilometres (default 25)
        capabilities_needed: Optional list of required capabilities
                             (e.g., ['cath_lab', 'stroke_center'])

    Returns:
        List of hospital dicts with name, distance_km, and capabilities.
    """
    try:
        from agents.base.tools import _get_pg_conn

        lat = patient_location.get("lat", 0)
        lon = patient_location.get("lon", 0)
        caps_needed = capabilities_needed or []

        caps_filter = ""
        if caps_needed:
            caps_list = ", ".join(f"'{c}'" for c in caps_needed)
            caps_filter = f"AND capabilities && ARRAY[{caps_list}]::text[]"

        conn = _get_pg_conn()
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    id, name, address, phone,
                    ST_Distance(
                        location::geography,
                        ST_MakePoint(%s, %s)::geography
                    ) / 1000.0 AS distance_km,
                    capabilities
                FROM hospitals
                WHERE active = TRUE
                  AND ST_DWithin(
                      location::geography,
                      ST_MakePoint(%s, %s)::geography,
                      %s
                  )
                  {caps_filter}
                ORDER BY distance_km
                LIMIT 20
                """,
                (lon, lat, lon, lat, radius_km * 1000),
            )
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            hospitals = [dict(zip(columns, row)) for row in rows]
        conn.close()

        return hospitals

    except Exception as exc:
        logger.error("find_hospitals_in_radius failed: %s", exc)
        return [{"error": str(exc)}]


# All tools provided by this module
GEOSPATIAL_TOOLS = [
    find_nearest_hospital,
    plan_route_to_hospital,
    find_hospitals_in_radius,
]
