import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.db import crud
from app.db.models import VoteEnum
from app.db.session import SessionLocal
from app.recommend.service import generate_recommendations, regenerate_recommendations
from app.taste.schema import TasteProfile
from app.taste.service import build_and_store_taste_profile
from app.tmdb.client import build_tmdb_poster_url, tmdb_client
from bot.keyboards import (
    movie_disambiguation_keyboard,
    regenerate_keyboard,
    selected_vote_keyboard,
    vote_keyboard,
)
from bot.text import (
    ASK_COUNTRY,
    ASK_LIKED_MOVIE,
    ASK_MOOD,
    ASK_SERVICES,
    INTERVIEW_INTRO,
    NOT_ENOUGH_VOTES,
    START_WELCOME,
)

logger = logging.getLogger(__name__)

router = Router()


class OnboardingState(StatesGroup):
    waiting_country = State()
    waiting_services = State()
    waiting_mood = State()
    waiting_liked_movie = State()
    waiting_seed_pick = State()
    interviewing = State()


async def _build_interview_candidates(
    user_id: int,
    state: FSMContext,
    minimum_to_add: int,
) -> None:
    data = await state.get_data()
    seed_movie_id = data.get("seed_movie_id")
    discover_page = int(data.get("discover_page", 1))
    queued_movies = list(data.get("queued_movies", []))
    shown_ids = set(data.get("shown_ids", []))

    async with SessionLocal() as db:
        user = await crud.get_user(db, user_id)
        if user is None:
            return

        seed_details = await tmdb_client.movie_details(db, seed_movie_id)
        seed_genres: list[int] = []
        for genre_obj in seed_details.get("genres", []):
            genre_id = genre_obj.get("id")
            if isinstance(genre_id, int):
                seed_genres.append(genre_id)

        voted_ids = await crud.get_voted_tmdb_ids(db, user_id)

        while len(queued_movies) < minimum_to_add:
            params: dict[str, str | int] = {
                "sort_by": "popularity.desc",
                "include_adult": "false",
                "page": discover_page,
            }
            if seed_genres:
                params["with_genres"] = ",".join(str(item) for item in seed_genres[:3])

            response = await tmdb_client.discover_movies(db, params)
            results = response.get("results", [])

            for result in results:
                movie_id = result.get("id")
                if not isinstance(movie_id, int):
                    continue
                if movie_id == seed_movie_id:
                    continue
                if movie_id in shown_ids:
                    continue
                if movie_id in voted_ids:
                    continue

                title = result.get("title") or "Unknown"
                year = (result.get("release_date") or "")[:4]
                queued_movies.append(
                    {
                        "id": movie_id,
                        "title": title,
                        "year": year,
                        "poster_path": result.get("poster_path"),
                    }
                )
                shown_ids.add(movie_id)

                if len(queued_movies) >= minimum_to_add:
                    break

            discover_page += 1
            total_pages = int(response.get("total_pages", 1))
            if discover_page > total_pages:
                discover_page = 1

            if discover_page > 50:
                break

    await state.update_data(
        queued_movies=queued_movies,
        shown_ids=list(shown_ids),
        discover_page=discover_page,
    )


async def _send_next_interview_movie(message: Message, state: FSMContext) -> bool:
    data = await state.get_data()
    queued_movies = list(data.get("queued_movies", []))

    if not queued_movies:
        return False

    movie = queued_movies.pop(0)
    await state.update_data(queued_movies=queued_movies)

    caption = _format_movie_title_year(movie)
    await _send_movie_message(
        message,
        caption=caption,
        poster_path=movie.get("poster_path"),
        reply_markup=vote_keyboard(movie["id"]),
    )
    return True


def _format_movie_title_year(movie: dict) -> str:
    title = movie.get("title") or "Unknown"
    year = movie.get("year") or ""
    if year:
        return f"{title} ({year})"
    return title


def _format_recommendation_caption(item: dict) -> str:
    lines: list[str] = [_format_movie_title_year(item)]
    reason = item.get("reason")
    if reason:
        lines.append(f"Reason: {reason}")

    providers = item.get("providers", {})
    flatrate = providers.get("flatrate", [])
    rent = providers.get("rent", [])
    buy = providers.get("buy", [])
    availability_text = providers.get("availability_text", "")

    if availability_text:
        lines.append(availability_text)
    else:
        if flatrate:
            lines.append(f"Flatrate: {', '.join(flatrate)}")
        if rent:
            lines.append(f"Rent: {', '.join(rent)}")
        if buy:
            lines.append(f"Buy: {', '.join(buy)}")

    return "\n".join(lines)


