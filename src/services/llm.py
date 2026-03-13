import json
from typing import Any, Dict

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

from src.utils.config import settings


SYSTEM_PROMPT = """
You are an Azure DevOps Work Item Assistant.
Generate a clean work item draft from the user's notes.

Return STRICT JSON with this exact shape:
{
  "title": "string",
  "description": "string",
  "acceptanceCriteria": ["string"],
  "tasks": ["string"],
  "assumptions": ["string"],
  "confidence": 0.0,
  "extraFields": {}
}

Rules:
- Title must be concise and useful.
- Description must be structured markdown.
- Acceptance criteria must be testable.
- Tasks must be actionable.
- If details are missing, add them to assumptions.
- confidence must be between 0 and 1.
- extraFields should usually be {} unless clearly needed.
"""


def _get_client() -> AzureOpenAI:
    if not settings.AZURE_OPENAI_ENDPOINT:
        raise ValueError("AZURE_OPENAI_ENDPOINT is missing.")

    if not settings.AZURE_OPENAI_DEPLOYMENT:
        raise ValueError("AZURE_OPENAI_DEPLOYMENT is missing.")

    credential = (
        DefaultAzureCredential(managed_identity_client_id=settings.AZURE_CLIENT_ID)
        if settings.AZURE_CLIENT_ID
        else DefaultAzureCredential()
    )

    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default",
    )

    return AzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version="2024-02-01",
    )


def generate_work_item_content(notes: str, work_item_type: str) -> Dict[str, Any]:
    try:
        client = _get_client()

        user_prompt = f"""
Work item type: {work_item_type}

Notes:
{notes}
"""

        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content or "{}"

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {
                "title": "Generated Work Item",
                "description": f"## Summary\n\n{notes}",
                "acceptanceCriteria": ["Review and refine generated output."],
                "tasks": [
                    "Validate notes",
                    "Refine title",
                    "Confirm acceptance criteria",
                ],
                "assumptions": ["Model returned non-JSON; fallback response used."],
                "confidence": 0.4,
                "extraFields": {},
            }

        parsed.setdefault("extraFields", {})
        return parsed

    except Exception as exc:
        raise RuntimeError(f"LLM generation failed: {str(exc)}") from exc
