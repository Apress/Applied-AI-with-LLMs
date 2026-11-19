# AGENTS.md

This repository contains an MVP Telegram movie recommendation system.

Architecture:
- FastAPI backend
- Telegram bot (aiogram v3)
- PostgreSQL
- TMDb API for metadata + streaming providers + discovery
- LLM step to build a "Taste Profile" from user votes and produce a TMDb /discover query

Goals:
1) Collect user mood/genre and enough preference signals
2) Build a Taste Profile (LLM-driven, with deterministic fallback)
3) Query TMDb /discover using the Taste Profile
4) Rank results deterministically
5) Recommend 3 movies and show where to watch them (country default IT)
6) Allow regenerate without redoing onboarding/interview

Non-goals:
- No manual ingestion of a movie catalog
- No scraping of streaming services
- No hallucination about where-to-watch providers (providers must come from TMDb watch/providers)

---

## Data Sources (TMDb)

Use TMDb API for all movie data.

Required endpoints:
- Search movie: GET /search/movie
- Movie details: GET /movie/{movie_id}
- Movie keywords: GET /movie/{movie_id}/keywords
- Movie credits: GET /movie/{movie_id}/credits
- Watch providers: GET /movie/{movie_id}/watch/providers
- Discover: GET /discover/movie

Hard rule:
- Where-to-watch providers must ONLY come from /watch/providers response.
- If providers are missing for country, say availability is unknown.

---

## Telegram User Flow

/start

Step 1: Ask country (default IT)
Step 2: Ask owned streaming services (optional, comma-separated)
Step 3: Ask mood/genre (free text). Store as mood_text.
Step 4: Ask: "Tell me one movie you liked recently" (free text).
- Search TMDb and disambiguate with top 5 buttons if needed.

Interview phase:
- Show movies one by one with inline buttons:
  👍 like
  👎 dislike
  ❓ never_seen

---

## Voting Rules (IMPORTANT)

Informative votes:
- like
- dislike

Neutral:
- never_seen (does NOT count toward minimum and does NOT contribute to preference inference)

Minimum requirement:
- The system MUST collect at least 7 informative votes (like/dislike) before generating recommendations.
- never_seen votes do NOT count.

Process:
- Initial pool: 10 movies (2 rounds x 5).
- If after 10 movies informative_votes < 7:
  continue with batches of 3 movies until informative_votes >= 7 or user cancels.

---

## Taste Profile (LLM-driven, deterministic fallback)

Once informative_votes >= 7, the system builds a "Taste Profile" from voted movies metadata.

High-level:
- Gather metadata for voted movies (like/dislike):
  - genres (from /movie/{id})
  - keywords (from /movie/{id}/keywords)
  - year, runtime, original_language (from /movie/{id})
  - optional: director/top cast (from /movie/{id}/credits)

Then:
- Use an LLM to produce a strict JSON TasteProfile used to call TMDb /discover/movie.
- If LLM is not configured, use a deterministic fallback builder.

LLM MUST return JSON only (no extra text).

TasteProfile JSON schema (minimum fields):
{
  "country": "IT",
  "with_genre_ids": [878, 18],
  "without_genre_ids": [27],
  "with_keyword_ids": [123, 456],
  "without_keyword_ids": [999],
  "primary_release_date_gte": "2000-01-01",
  "primary_release_date_lte": null,
  "vote_average_gte": 6.5,
  "original_language": "en",
  "sort_by": "popularity.desc",
  "explain": [
    "Likes sci-fi/drama themes based on liked genres and keywords",
    "Avoids horror based on disliked votes"
  ]
}

Mapping to TMDb /discover/movie params:
- with_genres = comma-separated with_genre_ids
- without_genres = comma-separated without_genre_ids
- with_keywords = comma-separated with_keyword_ids
- without_keywords = comma-separated without_keyword_ids
- primary_release_date.gte / .lte from the corresponding fields
- vote_average.gte from vote_average_gte
- with_original_language from original_language (optional)
- sort_by

Guardrails:
- Never output impossible fields.
- Keep lists short (<= 5 genres, <= 10 keywords) for stability.

---

## Recommendation Pipeline (MVP)

1) Precondition: informative_votes >= 7
2) Build TasteProfile (LLM or deterministic fallback)
3) Call TMDb /discover/movie with TasteProfile parameters
4) Generate candidate pool:
   - Fetch multiple pages if needed (explicit loop) to gather ~100 candidates
5) Filter candidates:
   - Remove movies already voted
   - Remove movies already suggested (suggestions history)
6) Score candidates deterministically:
   - Genre match bonus (with_genre_ids)
   - Keyword match bonus (with_keyword_ids)
   - Disliked genre/keyword penalty (without_* lists)
   - Optional: small bonus if matches mood_text (simple keyword contains check)
7) Select top 20 by score
8) Choose final 3 ensuring diversity:
   - Avoid picking 3 items with identical primary genre
9) For each final pick, fetch providers via /watch/providers for the user's country
10) Return message with:
   - title (year)
   - 1–2 line reason derived from scoring features (not creative guessing)
   - where to watch (flatrate/rent/buy), or "availability unknown"

---

## Regenerate Feature

After sending 3 recommendations:
- Show inline button "🔄 Regenerate"
- Support command /more

Regenerate behavior:
- Do NOT redo onboarding or interview.
- Reuse existing votes and stored TasteProfile.
- Exclude previously suggested items (suggestions table).
- If not enough remaining candidates:
  - Fetch more pages from /discover or relax sorting slightly (explicit logic).

---

## Database Schema (minimum)

users:
- id (telegram user id, BIGINT PK)
- country (default 'IT')
- language (default 'it')
- owned_services_json (JSON, nullable)
- mood_text (TEXT, nullable)
- taste_profile_json (JSON, nullable)
- created_at

votes:
- id (PK)
- user_id (FK)
- tmdb_id (INT)
- vote_enum ('like' | 'dislike' | 'never_seen')
- created_at

suggestions:
- id (PK)
- user_id (FK)
- tmdb_id (INT)
- batch_id (UUID)
- created_at

cache:
- key (TEXT PK)
- response_json (JSON)
- expires_at (TIMESTAMP)

---

## Cache TTL Rules

- search: 7 days
- movie details: 7 days
- keywords: 7 days
- credits: 7 days
- watch providers: 24 hours
- discover results: 24 hours (keyed by TasteProfile params + page)

---

## Coding Style Rules (MUST FOLLOW)

Readability > cleverness:
- Use explicit loops and intermediate variables
- Avoid nested list comprehensions and dense one-liners
- Keep functions small and single-purpose
- Use clear logs and early returns
- Code must be easy to step through in a debugger

Error handling:
- TMDb: simple retry/backoff with explicit loops
- Telegram callbacks: validate payload and state; always answer callback queries

---

## Local Development

Env vars:
- TMDB_API_KEY
- TELEGRAM_BOT_TOKEN
- DATABASE_URL
- LLM_PROVIDER (optional, e.g. "none" | "openai_compatible")
- LLM_API_KEY (optional)
- LLM_BASE_URL (optional)
- LLM_MODEL (optional)

Run:
- docker compose up --build

Acceptance criteria:
- docker compose up --build runs api at http://localhost:8000 and bot connects
- GET /health returns ok
- Telegram flow works end-to-end
- Recommendations only generated after >=7 like/dislike votes
- Regenerate returns different recommendations without restarting the interview
- Providers are never hallucinated