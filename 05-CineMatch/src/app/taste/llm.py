import json
import logging
from typing import Any

import httpx

from app.settings import settings
from app.taste.schema import TasteProfile, VotedMovieMetadata

logger = logging.getLogger(__name__)


async def build_taste_profile_with_llm(
    country: str,
    voted_movies: list[VotedMovieMetadata],
) -> TasteProfile | None:
    if settings.llm_provider != "gemini":
        return None

    if not settings.llm_api_key:
        return None

    if not settings.llm_base_url or not settings.llm_model:
        return None

    system_prompt = (
        "You are a strict JSON generator. Return only JSON matching TasteProfile fields. "
        "Do not include markdown. Keep short arrays: <=5 genres and <=10 keywords."
    )

    user_payload: dict[str, Any] = {
        "country": country,
        "voted_movies": [item.model_dump() for item in voted_movies],
        "required_fields": [
            "country",
            "with_genre_ids",
            "without_genre_ids",
            "with_keyword_ids",
            "without_keyword_ids",
            "primary_release_date_gte",
            "primary_release_date_lte",
            "vote_average_gte",
            "original_language",
            "sort_by",
            "explain",
        ],
    }

    url = settings.llm_base_url.rstrip("/") + "/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    request_json = {
        "model": settings.llm_model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload)},
        ],
        "temperature": 0,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers=headers,
                json=request_json,
            )
            response.raise_for_status()
            payload = response.json()

        content = payload["choices"][0]["message"]["content"]
        return TasteProfile.model_validate_json(content)

    except Exception:
        logger.exception(
            "LLM taste profile generation failed; fallback to deterministic"
        )
        return None
