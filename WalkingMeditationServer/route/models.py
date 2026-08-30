from typing import List, Tuple
from pydantic import BaseModel, Field

class LatLng(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)

class RouteRequest(BaseModel):
    origin: LatLng
    destination: LatLng
    extra_time: int = Field(..., ge=0, description="Extra time allowance in seconds")
    max_routes: int = Field(10, ge=1, le=50, description="Max number of routes to return")

class RouteOption(BaseModel):
    path: str
    duration_seconds: int
    distance_meters: int

class RouteResponse(BaseModel):
    baseline_duration_seconds: int
    allowed_duration_seconds: int
    routes: List[RouteOption]

class ParkDetourConstraints(BaseModel):
    extra_time: int = Field(..., ge=0, description="Extra time allowance in seconds")
    parks_radius_m: float = Field(1500.0, gt=0, le=50_000, description="Search radius around destination (meters)")
    parks_max_results: int = Field(12, ge=1, le=50, description="Max parks fetched from Places")
    parks_check_limit: int = Field(8, ge=1, le=25, description="How many closest parks to evaluate with Routes API")
    save_html: bool = Field(False, description="If true, writes HTML route visualizations (requires route_viz)")

class ParkDetourRequest(BaseModel):
    origin: LatLng
    destination: LatLng
    constraints: ParkDetourConstraints

class ParkInfo(BaseModel):
    place_id: str
    name: str
    lat: float
    lon: float
    distance_to_dest_m: float

class DetourInfo(BaseModel):
    path: str
    duration_seconds: int
    distance_meters: int
    extra_seconds_vs_baseline: int

class ParkDetourOption(BaseModel):
    park: ParkInfo
    detour: DetourInfo
    is_doable: bool

class ParkDetourBaseline(BaseModel):
    duration_seconds: int
    distance_meters: int
    path: str

class ParkDetourResponse(BaseModel):
    baseline: ParkDetourBaseline
    allowed_duration_seconds: int
    parks_considered: int
    feasible_detours: List[ParkDetourOption]
    infeasible_detours: List[ParkDetourOption]
    html_files: List[str] = []

class Place(BaseModel):
    place_id: str
    name: str
    lat: float
    lon: float
    distance_to_dest_m: float

class PathDescriptionRequest(BaseModel):
    path: str

class PathDescriptionResponse(BaseModel):
    description: str

class ScriptWithParkRequest(BaseModel):
    source: LatLng
    destination: LatLng
    park:LatLng
    to_park_time: int
    park_time: int
    park_to_destination_time: int
    context:str

class ScriptWithParkResponse(BaseModel):
    script: str

class ScriptWithoutParkRequest(BaseModel):
    source: LatLng
    destination: LatLng
    total_walking_time: int
    context:str

class ScriptWithoutParkResponse(BaseModel):
    script: str


class RouteInfo(BaseModel):
    duration_s: int
    distance_m: int
    polyline: str

class ParkPlace(BaseModel):
    place_id: str
    name: str
    lat: float
    lon: float
    

class ParkDetourResult(BaseModel):
    park: ParkPlace
    baseline_s: int
    detour_s: int
    added_s: int
    slack_s: int

class WalkRouteResponse(BaseModel):
    origin: LatLng
    destination: LatLng
    total_travel_time: int = Field(..., ge=0)
    baseline: RouteInfo
    parks: List[ParkDetourResult] = Field(default_factory=list)

class WalkRouteRequest(BaseModel):
    source: LatLng
    destination: LatLng
    total_travel_time: int

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    language: str = "English"   # or "Auto"
    speaker: str = "Ryan"
    instruct: str = ""
    bitrate: str = "192k"

class TTSResponse(BaseModel):
    content: bytes
    filename: str = "speech.mp3"
    media_type: str = "audio/mpeg"

class StepSegment(BaseModel):
    i: int
    instruction: str
    start: LatLng
    end: LatLng
    step_polyline: str
    elev_start_m: float
    elev_end_m: float
    elev_gain_m: float
    label: str


