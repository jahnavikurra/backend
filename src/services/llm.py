# src/services/llm.py

import json
from typing import Any, Dict, Optional

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from src.utils.config import settings


SYSTEM_PROMPT = """
You are an Azure DevOps Work Item Assistant.
Generate Scrum work items from notes.

Return STRICT JSON with this exact shape:
{
  "title": "string",
  "description": "string (markdown)",
  "acceptanceCriteria": ["string", "..."],
  "tasks": ["string", "..."],
  "assumptions": ["string", "..."],
  "confidence": 0.0
}

Rules:
- Title <= 120 characters
- Description must be structured and based only on the notes/context provided
- Acceptance criteria must be testable (Given/When/Then or checklist style)
- Tasks must be actionable, small steps
- Put missing info into assumptions
- confidence between 0.0 and 1.0
""".strip()


def _client() -> AzureOpenAI:
    """
    Creates an AzureOpenAI client authenticated via Microsoft Entra ID
    (no API key). Works locally (az login) and in Azure (Managed Identity).
    """
    if not settings.AZURE_OPENAI_ENDPOINT:
        raise RuntimeError("Missing AZURE_OPENAI_ENDPOINT")
    if not settings.AZURE_OPENAI_DEPLOYMENT:
        raise RuntimeError("Missing AZURE_OPENAI_DEPLOYMENT")

    credential = DefaultAzureCredential()

    # Correct scope for Azure OpenAI / Cognitive Services
    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default",
    )

    # Use /openai/v1/ for the latest SDK pattern
    return AzureOpenAI(
        base_url=f"{settings.AZURE_OPENAI_ENDPOINT.rstrip('/')}/openai/v1/",
        api_key=token_provider,  # token provider (NOT an API key)
    )


def generate_work_item_draft(
    notes_text: str,
    work_item_type: str = "PBI",
    process: str = "Scrum",
    extra_context: Optional[str] = None,
) -> Dict[str, Any]:
    client = _client()

    user_prompt = f"""
Process: {process}
WorkItemType: {work_item_type}

Notes:
{notes_text}
""".strip()

    if extra_context:
        user_prompt += f"\n\nAdditional context (use only if relevant):\n{extra_context}"

    resp = client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    raw = (resp.choices[0].message.content or "").strip()
    if not raw:
        raise RuntimeError("Model returned empty response")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Model returned invalid JSON: {e}. Raw: {raw}")

    # Normalize / defaults
    data.setdefault("acceptanceCriteria", [])
    data.setdefault("tasks", [])
    data.setdefault("assumptions", [])
    data.setdefault("confidence", None)

    # Basic validation
    if not data.get("title"):
        raise RuntimeError(f"Model JSON missing 'title'. Raw: {raw}")
    if "description" not in data or data["description"] is None:
        data["description"] = ""

    # Ensure lists are lists
    if not isinstance(data["acceptanceCriteria"], list):
        data["acceptanceCriteria"] = [str(data["acceptanceCriteria"])]
    if not isinstance(data["tasks"], list):
        data["tasks"] = [str(data["tasks"])]
    if not isinstance(data["assumptions"], list):
        data["assumptions"] = [str(data["assumptions"])]

    # Clamp confidence if present
    conf = data.get("confidence")
    if isinstance(conf, (int, float)):
        if conf < 0.0:
            data["confidence"] = 0.0
        elif conf > 1.0:
            data["confidence"] = 1.0

    return data
