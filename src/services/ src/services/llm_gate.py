import json
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
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(managed_identity_client_id=settings.AZURE_CLIENT_ID),
        "https://cognitiveservices.azure.com/.default",
    )

    return AzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version="2024-02-01",
    )


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

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "action": "create_draft",
            "messageToUser": "Proceeding with draft generation.",
            "questions": [],
            "assumptions": ["Model returned non-JSON; defaulted to create_draft."],
            "confidence": 0.5,
        }
