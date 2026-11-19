# Apress Source Code

This repository accompanies [*Applied AI with LLMs: Create, Deploy, and Monetize Intelligent Applications*](https://link.springer.com/book/10.1007/979-8-8688-3305-2) by Furio Piccinini and Antonio Ceppellini (Apress, 2026).

![Cover image](https://media.springernature.com/w153/springer-static/cover/book/979-8-8688-3305-2.jpg)

Download the files as a zip using the green **Code** button, or clone the repository to your machine using Git:

```bash
git clone https://github.com/Apress/Applied-AI-with-LLMs.git
cd Applied-AI-with-LLMs
```

## About the book

This book is a hands-on guide to turning large language models into real, working software. With a modest amount of Python, you connect to major LLM APIs and build practical tools that solve real problems—from bots and chat interfaces to RAG search, refactoring helpers, and inbox automation.

Book page: [Springer Nature / Apress](https://link.springer.com/book/10.1007/979-8-8688-3305-2)  
DOI: [10.1007/979-8-8688-3305-2](https://doi.org/10.1007/979-8-8688-3305-2)  
Softcover ISBN: `979-8-8688-3304-5`  
eBook ISBN: `979-8-8688-3305-2`

## Repository structure

Each numbered folder matches a project chapter in the book. Open a folder, read its local `README.md` (when present), copy any `.env.example` to `.env`, install dependencies, and run the scripts described there.

| Folder | Project |
|--------|---------|
| `01-Telegram bot with Economic Calendar` | Telegram bot with economic calendar |
| `02-20Words` | 20Words — the news condenser |
| `03-Smart Chatbot` | Smart chatbot |
| `04-Route Planner` | Route planner (with an LLM twist) |
| `05-CineMatch` | CineMatch — movie recommendation bot |
| `06-Git Commit Automessage` | Git commit auto-message helper |
| `07-Semantic Search Engine with RAG` | Semantic search engine with RAG |
| `08-Code Refactoring Studio` | Code refactoring studio |
| `09-AI Inbox Triage` | AI inbox triage |

> Folder names may include spaces. Quote paths in the shell, for example:  
> `cd "03-Smart Chatbot"`

## Requirements

Most projects are Python-based and follow a similar setup pattern.

- **Python** 3.10+ recommended (3.9+ may work for some chapters; check each project’s notes)
- **pip** (or another Python package manager)
- An **API key** for the LLM provider(s) used in that chapter (for example OpenAI, Google, Anthropic—see the chapter and local `.env.example`)
- Additional third-party credentials where needed (Telegram bot token, email provider, etc.)

Typical per-project setup:

```bash
cd "01-Telegram bot with Economic Calendar"
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill in your secrets
python script.py                   # or the entry point named in that folder’s README
```

**Important:** never commit real API keys or tokens. Keep secrets in `.env` (gitignored) and ship only `.env.example` templates.

## Releases

Release **v1.0** corresponds to the code in the published book, without later corrections or updates.

## Corrections

For corrections to the content in the published book, see [`errata.md`](errata.md).

If you find an issue in the source code, please open a GitHub issue or submit a pull request—see [Contribution](Contribution.md).

## Contributions

See [`Contribution.md`](Contribution.md) for how you can contribute to this repository.

## License / copyright

Copyright for Apress source code belongs to the author(s). Readers are encouraged to use the code while following the book, and to contribute minor corrections under fair use as described in `Contribution.md`.
