# Git Commit Auto Message - MVP

A minimal CLI tool that reads a git diff (or a saved diff file) and asks Google Gemini to propose a commit message following the [Conventional Commits](https://www.conventionalcommits.org/) specification. Recent commit subjects are included in the prompt so the suggestion can match repository style.

## Requirements

- Python 3.10+
- Git available on your `PATH`
- A [Google Gemini API key](https://aistudio.google.com/)
- Run the tool from inside a git repository (unless you pass a diff file with `--file`)

## Setup

1. Create and activate a virtual environment (optional but recommended):

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:

   ```bash
   cp .env.example .env
   ```

   Edit `.env`:

   ```bash
   GEMINI_API_KEY=your_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```

## Environment variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `GEMINI_MODEL` | Gemini model name (default: `gemini-2.5-flash`) | No |

## Usage

From a git repository with local changes:

```bash
python3 script.py
```

Use only staged changes:

```bash
python3 script.py --staged
```

Generate a message from a saved diff file:

```bash
python3 script.py --file path/to/changes.diff
```

The tool prints a suggested commit message to the terminal. It does **not** create the commit for you—copy the message and run `git commit` yourself.

## How it works

1. Collect the diff (`git diff` / `git diff --staged`, or read `--file`)
2. Load recent commit subjects with `git log`
3. Fill `prompts/prompt_template.txt` with the diff and recent subjects
4. Call Gemini and print the suggested Conventional Commits message

## Project structure

```
├── script.py                 # Main CLI application
├── prompts/
│   └── prompt_template.txt   # AI prompt template
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Dependencies

- `python-dotenv` — load variables from `.env`
- `google-generativeai` — Gemini API client

## Notes

- Secrets stay in `.env` (gitignored); only `.env.example` is committed
- Customize message style by editing `prompts/prompt_template.txt`
- If there are no changes, the script exits with a short message asking you to stage files or pass `--file`
