import pytest

from app.tmdb.client import build_tmdb_poster_url
from bot.flows.start import _send_movie_message


class DummyMessage:
    def __init__(self) -> None:
        self.answer_calls: list[dict] = []
        self.answer_photo_calls: list[dict] = []

    async def answer(self, text: str, reply_markup=None) -> None:
        self.answer_calls.append({"text": text, "reply_markup": reply_markup})

    async def answer_photo(self, photo: str, caption: str, reply_markup=None) -> None:
        self.answer_photo_calls.append(
            {"photo": photo, "caption": caption, "reply_markup": reply_markup}
        )


def test_build_tmdb_poster_url_returns_full_url() -> None:
    poster_url = build_tmdb_poster_url("/abc123.jpg")

    assert poster_url == "https://image.tmdb.org/t/p/w500/abc123.jpg"


def test_build_tmdb_poster_url_returns_none_for_missing_path() -> None:
    assert build_tmdb_poster_url(None) is None
    assert build_tmdb_poster_url("") is None
    assert build_tmdb_poster_url("   ") is None


@pytest.mark.asyncio
async def test_send_movie_message_falls_back_to_text_when_poster_missing() -> None:
    message = DummyMessage()

    await _send_movie_message(
        message,
        caption="Movie Title (2024)",
        poster_path=None,
    )

    assert message.answer_photo_calls == []
    assert message.answer_calls == [{"text": "Movie Title (2024)", "reply_markup": None}]


@pytest.mark.asyncio
async def test_send_movie_message_uses_photo_when_poster_exists() -> None:
    message = DummyMessage()

    await _send_movie_message(
        message,
        caption="Movie Title (2024)",
        poster_path="/poster.jpg",
    )

    assert message.answer_calls == []
    assert message.answer_photo_calls == [
        {
            "photo": "https://image.tmdb.org/t/p/w500/poster.jpg",
            "caption": "Movie Title (2024)",
            "reply_markup": None,
        }
    ]
