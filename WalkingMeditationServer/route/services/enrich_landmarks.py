from __future__ import annotations

from typing import List, Set

import httpx

from route.clients.osm_overpass import fetch_landmarks
from route.models import LatLng, ParkLandmarks, ParkPlace, StepSegment
from route.utils.utils import interpolate_points

SEGMENT_LANDMARK_RADIUS_M = 35
SEGMENT_POINT_SPACING_M = 70


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
    radius_m: int = SEGMENT_LANDMARK_RADIUS_M,
    point_spacing_m: float = SEGMENT_POINT_SPACING_M,
) -> List[StepSegment]:
    """
    Look up nearby OSM landmarks for each step segment (a street block),
    and attach them to that segment.

    Each segment's line (start -> end) is walked in point_spacing_m steps,
    and each point is queried separately (one Overpass call per point, no
    batching yet). Neighbouring points/segments can have overlapping search
    circles, so once a landmark has been attached once, it's skipped on
    later ones — otherwise the same bench could end up mentioned twice.
    """
    seen_osm_ids: Set[int] = set()
    enriched_segments: List[StepSegment] = []

    async with httpx.AsyncClient() as client:
        for segment in segments:
            points = interpolate_points(
                segment.start.lat, segment.start.lon,
                segment.end.lat, segment.end.lon,
                spacing_m=point_spacing_m,
            )

            segment_landmarks = []
            for lat, lon in points:
                landmarks, _ = await fetch_landmarks(
                    client, lat=lat, lon=lon, radius_m=radius_m
                )
                new_landmarks = [lm for lm in landmarks if lm.osm_id not in seen_osm_ids]
                seen_osm_ids.update(lm.osm_id for lm in new_landmarks)
                segment_landmarks.extend(new_landmarks)

            enriched_segments.append(
                segment.model_copy(update={"landmarks": segment_landmarks})
            )

    return enriched_segments
