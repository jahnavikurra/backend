import json
from typing import Any, Dict

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from src.utils.config import settings


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


def soft_gate(notes: str, work_item_type: str = "PBI") -> Dict[str, Any]:

    if len(notes.strip()) < 2:
        return {
            "action": "ask_questions_only",
            "messageToUser": "Please provide more details.",
            "questions": ["What should be built or fixed?"],
            "assumptions": [],
            "confidence": 0.2,
        }

    return {
        "action": "create_draft",
        "messageToUser": "Draft created.",
        "questions": [],
        "assumptions": [],
        "confidence": 0.9,
    }
