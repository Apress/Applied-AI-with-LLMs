import datetime as dt
import json
import uuid

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CacheEntry, Suggestion, User, Vote, VoteEnum


async def upsert_user(
    session: AsyncSession,
    user_id: int,
    country: str = "IT",
    language: str = "it",
) -> User:
    user = await session.get(User, user_id)
    if user is None:
        user = User(id=user_id, country=country, language=language)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    return user


async def update_user_onboarding(
    session: AsyncSession,
    user_id: int,
    country: str,
    owned_services: list[str],
    mood_text: str,
) -> None:
    user = await upsert_user(session, user_id, country=country)
    user.country = country
    user.owned_services_json = {"services": owned_services}
    user.mood_text = mood_text
    await session.commit()


async def set_user_taste_profile(session: AsyncSession, user_id: int, taste_profile: dict) -> None:
    user = await upsert_user(session, user_id)
    user.taste_profile_json = taste_profile
    await session.commit()


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def reset_user_recommendation_state(session: AsyncSession, user_id: int) -> None:
    user = await session.get(User, user_id)
    if user is not None:
        user.taste_profile_json = None

    votes_stmt = delete(Vote).where(Vote.user_id == user_id)
    suggestions_stmt = delete(Suggestion).where(Suggestion.user_id == user_id)

    await session.execute(votes_stmt)
    await session.execute(suggestions_stmt)
    await session.commit()


async def add_vote(session: AsyncSession, user_id: int, tmdb_id: int, vote_enum: VoteEnum) -> Vote:
    vote = Vote(user_id=user_id, tmdb_id=tmdb_id, vote_enum=vote_enum)
    session.add(vote)
    await session.commit()
    await session.refresh(vote)
    return vote


async def get_votes_by_user(session: AsyncSession, user_id: int) -> list[Vote]:
    stmt = select(Vote).where(Vote.user_id == user_id).order_by(Vote.created_at.asc(), Vote.id.asc())
    result = await session.execute(stmt)
    return list(result.scalars())


async def get_voted_tmdb_ids(session: AsyncSession, user_id: int) -> set[int]:
    stmt = select(Vote.tmdb_id).where(Vote.user_id == user_id)
    result = await session.execute(stmt)
    rows = result.all()
    tmdb_ids: set[int] = set()
    for row in rows:
        tmdb_ids.add(row[0])
    return tmdb_ids


async def count_informative_votes(session: AsyncSession, user_id: int) -> int:
    stmt = select(func.count(Vote.id)).where(
        and_(
            Vote.user_id == user_id,
            Vote.vote_enum.in_([VoteEnum.like, VoteEnum.dislike]),
        )
    )
    result = await session.execute(stmt)
    count_value = result.scalar_one()
    return int(count_value)


def count_informative_votes_from_values(vote_values: list[str]) -> int:
    count = 0
    for value in vote_values:
        if value in {VoteEnum.like.value, VoteEnum.dislike.value}:
            count += 1
    return count


async def get_informative_votes(session: AsyncSession, user_id: int) -> list[Vote]:
    stmt = (
        select(Vote)
        .where(and_(Vote.user_id == user_id, Vote.vote_enum.in_([VoteEnum.like, VoteEnum.dislike])))
        .order_by(Vote.created_at.asc(), Vote.id.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars())


async def add_suggestions_batch(session: AsyncSession, user_id: int, tmdb_ids: list[int]) -> str:
    batch_id = str(uuid.uuid4())
    for tmdb_id in tmdb_ids:
        suggestion = Suggestion(user_id=user_id, tmdb_id=tmdb_id, batch_id=batch_id)
        session.add(suggestion)
    await session.commit()
    return batch_id


async def get_suggested_tmdb_ids(session: AsyncSession, user_id: int) -> set[int]:
    stmt = select(Suggestion.tmdb_id).where(Suggestion.user_id == user_id)
    result = await session.execute(stmt)
    rows = result.all()
    output: set[int] = set()
    for row in rows:
        output.add(row[0])
    return output


async def cache_get_json(session: AsyncSession, key: str) -> dict | None:
    item = await session.get(CacheEntry, key)
    if item is None:
        return None
    now = dt.datetime.utcnow()
    if item.expires_at <= now:
        await session.delete(item)
        await session.commit()
        return None
    return item.response_json


async def cache_set_json(session: AsyncSession, key: str, response_json: dict, ttl_seconds: int) -> None:
    expires_at = dt.datetime.utcnow() + dt.timedelta(seconds=ttl_seconds)
    existing = await session.get(CacheEntry, key)
    if existing is None:
        entry = CacheEntry(key=key, response_json=response_json, expires_at=expires_at)
        session.add(entry)
    else:
        existing.response_json = response_json
        existing.expires_at = expires_at
    await session.commit()


def make_cache_key(prefix: str, payload: dict) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"{prefix}:{serialized}"


async def cleanup_expired_cache(session: AsyncSession) -> int:
    now = dt.datetime.utcnow()
    stmt = delete(CacheEntry).where(CacheEntry.expires_at <= now)
    result = await session.execute(stmt)
    await session.commit()
    return int(result.rowcount or 0)
