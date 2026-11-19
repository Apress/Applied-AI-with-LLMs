from app.taste.schema import TasteProfile


def _extract_release_year(candidate: dict) -> int | None:
    release_date = candidate.get("release_date")
    if not isinstance(release_date, str) or len(release_date) < 4:
        return None

    year_text = release_date[:4]
    if not year_text.isdigit():
        return None

    return int(year_text)


def compute_candidate_score(
    candidate: dict,
    taste_profile: TasteProfile,
    mood_text: str | None,
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    candidate_genres = candidate.get("genre_ids") or []
    candidate_keywords = candidate.get("keyword_ids") or []

    genre_match_count = 0
    for genre_id in candidate_genres:
        if genre_id in taste_profile.with_genre_ids:
            genre_match_count += 1
    if genre_match_count > 0:
        bonus = genre_match_count * 3.0
        score += bonus
        reasons.append(f"genre match x{genre_match_count}")

    disliked_genre_count = 0
    for genre_id in candidate_genres:
        if genre_id in taste_profile.without_genre_ids:
            disliked_genre_count += 1
    if disliked_genre_count > 0:
        penalty = disliked_genre_count * 4.0
        score -= penalty
        reasons.append(f"disliked genre penalty x{disliked_genre_count}")

    keyword_match_count = 0
    for keyword_id in candidate_keywords:
        if keyword_id in taste_profile.with_keyword_ids:
            keyword_match_count += 1
    if keyword_match_count > 0:
        bonus = keyword_match_count * 1.5
        score += bonus
        reasons.append(f"keyword match x{keyword_match_count}")

    disliked_keyword_count = 0
    for keyword_id in candidate_keywords:
        if keyword_id in taste_profile.without_keyword_ids:
            disliked_keyword_count += 1
    if disliked_keyword_count > 0:
        penalty = disliked_keyword_count * 2.0
        score -= penalty
        reasons.append(f"disliked keyword penalty x{disliked_keyword_count}")

    candidate_language = candidate.get("original_language")
    if (
        isinstance(candidate_language, str)
        and taste_profile.original_language
        and candidate_language == taste_profile.original_language
    ):
        score += 1.2
        reasons.append("language match")

    if taste_profile.primary_release_date_gte:
        minimum_year_text = taste_profile.primary_release_date_gte[:4]
        candidate_year = _extract_release_year(candidate)
        if minimum_year_text.isdigit() and candidate_year is not None:
            minimum_year = int(minimum_year_text)
            if candidate_year >= minimum_year:
                score += 0.8
                reasons.append("recency match")
            else:
                score -= 0.5

    vote_average = candidate.get("vote_average")
    if isinstance(vote_average, float | int):
        if vote_average >= taste_profile.vote_average_gte:
            score += 1.0

    if mood_text:
        mood = mood_text.strip().lower()
        title = str(candidate.get("title") or "").lower()
        overview = str(candidate.get("overview") or "").lower()
        if mood and (mood in title or mood in overview):
            score += 0.5
            reasons.append("mood text match")

    popularity = candidate.get("popularity")
    if isinstance(popularity, float | int):
        score += min(float(popularity) / 1000.0, 0.8)

    if not reasons:
        reasons.append("baseline discover ranking")

    return score, reasons

def pick_diverse_top_3(scored_candidates: list[dict]) -> list[dict]:
    selected: list[dict] = []
    selected_first_genre_ids: set[int] = set()

    # TMDb does not define genre_ids[0] as a canonical "primary genre".
    # We use the first returned genre only as a lightweight diversity heuristic.
    for item in scored_candidates:
        if len(selected) >= 3:
            break

        candidate_genres = item.get("genre_ids") or []
        first_genre_id = candidate_genres[0] if candidate_genres else None

        if (
            first_genre_id is not None
            and first_genre_id in selected_first_genre_ids
        ):
            continue

        selected.append(item)

        if first_genre_id is not None:
            selected_first_genre_ids.add(first_genre_id)

    # Diversity is a preference, not a hard constraint. If the first pass
    # cannot produce three items, fill the remaining slots by score order.
    if len(selected) < 3:
        for item in scored_candidates:
            if len(selected) >= 3:
                break

            if item in selected:
                continue

            selected.append(item)

    return selected
