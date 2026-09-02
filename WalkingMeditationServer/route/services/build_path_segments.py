from __future__ import annotations

from typing import List, Tuple

from route.models import LatLng, StepSegment
from route.services.enrich_elevation import build_route_elevation_segments


async def build_park_detour_segments(
    source: LatLng,
    park: LatLng,
    destination: LatLng,
) -> Tuple[List[StepSegment], List[StepSegment]]:
    """
    Get the step segments (with polylines) for a walk that detours through
    a park: source -> park, then park -> destination.

    compute_walking_steps() only takes one origin/destination pair at a
    time (no "intermediate stop" option), so a park detour has to be
    fetched as two separate leg calls rather than one combined call.
    Each leg reuses build_route_elevation_segments, so elevation is
    already attached to every segment too.
    """
    to_park_segments, _ = await build_route_elevation_segments(source, park)
    park_to_dest_segments, _ = await build_route_elevation_segments(park, destination)
    return to_park_segments, park_to_dest_segments
