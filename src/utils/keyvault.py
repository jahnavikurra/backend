from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from src.utils.config import settings


def _get_vault_url() -> str:
    if settings.resolved_key_vault_url:
        return settings.resolved_key_vault_url

    raise ValueError("Azure Key Vault URL or name is not configured.")


def _get_credential() -> DefaultAzureCredential:
    if settings.AZURE_CLIENT_ID:
        return DefaultAzureCredential(
            managed_identity_client_id=settings.AZURE_CLIENT_ID
        )

    return DefaultAzureCredential()


def get_secret_from_key_vault(secret_name: str) -> str:
    if not secret_name:
        raise ValueError("Secret name was not provided.")

    client = SecretClient(
        vault_url=_get_vault_url(),
        credential=_get_credential(),
    )

    value = client.get_secret(secret_name).value
    if not value:
        raise ValueError(f"Secret '{secret_name}' is empty or not found.")

    return value
