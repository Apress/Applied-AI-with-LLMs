import asyncio
import logging
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud import cache_get_json, cache_set_json, make_cache_key
from app.settings import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

TTL_SEARCH = 7 * 24 * 3600
TTL_DETAILS = 7 * 24 * 3600
TTL_KEYWORDS = 7 * 24 * 3600
TTL_CREDITS = 7 * 24 * 3600
TTL_PROVIDERS = 24 * 3600
TTL_DISCOVER = 24 * 3600


def build_tmdb_poster_url(poster_path: str | None) -> str | None:
    if not isinstance(poster_path, str):
        return None

    cleaned_path = poster_path.strip()
    if not cleaned_path:
        return None

    if not cleaned_path.startswith("/"):
        cleaned_path = f"/{cleaned_path}"

    return f"{IMAGE_BASE_URL}{cleaned_path}"


class TMDbClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=20.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        merged_params = dict(params)
        merged_params["api_key"] = self.api_key

        retries = 3
        for attempt in range(retries):
            try:
                response = await self._client.get(f"{BASE_URL}{path}", params=merged_params)
                if response.status_code >= 500:
                    logger.warning("TMDb server error %s on %s", response.status_code, path)
                    raise httpx.HTTPStatusError("server error", request=response.request, response=response)
                response.raise_for_status()
                payload = response.json()
                return payload
            except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                if attempt == retries - 1:
                    logger.exception("TMDb request failed for %s", path)
                    raise exc
                await asyncio.sleep(0.5 * (attempt + 1))

        raise RuntimeError("Unreachable retry block")

    async def search_movie(self, db: AsyncSession, query: str, page: int = 1) -> dict:
        payload = {"query": query, "page": page}
        cache_key = make_cache_key("tmdb_search", payload)
        cached = await cache_get_json(db, cache_key)
        if cached is not None:
            return cached

        response_json = await self._get("/search/movie", payload)
        await cache_set_json(db, cache_key, response_json, TTL_SEARCH)
        return response_json

    async def movie_details(self, db: AsyncSession, movie_id: int) -> dict:
        payload = {"movie_id": movie_id}
        cache_key = make_cache_key("tmdb_details", payload)
        cached = await cache_get_json(db, cache_key)
        if cached is not None:
            return cached

        response_json = await self._get(f"/movie/{movie_id}", {})
        await cache_set_json(db, cache_key, response_json, TTL_DETAILS)
        return response_json

    async def movie_keywords(self, db: AsyncSession, movie_id: int) -> dict:
        payload = {"movie_id": movie_id}
        cache_key = make_cache_key("tmdb_keywords", payload)
        cached = await cache_get_json(db, cache_key)
        if cached is not None:
            return cached

        response_json = await self._get(f"/movie/{movie_id}/keywords", {})
        await cache_set_json(db, cache_key, response_json, TTL_KEYWORDS)
        return response_json

    async def movie_credits(self, db: AsyncSession, movie_id: int) -> dict:
        payload = {"movie_id": movie_id}
        cache_key = make_cache_key("tmdb_credits", payload)
        cached = await cache_get_json(db, cache_key)
        if cached is not None:
            return cached

        response_json = await self._get(f"/movie/{movie_id}/credits", {})
        await cache_set_json(db, cache_key, response_json, TTL_CREDITS)
        return response_json

    async def watch_providers(self, db: AsyncSession, movie_id: int) -> dict:
        payload = {"movie_id": movie_id}
        cache_key = make_cache_key("tmdb_providers", payload)
        cached = await cache_get_json(db, cache_key)
        if cached is not None:
            return cached

        response_json = await self._get(f"/movie/{movie_id}/watch/providers", {})
        await cache_set_json(db, cache_key, response_json, TTL_PROVIDERS)
        return response_json

    async def discover_movies(self, db: AsyncSession, params: dict[str, Any]) -> dict:
        cache_key = make_cache_key("tmdb_discover", params)
        cached = await cache_get_json(db, cache_key)
        if cached is not None:
            return cached

        response_json = await self._get("/discover/movie", params)
        await cache_set_json(db, cache_key, response_json, TTL_DISCOVER)
        return response_json


tmdb_client = TMDbClient(api_key=settings.tmdb_api_key)
