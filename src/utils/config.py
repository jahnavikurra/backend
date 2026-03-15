from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ----------------------------------
    # Azure OpenAI
    # ----------------------------------
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_DEPLOYMENT: str
    AZURE_OPENAI_API_VERSION: str = "2024-02-01"

    # ----------------------------------
    # Azure Identity / Key Vault
    # ----------------------------------
    AZURE_CLIENT_ID: Optional[str] = None
    AZURE_TENANT_ID: Optional[str] = None
    AZURE_KEY_VAULT_NAME: Optional[str] = None
    AZURE_KEY_VAULT_URL: Optional[str] = None

    # Key Vault secret names
    AZURE_CLIENT_SECRET_SECRET_NAME: Optional[str] = None
    ADO_PAT_SECRET_NAME: Optional[str] = None

    # ----------------------------------
    # Azure DevOps
    # ----------------------------------
    ADO_ORGANIZATION: Optional[str] = None
    ADO_ORG_URL: Optional[str] = None
    ADO_PROJECT: Optional[str] = None
    ADO_DEFAULT_AREA_PATH: Optional[str] = None
    ADO_DEFAULT_ITERATION_PATH: Optional[str] = None

    # ----------------------------------
    # App
    # ----------------------------------
    ENVIRONMENT: str = "local"
    LOG_LEVEL: str = "INFO"
    PORT: int = 8010

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def resolved_ado_org_url(self) -> Optional[str]:
        if self.ADO_ORG_URL:
            return self.ADO_ORG_URL.rstrip("/")

        if self.ADO_ORGANIZATION:
            org = self.ADO_ORGANIZATION.strip().strip("/")
            if org.startswith("http://") or org.startswith("https://"):
                return org.rstrip("/")
            return f"https://dev.azure.com/{org}"

        return None

    @property
    def resolved_key_vault_url(self) -> Optional[str]:
        if self.AZURE_KEY_VAULT_URL:
            return self.AZURE_KEY_VAULT_URL.rstrip("/")

        if self.AZURE_KEY_VAULT_NAME:
            return f"https://{self.AZURE_KEY_VAULT_NAME}.vault.azure.net"

        return None


settings = Settings()
