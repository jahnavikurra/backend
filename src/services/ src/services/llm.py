# src/services/llm.py

import json
from typing import Any, Dict, Optional

from openai import AzureOpenAI
from azure.identity import (
    DefaultAzureCredential,
    ManagedIdentityCredential,
    ClientSecretCredential,
    get_bearer_token_provider,
)

from src.utils.config import settings


def _get_credential():
    """
    Enterprise-ready credential resolution:
    1. Managed Identity (Azure)
    2. Service Principal (if provided)
    3. Azure CLI login (local)
    """

    # If running in Azure with Managed Identity
    try:
        return ManagedIdentityCredential()
    except Exception:
        pass

    # If Service Principal is configured (optional enterprise scenario)
    # Requires these env vars:
    # AZURE_TENANT_ID
    # AZURE_CLIENT_ID
    # AZURE_CLIENT_SECRET
    try:
        return ClientSecretCredential(
            tenant_id=settings.__dict__.get("AZURE_TENANT_ID"),
            client_id=settings.__dict__.get("AZURE_CLIENT_ID"),
            client_secret=settings.__dict__.get("AZURE_CLIENT_SECRET"),
        )
    except Exception:
        pass

    # Fallback: DefaultAzureCredential (local dev)
    return DefaultAzureCredential()


def _client() -> AzureOpenAI:
    credential = _get_credential()

    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default",
    )

    return AzureOpenAI(
        base_url=f"{settings.AZURE_OPENAI_ENDPOINT.rstrip('/')}/openai/v1/",
        api_key=token_provider,  # Entra ID token provider
    )


def generate_response(prompt: str) -> Dict[str, Any]:
    client = _client()

    response = client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": "You are an AI Work Item Assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content
