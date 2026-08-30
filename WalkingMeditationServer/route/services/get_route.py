from __future__ import annotations

import asyncio
import httpx
from typing import Optional

from route.clients.google_places import search_parks_along_route
from route.clients.google_routes import compute_walking_route
from route.models import LatLng, ParkDetourResult, ParkPlace, WalkRouteResponse

async def generate_walk_route(
    source: LatLng,
    destination: LatLng,
    total_travel_time: int,
    *,
    sar_offset_m: int = 250,
    sar_max_parks: int = 25,
    concurrency: int = 6,
    timeout_s: float = 40.0,
) -> WalkRouteResponse:
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        baseline = await compute_walking_route(
            client, source, destination, want_polyline=True
        )

        if baseline.duration_s > total_travel_time:
            return WalkRouteResponse(
                origin=source,
                destination=destination,
                total_travel_time=total_travel_time,
                baseline=baseline,
                parks=[],
            )

        parks = await search_parks_along_route(
            client,
            route_polyline=baseline.polyline,
            max_results=sar_max_parks,
            route_offset_m=sar_offset_m,
        )

        if not parks:
            return WalkRouteResponse(
                origin=source,
                destination=destination,
                total_travel_time=total_travel_time,
                baseline=baseline,
                parks=[],
            )

        sem = asyncio.Semaphore(concurrency)

        async def eval_one(p: ParkPlace) -> Optional[ParkDetourResult]:
            async with sem:
                try:
                    inter = LatLng(lat=p.lat, lon=p.lon)
                    detour = await compute_walking_route(
                        client,
                        source,
                        destination,
                        intermediate=inter,
                        want_polyline=False,
                    )
                except Exception:
                    return None

                if detour.duration_s <= total_travel_time:
                    return ParkDetourResult(
                        park=p,
                        baseline_s=baseline.duration_s,
                        detour_s=detour.duration_s,
                        added_s=detour.duration_s - baseline.duration_s,
                        slack_s=total_travel_time - detour.duration_s,
                    )
                return None

        evaluated = await asyncio.gather(*(eval_one(p) for p in parks))
        results = [r for r in evaluated if r is not None]

        results.sort(key=lambda r: (-r.slack_s, r.added_s, r.detour_s))

        return WalkRouteResponse(
            origin=source,
            destination=destination,
            total_travel_time=total_travel_time,
            baseline=baseline,
            parks=results,
        )