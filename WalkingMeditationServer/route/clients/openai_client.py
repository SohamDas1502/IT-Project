from __future__ import annotations

import asyncio
from typing import Optional

from openai import OpenAI

from route.config import openai_api_key

DEFAULT_MODEL = "gpt-4.1-mini"

async def generate_text(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.8,
    api_key: Optional[str] = None,
) -> str:
    """
    Async wrapper around the (sync) OpenAI Python SDK call.
    Prevents blocking the event loop by running in a thread.
    """
    def _call() -> str:
        client = OpenAI(api_key=api_key or openai_api_key())
        resp = client.responses.create(
            model=model,
            input=prompt,
            temperature=temperature,
        )
        return (resp.output_text or "").strip()

    return await asyncio.to_thread(_call)