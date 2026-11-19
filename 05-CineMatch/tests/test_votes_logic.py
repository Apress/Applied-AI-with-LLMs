from app.db.crud import count_informative_votes_from_values


def test_count_informative_votes_from_values() -> None:
    values = ["like", "never_seen", "dislike", "like", "never_seen"]
    assert count_informative_votes_from_values(values) == 3
