# src/utils/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ----------------------------------
    # Azure OpenAI (Entra ID only)
    # ----------------------------------
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_DEPLOYMENT: str

    # ----------------------------------
    # Azure DevOps
    # ----------------------------------
    ADO_ORG_URL: str
    ADO_PROJECT: str
    ADO_PAT: str  # or later replace with ADO OAuth if required

    # ----------------------------------
    # Environment Settings
    # ----------------------------------
    ENVIRONMENT: str = "local"  # local | dev | prod

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
