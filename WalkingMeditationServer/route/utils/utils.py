from __future__ import annotations
import re
import math
import polyline as poly_decoder
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple

from route.errors import GoogleRoutesError, AudioConversionError

import subprocess
from pathlib import Path


_DURATION_RE = re.compile(r"^(\d+)s$")


def duration_to_seconds(duration: str) -> int:
    m = _DURATION_RE.match(duration or "")
    if not m:
        raise GoogleRoutesError(f"Unexpected duration format: {duration!r}")
    return int(m.group(1))


def latlng_waypoint(lat: float, lon: float) -> Dict[str, Any]:
    return {"location": {"latLng": {"latitude": lat, "longitude": lon}}}


def polyline_to_path_string(encoded_polyline: str) -> str:
    """
    Convert encoded polyline -> "lat,lon;lat,lon;..."
    """
    decoded_points = poly_decoder.decode(encoded_polyline)  # [(lat, lon), ...]
    return ";".join(f"{lat},{lon}" for lat, lon in decoded_points)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Great-circle distance (meters)
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c

def interpolate_points(
    lat1: float, lon1: float, lat2: float, lon2: float, spacing_m: float
) -> List[Tuple[float, float]]:
    """Points along the straight line from (lat1,lon1) to (lat2,lon2),
    spaced ~spacing_m apart. Always includes both endpoints."""
    length = haversine_m(lat1, lon1, lat2, lon2)
    n = max(1, math.ceil(length / spacing_m))
    return [
        (lat1 + (lat2 - lat1) * i / n, lon1 + (lon2 - lon1) * i / n)
        for i in range(n + 1)
    ]


def _ensure_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
    except Exception as e:
        raise RuntimeError("ffmpeg is not installed or not on PATH") from e


# def _wav_to_mp3(wav_path: Path, mp3_path: Path, bitrate: str) -> None:
#     subprocess.run(
#         [
#             "ffmpeg", "-y",
#             "-i", str(wav_path),
#             "-codec:a", "libmp3lame",
#             "-b:a", bitrate,
#             str(mp3_path),
#         ],
#         check=True,
#         stdout=subprocess.DEVNULL,
#         stderr=subprocess.DEVNULL,
#     )

    
def classify_step(elev_gain_m: float, elev_start_m: float, elev_end_m: float) -> str:
    """
    Replace with your own semantics.
    Example: label based on absolute slope/gain, not absolute altitude.
    """
    if elev_gain_m >= 8:
        return "high elevation (uphill)"
    if elev_gain_m <= -8:
        return "high elevation (downhill)"
    return "low elevation (mostly flat)"


def wav_to_mp3(wav_path: Path, mp3_path: Path, bitrate: str = "192k") -> None:
    """
    Convert a WAV file to MP3 using ffmpeg.

    Requirements:
      - ffmpeg installed and available in PATH

    Args:
      wav_path: input .wav path
      mp3_path: output .mp3 path
      bitrate: e.g. "128k", "192k"
    """
    if not wav_path.exists():
        raise AudioConversionError(f"WAV file not found: {wav_path}")

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(wav_path),
        "-codec:a",
        "libmp3lame",
        "-b:a",
        str(bitrate),
        str(mp3_path),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or "").strip()
        raise AudioConversionError(f"ffmpeg failed: {err}")

    if not mp3_path.exists():
        raise AudioConversionError("ffmpeg succeeded but MP3 file missing")