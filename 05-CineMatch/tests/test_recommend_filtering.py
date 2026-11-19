from app.recommend.service import filter_excluded_candidates


def test_filter_excluded_candidates_removes_voted_and_suggested() -> None:
    candidates = [
        {"id": 10, "title": "A"},
        {"id": 20, "title": "B"},
        {"id": 30, "title": "C"},
    ]
    voted = {20}
    suggested = {30}

    filtered = filter_excluded_candidates(candidates, voted, suggested)

    assert [item["id"] for item in filtered] == [10]
