from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud import get_informative_votes, get_user, set_user_taste_profile
from app.taste.deterministic import build_deterministic_taste_profile
from app.taste.llm import build_taste_profile_with_llm
from app.taste.schema import TasteProfile, VotedMovieMetadata
from app.tmdb.client import TMDbClient


async def _collect_voted_metadata(
    db: AsyncSession,
    tmdb: TMDbClient,
    user_id: int,
) -> list[VotedMovieMetadata]:
    informative_votes = await get_informative_votes(db, user_id)
    output: list[VotedMovieMetadata] = []

    for vote in informative_votes:
        details = await tmdb.movie_details(db, vote.tmdb_id)
        keywords_response = await tmdb.movie_keywords(db, vote.tmdb_id)

        genre_ids: list[int] = []
        for genre_obj in details.get("genres", []):
            genre_id = genre_obj.get("id")
            if isinstance(genre_id, int):
                genre_ids.append(genre_id)

        keyword_ids: list[int] = []
        for keyword_obj in keywords_response.get("keywords", []):
            keyword_id = keyword_obj.get("id")
            if isinstance(keyword_id, int):
                keyword_ids.append(keyword_id)

        release_year: int | None = None
        release_date = details.get("release_date")
        if isinstance(release_date, str) and len(release_date) >= 4:
            year_str = release_date[:4]
            if year_str.isdigit():
                release_year = int(year_str)

        voted_item = VotedMovieMetadata(
            tmdb_id=vote.tmdb_id,
            vote_enum=vote.vote_enum.value,
            genre_ids=genre_ids,
            keyword_ids=keyword_ids,
            release_year=release_year,
            runtime=details.get("runtime"),
            original_language=details.get("original_language"),
        )
        output.append(voted_item)

    return output


async def build_and_store_taste_profile(
    db: AsyncSession,
    tmdb: TMDbClient,
    user_id: int,
) -> TasteProfile:
    user = await get_user(db, user_id)
    if user is None:
        raise ValueError("User not found")

    voted_metadata = await _collect_voted_metadata(db, tmdb, user_id)

    llm_profile = await build_taste_profile_with_llm(user.country, voted_metadata)
    if llm_profile is not None:
        await set_user_taste_profile(db, user_id, llm_profile.model_dump())
        return llm_profile

    deterministic = build_deterministic_taste_profile(user.country, voted_metadata)
    await set_user_taste_profile(db, user_id, deterministic.model_dump())
    return deterministic
