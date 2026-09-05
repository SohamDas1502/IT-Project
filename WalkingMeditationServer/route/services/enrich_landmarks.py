from __future__ import annotations

from typing import List, Set

import httpx
import polyline as poly_decoder
from shapely.geometry import Point, Polygon

from route.clients.osm_overpass import fetch_landmarks, fetch_park_polygon
from route.models import LatLng, ParkLandmarks, ParkPlace, StepSegment
from route.utils.utils import haversine_m, interpolate_points

SEGMENT_LANDMARK_RADIUS_M = 35
SEGMENT_POINT_SPACING_M = 70


async def enrich_park_with_landmarks(
    park: ParkPlace,
    *,
    fallback_radius_m: int = 150,
) -> ParkLandmarks:
    """Landmarks inside the park's real OSM boundary, not a circle guess.

    Fetches the park's actual polygon and keeps only landmarks that fall
    inside it — so a long thin park doesn't pull in a bench from the
    building next door the way a plain radius search would. If no OSM
    polygon can be found for this park, falls back to the old radius
    search around its center point.
    """
    async with httpx.AsyncClient() as client:
        rings = await fetch_park_polygon(client, lat=park.lat, lon=park.lon)

        polygon = None
        for ring in rings:
            candidate = Polygon([(lon, lat) for lat, lon in ring])
            if candidate.contains(Point(park.lon, park.lat)):
                polygon = candidate
                break

        if polygon is None:
            landmarks, tree_count = await fetch_landmarks(
                client, lat=park.lat, lon=park.lon, radius_m=fallback_radius_m
            )
            return ParkLandmarks(
                center=LatLng(lat=park.lat, lon=park.lon),
                radius_m=fallback_radius_m,
                landmarks=landmarks,
                tree_count=tree_count,
            )

        # Query a circle big enough to cover the whole polygon, then keep
        # only the landmarks that are actually inside its real boundary.
        min_lon, min_lat, max_lon, max_lat = polygon.bounds
        cover_radius_m = int(max(
            haversine_m(park.lat, park.lon, max_lat, max_lon),
            haversine_m(park.lat, park.lon, min_lat, min_lon),
            haversine_m(park.lat, park.lon, max_lat, min_lon),
            haversine_m(park.lat, park.lon, min_lat, max_lon),
        )) + 20

        candidates, tree_count = await fetch_landmarks(
            client, lat=park.lat, lon=park.lon, radius_m=cover_radius_m
        )
        landmarks = [lm for lm in candidates if polygon.contains(Point(lm.lon, lm.lat))]

    return ParkLandmarks(
        center=LatLng(lat=park.lat, lon=park.lon),
        radius_m=cover_radius_m,
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

    Each segment's real path (its decoded polyline, not just start -> end)
    is walked in point_spacing_m steps, and each point is queried separately
    (one Overpass call per point, no batching yet). Neighbouring
    points/segments can have overlapping search circles, so once a landmark
    has been attached once, it's skipped on later ones — otherwise the same
    bench could end up mentioned twice.
    """
    seen_osm_ids: Set[int] = set()
    enriched_segments: List[StepSegment] = []

    async with httpx.AsyncClient() as client:
        for segment in segments:
            vertices = poly_decoder.decode(segment.step_polyline)
            points = interpolate_points(vertices, spacing_m=point_spacing_m)

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
