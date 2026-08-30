from __future__ import annotations

from pathlib import Path


from route.models import LatLng
from route.persistence.script_storage import save_script_text
from route.clients.openai_client import generate_text
from route.clients.google_weather import current_weather_lookup
from route.services.enrich_elevation import source_to_dest_elevation
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
    park: LatLng,
    to_park_time: int,                 # seconds
    park_time: int,                    # seconds
    park_to_destination_time: int,      # seconds
    context: str,
    output_folder: Path = DEFAULT_OUTPUT_FOLDER,
    save_to_disk: bool = True,
) -> str:
    fam_words = _words_for_minutes(to_park_time / 60)
    cm_words = _words_for_minutes(park_time / 60)
    closing_words = _words_for_minutes(park_to_destination_time / 60)

    weather_condition = current_weather_lookup(park.lat, park.lon)

    # BUG
    # Source to dest elevation generates StepSegments (src -> steps 1-3 -> dest), with elevation info
    # But here we are actually not taking into account the park detour, only computes elevation StepSegment data for baseline route
    # I think we can just to source to dest elevation from source -> park and then park -> dest
    source_to_park = await source_to_dest_elevation(source=source, destination=destination)

    print("\n\n\n\n\nSource to destination", source_to_park)

    prompt_tpl = get_script_generation_prompt("WITH_PARK")
    prompt = render_template(
        prompt_tpl,
        context=context,
        FAM_word_count=fam_words,
        source_to_park="\n".join(source_to_park),
        CM_word_count=cm_words,
        Closing_word_count=closing_words,
        weatherCondition= weather_condition,
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