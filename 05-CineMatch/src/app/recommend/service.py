from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud import (
    add_suggestions_batch,
    get_suggested_tmdb_ids,
    get_user,
    get_voted_tmdb_ids,
)
from app.recommend.scoring import compute_candidate_score, pick_diverse_top_3
from app.taste.schema import TasteProfile
from app.tmdb.client import TMDbClient


DISCOVER_PAGE_LIMIT = 5
ENRICH_LIMIT = 40


def taste_profile_to_discover_params(taste_profile: TasteProfile, page: int) -> dict[str, Any]:
    params: dict[str, Any] = {
        "include_adult": "false",
        "include_video": "false",
        "sort_by": taste_profile.sort_by,
        "page": page,
    }

    if taste_profile.with_genre_ids:
        params["with_genres"] = ",".join(str(item) for item in taste_profile.with_genre_ids)
    if taste_profile.without_genre_ids:
        params["without_genres"] = ",".join(str(item) for item in taste_profile.without_genre_ids)
    if taste_profile.with_keyword_ids:
        params["with_keywords"] = ",".join(str(item) for item in taste_profile.with_keyword_ids)
    if taste_profile.without_keyword_ids:
        params["without_keywords"] = ",".join(str(item) for item in taste_profile.without_keyword_ids)
    if taste_profile.primary_release_date_gte:
        params["primary_release_date.gte"] = taste_profile.primary_release_date_gte
    if taste_profile.primary_release_date_lte:
        params["primary_release_date.lte"] = taste_profile.primary_release_date_lte
    params["vote_average.gte"] = str(taste_profile.vote_average_gte)
    if taste_profile.original_language:
        params["with_original_language"] = taste_profile.original_language
    return params


def build_discover_param_sets(taste_profile: TasteProfile) -> list[dict[str, Any]]:
    common_params: dict[str, Any] = {
        "include_adult": "false",
        "include_video": "false",
        "sort_by": taste_profile.sort_by,
    }

    top_genres = taste_profile.with_genre_ids[:3]
    top_keywords = taste_profile.with_keyword_ids[:5]

    strategy_blueprints = [
        {
            "with_genres": top_genres,
            "with_keywords": top_keywords,
            "with_original_language": taste_profile.original_language,
            "primary_release_date.gte": taste_profile.primary_release_date_gte,
        },
        {
            "with_genres": top_genres,
            "with_original_language": taste_profile.original_language,
            "primary_release_date.gte": taste_profile.primary_release_date_gte,
        },
        {
            "with_genres": top_genres,
            "primary_release_date.gte": taste_profile.primary_release_date_gte,
        },
        {
            "with_genres": top_genres,
            "with_original_language": taste_profile.original_language,
        },
        {
            "with_genres": top_genres,
        },
        {
            "with_original_language": taste_profile.original_language,
            "primary_release_date.gte": taste_profile.primary_release_date_gte,
        },
        {
            "primary_release_date.gte": taste_profile.primary_release_date_gte,
        },
        {},
    ]

    output: list[dict[str, Any]] = []
    seen_signatures: set[tuple[tuple[str, str], ...]] = set()

    for blueprint in strategy_blueprints:
        params = dict(common_params)

        genres = blueprint.get("with_genres", [])
        if genres:
            params["with_genres"] = ",".join(str(item) for item in genres)

        keywords = blueprint.get("with_keywords", [])
        if keywords:
            params["with_keywords"] = ",".join(str(item) for item in keywords)

        language = blueprint.get("with_original_language")
        if language:
            params["with_original_language"] = language

        gte_date = blueprint.get("primary_release_date.gte")
        if gte_date:
            params["primary_release_date.gte"] = gte_date

        signature = tuple(sorted((key, str(value)) for key, value in params.items()))
        if signature in seen_signatures:
            continue

        seen_signatures.add(signature)
        output.append(params)

    return output


def filter_excluded_candidates(
    raw_candidates: list[dict],
    voted_tmdb_ids: set[int],
    suggested_tmdb_ids: set[int],
) -> list[dict]:
    filtered: list[dict] = []
    for candidate in raw_candidates:
        candidate_id = candidate.get("id")
        if not isinstance(candidate_id, int):
            continue
        if candidate_id in voted_tmdb_ids:
            continue
        if candidate_id in suggested_tmdb_ids:
            continue
        filtered.append(candidate)
    return filtered


def _merge_unique_candidates(existing: list[dict], new_items: list[dict]) -> list[dict]:
    seen_ids: set[int] = set()
    output: list[dict] = []

    for item in existing:
        item_id = item.get("id")
        if isinstance(item_id, int):
            seen_ids.add(item_id)
        output.append(item)

    for item in new_items:
        item_id = item.get("id")
        if not isinstance(item_id, int):
            continue
        if item_id in seen_ids:
            continue
        output.append(item)
        seen_ids.add(item_id)

    return output


async def _collect_candidates_with_relaxation(
    db: AsyncSession,
    tmdb: TMDbClient,
    taste_profile: TasteProfile,
    target_count: int = 100,
) -> list[dict]:
    candidates: list[dict] = []
    strategies = build_discover_param_sets(taste_profile)

    for strategy in strategies:
        page = 1
        while len(candidates) < target_count and page <= DISCOVER_PAGE_LIMIT:
            params = dict(strategy)
            params["page"] = page
            response_json = await tmdb.discover_movies(db, params)

            results = response_json.get("results", [])
            candidates = _merge_unique_candidates(candidates, results)

            total_pages = int(response_json.get("total_pages", 1))
            if page >= total_pages:
                break
            page += 1

        if len(candidates) >= target_count:
            break

    return candidates


