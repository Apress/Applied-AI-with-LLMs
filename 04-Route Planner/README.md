# Route Planner - MVP

A minimal command-line tool that collects a list of addresses and uses Google Gemini to suggest an optimized travel order. The first address is always the starting point; you can optionally return there at the end.

## Requirements

- Python 3.10+
- A [Google Gemini API key](https://aistudio.google.com/)

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

   Edit `.env` and set your API key (and optionally the address limit):

   ```bash
   GEMINI_API_KEY=your_api_key_here
   MAX_ADDRESSES=20
   ```

## Environment variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `MAX_ADDRESSES` | Maximum number of addresses to accept | Yes |

## Usage

```bash
python3 script.py
```

The program will:

1. Ask you to enter addresses one by one (empty line to finish)
2. Ask whether to return to the starting point
3. Send the list to Gemini with the prompt in `prompts/prompt_template.txt`
4. Print an optimized route and a short explanation

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
- `google-genai` — Gemini API client

## Notes

- Secrets stay in `.env` (gitignored); only `.env.example` is committed
- Customize routing behavior by editing `prompts/prompt_template.txt`
- The model used in code is `gemini-2.5-flash`
