from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Azure AI / Foundry
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_DEPLOYMENT: str
    AZURE_OPENAI_API_VERSION: str = "2024-10-21"

    # Azure DevOps
    ADO_ORG_URL: str

    # Key Vault
    AZURE_KEY_VAULT_URL: str
    ADO_PAT_SECRET_NAME: str

    # App
    ENVIRONMENT: str = "local"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
