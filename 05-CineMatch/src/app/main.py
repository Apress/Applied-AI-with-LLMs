import logging

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud import count_informative_votes, get_user
from app.db.session import get_db
from app.recommend.service import generate_recommendations, regenerate_recommendations
from app.settings import settings
from app.taste.schema import TasteProfile
from app.taste.service import build_and_store_taste_profile
from app.tmdb.client import tmdb_client

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

app = FastAPI(title="Film Suggestion Bot API")


class RecommendationRequest(BaseModel):
    telegram_user_id: int


class TasteRequest(BaseModel):
    telegram_user_id: int


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/tmdb/search")
async def tmdb_search(q: str, db: AsyncSession = Depends(get_db)) -> dict:
    return await tmdb_client.search_movie(db, query=q)


@app.get("/tmdb/movie/{movie_id}/providers")
async def tmdb_providers(movie_id: int, country: str = "IT", db: AsyncSession = Depends(get_db)) -> dict:
    payload = await tmdb_client.watch_providers(db, movie_id)
    result = payload.get("results", {}).get(country)
    return {"movie_id": movie_id, "country": country, "providers": result}


@app.post("/taste-profile/build")
async def build_taste_profile(request: TasteRequest, db: AsyncSession = Depends(get_db)) -> dict:
    informative_votes = await count_informative_votes(db, request.telegram_user_id)
    if informative_votes < 7:
        raise HTTPException(status_code=400, detail="Need at least 7 informative votes")

    profile = await build_and_store_taste_profile(db, tmdb_client, request.telegram_user_id)
    return profile.model_dump()


@app.post("/recommendations/generate")
async def recommendations_generate(
    request: RecommendationRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    informative_votes = await count_informative_votes(db, request.telegram_user_id)
    if informative_votes < 7:
        raise HTTPException(status_code=400, detail="Need at least 7 informative votes")

    user = await get_user(db, request.telegram_user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.taste_profile_json is None:
        profile = await build_and_store_taste_profile(db, tmdb_client, request.telegram_user_id)
    else:
        profile = TasteProfile.model_validate(user.taste_profile_json)

    return await generate_recommendations(db, tmdb_client, request.telegram_user_id, profile)


@app.post("/recommendations/regenerate")
async def recommendations_regenerate(
    request: RecommendationRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    informative_votes = await count_informative_votes(db, request.telegram_user_id)
    if informative_votes < 7:
        raise HTTPException(status_code=400, detail="Need at least 7 informative votes")

    user = await get_user(db, request.telegram_user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.taste_profile_json is None:
        profile = await build_and_store_taste_profile(db, tmdb_client, request.telegram_user_id)
    else:
        profile = TasteProfile.model_validate(user.taste_profile_json)

    return await regenerate_recommendations(db, tmdb_client, request.telegram_user_id, profile)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await tmdb_client.close()
