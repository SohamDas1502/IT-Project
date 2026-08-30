from __future__ import annotations

import httpx
from typing import List, Tuple
from route.config import *
from route.models import StepSegment, LatLng
from route.clients.google_steps import compute_walking_steps
from route.clients.google_elevation import fetch_elevation_samples_for_polyline
from route.clients.google_routes import fetch_route_polyline
from route.utils.route_hint import extract_street_hint
from route.utils.utils import classify_step


async def build_route_elevation_segments(
    origin: LatLng,
    dest: LatLng,
    *,
    per_step_samples: int = 2,   # 2 = start/end only; 10 = smoother per-step
    overall_samples: int = 200,  # overall elevation profile granularity
) -> Tuple[List[StepSegment], List[Tuple[float, float]]]:
    async with httpx.AsyncClient(timeout=40) as client:
        steps = await compute_walking_steps(client, origin, dest)

        print("steps", steps)

        segments: List[StepSegment] = []
        for i, st in enumerate(steps, start=1):
            instr = ((st.get("navigationInstruction") or {}).get("instructions")) or ""
            sp = (st.get("startLocation") or {}).get("latLng") or {}
            ep = (st.get("endLocation") or {}).get("latLng") or {}
            poly = ((st.get("polyline") or {}).get("encodedPolyline")) or ""
            
            if not poly or "latitude" not in sp or "latitude" not in ep:
                continue

            elev = await fetch_elevation_samples_for_polyline(client, poly, samples=per_step_samples)
            # The Elevation API returns results sampled along the path inclusive endpoints.  [oai_citation:6‡Google for Developers](https://developers.google.com/maps/documentation/elevation/requests-elevation?utm_source=chatgpt.com)
            elev_start = float(elev[0]["elevation"])
            elev_end = float(elev[-1]["elevation"])
            gain = elev_end - elev_start
            label = classify_step(gain, elev_start, elev_end)

            segments.append(
                StepSegment(
                    i=i,
                    instruction=instr.strip(),
                    start= LatLng(lat=float(sp["latitude"]), lon=float(sp["longitude"])),
                    end= LatLng(lat=float(ep["latitude"]), lon=float(ep["longitude"])),
                    step_polyline=poly,
                    elev_start_m=elev_start,
                    elev_end_m=elev_end,
                    elev_gain_m=gain,
                    label=label
                )
            )
        print("segments", segments)

        # Build an overall elevation profile (single call on the full route polyline):
        # We need a full route polyline; easiest is to request it from computeRoutes.
        poly = await fetch_route_polyline(client, origin, dest)
        
        elev_profile = await fetch_elevation_samples_for_polyline(client, poly, samples=overall_samples)

        profile = [
            (float(p["location"]["lat"]), float(p["elevation"]))
            for p in elev_profile
        ]
        print("profile", profile)

        return segments, profile

def print_segments(segments: List[StepSegment], origin: LatLng, dest: LatLng) -> list:

    sample_string = []
    sample_string.append(f"source @ {origin.lat:.5f},{origin.lon:.5f}")
    for s in segments:
        street_hint = extract_street_hint(s.instruction)
        sample_string.append(
            f"-> {street_hint}  "
            f"Start_{s.i} @ {s.start.lat:.5f},{s.start.lon:.5f} "
            f"End_{s.i} @ {s.end.lat:.5f},{s.end.lon:.5f} "
            f"[{s.label}; ^ { s.elev_gain_m:+.1f}m; {s.elev_start_m:.1f} -> {s.elev_end_m:.1f}m]"
        )
    sample_string.append(f"-> destination @ {dest.lat:.5f},{dest.lon:.5f}")
    return sample_string


async def source_to_dest_elevation(
    source : LatLng,
    destination: LatLng
    ) -> list:

    (segments, profile) = await build_route_elevation_segments(source, destination)
    return print_segments(segments, source, destination)