from __future__ import annotations

from typing import Any, Dict, List

import httpx

from route.config import google_maps_api_key
from route.models import ParkPlace

PLACES_TEXTSEARCH_NEW_URL = "https://places.googleapis.com/v1/places:searchText"


async def search_parks_along_route(
    client: httpx.AsyncClient,
    *,
    route_polyline: str,
    max_results: int = 20,
    route_offset_m: int = 250,
) -> List[ParkPlace]:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": google_maps_api_key(),
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location",
    }

    body: Dict[str, Any] = {
        "textQuery": "park",
        "searchAlongRouteParameters": {
            "polyline": {"encodedPolyline": route_polyline},
            # "routeOffset": {"meters": route_offset_m},  # enable if you want
        },
        # "pageSize": max_results,  # depending on Places API version/behavior
    }

    r = await client.post(PLACES_TEXTSEARCH_NEW_URL, headers=headers, json=body)
    r.raise_for_status()
    data = r.json()

    places = data.get("places") or []
    results: List[ParkPlace] = []

    for p in places:
        pid = p.get("id") or ""
        if not pid:
            continue

        display = (p.get("displayName") or {}).get("text") or "(unnamed park)"
        loc = p.get("location") or {}
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        if lat is None or lon is None:
            continue

        results.append(
            ParkPlace(place_id=pid, name=display, lat=float(lat), lon=float(lon))
        )

    # Dedup by place_id
    uniq: Dict[str, ParkPlace] = {p.place_id: p for p in results}
    return list(uniq.values())[:max_results]