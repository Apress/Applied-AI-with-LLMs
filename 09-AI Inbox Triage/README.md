# ai-inbox-triage

`ai-inbox-triage` is a minimal command-line AI assistant that reads recent unread Gmail messages, classifies them with an LLM, and prints a clean terminal dashboard.

This project is designed for a chapter in **Applied AI with LLMs**. It demonstrates a practical LLM workflow without a web app, database, background worker, or production framework: fetch data, normalize it, prompt a model, validate structured output, and present useful results.

## What it does

- Connects to Gmail with Google OAuth.
- Uses Gmail read-only access only.
- Fetches messages with a Gmail search query.
- Defaults to unread messages from the last 7 days.
- Sends only sender, subject, date, and Gmail snippet to the LLM by default.
- Optionally includes the plain text body with `--include-body`.
- Supports Gemini by default and Ollama for local inference.
- Prints a Rich terminal dashboard sorted by urgency.

It never sends, deletes, archives, marks as read, labels, drafts, or replies to email.

## Project structure

```text
mail-triager/
├── ai_inbox_triage.py
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
└── README.md
```

After setup, these local untracked files may exist:

```text
.env
credentials.json
token.json
```

## Setup

Install `uv` if it is not already available:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install project dependencies:

```bash
cd mail-triager
uv sync
```

Copy the example environment file:

```bash
cp .env.example .env
```

## Google OAuth credentials

1. Open Google Cloud Console.
2. Create or select a project.
3. Enable the Gmail API.
4. Configure the OAuth consent screen.
5. Create OAuth credentials for a Desktop app.
6. Download the JSON file.
7. Rename it to `credentials.json`.
8. Place `credentials.json` in this project directory.

The app requests only this Gmail scope:

```text
https://www.googleapis.com/auth/gmail.readonly
```

On the first run, a browser window opens for Google OAuth. The resulting local token is saved as `token.json`.

## Run with Gemini

Add your Gemini API key to `.env`:

```bash
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Run:

```bash
uv run python ai_inbox_triage.py
```

Or choose a Gemini model:

```bash
uv run python ai_inbox_triage.py --provider gemini --model gemini-2.5-flash
```

## Run with Ollama

Install Ollama, then start the local server:

```bash
ollama serve
```

Pull a model:

```bash
ollama pull llama3.1:8b
```

Run:

```bash
uv run python ai_inbox_triage.py --provider ollama --model llama3.1:8b
```

Ollama keeps inference local, but classification quality depends on the local model you choose.

## CLI examples

```bash
uv run python ai_inbox_triage.py
uv run python ai_inbox_triage.py --limit 20
uv run python ai_inbox_triage.py --query "is:unread newer_than:3d" --limit 20
uv run python ai_inbox_triage.py --provider gemini --model gemini-2.5-flash
uv run python ai_inbox_triage.py --provider ollama --model llama3.1:8b
uv run python ai_inbox_triage.py --include-body
uv run python ai_inbox_triage.py --json
uv run python ai_inbox_triage.py --verbose
```

## Privacy notes

Emails may contain sensitive personal, business, financial, or security information.

By default, this script sends sender, subject, date, and Gmail snippet to the selected LLM provider. If you pass `--include-body`, it may also send plain text email body content when available.

Gemini is cloud-based, so selected email text is sent to Google's Gemini API. Review your provider's data handling terms before using cloud inference on real email. Ollama runs locally, but output quality depends on the local model you choose.

The app uses Gmail read-only scope and does not modify your mailbox.

OAuth files and local secrets are ignored by Git:

- `.env`
- `credentials.json`
- `token.json`

## Troubleshooting

### `uv: command not found`

Install `uv`, then restart your shell if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then run:

```bash
uv sync
```

### `credentials.json` missing

Download OAuth client credentials from Google Cloud Console, rename the file to `credentials.json`, and place it in this project directory.

### `GEMINI_API_KEY` missing

Add your Gemini API key to `.env`:

```bash
GEMINI_API_KEY=your_api_key_here
```

Then run the app again:

```bash
uv run python ai_inbox_triage.py
```

### OAuth app not verified or access blocked

For a personal learning project, add your Google account as a test user on the OAuth consent screen in Google Cloud Console. Make sure the Gmail API is enabled and the OAuth client type is Desktop app.

### Gmail returns no emails

The default query is:

```text
is:unread newer_than:7d
```

Try a broader query:

```bash
uv run python ai_inbox_triage.py --query "newer_than:30d" --limit 20
```

### Ollama is not reachable

Start Ollama and pull the model:

```bash
ollama serve
ollama pull llama3.1:8b
```

Then run:

```bash
uv run python ai_inbox_triage.py --provider ollama --model llama3.1:8b
```

### Model returns invalid JSON

The app retries once with a stricter JSON-only prompt. If it still fails, that email is shown as `unknown` with a manual review action. Try a stronger model or reduce the number of emails while debugging:

```bash
uv run python ai_inbox_triage.py --limit 3 --verbose
```

### `token.json` problems after changing OAuth scopes

Delete the old token and run the app again to repeat OAuth:

```bash
rm token.json
uv run python ai_inbox_triage.py
```

## Limitations

- This is an educational MVP, not a production email client.
- It reads Gmail only.
- It does not modify email state.
- It does not understand full thread history unless the relevant text is present in the fetched message.
- It may misclassify ambiguous emails.
- Local Ollama models may return weaker structured JSON than cloud models.

## Possible extensions

- Apply Gmail labels.
- Generate Gmail drafts.
- Create a daily digest.
- Add a web dashboard.
- Run on a schedule.
- Use RAG over previous replies.
- Support Outlook.
