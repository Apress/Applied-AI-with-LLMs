from app.recommend.scoring import pick_diverse_top_3


def test_pick_diverse_top_3_prefers_different_first_genre() -> None:
    scored = [
        {"id": 1, "genre_ids": [18], "_score": 10},
        {"id": 2, "genre_ids": [18], "_score": 9},
        {"id": 3, "genre_ids": [28], "_score": 8},
        {"id": 4, "genre_ids": [35], "_score": 7},
    ]

    picks = pick_diverse_top_3(scored)

    assert [item["id"] for item in picks] == [1, 3, 4]


def test_pick_diverse_top_3_fills_when_all_first_genres_match() -> None:
    scored = [
        {"id": 1, "genre_ids": [18], "_score": 10},
        {"id": 2, "genre_ids": [18, 28], "_score": 9},
        {"id": 3, "genre_ids": [18, 35], "_score": 8},
        {"id": 4, "genre_ids": [18, 53], "_score": 7},
    ]

    picks = pick_diverse_top_3(scored)

    assert [item["id"] for item in picks] == [1, 2, 3]


def test_pick_diverse_top_3_keeps_score_order_for_movies_without_genres() -> None:
    scored = [
        {"id": 1, "genre_ids": [], "_score": 10},
        {"id": 2, "genre_ids": [], "_score": 9},
        {"id": 3, "_score": 8},
        {"id": 4, "genre_ids": [18], "_score": 7},
    ]

    picks = pick_diverse_top_3(scored)

    assert [item["id"] for item in picks] == [1, 2, 3]


def test_pick_diverse_top_3_returns_all_when_fewer_than_three_candidates() -> None:
    scored = [
        {"id": 1, "genre_ids": [18], "_score": 10},
        {"id": 2, "genre_ids": [28], "_score": 9},
    ]

    picks = pick_diverse_top_3(scored)

    assert [item["id"] for item in picks] == [1, 2]
