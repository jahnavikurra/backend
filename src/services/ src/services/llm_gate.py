import json
from typing import Any, Dict

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
- valid=true ONLY if the text clearly describes a feature/bug/task with understandable intent.
- If text is random, meaningless, too vague, or not actionable -> valid=false.
- requiredQuestions should ask what is missing (goal, expected behavior, user, scope, etc).
- confidence between 0.0 and 1.0
""".strip()


def _client() -> AzureOpenAI:
    if not settings.AZURE_OPENAI_ENDPOINT:
        raise RuntimeError("Missing AZURE_OPENAI_ENDPOINT")
    if not settings.AZURE_OPENAI_DEPLOYMENT:
        raise RuntimeError("Missing AZURE_OPENAI_DEPLOYMENT")

    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )

    return AzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )


def _safe_json(text: str) -> Dict[str, Any]:
    """
    Parse STRICT JSON. If the model returns extra text, try extracting first {...}.
    """
    text = (text or "").strip()
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                pass

    return {
        "valid": False,
        "reason": "Model did not return valid JSON",
        "requiredQuestions": ["Please provide clearer actionable requirements."],
        "confidence": 0.0,
    }


def gate_validate_notes(notes: str) -> Dict[str, Any]:
    """
    Calls LLM as strict gate before generating work items.
    """
    notes = (notes or "").strip()

    # quick local gate
    if len(notes) < 10:
        return {
            "valid": False,
            "reason": "Input is too short / unclear",
            "requiredQuestions": [
                "What feature/bug/task do you want to create? Provide clear details."
            ],
            "confidence": 0.2,
        }

    client = _client()
    resp = client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        temperature=0,
        messages=[
            {"role": "system", "content": GATE_SYSTEM_PROMPT},
            {"role": "user", "content": notes},
        ],
    )

    content = resp.choices[0].message.content if resp and resp.choices else ""
    data = _safe_json(content)

    # Normalize required keys
    data.setdefault("valid", False)
    data.setdefault("reason", "No reason provided")
    data.setdefault("requiredQuestions", [])
    data.setdefault("confidence", 0.0)

    # Clamp confidence
    try:
        data["confidence"] = max(0.0, min(1.0, float(data["confidence"])))
    except Exception:
        data["confidence"] = 0.0

    return data
