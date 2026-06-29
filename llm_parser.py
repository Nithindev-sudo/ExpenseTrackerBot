import json
import os
from pathlib import Path

try:
    from groq import Groq
except ImportError:  # pragma: no cover - depends on environment
    Groq = None

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

client = None


def init_llm(api_key: str | None = None):
    global client
    if api_key is None:
        api_key = os.getenv("GROQ_API_KEY")
    if not api_key or Groq is None:
        client = None
        return False
    client = Groq(api_key=api_key)
    return True


def _clean_llm_response(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```") and raw.endswith("```"):
        raw = raw.strip("`\n ")

    first = raw.find("{")
    last = raw.rfind("}")
    if first != -1 and last != -1 and last > first:
        raw = raw[first:last + 1]

    return raw.strip()


def _build_extract_prompt(message: str) -> str:
    return f"""
You are an expense tracking assistant.

Extract expense details from the user message.

Return ONLY valid JSON with exactly these keys:
- item_name
- amount
- category
- type

Do not include any explanation, markdown, code fences, or extra text.
Do not return arrays, comments, or any wrapper object.
If you cannot produce valid JSON, return no text.

Fields:

item_name:
The purchased item/service

amount:
Numeric amount only

category:
Choose one:
- Food
- Travel
- Shopping
- Health
- Fitness
- Bills
- Entertainment
- Groceries
- Education
- Other

type:
Always use "expense" for expense entries.

User message:

{message}

Example output:

{{
  "item_name": "Muscle Blaze Performance Whey",
  "amount": 2500,
  "category": "Health",
  "type": "expense"
}}
"""


def _build_validation_prompt(previous_response: str, message: str) -> str:
    return f"""
The previous response was not valid JSON:

{previous_response}

Please return ONLY valid JSON with exactly these keys:
- item_name
- amount
- category
- type

Fix the response above if possible, but do not add any explanation, markdown, code fences, or extra text.

User message:

{message}
"""


def _call_llm(prompt: str):
    return client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
            "role": "system",
            "content": "You extract structured expense data."
            },
            {
            "role": "user",
            "content": prompt
            }
        ],
        temperature=0
    )


def _parse_llm_output(raw: str):
    cleaned = _clean_llm_response(raw)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM returned invalid JSON") from exc

    if not isinstance(parsed, dict):
        raise ValueError("LLM did not return an object")

    required = {"item_name", "amount", "category", "type"}
    missing = required.difference(parsed)
    if missing:
        raise ValueError(f"LLM response missing fields: {sorted(missing)}")

    return parsed


def extract_expense(message):
    global client
    if client is None and not init_llm():
        raise RuntimeError("LLM client is not available")

    first_prompt = _build_extract_prompt(message)
    response = _call_llm(first_prompt)
    raw = response.choices[0].message.content

    try:
        return _parse_llm_output(raw)
    except ValueError:
        validation_prompt = _build_validation_prompt(raw, message)
        response = _call_llm(validation_prompt)
        raw = response.choices[0].message.content
        return _parse_llm_output(raw)
