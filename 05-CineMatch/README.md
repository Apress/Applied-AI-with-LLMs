# Film Suggestion Bot

Telegram movie recommendation MVP built with FastAPI, aiogram, PostgreSQL, and TMDb.

The project collects a user's mood and movie preferences, turns those signals into a structured taste profile, queries TMDb discovery endpoints, scores candidates deterministically, and returns 3 movie suggestions with provider availability for the user's country.

## Table of Contents

- [What This Project Does](#what-this-project-does)
- [Core Features](#core-features)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Requirements](#requirements)
- [Environment Variables](#environment-variables)
- [Quick Start With Docker](#quick-start-with-docker)
- [Local Development Without Docker](#local-development-without-docker)
- [How the Telegram Flow Works](#how-the-telegram-flow-works)
- [Recommendation Pipeline](#recommendation-pipeline)
- [Taste Profile Generation](#taste-profile-generation)
- [API Endpoints](#api-endpoints)
- [Database Model](#database-model)
- [Caching Rules](#caching-rules)
- [Running Tests and Checks](#running-tests-and-checks)
- [Troubleshooting](#troubleshooting)
- [Known Limitations](#known-limitations)

## What This Project Does

This repository contains an MVP recommendation system with two runtime components:

- A FastAPI backend that exposes health, TMDb helper, taste-profile, and recommendation endpoints.
- A Telegram bot that manages onboarding, interview voting, and recommendation delivery.

The recommendation flow is intentionally constrained:

- Movie metadata comes from TMDb.
- Streaming providers come only from TMDb `/watch/providers`.
- Recommendations are generated only after at least 7 informative votes.
- `never_seen` votes are stored, but they do not count toward the minimum vote threshold.

## Core Features

- Telegram onboarding flow with country, owned services, mood, and a seed movie.
- Seed movie search and disambiguation through TMDb.
- Interview phase with inline voting: `like`, `dislike`, `never_seen`.
- Minimum 7 informative votes before recommendations are allowed.
- Taste profile generation from voted movie metadata.
- Optional LLM-driven taste profile generation with deterministic fallback.
- Deterministic scoring and diversity-aware final selection.
- Provider output per country with explicit `availability unknown` fallback.
- Regenerate flow that reuses stored preferences and excludes already suggested movies.
- Database-backed caching for TMDb calls.

## Architecture Overview

High-level flow:

1. User starts the Telegram bot with `/start`.
2. The bot collects country, owned streaming services, mood text, and one liked movie.
3. The bot uses the liked movie as a seed to build an interview pool from TMDb Discover.
4. The user votes on movies.
5. Once the user reaches 7 informative votes, the system builds a taste profile.
6. The backend discovers candidate movies from TMDb, filters previous votes and suggestions, scores candidates, and picks 3 diverse recommendations.
7. The bot sends the final recommendations with reasons and provider availability.
8. The user can request more recommendations with `/more` or the regenerate button.

## Project Structure

```text
film_suggestion_bot/
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py
├── src/
│   ├── app/
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   ├── crud.py
│   │   │   ├── models.py
│   │   │   └── session.py
│   │   ├── recommend/
│   │   │   ├── scoring.py
│   │   │   └── service.py
│   │   ├── taste/
│   │   │   ├── deterministic.py
│   │   │   ├── llm.py
│   │   │   ├── schema.py
│   │   │   └── service.py
│   │   ├── tmdb/
│   │   │   └── client.py
│   │   ├── main.py
│   │   └── settings.py
│   └── bot/
│       ├── flows/
│       │   └── start.py
│       ├── keyboards.py
│       ├── main.py
│       └── text.py
├── tests/
│   ├── test_diversity_selection.py
│   ├── test_movie_posters.py
│   ├── test_recommend_filtering.py
│   ├── test_recommend_pipeline.py
│   ├── test_taste_deterministic.py
│   └── test_votes_logic.py
├── .env.example
├── AGENTS.md
├── alembic.ini
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.bot
└── pyproject.toml
```

### Directory Guide

- `src/app/main.py`: FastAPI entrypoint and API routes.
- `src/app/settings.py`: environment-based configuration.
- `src/app/db/`: SQLAlchemy models, sessions, and CRUD helpers.
- `src/app/tmdb/client.py`: TMDb HTTP client with retry logic and DB-backed caching.
- `src/app/taste/`: taste profile schema and builders.
- `src/app/recommend/`: candidate collection, filtering, scoring, and final selection.
- `src/bot/main.py`: Telegram bot entrypoint.
- `src/bot/flows/start.py`: onboarding, interview, voting, and regenerate flow.
- `alembic/`: database migrations.
- `tests/`: unit tests for voting logic, scoring, filtering, and selection behavior.

## Tech Stack

- Python 3.12
- FastAPI
- aiogram v3
- SQLAlchemy asyncio
- PostgreSQL 16
- Alembic
- httpx
- TMDb API
- Optional Gemini LLM integration through Google's OpenAI-compatible Chat Completions endpoint
- Docker Compose

## Requirements

To run the project you need:

- Docker and Docker Compose
- Or Python 3.12 and PostgreSQL if running locally without Docker
- A TMDb API key
- A Telegram bot token from BotFather

Optional:

- An LLM API key and base URL if you want LLM-driven taste profile generation

## Environment Variables

Copy `.env.example` to `.env` and fill in the values.

```env
TMDB_API_KEY=
TELEGRAM_BOT_TOKEN=
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/film_bot
- `LLM_PROVIDER`: optional. Use `none` to disable the LLM path or `gemini` to enable Gemini.
- `LLM_API_KEY`: required when `LLM_PROVIDER=gemini`. Use a Gemini API key created in Google AI Studio.
- `LLM_BASE_URL`: Gemini OpenAI-compatible API base URL. Defaults to `https://generativelanguage.googleapis.com/v1beta/openai`.
- `LLM_MODEL`: Gemini model used for taste-profile generation. Defaults to `gemini-2.5-flash-lite`.
LOG_LEVEL=INFO
```

If LLM_PROVIDER=none, if the API key is missing, or if the LLM request fails, taste-profile generation falls back to the deterministic implementation.

### Variable Reference

- `TMDB_API_KEY`: required, used for all TMDb requests.
- `TELEGRAM_BOT_TOKEN`: required, used by the Telegram bot.
- `DATABASE_URL`: required, async SQLAlchemy connection string.
- `LLM_PROVIDER`: optional. Use `none` to disable LLM usage.
- `LLM_API_KEY`: optional. Required only if an external LLM provider is enabled.
- `LLM_BASE_URL`: optional. Base URL for an OpenAI-compatible endpoint.
- `LLM_MODEL`: optional. Model name used by the LLM taste-profile builder.
- `LOG_LEVEL`: optional. Defaults to `INFO`.

## Quick Start With Docker

This is the simplest and recommended way to run the full stack.

### 1. Create `.env`

```bash
cp .env.example .env
```

Then edit `.env` and provide at least:

- `TMDB_API_KEY`
- `TELEGRAM_BOT_TOKEN`

### 2. Start the stack

```bash
docker compose up --build
```

This starts:

- `postgres` on `localhost:5432`
- `api` on `http://localhost:8000`
- `bot` as a long-running Telegram polling process

### 3. Verify the API

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

### 4. Start using the bot

Open Telegram, message your bot, and send:

```text
/start
```

### Notes about Docker startup

- The API container runs Alembic migrations before starting Uvicorn.
- The bot container depends on both PostgreSQL and API.
- Both Dockerfiles install the package with development dependencies.

## Local Development Without Docker

If you want to run services directly on your machine:

### 1. Install dependencies

This repository is configured to work well with `uv`.

```bash
uv sync
```

If you prefer a traditional virtual environment, you can also install the package with:

```bash
pip install -e ".[dev]"
```

### 2. Prepare PostgreSQL

Create a PostgreSQL database and set `DATABASE_URL` accordingly.

Example local DSN:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/film_bot
```

### 3. Run migrations

```bash
uv run alembic upgrade head
```

### 4. Run the API

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir src
```

### 5. Run the bot

In a separate terminal:

```bash
uv run python -m bot.main
```

## How the Telegram Flow Works

The bot implements the following conversation flow:

### Onboarding

1. `/start`
2. Ask for country
3. Ask for owned streaming services
4. Ask for mood or genre text
5. Ask for one movie the user liked recently
6. Search TMDb and show up to 5 disambiguation options

### Interview

After the seed movie is selected:

- The bot builds an interview pool from TMDb Discover.
- Movies are shown one by one.
- The user votes with inline buttons:
  - `like`
  - `dislike`
  - `never_seen`

Important rules:

- Only `like` and `dislike` are informative votes.
- `never_seen` is neutral and does not count toward the minimum.
- Recommendations are generated only after at least 7 informative votes.
- The initial interview target is 10 movies.
- If the user still has fewer than 7 informative votes after those 10, the interview is extended in batches of 3.

### Regenerate

After recommendations are sent:

- The last recommendation includes a regenerate button.
- The user can also send `/more`.
- Existing votes and the stored taste profile are reused.
- Already suggested movies are excluded from later batches.

### Cancel

The `/cancel` command clears the current Telegram FSM state.

## Recommendation Pipeline

The backend recommendation pipeline is deterministic after the taste profile is built.

### Candidate generation

- Build one or more TMDb Discover parameter strategies from the taste profile.
- Fetch multiple pages from TMDb.
- Merge unique candidates.
- Try relaxed query strategies if the stricter ones do not produce enough results.

### Candidate filtering

The system removes:

- movies the user already voted on
- movies already suggested in previous batches

### Enrichment

Candidates are enriched with:

- genres
- keywords
- language
- release date
- vote average
- popularity
- poster
- overview

### Scoring

Candidates receive bonuses or penalties based on:

- matching preferred genres
- matching disliked genres
- matching preferred keywords
- matching disliked keywords
- original language match
- release period match
- vote average threshold
- simple mood-text match
- popularity bonus

### Final selection

- Candidates are sorted by score.
- The top 20 are considered.
- Final output picks 3 movies with a simple diversity rule that tries to avoid identical primary genres.

### Provider output

Provider data is fetched from TMDb `/movie/{id}/watch/providers`.

Rules:

- Providers are never guessed or hallucinated.
- If no provider data exists for the selected country, the message says availability is unknown.

## Taste Profile Generation

Taste profiles are built after the user reaches 7 informative votes.

### Metadata used

For voted movies, the system gathers:

- genres
- keywords
- release year
- runtime
- original language

### LLM path

If an LLM provider is configured, the project attempts to build the taste profile with the LLM first.

### Deterministic fallback

If LLM usage is disabled or unavailable, the project falls back to the deterministic builder in `src/app/taste/deterministic.py`.

### Stored format

The taste profile is saved on the user record as JSON and later reused for regenerate requests.

Typical fields include:

- preferred genre IDs
- disliked genre IDs
- preferred keyword IDs
- disliked keyword IDs
- release date lower bound
- vote average threshold
- original language
- discover sort order
- short explanation strings

## API Endpoints

The API currently exposes the following routes.

### `GET /health`

Basic health check.

Response:

```json
{"status":"ok"}
```

### `GET /tmdb/search?q=<query>`

Proxy helper for TMDb movie search.

### `GET /tmdb/movie/{movie_id}/providers?country=IT`

Returns provider data for a movie in a specific country.

### `POST /taste-profile/build`

Builds and stores a taste profile for a Telegram user.

Request body:

```json
{
  "telegram_user_id": 123456789
}
```

### `POST /recommendations/generate`

Generates the first recommendation batch for a Telegram user.

Request body:

```json
{
  "telegram_user_id": 123456789
}
```

### `POST /recommendations/regenerate`

Generates a new recommendation batch while excluding previous suggestions.

Request body:

```json
{
  "telegram_user_id": 123456789
}
```

### Important API behavior

- Recommendation and taste-profile endpoints return an error if the user has fewer than 7 informative votes.
- If a stored taste profile is missing, recommendation endpoints rebuild it automatically.

## Database Model

Main tables:

### `users`

- Telegram user ID as primary key
- country
- language
- owned services JSON
- mood text
- stored taste profile JSON
- created timestamp

### `votes`

- internal ID
- user ID
- TMDb movie ID
- vote enum: `like`, `dislike`, `never_seen`
- created timestamp

### `suggestions`

- internal ID
- user ID
- TMDb movie ID
- recommendation batch UUID
- created timestamp

### `cache`

- cache key
- cached JSON payload
- expiration timestamp

## Caching Rules

TMDb responses are cached in the database.

- Search results: 7 days
- Movie details: 7 days
- Keywords: 7 days
- Credits: 7 days
- Watch providers: 24 hours
- Discover results: 24 hours

Benefits:

- fewer external API calls
- faster repeated flows
- stable repeated recommendation runs within the cache window

## Running Tests and Checks

Run the test suite:

```bash
uv run pytest
```

Run linting:

```bash
uv run ruff check .
```

Current tests cover areas such as:

- informative vote counting
- deterministic taste profile generation
- recommendation filtering
- end-to-end recommendation pipeline behavior
- diversity selection
- poster URL handling

## Troubleshooting

### API does not start

Check:

- `.env` exists
- `TMDB_API_KEY` is valid
- `DATABASE_URL` points to a reachable PostgreSQL instance
- migrations have been applied

### Bot starts but does not respond in Telegram

Check:

- `TELEGRAM_BOT_TOKEN` is valid
- the bot is running without polling errors
- you started a chat with the bot in Telegram

### Recommendations never trigger

This usually means the user has not reached 7 informative votes yet.

Remember:

- `like` counts
- `dislike` counts
- `never_seen` does not count

### Provider list is empty

This is valid behavior.

The system only reports providers returned by TMDb for the selected country. If TMDb has no provider data, the output explicitly says availability is unknown.

### Regenerate returns few or no results

This can happen if:

- the discover query is too narrow
- many candidates have already been suggested
- TMDb does not have enough suitable results for the current taste profile

The code already tries relaxed discover strategies, but the project is still an MVP.

## Known Limitations

- The bot currently uses in-memory FSM storage, so in-progress conversation state is not persistent across bot restarts.
- The owned streaming services collected during onboarding are stored, but the current recommendation filtering does not strictly enforce them.
- The country defaults to `IT`, but users can choose another 2-letter code.
- The project is designed as an MVP, so some heuristics are intentionally simple.

## Acceptance Targets

The intended baseline behavior is:

- `docker compose up --build` starts the stack successfully
- `GET /health` returns `ok`
- the Telegram flow works end to end
- recommendations are blocked until at least 7 informative votes
- regenerate returns different recommendations without restarting onboarding
- provider information is never hallucinated
