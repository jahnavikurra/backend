from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ----------------------------------
    # Azure OpenAI
    # ----------------------------------
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_DEPLOYMENT: str

    # ----------------------------------
    # Azure Identity / Key Vault
    # ----------------------------------
    AZURE_CLIENT_ID: str | None = None
    AZURE_TENANT_ID: str | None = None
    AZURE_KEY_VAULT_NAME: str | None = None
    AZURE_KEY_VAULT_URL: str | None = None

    # Key Vault secret names
    AZURE_CLIENT_SECRET_SECRET_NAME: str | None = None
    ADO_PAT_SECRET_NAME: str | None = None

    # ----------------------------------
    # Azure DevOps
    # ----------------------------------
    ADO_ORGANIZATION: str
    ADO_PROJECT: str
    ADO_DEFAULT_AREA_PATH: str | None = None
    ADO_DEFAULT_ITERATION_PATH: str | None = None

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


settings = Settings()
