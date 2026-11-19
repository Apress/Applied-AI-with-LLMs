import os
import json
import requests
from dotenv import load_dotenv
from accounting_tools import TOOL_FUNCTIONS

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

SYSTEM_PROMPT = """You are a careful AI assistant.
- If the question requires structured data, use one of the allowed tools.
- Never attempt to write SQL directly.
- For qualitative questions, respond in natural language.
- Ask for confirmation before actions that modify data.
"""

# REAL Gemini tool schema: tools -> functionDeclarations -> parameters (JSON Schema)
TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": "get_invoices",
                "description": "Returns a client's invoices for a given period.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client": {"type": "string"},
                        "period": {"type": "string", "description": "Year-month in the form YYYY-MM"},
                    },
                    "required": ["client", "period"],
                },
            },
            {
                "name": "add_invoice",
                "description": "Adds an invoice for a client.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client": {"type": "string"},
                        "date": {"type": "string", "description": "ISO date, e.g. 2024-04-10"},
                        "service": {"type": "string"},
                        "amount": {"type": "number"},
                    },
                    "required": ["client", "date", "service", "amount"],
                },
            },
            {
                "name": "get_client_stats",
                "description": "Returns aggregated stats for a client in a given period.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client": {"type": "string"},
                        "period": {"type": "string", "description": "Year-month in the form YYYY-MM"},
                    },
                    "required": ["client", "period"],
                },
            },
            {
                "name": "get_top_services",
                "description": "Returns the most requested services for a given period.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "period": {"type": "string", "description": "Year-month in the form YYYY-MM"},
                    },
                    "required": ["period"],
                },
            },
            {
                "name": "get_total_revenue",
                "description": "Returns total revenue for a given YYYY-MM period.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "period": {"type": "string", "description": "Year-month in the form YYYY-MM"},
                    },
                    "required": ["period"],
                },
            },
        ]
    }
]


def _extract_text(candidate: dict) -> str:
    content = candidate.get("content", {})
    parts = content.get("parts", [])
    for part in parts:
        if "text" in part:
            return part["text"]
    return ""


def gemini_generate(body: dict) -> dict:
    headers = {"Content-Type": "application/json", "x-goog-api-key": API_KEY}
    resp = requests.post(URL, json=body, headers=headers)
    resp.raise_for_status()
    return resp.json()


def explain_tool_result(user_question: str, tool_name: str, tool_result) -> str:
    """Ask the model to explain a tool result in plain language."""
    final_body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            f"User question: {user_question}\n"
                            f"Tool used: {tool_name}\n"
                            f"Tool result: {tool_result}\n"
                            "Explain the result clearly to the user."
                        )
                    }
                ],
            }
        ],
    }

    final_data = gemini_generate(final_body)
    return _extract_text(final_data["candidates"][0])


def gemini_chat(user_input: str) -> dict:
    """
    Chat with Gemini + function calling.

    Always returns a dict with this shape:
        {"text": str, "action": Optional[{"name": str, "args": dict}]}
    """
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user_input}]}],
        "tools": TOOLS,
    }

    data = gemini_generate(body)
    candidate_content = data["candidates"][0]["content"]
    parts = candidate_content.get("parts", [])

    # Default response: plain text, no action
    response = {"text": "", "action": None}

    # If the model proposed a tool call, execute it via the router (or request confirmation)
    for part in parts:
        function_call = part.get("functionCall")
        if not function_call:
            continue

        name = function_call["name"]
        args = function_call.get("args", {})

        if name not in TOOL_FUNCTIONS:
            return {"text": f"Tool '{name}' is not allowed.", "action": None}

        # Optional: enforce confirmation for write tools
        if name in {"add_invoice"}:
            return {
                "text": (
                    "I can add the invoice, but I need confirmation first.\n"
                    f"Proposed action: {name}({json.dumps(args, ensure_ascii=False)})\n"
                    "Reply with: CONFIRM"
                ),
                "action": {"name": name, "args": args},
            }

        result = TOOL_FUNCTIONS[name](**args)
        explanation = explain_tool_result(user_input, name, result)
        return {"text": explanation, "action": None}

    # No tool call: return plain text answer
    response["text"] = _extract_text(data["candidates"][0])
    return response


def run_cli_chat() -> None:
    print("Type 'exit' to quit the chat.")
    pending_action = None  # {"name": "...", "args": {...}, "user_input": "..."}

    while True:
        user_text = input("You: ").strip()
        if user_text.lower() == "exit":
            break

        # 1) confirm/cancel handled locally (NO LLM)
        if pending_action and user_text.upper() == "CONFIRM":
            name = pending_action["name"]
            args = pending_action["args"]
            original_user_input = pending_action["user_input"]

            fn = TOOL_FUNCTIONS[name]
            result = fn(**args)
            pending_action = None

            # Optional: ask LLM to explain the write result too
            explanation = explain_tool_result(original_user_input, name, result)
            print("Assistant:", explanation)
            continue

        if pending_action and user_text.upper() == "CANCEL":
            pending_action = None
            print("Operation cancelled.")
            continue

        # 2) normal flow -> call LLM
        llm_response = gemini_chat(user_text)

        # 3) if LLM proposed an action, store it and ask for confirmation
        if llm_response.get("action"):
            pending_action = {
                "name": llm_response["action"]["name"],
                "args": llm_response["action"]["args"],
                "user_input": user_text,
            }
            print("Assistant:", llm_response["text"])
            continue

        print("Assistant:", llm_response["text"])


if __name__ == "__main__":
    run_cli_chat()
