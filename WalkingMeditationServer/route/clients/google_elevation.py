from __future__ import annotations

from typing import Any, Dict, List

import httpx

from route.config import google_maps_api_key
from route.errors import GoogleAPIError

ELEVATION_URL = "https://maps.googleapis.com/maps/api/elevation/json"


async def fetch_elevation_samples_for_polyline(
    client: httpx.AsyncClient,
    encoded_polyline: str,
    *,
    samples: int = 2,
) -> List[Dict[str, Any]]:
    params = {
        "key": google_maps_api_key(),
        "path": f"enc:{encoded_polyline}",
        "samples": str(samples),
    }
    r = await client.get(ELEVATION_URL, params=params)
    r.raise_for_status()
    data = r.json()

    if data.get("status") != "OK":
        raise GoogleAPIError(
            f"Elevation API error: {data.get('status')} {data.get('error_message') or ''}".strip()
        )

    return data.get("results") or []

