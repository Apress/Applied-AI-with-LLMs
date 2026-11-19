# AI Tool-Driven Accounting Demo

This repository contains a minimal command-line chatbot that demonstrates how a language model can select and use explicitly authorized Python tools.

The chatbot uses the Gemini API to interpret natural-language requests, SQLite for local persistence, and a small registry of accounting functions. Read-only operations are executed after the proposed tool has been checked against the registry, while operations that modify data require explicit user confirmation.

This is an educational MVP, not a production accounting system.

## What the Project Demonstrates

- Declaring Python functions as tools available to a language model.
- Letting the model propose a structured function call.
- Restricting execution to an explicit tool registry.
- Executing read-only tools against a local SQLite database.
- Requiring `CONFIRM` before a write operation is performed.
- Passing tool results back to the model to produce a readable answer.

## Project Structure

```text
.
├── app/
│   ├── accounting_tools.py  # SQLite queries and callable accounting tools
│   ├── create_db.py         # Database schema and sample-data initialization
│   └── main.py              # Gemini integration and interactive CLI loop
├── pyproject.toml           # Project metadata and runtime dependencies
└── README.md
```

### `app/accounting_tools.py`

Defines the functions that can be called by the chatbot:

- `get_invoices`
- `add_invoice`
- `get_client_stats`
- `get_top_services`
- `get_total_revenue`

The `TOOL_FUNCTIONS` dictionary acts as an explicit execution registry. A function name proposed by the model is executed only when it is present in this dictionary.

### `app/create_db.py`

Creates the local `accounting.db` SQLite database, defines the `invoices` table, and inserts a small sample dataset.

At present, running this script more than once inserts the sample records again. Delete `accounting.db` before recreating the demo database from scratch.

### `app/main.py`

Contains:

- the Gemini API configuration;
- the system prompt;
- the Gemini function declarations;
- the tool-selection flow;
- the `CONFIRM`/`CANCEL` handling for write operations;
- the command-line chat loop.

The current implementation is stateless: each normal user request is sent to the model independently and previous conversational turns are not retained.

## Requirements

- Python 3.11 or later
- `uv`
- A Gemini API key

## Setup

Clone the repository and enter its directory:

```bash
git clone <repository-url>
cd chatbot
```

Install the dependencies declared in `pyproject.toml`:

```bash
uv sync
```

Create a `.env` file in the project root with the following content:

```env
GEMINI_API_KEY=replace_with_your_api_key
```

Replace `replace_with_your_api_key` with a valid Gemini API key. Do not commit the `.env` file to version control.

Initialize the SQLite database:

```bash
uv run python app/create_db.py
```

The command creates `accounting.db` in the repository root and inserts the sample invoices used by the demo.

## Running the Chatbot

Start the interactive CLI from the project root:

```bash
uv run python app/main.py
```

The terminal displays:

```text
Type 'exit' to quit the chat.
You:
```

Enter `exit` to close the application.

## Example Requests

The sample database currently contains records for `Mario Rossi`, `Luca Bianchi`, and `Maria Verdi`.

Read-only examples:

```text
Show me Mario Rossi's invoices for 2024-03.
```

```text
What was the total revenue for 2024-07?
```

```text
Which services were requested most often in 2024-07?
```

Write example:

```text
Add an invoice for Mario Rossi dated 2024-08-10 for a consulting service costing 650 euros.
```

For `add_invoice`, the chatbot proposes the tool call but does not immediately modify the database. It stores the proposed action and asks for one of these commands:

```text
CONFIRM
```

```text
CANCEL
```

`CONFIRM` executes the stored operation. `CANCEL` discards it.

## Execution Flow

For each normal user request, the application performs the following steps:

1. Sends the request and the allowed function declarations to Gemini.
2. Reads either a natural-language response or a proposed `functionCall`.
3. Checks that the proposed function exists in `TOOL_FUNCTIONS`.
4. Executes read-only tools immediately.
5. Stores write operations as pending actions until the user enters `CONFIRM`.
6. Sends the raw tool result back to Gemini to obtain a user-facing explanation.

The model proposes an action; the Python application remains responsible for deciding whether and when that action is executed.

## Current Limitations

This repository intentionally avoids production-level complexity. In particular, it currently has:

- no authentication or user isolation;
- no role-based tool permissions;
- no persistent conversation history;
- limited argument validation;
- no request timeout or retry policy;
- no structured logging or audit trail;
- no database migrations;
- no protection against repeated database initialization;
- SQLite `REAL` values for monetary amounts;
- no automated test suite.

These limitations are acceptable for demonstrating tool calling, but they must be addressed before using the design with real financial data or exposing it as a service.

## Suggested Next Steps

A practical next iteration would add:

- validation for dates, periods, strings, and monetary amounts;
- idempotency protection for write operations;
- network timeouts and clearer API error handling;
- automated tests with a temporary SQLite database;
- structured logging for proposed and executed tool calls;
- conversation or session management;
- a FastAPI interface and authenticated users;
- PostgreSQL and migrations for a multi-user deployment.
