import json
import re
from typing import Any, Dict, Optional

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
- Do not return markdown fences.
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
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )


def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _fallback_response(notes: str, title_hint: Optional[str] = None) -> Dict[str, Any]:
    return {
        "title": title_hint or "Generated Work Item",
        "description": f"## Summary\n\n{notes}",
        "acceptanceCriteria": ["Review and confirm the generated work item."],
        "tasks": [
            "Review generated title",
            "Review generated description",
            "Confirm acceptance criteria",
        ],
        "assumptions": ["Model returned non-JSON; fallback response used."],
        "confidence": 0.4,
        "extraFields": {},
    }


def generate_work_item_content(
    notes: str,
    work_item_type: str,
    title_hint: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        client = _get_client()

        user_prompt = f"""
Work item type: {work_item_type}

Title hint: {title_hint or "None"}

Notes:
{notes}
""".strip()

        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content or "{}"
        cleaned = _strip_code_fences(content)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    parsed = json.loads(cleaned[start:end + 1])
                except json.JSONDecodeError:
                    parsed = _fallback_response(notes, title_hint)
            else:
                parsed = _fallback_response(notes, title_hint)

        parsed.setdefault("title", title_hint or "Generated Work Item")
        parsed.setdefault("description", f"## Summary\n\n{notes}")
        parsed.setdefault("acceptanceCriteria", [])
        parsed.setdefault("tasks", [])
        parsed.setdefault("assumptions", [])
        parsed.setdefault("confidence", 0.0)
        parsed.setdefault("extraFields", {})

        if not isinstance(parsed["acceptanceCriteria"], list):
            parsed["acceptanceCriteria"] = []
        if not isinstance(parsed["tasks"], list):
            parsed["tasks"] = []
        if not isinstance(parsed["assumptions"], list):
            parsed["assumptions"] = []
        if not isinstance(parsed["extraFields"], dict):
            parsed["extraFields"] = {}

        try:
            parsed["confidence"] = float(parsed["confidence"])
        except Exception:
            parsed["confidence"] = 0.0

        parsed["confidence"] = max(0.0, min(1.0, parsed["confidence"]))
        return parsed

    except Exception as exc:
        raise RuntimeError(f"LLM generation failed: {str(exc)}") from exc
