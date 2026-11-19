from app.taste.deterministic import build_deterministic_taste_profile
from app.taste.schema import VotedMovieMetadata


def test_deterministic_profile_counts_and_filters() -> None:
    voted_movies = [
        VotedMovieMetadata(
            tmdb_id=1,
            vote_enum="like",
            genre_ids=[18, 878],
            keyword_ids=[10, 20],
            release_year=2015,
            runtime=120,
            original_language="en",
        ),
        VotedMovieMetadata(
            tmdb_id=2,
            vote_enum="like",
            genre_ids=[18],
            keyword_ids=[10],
            release_year=2019,
            runtime=110,
            original_language="en",
        ),
        VotedMovieMetadata(
            tmdb_id=3,
            vote_enum="dislike",
            genre_ids=[27],
            keyword_ids=[99],
            release_year=2010,
            runtime=95,
            original_language="it",
        ),
    ]

    profile = build_deterministic_taste_profile("IT", voted_movies)

    assert 18 in profile.with_genre_ids
    assert 27 in profile.without_genre_ids
    assert 10 in profile.with_keyword_ids
    assert 99 in profile.without_keyword_ids
    assert profile.original_language == "en"
    assert profile.primary_release_date_gte == "2015-01-01"
