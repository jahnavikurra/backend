import json
from typing import Any, Dict, Optional

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from src.utils.config import settings


SYSTEM_PROMPT = """
You are an Azure DevOps Work Item Assistant.

Turn short notes into a structured work item.

Return JSON with this structure:

{
"title": "string",
"description": "string",
"valueStatement": "string",
"acceptanceCriteria": ["string"],
"tasks": ["string"],
"assumptions": ["string"],
"dependencies": ["string"],
"questions": ["string"],
"confidence": 0.0
}
"""


def _client() -> AzureOpenAI:

    credential = DefaultAzureCredential()

    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default",
    )

    return AzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )


def generate_work_item_draft(
    notes_text: str,
    work_item_type: str = "PBI",
    extra_context: Optional[str] = None,
) -> Dict[str, Any]:

    client = _client()

    prompt = f"""
Work Item Type: {work_item_type}

Notes:
{notes_text}
"""

    if extra_context:
        prompt += f"\nContext:\n{extra_context}"

    resp = client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    content = resp.choices[0].message.content

    return json.loads(content)
