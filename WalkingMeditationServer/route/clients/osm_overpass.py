from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import httpx

from route.config import OVERPASS_URL
from route.errors import OverpassError
from route.models import OsmLandmark

# tag -> landmark kind label
POI_TAGS: Dict[str, str] = {
    'amenity="bench"': "bench",
    'amenity="fountain"': "fountain",
    'amenity="drinking_water"': "drinking_water",
    'tourism="artwork"': "artwork",
    'historic="memorial"': "memorial",
}

RETRYABLE_STATUS = {429, 502, 503, 504}

# Overpass's public instance enforces a fair-use policy and 406s generic
# User-Agents (e.g. bare "python-httpx/x.y") — needs an identifiable client.
HEADERS = {
    "User-Agent": "WalkingMeditationServer/0.1 (+https://github.com/SohamDas1502/IT-Project)"
}


def _build_query(lat: float, lon: float, radius_m: int) -> str:
    poi_clauses = "\n".join(
        f'  node[{tag}](around:{radius_m},{lat},{lon});' for tag in POI_TAGS
    )
    return f"""[out:json][timeout:25];
(
{poi_clauses}
);
out body;
node["natural"="tree"](around:{radius_m},{lat},{lon});
out count;"""


async def fetch_landmarks(
    client: httpx.AsyncClient,
    *,
    lat: float,
    lon: float,
    radius_m: int = 150,
    max_attempts: int = 3,
) -> tuple[List[OsmLandmark], int]:
    """Fetch OSM landmarks (and a tree count) within radius_m of (lat, lon).

    Used for both a park's center point and a route step segment's point —
    the query itself doesn't care which one it's centered on.

    Returns (landmarks, tree_count), e.g.:
        (
            [
                OsmLandmark(osm_id=1289222389, kind="fountain",
                            name="Josephine Shaw Lowell Fountain",
                            lat=40.7539846, lon=-73.9840908),
                OsmLandmark(osm_id=6436470442, kind="drinking_water",
                            name=None, lat=40.7535716, lon=-73.9842604),
            ],
            508,
        )

    tree_count is kept separate from landmarks rather than as more
    OsmLandmark entries: trees vastly outnumber every other tag (e.g. 508
    trees vs. ~17 named landmarks around Bryant Park), and they carry
    little narratable detail (no name, just a species/leaf tag at best).
    Returning 500+ near-identical nodes would drown out the few landmarks
    actually worth mentioning in a script. Overpass's `out count;` gives
    us just the number, so we can say "you're surrounded by trees" as a
    single fact instead of listing each one.
    """
    query = _build_query(lat, lon, radius_m)

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            r = await client.post(
                OVERPASS_URL, data={"data": query}, headers=HEADERS, timeout=40.0
            )
            if r.status_code in RETRYABLE_STATUS:
                last_error = OverpassError(f"Overpass returned {r.status_code}")
            else:
                r.raise_for_status()
                return _parse_response(r.json())
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last_error = e

        if attempt < max_attempts:
            await asyncio.sleep(2 ** attempt)

    raise OverpassError(f"Overpass request failed after {max_attempts} attempts: {last_error}")


def _parse_response(data: Dict[str, Any]) -> tuple[List[OsmLandmark], int]:
    landmarks: List[OsmLandmark] = []
    tree_count = 0

    for el in data.get("elements") or []:
        if el.get("type") == "count":
            tree_count = int((el.get("tags") or {}).get("total", 0))
            continue

        if el.get("type") != "node":
            continue

        tags = el.get("tags") or {}
        kind = None
        for tag_expr, label in POI_TAGS.items():
            key, _, value = tag_expr.partition("=")
            if tags.get(key) == value.strip('"'):
                kind = label
                break
        if kind is None:
            continue

        landmarks.append(
            OsmLandmark(
                osm_id=el["id"],
                kind=kind,
                name=tags.get("name"),
                lat=float(el["lat"]),
                lon=float(el["lon"]),
            )
        )

    return landmarks, tree_count