async def _send_movie_message(
    message: Message,
    caption: str,
    poster_path: str | None,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    poster_url = build_tmdb_poster_url(poster_path)
    if poster_url:
        try:
            await message.answer_photo(photo=poster_url, caption=caption, reply_markup=reply_markup)
            return
        except TelegramBadRequest:
            logger.warning("Falling back to text for invalid TMDb poster: %s", poster_url, exc_info=True)

    await message.answer(caption, reply_markup=reply_markup)


async def _send_recommendations(message: Message, payload: dict, country: str) -> None:
    recommendations = payload.get("recommendations", [])
    if not recommendations:
        await message.answer(f"No recommendations available for {country}.")
        return

    for index, item in enumerate(recommendations):
        reply_markup = regenerate_keyboard() if index == len(recommendations) - 1 else None
        await _send_movie_message(
            message,
            caption=_format_recommendation_caption(item),
            poster_path=item.get("poster_path"),
            reply_markup=reply_markup,
        )


async def _generate_and_send_recommendations(message: Message, user_id: int) -> None:
    async with SessionLocal() as db:
        informative_votes = await crud.count_informative_votes(db, user_id)
        if informative_votes < 7:
            await message.answer(NOT_ENOUGH_VOTES)
            return

        user = await crud.get_user(db, user_id)
        if user is None:
            await message.answer("User not found. Send /start again.")
            return

        if user.taste_profile_json:
            taste_profile = TasteProfile.model_validate(user.taste_profile_json)
        else:
            taste_profile = await build_and_store_taste_profile(db, tmdb_client, user_id)

        payload = await generate_recommendations(db, tmdb_client, user_id, taste_profile)
        await _send_recommendations(message, payload, user.country)


@router.message(Command("start"))
async def start(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    async with SessionLocal() as db:
        await crud.upsert_user(db, user_id)
        await crud.reset_user_recommendation_state(db, user_id)

    await state.clear()
    await state.set_state(OnboardingState.waiting_country)
    await message.answer(START_WELCOME)
    await message.answer(ASK_COUNTRY)


@router.message(OnboardingState.waiting_country)
async def receive_country(message: Message, state: FSMContext) -> None:
    country_text = (message.text or "").strip().upper()
    country = country_text if country_text else "IT"
    if len(country) != 2:
        country = "IT"

    await state.update_data(country=country)
    await state.set_state(OnboardingState.waiting_services)
    await message.answer(ASK_SERVICES)


@router.message(OnboardingState.waiting_services)
async def receive_services(message: Message, state: FSMContext) -> None:
    raw_text = (message.text or "").strip()
    services: list[str] = []
    if raw_text.lower() != "skip" and raw_text:
        parts = raw_text.split(",")
        for part in parts:
            cleaned = part.strip()
            if cleaned:
                services.append(cleaned)

    await state.update_data(services=services)
    await state.set_state(OnboardingState.waiting_mood)
    await message.answer(ASK_MOOD)


@router.message(OnboardingState.waiting_mood)
async def receive_mood(message: Message, state: FSMContext) -> None:
    mood_text = (message.text or "").strip()
    await state.update_data(mood_text=mood_text)
    await state.set_state(OnboardingState.waiting_liked_movie)
    await message.answer(ASK_LIKED_MOVIE)


@router.message(OnboardingState.waiting_liked_movie)
async def receive_liked_movie(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()
    if not query:
        await message.answer("Please type a movie title.")
        return

    async with SessionLocal() as db:
        response = await tmdb_client.search_movie(db, query=query)

    results = response.get("results", [])[:5]
    if not results:
        await message.answer("No results found, try another title.")
        return

    await state.update_data(seed_candidates=results)
    await state.set_state(OnboardingState.waiting_seed_pick)
    await message.answer("Pick the right movie:", reply_markup=movie_disambiguation_keyboard(results))


@router.callback_query(OnboardingState.waiting_seed_pick, F.data.startswith("seed:"))
async def pick_seed_movie(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    user_id = callback.from_user.id

    data = await state.get_data()
    country = data.get("country", "IT")
    services = data.get("services", [])
    mood_text = data.get("mood_text", "")

    seed_movie_id = int(callback.data.split(":", 1)[1])

    async with SessionLocal() as db:
        await crud.update_user_onboarding(db, user_id, country=country, owned_services=services, mood_text=mood_text)

    await state.update_data(
        seed_movie_id=seed_movie_id,
        queued_movies=[],
        shown_ids=[],
        interview_total_shown=0,
        interview_target=10,
        discover_page=1,
    )
    await state.set_state(OnboardingState.interviewing)

    await callback.message.answer(INTERVIEW_INTRO)
    await _build_interview_candidates(user_id, state, minimum_to_add=10)

    sent = await _send_next_interview_movie(callback.message, state)
    if not sent:
        await callback.message.answer("Could not start interview. Try /start again.")


@router.callback_query(OnboardingState.interviewing, F.data.startswith("vote:"))
async def handle_vote(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    user_id = callback.from_user.id

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.message.answer("Invalid vote payload")
        return

    movie_id = int(parts[1])
    vote_value = parts[2]
    if vote_value not in {"like", "dislike", "never_seen"}:
        await callback.message.answer("Invalid vote value")
        return

    async with SessionLocal() as db:
        await crud.add_vote(db, user_id, movie_id, VoteEnum(vote_value))
        informative_votes = await crud.count_informative_votes(db, user_id)

    if callback.message is not None:
        try:
            await callback.message.edit_reply_markup(reply_markup=selected_vote_keyboard(vote_value))
        except TelegramBadRequest:
            logger.warning("Could not lock vote keyboard for movie %s", movie_id, exc_info=True)

    if informative_votes >= 7:
        await state.clear()
        await _generate_and_send_recommendations(callback.message, user_id)
        return

    data = await state.get_data()
    interview_total_shown = int(data.get("interview_total_shown", 0)) + 1
    interview_target = int(data.get("interview_target", 10))
    await state.update_data(interview_total_shown=interview_total_shown)

    queued_movies = list(data.get("queued_movies", []))
    if not queued_movies:
        need_more = 1
        await _build_interview_candidates(user_id, state, minimum_to_add=need_more)

    sent = await _send_next_interview_movie(callback.message, state)
    if sent:
        return

    if interview_total_shown >= interview_target and informative_votes < 7:
        interview_target += 3
        await state.update_data(interview_target=interview_target)
        await callback.message.answer(
            f"Informative votes: {informative_votes}/7. Extending interview by 3 movies."
        )
        await _build_interview_candidates(user_id, state, minimum_to_add=3)
        sent_after_extend = await _send_next_interview_movie(callback.message, state)
        if sent_after_extend:
            return

    await callback.message.answer("No more interview movies available now. Send /start to retry.")


@router.callback_query(F.data == "vote_locked")
async def ignore_locked_vote(callback: CallbackQuery) -> None:
    await callback.answer("Vote already recorded.")


@router.callback_query(F.data == "regen")
async def regenerate_from_button(callback: CallbackQuery) -> None:
    await callback.answer()
    user_id = callback.from_user.id

    async with SessionLocal() as db:
        informative_votes = await crud.count_informative_votes(db, user_id)
        if informative_votes < 7:
            await callback.message.answer(NOT_ENOUGH_VOTES)
            return

        user = await crud.get_user(db, user_id)
        if user is None:
            await callback.message.answer("User not found. Send /start again.")
            return

        if user.taste_profile_json is None:
            taste_profile = await build_and_store_taste_profile(db, tmdb_client, user_id)
        else:
            taste_profile = TasteProfile.model_validate(user.taste_profile_json)

        payload = await regenerate_recommendations(db, tmdb_client, user_id, taste_profile)
        await _send_recommendations(callback.message, payload, user.country)


@router.message(Command("more"))
async def regenerate_from_command(message: Message) -> None:
    user_id = message.from_user.id

    async with SessionLocal() as db:
        informative_votes = await crud.count_informative_votes(db, user_id)
        if informative_votes < 7:
            await message.answer(NOT_ENOUGH_VOTES)
            return

        user = await crud.get_user(db, user_id)
        if user is None:
            await message.answer("User not found. Send /start again.")
            return

        if user.taste_profile_json is None:
            taste_profile = await build_and_store_taste_profile(db, tmdb_client, user_id)
        else:
            taste_profile = TasteProfile.model_validate(user.taste_profile_json)

        payload = await regenerate_recommendations(db, tmdb_client, user_id, taste_profile)
        await _send_recommendations(message, payload, user.country)


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Cancelled. Send /start to begin again.")
