import json
from typing import Any

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

from src.utils.config import settings


SYSTEM_PROMPT = """
You are an Azure DevOps Work Item Assistant.

Turn even short user notes into a useful first-draft work item.

Return STRICT JSON with this exact shape:
{
  "title": "string",
  "description": "string (markdown)",
  "valueStatement": "string",
  "acceptanceCriteria": ["string"],
  "tasks": ["string"],
  "assumptions": ["string"],
  "dependencies": ["string"],
  "questions": ["string"],
  "confidence": 0.0
}

Rules:
- Title <= 120 characters
- Description should be structured and action-oriented
- Acceptance criteria must be testable
- Tasks must be actionable
- Make reasonable assumptions if details are missing
- confidence must be between 0 and 1
- Return JSON only
""".strip()


def _build_client() -> AzureOpenAI:
    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default",
    )

    return AzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        azure_ad_token_provider=token_provider,
    )


def _safe_parse_json(content: str) -> dict[str, Any]:
    content = content.strip()

    if content.startswith("```"):
        content = content.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM did not return valid JSON. Raw content: {content}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("LLM response JSON must be an object.")

    return parsed


def generate_work_item_content(notes: str, work_item_type: str) -> dict[str, Any]:
    client = _build_client()

    user_prompt = f"""
Work item type: {work_item_type}

User notes:
{notes}
""".strip()

    response = client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=1200,
    )

    content = response.choices[0].message.content or ""
    parsed = _safe_parse_json(content)

    parsed.setdefault("title", "")
    parsed.setdefault("description", "")
    parsed.setdefault("valueStatement", "")
    parsed.setdefault("acceptanceCriteria", [])
    parsed.setdefault("tasks", [])
    parsed.setdefault("assumptions", [])
    parsed.setdefault("dependencies", [])
    parsed.setdefault("questions", [])
    parsed.setdefault("confidence", 0.0)

    if not isinstance(parsed["acceptanceCriteria"], list):
        parsed["acceptanceCriteria"] = []
    if not isinstance(parsed["tasks"], list):
        parsed["tasks"] = []
    if not isinstance(parsed["assumptions"], list):
        parsed["assumptions"] = []
    if not isinstance(parsed["dependencies"], list):
        parsed["dependencies"] = []
    if not isinstance(parsed["questions"], list):
        parsed["questions"] = []

    try:
        parsed["confidence"] = float(parsed["confidence"])
    except (TypeError, ValueError):
        parsed["confidence"] = 0.0

    parsed["confidence"] = max(0.0, min(1.0, parsed["confidence"]))

    return parsed
