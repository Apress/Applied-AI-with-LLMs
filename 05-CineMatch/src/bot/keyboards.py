from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


VOTE_LABELS = {
    "like": "👍 like",
    "dislike": "👎 dislike",
    "never_seen": "❓ never_seen",
}


def movie_disambiguation_keyboard(results: list[dict]) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for item in results:
        movie_id = item["id"]
        title = item.get("title", "Unknown")
        year = (item.get("release_date") or "")[:4]
        label = f"{title} ({year})" if year else title
        buttons.append([InlineKeyboardButton(text=label[:60], callback_data=f"seed:{movie_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def vote_keyboard(movie_id: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=VOTE_LABELS["like"], callback_data=f"vote:{movie_id}:like"),
            InlineKeyboardButton(text=VOTE_LABELS["dislike"], callback_data=f"vote:{movie_id}:dislike"),
        ],
        [InlineKeyboardButton(text=VOTE_LABELS["never_seen"], callback_data=f"vote:{movie_id}:never_seen")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def selected_vote_keyboard(vote_value: str) -> InlineKeyboardMarkup:
    label = VOTE_LABELS.get(vote_value, vote_value)
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=label, callback_data="vote_locked")]]
    )


def regenerate_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔄 Regenerate", callback_data="regen")]]
    )
