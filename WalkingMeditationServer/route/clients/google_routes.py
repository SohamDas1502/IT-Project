from __future__ import annotations

from typing import Any, Dict, Optional, List

import httpx

from route.config import google_maps_api_key
from route.errors import GoogleAPIError
from route.models import LatLng, RouteInfo
from route.utils.utils import duration_to_seconds, latlng_waypoint

ROUTES_COMPUTE_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"



async def compute_walking_route(
    client: httpx.AsyncClient,
    origin: LatLng,
    destination: LatLng,
    *,
    intermediate: Optional[LatLng] = None,
    want_polyline: bool = True,
) -> RouteInfo:
    headers = {
        "X-Goog-Api-Key": google_maps_api_key(),
        "Content-Type": "application/json",
        "X-Goog-FieldMask": (
            "routes.duration,routes.distanceMeters"
            + (",routes.polyline.encodedPolyline" if want_polyline else "")
        ),
    }

    body: Dict[str, Any] = {
        "origin": latlng_waypoint(origin.lat, origin.lon),
        "destination": latlng_waypoint(destination.lat, destination.lon),
        "travelMode": "WALK",
        "computeAlternativeRoutes": False,
    }
    if intermediate:
        body["intermediates"] = [latlng_waypoint(intermediate.lat, intermediate.lon)]

    r = await client.post(ROUTES_COMPUTE_URL, headers=headers, json=body)
    r.raise_for_status()
    data = r.json()

    routes = data.get("routes") or []
    if not routes:
        raise GoogleAPIError("No routes returned from computeRoutes")

    first = routes[0]
    dur_s = duration_to_seconds(first.get("duration"))
    dist_m = int(first.get("distanceMeters", 0))

    poly = ""
    if want_polyline:
        poly = (first.get("polyline") or {}).get("encodedPolyline") or ""
        if not poly:
            raise GoogleAPIError("Expected polyline.encodedPolyline but got empty.")

    return RouteInfo(duration_s=dur_s, distance_m=dist_m, polyline=poly)



async def fetch_route_polyline(
    client: httpx.AsyncClient,
    origin: LatLng,
    dest: LatLng,
) -> str:
    headers = {
        "X-Goog-Api-Key": google_maps_api_key(),
        "Content-Type": "application/json",
        "X-Goog-FieldMask": "routes.polyline.encodedPolyline",
    }
    body: Dict[str, Any] = {
        "origin": latlng_waypoint(origin.lat, origin.lon),
        "destination": latlng_waypoint(dest.lat, dest.lon),
        "travelMode": "WALK",
        "computeAlternativeRoutes": False,
    }

    r = await client.post(ROUTES_COMPUTE_URL, headers=headers, json=body)
    r.raise_for_status()
    data = r.json()

    routes = data.get("routes") or []
    poly = (((routes[0].get("polyline") or {}).get("encodedPolyline")) if routes else "") or ""
    if not poly:
        raise GoogleAPIError("Expected routes.polyline.encodedPolyline but got empty")
    return poly