from collections import Counter

from app.taste.schema import TasteProfile, VotedMovieMetadata


def _top_ids(counter: Counter[int], limit: int) -> list[int]:
    items = counter.most_common(limit)
    output: list[int] = []
    for item_id, _count in items:
        output.append(item_id)
    return output


def build_deterministic_taste_profile(
    country: str,
    voted_movies: list[VotedMovieMetadata],
) -> TasteProfile:
    liked_genres: Counter[int] = Counter()
    disliked_genres: Counter[int] = Counter()
    liked_keywords: Counter[int] = Counter()
    disliked_keywords: Counter[int] = Counter()
    language_counter: Counter[str] = Counter()
    liked_years: list[int] = []

    for item in voted_movies:
        if item.vote_enum == "like":
            for genre_id in item.genre_ids:
                liked_genres[genre_id] += 1
            for keyword_id in item.keyword_ids:
                liked_keywords[keyword_id] += 1
            if item.original_language:
                language_counter[item.original_language] += 1
            if item.release_year is not None:
                liked_years.append(item.release_year)
        elif item.vote_enum == "dislike":
            for genre_id in item.genre_ids:
                disliked_genres[genre_id] += 1
            for keyword_id in item.keyword_ids:
                disliked_keywords[keyword_id] += 1

    with_genres = _top_ids(liked_genres, 5)
    without_genres = _top_ids(disliked_genres, 5)
    with_keywords = _top_ids(liked_keywords, 10)
    without_keywords = _top_ids(disliked_keywords, 10)

    for genre_id in list(without_genres):
        if genre_id in with_genres:
            without_genres.remove(genre_id)

    for keyword_id in list(without_keywords):
        if keyword_id in with_keywords:
            without_keywords.remove(keyword_id)

    gte_date: str | None = None
    if liked_years:
        min_year = min(liked_years)
        if min_year < 1980:
            min_year = 1980
        gte_date = f"{min_year}-01-01"

    original_language: str | None = None
    if language_counter:
        original_language = language_counter.most_common(1)[0][0]

    explain: list[str] = []
    explain.append("Built from genre and keyword frequency in likes/dislikes")
    if with_genres:
        explain.append("Prioritized liked genres")
    if without_genres:
        explain.append("Penalized disliked genres")

    return TasteProfile(
        country=country,
        with_genre_ids=with_genres,
        without_genre_ids=without_genres,
        with_keyword_ids=with_keywords,
        without_keyword_ids=without_keywords,
        primary_release_date_gte=gte_date,
        vote_average_gte=6.0,
        original_language=original_language,
        sort_by="popularity.desc",
        explain=explain,
    )
