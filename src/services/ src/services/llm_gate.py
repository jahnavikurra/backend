# src/services/llm_gate.py

import json
from typing import Any, Dict, List

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from src.utils.config import settings


GATE_SYSTEM_PROMPT = """
You are a strict requirements validator for Azure DevOps work items.

Return STRICT JSON only with this shape:
{
  "valid": true/false,
  "reason": "short explanation",
  "requiredQuestions": ["question1", "question2", "..."],
  "confidence": 0.0
}

Rules:
- valid=true ONLY if the text clearly describes a feature/bug/task with an understandable goal.
- If text is random, meaningless, too vague, or not actionable -> valid=false.
- requiredQuestions should ask what is missing (e.g., goal, expected behaviour, user, scope).
- confidence between 0.0 and 1.0
""".strip()


def _client() -> AzureOpenAI:
    if not settings.AZURE_OPENAI_ENDPOINT:
        raise RuntimeError("Missing AZURE_OPENAI_ENDPOINT")
    if not settings.AZURE_OPENAI_DEPLOYMENT:
        raise RuntimeError("Missing AZURE_OPENAI_DEPLOYMENT")

    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default",
    )

    # Using /openai/v1/ pattern (same as llm.py)
    return AzureOpenAI(
        base_url=f"{settings.AZURE_OPENAI_ENDPOINT.rstrip('/')}/openai/v1/",
        api_key=token_provider,  # Entra token provider (NOT an API key)
    )


def validate_notes(notes_text: str) -> Dict[str, Any]:
    """
    Returns:
      {
        "valid": bool,
        "reason": str,
        "requiredQuestions": List[str],
        "confidence": float
      }
    """
    client = _client()

    resp = client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": GATE_SYSTEM_PROMPT},
            {"role": "user", "content": notes_text.strip()},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )

    raw = (resp.choices[0].message.content or "").strip()
    if not raw:
        raise RuntimeError("Model returned empty response")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Model returned invalid JSON: {e}. Raw: {raw}")

    # Normalize and validate
    data.setdefault("valid", False)
    data.setdefault("reason", "")
    data.setdefault("requiredQuestions", [])
    data.setdefault("confidence", None)

    if not isinstance(data["requiredQuestions"], list):
        data["requiredQuestions"] = [str(data["requiredQuestions"])]

    conf = data.get("confidence")
    if isinstance(conf, (int, float)):
        if conf < 0.0:
            data["confidence"] = 0.0
        elif conf > 1.0:
            data["confidence"] = 1.0

    # Ensure shape types
    data["valid"] = bool(data["valid"])
    data["reason"] = str(data["reason"] or "")

    # Optional: trim questions
    data["requiredQuestions"] = [
        str(q).strip() for q in data["requiredQuestions"] if str(q).strip()
    ]

    return data
