from __future__ import annotations

import httpx

from typing import List, Dict, Any

from route.models import LatLng
from route.config import google_maps_api_key
from route.errors import GoogleAPIError

ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

def _wp(lat: float, lon: float) -> Dict[str, Any]:
    return {"location": {"latLng": {"latitude": lat, "longitude": lon}}}

async def compute_walking_steps(client: httpx.AsyncClient, origin: LatLng, dest: LatLng) -> List[Dict[str, Any]]:
    headers = {
        "X-Goog-Api-Key": google_maps_api_key(),
        "Content-Type": "application/json",
        # Steps contain navigationInstruction, start/end locations, polyline, etc.  [oai_citation:4‡Google for Developers](https://developers.google.com/maps/documentation/routes/understand-route-response)
        "X-Goog-FieldMask": (
            "routes.duration,"
            "routes.legs.steps.startLocation,"
            "routes.legs.steps.endLocation,"
            "routes.legs.steps.polyline.encodedPolyline,"
            "routes.legs.steps.navigationInstruction.instructions"
        ),
    }
    body = {
        "origin": _wp(origin.lat, origin.lon),
        "destination": _wp(dest.lat, dest.lon),
        "travelMode": "WALK",
        "computeAlternativeRoutes": False,
    }
    r = await client.post(ROUTES_URL, headers=headers, json=body)
    r.raise_for_status()
    data = r.json()
    routes = data.get("routes") or []
    if not routes:
        raise GoogleAPIError("No routes returned")

    # For walking, there is typically 1 leg unless you added intermediates.
    legs = routes[0].get("legs") or []
    if not legs:
        raise GoogleAPIError("No legs returned")

    steps = legs[0].get("steps") or []
    return steps