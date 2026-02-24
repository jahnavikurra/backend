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


# Cache the client so we don't rebuild token provider every request
_client_cache: Optional[AzureOpenAI] = None


def _get_client() -> AzureOpenAI:
    """
    Creates an AzureOpenAI client authenticated via Microsoft Entra ID (no API key).
    Works locally (az login) and in Azure (Managed Identity).
    """
    global _client_cache
    if _client_cache is not None:
        return _client_cache

    endpoint = (settings.AZURE_OPENAI_ENDPOINT or "").strip()
    deployment = (settings.AZURE_OPENAI_DEPLOYMENT_NAME or settings.AZURE_OPENAI_DEPLOYMENT or "").strip()
    api_version = (settings.AZURE_OPENAI_API_VERSION or "").strip()

    if not endpoint:
        raise RuntimeError("Missing AZURE_OPENAI_ENDPOINT")
    if not deployment:
        raise RuntimeError("Missing AZURE_OPENAI_DEPLOYMENT_NAME (or AZURE_OPENAI_DEPLOYMENT)")
    if not api_version:
        # Use a safe default if you didn't set it (you can override in env)
        api_version = "2024-02-15-preview"

    credential = DefaultAzureCredential()

    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default",
    )

    _client_cache = AzureOpenAI(
        azure_endpoint=endpoint.rstrip("/"),
        api_version=api_version,
        azure_ad_token_provider=token_provider,
    )
    return _client_cache


def generate_work_item_draft(
    notes_text: str,
    work_item_type: str = "Product Backlog Item",
    process: str = "Scrum",
    extra_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calls Azure OpenAI and returns a validated dict containing:
    title, description, acceptanceCriteria, tasks, assumptions, confidence
    """
    if not notes_text or not notes_text.strip():
        raise ValueError("notes_text is empty")

    client = _get_client()

    deployment = (settings.AZURE_OPENAI_DEPLOYMENT_NAME or settings.AZURE_OPENAI_DEPLOYMENT or "").strip()

    user_prompt = f"""
Process: {process}
WorkItemType: {work_item_type}

Notes:
{notes_text}
""".strip()

    if extra_context:
        user_prompt += f"\n\nAdditional context (use only if relevant):\n{extra_context.strip()}"

    resp = client.chat.completions.create(
        model=deployment,  # MUST be your deployment name
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

    # Ensure required keys exist
    data.setdefault("title", "")
    data.setdefault("description", "")
    data.setdefault("acceptanceCriteria", [])
    data.setdefault("tasks", [])
    data.setdefault("assumptions", [])
    data.setdefault("confidence", 0.0)

    # Validate types / coerce
    if not isinstance(data["title"], str):
        data["title"] = str(data["title"])
    if not isinstance(data["description"], str):
        data["description"] = str(data["description"])

    if not isinstance(data["acceptanceCriteria"], list):
        data["acceptanceCriteria"] = [str(data["acceptanceCriteria"])]
    if not isinstance(data["tasks"], list):
        data["tasks"] = [str(data["tasks"])]
    if not isinstance(data["assumptions"], list):
        data["assumptions"] = [str(data["assumptions"])]

    # Final required check
    if not data["title"].strip():
        raise RuntimeError(f"Model JSON missing non-empty 'title'. Raw: {raw}")

    # Clamp confidence
    conf = data.get("confidence")
    if isinstance(conf, (int, float)):
        if conf < 0.0:
            data["confidence"] = 0.0
        elif conf > 1.0:
            data["confidence"] = 1.0
        else:
            data["confidence"] = float(conf)
    else:
        data["confidence"] = 0.0

    return data
