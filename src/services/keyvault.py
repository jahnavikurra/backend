from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from src.utils.config import settings


def get_secret(secret_name: str) -> str:
    credential = DefaultAzureCredential()
    client = SecretClient(
        vault_url=settings.AZURE_KEY_VAULT_URL,
        credential=credential,
    )

    secret = client.get_secret(secret_name)
    if not secret or not secret.value:
        raise ValueError(f"Secret '{secret_name}' was not found or has no value.")

    return secret.value
