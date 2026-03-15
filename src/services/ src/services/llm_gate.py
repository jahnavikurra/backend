import json
import re
from typing import Any, Dict

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

from src.utils.config import settings


SOFT_GATE_PROMPT = """
You are an Azure DevOps work item assistant.

Return ONLY valid JSON with this schema:
{
  "action": "create_draft" | "ask_questions_only",
  "messageToUser": "string",
  "questions": ["string"],
  "assumptions": ["string"],
  "confidence": 0.0
}

Rules:
- Use action="create_draft" for almost all normal inputs.
- Use action="ask_questions_only" only if the notes are too vague, meaningless, random, or unusable.
- Be practical and lenient.
- confidence must be between 0 and 1.
"""


def _get_client() -> AzureOpenAI:
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


def gate_notes(notes: str) -> Dict[str, Any]:
    client = _get_client()

    response = client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        temperature=0,
        messages=[
            {"role": "system", "content": SOFT_GATE_PROMPT},
            {"role": "user", "content": notes},
        ],
    )

    content = response.choices[0].message.content or "{}"
    cleaned = _strip_code_fences(content)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = {
            "action": "create_draft",
            "messageToUser": "Proceeding with draft generation.",
            "questions": [],
            "assumptions": ["Model returned non-JSON; defaulted to create_draft."],
            "confidence": 0.5,
        }

    parsed.setdefault("action", "create_draft")
    parsed.setdefault("messageToUser", "Proceeding with draft generation.")
    parsed.setdefault("questions", [])
    parsed.setdefault("assumptions", [])
    parsed.setdefault("confidence", 0.5)

    if not isinstance(parsed["questions"], list):
        parsed["questions"] = []
    if not isinstance(parsed["assumptions"], list):
        parsed["assumptions"] = []

    try:
        parsed["confidence"] = float(parsed["confidence"])
    except Exception:
        parsed["confidence"] = 0.5

    parsed["confidence"] = max(0.0, min(1.0, parsed["confidence"]))
    return parsed
