# AI Code Refactoring Studio - MVP

A minimal CLI tool that reads a Python file via MCP, analyzes it with AST, and asks Google Gemini for refactoring suggestions.

## Requirements

- Python 3.10+
- Node.js (for the MCP filesystem server via `npx`)
- Google Gemini API key

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your GEMINI_API_KEY to .env
```

## Usage

```bash
python script.py examples/bad_code.py
python script.py examples/good_code.py
```

## How it works

1. Read the target file through the MCP filesystem server (`read_text_file`; `read_file` is the legacy name)
2. Parse the code with Python's `ast` module and detect code smells
3. Send the code and detected issues to Gemini
4. Print refactoring suggestions to the terminal

## AST checks

- Cyclomatic complexity above 10
- Functions longer than 50 lines
- More than 5 parameters
- Nesting depth above 4