async def _enrich_candidates_for_scoring(
    db: AsyncSession,
    tmdb: TMDbClient,
    candidates: list[dict],
) -> list[dict]:
    enriched_candidates: list[dict] = []

    for index, candidate in enumerate(candidates):
        candidate_copy = dict(candidate)
        movie_id = candidate_copy.get("id")

        if not isinstance(movie_id, int):
            enriched_candidates.append(candidate_copy)
            continue

        if index >= ENRICH_LIMIT:
            candidate_copy["keyword_ids"] = []
            enriched_candidates.append(candidate_copy)
            continue

        details = await tmdb.movie_details(db, movie_id)
        keywords_response = await tmdb.movie_keywords(db, movie_id)

        genre_ids: list[int] = []
        for genre_obj in details.get("genres", []):
            genre_id = genre_obj.get("id")
            if isinstance(genre_id, int):
                genre_ids.append(genre_id)
        if genre_ids:
            candidate_copy["genre_ids"] = genre_ids

        keyword_ids: list[int] = []
        for keyword_obj in keywords_response.get("keywords", []):
            keyword_id = keyword_obj.get("id")
            if isinstance(keyword_id, int):
                keyword_ids.append(keyword_id)
        candidate_copy["keyword_ids"] = keyword_ids

        for field_name in [
            "original_language",
            "release_date",
            "vote_average",
            "popularity",
            "poster_path",
            "overview",
            "title",
        ]:
            if details.get(field_name) is not None:
                candidate_copy[field_name] = details.get(field_name)

        enriched_candidates.append(candidate_copy)

    return enriched_candidates


async def _build_pick_response(
    db: AsyncSession,
    tmdb: TMDbClient,
    picks: list[dict],
    reasons_map: dict[int, list[str]],
    country: str,
) -> list[dict]:
    output: list[dict] = []

    for pick in picks:
        movie_id = pick["id"]
        providers_response = await tmdb.watch_providers(db, movie_id)
        country_result = providers_response.get("results", {}).get(country)

        providers_payload = {
            "flatrate": [],
            "rent": [],
            "buy": [],
            "availability_text": f"Availability unknown in {country}",
        }

        if country_result:
            providers_payload["availability_text"] = ""
            for key in ["flatrate", "rent", "buy"]:
                raw_items = country_result.get(key, [])
                names: list[str] = []
                for provider in raw_items:
                    provider_name = provider.get("provider_name")
                    if isinstance(provider_name, str):
                        names.append(provider_name)
                providers_payload[key] = names

            has_any = False
            for key in ["flatrate", "rent", "buy"]:
                if providers_payload[key]:
                    has_any = True
            if not has_any:
                providers_payload["availability_text"] = f"Availability unknown in {country}"

        reason_list = reasons_map.get(movie_id, ["Matches your discovered taste profile"])
        reason_text = "; ".join(reason_list[:2])

        output.append(
            {
                "tmdb_id": movie_id,
                "title": pick.get("title"),
                "year": (pick.get("release_date") or "")[:4],
                "poster_path": pick.get("poster_path"),
                "reason": reason_text,
                "providers": providers_payload,
            }
        )

    return output


async def generate_recommendations(
    db: AsyncSession,
    tmdb: TMDbClient,
    user_id: int,
    taste_profile: TasteProfile,
) -> dict:
    user = await get_user(db, user_id)
    if user is None:
        raise ValueError("User not found")

    candidates = await _collect_candidates_with_relaxation(db, tmdb, taste_profile, target_count=120)

    voted_tmdb_ids = await get_voted_tmdb_ids(db, user_id)
    suggested_tmdb_ids = await get_suggested_tmdb_ids(db, user_id)

    filtered_candidates = filter_excluded_candidates(candidates, voted_tmdb_ids, suggested_tmdb_ids)
    enriched_candidates = await _enrich_candidates_for_scoring(db, tmdb, filtered_candidates)

    scored: list[dict] = []
    reasons_map: dict[int, list[str]] = {}
    for candidate in enriched_candidates:
        score, reasons = compute_candidate_score(candidate, taste_profile, user.mood_text)
        candidate_copy = dict(candidate)
        candidate_copy["_score"] = score
        scored.append(candidate_copy)
        candidate_id = candidate.get("id")
        if isinstance(candidate_id, int):
            reasons_map[candidate_id] = reasons

    scored.sort(key=lambda item: item.get("_score", 0.0), reverse=True)

    top20: list[dict] = []
    for item in scored[:20]:
        top20.append(item)

    final_picks = pick_diverse_top_3(top20)

    final_ids: list[int] = []
    for item in final_picks:
        final_ids.append(item["id"])

    batch_id = await add_suggestions_batch(db, user_id, final_ids)
    results = await _build_pick_response(db, tmdb, final_picks, reasons_map, user.country)

    return {
        "batch_id": batch_id,
        "taste_profile": taste_profile.model_dump(),
        "recommendations": results,
    }


async def regenerate_recommendations(
    db: AsyncSession,
    tmdb: TMDbClient,
    user_id: int,
    taste_profile: TasteProfile,
) -> dict:
    return await generate_recommendations(db, tmdb, user_id, taste_profile)
