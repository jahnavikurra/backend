from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from src.utils.config import settings


def _get_vault_url() -> str:
    if settings.AZURE_KEY_VAULT_URL:
        return settings.AZURE_KEY_VAULT_URL.rstrip("/")

    if settings.AZURE_KEY_VAULT_NAME:
        return f"https://{settings.AZURE_KEY_VAULT_NAME}.vault.azure.net"

    raise ValueError("Azure Key Vault URL or name is not configured.")


def _get_credential() -> DefaultAzureCredential:
    return DefaultAzureCredential(
        managed_identity_client_id=settings.AZURE_CLIENT_ID
    )


def get_secret_from_key_vault(secret_name: str) -> str:
    if not secret_name:
        raise ValueError("Secret name was not provided.")

    client = SecretClient(
        vault_url=_get_vault_url(),
        credential=_get_credential(),
    )

    return client.get_secret(secret_name).value
