import warnings
import os
import uvicorn
import torch
import asyncio
from fastapi import FastAPI, HTTPException
from typing import Optional

from qwen_tts import Qwen3TTSModel
from contextlib import asynccontextmanager

from route.services.generate_script import generate_script_with_park, generate_script_without_park
from route.services.get_route import generate_walk_route
from route.services.text_to_speech import generate_tts_mp3
from route.errors import OpenaiAPIError
from route.models import WalkRouteRequest, WalkRouteResponse, ScriptWithParkRequest, ScriptWithParkResponse
from route.models import ScriptWithoutParkRequest, ScriptWithoutParkResponse, TTSRequest, TTSResponse
from route.utils.utils import _ensure_ffmpeg


# Your global model handle
MODEL: Optional["Qwen3TTSModel"] = None  # quotes avoid import-time issues if needed

TTS_SEMAPHORE = asyncio.Semaphore(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler:
    - code before 'yield' runs on startup
    - code after 'yield' runs on shutdown
    """
    warnings.filterwarnings("ignore", message=".*flash-attn.*")

    global MODEL

    _ensure_ffmpeg()

    use_cuda = torch.cuda.is_available()
    device_map = "cuda:0" if use_cuda else "cpu"
    dtype = torch.bfloat16 if use_cuda else torch.float32

    MODEL = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        device_map=device_map,
        dtype=dtype,
        # If on CUDA + flash-attn2 installed, you can enable:
        # attn_implementation="flash_attention_2",
    )

    try:
        from joblib.externals.loky import get_reusable_executor
        get_reusable_executor().shutdown(wait=True)
        print("Joblib Turned off")
    except Exception as e:
        print("Joblib Not Turned off", str(e))


    try:
        yield  # ---- app runs here ----
    finally:
        # ---- shutdown ----
        # If your model/library needs explicit cleanup, do it here.
        # Example patterns:
        MODEL = None
        if use_cuda:
            # optional: helps release cached GPU memory in some cases
            torch.cuda.empty_cache()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"Heartbeat": "Hello World"}

@app.post("/route/generate-path", response_model=WalkRouteResponse)
async def generate_route(payload: WalkRouteRequest):
    try:
        result: WalkRouteResponse = await generate_walk_route(
            payload.source,
            payload.destination,
            payload.total_travel_time
        )
        return result 
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/route/generate-script/park", response_model=ScriptWithParkResponse)
async def generate_script_w_park(payload: ScriptWithParkRequest):
    try:
        result: str = await generate_script_with_park(
            payload.source,
            payload.destination,
            payload.park,
            payload.to_park_time,
            payload.park_time,
            payload.park_to_destination_time,
            payload.context
        )

        return {
            "script": result
        }

    except OpenaiAPIError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    
@app.post("/route/generate-script/without-park", response_model=ScriptWithoutParkResponse)
async def generate_script_wo_park(payload: ScriptWithoutParkRequest):
    try:
        result: str = await generate_script_without_park(
            payload.source,
            payload.destination,
            payload.total_walking_time,
            payload.context
        )

        return {
            "script": result
        }

    except OpenaiAPIError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/tts")#, response_model=Response)
async def text_to_speech_endpoint(payload: TTSRequest):

    global MODEL

    if TTS_SEMAPHORE is None:
        # If you forgot to set it, fail loudly rather than creating unbounded concurrency.
        print("None Semaphore")
        raise HTTPException(status_code=500, detail="TTS semaphore not initialized")

    try:
        result = await generate_tts_mp3(
            model=MODEL,
            semaphore=TTS_SEMAPHORE,
            text=payload.text,
            language=payload.language,
            speaker=payload.speaker,
            instruct=payload.instruct,
            bitrate="192k",
            offload_model_to_thread=False,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {e}")

    return result



if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_excludes=[os.path.join("env", "*")],
    )