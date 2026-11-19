import pytest

from app.recommend.scoring import compute_candidate_score
from app.recommend.service import (
    _collect_candidates_with_relaxation,
    build_discover_param_sets,
    filter_excluded_candidates,
)
from app.taste.schema import TasteProfile


class FakeTMDb:
    def __init__(self) -> None:
        self.discover_calls: list[dict] = []

    async def discover_movies(self, db, params: dict) -> dict:
        self.discover_calls.append(dict(params))

        if "with_keywords" in params:
            return {
                "results": [{"id": 101, "title": "Strict Match", "genre_ids": [18]}],
                "total_pages": 1,
            }

        if "with_genres" in params:
            return {
                "results": [
                    {"id": 101, "title": "Strict Match", "genre_ids": [18]},
                    {"id": 102, "title": "Relaxed Match 1", "genre_ids": [18, 878]},
                    {"id": 103, "title": "Relaxed Match 2", "genre_ids": [878]},
                ],
                "total_pages": 1,
            }

        return {"results": [{"id": 104, "title": "Broad Match", "genre_ids": [35]}], "total_pages": 1}


def test_build_discover_param_sets_relaxes_constraints() -> None:
    profile = TasteProfile(
        country="IT",
        with_genre_ids=[18, 878],
        with_keyword_ids=[10, 20],
        original_language="en",
        primary_release_date_gte="2015-01-01",
    )

    strategies = build_discover_param_sets(profile)

    assert len(strategies) >= 4
    assert strategies[0]["with_genres"] == "18,878"
    assert strategies[0]["with_keywords"] == "10,20"
    assert "with_keywords" not in strategies[1]
    assert strategies[-1]["sort_by"] == profile.sort_by


def test_compute_candidate_score_rewards_liked_overlap_and_penalizes_disliked_overlap() -> None:
    profile = TasteProfile(
        country="IT",
        with_genre_ids=[18, 878],
        without_genre_ids=[27],
        with_keyword_ids=[10, 20],
        without_keyword_ids=[99],
        original_language="en",
        primary_release_date_gte="2015-01-01",
        vote_average_gte=6.0,
    )

    positive_candidate = {
        "title": "Positive",
        "genre_ids": [18, 878],
        "keyword_ids": [10, 20],
        "original_language": "en",
        "release_date": "2020-01-01",
        "vote_average": 7.2,
        "popularity": 100.0,
    }
    negative_candidate = {
        "title": "Negative",
        "genre_ids": [27],
        "keyword_ids": [99],
        "original_language": "it",
        "release_date": "2010-01-01",
        "vote_average": 5.0,
        "popularity": 100.0,
    }

    positive_score, _positive_reasons = compute_candidate_score(positive_candidate, profile, None)
    negative_score, _negative_reasons = compute_candidate_score(negative_candidate, profile, None)

    assert positive_score > negative_score


def test_filter_excluded_candidates_removes_seen_movies() -> None:
    candidates = [{"id": 1}, {"id": 2}, {"id": 3}]

    filtered = filter_excluded_candidates(candidates, voted_tmdb_ids={2}, suggested_tmdb_ids={3})

    assert [item["id"] for item in filtered] == [1]


@pytest.mark.asyncio
async def test_collect_candidates_with_relaxation_fetches_more_when_strict_query_is_too_small() -> None:
    profile = TasteProfile(
        country="IT",
        with_genre_ids=[18, 878],
        with_keyword_ids=[10],
        original_language="en",
        primary_release_date_gte="2015-01-01",
    )
    tmdb = FakeTMDb()

    candidates = await _collect_candidates_with_relaxation(None, tmdb, profile, target_count=3)

    assert [item["id"] for item in candidates[:3]] == [101, 102, 103]
    assert len(tmdb.discover_calls) >= 2
