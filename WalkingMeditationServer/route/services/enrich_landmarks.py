from __future__ import annotations

from typing import List, Set

import httpx

from route.clients.osm_overpass import fetch_landmarks
from route.models import LatLng, ParkLandmarks, ParkPlace, StepSegment


async def enrich_park_with_landmarks(
    park: ParkPlace,
    *,
    radius_m: int = 150,
) -> ParkLandmarks:
    async with httpx.AsyncClient() as client:
        landmarks, tree_count = await fetch_landmarks(
            client, lat=park.lat, lon=park.lon, radius_m=radius_m
        )

    return ParkLandmarks(
        center=LatLng(lat=park.lat, lon=park.lon),
        radius_m=radius_m,
        landmarks=landmarks,
        tree_count=tree_count,
    )


async def enrich_segments_with_landmarks(
    segments: List[StepSegment],
    *,
    radius_m: int = 50,
) -> List[StepSegment]:
    """
    Look up nearby OSM landmarks for each step segment (a street block),
    and attach them to that segment.

    Each segment is queried around its midpoint. Neighbouring segments can
    have overlapping search circles, so once a landmark has been attached
    to one segment, it's skipped on later ones — otherwise the same bench
    could end up mentioned twice in the script.
    """
    seen_osm_ids: Set[int] = set()
    enriched_segments: List[StepSegment] = []

    async with httpx.AsyncClient() as client:
        for segment in segments:
            mid_lat = (segment.start.lat + segment.end.lat) / 2
            mid_lon = (segment.start.lon + segment.end.lon) / 2

            landmarks, _ = await fetch_landmarks(
                client, lat=mid_lat, lon=mid_lon, radius_m=radius_m
            )

            new_landmarks = [lm for lm in landmarks if lm.osm_id not in seen_osm_ids]
            seen_osm_ids.update(lm.osm_id for lm in new_landmarks)

            enriched_segments.append(
                segment.model_copy(update={"landmarks": new_landmarks})
            )

    return enriched_segments
