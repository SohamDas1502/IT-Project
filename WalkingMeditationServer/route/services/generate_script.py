from __future__ import annotations

from pathlib import Path

import httpx

from route.models import LatLng, ParkPlace
from route.persistence.script_storage import save_script_text
from route.clients.openai_client import generate_text
from route.clients.google_weather import current_weather_lookup
from route.clients.google_routes import compute_walking_route
from route.services.build_path_segments import build_park_detour_segments
from route.services.enrich_landmarks import enrich_segments_with_landmarks
from route.services.enrich_elevation import source_to_dest_elevation, print_segments
from route.config import get_script_generation_prompt, render_template

WITH_PARK_FAM = 0.2
WITH_PARK_CM = 0.4
WITH_PARK_CLOSING = 0.4

BASE_DIR = Path(__file__).resolve().parents[1]  # route/
DEFAULT_OUTPUT_FOLDER = BASE_DIR / "scripts"


def _words_for_minutes(minutes: float, *, wpm: int = 150) -> int:
    return int(round(minutes * wpm))


async def generate_script_with_park(
    source: LatLng,
    destination: LatLng,
    park: ParkPlace,
    total_travel_time: int,   # seconds; whole walk's time budget
    context: str,
    output_folder: Path = DEFAULT_OUTPUT_FOLDER,
    save_to_disk: bool = True,
) -> str:
    park_latlng = LatLng(lat=park.lat, lon=park.lon)

    # Real path through the detour: source -> park, then park -> destination.
    # (Was previously computing elevation for source -> destination directly,
    # which ignored the park detour entirely.)
    to_park_segments, _park_to_dest_segments = await build_park_detour_segments(
        source, park_latlng, destination
    )

    # Step segments carry geometry, not duration, so fetch each leg's
    # walking time separately to split total_travel_time across the
    # focused_attention / compassion_meditation / closing sections.
    async with httpx.AsyncClient(timeout=40) as client:
        to_park_route = await compute_walking_route(
            client, source, park_latlng, want_polyline=False
        )
        park_to_dest_route = await compute_walking_route(
            client, park_latlng, destination, want_polyline=False
        )

    to_park_time = to_park_route.duration_s
    park_to_destination_time = park_to_dest_route.duration_s
    # Whatever's left of the budget after both walking legs is time in the park.
    park_time = max(total_travel_time - to_park_time - park_to_destination_time, 0)

    # Word counts pace the narration to match how long each part of the
    # walk actually takes, so the audio doesn't run out early or drag on
    # after the user has moved on. The LLM has no way to know these
    # durations itself, so we compute the target length here.
    fam_words = _words_for_minutes(to_park_time / 60)
    cm_words = _words_for_minutes(park_time / 60)
    closing_words = _words_for_minutes(park_to_destination_time / 60)

    weather_condition = current_weather_lookup(park.lat, park.lon)

    # Attach nearby OSM landmarks (benches, fountains, etc.) to each
    # segment. Not read by the prompt yet — print_segments below still
    # only writes out elevation info — this just gets the data flowing.
    to_park_segments = await enrich_segments_with_landmarks(to_park_segments)

    source_to_park = print_segments(to_park_segments, source, park_latlng)

    print("\n\n\n\n\nSource to destination", source_to_park)

    prompt_tpl = get_script_generation_prompt("WITH_PARK")
    prompt = render_template(
        prompt_tpl,
        context=context,
        FAM_word_count=fam_words,
        source_to_park="\n".join(source_to_park),
        CM_word_count=cm_words,
        Closing_word_count=closing_words,
        weatherCondition=weather_condition,
    )

    script = await generate_text(prompt)

    if save_to_disk:
        save_script_text(script, output_folder, prefix="meditation_script")

    return script


async def generate_script_without_park(
    source: LatLng,
    destination: LatLng,
    total_walking_time: int,   # seconds
    context: str,
    output_folder: Path = DEFAULT_OUTPUT_FOLDER,
    save_to_disk: bool = True,
) -> str:
    fam_words = _words_for_minutes(((total_walking_time * WITH_PARK_FAM) / 60))
    cm_words = _words_for_minutes(((total_walking_time * WITH_PARK_CM) / 60))
    closing_words = _words_for_minutes(((total_walking_time * WITH_PARK_CLOSING) / 60))

    weather_condition = current_weather_lookup(destination.lat, destination.lon)

    total_path = await source_to_dest_elevation(source=source, destination=destination)

    prompt_tpl = get_script_generation_prompt("WITHOUT_PARK")
    prompt = render_template(
        prompt_tpl,
        context=context,
        FAM_word_count=fam_words,
        source_to_park="\n".join(total_path),
        CM_word_count=cm_words,
        Closing_word_count=closing_words,
        weatherCondition=weather_condition,
    )

    script = await generate_text(prompt)

    if save_to_disk:
        save_script_text(script, output_folder, prefix="meditation_script")

    return await generate_text(prompt)
